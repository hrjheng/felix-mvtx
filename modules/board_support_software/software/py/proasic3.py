"""
   Class implementing an abstraction layer for the ProAsic3
   new for 208: loss of lock counters for the jitter cleaner signals, initially made for debugging of ru board 18
"""

import logging
import time

from gbt_sca import Sca, ScaI2cChannelRU, ScaI2cSpeed, ScaGpioRU, ScaI2cBadStatusError, ScaBadErrorFlagError
from proasic3_enums import Pa3Register
from proasic3_convenience import ConvenienceInitializer, Flash, ReadController
from proasic3_convenience import Status, ConfigController, Clock, LossOfLockCounter, Ecc
from proasic3_convenience import DoubleBitError, ScrubbingStuckOn
from proasic3_flash import ProAsic3Flash
from proasic3_selectmap import ProAsic3Selmap
import git_hash_lut


class ProAsic3:
    """Class to handle PA3 transactions"""
    sca: Sca

    def __init__(self, sca, gbt_channel, ultrascale_fifo_write_f=None):
        """
        :type sca: gbt_sca.Sca
        sca passed from testbench.  \n
        :type ultrascale_fifo_write_f: function
        ultrascale fifo write function passed from testbench
        for enabling loading of the flash via the ultrascale fifo.
        This function should take only one parameter (the data)
        """
        self.logger = logging.getLogger(f"RU {gbt_channel if gbt_channel is not None else ''} PA3")

        self.sca = sca
        self.sca_channel_used = ScaI2cChannelRU.PA3_0

        # to get nice python Fire interface:
        conv_init = ConvenienceInitializer(self.write_reg, self.read_reg, self.logger)
        self.config_controller = ConfigController(conv_init)
        self.start_scrubbing = self.config_controller.start_blind_scrubbing
        self.run_single_scrub = self.config_controller.run_single_scrub
        self.run_single_scrub_test = self.config_controller.run_single_scrub_test
        self.program_xcku = self.config_controller.program_xcku
        self.cfg_is_idle = self.config_controller.is_idle

        self.read_controller = ReadController(conv_init)
        self.get_rc_current_page = self.read_controller.get_rc_current_page

        self._Status = Status(conv_init)
        self.dump_config = self._Status.config_get
        self.version = self._Status.version
        self.githash = self._Status.githash
        self.is_pa3_fw_mature = self._Status.is_pa3_fw_mature

        self._FlashIf = ProAsic3Flash(conv_init, self.write_fifo_reg_multibyte, ultrascale_fifo_write_f, self.reset_pa3)
        self.flash_save_page = self._FlashIf.save_page
        self.flash_write_file = self._FlashIf.flash_write_file
        self.flash_update_parameter_page = self._FlashIf.update_parameter_page
        self.flash_verify_file = self._FlashIf.flash_verify_file
        self.flash_compare_file = self._FlashIf.flash_compare_file
        self.flash_compare_file_with_ecc = self._FlashIf.flash_compare_file_with_ecc
        self.get_bitfile_locations = self._FlashIf.get_bitfile_locations
        self.get_scrub_block_location = self._FlashIf.get_scrub_block_location
        self.test_readback = self._FlashIf.test_readback
        self.flash_read_page = self._FlashIf.flash_read_page

        self._Clock = Clock(conv_init)
        self.set_clock_mux_source_crystal = self._Clock.set_clock_mux_source_crystal
        self.set_clock_mux_source_jitter_cleaner = self._Clock.set_clock_mux_source_jitter_cleaner

        self._SelMap = ProAsic3Selmap(conv_init)
        self.smap_write_frame = self._SelMap.write_frames
        self.smap_read_frame = self._SelMap.read_frames
        self.smap_get_idcode = self._SelMap.get_idcode
        self.smap_read_address = self._SelMap.sm_read

        self.loss_of_lock_counter = LossOfLockCounter(conv_init)

        self.ecc = Ecc(conv_init)

        self._Flash = Flash(conv_init)
        self.get_flash_select_ic = self._Flash.get_flash_select_ic
        self.set_flash_select_ic = self._Flash.set_flash_select_ic
        self.set_scrub_block_address = self._Flash.set_scrub_block_address
        self.clear_scrub_block_address = self._Flash.clear_scrub_block_address

    def initialize(self, ultrascale_write_f=None, verbose=False, reset=False, reset_force=False):
        """Initializes the class"""
        self.sca.initialize_i2c_channel(channel=ScaI2cChannelRU.PA3_0)
        self.sca.set_i2c_w_ctrl_reg(channel=ScaI2cChannelRU.PA3_0, speed=ScaI2cSpeed.f1MHz, nbytes=1, sclmode=0)
        self.sca.initialize_i2c_channel(channel=ScaI2cChannelRU.PA3_1)
        if callable(ultrascale_write_f):
            self.insert_ultrascale_fifo_write_function(ultrascale_write_f)
        if reset:
            self.reset_pa3()
        elif reset_force:
            self.reset_pa3(force=True)
        self.loss_of_lock_counter._update_count()
        if verbose:
            self.logger.info('Done!')

    def insert_ultrascale_fifo_write_function(self, write_function, verbose=False):
        """load write function for fifo data transfer. write function needs to take one parameter (the data)"""
        if callable(write_function):
            if verbose:
                self.logger.info("Loading Xilinx write function into flash interface")
            self._FlashIf.write_ultrascale_fifo = write_function
        else:
            raise ValueError("not a function")

    def set_i2c_channel(self, channel):
        """Changes the active SCA-I2C channel used"""
        channel = ScaI2cChannelRU(channel)
        assert channel in [ScaI2cChannelRU.PA3_0, ScaI2cChannelRU.PA3_1]
        self.sca_channel_used = channel

    def check_git_hash(self, expected_git_hash=None):
        """Verifies the githash against the given value"""
        assert (expected_git_hash is None) or (expected_git_hash | 0xFFFFFFFF == 0xFFFFFFFF)
        githash = self._Status.githash()
        message_hash = ">> git hash: 0x{0:08x}".format(githash)
        if expected_git_hash is not None:
            assert githash==expected_git_hash, f"Expected 0x{expected_git_hash:08X}, got 0x{githash:08X}"
        return message_hash

    def write_reg(self, address, value):
        """Writes to a PA3 register using SCA-I2C single byte mode"""
        assert 0 <= address <= 0x7F, "Only 7-bit address allowed"
        assert 0 <= value <= 0xFF, "Only 8-bit data allowed"

        self.sca._write_i2c(channel=self.sca_channel_used,
                            sl_addr=address,
                            nbytes=1,
                            data0=(value << 24))

    def write_fifo_reg_multibyte(self, address, data):
        """Writes up to 16 bytes to the same PA3 address, ie. fifo mode,
        using SCA-I2C multi byte mode. Expects a bytearray as input"""
        assert address | 0x7F == 0x7F, "Only 7-bit address allowed"
        assert len(data) in range(1, 16 + 1), "Max 16 bytes per I2C transaction"

        data_words = [0, 0, 0, 0]
        data_word = 0
        word_num = 0
        byte_num = 0

        # Join 4 bytes together in a 32-bit data word,
        # and store the 32-bit words in the list data_words
        for byte in data:
            assert byte | 0xFF == 0xFF, "Only 8-bit data allowed"
            data_word = (data_word << 8) | byte
            byte_num += 1

            if byte_num == 4:
                data_words[word_num] = data_word
                data_word = 0
                byte_num = 0
                word_num += 1

        if byte_num != 0:  # Not on a 4-byte boundary, add last word
            data_words[word_num] = data_word << (8 * (4 - byte_num))

        self.sca._write_i2c(channel=self.sca_channel_used,
                            sl_addr=address,
                            nbytes=len(data),
                            data0=data_words[0],
                            data1=data_words[1],
                            data2=data_words[2],
                            data3=data_words[3])

    def read_reg(self, address):
        """Reads a PA3 register using SCA-I2C single byte mode"""
        assert 0 <= address <= 0x7F, "Only 7-bit address allowed"
        try:
            result = self.sca._read_i2c(channel=self.sca_channel_used, sl_addr=address, nbytes=1)
        except Exception as e:
            add = Pa3Register(address)
            self.logger.error("Error in I2C read from address {0} = 0x{1:02X}".format(add.name, add.value))
            raise e
        return (result[0] >> 16) & 0xFF

    def read_fifo_reg(self, address, length):
        """Reads up to 16 bytes to a the same PA3 address, ie. fifo mode,
        using SCA-I2C multi byte mode. Returns a bytearray with the data"""
        assert 0 <= address <= 0x7F, "Only 7-bit address allowed"
        assert length in range(1, 16 + 1), "Max 16 bytes per I2C transaction"

        result = self.sca._read_i2c(channel=self.sca_channel_used, sl_addr=address, nbytes=length)
        data = bytearray(0)

        for byte_num in range(0, length):
            # First entry in results is status, data starts from index 1
            # Line below extracts one byte at a time from results, in correct order
            index = int(byte_num / 4) + 1
            shift_amount = 24 - 8 * (byte_num % 4)
            data_byte = result[index] >> (shift_amount)
            data_byte = data_byte & 0xFF
            data.append(data_byte)
        return data

    def reset_pa3(self, force=False):
        """Pulse reset pin.
         Note: #136 describes a case in which this is not a good idea.
         Make SURE SCRUBBING IS NOT RUNNING

        If force is set to False, a double-bit error causes the reset to be aborted.
        If force is set to True, the PA3 is always reset.
        """
        try:
            self.stop_scrubbing()
            self.reset_then_smap_abort_and_verify()

        except ScrubbingStuckOn as sso:
            self.logger.warning(sso)
            self.reset_then_smap_abort_and_verify()

        except DoubleBitError as dbe:
            self.logger.warning(dbe)
            self._force_reset(force, "Force reset required to reset PA3 with double-bit error")

        except ScaI2cBadStatusError as bse:
            self.logger.error("Could not get PA3 scrubbing status")
            self.logger.error(bse)
            self._force_reset(force, bse)
        except ScaBadErrorFlagError as bef:
            self.logger.error("Could not get PA3 scrubbing status")
            self.logger.error(bef)
            self._force_reset(force, bef)
        except Exception as e:
            self.logger.error("Could not get PA3 scrubbing status")
            self.logger.error(f"Unknown error: {e}")
            self._force_reset(force, e)

    def _force_reset(self, force, msg):
        if force:
            self.logger.debug("PA3 Force reset!")
            self.reset_then_smap_abort_and_verify()
        else:
            self.logger.warning(msg)
            raise PA3ResetFailed(msg)

    def stop_scrubbing(self):
        """Attempt to stop scrubbing if it is running"""
        if self.config_controller.is_scrubbing():
            self.logger.debug("Deactivating scrubbing...")
            if not self.ecc.has_db_error_occurred():
                self.config_controller.stop_blind_scrubbing()
                cnt = 0
                while self.config_controller.is_scrubbing():
                    time.sleep(0.5)
                    cnt = cnt + 1
                    if (cnt == 10): # scrubbing should stop after max 2 seconds - wait for 5 seconds
                        raise ScrubbingStuckOn("Could not stop scrubbing: timed out.")
                self.logger.info("Scrubbing is off!")
                return
            else:
                raise DoubleBitError("Scrubbing already stopped: Double-bit error detected.")

    def _set_pa3_reset(self, value):
        """Sets the PA3 reset pin to specified value

        N.B! Must not be called without a following SM abort and verify, i.e. smap_abort_and_verify().
        """
        self.sca.set_gpio(ScaGpioRU.PA3_RESET, value)

    def smap_abort_and_verify(self):
        """Abort ongoing selectmap transaction and verifies the bus by reading idcode"""
        self._SelMap.abort()
        expected_idcode = 0x13919093
        idcode = self.smap_get_idcode()
        if idcode != expected_idcode:
            raise Exception(f"SM abort and verify not successful: SMAP IDCODE mismatch {idcode}!={expected_idcode}.\nTo restore XCKU, try _SelMap clear_and_init_xilinx")

    def reset_then_smap_abort_and_verify(self):
        """1. Toggles pa3 reset pin,
           2. aborts any ongoing selectmap transaction,
           3. verifies selectmap bus by reading idcode"""
        for i in [1, 0]:
            self._set_pa3_reset(i)
        self.smap_abort_and_verify()

    def stop_scrubbing_and_reset_on_db_error(self):
        """Stop scrubbing, and in case of DB-error, reset the PA3"""
        try:
            self.stop_scrubbing()
        except DoubleBitError as dbe:
            self.logger.info("PA3 stuck after DB error: resetting PA3 and aborting SMap transactions")
            self.reset_then_smap_abort_and_verify()

    def program_xcku_and_check(self, use_gold=False, chip_num=0):
        if self.config_controller.is_scrubbing():
            self.logger.error(f"XCKU Program not executed, scrubbing is active")
            return False
        self.reset_pa3()
        self.set_flash_select_ic(chip_num)
        self.config_controller.program_xcku(use_gold=use_gold)
        time.sleep(2.5)

        if not self.config_controller.is_config_done(golden=use_gold):
            self.logger.error(f"Flash failed to program, init/golden config not done")
            return False
        if self.config_controller.get_program_done()[0] != 1:
            self.logger.error(f"Flash failed to program, program not done")
            return False
        return True

    def set_start_program(self, value):
        """Sets the START_PROGRAM pin of the PA3 FPGA to value"""
        self.sca.set_gpio(ScaGpioRU.PA3_START_PROGRAM, value)

    def dump_selected_config(self):
        """Returns a string with selected registers of the PA3"""
        address_list = [Pa3Register.LOCAL_CLK_LOL_CNT,
                        Pa3Register.LOCAL_CLK_C2B_CNT,
                        Pa3Register.CC_SCRUB_CNT_MSB,
                        Pa3Register.CC_SCRUB_CNT_LSB,
                        Pa3Register.ECC_SB_ERROR_CNT,
                        Pa3Register.ECC_STATUS,
                        Pa3Register.SMAP_STATUS]

        config_str = f"--- PA3 ---\n"
        for address in address_list:
            name = address.name
            try:
                value = self.read_reg(address.value)
                config_str += f"    - {name} : 0x{value:02X}\n"
            except:
                config_str += f"    - {name} : FAILED\n"
        return config_str


class PA3ResetFailed(Exception):
    pass
