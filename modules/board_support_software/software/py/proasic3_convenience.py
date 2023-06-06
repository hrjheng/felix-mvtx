from collections import OrderedDict

import datetime
import json
import time

# import enums that define the registers.
from proasic3_enums import Pa3Register, \
    CcActiveState, CcCmdOpcode, CcStatus, RcCmdOpcode, \
    RcState, SmapCmdOpcode, SmapStatus, FlashCmdOpcode, \
    FlashFsmBlockEraseControllerState, FlashFsmNandControllerState, \
    FlashFsmPageReadController, FlashFsmPageWriteController, \
    FlashFsmReadIdControllerState, FifoState, FifoWriterCmdOpcode, \
    FifoWriterStatus, FlashSelectICOpcode, EccCmdFlags, \
    EccCmdOpcodes, EccStatus, LocalClockMuxInputSelect

EXEC = 0x80

ARM_SCRUBBING_KEY = 0xA5
PA3_FW_MATURE = 0x20d

BLOCK_COUNT = 8192
PAGE_SIZE = 0x1000
PAGE_SIZE_ECC = 0x1060
PAGE_PER_BLOCK = 64
ADDRESS_MAX = PAGE_PER_BLOCK * BLOCK_COUNT
PAGES_IN_SCRUB_FILE = 4504


class ConvenienceInitializer:
    """ send PA3 write, read, and logger methods to this

    why not use the Pa3 object you ask? answer: because the methods needed are explicitly these.
    So this will look cleaner, and be easier to read.
    """

    def __init__(self, write_f, read_f, logger):
        assert callable(write_f)
        assert callable(read_f)
        self.write_f = write_f
        self.read_f = read_f
        self.logger = logger


class ConvenienceBase:
    """ parent of convenience functions. Takes initalizer of class ConvenienceInitializer
    usages: child = Child(Initializer)
    , ecc_commands = Ecc(Initializer)"""

    def __init__(self, convcarrier: ConvenienceInitializer):
        self.read_reg = convcarrier.read_f
        self.write_reg = convcarrier.write_f
        self.logger = convcarrier.logger

    def version(self, verbose=True):
        """Gets the PA3 FPGA design version"""
        version_msb = self.read_reg(Pa3Register.MAJOR_VERSION)
        version_lsb = self.read_reg(Pa3Register.MINOR_VERSION)
        version = ((version_msb & 0xFF) << 8) | (version_lsb & 0xFF)
        if verbose:
            self.logger.info(f"ProAsic3 Ru Board firmware v{version:04X}")
        return hex(version)

    def is_pa3_fw_mature(self):
        """Determine if loaded PA3 FW supports mature features like arm scrubbing key and custom scrub locations"""
        return True if int(self.version(False), 16) >= PA3_FW_MATURE else False

class Status(ConvenienceBase):
    """Basic status items"""

    def get_dipswitches(self):
        lsb = self.read_reg(Pa3Register.DIPSWITCH1)
        msb = self.read_reg(Pa3Register.DIPSWITCH2)
        return msb << 8 | lsb

    def get_led(self):
        return self.read_reg(Pa3Register.CTRL_LEDS)

    def set_led(self, value):
        assert value <= 0xF
        self.write_reg(Pa3Register.CTRL_LEDS, value)

    def config_get(self, filename=None) -> dict:
        """Print (or if filename is set, log to file) all wishbone registers of the PA3"""
        regs = dict()
        regs["TIMESTAMP"] = datetime.datetime.now().isoformat()
        for register in Pa3Register:
            regs[register.name] = f"0x{self.read_reg(register):02x}"  # hex(self.read_reg(register))
        if filename:
            with open(filename, 'a') as logfile:
                json.dump(regs, logfile)
        return regs

    def githash(self):
        regs = [Pa3Register.HASH_0, Pa3Register.HASH_1,
                Pa3Register.HASH_2, Pa3Register.HASH_3]
        hashcode = 0
        for i, reg in enumerate(regs):
            regval = self.read_reg(reg)
            hashcode = hashcode | (regval << 8 * i)
        return hashcode


class ConfigController(ConvenienceBase):
    """Configuration controller module, responsible for scrubbing and programming of the ultrascale

    reprogram_ultrascale loads the firmare onto the Xilinx

    (start/stop)_blind_scrubbing controls the blind scrubbing. If this works you should see the scrubbing counter increase

    get_scrubbing_counter shows the n.o. times scrubbing has occured since reset

    cc is short for Configuration Controller
    """

    def set_cc_command_register(self, opcode, execute=True):
        """Writes the CC_CMD register"""
        opcode = CcCmdOpcode(opcode)
        self.write_reg(Pa3Register.CC_CMD, opcode | (execute and EXEC))

    def get_cc_command_register(self):
        """Reads the CC_CMD register"""
        value = self.read_reg(Pa3Register.CC_CMD)
        name = None
        if value in [item.value for item in CcCmdOpcode]:
            name = CcCmdOpcode(value).name
        return value, name

    def get_program_done(self):
        value = self.read_reg(Pa3Register.SMAP_STATUS)
        return (value >> SmapStatus.XILINX_DONE_PIN) & 1, value

    def program_xcku(self, use_gold=False):
        if use_gold:
            init_gold_opcode = CcCmdOpcode.INIT_CONFIG_2
            self.set_cc_command_register(init_gold_opcode)
        else:
            self.set_cc_command_register(CcCmdOpcode.INIT_CONFIG)

    def start_blind_scrubbing(self):
        if self.is_golden_config_done():
            self.logger.error("Scrubbing can not be run with bitfile loaded from golden position")
            return
        if self.is_pa3_fw_mature():
            self.arm_scrubbing()
        self.set_cc_command_register(CcCmdOpcode.CONT_SCRUB)
        if self.is_pa3_fw_mature():
            self.disarm_scrubbing() # For safety

    def stop_blind_scrubbing(self):
        self.set_cc_command_register(CcCmdOpcode.STOP)

    def run_single_scrub(self, max_trials=5, wait_sec=0.55, verbose=False):
        """Run a single scrub cycle"""
        if self.is_pa3_fw_mature():
            self.arm_scrubbing()
        self.set_cc_command_register(CcCmdOpcode.SINGLE_SCRUB)
        for i in range(max_trials):
            time.sleep(wait_sec)
            cc_status = self.get_cc_status()
            if verbose:
                self.logger.debug(f"Scrubbing ongoing: {self.is_scrubbing(cc_status)}, Busy: {self.is_busy(cc_status)}")
            if self.is_scrubbing_done(cc_status):
                if verbose:
                    self.logger.info(f"Scrubbing cycle completed after {wait_sec*(i+1)}s")
                return True
        if self.is_pa3_fw_mature():
            # For safety
            self.disarm_scrubbing()

        # Failed! But this is expected if there was a DB error.
        self.logger.debug(f"Scrubbing cycle failed after {max_trials} trials with {wait_sec}s sleep between polling!")
        return False

    def run_single_scrub_test(self, verbose=False):
        """Run a single scrub cycle in test mode, i.e. with the SMAP interface disabled"""
        self.set_disable_programming()
        success = self.run_single_scrub(verbose=verbose)
        self.clear_disable_programming()
        return success

    def clear_scrubbing_counter(self):
        self.logger.info("Resetting PA3 scrubbing counter")
        self.set_cc_command_register(CcCmdOpcode.SCRUB_CNT_CLR)

    def get_cc_status(self):
        value = self.read_reg(Pa3Register.CC_STATUS)
        ret_dict = {}
        for flag in CcStatus:
            ret_dict[flag.name] = (value >> flag.value) & 1
        return value, ret_dict

    def get_scrubbing_counter(self):
        scrub_cnt_lsb = self.read_reg(Pa3Register.CC_SCRUB_CNT_LSB)
        scrub_cnt_msb = self.read_reg(Pa3Register.CC_SCRUB_CNT_MSB)
        scrub_cnt = (scrub_cnt_msb << 8) | scrub_cnt_lsb
        return scrub_cnt

    def get_bs_key(self):
        return self.read_reg(Pa3Register.CC_BS_KEY)

    def set_bs_key(self, value):
        self.write_reg(Pa3Register.CC_BS_KEY, value)

    def arm_scrubbing(self):
        self.set_bs_key(ARM_SCRUBBING_KEY)

    def disarm_scrubbing(self):
        """In the event scrubbing was not executed, one needs to manually disarm"""
        self.set_bs_key(0)

    def is_scrubbing_armed(self):
        return True if self.get_bs_key() == ARM_SCRUBBING_KEY else False

    def get_crc(self):
        crc_0 = self.read_reg(Pa3Register.CRC_0)
        crc_1 = self.read_reg(Pa3Register.CRC_1)
        crc_2 = self.read_reg(Pa3Register.CRC_2)
        crc_3 = self.read_reg(Pa3Register.CRC_3)
        crc = (crc_3 << 24) | (crc_2 << 16) | (crc_1 << 8) | crc_0
        return crc

    def log_crc(self):
        self.logger.info(f"CRC: {hex(self.get_crc())}")

    def get_upcounter(self):
        upcounter_0 = self.read_reg(Pa3Register.UPCOUNTER_0)
        upcounter_1 = self.read_reg(Pa3Register.UPCOUNTER_1)
        upcounter = ((upcounter_1 << 8) | upcounter_0)
        return str(datetime.timedelta(seconds=int(upcounter*67.108864)))

    def get_reset_upcounter(self):
        reset_upcounter_0 = self.read_reg(Pa3Register.RST_UPCOUNTER_0)
        reset_upcounter_1 = self.read_reg(Pa3Register.RST_UPCOUNTER_1)
        reset_upcounter = ((reset_upcounter_1 << 8) | reset_upcounter_0)
        return str(datetime.timedelta(seconds=int(reset_upcounter*67.108864)))

    def set_disable_programming(self):
        self.write_reg(Pa3Register.DISABLE_PROGRAMMING, 0x1)

    def clear_disable_programming(self):
        self.write_reg(Pa3Register.DISABLE_PROGRAMMING, 0x0)

    def is_disable_programming_set(self):
        return self.read_reg(Pa3Register.DISABLE_PROGRAMMING) == 1

    def get_crc_write_cnt(self):
        return self.read_reg(Pa3Register.CRC_WRITE_CNT)

    def is_busy(self, cc_status=None):
        if cc_status is None:
            cc_status = self.get_cc_status()
        return cc_status[1]['BUSY'] == 1

    def is_idle(self, cc_status=None):
        if cc_status is None:
            cc_status = self.get_cc_status()
        return cc_status[1]['IDLE'] == 1

    def is_config_done(self, golden=False):
        """returns the configuration done for standard and golden configurations"""
        if golden:
            return self.is_golden_config_done()
        else:
            return self.is_init_config_done()

    def is_init_config_done(self, cc_status=None):
        if cc_status is None:
            cc_status = self.get_cc_status()
        return cc_status[1]['INIT_CONFIG_DONE'] == 1

    def is_golden_config_done(self, cc_status=None):
        if cc_status is None:
            cc_status = self.get_cc_status()
        return cc_status[1]['GOLDEN_CONFIG_DONE'] == 1

    def is_scrubbing(self, cc_status=None):
        if cc_status is None:
            cc_status = self.get_cc_status()
        return cc_status[1]['SCRUBBING_ONGOING'] == 1

    def is_scrubbing_done(self, cc_status=None):
        if cc_status is None:
            cc_status = self.get_cc_status()
        return cc_status[1]['SCRUBBING_DONE'] == 1

    def get_cc_active_state(self):
        value = self.read_reg(Pa3Register.CC_ACTIVE_STATE)
        return value, CcActiveState(value).name


class DoubleBitError(Exception):
    pass


class ScrubbingStuckOn(Exception):
    pass


class Ecc(ConvenienceBase):
    """ Ecc module, responsible for data integrity on the flash chip."""

    def get_ecc_command_register(self):
        value = self.read_reg(Pa3Register.ECC_COMMAND)
        ret_dict = {}
        for flag in EccCmdFlags:
            ret_dict[str(flag.name)] = (value >> flag.value) & 1
        return value, ret_dict

    def enable_ecc(self):
        self.write_reg(Pa3Register.ECC_COMMAND, EccCmdOpcodes.ECC_CLEAR_ENABLE)

    def disable_ecc(self):
        self.write_reg(Pa3Register.ECC_COMMAND, EccCmdOpcodes.ECC_CLEAR_DISABLE)

    def reset_ecc_counters_and_status(self):
        if self.ecc_on():
            self.write_reg(Pa3Register.ECC_COMMAND, EccCmdOpcodes.ECC_CLEAR_ENABLE)
        else:
            self.write_reg(Pa3Register.ECC_COMMAND, EccCmdOpcodes.ECC_CLEAR_DISABLE)

    def get_ecc_sb_error_payload_counter(self):
        return self.read_reg(Pa3Register.ECC_SB_ERROR_CNT)

    def get_ecc_sb_error_eccbits_counter(self):
        return self.read_reg(Pa3Register.ECC_ECCSB_CNT)

    def get_ecc_sb_error_total_counter(self):
        return (self.get_ecc_sb_error_payload_counter() + self.get_ecc_sb_error_eccbits_counter())

    def get_ecc_fifo_tmr_error(self):
        return self.read_reg(Pa3Register.ECC_FIFO_TMR_ERROR)

    def clear_ecc_status(self):
        self.write_reg(Pa3Register.ECC_STATUS, 0xF)

    def get_status(self):
        return self.read_reg(Pa3Register.ECC_STATUS)

    def get_db_error(self):
        mask = (1 << EccStatus.DB_ERROR)
        return ((self.get_status() & mask) >> EccStatus.DB_ERROR)

    def has_db_error_occurred(self):
        return (self.get_db_error() != 0)

    def get_sb_error(self):
        mask = (1 << EccStatus.SB_ERROR)
        return ((self.get_status() & mask) >> EccStatus.SB_ERROR)

    def has_sb_error_occurred(self):
        return self.get_sb_error() != 0

    def get_eccsb_error(self):
        mask = (1 << EccStatus.ECCSB_ERROR)
        return ((self.get_status() & mask) >> EccStatus.ECCSB_ERROR)

    def get_fifo_tmr_error(self):
        mask = (1 << EccStatus.TMR_ERROR_IN_READ_FIFO)
        return ((self.get_status() & mask) >> EccStatus.TMR_ERROR_IN_READ_FIFO)

    def ecc_on(self) -> bool:
        """is ecc on?"""
        return self.read_reg(Pa3Register.ECC_COMMAND) & 0b1 == 1

    def ecc_ok(self) -> bool:
        """is ecc in a good state?"""
        status = self.read_reg(Pa3Register.ECC_STATUS)
        good = status == 0
        return good


class Flash(ConvenienceBase):
    """Flash module registers"""

    # if pattern verification is wanted this function must be adapted to read/write function to check status of bit 6
    def set_flash_command_register(self, opcode, execute=True):
        """
        Write opcode to flash control module
        :param FlashCmdOpcode opcode: opcode. Careful!
        :param bool execute: should always be True
        """
        opcode = FlashCmdOpcode(opcode)
        self.write_reg(Pa3Register.FLASH_CTRL, opcode | (execute and EXEC))

    def get_flash_command_register(self):
        value = self.read_reg(Pa3Register.FLASH_CTRL)
        name = None
        if value in [item.value for item in FlashCmdOpcode]:
            name = FlashCmdOpcode(value).name
        return value, name

    def set_flash_address(self, block_address=0, page_address=0, whole_address=None):
        """Uses either block_address and page_addres OR the whole_address
        :param int block_address: 13 bit "block" address
        :param int page_address: 6 bit "page" address
        :param int whole_address: 19 bit address (8192 block count * 64 pages per block)
        """
        if whole_address is None:
            assert block_address <= 0x1FFF
            assert page_address <= 0x3F
            addr1 = ((block_address & 0x3) << 6) | page_address
            addr2 = (block_address >> 2) & 0xFF
            addr3 = (block_address >> 10) & 0x07
        else:
            assert whole_address <= 0x7FFFF
            addr1 = whole_address & 0xFF
            addr2 = (whole_address >> 8) & 0xFF
            addr3 = (whole_address >> 16) & 0x07
        self.write_reg(Pa3Register.FLASH_ROW_ADDR3, addr3)
        self.write_reg(Pa3Register.FLASH_ROW_ADDR2, addr2)
        self.write_reg(Pa3Register.FLASH_ROW_ADDR1, addr1)

    def get_flash_byte_counter(self):
        value = self.read_reg(Pa3Register.FLASH_TRX_CNT_LSB)
        value = self.read_reg(Pa3Register.FLASH_TRX_CNT_MSB) << 8 | value
        return value

    def set_flash_select_ic(self, value):
        """
        b00: Not legal value. Default flash b01 (IC 1) is selected  \n
        b01: Flash IC 1 (FLASH_CE1/FLASH_R_B1_n)  \n
        b10: Flash IC 2 (FLASH_CE2/FLASH_R_B2_n)  \n
        b11: Both IC1 and IC2 active (NOT LEGAL FOR READ PAGE OR READ ID OPERATION - WILL CORRUPT DATA. Writing and Erasing is OK.
        """
        self.write_reg(Pa3Register.FLASH_SELECT_IC, value)

    def set_scrub_block_address(self, start_block):
        """Set start and stop pages to use with non-page0 start block address

        Args:
            start_block (int): Start block address of non-page0 scrub location
        """
        if self.is_pa3_fw_mature():
            start_page = start_block * PAGE_PER_BLOCK
            stop_page = start_page + PAGES_IN_SCRUB_FILE
            self.set_bs_start(start_page)
            self.set_bs_stop(stop_page)
        else:
            self.logger.warning("Ignoring block address for non-mature PA3 version - you might be scrubbing with wrong location...")

    def clear_scrub_block_address(self):
        self.set_bs_start(0)
        self.set_bs_stop(0)

    def set_bs_start(self, start_page):
        page0 = start_page & 0xFF
        page1 = (start_page >> 8) & 0xFF
        page2 = (start_page >> 16) & 0x07
        self.write_reg(Pa3Register.BS_START_0, page0)
        self.write_reg(Pa3Register.BS_START_1, page1)
        self.write_reg(Pa3Register.BS_START_2, page2)

    def get_bs_start(self):
        value = (self.read_reg(Pa3Register.BS_START_0) |
                 self.read_reg(Pa3Register.BS_START_1) << 8 |
                 self.read_reg(Pa3Register.BS_START_2) << 16)
        return value

    def set_bs_stop(self, stop_page):
        page0 = stop_page & 0xFF
        page1 = (stop_page >> 8) & 0xFF
        page2 = (stop_page >> 16) & 0x07
        self.write_reg(Pa3Register.BS_STOP_0, page0)
        self.write_reg(Pa3Register.BS_STOP_1, page1)
        self.write_reg(Pa3Register.BS_STOP_2, page2)

    def get_bs_stop(self):
        value = (self.read_reg(Pa3Register.BS_STOP_0) |
                 self.read_reg(Pa3Register.BS_STOP_1) << 8 |
                 self.read_reg(Pa3Register.BS_STOP_2) << 16)
        return value

    def get_flash_select_ic(self):
        value = self.read_reg(Pa3Register.FLASH_SELECT_IC)
        if value in [item.value for item in FlashSelectICOpcode]:
            name = FlashSelectICOpcode(value).name
        return value, name

    def get_flash_status_word(self):
        value = self.read_reg(Pa3Register.FLASH_STATUS_WORD)
        return value

    def get_flash_status(self):
        """
        #1 [0] Done with command (Read/Write/Erase/Read ID)
        #2 [1] Fifo Status (Write FIFO EMPTY or Read FIFO FULL)
        #4 [2] Status Bit from Flash after ended command. '1' means an error has occured.
        #8 [3] Write Active
        #0x10 [4] Read Active
        #0x20 [5] Command Active (ReadID, Erase, Reset)
        #0x40 [6] Trx_done (Sticky bit)"
        :return:
        """

        status_dict = OrderedDict({'Done_with_command': False, 'WfifoEmpty_or_RfifoFull': False,
                                   'Error_bit': False, 'Write_active': False, 'Read_active': False,
                                   'Command_active': False, 'done_sticky': False, 'activity': False})
        value = self.read_reg(Pa3Register.FLASH_STATUS)
        for bitn, key in enumerate(status_dict.keys()):
            status_dict[key] = bool((value >> bitn) & 0b1)
        status_dict['activity'] = status_dict['Write_active'] or status_dict['Read_active'] or status_dict[
            'Command_active']
        return value, status_dict

    def set_pattern_checker(self, value):
        self.write_reg(Pa3Register.FLASH_PATTERN, value)
        self.write_reg(Pa3Register.FLASH_CTRL, 0x40)
        return value

    def get_flash_state(self):
        value = (self.read_reg(Pa3Register.FLASH_STATE_0) |
                 self.read_reg(Pa3Register.FLASH_STATE_1) << 8 |
                 self.read_reg(Pa3Register.FLASH_STATE_2) << 16 |
                 self.read_reg(Pa3Register.FLASH_STATE_3) << 24)
        ret_dict = {}

        value_tmp = value & 0xF  # [3:0]
        name = None
        if value_tmp in [item.value for item in FlashFsmNandControllerState]:
            name = FlashFsmNandControllerState(value_tmp).name
        ret_dict['fsm_nand_controller'] = (value_tmp, name)

        value_tmp = value >> 4 & 0x3F  # [9:4]
        name = None
        if value_tmp in [item.value for item in FlashFsmPageWriteController]:
            name = FlashFsmPageWriteController(value_tmp).name
        ret_dict['fsm_page_write_controller'] = (value_tmp, name)

        value_tmp = (value >> 9) & 0x3F  # [15:9]
        name = None
        if value_tmp in [item.value for item in FlashFsmPageReadController]:
            name = FlashFsmPageReadController(value_tmp).name
        ret_dict['fsm_page_read_controller'] = (value_tmp, name)

        value_tmp = (value >> 16) & 0x3F  # [21:16]
        name = None
        if value_tmp in [item.value for item in FlashFsmBlockEraseControllerState]:
            name = FlashFsmBlockEraseControllerState(value_tmp).name
        ret_dict['fsm_block_erase_controller'] = (value_tmp, name)

        value_tmp = (value >> 22) & 0xF  # [25:22]
        name = None
        if value_tmp in [item.value for item in FlashFsmReadIdControllerState]:
            name = FlashFsmReadIdControllerState(value_tmp).name
        ret_dict['fsm_read_id_controller'] = (value_tmp, name)

        return value, ret_dict

    def get_flash_page_size(self):
        page_size_lsb = self.read_reg(Pa3Register.FLASH_TRX_SIZE_LSB)
        page_size_msb = self.read_reg(Pa3Register.FLASH_TRX_SIZE_MSB)
        return (page_size_msb << 8) | page_size_lsb

    def set_flash_page_size(self, page_size):
        self.write_reg(Pa3Register.FLASH_TRX_SIZE_LSB, page_size & 0xFF)
        self.write_reg(Pa3Register.FLASH_TRX_SIZE_MSB, (page_size >> 8) & 0xFF)


class Clock(ConvenienceBase):
    """Status and configuration of the RU clock tree"""

    def get_clock_status(self):
        """Get status of loss of lock/signal from the jitter cleaner
        lcl_clk_lol : Jitter cleaner loss of lock
        lcl_clk_c1b : Board clock loss of signal
        lcl_clk_c2b : GBTx0 clock loss of signal"""
        value = self.read_reg(Pa3Register.STATUS_CLOCK)
        ret_dict = {'lcl_clk_lol': (value >> 0) & 1,
                    'lcl_clk_c1b': (value >> 1) & 1,
                    'lcl_clk_c2b': (value >> 2) & 1}
        return value, ret_dict

    def set_clock_config(self, lcl_clk_in_se=None, lcl_clk_cs=None, lcl_clk_rst=None):
        """Set the clock configuration
        :param lcl_clk_in_se : Clock mux select: 0 Jitter cleaner clock, 1 - board clock
        :param lcl_clk_in_cs : Jitter cleaner clock select: 0 - board clock, 1 - GBTx0 clk (pin not connected)
        :param lcl_clk_rst   : Jitter cleaner reset, active low (pin not connected)"""
        do_read = False
        if lcl_clk_in_se is None or lcl_clk_cs is None or lcl_clk_rst is None:
            do_read = True
        if do_read:
            _, read_value = self.get_clock_config()
        if lcl_clk_in_se is None:
            lcl_clk_in_se = read_value['lcl_clk_in_se']
        if lcl_clk_cs is None:
            lcl_clk_cs = read_value['lcl_clk_cs']
        if lcl_clk_rst is None:
            lcl_clk_rst = read_value['lcl_clk_rst']
        assert lcl_clk_in_se in range(2)
        assert lcl_clk_cs in range(2)
        assert lcl_clk_rst in range(2)
        write_value = lcl_clk_rst << 2 | lcl_clk_cs << 1 | lcl_clk_in_se
        self.write_reg(Pa3Register.CNFG_CLOCK, write_value)

    def get_clock_config(self):
        """Gets the clock configuration
        lcl_clk_in_se : Clock mux select: 0 Jitter cleaner clock, 1 - board clock
        lcl_clk_in_cs : Jitter cleaner clock select: 0 - board clock, 1 - GBTx0 clk (pin not connected)
        lcl_clk_rst   : Jitter cleaner reset, active low (pin not connected)"""
        value = self.read_reg(Pa3Register.CNFG_CLOCK)
        ret_dict = {'lcl_clk_in_se': (value >> 0) & 1,
                    'lcl_clk_cs': (value >> 1) & 1,
                    'lcl_clk_rst': (value >> 2) & 1}
        return value, ret_dict

    def set_clock_mux_input(self, value):
        """Sets the clock multiplexer on the RU"""
        value = LocalClockMuxInputSelect(value)
        self.set_clock_config(lcl_clk_in_se=value)

    def get_clock_mux_input(self):
        """Gets the clock multiplexer on the RU"""
        info = self.get_clock_config()[1]['lcl_clk_in_se']
        return LocalClockMuxInputSelect(info).name

    def set_clock_mux_source_crystal(self):
        self.set_clock_mux_input(LocalClockMuxInputSelect.CRYSTAL)

    def set_clock_mux_source_jitter_cleaner(self):
        self.set_clock_mux_input(LocalClockMuxInputSelect.JITTER_CLEANER)


class Fifo(ConvenienceBase):
    def get_fifo_rx_data(self):
        return self.read_reg(Pa3Register.FIFO_DATA_RD)

    def set_fifo_tx_data(self, data):
        assert data <= 0xFF
        self.write_reg(Pa3Register.FIFO_DATA_WR, data)

    def get_fifo_status(self):
        value = self.read_reg(Pa3Register.FIFO_STATUS)
        ret_dict = {}
        for flag in FifoState:
            ret_dict[str(flag.name)] = bool((value >> flag.value) & 1)
        return value, ret_dict

    def set_fifo_writer_command_register(self, opcode, execute=True):
        """
        :param FifoWriterCmdOpcode opcode: opcodes defined by enum
        :param bool execute: True as default
        """
        opcode = FifoWriterCmdOpcode(opcode)  # auto asserts
        self.write_reg(Pa3Register.FIFO_WRITER_CMD, opcode | (execute and EXEC))

    def get_fifo_writer_command_register(self):
        value = self.read_reg(Pa3Register.FIFO_WRITER_CMD)
        name = None
        if value in [item.value for item in FifoWriterCmdOpcode]:
            name = FifoWriterCmdOpcode(value).name
        return value, name

    def get_fifo_writer_status(self):
        value = self.read_reg(Pa3Register.FIFO_WRITER_STATUS)
        ret_dict = {}
        for flag in FifoWriterStatus:
            ret_dict[str(flag.name)] = bool((value >> flag.value) & 1)
        return value, ret_dict


class ReadController(ConvenienceBase):
    """Readcontroller class, see RcCmdOpcode enum """

    def set_rc_command_register(self, opcode, execute=True):
        assert opcode in [item.value for item in RcCmdOpcode], "Invalid RC CMD opcode"
        opcode = RcCmdOpcode(opcode)
        self.write_reg(Pa3Register.RC_CMD, opcode | (execute and EXEC))

    def get_rc_command_register(self):
        value = self.read_reg(Pa3Register.RC_CMD)
        name = None
        if value in [item.value for item in RcCmdOpcode]:
            name = RcCmdOpcode(value).name
        return value, name

    def get_rc_current_page(self):
        value = self.read_reg(Pa3Register.RC_FLASHPAGE1)
        value = self.read_reg(Pa3Register.RC_FLASHPAGE2) << 8 | value
        value = self.read_reg(Pa3Register.RC_FLASHPAGE3) << 16 | value
        return value

    def get_rc_status(self):
        value = self.read_reg(Pa3Register.RC_STATUS)
        ret_dict = {}
        for flag in RcState:
            ret_dict[str(flag.name)] = (value >> flag.value) & 1
        return value, ret_dict


class LossOfLockCounter(ConvenienceBase):
    """loss of lock counting. The counters are edge detectors on the LOL,C1B,C2B lines from the jitter cleaner
    If these go up"""
    def __init__(self, convcarrier: ConvenienceInitializer):
        super().__init__(convcarrier)
        self.count_lol, self.count_c1b, self.count_c2b = 0, 0, 0

    def _update_count(self):
        self.count_lol, self.count_c1b, self.count_c2b = (
            self.read_reg(Pa3Register.LOCAL_CLK_LOL_CNT),
            self.read_reg(Pa3Register.LOCAL_CLK_C1B_CNT),
            self.read_reg(Pa3Register.LOCAL_CLK_C2B_CNT))

    def display(self):
        self._update_count()
        infostr = f"Loss of lock counters \nLOL (local): {self.count_lol}\n" \
            f"C1B: {self.count_c1b}\n" \
            f"C2B: {self.count_c2b}"
        self.logger.info(infostr)

    def get(self):
        """Returns the counters"""
        self._update_count()
        return self.count_lol, self.count_c1b, self.count_c2b

    def jitter_cleaner_is_ok(self):
        previous_counts = [self.count_lol, self.count_c1b, self.count_c2b]
        self._update_count()
        ok = True
        if [self.count_lol, self.count_c1b, self.count_c2b]!= previous_counts:
            ok = False
            self.logger.error(f"Counter not 0 in jitter cleaner lol {self.count_lol},  c1b {self.count_c1b},  c2b {self.count_c2b}" )
        return ok
