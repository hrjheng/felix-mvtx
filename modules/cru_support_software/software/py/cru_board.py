"""O2 CRU implementation"""

import logging
import time
import os
import inspect

from enum import IntEnum, unique
from timeout_decorator import timeout

import libO2Lla

import git_hash_lut

from roc import Roc

import cru_table
import cru_bsp
import cru_dwrapper
import cru_gbt
import cru_ttc
import cru_i2c
import cru_ltc2990

from cru_modules import UserLogicVersionCore, UserLogicVersion, UserLogicCommon, UserLogicLink, UserLogicEP

# Constants
MAX_CHANNELS = 24
CRU_PARALLEL_SC_BASE = 0x00F0
CRU_PARALLEL_SC_REGS = ['add_gbt_sca_wr_data', 'add_gbt_sca_wr_cmd', 'add_gbt_sca_wr_ctr',
                        'add_gbt_ic_wr_data', 'add_gbt_ic_wr_cfg', 'add_gbt_ic_wr_cmd',
                        'add_gbt_swt_wr_l', 'add_gbt_swt_wr_m', 'add_gbt_swt_wr_h',
                        'add_gbt_sca_rd_data', 'add_gbt_sca_rd_cmd', 'add_gbt_sca_rd_ctr',
                        'add_gbt_ic_rd_data',
                        'add_gbt_swt_rd_l', 'add_gbt_swt_rd_m', 'add_gbt_swt_rd_h',
                        'add_gbt_swt_mon', 'add_gbt_swt_word_mon',
                        'add_gbt_sc_rst']
CRU_PARALLEL_SC_ADDR = {x:cru_table.CRUADD[x] for x in CRU_PARALLEL_SC_REGS}


@unique
class GbtxTxMuxMode(IntEnum):
    """Enum defining the operating mode of the gbtx multiplexer.
    The multiplexer controls the downlink to the RU.
    """
    TRIGGER        = 0
    DATA_GENERATOR = 1
    SWT            = 2
    TTC_UP         = 3
    USER_LOGIC     = 4


class O2Cru(Roc):
    """
    Implementation of the O2 CRU
    several functions imported from equivalent class in cru-sw subtree
    """
    def __init__(self, pcie_id="3b:00.0",
                 bar_ch=2,
                 swt_link_list=[],
                 trigger_link_list=[],
                 data_link_list=[]):

        Roc.__init__(self)
        self._pcie_id = pcie_id
        self._bar_ch = bar_ch
        self.logger = logging.getLogger(f"CRU {pcie_id}")

        self.open_roc(self._pcie_id, self._bar_ch)

        self.dwrapper_count = 2

        self.bsp = cru_bsp.CruBsp(pcie_opened_roc=self._roc, pcie_id=self._pcie_id)
        self.dwrapper = cru_dwrapper.CruDwrapper(pcie_opened_roc=self._roc,
                                                 wrapper_count=self.dwrapper_count)
        self.gbt = cru_gbt.CruGbt(pcie_opened_roc=self._roc, ch_range="0")
        self.ttc = cru_ttc.CruTtc(pcie_opened_roc=self._roc, pcie_id=self._pcie_id)

        self._ltc2990_addresses = [0x4c, 0x4e, 0x4f]
        self.ltc2990 = None  # not init for performance issue

        self._minipod_addresses = []
        self.minipod_list = []  # not init for performance issue

        self._assign_link_lists(swt_link_list=swt_link_list,
                                data_link_list=data_link_list,
                                trigger_link_list=trigger_link_list)

        self.gbt.set_links(self._all_links)

        ### LLA
        self._implicit_lla = True
        self._lla_last_break = time.time()
        self._lla_lock_count = 0
        self._lla_session = None
        self._lla_session = libO2Lla.Session(f"CRU_ITS_{os.getpid()}", f"{self._pcie_id}")
        self._lla_is_locked = False

        # UL Modules
        self.ul_version_core = UserLogicVersionCore(self)
        self.ul_version = UserLogicVersion(self)
        self.ul_common = UserLogicCommon(self)

        self.ul_ep = []
        self.ul_links = []
        for dw in range(2):
            self.ul_ep.append(UserLogicEP(self, dw))
            for link in range(12):
                self.ul_links.append(UserLogicLink(self, dw, link))

    def are_ul_links_busy(self):
        for l in self.ul_links:
            if l.is_busy():
                return True
        return False

    def roc_write(self, reg, data, channel=None):
        """
        Write data to ROC register.

        Overload function that shifts base address with offset based on GBT channel.
        Checks if address is one of CRU parallel slow control registers. If yes,
        shift base address based on GBT channel.
        """
        if reg in CRU_PARALLEL_SC_ADDR.values():
            #self.logger.debug(f"Modify addr {hex(reg)} to {hex(self.get_addr_offset(reg, channel))}")
            reg = self.get_addr_offset(reg, channel)
        super().roc_write(reg, data)

    def roc_read(self, reg, channel=None):
        """
        Read from a ROC register

        Overload function that shifts base address with offset based on GBT channel.
        Checks if address is one of CRU parallel slow control registers. If yes,
        shift base address based on GBT channel.
        """
        if reg in CRU_PARALLEL_SC_ADDR.values():
            #self.logger.debug(f"Modify addr {hex(reg)} to {hex(self.get_addr_offset(reg, channel))}")
            reg = self.get_addr_offset(reg, channel)
        return super().roc_read(reg)

    def get_addr_offset(self, addr, channel):
        """
        Adds the offset for the selected GBT channel

        When using the parallel slow control feature of the CRU, the base addr offset
        must be tweaked for all reg writes and reads using base addr 0x00F0_0000. This function
        simply adds the base addr increment for the selectect gbt channel. One can either used
        the preset selected channel for CRU or specify channel for the operation that is
        different from the selected gbt channel.
        """
        assert (addr >> 16) == CRU_PARALLEL_SC_BASE, f"Expected base addr 0x00F0, got 0x{(addr >> 16):04X}"
        return addr + (channel << 8)


    def _lock_comm(self):
        if self._implicit_lla:
            if not self._lla_is_locked:
                lock_attempt_counter = 0
                while (not self._lla_is_locked):
                    lock_attempt_counter += 1
                    locking_issue = not self._lla_session.start()
                    if locking_issue:
                        if lock_attempt_counter > 500 and lock_attempt_counter < 510:
                            self.logger.warning(f"Its tricky to lock LLA - tries: {lock_attempt_counter}")
                            time.sleep(0.5)
                        elif lock_attempt_counter > 510:
                            self.logger.error(f"Could not lock LLA! - tries: {lock_attempt_counter}")
                            raise Exception(f"Could not lock LLA! - tries: {lock_attempt_counter}")
                    else:
                        self._lla_is_locked = True
                        self._lla_lock_count += 1
            elif self._lla_is_locked:
                self._lla_lock_count += 1
            else:
                self.logger.warning("[LLA] Can't lock comm")
                #self.logger.info(f"{inspect.stack()[1][3]} \t {self._lla_lock_count}")
                return False
            return True
        else:
            return True


    def _unlock_comm(self, force=False):
        if self._implicit_lla:
            if force:
                self._lla_session.stop()
                self._lla_lock_count = 0
            elif (self._lla_is_locked and (self._lla_lock_count <= 1)):
                self._lla_lock_count = 0
                self._lla_session.stop()
                if (time.time()-self._lla_last_break)>0.5:
                    time.sleep(0.5) # 500ms break to let DCS do it's job
                    self._lla_last_break = time.time()
                self._lla_is_locked = False
            elif self._lla_is_locked and (self._lla_lock_count > 1):
                self._lla_lock_count -= 1
            else:
                self.logger.warning("[LLA] You are trying to unlock comm, but it's not locked!")
                #self.logger.info(f"{inspect.stack()[1][3]} \t {self._lla_lock_count}")
                return False
            return True
        else:
            return True

    def _is_lla_locked(self):
        if self._implicit_lla:
            return self._lla_is_locked
        else:
            return True


    def _init_minipods(self):
        self._minipod_addresses = self.get_minipod_addresses()
        for address in self._minipod_addresses:
            try:
                # Init Minipod object
                minipod = cru_i2c.CruI2c(pcie_opened_roc=self._roc,
                                         pcie_id=self._pcie_id,
                                         base_add=cru_table.CRUADD['add_bsp_i2c_minipods'],
                                         chip_add=address)
                self.minipod_list.append((address, minipod))
            except ValueError:
                # chip is neither TX nor RX
                continue

    def git_hash(self):
        return self.bsp.get_short_hash()

    def git_tag(self, git_hash=None):
        if git_hash is None:
            return git_hash_lut.get_cru_version(self.bsp.get_short_hash())
        else:
            return git_hash_lut.get_cru_version(git_hash)

    def version(self):
        self.logger.info(f"CRU Version:\t0x{self.git_hash():08X}\t{self.git_tag()}")

    def compare_expected_githash(self, expected_githash):
        actual_githash = self.bsp.get_short_hash()
        return expected_githash == actual_githash

    def check_git_hash_and_date(self, expected_githash):
        actual_githash = self.bsp.get_short_hash()
        assert actual_githash==expected_githash, f"Expected 0x{expected_githash:08X}, got 0x{actual_githash:08X}"

    def id(self):
        """Returns the board id"""
        id = self.bsp.get_chip_id()
        return id[1]<<32|id[0]

    def get_pcie_id(self):
        return self._pcie_id

    def date(self):
        """Returns the build date"""
        return hex(self.bsp.get_build_date())

    def log_temperatures(self):
        self.logger.info(f"FPGA\t{self.get_fpga_temperature():.2f} C")
        minipod_temperature = self.get_minipod_temperature()
        for mp in minipod_temperature:
            self.logger.info(f"minipod 0x{mp[0]:02X}: {mp[1]:.2f} C")
        t_int, t_ext0, t_ext1 = self.get_ltc2990_temperature()
        for i, chip in enumerate(self._ltc2990_addresses):
            self.logger.info(f"ltc2990 0x{chip:02X}: Internal {t_int[i]:.2f} C external 0 {t_ext0[i]:.2f} C external 1 {t_ext1[i]:.2f} C")

    def get_fpga_temperature(self):
        """Extracted from cru-sw/COMMON/temperature.py"""
        fpga_raw_temp = self.roc_read(cru_table.CRUADD['add_bsp_hkeeping_tempctrl']) & 0x3ff
        return fpga_raw_temp * 693.0 / 1024 - 265    # Convert to degC

    def get_minipod_temperature(self):
        """Extracted from cru-sw/COMMON/temperature.py"""
        if self.minipod_list == []:
            self._init_minipods()
        minipod_temperatures = []
        for add, minipod in self.minipod_list:
            minipod_temperatures.append((add, minipod.getTemperature()))
        return minipod_temperatures

    def get_ltc2990_temperature(self):
        """Extracted from cru-sw/COMMON/temperature.py"""
        chip_adds = self._ltc2990_addresses
        if self.ltc2990 is None:
            self.ltc2990 = cru_ltc2990.CruLtc2990(pcie_opened_roc=self._roc,
                                                  pcie_id=self._pcie_id,
                                                  base_add=cru_table.CRUADD['add_bsp_i2c_tsensor'],
                                                  chip_add=0)

        tint = []
        remote_temp0 = []
        remote_temp1 = []

        for chip_add in chip_adds:
            self.ltc2990.i2c_update_chip_address(chip_add)
            v = self.ltc2990.read_reg(self.ltc2990.TINT_MSB_ADD, self.ltc2990.TINT_LSB_ADD)
            tint.append(self.ltc2990.calc_temperature(v))
            self.ltc2990.reset_i2c()
            self.ltc2990.configure_chip_temperature()

        for chip_add in chip_adds:
            self.ltc2990.i2c_update_chip_address(chip_add)
            # read TR1
            v = self.ltc2990.read_reg(self.ltc2990.V1_MSB_ADD, self.ltc2990.V1_LSB_ADD)
            remote_temp0.append(self.ltc2990.calc_temperature(v))

            # read TR3
            v = self.ltc2990.read_reg(self.ltc2990.V3_MSB_ADD, self.ltc2990.V3_LSB_ADD)
            remote_temp1.append(self.ltc2990.calc_temperature(v))
        return tint, remote_temp0, remote_temp1

    def set_gbt_channel(self, gbt_channel=0):
        """Selects the GBT_CH where the RU is connected to"""
        raise DeprecationWarning("set_gbt_channel() is deprecated")
        assert gbt_channel in self._swt_link_list, f"{gbt_channel} not in {self._swt_link_list}"
        self._selected_gbt_channel = gbt_channel
        add = cru_table.CRUADD['add_gbt_sc_link']
        self.roc_write(add, gbt_channel)

    def get_gbt_channel(self):
        """Returns the GBT CH where the RU is connected to"""
        raise DeprecationWarning("get_gbt_channel() is deprecated")
        return self._selected_gbt_channel

    def _assign_link_lists(self,
                           swt_link_list,
                           trigger_link_list,
                           data_link_list):
        """Assigns the links lists"""
        assert len(list(set(swt_link_list))) == len(swt_link_list), "repeated values in links list: {0}".format(swt_link_list)
        assert len(list(set(trigger_link_list))) == len(trigger_link_list), "repeated values in links list: {0}".format(trigger_link_list)
        assert len(list(set(data_link_list))) == len(data_link_list), "repeated values in links list: {0}".format(data_link_list)

        assert set(swt_link_list).issubset(set(range(MAX_CHANNELS)))
        assert set(data_link_list).issubset(set(range(MAX_CHANNELS)))
        assert set(trigger_link_list).issubset(set(range(MAX_CHANNELS)))

        self._swt_link_list = swt_link_list
        self._data_link_list = data_link_list
        self._trigger_link_list = trigger_link_list
        self._shared_trigger_link = trigger_link_list == []
        self._all_links = list(set(swt_link_list) | set(data_link_list) | set(trigger_link_list))

    def get_swt_link_list(self):
        """Returns the swt link list"""
        return self._swt_link_list

    def get_trigger_link_list(self):
        """Returns the trigger link list"""
        return self._trigger_link_list

    def get_data_link_list(self):
        """Returns the GBT CH where the RU is connected to"""
        return self._data_link_list

    def reset_sc_core(self, channel):
        """Resets the slow control core for a specific link, including SWT FIFOs and SCA core"""
        add_gbt_sc_rst = cru_table.CRUADD['add_gbt_sc_rst']
        self._lock_comm()
        try:
            self.roc_write(add_gbt_sc_rst, 1, channel)
            self.roc_write(add_gbt_sc_rst, 0, channel)
        finally:
            self._unlock_comm()

    def reset_sc_cores(self):
        """Resets all the slow control cores, including SWT FIFOs and SCA core"""
        for channel in range(24):
            self.reset_sc_core(channel)

    def get_swt_monitor_write(self, channel):
        add = cru_table.CRUADD['add_gbt_swt_mon']
        value = self.roc_read(add, channel=channel)
        self.logger.info(f"CRU SWT FIFO Words {value}")
        return value

    def get_swt_flow_monitor_counters(self, channel):
        """Gets the numner of SWT transmitted and received"""
        add = cru_table.CRUADD['add_gbt_swt_word_mon']
        value = self.roc_read(add, channel=channel)
        in_swt = value & 0xFFF
        out_swt = (value>>12) & 0xFFF
        self.logger.info(f"written {out_swt}, read {in_swt}")
        return out_swt, in_swt

    @timeout(5, exception_message=f"cru not coming up, is the RU powered on or connected?\nADVICE: Run a o2-roc-status on the two PCIeID of the CRU and verify that all the SWT links are UP")
    def initialize(self, gbt_ch=None):
        """Initializes the CRU and sets also the GBT downlink multiplexer to SWT."""
        if gbt_ch is not None:
            raise DeprecationWarning("Setting CRU GBT ch is deprecated... To be removed from codebase.")
        self.logger.debug("Initializes CRU...")
        self._lock_comm()
        try:
            self.reset_sc_cores()
            self.bsp.initialize()
            self.dwrapper.initialize(self._data_link_list)
            self.gbt.initialize()
            self.ttc.initialize()
            self.initialize_downlinks()
            self.dwrapper.set_data_link_list(self._data_link_list)
        finally:
            self._unlock_comm()

    # Tx Mux

    def set_gbt_mux_to_swt(self, channel=None):
        """Set transmission of channel to SWT in downlink to the RU (channel == None: all configured channels)"""
        self._set_gbt_tx_mux(GbtxTxMuxMode.SWT, channel)

    def set_gbt_mux_to_ddg(self, channel=None):
        """Set transmission of channel to Data Generator in downlink to the RU (channel == None: all configured channels)"""
        self._set_gbt_tx_mux(GbtxTxMuxMode.DATA_GENERATOR, channel)

    def set_gbt_mux_to_trigger(self, channel=None):
        """Set transmission of channel to Trigger in downlink to the RU (channel == None: all configured channels)"""
        self._set_gbt_tx_mux(GbtxTxMuxMode.TRIGGER, channel)

    def _set_gbt_tx_mux(self, sel, channel=None):
        """Select the downlink data source of channel to the RU (channel == None: all configured channels).
        """
        if channel is None:
            sel = GbtxTxMuxMode(sel)
            for entry in self.gbt.links:
                index, _, _, _, _ = entry
                reg = (index // 8)  # 4 bit per link, 8 links per reg
                bit_offset = (index % 8) * 4
                self.roc_rmw(cru_table.CRUADD['add_bsp_info_usertxsel'] + reg * 4, bit_offset, 4, sel)
        else:
            assert channel < len(self.gbt.links), "Channel must be < {}".format(len(self.gbt.links))
            index, _, _, _, _ = self.gbt.links[channel]
            reg = (index // 8)  # 4 bit per link, 8 links per reg
            bit_offset = (index % 8) * 4
            self.roc_rmw(cru_table.CRUADD['add_bsp_info_usertxsel'] + reg * 4, bit_offset, 4, sel)

    def get_gbt_tx_mux(self, channel):
        """Read the setting of the GBT TX MUX"""
        _, _, bank, link, _ = self.gbt.links[channel]
        txsel = (self.roc_read(cru_table.CRUADD['add_bsp_info_usertxsel'] + link * 4) >> (bank * 4)) & 0xf
        return txsel

    def get_gbt_tx_mux_all(self):
        """ Gets TX GBT mux state for each link """
        muxes = []
        self.gbt.set_links(self._swt_link_list + self._trigger_link_list)
        for entry in self.gbt.links:
            index, wrapper, bank, link, _ = entry
            txsel = (self.roc_read(cru_table.CRUADD['add_bsp_info_usertxsel'] + link * 4) >> bank * 4) & 0xf
            mux = GbtxTxMuxMode(txsel).name
            if (self.roc_read(self.gbt.get_rx_ctrl_address(wrapper, bank, link)) >> 16) & 0x1 == 1:
                mux += ":SHORTCUT"
            muxes.append((index, mux))
        return muxes

    def initialize_downlinks(self):
        """Initializes trigger and swt"""
        if self._trigger_link_list != []:
            self.gbt.set_links(self._trigger_link_list)
            self.set_gbt_mux_to_trigger()
        self.gbt.set_links(self._swt_link_list)
        self.set_gbt_mux_to_swt()

    # Triggering

    def send_soc(self):
        """Sends a Start Of Continuous trigger.
        Additionally automatically sets the GbtxTxMux"""
        if self._shared_trigger_link:
            self.gbt.set_links(self._swt_link_list)
            self.set_gbt_mux_to_trigger()
        self.ttc.send_soc()
        if self._shared_trigger_link:
            time.sleep(0.01)
            self.set_gbt_mux_to_swt()
            # restore initial link list
            self.gbt.set_links(self._all_links)

    def send_eoc(self):
        """Sends a End Of Continuous trigger.
        Additionally automatically sets the GbtxTxMux"""
        if self._shared_trigger_link:
            self.gbt.set_links(self._swt_link_list)
            self.set_gbt_mux_to_trigger()
        self.ttc.send_eoc()
        if self._shared_trigger_link:
            time.sleep(0.1)
            self.set_gbt_mux_to_swt()
            # restore initial link list
            self.gbt.set_links(self._all_links)

    def send_sot(self, periodic_triggers=False):
        """Sends a Start Of Triggered trigger.
        Additionally automatically sets the GbtxTxMux"""
        if self._shared_trigger_link:
            self.gbt.set_links(self._swt_link_list)
            self.set_gbt_mux_to_trigger()
        self.ttc.send_sot(periodic_triggers)
        if self._shared_trigger_link:
            time.sleep(0.01)
            self.set_gbt_mux_to_swt()
            # restore initial link list
            self.gbt.set_links(self._all_links)

    def send_eot(self):
        """Sends a End Of Triggered trigger.
        Additionally automatically sets the GbtxTxMux"""
        if self._shared_trigger_link:
            self.gbt.set_links(self._swt_link_list)
            self.set_gbt_mux_to_trigger()
        self.ttc.send_eot()
        if self._shared_trigger_link:
            time.sleep(0.1)
            self.set_gbt_mux_to_swt()
            # restore initial link list
            self.gbt.set_links(self._all_links)

    def send_physics_trigger(self):
        """Sends one physics trigger.
        Automatically handles the GbtxTxMux"""
        if self._shared_trigger_link:
            self.gbt.set_links(self._swt_link_list)
            self.set_gbt_mux_to_trigger()
        self.ttc.send_physics_trigger()
        if self._shared_trigger_link:
            time.sleep(0.01)
            self.set_gbt_mux_to_swt()
            # restore initial link list
            self.gbt.set_links(self._all_links)

    def send_start_of_triggered(self):
        self.send_sot()

    def send_end_of_triggered(self):
        self.send_eot()

    def send_trigger(self):
        self.send_physics_trigger()

    def wait(self, value):
        time.sleep(value * 6.25e-9)

    def set_prev_swt_cntr(self, cntr_val):
        """store cntr_val as the previous SWT counter value for use by  the class"""
        self._prev_swt_cntr = cntr_val


    def get_optical_power(self):
        """
        Return a list of optical powers of all found RX links.
        Adapted from:
        https://github.com/AliceO2Group/ReadoutCard/blob/master/src/Cru/I2c.cxx
        """
        if self.minipod_list == []:
            self._init_minipods()

        optical_powers_all = []
        for chip_addr in self._minipod_addresses:
            minipod = cru_i2c.CruI2c(pcie_opened_roc=self._roc,
                                     pcie_id=self._pcie_id,
                                     base_add=cru_table.CRUADD['add_bsp_i2c_minipods'],
                                     chip_add=chip_addr)
            minipod.reset_i2c()
            m_type = minipod.read_i2c(177)
            # check that it is RX, otherwise continue
            if m_type != 50:
                continue

            optical_powers = []
            # read the reg values and apply the necessary function for optical power
            for reg_address in range(64, 88, 2):
                reg0 = minipod.read_i2c(reg_address)
                reg1 = minipod.read_i2c(reg_address + 1)
                optical_power = (((reg0 << 8) + reg1) * 0.1)
                optical_powers.append(optical_power)
            # the links are reversed in this list:
            optical_powers.reverse()
            optical_powers_all += optical_powers

        return optical_powers_all

    def log_optical_power(self):
        """print the optical powers of all found links"""
        optical_powers = self.get_optical_power()
        self.logger.info("Optical Power of all found links:")
        for i in range(len(optical_powers)):
            self.logger.info(f"Link {i:2d}: {optical_powers[i]:5.1f} uW")

    def get_minipod_addresses(self):
        """returns a list with all the available minipod chip I2C addresses"""
        chip_found = []
        scan = cru_i2c.CruI2c(pcie_opened_roc=self._roc,
                              pcie_id=self._pcie_id,
                              base_add=cru_table.CRUADD['add_bsp_i2c_minipods'],
                              chip_add=0x0)
        for addr in range(scan.start_chip_add, scan.end_chip_add + 1):
            scan.reset_i2c()
            val_32 = (addr << 16) | 0x0
            scan.roc_write(scan.i2c_cfg, int(val_32))

            scan.roc_write(scan.i2c_cmd, 0x4)
            scan.roc_write(scan.i2c_cmd, 0x0)

            scan.wait_i2c_ready()

            val = scan.roc_read(scan.i2c_dat)
            if val >> 31 == 0x1:
                chip_found.append(addr)

        return chip_found

    def start_gbt_loopback_test(self):
        self.gbt.txmode("gbt")
        self.gbt.rxmode("gbt")
        self.gbt.patternmode("counter")
        self.gbt.txcountertype("8bit")
        self.gbt.internal_data_generator(1)
        self.gbt.cntrst()
        self.logger.info("GBT Loopback setup, internal data generator started")

    def stop_gbt_loopback_test(self):
        self.gbt.internal_data_generator(0)
        self.logger.info("Internal data generator stopped")
