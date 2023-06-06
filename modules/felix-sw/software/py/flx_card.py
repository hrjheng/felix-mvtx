"""MVTX FELIX Card implementation"""

import logging
import time
import os
import traceback
import inspect

from enum import IntEnum, unique
from timeout_decorator import timeout

import libO2Lla

from sca_flx import Sca_flx
import proasic3
import gbtx
import git_hash_lut

from flx_roc import Roc

import flx_table
import flx_bsp
import flx_gbt
import flx_ttc

# Constants
MAX_CHANNELS = 24


@unique
class GbtxTxMuxMode(IntEnum):
    """Enum defining the operating mode of the gbtx multiplexer.
    The multiplexer controls the downlink to the RU.
    """
    SWT            = 0
    TRIGGER        = 1


class FlxCard (Roc):
    """
    Implementation of the MVTX FELIX card
    several functions imported from equivalent class in ALICE CRU
    """
    def __init__(self, card_id=0,
                 lock_mask=0,
                 swt_link_list=[],
                 trigger_link_list=[],
                 data_link_list=[],
                 implicit_locking=True):

        Roc.__init__(self)
        self.logger  = logging.getLogger("MVTX FELIX")
        self._card_id=card_id
        self.open_card(card_id, lock_mask)

        self.bsp = flx_bsp.FlxBsp(flx_opened_roc=self._roc)

        self.gbt = flx_gbt.FlxGbt(flx_opened_roc=self._roc, ch_range="0")
        self.ttc = flx_ttc.FlxTtc(flx_opened_roc=self._roc)

        self._selected_gbt_channel = None

        self._assign_link_lists(swt_link_list=swt_link_list,
                                data_link_list=data_link_list,
                                trigger_link_list=trigger_link_list)

        self.gbt.set_links(self._all_links)

        self._prev_swt_cntr = None

        ### LLA
        self._implicit_lla = implicit_locking
        self._lla_last_break = time.time()
        self._lla_lock_count = 0
        self._lla_session = None
        if self._implicit_lla:
            self._lla_session = libO2Lla.Session(f"CRU_ITS_{os.getpid()}", f"{self._card_id:03}")
        self._lla_is_locked = False

    def set_implicit_lla(self, active=True):
        assert active in [True, False]
        self._implicit_lla = active

    def get_implicit_lla(self):
        return self._implicit_lla

    def _lock_comm(self):
        if self._implicit_lla:
            if not self._lla_is_locked:
                lock_attempt_counter = 0
                while (not self._lla_is_locked):
                    lock_attempt_counter += 1
                    locking_issue = not self._lla_session.start()
                    if locking_issue:
                        if 500 < lock_attempt_counter < 510:
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

    def git_hash(self):
        return self.bsp.get_short_hash()

    def git_tag(self, git_hash=None):
        if git_hash is None:
            return git_hash_lut.get_cru_version(self.bsp.get_short_hash())
        else:
            return git_hash_lut.get_cru_version(git_hash)

    def version(self):
        self.logger.info(f"CRU Version:\t0x{self.git_hash():08X}\t{self.git_tag()}")

    def version_formatted(self, as_git_hash=True, git_hash=None):
        """Returns the git hash of the commit if available"""
        if as_git_hash:
            return self.bsp.get_short_hash()
        if git_hash is None:
            return git_hash_lut.get_cru_version(self.bsp.get_short_hash())
        return git_hash_lut.get_cru_version(git_hash)

    def compare_expected_githash(self, expected_githash):
        actual_githash = self.bsp.get_short_hash()
        return expected_githash == actual_githash

    def check_git_hash_and_date(self, expected_githash):
        actual_githash = self.bsp.get_short_hash()
        assert actual_githash==expected_githash, f"Expected 0x{expected_githash:08X}, got 0x{actual_githash:08X}"

    # def id(self):
    #     """Returns the board id"""
    #     id = self.bsp.get_chip_id()
    #     return id[1]<<32|id[0]

    # def get_pcie_id(self):
    #     return self._pcie_id

    def date(self):
        """Returns the build date"""
        return hex(self.bsp.get_build_date())

    def set_gbt_channel(self, gbt_channel=0):
        """Selects the GBT_CH where the RU is connected to"""
        assert gbt_channel in self._swt_link_list, f"{gbt_channel} not in {self._swt_link_list}"
        self._selected_gbt_channel = gbt_channel
        add = flx_table.FLXADD['add_gbt_sc_link']
        self.roc_write(add, gbt_channel)

    def get_gbt_channel(self):
        """Returns the GBT CH where the RU is connected to"""
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
        """Resets the FIFOs used for the SWTs"""
        add = flx_table.FLXADD['add_gbt_sc_rst']
        self._lock_comm()
        try:
            self.roc_write(add, 1)
            self.roc_write(add, 0)
            self.set_prev_swt_cntr(None)
        finally:
            self._unlock_comm()

    def force_swt_counter_update(self):
        self.set_prev_swt_cntr(None)

    def get_swt_flow_monitor_counters(self):
        """Gets the numner of SWT transmitted and received"""
        add = flx_table.FLXADD['add_gbt_swt_mon']
        value = self.roc_read(add)
        in_swt = value & 0xFFF
        out_swt = (value>>12) & 0xFFF
        self.logger.info(f"written {out_swt}, read {in_swt}")
        return out_swt, in_swt

    @timeout(5, exception_message="FELIX not coming up, is the RU powered on or connected?")
    def initialize(self, gbt_ch=None):
        """Initializes the FELIX, selecting the RU on the GBT_CH selected.
        Sets also the GBT downlink multiplexer to SWT"""
        if gbt_ch is None:
            gbt_ch = self._swt_link_list[0]
        elif gbt_ch == -1:
            raise RuntimeError("GBT channel cannot be -1. Please use an rdo with a defined gbt_channel")
        #self.reset_flx()
        self.reset_sc_core(gbt_ch)
        self.bsp.initialize()
        #self.dwrapper.initialize(self._data_link_list)
        self.gbt.initialize()
        #self.ttc.initialize()
        self.initialize_downlinks()
        #self.dwrapper.set_data_link_list(self._data_link_list)

    def set_prev_swt_cntr(self, cntr_val):
        """store cntr_val as the previous SWT counter value for use by  the class"""
        self._prev_swt_cntr = cntr_val

    def get_prev_swt_cntr(self):
        """return the previous SWT counter value"""
        return self._prev_swt_cntr

    # Tx Mux

    def set_gbt_mux_to_swt(self, channel=None):
        """Set transmission of channel to SWT in downlink to the RU (channel == None: all configured channels)"""
        self._set_gbt_tx_mux(GbtxTxMuxMode.SWT, channel)

    def set_gbt_mux_to_trigger(self, channel=None):
        """Set transmission of channel to Trigger in downlink to the RU (channel == None: all configured channels)"""
        self._set_gbt_tx_mux(GbtxTxMuxMode.TRIGGER, channel)

    def _set_gbt_tx_mux(self, sel, channel=None):
        """Select the downlink data source of channel to the RU (channel == None: all configured channels).
        """
        if channel is None:
            sel = GbtxTxMuxMode(sel)
            for entry in self.gbt.links:
                _, link = entry
                self.roc_rmw(flx_table.FLXADD['add_gbt_trg_swt_mux'], link, 1, sel)
        else:
            assert channel < len(self.gbt.links), "Channel must be < {}".format(len(self.gbt.links))
            _, link = self.gbt.links[channel]
            self.roc_rmw(flx_table.FLXADD['add_gbt_trg_swt_mux'], link, 1, sel)

    def get_gbt_tx_mux(self, channel):
        """Read the setting of the GBT TX MUX"""
        _, link = self.gbt.links[channel]
        txsel = (self.roc_read(flx_table.FLXADD['add_gbt_trg_swt_mux']) >> link) & 0x1
        return txsel

    #def get_gbt_tx_mux_all(self):
    #    """ Gets TX GBT mux state for each link """
    #    muxes = []
    #    self.gbt.set_links(self._swt_link_list + self._trigger_link_list)
    #    for entry in self.gbt.links:
    #        index, wrapper, bank, link, _ = entry
    #        txsel = (self.roc_read(cru_table.CRUADD['add_bsp_info_usertxsel'] + bank * 4) >> link * 4) & 0x3
    #        mux = GbtxTxMuxMode(txsel).name
    #        if (self.roc_read(self.gbt.get_rx_ctrl_address(wrapper, bank, link)) >> 16) & 0x1 == 1:
    #            mux += ":SHORTCUT"
    #        muxes.append((index, mux))
    #    return muxes

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
        """
        self.ttc.send_soc()

    def send_eoc(self):
        """Sends a End Of Continuous trigger.
        """
        self.ttc.send_eoc()

    def send_sot(self, periodic_triggers=False):
        """Sends a Start Of Triggered trigger.
        """
        self.ttc.send_sot(periodic_triggers)

    def send_eot(self):
        """Sends a End Of Triggered trigger.
        """
        self.ttc.send_eot()

    def send_physics_trigger(self):
        """Sends one physics trigger.
        """
        self.ttc.send_physics_trigger()

    def send_start_of_triggered(self):
        self.send_sot()

    def send_end_of_triggered(self):
        self.send_eot()

    def send_trigger(self):
        self.send_physics_trigger()
