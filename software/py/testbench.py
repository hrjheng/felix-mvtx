#!/usr/bin/env python3.9
"""Generic Testbench for testing different routines and interactive access to RU modules"""

from enum import IntEnum, unique
from itertools import starmap
import itertools,operator
from timeout_decorator.timeout_decorator import TimeoutError

import collections
import collections.abc
import errno
import fire
import imageio
import json
import logging
import numpy as np
import os
import pprint
import random
import select
import sys
import time
import traceback
import warnings
import yaml
import re
import threading
import warnings

if False:
    print(f"A syntax error here indicates the program was started with Python 2 instead of 3, did you remember to first run \'module load ReadoutCard/vX.YY.Z-1\' ?")


# Static configuration parameters
class CruType(IntEnum):
    O2   = 0
    RUv0 = 1
    FLX  = 2
    NONE = 3

#################
# Configuration #
#################

# If True uses the usb_comm to connect to the RDO/CRU_emulator
USE_USB_COMM = False
# If True runs as standalone
STANDALONE_RUN = False
CANBUS_HW_IF = "vcan0" # see modules/dcs_canbus/software/can_hlp/SocketCANGateway/README.md for setting up the interface
# Githash of CRU emulator
EXPECTED_RUV0_CRU_GITHASH : 0x06C85C35
# USB serial for communicating with the RU via USB
USB_SERIAL_RDO = "000000"
# USB serial for communicating with the RUv0 via USB
USB_SERIAL_RUv0_CRU = "000001"
# Regular expression string to identify subracks in 167
SUBRACK_REGEX = r"^L[0-6][B,T][I,O]{0,1}\-PP1\-[I,O]-[0-7].*"

########################
# End of Configuration #
########################

script_path = os.path.dirname(os.path.realpath(__file__))
modules_path = os.path.join(script_path, '../../modules/board_support_software/software/py/')
sys.path.append(modules_path)
from module_includes import *

from chip import ModeControlChipModeSelector
from communication import WishboneReadError
from pALPIDE import Alpide, Opcode, ModeControlIbSerialLinkSpeed, AdcIndex, CommandRegisterOpcode
from proasic3 import Pa3Register
from proasic3_enums import CcCmdOpcode, FlashSelectICOpcode
from ws_gbt_prbs_chk import PrbsMode
from proasic3_convenience import ScrubbingStuckOn, DoubleBitError

import communication
import cru_board
import cru_swt_communication
import flx_card
import flx_swt_communication
import events
import gbt_sca
import logbook
import ltu
import power_unit
import ru_board
import ru_eyescan
import ru_transition_board
import usb_communication
import ws_identity
import ws_i2c_gbtx
import crate_mapping
import power_cable_mapping
import ws_can_hlp
from can_hlp_comm import CanHlpComm


@unique
class SensorMatrixPattern(IntEnum):
    """Sensor matrix patterns for masking/pulsing"""
    EMPTY                 = 0
    EMPTY_DOUBLE_COLUMNS  = 1
    IMAGE                 = 2
    ROW                   = 3
    PIXEL                 = 4
    TWO_PIXELS_PER_REGION = 5
    MAX_100KHZ_1GBTX      = 6
    MAX_100KHZ_3GBTX      = 7
    MAX_100KHZ_1GBTX_OB   = 8
    ONE_PIXEL             = 9
    ALL_PIXELS            = 10
    FRACTION              = 11
    ALL_BUT_UNPULSED      = 12

@unique
class LayerList(IntEnum):
    """List of layers, INNER, MIDDLE or OUTER"""
    INNER    = 0
    MIDDLE   = 1
    OUTER    = 2
    NO_PT100 = 3


def heardKeypress():
    i,o,e = select.select([sys.stdin],[],[],0.0001)
    for s in i:
        if s == sys.stdin:
            in_val = sys.stdin.readline()
            return in_val.strip()
    return None


poweroff_sequence = [
        0xa3010000,
        0xa3020000,
        0x861600ff,
        0x86060000,
        0x86060100,
        0x86060200,
        0x86060300,
        0x86070000,
        0x86070100,
        0x86070200,
        0x86070300,
        0x86080000,
        0x86080100,
        0x86080200,
        0x86080300,
        0x86090000,
        0x86090100,
        0x86090200,
        0x86090300,
        0x860a1100,
        0x8600003f,
        0x86020000,
        0x86030000,
        0x86040000,
        0x86050000
]

disablepower_sequence = [
        0xa3010000,
        0xa3020000
]

disablebias_sequence = [
        0x861600ff
]

set_power_voltage_all_sequence = [
        0x86060000,
        0x86060100,
        0x86060200,
        0x86060300,
        0x86070000,
        0x86070100,
        0x86070200,
        0x86070300,
        0x86080000,
        0x86080100,
        0x86080200,
        0x86080300,
        0x86090000,
        0x86090100,
        0x86090200,
        0x86090300
]

set_bias_voltage_all_sequence = [
        0x860a1100
]

lower_current_threshold_sequence = [
        0x8600003f,
        0x86020000,
        0x86030000,
        0x86040000,
        0x86050000
]

monitor_sequence = [
        0x25000000,
        0x25030000,
        0x25010000,
        0x25040000,
        0x25020000,
        0x25050000,
        0x86100020,
        0x86180000,
        0x06200000,
        0x06200000,
        0x06210000,
        0x86100021,
        0x86180000,
        0x06200000,
        0x06210000,
        0x86100022,
        0x86180000,
        0x06200000,
        0x06210000,
        0x86100023,
        0x86180000,
        0x06200000,
        0x06210000,
        0x86100024,
        0x86180000,
        0x06200000,
        0x06210000,
        0x86100025,
        0x86180000,
        0x06200000,
        0x06210000,
        0x86100026,
        0x86180000,
        0x06200000,
        0x06210000,
        0x86100027,
        0x86180000,
        0x06200000,
        0x06210000,
        0x86110020,
        0x86190000,
        0x06200000,
        0x06210000,
        0x86110021,
        0x86190000,
        0x06200000,
        0x06210000,
        0x86110022,
        0x86190000,
        0x06200000,
        0x06210000,
        0x86110023,
        0x86190000,
        0x06200000,
        0x06210000,
        0x86110024,
        0x86190000,
        0x06200000,
        0x06210000,
        0x86110025,
        0x86190000,
        0x06200000,
        0x06210000,
        0x86110026,
        0x86190000,
        0x06200000,
        0x06210000,
        0x86110027,
        0x86190000,
        0x06200000,
        0x06210000,
        0x86120020,
        0x861a0000,
        0x06200000,
        0x06210000,
        0x86120021,
        0x861a0000,
        0x06200000,
        0x06210000,
        0x86120022,
        0x861a0000,
        0x06200000,
        0x06210000,
        0x86120023,
        0x861a0000,
        0x06200000,
        0x06210000,
        0x86120024,
        0x861a0000,
        0x06200000,
        0x06210000,
        0x86120025,
        0x861a0000,
        0x06200000,
        0x06210000,
        0x86120026,
        0x861a0000,
        0x06200000,
        0x06210000,
        0x86120027,
        0x861a0000,
        0x06200000,
        0x06210000,
        0x86130020,
        0x861b0000,
        0x06200000,
        0x06210000,
        0x86130021,
        0x861b0000,
        0x06200000,
        0x06210000,
        0x86130022,
        0x861b0000,
        0x06200000,
        0x06210000,
        0x86130023,
        0x861b0000,
        0x06200000,
        0x06210000,
        0x86130024,
        0x861b0000,
        0x06200000,
        0x06210000,
        0x86130025,
        0x861b0000,
        0x06200000,
        0x06210000,
        0x86130026,
        0x861b0000,
        0x06200000,
        0x06210000,
        0x86130027,
        0x861b0000,
        0x06200000,
        0x06210000
]


class Testbench(object):
    """Testbench for executing different tests"""
    logbook=None
    lol_cntr=None

    def __init__(self,
                 cru_sn,
                 check_cru_hash,
                 expected_cru_githash,
                 ru_main_revision, ru_minor_revision,
                 ctrl_and_data_link_list,
                 only_data_link_list,
                 trigger_link_list,
                 ru_transition_board_version,
                 power_board_version,
                 power_board_filter_50hz_ac_power_mains_frequency,
                 powerunit_resistance_offset_pt100,
                 layer,
                 ltu_hostname,
                 subrack,
                 use_usb_comm=USE_USB_COMM,
                 use_rdo_usb=False,
                 cru_type=CruType.O2,
                 use_can_comm=False,
                 run_standalone=False):
        # setup comms
        self.logger = logging.getLogger("Testbench")
        self.serv_ruv0_cru = None
        self.serv_rdo = None
        self.comm_ruv0_cru = None
        self.comm_rdo = None
        self.cru = None
        self.rdo = None
        self.ltu = None

        self.rdo_list = []
        self.comm_rdo_list = []
        self.stave_list = []
        self.stave_ob_dict = {}
        self.stave_ob_lower_dict = {}
        self.stave_ob_upper_dict = {}
        self.stave_ml_dict = {}
        self.stave_ml_lower_dict = {}
        self.stave_ml_upper_dict = {}
        self.chip_broadcast_dict = {}
        self._cable_resistance = {}

        self.use_can_comm = use_can_comm
        self.use_usb_comm = use_usb_comm
        self.use_rdo_usb = use_rdo_usb
        self.cru_type = cru_type
        if (self.cru_type is CruType.NONE) and not (self.use_rdo_usb or self.use_can_comm):
            raise ValueError("Config error: No configured interface to RU, CRU can't be CruType.NONE while USE_RDO_USB and USE_CAN_COMM are both false")

        self._chipids_ib = list(range(9))
        self.chips = []
        self.chip_broadcast = None

        # chipids in b0/a8. 7 chips per module, 7 modules from 1 to 7
        self._chipids_ob_b0 = [list(range(0+16*module,0+16*module+7)) for module in range(1,8)]
        self._chipids_ob_b0 = [i for ls in self._chipids_ob_b0 for i in ls]
        self._chipids_ob_a8 = [list(range(8+16*module,8+16*module+7)) for module in range(1,8)]
        self._chipids_ob_a8 = [i for ls in self._chipids_ob_a8 for i in ls]
        self.chips_ob_lower = {} # OB HS Lower
        self.chips_ob_upper = {} # OB HS Upper
        self.chips_ob = {}

        # chipids in b0/a8. 7 chips per module, 4 modules from 1 to 4
        self._chipids_ml_b0 = [list(range(0+16*module,0+16*module+7)) for module in range(1,5)]
        self._chipids_ml_b0 = [i for ls in self._chipids_ml_b0 for i in ls]
        self._chipids_ml_a8 = [list(range(8+16*module,8+16*module+7)) for module in range(1,5)]
        self._chipids_ml_a8 = [i for ls in self._chipids_ml_a8 for i in ls]
        self.chips_ml_lower = {} # ML HS Lower
        self.chips_ml_upper = {} # ML HS Upper
        self.chips_ml = {}

        self.cru_sn = None
        self.set_cru_sn(cru_sn)
        self.check_cru_hash = check_cru_hash
        self.expected_cru_githash = expected_cru_githash

        self.ctrl_link_list = None
        self.data_link_list = None
        self.trigger_link_list = None
        self.set_links_list(ctrl_and_data_link_list=ctrl_and_data_link_list,
                            only_data_link_list=only_data_link_list,
                            trigger_link_list=trigger_link_list)

        self.ltu_hostname = ltu_hostname

        assert ru_main_revision is not None
        assert ru_minor_revision is not None
        assert ru_transition_board_version is not None
        self.ru_main_revision = ru_main_revision
        self.ru_minor_revision = ru_minor_revision
        self.ru_transition_board_version = ru_transition_board_version

        assert power_board_filter_50hz_ac_power_mains_frequency is not None
        assert power_board_version is not None
        self.power_board_version = power_board_version
        self.power_board_filter_50hz_ac_power_mains_frequency = power_board_filter_50hz_ac_power_mains_frequency

        assert powerunit_resistance_offset_pt100 is not None
        self.powerunit_resistance_offset_pt100 = powerunit_resistance_offset_pt100
        self._pu_calibration_fpath = os.path.join(script_path, "../config/pu_calibration.json")
        self._pu_calibration = None

        self.layer = layer

        self.subrack = subrack

        if run_standalone:
            self.setup_standalone()

    def raw_poweroff(self,index,delay):
        self.raw_execute(index,poweroff_sequence,delay)

    def raw_disable_power(self,index):
        self.raw_execute(index,disablepower_sequence)

    def raw_disable_bias(self,index,delay):
        new_seq = disablebias_sequence
        self.raw_execute(index,new_seq,delay)

    def raw_set_power_voltage(self,index):
        self.raw_execute(index,set_power_voltage_all_sequence)

    def raw_set_bias_voltage(self,index):
        self.raw_execute(index,set_bias_voltage_all_sequence)

    def raw_lower_current(self,index):
        self.raw_execute(index,lower_current_threshold_sequence)

    def raw_execute(self,index,sequence,delay=0):
        assert(index<=len(sequence))
        self.rdo.powerunit_1.reset_all_counters()
        self.rdo.powerunit_1.reset_all_fifos()
        time.sleep(0.5)
        offset = 0
        if index>0 and delay>0:
            sequence.insert(index,0x8a000000 | (delay & 0xFFFF))
            offset = 1
        sequence.insert(index+offset,0x86000101)
        sequence.insert(index+1+offset,0x8617ffff)
        sequence.insert(index+2+offset,0x861f0000)
        if index<len(sequence) and delay>0:
            sequence.insert(index+3+offset,0x8a000000 | (delay & 0xFFFF))
        self.rdo.comm.raw_sequence(sequence)
        time.sleep(1.0)
        empty = self.rdo.powerunit_1.read(32)
        if empty == 1:
            self.logger.info("nothing in FIFO")
        while empty != 1:
            self.logger.info(hex(self.rdo.powerunit_1.read(33)))
            empty = self.rdo.powerunit_1.read(32)
        self.logger.info(self.rdo.powerunit_1.read_counters())

    def raw_monitor(self):
        self.rdo.comm.raw_sequence(monitor_sequence)

    def set_cru_sn(self, cru_sn):
        """Sets the CRU_SN attribute of the testbench"""
        self.cru_sn = cru_sn

    def set_links_list(self,
                       ctrl_and_data_link_list,
                       only_data_link_list,
                       trigger_link_list):
        """Sets the links_list of the testbench

        ctrl_and_data_link_list: list of CRU channels used for control and data,
                                 i.e. connected to the GBTx0 of the RU
        only_data_link_list:     list of CRU channels used for data only,
                                 i.e. connected to the GBTx1 or GBTx2 of the RU
        trigger_link_list:       list of CRU channels used for trigger
                                 i.e. connected to the GBTx2 of the RU in downlink
        """
        assert len(list(set(ctrl_and_data_link_list))) == len(ctrl_and_data_link_list), "repeated values in links list: {0}".format(ctrl_and_data_link_list)
        assert len(list(set(ctrl_and_data_link_list+only_data_link_list))) == len(only_data_link_list+ctrl_and_data_link_list), "repeated values in links list: {0}, {1}".format(ctrl_and_data_link_list, only_data_link_list)
        assert len(list(set(trigger_link_list))) == len(trigger_link_list), "repeated values in links list: {} {}".format(trigger_link_list, set(trigger_link_list))

        MAX_CRU_CHANNELS = cru_board.MAX_CHANNELS
        assert set(ctrl_and_data_link_list).issubset(set(range(MAX_CRU_CHANNELS)))
        assert set(only_data_link_list).issubset(set(range(MAX_CRU_CHANNELS)))
        assert set(trigger_link_list).issubset(set(range(MAX_CRU_CHANNELS)))

        self.ctrl_link_list = ctrl_and_data_link_list
        self.data_link_list = ctrl_and_data_link_list + only_data_link_list
        self.trigger_link_list = trigger_link_list
        self.logger.debug(f"CTRL_LINK_LIST {self.ctrl_link_list}")
        self.logger.debug(f"DATA_LINK_LIST {self.data_link_list}")
        self.logger.debug(f"TRIGGER_LINK_LIST {self.trigger_link_list}")

    def tg_notification(self, message):
        self.logger.debug("sending message to tg: \"{0}\"".format(message))
        os.system('telegram-send "{0}"'.format(message))

    def monitor(self, rdo=None, is_powerunit_2_used=False):
        """Monitors the current, voltages and temperatures on the RU"""
        if rdo is None:
            rdo_list = self.rdo_list
        else:
            rdo_list = [self.rdo_list[rdo]]
        self.cru.initialize()
        for rdo in rdo_list:
            self.logger.info(f"RU {rdo.get_gbt_channel()}")
            rdo.sca.log_adcs()
            rdo.sysmon.log_temperature()
            rdo.powerunit_1.initialize()
            rdo.powerunit_1.log_temperatures()
            if is_powerunit_2_used:
                rdo.powerunit_2.initialize()
                rdo.powerunit_2.log_temperatures()

    def get_all_xcku_temperatures(self):
        """ Returns all RDO temperatures """
        ret_dict = {}
        for i,rdo in enumerate(self.rdo_list):
            rdo_temperature = rdo.sysmon.get_temperature()
            ret_dict[i] = rdo_temperature
        return ret_dict

    def log_all_xcku_temperatures(self):
        """Logs the output from get_all_lol_counters"""
        ret_dict = self.get_all_xcku_temperatures()
        for rdo, temp in ret_dict.items():
            self.logger.info(f"RDO {(self.rdo_list[rdo]).get_gbt_channel():2}: {temp:.2f} C")

    def log_all_pu_internal_temperature(self):
        """Logs all powerunit internal temperatures"""
        for rdo in self.rdo_list:
            temp = rdo.powerunit_1.read_temperature(0)
            self.logger.info(f"RDO {rdo.get_gbt_channel():2}: PU internal temperature = {temp:.2f}")

    def log_all_trigger_rates(self):
        for rdo in self.rdo_list:
            rate = rdo.format_trigger_rates()
            self.logger.info(f"RDO {rdo.get_gbt_channel():2} - {rate}")

    def log_all_timebase_lols(self):
        for rdo in self.rdo_list:
            lol = rdo._trigger_handler_monitor.read_counters()['LOL_TIMEBASE']
            self.logger.info(f"RDO {rdo.get_gbt_channel():2} - {lol}")

    def log_fec_lol_1v5(self, rdo=None):
        if rdo is None:
            rdo = self.rdo
        else:
            rdo = self.rdo_list[rdo]
        lol = 0x1 if rdo.clock_health_status.is_any_clk_event_flags_set() else 0x0
        rdo.clock_health_status.reset_clock_health_flags()
        self.logger.info(f"RDO {rdo.get_gbt_channel():2} - LOL: {lol}")
        fec = rdo.gbtx0_swt.getreg_fec()
        self.logger.info(f"RDO {rdo.get_gbt_channel():2} - FEC: {fec}")
        i_1v5 = round(rdo.sca.read_adc_converted("I_1V5"), 3)
        v_1v5 = round(rdo.sca.read_adc_converted("V_1V5"), 3)
        self.logger.info(f"RDO {rdo.get_gbt_channel():2} - I_1V5: {i_1v5}")
        self.logger.info(f"RDO {rdo.get_gbt_channel():2} - V_1V5: {v_1v5}")

    def version(self):
        """Logs the FW versions of the CRU and the RU FPGAs"""
        if self.cru_type is not CruType.NONE:
            self.cru.version()
        for rdo in self.rdo_list:
            if self.cru_type is CruType.NONE:
                rdo.version(get_pa3=False)
            else:
                rdo.version(get_pa3=True)

    def dna(self):
        for rdo in self.rdo_list:
            rdo.dna()

    def feeid(self):
        """Returns the feeid of the boards"""
        for rdo in self.rdo_list:
            rdo.feeid()

    def temperature(self):
        """Logs the temperature of the boards"""
        for rdo in self.rdo_list:
            t = rdo.sysmon.get_temperature()
            self.logger.info(f"RDO {rdo.get_gbt_channel():2} Temperature {t:.2f} C")

    def gbtx0_charge_pump_settings(self):
        """Logs GBTx0 charge pump settings of the boards"""
        for rdo in self.rdo_list:
            cp = rdo.gbtx0_swt.get_phase_detector_charge_pump()
            self.logger.info(f"RDO {rdo.get_gbt_channel():2} GBTx0 charge pump setting: {cp}")

    def log_all_gbtx_status(self, verbose=False, pll_lock=False, lol_counters=False, fec=False, use_xcku=False):
        for rdo in self.rdo_list:
            if use_xcku:
                gbtxs = rdo.gbtxs_swt
            else:
                gbtxs = rdo.gbtxs_sca
            gbtx0 = gbtxs[0].get_pu_fsm_status()
            gbtx1 = gbtxs[1].get_pu_fsm_status()
            gbtx2 = gbtxs[2].get_pu_fsm_status()
            gbtx0_bool = str(gbtxs[0].is_gbtx_config_completed())
            gbtx1_bool = str(gbtxs[1].is_gbtx_config_completed())
            gbtx2_bool = str(gbtxs[2].is_gbtx_config_completed())
            self.logger.info(f"RDO {rdo.get_gbt_channel():2} GBTx Config Done/Status - GBTx0: {gbtx0_bool:<5}/ {gbtx0:<14} GBTx1: {gbtx1_bool:<5}/ {gbtx1:<14} GBTx2: {gbtx2_bool:<5}/ {gbtx2:<14}")
            gbtx0 = gbtxs[0].get_phase_detector_charge_pump()
            gbtx1 = gbtxs[1].get_phase_detector_charge_pump()
            gbtx2 = gbtxs[2].get_phase_detector_charge_pump()
            self.logger.info(f"RDO {rdo.get_gbt_channel():2} GBTx Charge Pump        - GBTx0: {gbtx0:<21} GBTx1: {gbtx1:<21} GBTx2: {gbtx2:<21}")
            if pll_lock or verbose:
                gbtx0 = str(gbtxs[0].is_tx_rx_pll_locked())
                gbtx1 = str(gbtxs[1].is_tx_rx_pll_locked())
                gbtx2 = str(gbtxs[2].is_tx_rx_pll_locked())
                self.logger.info(f"RDO {rdo.get_gbt_channel():2} GBTx TX/RX PLL Lock     - GBTx0: {gbtx0:<21} GBTx1: {gbtx1:<21} GBTx2: {gbtx2:<21}")
            if lol_counters or verbose:
                gbtx0 = gbtxs[0].getreg_rx_ref_pll_lol_cnt()
                gbtx1 = gbtxs[1].getreg_rx_ref_pll_lol_cnt()
                gbtx2 = gbtxs[2].getreg_rx_ref_pll_lol_cnt()
                self.logger.info(f"RDO {rdo.get_gbt_channel():2} GBTx RefPLL LOL Cnt     - GBTx0: {gbtx0:<21} GBTx1: {gbtx1:<21} GBTx2: {gbtx2:<21}")
                gbtx0 = gbtxs[0].getreg_rx_epll_lol_cnt()
                gbtx1 = gbtxs[1].getreg_rx_epll_lol_cnt()
                gbtx2 = gbtxs[2].getreg_rx_epll_lol_cnt()
                self.logger.info(f"RDO {rdo.get_gbt_channel():2} GBTx EPLL   LOL Cnt     - GBTx0: {gbtx0:<21} GBTx1: {gbtx1:<21} GBTx2: {gbtx2:<21}")
            if fec or verbose:
                gbtx0 = gbtxs[0].getreg_fec()
                gbtx1 = gbtxs[1].getreg_fec()
                gbtx2 = gbtxs[2].getreg_fec()
                self.logger.info(f"RDO {rdo.get_gbt_channel():2} GBTx FEC Correction     - GBTx0: {gbtx0:<21} GBTx1: {gbtx1:<21} GBTx2: {gbtx2:<21}")


    def uptime(self):
        """Returns the uptime of the Readout unit"""
        for rdo in self.rdo_list:
            rdo.uptime()

    def setup_standalone(self):
        self.setup_logging()
        self.setup_ltu()
        if self.cru_type in [CruType.O2, CruType.FLX]:
            self.setup_cru()
            self.setup_comms(gbt_channel=self.ctrl_link_list[0])
            self.setup_rdo()
            self.setup_stave()
            self.setup_rdos()
        elif self.cru_type is CruType.RUv0:
            self.setup_comms()
            self.setup_boards()
            self.setup_stave()
        elif self.cru_type is CruType.NONE:
            if self.use_can_comm:
                self._can_node_id_list = []
                for gbt_channel in self.ctrl_link_list:
                    s = self.get_stave_number(gbt_channel)
                    l = self.get_layer(gbt_channel)
                    self._can_node_id_list.append(ws_identity._encode_feeid(l, s))
                self.setup_comms()
                self.setup_rdo()
                self.setup_stave()
                self.setup_rdos()
            elif self.use_rdo_usb:
                self.setup_comms()
                self.setup_boards()
                self.setup_stave()
            else:
                raise NotImplementedError
        else:
            raise NotImplementedError

    def setup_logging(self):

        warnings.simplefilter("always")

        # Logging folder
        logdir = os.path.join(
            os.getcwd(),
            'logs/Testbench')
        try:
            os.makedirs(logdir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        # setup logging
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        log_file = os.path.join(logdir, "testbench.log")
        log_file_errors = os.path.join(logdir,
                                       "testbench_errors.log")

        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)

        fh2 = logging.FileHandler(log_file_errors)
        fh2.setLevel(logging.ERROR)

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        formatter = logging.Formatter("[%(asctime)s]    %(levelname)-10s %(name)-28s %(message)s")

        def fmt_filter(record):
            record.levelname = f"[{record.levelname}]"
            record.name = f"[{record.name}]"
            return True

        fh.setFormatter(formatter)
        fh2.setFormatter(formatter)
        ch.setFormatter(formatter)
        fh.addFilter(fmt_filter) # Adds filter on all handlers

        logger.addHandler(fh)
        logger.addHandler(fh2)
        logger.addHandler(ch)

    def setup_comms(self, cru_ctlOnly=False, gbt_channel=None):
        """Setup Communication interfaces for CRU and RDO"""
        if self.cru_type in [CruType.O2, CruType.FLX]:
            self.setup_comm_rdo(ctlOnly=cru_ctlOnly, gbt_channel=gbt_channel)
            self.setup_comms_rdo()
        elif self.cru_type is CruType.RUv0:
            self.setup_comm_ruv0_cru(ctlOnly=cru_ctlOnly)
            self.setup_comm_rdo(ctlOnly=cru_ctlOnly)
        elif self.cru_type is CruType.NONE:
            if self.use_can_comm:
                self.setup_comm_rdo()
                self.setup_comms_rdo()
            elif self.use_rdo_usb:
                self.setup_comm_rdo(ctlOnly=cru_ctlOnly)
            else:
                raise NotImplementedError
        else:
            raise NotImplementedError

    def setup_comm_ruv0_cru(self, ctlOnly=False):
        """Setup Communication interfaces for RUv0 CRU"""
        assert self.cru_type is CruType.RUv0, "CRU comm only needs to be set up on RUv0"
        if self.use_usb_comm:
            self.serv_ruv0_cru = usb_communication.UsbCommServer(
                serial=USB_SERIAL_RUv0_CRU)
            self.serv_ruv0_cru.start()
            time.sleep(0.1)
            comm = usb_communication.NetUsbComm(ctlOnly=ctlOnly, Timeout=0.5)
            comm.set_server(self.serv_ruv0_cru)
            comm = communication.PrefetchCommunication(comm)
            comm.enable_rderr_exception()
            time.sleep(0.2)
            self.logger.debug(self.serv_ruv0_cru.read_messages())
        else:
            comm = usb_communication.PyUsbComm(serialNr=USB_SERIAL_RUv0_CRU)
        self.comm_ruv0_cru = comm

    def setup_comm_rdo(self, ctlOnly=False, gbt_channel=None):
        """Setup Communication interfaces for RDO"""
        if self.use_can_comm:
            # Gets the logger instantiated into the canbus module and silence it by setting its
            # logger verobosity to WARNING
            can_logger = logging.getLogger('can.interfaces.socketcan.socketcan')
            can_logger.setLevel(logging.WARNING)  # disable INFO logger messages from can module
            self.comm_rdo = CanHlpComm(can_if=CANBUS_HW_IF, timeout_ms=5000, initial_node_id=self._can_node_id_list[0], sim=False)
        elif self.use_rdo_usb:
            if self.use_usb_comm:
                self.serv_rdo = usb_communication.UsbCommServer(
                    serial=USB_SERIAL_RDO)
                self.serv_rdo.start()
                time.sleep(0.1)
                comm = usb_communication.NetUsbComm(ctlOnly=ctlOnly, Timeout=0.5)
                comm.set_server(self.serv_rdo)
                comm = communication.PrefetchCommunication(comm)
                comm.enable_rderr_exception()
                time.sleep(0.2)
                self.logger.debug(self.serv_rdo.read_messages())
            else:
                self.comm_rdo = usb_communication.PyUsbComm(serialNr=USB_SERIAL_RDO)
        elif self.cru_type in [CruType.O2, CruType.FLX]:
            if isinstance(gbt_channel, (list, tuple, set)):
                gbt_channel = gbt_channel[0]
            if self.cru_type is CruType.O2:
                self.comm_rdo = cru_swt_communication.CruSwtCommunication(cru=self.cru,
                                                                          gbt_channel=gbt_channel)
            else:
                self.comm_rdo = flx_swt_communication.FlxSwtCommunication(flx=self.cru,
                                                                          gbt_channel=gbt_channel)
        elif self.cru_type is CruType.RUv0:
            self.comm_rdo = self.comm_ruv0_cru
        elif self.cru_type is CruType.NONE:
            pass
        else:
            raise NotImplementedError

    def setup_comms_rdo(self):
        """Setup Communication interfaces for multiple RDOs in the ctrl_link_list/can_node_id_list"""
        if self.cru_type is CruType.O2:
            for gbt_channel in self.ctrl_link_list:
                self.comm_rdo_list.append(cru_swt_communication.CruSwtCommunication(cru=self.cru, gbt_channel=gbt_channel))
                self.logger.debug(f"gbt_channel {gbt_channel}, comm_gbt_channel {self.comm_rdo_list[-1]._gbt_channel}")
            assert len(self.comm_rdo_list) == len(self.ctrl_link_list), \
                f"Not all the communication objects were correctly created.\n gbt_channel_link {self.ctrl_link_list}, comms {self.comm_rdo_list}"
        elif self.cru_type is CruType.FLX:
            for gbt_channel in self.ctrl_link_list:
                self.comm_rdo_list.append(flx_swt_communication.FlxSwtCommunication(flx=self.cru,
                                                                                    gbt_channel=gbt_channel))
                self.logger.debug(f"gbt_channel {gbt_channel}, comm_gbt_channel {self.comm_rdo_list[-1]._gbt_channel}")
            assert len(self.comm_rdo_list) == len(self.ctrl_link_list), \
                f"Not all the communication objects were correctly created.\n gbt_channel_link {self.ctrl_link_list}, comms {self.comm_rdo_list}"
        elif self.cru_type is CruType.NONE:
            if self.use_can_comm:
                can_logger = logging.getLogger('CANbus')
                can_logger.setLevel(logging.WARNING)  # disable INFO logger messages from can module
                for can_ch in self._can_node_id_list:
                    self.comm_rdo_list.append(CanHlpComm(can_if=CANBUS_HW_IF, timeout_ms=5000, initial_node_id=can_ch, sim=False, filter=True))
                assert len(self.comm_rdo_list) == len(self._can_node_id_list), "Not all the communication objects were correctly created.\n gbt_channel_link {0}, comms {1}".format(can_ch, self.comm_rdo_list)
            else:
                raise NotImplementedError
        else:
            raise NotImplementedError

    def force_unlock_lla(self):
        """
        Force the unlock of LLA. To be used if the software crashed while locking CRU comm.
        """
        self.cru._unlock_comm(force=True)

    def stop(self):
        if self.cru_type is CruType.RUv0:
            if self.comm_ruv0_cru is not None:
                self.comm_ruv0_cru.stop()
        if self.use_rdo_usb:
            if self.comm_rdo is not None:
                self.comm_rdo.stop()
        if self.serv_ruv0_cru:
            self.serv_ruv0_cru.stop()
        if self.serv_rdo:
            self.serv_rdo.stop()

    def setup_ltu(self):
        self.ltu = ltu.Ltu(hostname=self.ltu_hostname)

    def setup_cru(self):
        if self.cru_type is CruType.RUv0:
            self.cru = ru_board.RUv0_CRU(
                self.comm_ruv0_cru,
                sca_is_on_ruv1=(self.ru_main_revision==1),
                sca_is_on_ruv2_0=(self.ru_main_revision==2 and
                                  self.ru_minor_revision==0))
            assert self.cru.git_hash() == EXPECTED_RUV0_CRU_GITHASH, \
                f"Software incompatible with RUv0 CRU Firmware version with githash 0x{self.cru.git_hash():08X}"
        elif self.cru_type is CruType.O2:
            self.cru = cru_board.O2Cru(pcie_id=self.cru_sn,
                                       bar_ch=2,
                                       swt_link_list=self.ctrl_link_list,
                                       trigger_link_list=self.trigger_link_list,
                                       data_link_list=self.data_link_list)
            if self.check_cru_hash:
                assert self.cru.compare_expected_githash(self.expected_cru_githash), \
                f"Software incompatible with CRU Firmware version with githash 0x{self.cru.bsp.get_short_hash():08X}"
        elif self.cru_type is CruType.FLX:
            self.cru = flx_card.FlxCard(card_id=int(self.cru_sn),
                                        lock_mask=0,
                                        swt_link_list=self.ctrl_link_list,
                                        trigger_link_list=self.trigger_link_list,
                                        data_link_list=self.data_link_list)
        elif self.cru_type is CruType.NONE:
            self.cru = None
        else:
            raise NotImplementedError

    def get_stave_number(self, gbt_channel):
        stave_number = None
        if gbt_channel == -1:
            _, _, stave = self.rdo.identity.get_decoded_fee_id()
            stave_number = int(stave)
        else:
            if self.subrack is None:
                stave_number = None
            else:
                for entry in crate_mapping.subrack_lut[self.subrack]:
                    if entry[crate_mapping.Fields.gbt_channel] == gbt_channel:
                        stave_number = entry[crate_mapping.Fields.board_id_in_layer]
        return stave_number

    def get_layer(self, gbt_channel):
        layer = None
        if gbt_channel == -1:
            _, layer, _ = self.rdo.identity.get_decoded_fee_id()
            layer = int(layer)
        else:
            if self.subrack is None:
                layer = None
            else:
                for entry in crate_mapping.subrack_lut[self.subrack]:
                    if entry[crate_mapping.Fields.gbt_channel] == gbt_channel:
                        layer = entry[crate_mapping.Fields.layer]
        return layer

    def load_powerunit_offset_file(self):
        # read Miko's calibration file for the powerunit offset calibrations
        with open(self._pu_calibration_fpath) as f:
            self._pu_calibration = json.load(f)

    def get_powerunit_offsets(self, layer_number, stave_number):
        offsets = {1: {'avdd': None, 'dvdd': None}, 2: {'avdd': None, 'dvdd': None}}
        if layer_number is None or stave_number is None:
            return offsets

        ru_name = f"L{layer_number}_{stave_number:02}"

        if ru_name in self._pu_calibration.keys():
            offsets[1]['avdd'] = [int(o, 16) for o in self._pu_calibration[ru_name]['offset_avdd']]
            offsets[1]['dvdd'] = [int(o, 16) for o in self._pu_calibration[ru_name]['offset_dvdd']]

            if layer_number > 4:
                # OUTER LAYER should have 2 keys in the file pu_calibration.json
                ru_name2 = ru_name + "_2"
                offsets[2]['avdd'] = [int(o, 16) for o in self._pu_calibration[ru_name2]['offset_avdd']]
                offsets[2]['dvdd'] = [int(o, 16) for o in self._pu_calibration[ru_name2]['offset_dvdd']]
            else:
                # no calibrations for PU[2] in file for MIDDLE and INNER layers
                offsets[2]['avdd'] = [0x12] * 8  # no calibrations for PU[2] in file
                offsets[2]['dvdd'] = [0x12] * 8  # no calibrations for PU[2] in file
        else:
            self.logger.debug(f"{ru_name} not in {self._pu_calibration_fpath}, setting offsets to None")

        return offsets

    def setup_rdo(self, connector_nr=4):
        self.rdo = ru_board.Xcku(self.comm_rdo,
                                 self.cru,
                                 ru_main_revision=self.ru_main_revision,
                                 ru_minor_revision=self.ru_minor_revision,
                                 transition_board_version=self.ru_transition_board_version,
                                 power_board_version=self.power_board_version,
                                 power_board_filter_50Hz_ac_power_mains_frequency=self.power_board_filter_50hz_ac_power_mains_frequency,
                                 powerunit_resistance_offset_pt100=self.powerunit_resistance_offset_pt100,
                                 powerunit_1_offset_avdd=None,
                                 powerunit_1_offset_dvdd=None,
                                 powerunit_2_offset_avdd=None,
                                 powerunit_2_offset_dvdd=None,
                                 layer=self.layer)
        self.set_dctrl_connectors(connector_nr, rdo=self.rdo)
        self.chips = [Alpide(self.rdo, chipid=i) for i in self._chipids_ib]
        return self

    def setup_stave(self, rdo=None):
        if rdo is None:
            rdo = self.rdo
        self.chips_ob_lower = {}
        self.chips_ob_lower.update({0<<7|i:Alpide(rdo, chipid=i, is_on_lower_hs=True) for i in self._chipids_ob_a8})
        self.chips_ob_lower.update({0<<7|i:Alpide(rdo, chipid=i, is_on_lower_hs=True) for i in self._chipids_ob_b0})
        self.chips_ob_upper = {}
        self.chips_ob_upper.update({1<<7|i:Alpide(rdo, chipid=i, is_on_upper_hs=True) for i in self._chipids_ob_a8})
        self.chips_ob_upper.update({1<<7|i:Alpide(rdo, chipid=i, is_on_upper_hs=True) for i in self._chipids_ob_b0})
        self.chips_ob = {}
        self.chips_ob.update(self.chips_ob_lower)
        self.chips_ob.update(self.chips_ob_upper)

        self.chips_ml_lower = {}
        self.chips_ml_lower.update({0<<7|i:Alpide(rdo, chipid=i, is_on_lower_hs=True) for i in self._chipids_ml_a8})
        self.chips_ml_lower.update({0<<7|i:Alpide(rdo, chipid=i, is_on_lower_hs=True) for i in self._chipids_ml_b0})
        self.chips_ml_upper = {}
        self.chips_ml_upper.update({1<<7|i:Alpide(rdo, chipid=i, is_on_upper_hs=True) for i in self._chipids_ml_a8})
        self.chips_ml_upper.update({1<<7|i:Alpide(rdo, chipid=i, is_on_upper_hs=True) for i in self._chipids_ml_b0})
        self.chips_ml = {}
        self.chips_ml.update(self.chips_ml_lower)
        self.chips_ml.update(self.chips_ml_upper)

        self.chip_broadcast = Alpide(rdo, chipid=0xF)

    def set_dctrl_connector(self, connector_nr,
                            force=False,
                            rdo=None):
        """Sets the dctrl connector lut for the chips in chipids IB module.
        if force, it also sets the connector on the associated rdo.
        if rdo is not set, the self.rdo is used instead.
        """
        if rdo is None:
            rdo = self.rdo
        lut = {i: connector_nr for i in self._chipids_ib}
        rdo.set_chip2connector_lut(lut)
        if force:
            rdo.alpide_control.set_input(connector_nr, force=True)

    def set_dctrl_connector_ob(self, connector_nr, chipid_list,
                               is_on_upper_hs=False, force=False,
                               rdo=None):
        """Sets the dctrl connector lut for the chipids (simple, i.e. 7 bits)
        in the chipid_list.
        if is_on_upper_hs it also adds the 8th bit to the chipid.
        if force, it also sets the connector on the associated rdo.
        if rdo is not set, the self.rdo is used instead."""
        assert connector_nr in range(4)
        if rdo is None:
            rdo = self.rdo
        if is_on_upper_hs:
            lut = {1<<7|i: connector_nr for i in chipid_list}
        else:
            lut = {i: connector_nr for i in chipid_list}
        rdo.update_chip2connector_lut(lut)
        if force:
            rdo.alpide_control.set_input(connector_nr, force=True)

    def set_dctrl_connectors(self, connector_nr, rdo=None):
        """Sets the dctrl connectors"""
        if rdo is None:
            rdo = self.rdo
        self.set_dctrl_connector(connector_nr, rdo=rdo)
        self.set_dctrl_connector_ob(0, self._chipids_ob_a8, is_on_upper_hs=False, rdo=rdo)
        self.set_dctrl_connector_ob(1, self._chipids_ob_b0, is_on_upper_hs=False, rdo=rdo)
        self.set_dctrl_connector_ob(2, self._chipids_ob_a8, is_on_upper_hs=True, rdo=rdo)
        self.set_dctrl_connector_ob(3, self._chipids_ob_b0, is_on_upper_hs=True, rdo=rdo)

    def setup_rdos(self, connector_nr=2):
        """Fills the rdos list with RUs, assigns them the chips in the stave list"""

        for rdo in self.rdo_list:
            if self.chips_ob_lower == {}:
                self.setup_stave()
            assert self.chips_ob_lower != {}

        self.load_powerunit_offset_file()
        for list_index, gbt_channel in enumerate(self.ctrl_link_list):

            stave_number = self.get_stave_number(gbt_channel)
            layer_number = self.get_layer(gbt_channel)
            offsets = self.get_powerunit_offsets(layer_number, stave_number)
            rdo = ru_board.Xcku(comm=self.comm_rdo_list[list_index],
                                cru=self.cru,
                                ru_main_revision=self.ru_main_revision,
                                ru_minor_revision=self.ru_minor_revision,
                                transition_board_version=self.ru_transition_board_version,
                                power_board_version=self.power_board_version,
                                power_board_filter_50Hz_ac_power_mains_frequency=self.power_board_filter_50hz_ac_power_mains_frequency,
                                powerunit_resistance_offset_pt100=self.powerunit_resistance_offset_pt100,
                                powerunit_1_offset_avdd=offsets[1]['avdd'],
                                powerunit_1_offset_dvdd=offsets[1]['dvdd'],
                                powerunit_2_offset_avdd=offsets[2]['avdd'],
                                powerunit_2_offset_dvdd=offsets[2]['dvdd'],
                                layer=self.layer)
            self.setup_stave(rdo=rdo)
            self.set_dctrl_connectors(connector_nr, rdo=rdo)
            self.stave_list.append([Alpide(rdo, chipid=chipid) for chipid in self._chipids_ib])
            # OL
            stave_ob_lower_dict = {chip.extended_chipid: Alpide(rdo,
                                                                chipid=chip.chipid,
                                                                is_on_lower_hs=chip.is_on_lower_hs,
                                                                is_on_upper_hs=chip.is_on_upper_hs)
                                   for chipid, chip in self.chips_ob_lower.items()}
            stave_ob_upper_dict = {chip.extended_chipid: Alpide(rdo,
                                                                chipid=chip.chipid,
                                                                is_on_lower_hs=chip.is_on_lower_hs,
                                                                is_on_upper_hs=chip.is_on_upper_hs)
                                   for chipid, chip in self.chips_ob_upper.items()}
            ob_stave_dict = {}
            ob_stave_dict.update(stave_ob_lower_dict)
            ob_stave_dict.update(stave_ob_upper_dict)
            for i in ob_stave_dict.keys():
                assert isinstance(ob_stave_dict[i], Alpide)

            for chipid in self._chipids_ob_a8:
                assert chipid in rdo.get_chip2connector_lut().keys()
                assert chipid in stave_ob_lower_dict.keys(), f"{chipid} not in {stave_ob_lower_dict.keys()}"
            for chipid in self._chipids_ob_b0:
                assert chipid in rdo.get_chip2connector_lut().keys()
                assert chipid in stave_ob_lower_dict.keys(), f"{chipid} not in {stave_ob_lower_dict.keys()}"

            self.stave_ob_dict[gbt_channel] = ob_stave_dict
            self.stave_ob_lower_dict[gbt_channel] = stave_ob_lower_dict
            self.stave_ob_upper_dict[gbt_channel] = stave_ob_upper_dict

            # ML
            stave_ml_lower_dict = {chip.extended_chipid: Alpide(rdo,
                                                                chipid=chip.chipid,
                                                                is_on_lower_hs=chip.is_on_lower_hs,
                                                                is_on_upper_hs=chip.is_on_upper_hs)
                                   for chipid, chip in self.chips_ml_lower.items()}
            stave_ml_upper_dict = {chip.extended_chipid: Alpide(rdo,
                                                                chipid=chip.chipid,
                                                                is_on_lower_hs=chip.is_on_lower_hs,
                                                                is_on_upper_hs=chip.is_on_upper_hs)
                                   for chipid, chip in self.chips_ml_upper.items()}
            ml_stave_dict = {}
            ml_stave_dict.update(stave_ml_lower_dict)
            ml_stave_dict.update(stave_ml_upper_dict)
            for i in ml_stave_dict.keys():
                assert isinstance(ml_stave_dict[i], Alpide)

            for chipid in self._chipids_ml_a8:
                assert chipid in rdo.get_chip2connector_lut().keys()
                assert chipid in stave_ml_lower_dict.keys(), f"{chipid} not in {stave_ml_lower_dict.keys()}"
            for chipid in self._chipids_ml_b0:
                assert chipid in rdo.get_chip2connector_lut().keys()
                assert chipid in stave_ml_lower_dict.keys(), f"{chipid} not in {stave_ml_lower_dict.keys()}"

            self.stave_ml_dict[gbt_channel] = ml_stave_dict
            self.stave_ml_lower_dict[gbt_channel] = stave_ml_lower_dict
            self.stave_ml_upper_dict[gbt_channel] = stave_ml_upper_dict

            self.chip_broadcast_dict[gbt_channel] = Alpide(rdo, chipid=0xF)
            self.rdo_list.append(rdo)
        assert len(self.rdo_list) == len(self.ctrl_link_list), \
            f"Not all the rdo objects were correctly created.\n gbt_channel_link {self.ctrl_link_list},rdo_list {self.rdo_list}"
        self.rdo = self.rdo_list[0]

    def setup_boards(self):
        """Setup board classes"""
        assert self.cru_type not in [CruType.O2, CruType.FLX], "Setup boards should not be used for O2 CRU setup"
        self.setup_cru()
        #using first rdo from rdo_list as default
        #self.setup_rdo()
        self.rdo_list = [self.rdo]

    def initialize_gbtx_usb(self, all_gbtx=True, gbtx_num=0,
                            xml_gbtx0_RUv1_1=os.path.join(script_path, "../../modules/gbt/software/GBTx_configs/GBTx0_Config_RUv1_1.xml"),
                            xml_gbtx1_RUv1_1=os.path.join(script_path, "../../modules/gbt/software/GBTx_configs/GBTx1_Config_RUv1_1.xml"),
                            xml_gbtx2_RUv1_1=os.path.join(script_path, "../../modules/gbt/software/GBTx_configs/GBTx2_Config_RUv1_1.xml"),
                            xml_gbtx0_RUv2_x=os.path.join(script_path, "../../modules/gbt/software/GBTx_configs/GBTx0_Config_RUv2.xml"),
                            xml_gbtx1_RUv2_x=os.path.join(script_path, "../../modules/gbt/software/GBTx_configs/GBTx1_Config_RUv2.xml"),
                            xml_gbtx2_RUv2_x=os.path.join(script_path, "../../modules/gbt/software/GBTx_configs/GBTx2_Config_RUv2.xml")):
        """Configures the GBTx0, 1 and 2 on the RU via USB, if <all_gbtx> is false, then only the gbtx specified by <gbtx_num> is configured"""
        assert gbtx_num in range(3)
        comm_old = self.comm_rdo
        self.comm_rdo.stop()
        self.comm_rdo = usb_communication.PyUsbComm(serialNr=USB_SERIAL_RDO)
        self.setup_rdo()
        self.rdo.initialize()
        if self.rdo.ru_main_revision == 1:
            if gbtx_num == 0 or all_gbtx:
                self.rdo.gbtx0_swt.configure(filename=xml_gbtx0_RUv1_1)
            if gbtx_num == 1 or all_gbtx:
                self.rdo.gbtx1_swt.configure(filename=xml_gbtx1_RUv1_1)
            if gbtx_num == 2 or all_gbtx:
                self.rdo.gbtx2_swt.configure(filename=xml_gbtx2_RUv1_1)
        else:
            if gbtx_num == 0 or all_gbtx:
                self.rdo.gbtx0_swt.configure(filename=xml_gbtx0_RUv2_x)
            if gbtx_num == 1 or all_gbtx:
                self.rdo.gbtx1_swt.configure(filename=xml_gbtx1_RUv2_x)
            if gbtx_num == 2 or all_gbtx:
                self.rdo.gbtx2_swt.configure(filename=xml_gbtx2_RUv2_x)
        self.comm_rdo.stop()
        self.comm_rdo = comm_old
        self.setup_rdo()

    def initialize_all_gbtx12(self,
                              check=False,
                              readback=False,
                              use_xcku=True,
                              pre_check_fsm=True):
        """Configures the GBTx1 and GBTx2 on the RU
        If use_xcku is true, it uses the ultrascale wishbone slave to execute the transaction, otherwise it uses the sca I2C
        """
        for rdo in self.rdo_list:
            rdo.initialize_gbtx(check=check, readback=readback, use_xcku=use_xcku, pre_check_fsm=pre_check_fsm, gbtx_index=2)
            rdo.initialize_gbtx(check=check, readback=readback, use_xcku=use_xcku, pre_check_fsm=pre_check_fsm, gbtx_index=1)

    def initialize_all_gbtx1(self,
                             check=False,
                             readback=False,
                             use_xcku=True,
                             pre_check_fsm=True):
        """Configures the GBTx1 on the RU
        If use_xcku is true, it uses the ultrascale wishbone slave to execute the transaction, otherwise it uses the sca I2C
        """
        for rdo in self.rdo_list:
            rdo.initialize_gbtx(check=check, readback=readback, use_xcku=use_xcku, pre_check_fsm=pre_check_fsm, gbtx_index=1)

    def initialize_board(self, gbt_channel, reset_pa3=False, reset_force=False):
        rdo = self.rdos(gbt_channel)
        if self.cru_type is CruType.O2:
            self.cru.reset_sc_core(gbt_channel)
            rdo.sca.initialize()
            rdo.pa3.initialize(reset=reset_pa3, reset_force=reset_force)
        elif self.cru_type is CruType.FLX:
            self.cru.initialize(gbt_ch=gbt_channel)
            rdo.sca.initialize()
            rdo.pa3.initialize(reset=reset_pa3, reset_force=reset_force)
        elif self.cru_type is CruType.RUv0:
            self.cru.reset_sc_core(gbt_channel)
            rdo.sca.initialize()
            rdo.pa3.initialize(reset=reset_pa3, reset_force=reset_force)
        else:
            raise NotImplementedError("Unkown CRU")

    def initialize_boards(self, reset_pa3=False, reset_force=False, initialize_gbtx12=False):
        if self.cru_type is CruType.O2:
            self.cru.initialize()
            for rdo in self.rdo_list:
                rdo.sca.initialize()
                rdo.pa3.initialize(reset=reset_pa3, reset_force=reset_force)
        elif self.cru_type is CruType.FLX:
            self.cru.initialize()
            for rdo in reversed(self.rdo_list):
                rdo.initialize(initialize_gbtx12=initialize_gbtx12)
                rdo.sca.initialize()
                rdo.pa3.initialize(reset=reset_pa3, reset_force=reset_force)
        elif self.cru_type is CruType.RUv0:
            self.cru.initialize()
            self.rdo.pa3.initialize(reset=reset_pa3, reset_force=reset_force)
        else:
            raise NotImplementedError("Unknown CRU")

    def initialize_all_rdos(self):
        for rdo in reversed(self.rdo_list):
            rdo.initialize()
        time.sleep(0.1)

    def are_all_rdos_initialized(self):
        """Verifies that all the RDOs are correctly initialised.
        To be executed at the beginning of a data taking run.

        returns:
         okay     : global status
         ret_list : list of stave numbers with problems in format L<layer:1>_<stave:02>
        """
        okay = True
        ret_list = []
        for rdo in self.rdo_list:
            if not rdo.is_initialized():
                okay = False
                gbt_channel = rdo.get_gbt_channel()
                stave_number = self.get_stave_number(gbt_channel)
                layer_number = self.get_layer(gbt_channel)
                stave = f"L{layer_number}_{stave_number:02}"
                ret_list.append(stave)
                self.logger.error(f"RU on channel {gbt_channel} for stave {stave} not initialised!")
        return okay, ret_list

    def initialize_for_regression(self):
        assert self.cru_type is CruType.RUv0, "Regression only supported on RUv0 CRU"
        self.initialize_boards()
        self.rdo.powerunit_1.initialize()
        self.rdo.powerunit_1.power_off_all()
        time.sleep(2)
        self.rdo.powerunit_1.setup_power_modules()
        time.sleep(1)
        self.rdo.powerunit_1.power_on_modules()
        time.sleep(2)
        self.rdo.powerunit_1.log_values_modules()

    def switch_to_crystal_clock(self, reprogram_ultrascale=False):
        """Switches all the RUs to the crystal clock"""
        self.cru.initialize()
        for rdo in self.rdo_list:
            rdo.pa3.set_clock_mux_source_crystal()
        time.sleep(1.2)
        if reprogram_ultrascale:
            self.program_all_xcku()
        else:
            self.reset_all_xcku()

    def switch_to_jitter_cleaner_clock(self, reprogram_ultrascale=False):
        """Switches all the RUs to the jitter cleaner clock"""
        self.cru.initialize()
        for rdo in self.rdo_list:
            rdo.pa3.set_clock_mux_source_jitter_cleaner()
        time.sleep(1.2)
        if reprogram_ultrascale:
            self.program_all_xcku()
        else:
            self.reset_all_xcku()

    def get_all_lol_counters(self):
        """returns all the pa3 lol countrs """
        ret_dict = {}
        for rdo in self.rdo_list:
            d = {}
            d['lol'],d['c1b'],d['c2b'] = rdo.pa3.loss_of_lock_counter.get()
            ret_dict[rdo.get_gbt_channel()] = d
        return ret_dict

    def log_all_lol_counters(self):
        """Logs the output from get_all_lol_counters"""
        ret_dict = self.get_all_lol_counters()
        for gbt_channel, d in ret_dict.items():
            self.logger.info(f"GBT channel {gbt_channel:2}: LOL {d['lol']} C1B {d['c1b']} C2B {d['c2b']}")

    def is_any_lol(self):
        """Returns global and single LOL for the boards connected to the CRU
        global_lol = bool
        single_lol = {gbt_channel: bool}
        """
        global_lol = False # https://gitlab.cern.ch/alice-its-wp10-firmware/CRU_ITS/issues/113
        single_lol = {k:False for k in self.ctrl_link_list} # https://gitlab.cern.ch/alice-its-wp10-firmware/CRU_ITS/issues/91
        ret_dict = self.get_all_lol_counters()
        if self.lol_cntr is None:
            self.logger.info('First instance, recording lol')
            self.lol_cntr = ret_dict
        else:
            lols = 0
            for gbt_channel, d in ret_dict.items():
                if d['c2b'] > self.lol_cntr[gbt_channel]['c2b'] and d['lol'] > self.lol_cntr[gbt_channel]['lol']:
                    # LOL condition
                    single_lol[gbt_channel] = True
                    lols +=1
                    self.lol_cntr[gbt_channel]['c2b'] = d['c2b'] # update
                    self.lol_cntr[gbt_channel]['lol'] = d['lol'] # update
                elif d['c2b'] < self.lol_cntr[gbt_channel]['c2b'] or d['lol'] < self.lol_cntr[gbt_channel]['lol']:
                    # Any of the two counters decreased
                    self.logger.warning(f"LOL counter c2b or lol decreased for channel {gbt_channel}. c2b {self.lol_cntr[gbt_channel]['c2b']}=>{d['c2b']}, lol  {self.lol_cntr[gbt_channel]['lol']}=>{d['lol']}")
                    self.logger.warning("Updating counters")
                    self.lol_cntr[gbt_channel]['c2b'] = d['c2b'] # update
                    self.lol_cntr[gbt_channel]['lol'] = d['lol'] # update
                elif d['c2b'] > self.lol_cntr[gbt_channel]['c2b']:
                    # ONLY C2B increased
                    self.logger.warning(f"Only counter c2b increased for channel {gbt_channel}")
                    self.logger.warning("Updating counters")
                    self.lol_cntr[gbt_channel]['c2b'] = d['c2b'] # update
                    self.lol_cntr[gbt_channel]['lol'] = d['lol'] # update
                elif d['lol'] > self.lol_cntr[gbt_channel]['lol']:
                    # ONLY LOL increased
                    self.logger.warning(f"Only counter lol increased for channel {gbt_channel}")
                    self.logger.warning("Updating counters")
                    self.lol_cntr[gbt_channel]['c2b'] = d['c2b'] # update
                    self.lol_cntr[gbt_channel]['lol'] = d['lol'] # update
            if lols == len(self.ctrl_link_list):
                global_lol = True
        return global_lol, single_lol

    def reset_all_xcku(self):
        """Resets all the XCKU FPGAs"""
        self.initialize_boards()
        for rdo in self.rdo_list:
            rdo.sca.reset_xcku()

    def reset_all_pa3(self, force=True):
        """Resets all the PA3 FPGAs"""
        self.initialize_boards()
        for rdo in self.rdo_list:
            try:
                rdo.pa3.stop_scrubbing()
            except (ScrubbingStuckOn, DoubleBitError):
                if not force:
                    self.logger.error("PA3 reset without force failed, scrubbing stuck or double-bit error")
            if not force:
                rdo.pa3.initialize(reset=True)
            else:
                rdo.pa3.initialize(reset_force=True)
        time.sleep(0.5)

    def check_scrub_ok_all(self, ic=FlashSelectICOpcode.FLASH_IC1, num_checks=2, logging=True):
        self.initialize_boards()
        errors = 0
        for rdo in self.rdo_list:
            already_at_fault = False
            try:
                rdo.pa3.stop_scrubbing()
            except (ScrubbingStuckOn, DoubleBitError):
                already_at_fault = True
            rdo.pa3.initialize(reset_force=True)
            time.sleep(0.5)

            for _ in range(num_checks):
                if already_at_fault:
                    errors += 1
                    already_at_fault = False
                else:
                    success = rdo.check_scrub_ok(ic=ic, logging=logging)
                    if not success:
                        errors += 1

        if errors > 0:
            self.logger.warning(f"Scrubbing failed {errors} times")
            return False
        else:
            return True

    def check_scrub_and_reflash_all(self, filename, ic=FlashSelectICOpcode.FLASH_IC1, num_checks=2):
        """Checks all scrubbing images, and reflash if needed

        filename: Path to scrubbing file, e.g. ~/XCKU_top_220506_1606_9667c5d4_bs_ecc.bit
        """
        self.initialize_boards()
        for rdo in self.rdo_list:
            already_at_fault = False
            try:
                rdo.pa3.stop_scrubbing()
            except (ScrubbingStuckOn, DoubleBitError):
                already_at_fault = True
            rdo.pa3.initialize(reset_force=True)
            time.sleep(0.5)

            for _ in range(num_checks):
                if already_at_fault:
                    self.logger.info("Forcing reflash...")
                    rdo.reflash_scrub_block(filename=filename, location=ic)
                    already_at_fault = False
                else:
                    rdo.check_scrub_and_reflash(filename=filename, ic=ic)

    def program_all_xcku(self, use_gold=False):
        """Programs all ultrascale devices"""
        self.initialize_boards()
        for rdo in self.rdo_list:
            if not use_gold:
                # Default functionality. Tests all bitfile positions
                if not rdo.program_xcku_and_retry():
                    self.logger.error(f"RDO {rdo.get_gbt_channel()}\tCould not program XCKU")
            else:
                # Special case, forcing use of gold position on chip 1
                if not rdo.program_xcku(use_gold=True):
                    self.logger.error(f"RDO {rdo.get_gbt_channel()}\tCould not program XCKU")
        self.initialize_boards()

    def enable_all_scrubbing(self):
        """Starts scrubbing for all XCKU"""
        for rdo in self.rdo_list:
            rdo.pa3.initialize(reset=False)
            rdo.pa3.config_controller.start_blind_scrubbing()

    def disable_all_scrubbing(self):
        """Stops scrubbing for all XCKU"""
        for rdo in self.rdo_list:
            rdo.pa3.initialize(reset=False)
            rdo.pa3.stop_scrubbing()

    def log_scrubbing_counter(self):
        """Logs scrubbing counter for all XCKU"""
        for rdo in self.rdo_list:
            self.logger.info(f"RU {rdo.get_gbt_channel()}: {rdo.pa3.config_controller.get_scrubbing_counter()} cycles")

    def log_all_scrubbing_status(self):
        for rdo in self.rdo_list:
                status = rdo.pa3.config_controller.is_scrubbing()
                counter = rdo.pa3.config_controller.get_scrubbing_counter()
                sb_error = rdo.pa3.ecc.get_sb_error()
                db_error = rdo.pa3.ecc.get_db_error()
                ecc_status = rdo.pa3.ecc.get_status()
                self.logger.info(f"RDO {rdo.get_gbt_channel():2} Scrubbing? {status} Count: {counter:<5} SB errors: {sb_error:<5} DB errors: {db_error:<5} ECC status: 0b{ecc_status:04b}")

    def scrubbing_off_all(self):
        for rdo in self.rdo_list:
            rdo.pa3.initialize(reset=False)
            try:
                rdo.pa3.stop_scrubbing()
            except DoubleBitError:
                rdo.pa3.reset_pa3(force=True)


    def loopback_test_gbtx01(self, test_time_sec=30):
        """ Loopback test from CRU to all XCKU GBTx0 and GBTx1

        The CRU transmit counters values on the SWT downlinks. The GBTx0 and GBTx1
        of all XCKUs are configured to transmit the same value back to the CRU. The CRU checks
        whether the value matches the transmitted one. Error counts are printed to screen.
        """
        self.logger.info("Starting loopback test of GBTx0 and GBTx1")
        self._loopback_all_gbt_packets_in_fpga()
        self.cru.start_gbt_loopback_test()
        time.sleep(2)
        self.cru.gbt.cntrst()
        self.logger.info(f"Waiting {test_time_sec} seconds before printing results")
        time.sleep(test_time_sec)
        self.cru.gbt.log_loopback_counters()
        self.cru.stop_gbt_loopback_test()
        time.sleep(2)
        self.reset_all_xcku()
        self.cru.initialize()


    def loopback_all_gbt_packets(self, in_fpga=True):
        """Loopback all gbtx0 packets for test purposes"""
        if in_fpga:
            self._loopback_all_gbt_packets_in_fpga()
        else:
            self._loopback_all_gbt_packets_in_gbtx()

    def _loopback_all_gbt_packets_in_fpga(self):
        """Loopback gbtx0 gbt packets controllers for test purposes"""
        for rdo in self.rdo_list:
            rdo.gbtx01_controller.set_loopback()

    def _loopback_all_gbt_packets_in_gbtx(self):
        """Loopback all gbtx0 gbt packets for test purposes"""
        for rdo in self.rdo_list:
            rdo.gbtx0_swt.set_internal_loopback()

    def set_gbtx0_clkdes_delay(self, coarse_delay=4, fine_delay=0, clkdes_index=2):
        """Sets the coarse and fine delay of the GBTx CLKDES"""
        for rdo in self.rdo_list:
            rdo.gbtx0_swt.setreg_coarse_delay(channel=clkdes_index, delay=coarse_delay)
            assert rdo.gbtx0_swt.getreg_coarse_delay(channel=clkdes_index)==coarse_delay
            rdo.gbtx0_swt.setreg_fine_delay(channel=clkdes_index, delay=fine_delay)
            assert rdo.gbtx0_swt.getreg_fine_delay(channel=clkdes_index)==fine_delay

    def _to_rdo_list_len_list(self, value):
        """Takes a value or a list of values,
        if it is a value, it returns it as list of len of the rdo_list,
        if it is a list or tuple, it checks that it has the correct length"""
        if value is None:
            value = [None for _ in self.rdo_list]
        if isinstance(value, int):
            value = [value for _ in self.rdo_list]
        assert isinstance(value, (list, tuple)), value
        assert len(value)==len(self.rdo_list)
        return value

    @staticmethod
    def _to_tuple(value, default):
        """Convert input from None/int/list/tuple to tuple"""
        if value is None:
            value = (default,)
        if isinstance(value, int):
            value = (value,)
        return tuple(value)

    def flash_all_rdo_bitfiles(self,
                               filename,
                               bitfile_block=None,
                               scrubfile_block=None,
                               use_ultrascale_fifo=True,
                               force_overwrite=False,
                               ignore_lla=False,
                               ic=FlashSelectICOpcode.FLASH_BOTH_IC):
        """Flash all the bitfiles and scrubfiles in the given location"""
        if ignore_lla:
            self.cru._implicit_lla = False
        for rdo in self.rdo_list:
            rdo.sc_core_reset(reset_force=True)
            rdo.flash_bitfiles_to_block(filename=filename,
                                        blocks=[bitfile_block, scrubfile_block],
                                        force_update_param=False,
                                        golden=False,
                                        use_ultrascale_fifo=use_ultrascale_fifo,
                                        force_overwrite=force_overwrite,
                                        ic=ic)

    def flash_all_rdo_goldfiles(self,
                               filename,
                               goldfile_block=None,
                               use_ultrascale_fifo=True,
                               force_overwrite=False,
                               ignore_lla=False,
                               ic=FlashSelectICOpcode.FLASH_BOTH_IC):
        """Flash all the bitfiles and scrubfiles in the given location"""
        if ignore_lla:
            self.cru._implicit_lla = False
        for rdo in self.rdo_list:
            rdo.sc_core_reset(reset_force=True)
            rdo.flash_bitfiles_to_block(filename=filename,
                                        blocks=[goldfile_block],
                                        force_update_param=False,
                                        golden=True,
                                        use_ultrascale_fifo=use_ultrascale_fifo,
                                        force_overwrite=force_overwrite,
                                        ic=ic)

    def flash_all_rdos(self,
                       filename,
                       bitfile_block=None,
                       scrubfile_block=None,
                       goldfile_block=None,
                       use_ultrascale_fifo=True,
                       force_overwrite=False,
                       ignore_lla=False):
        if ignore_lla:
            self.cru._implicit_lla = False
        for rdo in self.rdo_list:
            rdo.sc_core_reset(reset_force=True)
            rdo.flash_bitfiles_to_all_blocks(filename=filename,
                                             blocks=[bitfile_block, scrubfile_block],
                                             goldblock=[goldfile_block],
                                             force_update_param=False,
                                             use_ultrascale_fifo=use_ultrascale_fifo,
                                             force_overwrite=force_overwrite)

    def get_bitfile_locations(self):
        """Displays the location of the bitfiles for all RUs"""
        for rdo in self.rdo_list:
            rdo.sc_core_reset(reset_force=True)
            bit, scrub, gold = rdo.pa3.get_bitfile_locations()
            self.logger.info(f"RU on {rdo.get_gbt_channel():2}\tdefault [0x{bit:04X}], scrub_default [0x{scrub:04X}], golden [0x{gold:04X}]")

    def log_input_power(self):
        """Displays the current and voltage for all RUs"""
        for rdo in self.rdo_list:
            gbt_channel = rdo.get_gbt_channel()
            try:
                self.logger.info(f"RU on {gbt_channel:2}\t{rdo.sca.read_adc_converted(rdo.sca.adc_channels.V_IN):1.3f} V {rdo.sca.read_adc_converted(rdo.sca.adc_channels.I_IN):.3f} A")
            except Exception as e:
                self.logger.info(e,exc_info=True)
                self.logger.error(f"FAILED on RU {gbt_channel}")
            except:
                raise

    def log_optical_power(self):
        """Displays the optical power for all RUs"""
        for rdo in self.rdo_list:
            try:
                self.logger.info(f"RU on {rdo.get_gbt_channel():2}\tCRU {rdo.sca.read_adc_converted(rdo.sca.adc_channels.I_VTRx1):.2f} uA Trigger {rdo.sca.read_adc_converted(rdo.sca.adc_channels.I_VTRx2):.2f} uA")
            except Exception as e:
                self.logger.info(e,exc_info=True)
                self.logger.error(f"FAILED on RU {rdo.get_gbt_channel()}")
            except:
                raise

    def info_for_log_entry(self):
        self.initialize_boards()
        self.logger.info("Input Power")
        self.log_input_power()
        self.logger.info("Version")
        self.version()
        self.logger.info("Bitfile Locations")
        self.get_bitfile_locations()
        self.logger.info("DNA")
        self.dna()
        self.logger.info("Fee ID")
        self.feeid()
        self.logger.info("Uptime")
        self.uptime()
        self.logger.info("Temperature")
        self.temperature()
        self.logger.info("Optical Power")
        self.log_optical_power()

    def info_for_ru_with_corrupt_data(self):
        """Collects information on the status of the RU to be used when debugging
           cases of data corruption at P2"""
        self.logger.info("Input Power")
        self.log_input_power()
        self.logger.info("Version")
        self.version()
        self.logger.info("DNA")
        self.dna()
        self.logger.info("Fee ID")
        self.feeid()
        self.logger.info("Uptime")
        self.uptime()
        self.logger.info("Temperature")
        self.temperature()
        self.logger.info("Optical Power")
        self.log_optical_power()
        for rdo in self.rdo_list:
            self.logger.info(rdo.feeid())
            self.logger.info("### Trigger Handler ###")
            self.logger.info(rdo.trigger_handler.dump_config())
            self.logger.info("### IB Lanes ###")
            self.logger.info(rdo.lanes_ib.dump_config())
            self.logger.info("### OB Lanes ###")
            self.logger.info(rdo.lanes_ob.dump_config())
            self.logger.info("### GBT Packer ###")
            self.logger.info(rdo.gbt_packer.dump_config())
            self.logger.info("### Readout Master ###")
            self.logger.info(rdo.readout_master.dump_config())
            self.logger.info("### IB Datapath Monitor Counters ###")
            self.logger.info(rdo.datapath_monitor_ib.read_counters())
            self.logger.info("### OB Datapath Monitor Counters ###")
            self.logger.info(rdo.datapath_monitor_ob.read_counters())
        self.log_all_gbtx_status(True)
        for rdo in self.rdo_list:
            self.logger.info("### Checking GBTx config ###")
            self.logger.info(rdo.feeid())
            filename = os.path.join(script_path, f"../../modules/gbt/software/GBTx_configs/GBTx0_Config_RUv2.xml")
            self.logger.info(f"GBTx0 {rdo.gbtx0_swt.check_config(filename=filename, use_xml=True)}")
            filename = os.path.join(script_path, f"../../modules/gbt/software/GBTx_configs/GBTx1_Config_RUv2.xml")
            self.logger.info(f"GBTx1 {rdo.gbtx1_swt.check_config(filename=filename, use_xml=True)}")
            filename = os.path.join(script_path, f"../../modules/gbt/software/GBTx_configs/GBTx2_Config_RUv2.xml")
            self.logger.info(f"GBTx2 {rdo.gbtx2_swt.check_config(filename=filename, use_xml=True)}")
            self.logger.info(rdo.gbtx2_swt.check_config(filename=filename, use_xml=True))

    def dump_all_gbtx_config(self):
        """Dumps the configuration of all GBTx chips"""
        directory = 'logs/gbtx_config_dump/'
        if not os.path.exists(directory):
            os.makedirs(directory)
        for rdo in self.rdo_list:
            gbt_channel = rdo.get_gbt_channel()
            self.logger.info(f"Board on channel {gbt_channel}")
            for gbtx in range(3):
                self.logger.info(f"GBTx{gbtx}")
                d = rdo.i2c_gbtx.dump_gbtx_config(gbtx_index=gbtx)
                fname = directory + f"gbtx{gbtx}_ch{gbt_channel}"
                with open(fname, 'w') as f:
                    f.write(d)

    def dump_all_pa3_selected_config(self, directory='logs'):
        """Dumps a limited selection of the PA3 configuration for monitoring purposes"""
        t = time.time()
        if not os.path.exists(directory):
            os.makedirs(directory)
        self.cru.initialize()
        for rdo in self.rdo_list:
            gbt_channel = rdo.get_gbt_channel()
            self.logger.info(f"Dump from PA3 on channel {gbt_channel}")
            d = rdo.pa3.dump_selected_config()
            fname = os.path.join(directory, f"pa3_reads_ch{gbt_channel}")
            with open(fname, 'w') as f:
                f.write(d)
        self.logger.info(f'Done in {time.time()-t:.2f} s')

    def dump_all_rdo_config(self):
        """Dumps all the RDO config"""
        directory = 'logs/ru_config_dump/'
        if not os.path.exists(directory):
            os.makedirs(directory)
        self.cru.initialize()
        for rdo in self.rdo_list:
            gbt_channel = rdo.get_gbt_channel()
            rdo.pa3.initialize(verbose=False)
            d = rdo.pa3.dump_config()
            fname = directory + f"pa3_{gbt_channel}"
            with open(fname, 'w') as f:
                f.write(d)
            self.logger.info(f"Board on channel {gbt_channel}")
            d = rdo.dump_config()
            fname = directory + f"xcku_{gbt_channel}"
            with open(fname, 'w') as f:
                f.write(d)
            for gbtx in range(3):
                self.logger.info(f"GBTx{gbtx}")
                d = rdo.i2c_gbtx.dump_gbtx_config(gbtx_index=gbtx)
                fname = directory + f"gbtx{gbtx}_ch{gbt_channel}"
                with open(fname, 'w') as f:
                    f.write(d)

    def clean_all_datapaths(self):
        """Cleans the datapath of all the RUs"""
        for rdo in self.rdo_list:
            rdo.clean_datapath()

    def gbt_packer_clean_fifos(self):
        raise DeprecationWarning("use rdo.clean_datapath_instead")
        for rdo in self.rdo_list:
            for packer in range(3):
                rdo.trigger_handler.enable_packer(packer=packer)
            rdo.alpide_control.disable_all_dctrl_connectors()
        self.cru.send_start_of_triggered()
        for i in range(10000):
            self.cru.send_trigger(orbit=0xC1EA2,bc=i)
        self.cru.send_end_of_triggered()
        for rdo in self.rdo_list:
            for packer in range(3):
                rdo.trigger_handler.disable_packer(packer=packer)


    def test_pa3_single_scrub(self, num_tests=10):
        for rdo in self.rdo_list:
            pa3 = rdo.pa3
            self.logger.info(f"Checking scrubbing on RU {rdo.get_gbt_channel()}")
            succeed = True
            for _ in range(num_tests):
                pa3.run_single_scrub()
                time.sleep(0.2)
                if pa3.ecc.has_db_error_occurred():
                    self.logger.error("DB errors observed!")
                    succeed = False
                if pa3.ecc.has_sb_error_occurred():
                    self.logger.warning("SB errors observed!")
                    succeed = False
            if succeed:
                self.logger.info(f"Scrubbing on RU {rdo.get_gbt_channel()} is ok!")

    def test_readout_gpio_setup_sensors(self, connector=0,
                                        driver_dac=0x8, pre_dac=0x8,
                                        pll_dac=0x8,
                                        scan_idelay=False):
        self.setup_sensors(LinkSpeed=ModeControlIbSerialLinkSpeed.MBPS400,
                           driver_dac=driver_dac,
                           pre_dac=pre_dac,
                           pll_dac=pll_dac)
        self.rdo.gpio.enable_data(False)
        self.setup_rdo(connector)
        if connector < 4:
            self.rdo.gpio_subset(list(range(7*connector,7*connector+7)))
        else:
            raise RuntimeError("define lookup for connector")
        if scan_idelay:
            self.scan_idelay_gpio(stepsize=1, waittime=0.01)
        self.setup_sensors(LinkSpeed=ModeControlIbSerialLinkSpeed.MBPS400,
                           driver_dac=driver_dac,
                           pre_dac=pre_dac,
                           pll_dac=pll_dac)
        self.setup_readout_gpio()

    def test_readout_gpio_scope(self, connector=0,
                                driver_dac=0x8, pre_dac=0x8,
                                pll_dac=0x8,
                                scan_idelay=False):
        self.setup_sensors(LinkSpeed=ModeControlIbSerialLinkSpeed.MBPS400,
                           driver_dac=driver_dac,
                           pre_dac=pre_dac,
                           pll_dac=pll_dac)
        self.rdo.gpio.enable_data(False)
        self.setup_rdo(connector)
        if connector < 4:
            self.rdo.gpio_subset(list(range(7*connector,7*connector+7)))
        else:
            raise RuntimeError("define lookup for connector")
        if scan_idelay:
            self.scan_idelay_gpio(stepsize=1, waittime=0.01)

    def scan_readout_ob_stave(self,waittime=0.01, full=True):
        """Scans the idelay ranges under different conditions"""
        if full:
            settings = [(dr,pe) for dr in range(1,16) for pe in range(0,16,3)]
        else:
            settings = [(3,3),(3,6),(3,9),(3,0xC),(3,0xF),
                        (4,9),(4,0xC),(4,0xF),
                        (5,9),(5,0xC),(5,0xF),
                        (6,8),(6,0xC),(6,0xF),
                        (8,8),(8,0xC),(8,0xF),
                        (0xC,8),(0xC,0xC),(0xC,0xF)]
        input(f"The scan will take approximately {16*len(settings)*waittime/0.01}s!\nPress enter to continue or Ctrl-c to abort")
        logging.getLogger().setLevel(logging.ERROR)
        for driver_dac,pre_dac in settings:
            self.test_readout_ob_stave_scope(
                driver_dac=driver_dac, pre_dac=pre_dac,
                pll_dac=0x8,pll_stages=4,
                scan_idelay=True,
                trigger_frequency_hz=100000,
                use_scope=False,
                waittime=waittime)

    def scan_waittime_ob_stave(self,waittime=0.01):
        """Scans the idelay ranges under different conditions"""
        settings = [0.001,0.01,0.1,1]
        logging.getLogger().setLevel(logging.ERROR)
        for waittime in settings:
            self.test_readout_ob_stave_scope(
                driver_dac=0x8, pre_dac=0x8,
                pll_dac=0x8,pll_stages=4,
                scan_idelay=True,
                trigger_frequency_hz=100000,
                use_scope=False,
                waittime=waittime)

    def test_readout_ob_stave_scope(self,
                                    driver_dac=0x8, pre_dac=0x8,
                                    pll_dac=0x8,
                                    pll_stages=4,
                                    scan_idelay=True,
                                    trigger_frequency_hz=0,
                                    use_scope=True,
                                    waittime=0.01,
                                    rdo=None):
        """Method for scanning the idelays and gather eye diagrams for the OB setup.
        If use_scope it requests to press enter and instruct on how to start/stop/reset scope.
        If not it is meant to be called by scan_readout_ob_stave"""
        if rdo is None:
            rdo = self.rdo
        idelay_dir = os.path.join(script_path,'idelay')
        enable_data_after=False
        pattern_name_dict = {False:'prbs',True:'comma'}
        if trigger_frequency_hz != 0:
            self.initialize_all_gbtx12()
            # TODO: Fix
            raise NotImplementedError("Update to new readout!")
            #rdo.trigger_handler.set_trigger_source_mask(0x7)
            rdo.trigger_handler.reset_counters()
            if rdo.trigger_handler.read_counters()['TRIGGER_SENT']!=0:
                # TODO: fix
                raise NotImplementedError
                #rdo.gbt_word_inject.send_eoc()
                rdo.trigger_handler.reset_counters()
                assert rdo.trigger_handler.read_counters()['TRIGGER_SENT'] == 0, 'trigger_handler in mode'
                assert rdo.trigger_handler.get_operating_mode()[0] == 0, 'trigger_handler in mode'
            rdo.trigger_handler.setup_for_continuous_mode(trigger_frequency_hz=trigger_frequency_hz,
                                                          send_pulses=True)
            mode=ModeControlChipModeSelector.TRIGGERED
            pattern=SensorMatrixPattern.TWO_PIXELS_PER_REGION
            pulse2strobe=True
        else:
            mode=ModeControlChipModeSelector.CONFIGURATION
            pattern=SensorMatrixPattern.EMPTY
            pulse2strobe=False
        self.setup_sensors_ob_stave(mode=mode,
                                    pattern=pattern,
                                    driver_dac=driver_dac,
                                    pre_dac=pre_dac,
                                    pll_dac=pll_dac,
                                    pll_stages=pll_stages,
                                    pulse2strobe=pulse2strobe,
                                    rdo=rdo)
        rdo.gpio.enable_data(False)
        if scan_idelay:
            optima,ranges=self.scan_idelay_ob_stave(stepsize=1, waittime=waittime,
                                                    enable_data_after=enable_data_after,
                                                    rdo=rdo)
            if not os.path.exists(idelay_dir):
                os.makedirs(idelay_dir)
            _,layer,stave = rdo.identity.get_decoded_fee_id()
            filename = f"L{layer}_{stave:02}_scan_{waittime*1000}ms_{pattern_name_dict[enable_data_after]}_0kHz_{mode.name}_d{driver_dac}p{pre_dac}s{pll_stages}.csv"
            with open(os.path.join(idelay_dir,filename),'w') as f:
                f.write(f"{optima},{ranges}\n")

        if trigger_frequency_hz != 0:
            if use_scope:
                input('Please reset scope and press enter!')
                # TODO: fix
                raise NotImplementedError
                #rdo.gbt_word_inject.send_soc()
            assert rdo.trigger_handler.read_counters()['TRIGGER_SENT'] != 0, 'trigger_handler not in mode'
            assert rdo.trigger_handler.get_operating_mode()[1]['is_continuous'] == 1, 'trigger_handler not in mode'
            if scan_idelay:
                optima,ranges=self.scan_idelay_ob_stave(stepsize=1, waittime=waittime,
                                                        enable_data_after=enable_data_after,
                                                        rdo=rdo)
                filename = f"L{layer}_{stave:02}_scan_{waittime*1000}ms_{pattern_name_dict[enable_data_after]}_{trigger_frequency_hz}kHz_{mode.name}_d{driver_dac}p{pre_dac}s{pll_stages}.csv"
                with open(os.path.join(idelay_dir,filename),'a+') as f:
                    f.write(f"{optima},{ranges}\n")
                    self.logger.info(f'd{driver_dac:X}p{pre_dac:X}s{pll_stages}: ranges {ranges}')
            if use_scope:
                input('Please stop scope to stop acquisition')
                # TODO: fix
                raise NotImplementedError
                #rdo.gbt_word_inject.send_eoc()

    def test_readout_gpio_routine(self, connector=0, scan_idelay=False, nr_triggers=10):
        self.test_readout_gpio_setup_sensors(connector=connector, scan_idelay=scan_idelay)
        self.cru.send_start_of_triggered()
        self.logger.setLevel(logging.WARNING)
        i = 0

        triggers_sent = 0
        total_events = 0
        total_errors = 0
        try:

            while True:
                read_events, errors = self.test_readout_gpio(nr_triggers, dump_data=False)
                total_events += read_events
                total_errors += errors
                triggers_sent += nr_triggers
                self.logger.info('.', end='', flush=True)
                i += 1
                if i % 20 == 0:
                    self.logger.setLevel(logging.INFO)
                    msg = 'Sent: {0} triggers total, Received {1} events, {2} errors'.format(triggers_sent, total_events, total_errors)
                    self.logger.info(msg)
                    sca_adc_vals = self.rdo.sca.read_adcs_conv()
                    self.logger.info(sca_adc_vals)
                    self.logger.setLevel(logging.WARNING)
        except KeyboardInterrupt:
            self.logger.setLevel(logging.INFO)
            self.logger.info("Done")
            msg = 'Sent: {0} triggers total, Received {1} events, {2} errors'.format(triggers_sent, total_events, total_errors)
            self.logger.info(msg)
            self.cru.send_end_of_triggered()

    def read_maskfile(self, filename):
        maskdict = {}
        if os.path.exists(filename):
            with open(filename, "r") as f:
                data = f.readlines()
                for line in data:
                    splitline = line.split(",")
                    if line[0] == '#' or len(splitline) != 4:
                        continue
                    chipcoord  = ( int(splitline[0]), int(splitline[1]) )
                    pixelcoord = ( int(splitline[2]), int(splitline[3]) )
                    if chipcoord not in maskdict:
                        maskdict[chipcoord] = [ pixelcoord ]
                    else:
                        maskdict[chipcoord].append(pixelcoord)
        else:
            print(f"Maskfile {filename} was not found, continuing w/o masking")

        return maskdict

    def setup_sensors_mask(self, rdo=None):
        #masking pixels in dictionary maskdict
        mask_fl_name = "masklist_testbench.txt"
        maskdict = self.read_maskfile(mask_fl_name)
        if maskdict != None and len(maskdict) != 0:
            for chipcoord in maskdict.keys():
                if chipcoord[0] == self.rdo_list.index(rdo):
                    chip = Alpide(rdo, chipcoord[1])
                    pixelcoords = maskdict[chipcoord]
                    print(f"Masking {len(pixelcoords)} pixels on chip {chipcoord}")
                    chip.mask_pixel(pixelcoords, readback=False, log=False, commitTransaction=True)

    def setup_sensors(self,
                      mode=ModeControlChipModeSelector.TRIGGERED,
                      enable_strobe_generation=0,
                      LinkSpeed=ModeControlIbSerialLinkSpeed.MBPS600,
                      disable_manchester=1,
                      pattern=SensorMatrixPattern.EMPTY,
                      driver_dac=0x8, pre_dac=0x8,
                      pll_dac=0x8, pll_stages=4,
                      enable_clock_gating=True,
                      analogue_pulsing=False,
                      enable_skew_start_of_readout=True,
                      enable_clustering=True,
                      pulse2strobe=True,
                      rdo=None):
        if type(rdo) ==  int:
            rdo = self.rdos(nr=rdo)
        if rdo is None:
            rdo = self.rdo
        if enable_clock_gating:
            enable_clock_gating = 1
        else:
            enable_clock_gating = 0
        if enable_skew_start_of_readout:
            enable_skew_start_of_readout = 1
        else:
            enable_skew_start_of_readout = 0
        if enable_clustering:
            enable_clustering = 1
        else:
            enable_clustering = 0
        assert mode in [ModeControlChipModeSelector.CONFIGURATION,ModeControlChipModeSelector.TRIGGERED]

        stageregs = {5: 0b11, 4: 0b01, 3: 0b00}
        assert pll_stages in stageregs, f'pll_stages={pll_stages} not in {stageregs.keys()}'
        VcoDelayStages = stageregs[pll_stages]

        chip_broadcast = self.stave_chip_broadcast(gbt_ch=rdo.get_gbt_channel())

        chip_broadcast.reset()
        rdo.gth.initialize(check_reset_done=False)
        chip_broadcast.initialize(disable_manchester=disable_manchester, grst=False, cfg_ob_module=False)
        chip_broadcast.setreg_dtu_dacs(PLLDAC=pll_dac, DriverDAC=driver_dac, PreDAC=pre_dac)
        for pll_off_sig in [0, 1, 0]:
            chip_broadcast.setreg_dtu_cfg(VcoDelayStages=VcoDelayStages,
                                          PllBandwidthControl=1,
                                          PllOffSignal=pll_off_sig,
                                          SerPhase=8,
                                          PLLReset=0,
                                          LoadENStatus=0)

        chip_broadcast.board.write_chip_opcode(Opcode.RORST)
        chip_broadcast.setreg_fromu_cfg_1(
            MEBMask=0,
            EnStrobeGeneration=enable_strobe_generation,
            EnBusyMonitoring=1,
            PulseMode=analogue_pulsing,
            EnPulse2Strobe=pulse2strobe,
            EnRotatePulseLines=0,
            TriggerDelay=0)

        self.setup_pulse_and_strobe_duration(pulse_duration_ns=100,
                                             strobe_duration_ns=100,
                                             pulse_to_strobe_duration_ns=25,
                                             strobe_gap_duration_ns=25,
                                             rdo=rdo)

        self.setup_sensor_matrix(pattern=pattern,
                                 rdo=rdo)
        self.setup_sensors_mask(rdo=rdo)

        # ChipModeSelector determines the trigger mode:
        chip_broadcast.setreg_mode_ctrl(ChipModeSelector=ModeControlChipModeSelector.TRIGGERED,
                                        EnClustering=enable_clustering,
                                        MatrixROSpeed=1,
                                        IBSerialLinkSpeed=LinkSpeed,
                                        EnSkewGlobalSignals=0,
                                        EnSkewStartReadout=enable_skew_start_of_readout,
                                        EnReadoutClockGating=enable_clock_gating,
                                        EnReadoutFromCMU=0)

    def setup_sensors_ml_stave(self,
                               mode=ModeControlChipModeSelector.CONFIGURATION,
                               module_list_lower=[1,2,3,4],
                               module_list_upper=[1,2,3,4],
                               excluded_chipid_ext=[],
                               enable_strobe_generation=0,
                               disable_manchester=1,
                               pattern=SensorMatrixPattern.EMPTY,
                               driver_dac=0x8, pre_dac=0x8, pll_dac=0x8,
                               pll_stages=4,
                               enable_clock_gating=False,
                               enable_skew_start_of_readout=False,
                               enable_clustering=True,
                               only_master_chips=False,
                               bad_double_columns=None,
                               bad_pixels=None,
                               avdd=1.82,
                               dvdd=1.82,
                               grst=False,
                               rdo=None):
        self.setup_sensors_ob_stave(mode=mode,
                                    module_list_lower=module_list_lower,
                                    module_list_upper=module_list_upper,
                                    excluded_chipid_ext=excluded_chipid_ext,
                                    enable_strobe_generation=enable_strobe_generation,
                                    disable_manchester=disable_manchester,
                                    pattern=pattern,
                                    driver_dac=driver_dac,
                                    pre_dac=pre_dac,
                                    pll_dac=pll_dac,
                                    pll_stages=pll_stages,
                                    enable_clock_gating=enable_clock_gating,
                                    enable_skew_start_of_readout=enable_skew_start_of_readout,
                                    enable_clustering=enable_clustering,
                                    only_master_chips=only_master_chips,
                                    bad_double_columns=None,
                                    bad_pixels=None,
                                    avdd=avdd,
                                    dvdd=dvdd,
                                    grst=grst,
                                    rdo=rdo)

    def setup_sensors_ob_stave(self,
                               mode=ModeControlChipModeSelector.CONFIGURATION,
                               module_list_lower=[1,2,3,4,5,6,7],
                               module_list_upper=[1,2,3,4,5,6,7],
                               excluded_chipid_ext=[],
                               disable_manchester=1,
                               pattern=SensorMatrixPattern.EMPTY,
                               analogue_pulsing=False,
                               driver_dac=0x8, pre_dac=0x8, pll_dac=0x8,
                               pll_stages=4,
                               enable_clock_gating=False,
                               enable_skew_start_of_readout=False,
                               enable_clustering=True,
                               only_master_chips=False,
                               enable_strobe_generation=0,
                               pulse2strobe=1,
                               bad_double_columns=None,
                               bad_pixels=None,
                               avdd=1.82,
                               dvdd=1.82,
                               grst=False,
                               rdo=None):
        self.logger.info(f"avdd: {avdd}, dvdd: {dvdd}")
        if rdo is None:
            rdo = self.rdo
        cable_length = self.get_cable_length(rdo)
        if enable_clock_gating:
            enable_clock_gating = 1
        else:
            enable_clock_gating = 0
        if enable_skew_start_of_readout:
            enable_skew_start_of_readout = 1
        else:
            enable_skew_start_of_readout = 0
        if enable_clustering:
            enable_clustering = 1
        else:
            enable_clustering = 0
        assert mode in [ModeControlChipModeSelector.CONFIGURATION,ModeControlChipModeSelector.TRIGGERED]

        if self.layer is LayerList.OUTER:
            pu_index_set = [1,2]
            pu_module_lists = [[ x-1 for x in module_list_lower ], [ x-1 for x in module_list_upper ]]
        elif self.layer is LayerList.MIDDLE:
            pu_index_set = [1]
            pu_module_lists = [[ x-1 for x in module_list_lower ]]
            for m in module_list_upper:
                pu_module_lists[0].append(m+3)
        pu_list = self._get_pu_list(pu_index_set, rdo=rdo)

        chip_broadcast = self.stave_chip_broadcast(gbt_ch=rdo.get_gbt_channel())

        self.log_values(rdo=rdo)

        if grst:
            for pu_index, powerunit in enumerate(pu_list):
                powerunit.reset_voltage(avdd=avdd, dvdd=dvdd)
                time.sleep(2) # let the system settle
            self.log_values(rdo=rdo)

            chip_broadcast.reset()
            time.sleep(2) # let the system settle
            self.log_values(rdo=rdo)

            for pu_index, powerunit in enumerate(pu_list):
                powerunit.compensate_voltage_drops_ob(avdd=avdd, dvdd=dvdd, l=cable_length[pu_index], powered_module_list=pu_module_lists[pu_index])
            self.log_values(rdo=rdo)

        chip_broadcast.send_PRST()
        chip_broadcast.clear_cmuerrors(commitTransaction=True)
        chip_broadcast.setreg_cmd(Command=Opcode.RORST, commitTransaction=True) # RORST write_chip_opcode(Opcode.RORST)

        self._setup_sensors_ob_stave(mode=mode,
                                     module_list=module_list_lower,
                                     is_on_lower_hs=True,
                                     excluded_chipid_ext=excluded_chipid_ext,
                                     pll_dac=pll_dac,
                                     driver_dac=driver_dac,
                                     pre_dac=pre_dac,
                                     pll_stages=pll_stages,
                                     disable_manchester=disable_manchester,
                                     only_master_chips=only_master_chips,
                                     enable_clock_gating=enable_clock_gating,
                                     enable_skew_start_of_readout=enable_skew_start_of_readout,
                                     enable_clustering=enable_clustering,
                                     rdo=rdo)

        self._setup_sensors_ob_stave(mode=mode,
                                     module_list=module_list_upper,
                                     is_on_lower_hs=False,
                                     excluded_chipid_ext=excluded_chipid_ext,
                                     pll_dac=pll_dac,
                                     driver_dac=driver_dac,
                                     pre_dac=pre_dac,
                                     pll_stages=pll_stages,
                                     disable_manchester=disable_manchester,
                                     only_master_chips=only_master_chips,
                                     enable_clock_gating=enable_clock_gating,
                                     enable_skew_start_of_readout=enable_skew_start_of_readout,
                                     enable_clustering=enable_clustering,
                                     rdo=rdo)

        chip_broadcast.board.write_chip_opcode(Opcode.RORST)
        chip_broadcast.setreg_fromu_cfg_1(MEBMask=0,
                                          EnStrobeGeneration=enable_strobe_generation,
                                          EnBusyMonitoring=0,
                                          PulseMode=analogue_pulsing,
                                          EnPulse2Strobe=pulse2strobe,
                                          EnRotatePulseLines=0,
                                          TriggerDelay=0)

        self.setup_pulse_and_strobe_duration(pulse_duration_ns=100,
                                             strobe_duration_ns=100,
                                             pulse_to_strobe_duration_ns=25,
                                             strobe_gap_duration_ns=25,
                                             rdo=rdo)

        self.setup_sensor_matrix(pattern=pattern,
                                 bad_double_columns=bad_double_columns,
                                 bad_pixels=bad_pixels,
                                 rdo=rdo)

        for pu_index, powerunit in enumerate(pu_list):
            powerunit.compensate_voltage_drops_ob(avdd=avdd, dvdd=dvdd, l=cable_length[pu_index], powered_module_list=pu_module_lists[pu_index])
        for pu_index, powerunit in enumerate(pu_list):
            powerunit.compensate_voltage_drops_ob(avdd=avdd, dvdd=dvdd, l=cable_length[pu_index], powered_module_list=pu_module_lists[pu_index])
        self.log_values(rdo=rdo)

    def _setup_sensors_ob_stave(self,
                                mode=ModeControlChipModeSelector.TRIGGERED,
                                module_list=[],
                                is_on_lower_hs=True,
                                excluded_chipid_ext=[],
                                driver_dac=0x8, pre_dac=0x8, pll_dac=0x8,
                                pll_stages=4,
                                disable_manchester=True,
                                only_master_chips=False,
                                enable_clock_gating=False,
                                enable_skew_start_of_readout=False,
                                enable_clustering=True,
                                rdo=None):
        """Setups the ob staves for daq"""
        if rdo is None:
            rdo = self.rdo
        assert mode in [ModeControlChipModeSelector.CONFIGURATION,ModeControlChipModeSelector.TRIGGERED]
        chip_list = self._select_hs(is_on_lower_hs, rdo=rdo)
        self.logger.debug(f"chip_list {chip_list.keys()}")
        stageregs = {5: 0b11, 4: 0b01, 3: 0b00}
        assert pll_stages in stageregs, f'pll_stages={pll_stages} not in {stageregs.keys()}'
        VcoDelayStages = stageregs[pll_stages]
        for module in module_list:
            for _, chip in chip_list.items():
                if chip.extended_chipid not in excluded_chipid_ext:
                    if chip.is_on_module(module):
                        if chip.is_outer_barrel_master():
                            if only_master_chips:
                                previous_chipid = chip.chipid & 0xF
                            else:
                                previous_chipid = chip.get_previous_chipid_ob_stave(excluded_chipid_ext=excluded_chipid_ext)
                            self.logger.debug(f"Configuring master {chip.extended_chipid} with previous {previous_chipid}")
                            chip.setreg_cmu_and_dmu_cfg(PreviousChipID=previous_chipid&0xF,
                                                        InitialToken=True,
                                                        DisableManchester=disable_manchester,
                                                        EnableDDR=True,
                                                        commitTransaction=False)

                            chip.setreg_dtu_dacs(PLLDAC=pll_dac,
                                                 DriverDAC=driver_dac,
                                                 PreDAC=pre_dac,
                                                 commitTransaction=False)
                            for pll_off_sig in [0, 1, 0]:
                                chip.setreg_dtu_cfg(VcoDelayStages=VcoDelayStages,
                                                    PllBandwidthControl=1,
                                                    PllOffSignal=pll_off_sig,
                                                    SerPhase=8,
                                                    PLLReset=0,
                                                    LoadENStatus=0,
                                                    commitTransaction=False)
                        elif chip.is_outer_barrel_slave():
                            if not only_master_chips:
                                previous_chipid = chip.get_previous_chipid_ob_stave(excluded_chipid_ext=excluded_chipid_ext)
                                self.logger.debug(f"Configuring slave {chip.extended_chipid} with previous {previous_chipid}")
                                chip.setreg_cmu_and_dmu_cfg(PreviousChipID=previous_chipid&0xF,
                                                            InitialToken=False,
                                                            DisableManchester=disable_manchester,
                                                            EnableDDR=True,
                                                            commitTransaction=False)
                            else:
                                # Comment copied from below (not excluded chips in case of only master)
                                # one chip could be broken, so we need to take care of it
                                # As discussed with @freidt a chip which is excluded
                                # should have:
                                # - previous chipid set to 0
                                # - DDR disabled
                                # - No token
                                previous_chipid = 0
                                chip.setreg_cmu_and_dmu_cfg(PreviousChipID=previous_chipid,
                                                            InitialToken=False,
                                                            DisableManchester=disable_manchester,
                                                            EnableDDR=False,
                                                            commitTransaction=False)

                        # ChipModeSelector determines the trigger mode:
                        # Run for master and slaves on the module
                        chip.setreg_mode_ctrl(ChipModeSelector=mode,
                                              EnClustering=enable_clustering,
                                              MatrixROSpeed=1,
                                              IBSerialLinkSpeed=ModeControlIbSerialLinkSpeed.MBPS1200ALT, # 1.2Gbps (else it does not work)
                                              EnSkewGlobalSignals=0,
                                              EnSkewStartReadout=enable_skew_start_of_readout,
                                              EnReadoutClockGating=enable_clock_gating,
                                              EnReadoutFromCMU=0)

                else: # not (chip.extended_chipid not in excluded_chipid_ext) i.e. chip.extended_chipid in excluded_chipid_ext
                    if chip.is_on_module(module):
                        # As discussed with @freidt a chip which is excluded
                        # should have:
                        # - previous chipid set to 0
                        # - DDR disabled
                        # - No token
                        previous_chipid = 0
                        chip.setreg_cmu_and_dmu_cfg(PreviousChipID=previous_chipid,
                                                    InitialToken=False,
                                                    DisableManchester=disable_manchester,
                                                    EnableDDR=False,
                                                    commitTransaction=False,
                                                    readback=False)
                        # excluded chips should also be put in configuration mode
                        chip.setreg_mode_ctrl(ChipModeSelector=ModeControlChipModeSelector.CONFIGURATION, # not in readout (might not work)
                                              EnClustering=enable_clustering,
                                              MatrixROSpeed=1,
                                              IBSerialLinkSpeed=ModeControlIbSerialLinkSpeed.MBPS1200ALT, # 1.2Gbps (else it does not work)
                                              EnSkewGlobalSignals=0,
                                              EnSkewStartReadout=enable_skew_start_of_readout,
                                              EnReadoutClockGating=enable_clock_gating,
                                              EnReadoutFromCMU=0,
                                              readback=False)

            rdo.flush()

    def setup_dtu_dacs_single_sensor(self,
                                     driver_dac=0x8, pre_dac=0x8, pll_dac=0x8,
                                     chipid=None,
                                     rdo=None):
        """Setups the ob staves for daq"""
        if rdo is None:
            rdo = self.rdo

        if chipid is None:
            raise ValueError
        is_on_lower_hs = False
        is_on_upper_hs = False
        if chipid > 127:
            chipid = chipid - 128
            is_on_upper_hs = True
        else:
            is_on_lower_hs = True

        chip = Alpide(chipid=chipid, board=rdo, is_on_lower_hs=is_on_lower_hs, is_on_upper_hs=is_on_upper_hs)

        chip.setreg_dtu_dacs(PLLDAC=pll_dac,
                             DriverDAC=driver_dac,
                             PreDAC=pre_dac,
                             commitTransaction=True)

    def configure_dtu(self,rdo=None,module_list=[1,2,3,4], is_on_lower_hs=True):
        if rdo is None:
            rdo = self.rdo
        chip_list = self._select_hs(is_on_lower_hs, rdo=rdo)
        self.logger.debug(f"chip_list {chip_list.keys()}")
        for module in module_list:
            for _, chip in chip_list.items():
                if chip.is_on_module(module) and chip.is_outer_barrel_master():
                    for pll_off_sig in [0, 1, 0]:
                        chip.setreg_dtu_cfg(VcoDelayStages=0b01,
                                            PllBandwidthControl=1,
                                            PllOffSignal=pll_off_sig,
                                            SerPhase=8,
                                            PLLReset=0,
                                            LoadENStatus=0,
                                            commitTransaction=False)

    def set_chips_in_mode(self,
                          mode,
                          LinkSpeed=ModeControlIbSerialLinkSpeed.MBPS600,
                          enable_clock_gating=False,
                          enable_skew_start_of_readout=False,
                          enable_clustering=True,
                          rdo=None,
                          silent=False,
                          excluded_chipid_ext=[],
                          only_masters=False):
        if rdo is None:
            rdo = self.rdo
        gbt_ch = rdo.get_gbt_channel()
        if enable_clock_gating:
            enable_clock_gating = 1
        else:
            enable_clock_gating = 0
        if enable_skew_start_of_readout:
            enable_skew_start_of_readout = 1
        else:
            enable_skew_start_of_readout = 0
        if enable_clustering:
            enable_clustering = 1
        else:
            enable_clustering = 0
        assert mode in [ModeControlChipModeSelector.TRIGGERED,
                        ModeControlChipModeSelector.CONFIGURATION]

        if self.layer is LayerList.OUTER or self.layer is LayerList.MIDDLE:
            LinkSpeed = ModeControlIbSerialLinkSpeed.MBPS1200

        chip_broadcast = self.stave_chip_broadcast(gbt_ch=gbt_ch)
        chip_broadcast.setreg_mode_ctrl(ChipModeSelector=mode,
                                        EnClustering=enable_clustering,
                                        MatrixROSpeed=1,
                                        IBSerialLinkSpeed=LinkSpeed,
                                        EnSkewGlobalSignals=0,
                                        EnSkewStartReadout=enable_skew_start_of_readout,
                                        EnReadoutClockGating=enable_clock_gating,
                                        EnReadoutFromCMU=0)
        if not silent:
            self.logger.info(f"Chip triggering mode: {mode}")

        if self.layer is LayerList.OUTER or self.layer is LayerList.MIDDLE:
            if mode is ModeControlChipModeSelector.TRIGGERED:
                # In triggered mode, excluded chips and slave (only_master) need to
                # be set back in configuration to avoid disturbing datataking
                # WARNING: no reads with addres[9:8] = 0x01 are allowed once triggered mode is active
                for chipid in excluded_chipid_ext:
                    chip = self.stave_ob(gbt_ch=gbt_ch)[chipid]
                    chip.setreg_mode_ctrl(ChipModeSelector=ModeControlChipModeSelector.CONFIGURATION, # not in readout (might not work)
                                          EnClustering=enable_clustering,
                                          MatrixROSpeed=1,
                                          IBSerialLinkSpeed=ModeControlIbSerialLinkSpeed.MBPS1200, # 1.2Gbps (else it does not work)
                                          EnSkewGlobalSignals=0,
                                          EnSkewStartReadout=enable_skew_start_of_readout,
                                          EnReadoutClockGating=enable_clock_gating,
                                          EnReadoutFromCMU=0,
                                          readback=False)
                if only_masters:
                    for chipid, chip in self.stave_ob(gbt_ch=gbt_ch).items():
                        if not chip.is_outer_barrel_master():
                            chip = self.stave_ob(gbt_ch=gbt_ch)[chipid]
                            chip.setreg_mode_ctrl(ChipModeSelector=ModeControlChipModeSelector.CONFIGURATION, # not in readout (might not work)
                                                  EnClustering=enable_clustering,
                                                  MatrixROSpeed=1,
                                                  IBSerialLinkSpeed=ModeControlIbSerialLinkSpeed.MBPS1200ALT, # 1.2Gbps (else it does not work)
                                                  EnSkewGlobalSignals=0,
                                                  EnSkewStartReadout=enable_skew_start_of_readout,
                                                  EnReadoutClockGating=enable_clock_gating,
                                                  EnReadoutFromCMU=0,
                                                  readback=False)

    def monitor_temperatures_ob_stave(self):
        self.logger.info(f"{self.rdo_list[0].powerunit_1.read_temperature(1)} {self.rdo_list[0].powerunit_2.read_temperature(1)}")

    def setup_sensor_matrix(self,
                            pattern=SensorMatrixPattern.EMPTY,
                            bad_double_columns=None,
                            bad_pixels=None,
                            rdo=None):
        if rdo is None:
            rdo = self.rdo
        chip_broadcast = self.stave_chip_broadcast(gbt_ch=rdo.get_gbt_channel())

        if pattern == SensorMatrixPattern.EMPTY:
            chip_broadcast.pulse_all_pixels_disable()
            chip_broadcast.mask_all_pixels()
        elif pattern == SensorMatrixPattern.EMPTY_DOUBLE_COLUMNS:
            chip_broadcast.pulse_all_pixels_disable()
            chip_broadcast.mask_all_pixels()
            chip_broadcast.region_control_register_mask_all_double_columns()
        elif pattern == SensorMatrixPattern.IMAGE:
            self.setup_sensor_matrix_image(img_path='sensor_pattern.bmp', rdo=rdo)
        elif pattern == SensorMatrixPattern.ROW:
            chip_broadcast.pulse_all_pixels_disable()
            chip_broadcast.mask_all_pixels()
            chip_broadcast.unmask_row(row=255)
            chip_broadcast.pulse_row_enable(row=255)
        elif pattern == SensorMatrixPattern.PIXEL:
            chip_broadcast.pulse_all_pixels_disable()
            chip_broadcast.mask_all_pixels()
            chip_broadcast.unmask_pixel(pixel_coordinates=[(0,255)])
            chip_broadcast.pulse_pixel_enable(pixel_coordinates=[(0,255)])
        elif pattern == SensorMatrixPattern.TWO_PIXELS_PER_REGION:
            chip_broadcast.pulse_all_pixels_disable()
            chip_broadcast.mask_all_pixels()
            coordinates = [(32*i,255) for i in range(32)] + [(32*i+1,255) for i in range(32)]
            chip_broadcast.unmask_pixel(pixel_coordinates=coordinates)
            chip_broadcast.pulse_pixel_enable(pixel_coordinates=coordinates)
        elif pattern == SensorMatrixPattern.MAX_100KHZ_1GBTX:
            row = 255
            chip_broadcast.pulse_all_pixels_disable()
            chip_broadcast.mask_all_pixels()
            coordinates = []
            for offset in range(3): # Double column offset
                for r in range(row,row+4):  # 8 pixel per cluster
                    coordinates += [(32*i+2*offset+0,r) for i in range(32)] # left pixel
                    coordinates += [(32*i+2*offset+1,r) for i in range(32)] # right pixel
            assert len(coordinates) == len(set(coordinates))
            self.logger.info("{0} pixel pulsed".format(len(set(coordinates))))
            chip_broadcast.unmask_pixel(pixel_coordinates=coordinates)
            chip_broadcast.pulse_pixel_enable(pixel_coordinates=coordinates)
        elif pattern == SensorMatrixPattern.MAX_100KHZ_3GBTX:
            row = 255
            chip_broadcast.pulse_all_pixels_disable()
            chip_broadcast.mask_all_pixels()
            coordinates = []
            for offset in range(9): # Double column offset
                for r in range(row,row+4):  # 8 pixel per cluster
                    coordinates += [(32*i+2*offset+0,r) for i in range(32)] # left pixel
                    coordinates += [(32*i+2*offset+1,r) for i in range(32)] # right pixel
            assert len(coordinates) == len(set(coordinates))
            self.logger.info("{0} pixel pulsed".format(len(set(coordinates))))
            chip_broadcast.unmask_pixel(pixel_coordinates=coordinates)
            chip_broadcast.pulse_pixel_enable(pixel_coordinates=coordinates)
        elif pattern == SensorMatrixPattern.MAX_100KHZ_1GBTX_OB:
            # OB: (CH, CT)    => 3 B
            # 3 full clusters => 12 B
            # 1 DS            => 3 B
            # Total of 18 B per chip
            row = 255
            regions = 3
            chip_broadcast.pulse_all_pixels_disable()
            chip_broadcast.mask_all_pixels()
            coordinates = []
            for offset in range(3): # Double column offset
                for r in range(row,row+4):  # 8 pixel per cluster
                    coordinates += [(32*i+2*offset+0,r) for i in range(regions)] # left pixel
                    coordinates += [(32*i+2*offset+1,r) for i in range(regions)] # right pixel
            coordinates += [(32*i+2*offset+1,r) for i in [regions]] # Single pixel
            assert len(coordinates) == len(set(coordinates))
            self.logger.info("{0} pixel pulsed".format(len(set(coordinates))))
            chip_broadcast.unmask_pixel(pixel_coordinates=coordinates)
            chip_broadcast.pulse_pixel_enable(pixel_coordinates=coordinates)
        elif pattern == SensorMatrixPattern.ONE_PIXEL:
            coordinates = [(511,255)]
            chip_broadcast.pulse_all_pixels_disable()
            chip_broadcast.mask_all_pixels()
            chip_broadcast.region_control_register_mask_all_double_columns()
            raise NotImplementedError
            #chip_broadcast.unmask_pixel(pixel_coordinates=coordinates)
            #chip_broadcast.pulse_pixel_enable(pixel_coordinates=coordinates)
        elif pattern == SensorMatrixPattern.ALL_PIXELS:
            chip_broadcast.unmask_all_pixels()
            chip_broadcast.pulse_all_pixels_enable()
        elif pattern == SensorMatrixPattern.FRACTION:
            chip_broadcast.pulse_all_pixels_disable()
            chip_broadcast.mask_all_pixels()
            for row in range(511):
                if row%10 == 0:
                    chip_broadcast.unmask_row(row=row)
                    chip_broadcast.pulse_row_enable(row=row)
        elif pattern == SensorMatrixPattern.ALL_BUT_UNPULSED:
            chip_broadcast.unmask_all_pixels()
            chip_broadcast.pulse_all_pixels_disable()
        else:
            raise NotImplementedError("Pattern not defined")

        if bad_pixels is not None:
            for chipid_ext, pixellist in bad_pixels.items():
                self.logger.info(f"chipid_ext {chipid_ext}")
                for i,pixelcoords in enumerate(pixellist):
                    if len(pixelcoords) > 2:
                        pixellist[i]=pixelcoords[:2]
                self.logger.info(f"Masking pixels: {pixellist}")
                chipid = chipid_ext & 0x7F
                if chipid_ext > 0x80:
                    is_on_upper_hs = True
                    is_on_lower_hs = False
                else:
                    is_on_upper_hs = False
                    is_on_lower_hs = True
                self.logger.debug(f"ChipID: {chipid} - pixellist: {pixellist}")

                ch = Alpide(chipid=chipid, board=rdo, is_on_upper_hs=is_on_upper_hs, is_on_lower_hs=is_on_lower_hs)
                ch.mask_pixel(pixel_coordinates=pixellist, commitTransaction=True)

        if bad_double_columns is not None:
            for chipid_ext, dcols in bad_double_columns.items():
                chipid = chipid_ext & 0x7F
                if chipid_ext > 0x80:
                    is_on_upper_hs = True
                    is_on_lower_hs = False
                else:
                    is_on_upper_hs = False
                    is_on_lower_hs = True

                self.logger.debug(f"ChipID: {chipid}, ChipIdExt: {chipid_ext}, - double column: {dcols}")
                ch = Alpide(chipid=chipid, board=rdo, is_on_upper_hs=is_on_upper_hs, is_on_lower_hs=is_on_lower_hs)
                ch.mask_dcol(dcol=list(dcols), commitTransaction=True)

    def setup_pulse_and_strobe_duration(self,
                                        pulse_duration_ns,
                                        strobe_duration_ns,
                                        pulse_to_strobe_duration_ns,
                                        strobe_gap_duration_ns,
                                        rdo=None):
        """Sets up the pulse and strobe duration for all the chips"""
        if rdo is None:
            rdo = self.rdo
        chip_broadcast = self.stave_chip_broadcast(gbt_ch=rdo.get_gbt_channel())
        self.logger.info("setting up pulse and strobe duration!")
        # Duration of a Strobe Frame (Trigger)
        frame_duration = round(strobe_duration_ns/25)-1
        chip_broadcast.setreg_fromu_cfg_2(FrameDuration=frame_duration) # (n+1)*25ns

        # Gap between Strobes (internal Trigger, when EnStrobeGeneration=1)
        strobe_gap_duration = round(strobe_gap_duration_ns/25)-1
        chip_broadcast.setreg_fromu_cfg_3(FrameGap=strobe_gap_duration) # (n+1)*25ns

        # Duration of PULSE window
        pulse_duration = round(pulse_duration_ns/25)
        chip_broadcast.setreg_fromu_pulsing_2(PulseDuration=pulse_duration) # n*25ns

        # Delay between Start of PULSE and start of STROBE (when EnPulse2Strobe=1)
        pulse_to_strobe_duration = round(pulse_to_strobe_duration_ns/25)-1
        chip_broadcast.setreg_fromu_pulsing1(PulseDelay=pulse_to_strobe_duration) # (n+1)*25ns

    def chip_write_test(self):
        for i, chip in enumerate(self.chips):
            for j, chip in enumerate(self.chips):
                chip.setreg_VRESETP(0)
            self.chips[i].setreg_VRESETP(i*4+1)
            for j, chip in enumerate(self.chips):
                self.logger.info("iteartion{2}\t{0}:\t{1}".format(j,chip.getreg_VRESETP(),i))

        for i, chip in enumerate(self.chips):
            for j, chip in enumerate(self.chips):
                chip.setreg_dtu_test_2(0)
            self.chips[i].setreg_dtu_test_2(i*4+1)
            for j, chip in enumerate(self.chips):
                self.logger.info("iteartion{2}\t{0}:\t{1}".format(j,chip.getreg_dtu_test_2(),i))

    def setup_sensor_matrix_image(self, img_path,
                                  rdo=None):
        if rdo is None:
            rdo = self.rdo
        chip_broadcast = self.stave_chip_broadcast(gbt_ch=rdo.get_gbt_channel())

        MAX_PIXEL_TRAIN = 500
        image = imageio.imread(img_path)
        chip_broadcast.pulse_all_pixels_disable()
        chip_broadcast.mask_all_pixels()
        coords = []
        total_pixels = 0
        for (row,col), value in np.ndenumerate(image):
            if value == 0:
                coords.append((col,row))
            if len(coords) >= MAX_PIXEL_TRAIN:
                chip_broadcast.unmask_pixel(coords, readback=False, log=False, commitTransaction=False)
                chip_broadcast.pulse_pixel_enable(coords, readback=False, log=False, commitTransaction=True)
                total_pixels += len(coords)
                time.sleep(0.5)
                coords = []
        chip_broadcast.unmask_pixel(coords, readback=False, log=False, commitTransaction=False)
        chip_broadcast.pulse_pixel_enable(coords, readback=False, log=False, commitTransaction=True)
        total_pixels += len(coords)
        self.logger.info("Unmask {0} pixels per image pattern".format(total_pixels))

    def setup_prbs_test_gth(self, chips=None, pll_dac=8, driver_dac=8, pre_dac=8, prbs_rate=600, rdo=None):
        """Set up the prbs test (verifying that it is activated).
        chips is a list of chipids"""
        assert prbs_rate in [600, 1200], "Link Speed for IB must be 600 or 1200"
        if rdo is None:
            rdo = self.rdo
        if chips is None:
            chips = self._chipids_ib
        if prbs_rate == 600:
            PrbsRate = 2
        else:
            PrbsRate = 0  # 1200 Mbps
        for chipid in chips:
            ch = Alpide(rdo, chipid=chipid)
            ch.setreg_dtu_dacs(PLLDAC=pll_dac, DriverDAC=driver_dac, PreDAC=pre_dac)
            for pll_off_sig in [0,1,0]:
                ch.setreg_dtu_cfg(VcoDelayStages=1,
                                  PllBandwidthControl=1,
                                  PllOffSignal=pll_off_sig,
                                  SerPhase=8,
                                  PLLReset=0,
                                  LoadENStatus=0)
            ch.propagate_prbs(PrbsRate=PrbsRate)
        rdo.gth.set_transceivers(chips)
        assert rdo.gth.initialize(), f"Failed to initialize GTH on RU {rdo.get_gbt_channel()}"
        locked = rdo.gth.is_cdr_locked()
        assert False not in locked, f"Failed to lock to the stream on RU {rdo.get_gbt_channel()}: locked by lane {locked}"
        rdo.gth.enable_prbs(enable=True, commitTransaction=True)
        rdo.gth.reset_prbs_counter()
        self.verify_prbs_test_gth(chips=chips, prbs_rate=prbs_rate, rdo=rdo, verbose=True)

    def verify_prbs_test_gth(self, chips, prbs_rate=600, rdo=None, verbose=True):
        """verifies that the prbs test is correctly running by switching each
        chip individually to comma propagation and expecting errors.

        chips is a list of CHIPIDs to test for"""
        assert prbs_rate in [600, 1200], "Link Speed for IB must be 600 or 1200"
        if rdo is None:
            rdo = self.rdo
        nonvalid_prbs = []
        if prbs_rate == 600:
            PrbsRate = 2
        else:
            PrbsRate = 0  # 1200 Mbps
        for chipid in chips:
            ch = Alpide(rdo, chipid=chipid)
            ch.propagate_comma()
            counters = rdo.gth.read_prbs_counter()
            self.logger.debug(f"RDO {rdo.get_gbt_channel()} CHIPID {chipid}: counters {counters}")

            # If the error number is still 0 after clock propagation something is not working
            if counters == [0]*len(rdo.gth.get_transceivers()):
                nonvalid_prbs.append(chipid)
                self.logger.info(f"RDO {rdo.get_gbt_channel()} PRBS errors for chipid {chipid}: {counters}")
            ch.propagate_prbs(PrbsRate=PrbsRate)
            rdo.gth.reset_prbs_counter()
        if nonvalid_prbs == []:
            if verbose:
                self.logger.info(f"RDO {rdo.get_gbt_channel()}: PRBS correctly activated for all chips")
        else:
            self.logger.warning(f"RDO {rdo.get_gbt_channel()}: PRBS NOT activated correctly for chipids {nonvalid_prbs}")

    def check_prbs_test_gth(self, chips, verbose=True, rdo=None):
        """Checks that the PRBS errors are 0.
        chips is a list of CHIPIDs to test for"""
        if rdo is None:
            rdo=self.rdo
        if chips is None:
            chips = self._chipids_ib
        gths = rdo.gth.get_transceivers()
        rdo.gth.set_transceivers(self._chipids_ib) # counters are list-based
        counters = rdo.gth.read_prbs_counter()
        for chipid in chips:
            if counters[chipid]!=0:
                self.logger.error(f"PRBS errors for chipid {chipid} at the beginning: {counters[chipid]}")
        rdo.gth.set_transceivers(gths)
        return counters

    def scan_pll_dac_for_prbs_errors_gth(self, chips, sleeptime=0.1):
        """Aimed at investigating issue #84

        chips is a list of chipds """
        assert sleeptime > 0
        assert self.rdo.gth.read_prbs_counter() == [0] * 9, "PRBS errors already present before start of test. Please start again PRBS test."
        errors={}
        for pll_dac in range(16):
            for chipid in chips:
                ch = Alpide(self.rdo, chipid=chipid)
                ch.setreg_dtu_dacs(PLLDAC=pll_dac)
            time.sleep(sleeptime)
            counters = self.rdo.gth.read_prbs_counter()
            if counters != [0] * 9:
                self.logger.warning("Errors observed in counters for PLL DAC 0x{0:1X} settings: {1}".format(pll_dac, counters))
                errors[pll_dac] = counters
                self.rdo.gth.reset_prbs_counter()
                self.verify_prbs_test_gth(chips=chips, verbose=False)
            else:
                self.logger.info("No errors observed for PLL DAC 0x{0:1X}".format(pll_dac))
        for chipid in chips:
            ch = Alpide(self.rdo, chipid=chipid)
            ch.setreg_dtu_dacs(PLLDAC=0x8)
        return errors

    def scan_prbs_errors_gth(self, chips,
                         sleeptime=0.1,
                         voltage_range=[2.0, 1.9, 1.8, 1.7,
                                        1.68, 1.66, 1.64, 1.62, 1.60],
                         module_list=[0]):
        """Runs a PRBS scan over different PLL chargepump DAC settings and voltages.
        Alpide chips need to be powered on and the """

        errors = {}
        for voltage in voltage_range:
            self.rdo.powerunit_1.setup_power_modules(module_list=module_list,
                                                 avdd=voltage, dvdd=voltage)
            self.rdo.powerunit_1.log_values_modules(module_list=module_list)
            self.rdo.wait(0xFFFF)
            self.setup_prbs_test_gth(chips=chips)
            errors[voltage] = self.scan_pll_dac_for_prbs_errors_gth(chips=chips,
                                                                    sleeptime=sleeptime)
        self.logger.info("Done!")
        return errors

    def setup_all_prbs_test_gth(self, chips=None, pll_dac=8, driver_dac=8, pre_dac=8, prbs_rate=600):
        """Setup GTH PRBS test for all RU's and all chips"""
        for rdo in self.rdo_list:
            self.setup_prbs_test_gth(chips=chips, pll_dac=pll_dac, driver_dac=driver_dac, pre_dac=pre_dac, prbs_rate=prbs_rate, rdo=rdo)
        # reset all PRBS counters again to have them starting about the same time:
        for rdo in self.rdo_list:
            rdo.gth.reset_prbs_counter()

    def read_all_prbs_counters_gth(self, verbose=False):
        """Read the PRBS error counters for all RU's and chips"""
        all_errors = 0
        for rdo in self.rdo_list:
            prbs_errors = rdo.gth.read_prbs_counter()
            if verbose:
                self.logger.info(f"RDO {rdo.get_gbt_channel()} PRBS errors {prbs_errors}")
            for cnt, link in zip(prbs_errors, rdo.gth.transceivers):
                if cnt > 0:
                    self.logger.error(
                        f"{self.subrack} RDO {rdo.get_gbt_channel()} Link {link}: {cnt} PRBS errors observed")
                    all_errors += cnt
        self.logger.info(f"{self.subrack}: Total PRBS errors observed so far: {all_errors}")

    def setup_all_prbs_stress_test_gth(self, pll_dac=15, driver_dac=5, pre_dac=15,
                                       chips=None,
                                       prbs_rate=600,
                                       trigger_period_bc=198,
                                       avdd_set=1.8, dvdd_set=1.8):
        ENABLE_CLOCK_GATING = False
        ENABLE_SKEW_START_OF_READOUT = True
        ENABLE_CLUSTERING = True

        self.compensate_all_voltage_drops_ib_staves(r="from_file", dvdd_set=dvdd_set, avdd_set=avdd_set)
        time.sleep(2.0)
        for rdo in self.rdo_list:
            # TODO: Fix
            rdo.trigger_handler.enable()
            rdo.trigger_handler.set_trigger_delay(1) # 25 ns of delay
            rdo.trigger_handler.set_trigger_source(1)  # Trigger source == SEQUENCER
            rdo.gbt_packer.reset()
            rdo.gbt_packer.set_timeout_to_start(0x0FFF)
            rdo.gbt_packer.set_timeout_start_stop(0xFFFF)
            rdo.gbt_packer.set_timeout_in_idle(0xFFFF)
            # since we don't expect any data, set the timeout to 1 ?
            rdo.trigger_handler.disable_packer(0)
            rdo.trigger_handler.disable_packer(1)
            rdo.trigger_handler.disable_packer(2)
            rdo.trigger_handler.sequencer_set_number_of_hb_per_timeframe(5)
            rdo.trigger_handler.sequencer_set_number_of_hba_per_timeframe(5)
            rdo.trigger_handler.sequencer_set_trigger_period(trigger_period_bc)
            rdo.trigger_handler.disable_timebase_sync()
            rdo.trigger_handler.sequencer_set_mode_continuous()
            rdo.trigger_handler.sequencer_set_number_of_timeframes_infinite(True)

            self.setup_sensors(mode=ModeControlChipModeSelector.CONFIGURATION,
                               enable_strobe_generation=0,
                               pattern=SensorMatrixPattern.ROW,
                               driver_dac=driver_dac,
                               pre_dac=pre_dac,
                               pll_dac=pll_dac,
                               pll_stages=4,
                               enable_clock_gating=ENABLE_CLOCK_GATING,
                               enable_skew_start_of_readout=ENABLE_SKEW_START_OF_READOUT,
                               enable_clustering=ENABLE_CLUSTERING,
                               disable_manchester=1,
                               analogue_pulsing=False,
                               pulse2strobe=True,
                               rdo=rdo)
            self.setup_pulse_and_strobe_duration(pulse_duration_ns=100,
                                                 strobe_duration_ns=trigger_period_bc*25-100,
                                                 pulse_to_strobe_duration_ns=25,
                                                 strobe_gap_duration_ns=25,
                                                 rdo=rdo)
            rdo.trigger_handler.setup_for_continuous_mode(trigger_period_bc=trigger_period_bc,
                                                          send_pulses=True)

        self.setup_all_prbs_test_gth(chips=chips, pll_dac=pll_dac, driver_dac=driver_dac, pre_dac=pre_dac, prbs_rate=prbs_rate)

        for rdo in self.rdo_list:
            self.set_chips_in_mode(mode=ModeControlChipModeSelector.TRIGGERED,
                                   enable_clock_gating=ENABLE_CLOCK_GATING,
                                   enable_skew_start_of_readout=ENABLE_SKEW_START_OF_READOUT,
                                   enable_clustering=ENABLE_CLUSTERING,
                                   rdo=rdo)

        # perform voltage drop compensation twice with a pause in between
        self.compensate_all_voltage_drops_ib_staves(r="from_file", dvdd_set=dvdd_set, avdd_set=avdd_set)
        time.sleep(1.0)
        self.compensate_all_voltage_drops_ib_staves(r="from_file", dvdd_set=dvdd_set, avdd_set=avdd_set)
        time.sleep(1.0)
        self.log_values_ib_staves()

        # now reset the PRBS counters and start triggering
        for rdo in self.rdo_list:
            rdo.gth.reset_prbs_counter()
            #rdo.trigger_handler.sequencer_start()

    def setup_prbs_test_gpio(self, chips, rdo=None):
        """Set up the prbs test for the GPIOs (verifying that it is activated).
        chips is a list of chipids"""
        if rdo is None:
            rdo = self.rdo
        rdo.gpio.enable_data(False)
        for chipid in chips:
            ch = Alpide(rdo, chipid=chipid)
            ch.setreg_mode_ctrl(IBSerialLinkSpeed=ModeControlIbSerialLinkSpeed.MBPS1200)
            ch.propagate_prbs(PrbsRate=1)
        rdo.gpio.enable_prbs(enable=True, commitTransaction=True)
        rdo.gpio.reset_prbs_counter()

        # verifies correct activation
        nonvalid_prbs = []
        for chipid in chips:
            ch = Alpide(rdo, chipid=chipid)
            ch.propagate_clock()
            counters = rdo.gth.read_prbs_counter()
            self.logger.debug("CHIPID {0}: counters {1}".format(chipid, counters))
            if counters==[0]*9:
                nonvalid_prbs.append(chipid)
            rdo.gth.reset_prbs_counter()
            ch.propagate_prbs()
        if nonvalid_prbs==[]:
            self.logger.info("PRBS correctly activated for all chips")
        else:
            self.logger.warning("PRBS NON activated correctly for chipids {0}".format(nonvalid_prbs))

    def scan_idelay_gpio(self,
                         stepsize=10,
                         waittime=1,
                         set_optimum=True,
                         rdo=None):
        if rdo is None:
            rdo = self.rdo
        self.setup_prbs_test_gpio(list(self._chipids_ib), rdo=rdo)

        rdo.gpio.scan_idelays(stepsize, waittime, set_optimum, True)

        for ch in self.chips:
            ch.setreg_mode_ctrl(IBSerialLinkSpeed=ModeControlIbSerialLinkSpeed.MBPS400)
            ch.propagate_data()

    def chips_propagate_clock(self, first=0, last=8):
        for i in range(first, last+1):
            ch = Alpide(self.rdo, chipid=i)
            ch.propagate_clock()

    def reset_counters(self, commitTransaction=True):
        DeprecationWarning("Moved to ru_board")
        self.rdo.reset_counters(commitTransaction=commitTransaction)

    def setup_readout(self, max_retries=10, transceivers=None,
                      rdo=None):
        if type(rdo) == int:
            rdo = self.rdos(nr=rdo)

        if rdo is None:
            rdo = self.rdo
        if transceivers is not None:
            rdo.gth.set_transceivers(transceivers)

        rdo.gth.initialize(commitTransaction=True,
                           check_reset_done=True)
        rdo.wait(10000)
        initialized = rdo.gth.is_reset_done()
        result = True
        if not initialized:
            self.logger.error(f"Could not initialize GTH transceivers on RDO {rdo.get_gbt_channel()}")
            result = False
        rdo.wait(1000)
        locked = rdo.gth.is_cdr_locked()
        if False in locked:
            self.logger.warning(
                f"Could not lock to all sensor clocks: {locked} on RDO {rdo.get_gbt_channel()}")
            result = False
        aligned = rdo.gth.align_transceivers(check_aligned=True)
        retries = 0
        while not aligned and retries < max_retries:
            retries += 1
            self.logger.warning(f"Not Aligned, retry {retries}/{max_retries} on RDO {rdo.get_gbt_channel()}")
            self.logger.warning("Resetting sensors!")
            self.logger.warning("Illegal call to setup_sensors inside setup_datapath_gth! Move it!")
            self.setup_sensors(rdo=rdo)
            aligned=rdo.gth.align_transceivers(check_aligned=True)
        if not aligned:
            self.logger.error("Could not align all transceivers to comma: %r on RDO %d",
                              rdo.gth.is_aligned(),
                              rdo.get_gbt_channel())
            result = False
        else:
            self.logger.info(f"All Transceivers aligned to comma on RDO {rdo.get_gbt_channel()}")
            rdo.gth.enable_data()
            result = True
        rdo.datapath_monitor_ib.reset_all_counters()
        return result

    def setup_readout_gpio(self,rdo=None):
        if rdo is None:
            rdo = self.rdo
        rdo.gpio.initialize()
        aligned = rdo.gpio.align_transceivers(check_aligned=True, max_retries=50)
        result=True
        if not aligned:
            self.logger.error(f"Could not align all transceivers to comma on RDO {rdo.get_gbt_channel()}")
            result = False
        else:
            self.logger.info(f"All Transceivers aligned to comma on RDO {rdo.get_gbt_channel()}")
            time.sleep(1)
            rdo.gpio.enable_data()
        rdo.datapath_monitor_ob.reset_all_counters()
        return result

    def setup_for_continuous_mode(self,
                                  trigger_period_bc,
                                  send_pulses=False,
                                  use_ltu=False):
        """Sets up CRU and RU for continuous mode
        trigger_period_bc: trigger period in BCs
        """
        DeprecationWarning("This function in now deprecated")
        for rdo in self.rdo_list:
            rdo.trigger_handler.setup_for_continuous_mode(trigger_period_bc=trigger_period_bc,
                                                          send_pulses=send_pulses)
        if not use_ltu:
            hb_period_bc=3564,
            hb_period_us = hb_period_bc*25e-3
            self.logger.info(f"hb period {hb_period_us} us")
            self.cru.ttc.configure_emulator(heartbeat_period_bc=hb_period_bc,
                                            heartbeat_wrap_value=255,
                                            heartbeat_keep=6,
                                            heartbeat_drop=2,
                                            periodic_trigger_period_bc=8)

    def setup_for_triggered_mode(self,
                                 trigger_period_bc,
                                 trigger_frequency_hz=20000,
                                 hb_period_bc=3564,
                                 trigger_minimum_distance=100,
                                 num_triggers=None,
                                 send_pulses=False,
                                 use_ltu=False):
        """Sets up CRU and RU for triggered mode"""
        DeprecationWarning("This function in now deprecated")
        # minimum trigger distance 625ns = 100*6.25ns to avoid loss by alpide_control
        assert trigger_minimum_distance < trigger_period_bc<<2, \
            "Trigger period {trigger_period_bc*25e-9} lower than minimum distance between triggers {trigger_minimum_distance*6.25e-9}"
        for rdo in self.rdo_list:
            rdo.trigger_handler.setup_for_triggered_mode(trigger_minimum_distance=trigger_minimum_distance,
                                                         send_pulses=send_pulses)
        if use_ltu:
            self.ltu.set_trigger_rate((1/trigger_frequency_hz)/25e-9)
            if num_triggers is None:
                self.ltu.set_num_triggers(self.ltu.INFINITE_TRIGGERS)
            else:
                self.ltu.set_num_triggers(num_triggers)
        else:
            assert num_triggers is None, "Number of triggers to send can not be adjusted with CRU"
            self.cru.ttc.configure_emulator(heartbeat_period_bc=hb_period_bc,
                                            heartbeat_wrap_value=8,
                                            heartbeat_keep=6,
                                            heartbeat_drop=2,
                                            periodic_trigger_period_bc=trigger_period_bc)

    def chip(self, nr):
        """Return a chip with given number"""
        assert nr in self._chipids_ib, f"Chip {nr} not in {self._chipids_ib}"
        return self.chips[nr]

    def rdos(self, nr):
        """Return a rdo with given gbt_channel"""
        if self.use_can_comm:
            return self.rdo_list[nr]
        else:
            assert nr in self.ctrl_link_list, "RDO {0} not in {1}".format(nr, self.ctrl_link_list)
            index = self.ctrl_link_list.index(nr)
            return self.rdo_list[index]

    def stave(self, nr):
        """Return a stave with given gbt_channel"""
        assert nr in self.ctrl_link_list, "Stave {0} not in {1}".format(nr, self.ctrl_link_list)
        index = self.ctrl_link_list.index(nr)
        return self.stave_list[index]

    def sca(self):
        return self.rdo.sca

    def scas(self, nr):
        assert nr in self.ctrl_link_list, "RDO {0} not in {1}".format(nr, self.ctrl_link_list)
        sca = self.rdos(nr).sca
        return sca

    def pa3(self):
        return self.rdo.pa3

    def pa3s(self, nr):
        assert nr in self.ctrl_link_list, "RDO {0} not in {1}".format(nr, self.ctrl_link_list)
        pa3 = self.rdos(nr).pa3
        return pa3

    def stave_ob(self, gbt_ch):
        """Return a stave_ob with given gbt_channel"""
        if gbt_ch == -1:
            if self.layer is LayerList.OUTER:
                return self.chips_ob
            elif self.layer is LayerList.MIDDLE:
                return self.chips_ml
            else:
                raise NotImplementedError
        else:
            assert gbt_ch in self.ctrl_link_list, "OB stave {0} not in {1}".format(gbt_ch, self.ctrl_link_list)
            if self.layer is LayerList.OUTER:
                return self.stave_ob_dict[gbt_ch]
            elif self.layer is LayerList.MIDDLE:
                return self.stave_ml_dict[gbt_ch]
            else:
                raise NotImplementedError

    def stave_ob_lower(self, gbt_ch):
        """Return a lower half stave_ob with given gbt_channel"""
        if gbt_ch == -1:
            return self.chips_ob_lower
        else:
            assert gbt_ch in self.ctrl_link_list, "OB stave {0} not in {1}".format(gbt_ch, self.ctrl_link_list)
            return self.stave_ob_lower_dict[gbt_ch]

    def stave_ob_upper(self, gbt_ch):
        """Return an upper half stave_ob with given gbt_channel"""
        if gbt_ch == -1:
            return self.chips_ob_upper
        else:
            assert gbt_ch in self.ctrl_link_list, "OB stave {0} not in {1}".format(gbt_ch, self.ctrl_link_list)
            return self.stave_ob_upper_dict[gbt_ch]

    def stave_chip_broadcast(self, gbt_ch):
        """Return a chip broadcast for the stave with given gbt_channel"""
        if gbt_ch == -1:
            return self.chip_broadcast
        else:
            assert gbt_ch in self.ctrl_link_list, "Stave {0} not in {1}".format(gbt_ch, self.ctrl_link_list)
            return self.chip_broadcast_dict[gbt_ch]

    def test_chips(self, nrfirst=0, nrlast=8, nrtests=1000, verbose=True, verbose_ob=False, is_on_ob=False, rdo=None):
        """Perform a chip test on chips [first,last]"""
        if rdo is None:
            rdo = self.rdo
        start_time = time.time()
        total_errors = {}
        register_list = [0x19]
        if is_on_ob:
            chip_list = self.chips_ob
            for _, chip in chip_list.items():
                chip.set_board(board=rdo)
        else:
            chip_list = self.chips
            for chip in chip_list:
                chip.set_board(board=rdo)
        if verbose:
            self.logger.info("Test Chips %d to %d. Nr of RD/WR: %d", nrfirst, nrlast, nrtests)
        for test_reg in register_list:
            for chipid in range(nrfirst, nrlast + 1):
                if verbose and verbose_ob:
                    self.logger.info("Test Chip %d", chipid)
                errors = 0
                self.logger.setLevel(logging.FATAL)
                for j in range(nrtests):
                    pattern =(0x0A+j) & 0xFFFF # limited to 16 bits
                    chip_list[chipid].write_reg(test_reg, pattern, readback=False)
                    try:
                        rdback = chip_list[chipid].read_reg(test_reg, disable_read=False)
                        if rdback != pattern:
                            errors += 1
                            self.logger.error("Readback failure for Chip {0}".format(chipid))
                    except:
                        errors += 1
                        self.logger.error("Readback failure for Chip {0}".format(chipid))
                self.logger.setLevel(logging.INFO)
                if verbose:
                    self.logger.info("Done. Errors: %d", errors)
                total_errors[chipid] = errors
        elapsed_time = time.time() - start_time
        if verbose:
            self.logger.info("Elapsed time {0:.3f} s".format(elapsed_time))
        return total_errors, elapsed_time

    def test_cmu_dmu_errors(self, nrfirst=0, nrlast=8, nrtests=1, verbose=True, verbose_ob=False, is_on_ob=False, rdo=None):
        """Performs a read of the CMU/DMU error register and check for 0 errors,
        derived from test_chips"""
        if rdo is None:
            rdo = self.rdo
        start_time = time.time()
        total_errors = {}
        register_list = [0x11]
        if is_on_ob:
            chip_list = self.chips_ob
            for _, chip in chip_list.items():
                chip.set_board(board=rdo)
        else:
            chip_list = self.chips
            for chip in chip_list:
                chip.set_board(board=rdo)
        if verbose:
            self.logger.info("Test Chips %d to %d. Nr of RD/WR: %d", nrfirst, nrlast, nrtests)
        for test_reg in register_list:
            for chipid in range(nrfirst, nrlast + 1):
                if verbose and verbose_ob:
                    self.logger.info("Test Chip %d", chipid)
                errors = 0
                self.logger.setLevel(logging.FATAL)
                for j in range(nrtests):
                    try:
                        pattern = 0
                        rdback = chip_list[chipid].read_reg(test_reg)
                        if rdback != pattern:
                            errors += 1
                            self.logger.error(f"Readback failure for Chip {chipid}, got 0x{rdback:04x} != 0x{pattern:04x}")
                    except Exception:
                        errors += 1
                        self.logger.error("Readback failure for Chip {0}".format(chipid))
                self.logger.setLevel(logging.INFO)
                if verbose:
                    self.logger.info("Done. Errors: %d", errors)
                total_errors[chipid] = errors
        elapsed_time = time.time() - start_time
        if verbose:
            self.logger.info("Elapsed time {0:.3f} s".format(elapsed_time))
        return total_errors

    def test_chips_fast(self, nrfirst=0, nrlast=8, nrtests=100):
        """Perform a chip test on chips [first,last]"""
        # reads once to set the correct connector to read from
        try:
            self.chips[0].read_reg(0)
        except:
            pass
        min_tests = 10
        if nrtests % min_tests != 0:
            self.logger.info("rounding up number of tests to a multiple of {0}".format(min_tests))
            nrtests = ((nrtests//min_tests)+1)*min_tests
        self.logger.info("Test Chips %d to %d. Nr of RD/WR: %d",
                         nrfirst,
                         nrlast,
                         nrtests)
        self.logger.info("expected run time is {0:.2f}s".format(3.59 + 0.00195*(nrtests - min_tests)))
        total_time = 0
        total_errors = {chipid: 0 for chipid in range(nrfirst, nrlast+1)}

        self.comm_rdo.start_recording()
        errors, elapsed_time = self.test_chips(nrfirst=nrfirst, nrlast=nrlast, nrtests=min_tests, verbose=False)
        total_time += elapsed_time
        total_errors = {chipid: total_errors[chipid]+errors[chipid] for chipid in total_errors.keys()}

        sequence = self.comm_rdo.stop_recording()
        if nrtests > min_tests:
            for _ in range((nrtests//min_tests) - 1):
                self.comm_rdo.load_sequence(sequence)
                self.comm_rdo.prefetch()
                errors, elapsed_time = self.test_chips(nrfirst=nrfirst, nrlast=nrlast, nrtests=min_tests, verbose=False)
                total_time += elapsed_time
                total_errors = {chipid: total_errors[chipid]+errors[chipid] for chipid in total_errors.keys()}

        for chipid in range(nrfirst, nrlast+1):
            self.logger.info("Chipid %d, Errors: %d", chipid, total_errors[chipid])
        self.logger.info("Elapsed time {0:.3f} s".format(total_time))
        return total_errors, total_time

    def reset_readout_master(self):
        for rdo in self.rdo_list:
            rdo.trigger_handler.set_opcode_gating(1)
            rdo.trigger_handler.reset_readout_master()
            rdo.trigger_handler.set_opcode_gating(0)

    def power_on_ib_stave(self,
                          avdd=1.8, dvdd=1.8,
                          avdd_current=1.5, dvdd_current=1.5,
                          bb=0,
                          internal_temperature_limit=30,
                          internal_temperature_low_limit=10,
                          external_temperature_limit=None,
                          external_temperature_low_limit=None,
                          no_offset=False,
                          check_interlock=True,
                          link_speed=600,
                          configure_chips=False,
                          compensate_v_drop=True,
                          rdo=None):
        """Powers on the IB modules connected to the powerunit_1

        Mapping is conform to powerunit channel mapping,
        avdd is the analogue supply voltage
        dvdd is the digital supply voltage
        avdd_current is the analogue supply voltage max current
        dvdd_current is the digital supply voltage max current
        bb is the backbias voltage
        internal_temperature_limit max internal pt100
        external_temperature_limit max stave pt100
        check_interlock parameter for power on and setup power
        configure_chips will configure sensors if True
        compensate_v_drop will compensate voltage drop if True
        """
        assert link_speed in [600, 1200], "Link Speed for IB must be 600 or 1200"
        if rdo is None:
            rdo = self.rdo
            # setup the powerunit offsets
            _, layer, stave = rdo.identity.get_decoded_fee_id()
            self.load_powerunit_offset_file()
            offsets = self.get_powerunit_offsets(layer_number=layer, stave_number=stave)
            rdo.powerunit_1.set_voltage_offset(offsets[1]["avdd"], offsets[1]["dvdd"])
        else:
            gbt_channel = rdo.get_gbt_channel()
            layer = self.get_layer(gbt_channel)
            stave = self.get_stave_number(gbt_channel)

        module_list=[0]
        if not check_interlock:
            self.logger.warning("Ignoring external PT100 reads!")
            external_temperature_limit=None
        try:
            if re.match(SUBRACK_REGEX, self.subrack):
                rdo.powerunit_1.controller.disable_power_interlock()
            else:
                rdo.powerunit_1.controller.disable_all_interlocks()
            time.sleep(0.1)  # let monitoring loop finish
            rdo.powerunit_1.initialize()
            rdo.powerunit_1.controller.enable_temperature_interlock(internal_temperature_limit=internal_temperature_limit,
                                                                    ext1_temperature_limit=external_temperature_limit,
                                                                    internal_temperature_low_limit=internal_temperature_low_limit,
                                                                    ext1_temperature_low_limit=external_temperature_low_limit)
            time.sleep(0.5)  # ADC and RTD values take some time to initialize and read properly
            rdo.powerunit_1.controller.reset_tripped_latch()
            rdo.powerunit_1.log_values_modules(module_list=module_list)
            rdo.alpide_control.disable_dclk()
            rdo.powerunit_1.setup_power_modules(module_list=module_list,
                                            avdd=avdd,
                                            dvdd=dvdd,
                                            avdd_current=avdd_current,
                                            dvdd_current=dvdd_current,
                                            bb=bb,
                                            no_offset=no_offset,
                                            check_interlock=check_interlock)
            rdo.powerunit_1.power_on_modules(module_list=module_list,
                                         backbias_en=(bb!=0),
                                         check_interlock=check_interlock)
            rdo.powerunit_1.log_values_modules(module_list=module_list)
            self.logger.info("Propagating clock")
            rdo.alpide_control.enable_dclk()
            time.sleep(0.3)
            assert not rdo.powerunit_1.controller.did_interlock_fire(), f"Clock propagation provoked interlock!"
            assert rdo.powerunit_1.log_values_modules(module_list=module_list, zero_volt_read_check=True), f"Clock propagation killed voltage => probably internal PU interlock."
            ch = Alpide(rdo, chipid=0x0F)  # global broadcast
            ch.reset()

            if configure_chips:
                if link_speed == 600:
                    LinkSpeed = ModeControlIbSerialLinkSpeed.MBPS600
                else:
                    LinkSpeed = ModeControlIbSerialLinkSpeed.MBPS1200
                self.logger.info(f"Configuring chips on stave L{layer:1}_{stave:02}")
                self.setup_sensors(mode=ModeControlChipModeSelector.CONFIGURATION,
                                   LinkSpeed=LinkSpeed,
                                   rdo=rdo)
                self.logger.info("Chips configured!")

            if compensate_v_drop:
                time.sleep(1.0)  # wait for applied voltage to settle
                self.logger.info("Iterative voltage compensation started...")
                # initial compensation
                self.compensate_voltage_drop_ib_stave(dvdd_set=dvdd, avdd_set=avdd, rdo=rdo)
                time.sleep(0.5)  # wait for voltage to settle
                # iterative compensation

                self.compensate_voltage_drop_ib_stave(dvdd_set=dvdd, avdd_set=avdd, rdo=rdo)
                time.sleep(0.5)  # wait for voltage to settle
                self.logger.info("Iterative voltage compensation completed...")

            rdo.powerunit_1.log_values_modules(module_list=module_list)


        except Exception as e:
            self.logger.error("Power-on failed Exception")
            self.logger.error(e)
            self.logger.info("Power off!")
            self.power_off_ib_stave()
            self.logger.error("Printing Traceback and raising")
            raise e

    def reset_all_temp_interlocks(self,
                                  internal_temperature_limit=30,
                                  external_temperature_limit=None):
        for rdo in self.rdo_list:
            self.reset_temp_interlock(internal_temperature_limit=internal_temperature_limit,
                                      external_temperature_limit=external_temperature_limit,
                                      rdo=rdo)

    def reset_temp_interlock(self,
                             internal_temperature_limit=30,
                             external_temperature_limit=None,
                             internal_temperature_low_limit=10,
                             external_temperature_low_limit=None,
                             rdo=None):
        if rdo is None:
            rdo = self.rdo

        if self.layer is LayerList.OUTER:
            pu_index_set = [1,2]
        elif self.layer is LayerList.INNER or self.layer is LayerList.MIDDLE:
            pu_index_set = [1]
        else:
            raise NotImplementedError

        pu_list = self._get_pu_list(pu_index_set, rdo=rdo)
        try:
            for pu_index, powerunit in enumerate(pu_list):
                powerunit.controller.disable_all_interlocks()
                time.sleep(0.1)  # let monitoring loop finish
                powerunit.initialize()
                if self.layer is LayerList.MIDDLE:
                    powerunit.controller.enable_temperature_interlock(internal_temperature_limit=internal_temperature_limit,
                                                                      ext1_temperature_limit=external_temperature_limit,
                                                                      ext2_temperature_limit=external_temperature_limit,
                                                                      internal_temperature_low_limit=internal_temperature_low_limit,
                                                                      ext1_temperature_low_limit=external_temperature_low_limit,
                                                                      ext2_temperature_low_limit=external_temperature_low_limit)
                else:
                    powerunit.controller.enable_temperature_interlock(internal_temperature_limit=internal_temperature_limit,
                                                                      ext1_temperature_limit=external_temperature_limit,
                                                                      internal_temperature_low_limit=internal_temperature_low_limit,
                                                                      ext1_temperature_low_limit=external_temperature_low_limit)
                assert powerunit.controller.is_temperature_interlock_enabled(interlock=powerunit.interlock)
                time.sleep(0.5)  # ADC and RTD values take some time to initialize and read properly
                powerunit.controller.reset_tripped_latch()
                powerunit.controller.log_temperatures()

        except Exception as e:
            self.logger.error("Interlock reset failed")
            self.logger.error(e)
            self.logger.error("Printing Traceback and raising")
            raise e

    def power_on_ib_stave_ORNL(self, avdd=1.92, dvdd=1.92, rdo=None):
        if rdo is None:
            rdo = self.rdo_list[0]
        self.power_on_ib_stave(avdd=avdd, dvdd=dvdd,
                               internal_temperature_limit=30,
                               external_temperature_limit=None, external_temperature_low_limit=None,
                               compensate_v_drop=False,
                               rdo=rdo)

    def power_on_ib_stave_LANL(self, avdd=1.95, dvdd=1.95, rdo=None):
        if rdo is None:
            self.power_on_all_ib_staves(avdd=avdd, dvdd=dvdd,
                                       internal_temperature_limit=45,
                                       external_temperature_limit=None,
                                       check_interlock=False)
        else:
            self.power_on_ib_stave(avdd=avdd, dvdd=dvdd,
                                   internal_temperature_limit=45,
                                   external_temperature_limit=None, external_temperature_low_limit=None,
                                   compensate_v_drop=False,
                                   rdo=rdo)

    def power_on_all_ib_staves_LANL(self, avdd=1.95, dvdd=1.95):
        self.power_on_ib_stave_LANL(avdd=avdd, dvdd=dvdd, rdo=None)

    def power_on_ib_stave_UIB(self):
        self.power_on_ib_stave(avdd=2.0, dvdd=2.0, internal_temperature_limit=30, compensate_v_drop=False, external_temperature_limit=30, external_temperature_low_limit=None)

    def log_values_ib_stave(self,
                            use_i2c=False,
                            rdo=None):
        """Reads the V/I on the modules connected to the powerunit_1
        """
        if rdo is None:
            rdo = self.rdo
        module_list=[0]
        rdo.powerunit_1.log_values_modules(module_list=module_list, use_i2c=use_i2c)

    def power_off_ib_stave(self, disable_power_interlock=False, rdo=None):
        """Powers off all the modules connected to the powerunit_1"""
        if rdo is None:
            rdo = self.rdo
        module_list=[0]
        rdo.powerunit_1.log_values_modules(module_list=module_list)
        rdo.powerunit_1.power_off_all(disable_power_interlock=disable_power_interlock)
        time.sleep(0.3)
        rdo.alpide_control.disable_dclk()
        rdo.wait(0xFFFFFF)
        time.sleep(0.3)
        rdo.powerunit_1.log_values_modules(module_list=module_list)
        self.logger.info("All off!")

    def power_on_all_ib_staves(self,
                               avdd=1.80, dvdd=1.80,
                               avdd_current=1.5, dvdd_current=1.5,
                               bb=0,
                               internal_temperature_limit=30,
                               external_temperature_limit=None,
                               link_speed=600,
                               configure_chips=True,
                               compensate_v_drop=True,
                               check_interlock=True):
        """Powers on all IB staves connected to the current testbench"""
        for rdo in self.rdo_list:
            self.logger.info(f"RU {rdo.get_gbt_channel():2}")
            try:
                self.power_on_ib_stave(avdd=avdd,dvdd=dvdd,
                                       avdd_current=avdd_current,
                                       dvdd_current=dvdd_current,
                                       bb=bb,
                                       internal_temperature_limit=internal_temperature_limit,
                                       external_temperature_limit=external_temperature_limit,
                                       check_interlock=check_interlock,
                                       link_speed=link_speed,
                                       configure_chips=configure_chips,
                                       compensate_v_drop=compensate_v_drop,
                                       rdo=rdo)
            except Exception as e:
                self.logger.error(f"RU {rdo.get_gbt_channel():2} Power-on failed Exception")
                self.logger.error(e)
                traceback.print_exc(limit=2, file=sys.stdout)

    def _load_cable_resistance_from_file(self):
        ''' Naming scheme as in configure_dacs_from_file '''
        cable_resistance_fpath = os.path.join(script_path, "../config/cable_resistances.json")

        with open(cable_resistance_fpath) as jsonfile:
            conf = json.load(jsonfile)
        r = {}
        for rdo in self.rdo_list:
            gbt_channel = rdo.get_gbt_channel()
            stave = self.get_stave_number(gbt_channel)
            layer = self.get_layer(gbt_channel)
            if stave is None or layer is None:
                raise ValueError("stave or layer not found in crate mapping")
            ru_name = f"L{layer}_{stave:02}"

            for rukey in ['LX_XX', f"L{layer}"+'_XX', ru_name]:
                if rukey not in conf.keys():
                    continue
                r[ru_name] = conf[rukey]
                self.logger.debug(f"Read cable resistance {r[ru_name]} for {ru_name}")
        if len(r.keys()) == len(self.rdo_list):
            self._cable_resistance = r
            self.logger.debug(f"Loaded cable resistance from file {cable_resistance_fpath}")
        else:
            missing = [ru_name for rdo in self.rdo_list if ru_name not in r.keys()]
            self.logger.fatal(f"Cable resistance file {cable_resistance_fpath} does not contain values for all staves! Missing staves: {missing}")
            raise KeyError(f"{missing} keys not found in cable resistance file")

    def compensate_voltage_drop_ib_stave(self, dvdd_set=None, avdd_set=None, r="from_file", rdo=None):
        """
        Perform voltage drop compensation on powerunit for readout unit "rdo".
        If dvdd_set/avdd_set is None, use the currently measured voltage to compensate for.
        If r is "from_file", read resistances from configuration file for currently selected stave,
        otherwise use the provided dictionary for the resistance values.
        """
        layer = stave = None
        if rdo is None:
            rdo = self.rdo
            _, layer, stave = rdo.identity.get_decoded_fee_id()
            self.load_powerunit_offset_file()
            offsets = self.get_powerunit_offsets(layer_number=layer, stave_number=stave)
            rdo.powerunit_1.set_voltage_offset(offsets[1]["avdd"], offsets[1]["dvdd"])

        if r == "from_file":
            self._load_cable_resistance_from_file()
            if stave is None or layer is None:
                gbt_channel = rdo.get_gbt_channel()
                stave = self.get_stave_number(gbt_channel)
                layer = self.get_layer(gbt_channel)
                if stave is None or layer is None:
                    raise ValueError("stave or layer not found in crate mapping")
            ru_name = f"L{layer}_{stave:02}"
            r = self._cable_resistance[ru_name]
        rdo.powerunit_1.compensate_voltage_drops(r=r, dvdd_set=dvdd_set, avdd_set=avdd_set, module_list=[0])

    def compensate_all_voltage_drops_ib_staves(self, dvdd_set=None, avdd_set=None, r="from_file"):
        """
        Perform voltage drop compensation on all staves connected to the current testbench
        If dvdd_set/avdd_set is None, use the currently measured voltage to compensate for.
        If r is "from_file", read resistances from configuration file for currently selected stave,
        otherwise use the provided dictionary for the resistance values.
        """
        if r == "from_file":
            self._load_cable_resistance_from_file()

        for rdo in self.rdo_list:
            gbt_channel = rdo.get_gbt_channel()
            self.logger.info(f"RU {gbt_channel:02}")
            if r == "from_file":
                stave = self.get_stave_number(gbt_channel)
                layer = self.get_layer(gbt_channel)
                if stave is None or layer is None:
                    raise ValueError("stave or layer not found in crate mapping")
                ru_name = f"L{layer}_{stave:02}"
                r = self._cable_resistance[ru_name]
            rdo.powerunit_1.compensate_voltage_drops(r=r, dvdd_set=dvdd_set, avdd_set=avdd_set, module_list=[0])

    def log_values_ib_staves(self, use_i2c=False):
        """log the power values for for each RU"""
        for rdo in self.rdo_list:
            self.logger.info(f"RU {rdo.get_gbt_channel():2}")
            self.log_values_ib_stave(rdo=rdo, use_i2c=use_i2c)

    def power_off_all_ib_staves(self, disable_power_interlock=False):
        """Powers off all the modules connected to the powerunit_1 for each RU"""
        for rdo in self.rdo_list:
            self.logger.info(f"RU {rdo.get_gbt_channel():2}")
            self.power_off_ib_stave(disable_power_interlock,
                                    rdo=rdo)


    def emergency_off(self):
        """ Powers off all the modules connected to the RUs in this sub-rack"""
        if self.layer is LayerList.OUTER:
            pu_index_set = [1,2]
        elif self.layer is LayerList.INNER or self.layer is LayerList.MIDDLE:
            pu_index_set = [1]
        else:
            raise NotImplementedError

        for rdo in self.rdo_list:
            pu_list = self._get_pu_list(pu_index_set, rdo=rdo)
            try:
                for pu_index, powerunit in enumerate(pu_list):
                    powerunit.power_off_all()
                    powerunit.controller.disable_power_interlock()
                    powerunit.controller.reset_tripped_latch()
            except:
                pass

        for rdo in self.rdo_list:
            pu_list = self._get_pu_list(pu_index_set, rdo=rdo)
            try:
                for pu_index, powerunit in enumerate(pu_list):
                    powerunit.log_values_modules(module_list=list(range(8)))
            except:
                pass

        self.logger.info("Emergency off completed!")

    def power_off_all_chips(self):
        """Powers off all the modules connected to the powerunit_1"""
        self.rdo.powerunit_1.log_values_modules(module_list=list(range(8)))
        self.rdo.powerunit_1.power_off_all()
        self.rdo.wait(0xFFFFFF)
        time.sleep(1)
        self.rdo.powerunit_1.log_values_modules(module_list=list(range(8)))
        self.logger.info("All off!")


    def test_chips_continuous(self, nrfirst=0, nrlast=8):
        """Perform a chip test on chips [first,last]"""
        # reads once to set the correct connector to read from
        PRINT_INTERVAL = 10
        try:
            self.chips[0].read_reg(0)
        except Exception:
            pass
        min_tests = 10
        self.logger.info("Test Chips %d to %d",
                         nrfirst,
                         nrlast)
        total_time = 0
        total_errors = {chipid: 0 for chipid in range(nrfirst, nrlast+1)}

        # record sequence
        self.comm_rdo.start_recording()
        errors, elapsed_time = self.test_chips(nrfirst=nrfirst, nrlast=nrlast, nrtests=min_tests, verbose=False)
        total_time += elapsed_time
        total_errors = {chipid: total_errors[chipid]+errors[chipid] for chipid in total_errors.keys()}
        sequence = self.comm_rdo.stop_recording()

        start_time = last_read = time.time()
        try:

            while True:
                self.comm_rdo.load_sequence(sequence)
                self.comm_rdo.prefetch()
                errors, elapsed_time = self.test_chips(nrfirst=nrfirst, nrlast=nrlast, nrtests=min_tests, verbose=False)
                total_time += elapsed_time
                total_errors = {chipid: total_errors[chipid]+errors[chipid] for chipid in total_errors.keys()}
                if(time.time() - last_read) > PRINT_INTERVAL:
                    last_read = time.time()
                    self.logger.info("Total errors {0}, in {1:.2f}s".format(total_errors, last_read-start_time))
                    if sum([errors[chipid] for chipid in total_errors.keys()]) > 0:
                        self.tg_notification("Errors detected: {0} at {1:.2f} s. Execution paused".format(total_errors, last_read-start_time))
                        input("press a key to continue...")

        except KeyboardInterrupt:
            self.logger.info("Ctrl-c")

        for chipid in range(nrfirst, nrlast+1):
            self.logger.info("Chipid %d, Errors: %d", chipid, total_errors[chipid])
        self.logger.info("Elapsed time {0:.3f} s".format(time.time() - start_time))

    def test_dclk_phases(self, nrtests=1000, connector=None, manchester_tx_en=False):
        BASE_CONNECTOR = 4
        FIRST = 0
        LAST = 8
        if connector is None:
            connector = BASE_CONNECTOR
        else:
            assert connector in range(5)
        if manchester_tx_en:
            self.rdo.alpide_control.enable_manchester_tx()
        phase_list = self.rdo.alpide_control.phase_dict.keys()
        errors_dict = {}
        initial_phase = self.rdo.alpide_control.get_dclk_parallel(index=connector)
        total_time = 0
        self.rdo.alpide_control.logger.setLevel(logging.CRITICAL)
        self.logger.setLevel(logging.CRITICAL)
        for phase in phase_list:
            self.rdo.alpide_control.set_dclk_parallel(index=connector, phase=phase)
            self.setup_sensors()
            errors, elapsed_time = self.test_chips_fast(nrfirst=FIRST, nrlast=LAST, nrtests=nrtests)
            errors_dict[phase] = errors
            total_time += elapsed_time
        self.rdo.alpide_control.set_dclk_parallel(index=connector, phase=initial_phase)
        if manchester_tx_en:
            self.rdo.alpide_control.disable_manchester_tx()
        self.rdo.alpide_control.logger.setLevel(logging.INFO)
        self.logger.setLevel(logging.INFO)
        self.setup_sensors()
        for phase in errors_dict.keys():
            self.logger.info("Phase \t{0}\ttotal errors \t{1}".format(phase, sum(errors_dict[phase].values())))
        return errors_dict, total_time

    def test_prbs(self, runtime=10):
        self._test_prbs(frontend=self.rdo.gth, runtime=runtime)

    def test_prbs_gpio(self, runtime=10):
        self._test_prbs(frontend=self.rdo.gpio, runtime=runtime)

    def _test_prbs(self, frontend, runtime=10):
        frontend.enable_data(False)
        for ch in self.chips:
            ch.propagate_prbs(PrbsRate=0)

        frontend.enable_prbs(enable=True, commitTransaction=True)
        frontend.reset_prbs_counter()

        self.logger.info("Chip + Board setup for PRBS run.")
        self.logger.info("Wait for %d s", runtime)
        time.sleep(runtime)

        prbs_errors = frontend.read_prbs_counter(self)
        all_errors = 0
        for cnt, link in zip(prbs_errors, frontend.transceivers):
            if cnt > 0:
                self.logger.error(
                    "Link %d: %d PRBS Errors observed", link, cnt)
            all_errors += cnt
        self.logger.info("PRBS run finished. Total Errors: %d", all_errors)

        for ch in self.chips:
            ch.propagate_data()

    def _test_readout_nocheck(self, dpmon, nr_triggers=10, dump_data=False, trigger_wait=1000):
        dpmon.reset_counters()

        self.rdo.alpide_control.reset_counters()

        time.sleep(0.1)

        self.logger.info(
            "Counters reset. Send %d triggers over CRU", nr_triggers)
        for i in range(nr_triggers):
            self.cru.send_trigger(orbit=i)
            self.cru.wait(trigger_wait)
        self.logger.info(
            "All Triggers sent. Start checking counters + readback")
        events_received = False
        retries = 0

        while not events_received and retries < 20:
            event_counters = dpmon.read_counter(None, counter="EVENT_COUNT")
            if not isinstance(event_counters, collections.abc.Iterable):
                event_counters = [event_counters]

            events_received = all(
                [trig == nr_triggers for trig in event_counters])
            retries += 1
            if not events_received:
                time.sleep(0.25)
        counters = dpmon.read_all_counters()
        raise NotImplementedError("Update to new readout!")
        # TODO: update
        # zero_counters = []
        # zero_counters = [
        #     "DECODE_ERROR_COUNT",
        #     "EVENT_ERROR_COUNT",
        #     "EMPTY_REGION_COUNT",
        #     "BUSY_COUNT",
        #     "BUSY_VIOLATION_COUNT",
        #     "DOUBLE_BUSY_ON_COUNT",
        #     "DOUBLE_BUSY_OFF_COUNT",
        #     "LANE_FIFO_FULL_COUNT",
        #     "LANE_FIFO_OVERFLOW_COUNT",
        #     "CPLL_LOCK_LOSS_COUNT",
        #     #"CDR_LOCK_LOSS_COUNT", #TODO MB: Investigate source of CDR lock loss. Deactivate for now
        #     "ALIGNED_LOSS_COUNT",
        #     "REALIGNED_COUNT",
        #     "ELASTIC_BUF_OVERFLOW_COUNT",
        #     "ELASTIC_BUF_UNDERFLOW_COUNT",
        #     "LANE_PACKAGER_LANE_TIMEOUT_COUNT",
        #     "GBT_PACKER_LANE_TIMEOUT_COUNT",
        #     "GBT_PACKER_LANE_START_VIOLATION_COUNT"
        # ]
        for lane,r in enumerate(counters):
            for name, val in counters[lane].items():
                expected_val = 0
                any_val = False
                raise NotImplementedError("Update to new readout!")
                # TODO: update
                # if name == 'EVENT_COUNT':
                #     expected_val = nr_triggers
                # elif name not in zero_counters:
                #     any_val = True
                if not any_val and val != expected_val:
                    self.logger.error("Lane %d, counter '%s': Counter value '%d' not as expected (%d)",
                                      lane, name, val, expected_val)
                #self.logger.info("Lane %d, counter '%s': value: %d",lane,name,val)

        if dump_data:
            self.logger.info(pprint.pformat(counters))

        self.logger.info("Events received: %r", event_counters)
        self.logger.info("Event counters read and checked.")

        alpide_control_counters = self.rdo.alpide_control.get_counters()
        self.logger.info(alpide_control_counters)
        if alpide_control_counters['TRIGGER_SENT'] != nr_triggers:
            self.logger.error(
                "alpide_control: Not all Triggers sent: {0}/{1}".format(alpide_control_counters['TRIGGER_SENT'], nr_triggers))

    def _test_readout(self, dpmon, nr_triggers=10, dump_data=False):
        self._test_readout_nocheck(dpmon, nr_triggers, dump_data)
        return self.check_event_readout(nr_triggers, nr_triggers, dpmon.lanes, dump_data)

    def test_readout(self, nr_triggers=10, dump_data=False):
        return self._test_readout(self.rdo.datapath_monitor_ib, nr_triggers, dump_data)

    def test_readout_gpio(self, nr_triggers=10, dump_data=False):
        return self._test_readout(self.rdo.datapath_monitor_ob, nr_triggers, dump_data)

    def test_usb_performance_read(self,
                                  packets_per_train=1000,
                                  nr_trains=1000,
                                  test_cru=True,
                                  test_rdo=True):
        if self.cru_type is CruType.RUv0:
            self.logger.info("Test USB Performance: Read (usb_comm: %r)", self.use_usb_comm)
            assert test_cru or test_rdo, "At least CRU or RDO must be set to True"
            if test_cru and test_rdo:
                packet_range = range(packets_per_train//2)
            else:
                packet_range = range(packets_per_train)
            start = time.time()
            for i in range(nr_trains):
                for j in packet_range:
                    if test_cru:
                        self.cru.read(0x41,1,False)
                    if test_rdo:
                        self.rdo.read(1,1,False)
                self.cru.flush()
                results = self.cru.read_all()
                if len(results) != packets_per_train:
                    self.logger.error("Train %d: Not all packets received: %d/%d",i,len(results),packets_per_train)
            end = time.time()
            duration = end-start
            mbit_sent = packets_per_train*nr_trains*32/(1024*1024)
            data_rate = mbit_sent/duration
            self.logger.info("Test finished in %.4f seconds. Raw data rate (Send/Receive): %.4f Mbps", duration,data_rate)

            self.logger.info("Test USB Performance done")

            return mbit_sent, duration
        else:
            raise NotImplementedError

    def test_usb_performance_write(self, packets_per_train=1000, nr_trains=1000, test_cru=True, test_rdo=True):
        if self.cru_type is CruType.RUv0:
            self.logger.info("Test USB Performance: Write")
            assert test_cru or test_rdo, "At least CRU or RDO must be set to True"
            assert test_rdo and self.use_rdo_usb, "Not supported"
            if test_cru and test_rdo:
                packet_range = range(packets_per_train//2 - 2)
            else:
                packet_range = range(packets_per_train - 1)
            start = time.time()
            for i in range(nr_trains):
                for _ in packet_range:
                    if test_cru:
                        self.cru.master_monitor.write(0,False)
                    if test_rdo:
                        self.rdo.master_monitor.write(0,False)
                if test_cru:
                    self.cru.read(0x41,1,False)
                if test_rdo:
                    self.rdo.read(1,1,False)
                self.cru.flush()
                results = self.cru.read_all()
                if len(results) != test_rdo + test_cru:
                    self.logger.error("Train %d: Read synchronisation not received: %d/%d",i,len(results),packets_per_train)
            end = time.time()
            duration = end-start
            mbit_sent = packets_per_train*nr_trains*32/(1024*1024)
            data_rate = mbit_sent/duration
            self.logger.info("Test finished in %.4f seconds. Raw data rate (Send/Receive): %.4f Mbps", duration,data_rate)

            self.logger.info("Test USB Performance done")

            return mbit_sent, duration
        else:
            raise NotImplementedError

    def check_event_readout(self, nr_events, nr_empty_triggers, lanes, verbose=False, raw_data_file=None):
        return events.check_event_readout(self.cru, nr_events, nr_empty_triggers, lanes, verbose=verbose,
                                          raw_data_file=raw_data_file)

    def test_usb_endurance(self):
        if self.cru_type is CruType.RUv0:
            TEST_PER_RUN = 30
            PRINT_INTERVAL = 10
            testlist_cru = [(65,0),(65,1)]*75
            testlist_rdo = [(3,i) for i in range(150)]
            start = time.time()
            total_transactions_rdo = 0
            total_transactions_cru = 0
            last_read = start
            try:
                while True:
                    for _ in range(TEST_PER_RUN):
                        for addr_cru,addr_rdo in zip(testlist_cru,testlist_rdo):
                            self.cru.read(addr_cru[0],addr_cru[1],False)
                            self.cru.read(addr_rdo[0],addr_rdo[1],False)
                        self.cru.flush()

                    results = self.cru.comm.read_results()
                    result_set = {}
                    for addr,data in results:
                        if addr not in result_set:
                            result_set[addr] = 0
                        result_set[addr] += 1
                    # check nr of transactions
                    for mod,addr in testlist_cru[0:2]:
                        full_addr = (mod<<8)|addr
                        total_transactions_cru += result_set[full_addr]
                        assert result_set[full_addr] == 75*TEST_PER_RUN, "Address {0:04X}: nr. Result mismatch".format(full_addr)
                    for mod,addr in testlist_rdo:
                        full_addr = (mod<<8)|addr
                        total_transactions_rdo += result_set[full_addr]
                        assert result_set[full_addr] == TEST_PER_RUN, "Address {0:04X}: nr. Result mismatch".format(full_addr)

                    if(time.time() - last_read) > PRINT_INTERVAL:
                        last_read = time.time()
                        self.logger.info("Total Transactions: {0:.3e} RDO, {1:.3e} CRU. Runtime: {2:.2f}s".format(total_transactions_rdo,
                                                                                           total_transactions_cru,
                                                                                           last_read-start))
            except Exception as e:
                self.logger.info("Test stopped with %s", e)
                self.logger.info("Total Transactions: {0:.3e} RDO, {1:.3e} CRU. Runtime: {2:.2f}s".format(total_transactions_rdo,
                                                                                              total_transactions_cru,
                                                                                              last_read-start))
        else:
            raise NotImplementedError

    def test_usb_rdo_read(self):
        if self.cru_type == CruType.RUv0:
            TEST_PER_RUN = 3000
            PRINT_INTERVAL = 10
            testlist_rdo = [(2,3), (4,1), (4,2)]
    #        for i in range(2,0xC):
    #            testlist_rdo.append( (8,i) )
    #            testlist_rdo.append( (9,i) )
            start = time.time()
            total_transactions_rdo = 0
            total_transactions_cru = 0
            last_read = start
            WRITE_VAL = 0xAAAA

            data_mismatch = collections.defaultdict(int)

            for mod,addr in testlist_rdo:
                self.cru.write(mod,addr,WRITE_VAL)

            try:
                while True:
                    for i in range(TEST_PER_RUN):
                        for addr_rdo in testlist_rdo:
                            self.cru.read(addr_rdo[0],addr_rdo[1],False)
                        self.cru.flush()

                    results = self.cru.comm.read_results()
                    result_set = collections.defaultdict(int)
                    for addr,data in results:
                        result_set[addr] += 1
                        if data != WRITE_VAL:
                            data_mismatch[addr] += 1
                            self.logger.info("Address %04x, Mismatch. Value read: %04x",addr,data)
                    # check nr of transactions
                    for mod,addr in testlist_rdo:
                        full_addr = (mod<<8)|addr
                        total_transactions_rdo += result_set[full_addr]
                        assert result_set[full_addr] == TEST_PER_RUN, "Address {0:04X}: nr. Result mismatch".format(full_addr)

                    if(time.time() - last_read) > PRINT_INTERVAL:
                        last_read = time.time()
                        self.logger.info("Total Transactions: {0:.3e} RDO, {1:.3e} CRU. Runtime: {2:.2f}s".format(total_transactions_rdo,
                                                                                           total_transactions_cru,
                                                                                           last_read-start))
                        for addr, mismatch in data_mismatch.items():
                            if mismatch > 0:
                                self.logger.info("Address %04x, Mismatch count: %d",addr,mismatch)
            except Exception as e:
                self.logger.info("Test stopped with %s", e)
                self.logger.info("Total Transactions: {0:.3e} RDO, {1:.3e} CRU. Runtime: {2:.2f}s".format(total_transactions_rdo,
                                                                                              total_transactions_cru,
                                                                                              last_read-start))
        else:
            raise NotImplementedError

    def test_cru_parallel_sc(self, num_swt_tests=200000, num_sca_tests=10000):
        self.logger.info("Starting CRU Parallel Slow Control SWT/SCA test - using all RUs in crate")
        self.cru.initialize()
        threads = list()
        errors = [None] * (len(self.rdo_list)*2)
        for index, rdo in enumerate(self.rdo_list):
            thread = threading.Thread(target=self._test_cru_parallel_sc_sca, args=(rdo.pa3, num_sca_tests, errors, index*2))
            threads.append(thread)
            thread = threading.Thread(target=self._test_cru_parallel_sc_swt, args=(rdo, num_swt_tests, errors, (index*2)+1))
            threads.append(thread)
        for thread in threads:
            thread.start()
        while threads[0].is_alive():
            self.logger.info("Test still running...")
            time.sleep(10)
        for thread in threads:
            thread.join()
        errors = sum(errors)
        msg = f"CRU Parallel Slow Control SWT/SCA test, finished with {errors} errors. Error rate: {errors}/{(num_swt_tests+num_sca_tests)*len(self.rdo_list)} = {errors/((num_swt_tests+num_sca_tests)*len(self.rdo_list)*2)}"
        if errors > 0:
            self.logger.error(msg)
        else:
            self.logger.info(msg)

    def test_cru_parallel_sc_sca(self, num_tests=100000):
        self.logger.info("Starting CRU Parallel Slow Control SCA test - using all RUs in crate")
        self.cru.initialize()
        threads = list()
        errors = [None] * len(self.rdo_list)
        for index, rdo in enumerate(self.rdo_list):
            thread = threading.Thread(target=self._test_cru_parallel_sc_sca, args=(rdo.pa3, num_tests, errors, index))
            threads.append(thread)
        for thread in threads:
            thread.start()
        while threads[0].is_alive():
            self.logger.info("Test still running...")
            time.sleep(10)
        for thread in threads:
            thread.join()
        errors = sum(errors)
        msg = f"CRU Parallel Slow Control SCA test, finished with {errors} errors. Error rate: {errors}/{num_tests*len(self.rdo_list)} = {errors/num_tests*len(self.rdo_list)}"
        if errors > 0:
            self.logger.error(msg)
        else:
            self.logger.info(msg)

    def _test_cru_parallel_sc_sca(self, pa3, num_tests, errors, index):
        self.logger.info(f"Starting SCA test thread with channel {pa3.sca.comm.get_gbt_channel()}")
        errors[index] = 0
        for i in range(num_tests):
            rand_value = random.randint(0, 0xff)
            pa3.write_reg(Pa3Register.FLASH_PATTERN, rand_value)
            if pa3.read_reg(Pa3Register.FLASH_PATTERN) != rand_value:
                errors[index] = errors[index]+1
        self.logger.info(f"Finished SCA test thread with channel {pa3.sca.comm.get_gbt_channel()}")
        if errors[index] > 0:
            self.logger.warning(f"SCA thread {pa3.sca.comm.get_gbt_channel()} finished tests with {errors[index]} errors")

    def test_cru_parallel_sc_swt(self, num_tests=1000000):
        self.logger.info("Starting CRU Parallel Slow Control SWT test - using all RUs in crate")
        self.cru.initialize()
        threads = list()
        errors = [None] * len(self.rdo_list)
        for index, rdo in enumerate(self.rdo_list):
            thread = threading.Thread(target=self._test_cru_parallel_sc_swt, args=(rdo, num_tests, errors, index))
            threads.append(thread)
        for thread in threads:
            thread.start()
        while threads[0].is_alive():
            self.logger.info("Test still running...")
            time.sleep(10)
        for thread in threads:
            thread.join()
        errors = sum(errors)
        msg = f"CRU Parallel Slow Control SWT test, finished with {errors} errors. Error rate: {errors}/{num_tests*len(self.rdo_list)} = {errors/num_tests*len(self.rdo_list)}"
        if errors > 0:
            self.logger.error(msg)
        else:
            self.logger.info(msg)

    def _test_cru_parallel_sc_swt(self, rdo, num_tests, errors, index):
        self.logger.info(f"Starting SWT test thread with channel {rdo.get_gbt_channel()}")
        errors[index] = 0
        for i in range(num_tests):
            rand_value = random.randint(0, 0xffff)
            rdo.gbt_packer.set_timeout_to_start(rand_value)
            if rdo.gbt_packer.get_timeout_to_start() != rand_value:
                errors[index] = errors[index]+1
        self.logger.info(f"Finished SWT test thread with channel {rdo.get_gbt_channel()}")
        if errors[index] > 0:
            self.logger.warning(f"SWT thread {rdo.get_gbt_channel()} finished tests with {errors[index]} errors")

    def test_rdo_uptime_stability(self, rdo=None, test_sec=3600):
        assert test_sec < (2**48)-(1.6e9), "test_sec must be lower than max value of uptime, minus safety factor of 10 secs"
        self.initialize_boards()
        if rdo is None:
            rdo = self.rdo_list[0]
        test_start = time.time()
        time_since_start = time.time() - test_start
        self.rdo.sca.reset_xcku()
        uptime = self.rdo.identity.get_time_since_reset()
        num_errors = 0
        while time_since_start < test_sec:
            time.sleep(0.6)
            time_since_start = time.time() - test_start
            uptime_new = self.rdo.identity.get_time_since_reset()
            if int(time_since_start) % 120 == 0:
                print(uptime_new)
            if uptime >= uptime_new:
                num_errors += 1
                self.logger.warning(f"Prev uptime {uptime} is larger or equal to new uptime {uptime_new}")
            uptime = uptime_new
        if num_errors > 0:
            self.logger.error(f"Uptime stability test FAILED\tnum error = {num_errors}")
        else:
            self.logger.info(f"Uptime stability test SUCCEEDED")



    def test_pa3_read_error_rate(self):
        TEST_PER_RUN = 10
        PRINT_INTERVAL = 10
        start = time.time()
        total_tests = 0
        failed_tests = 0
        wrong_reads = 0
        last_read = start
        self.logger.setLevel('CRITICAL')
        while True:
            try:
                for _ in range(TEST_PER_RUN):
                    version = self.rdo.pa3.version()
                    total_tests += 1
                    if version != 0xA209:
                        wrong_reads += 1
                        print(hex(version))

                if(time.time() - last_read) > PRINT_INTERVAL:
                    last_read = time.time()
                    self.logger.setLevel('INFO')
                    self.logger.info("Number of tests failed: %d/%d, %d/%d wrong_read", failed_tests, total_tests, wrong_reads, total_tests)
                    self.logger.setLevel('CRITICAL')
            except KeyboardInterrupt as ki:
                self.logger.setLevel('INFO')
                self.logger.info("Test stopped with %s", ki)
                self.logger.info("Number of tests failed: %d/%d, %d/%d wrong_read", failed_tests, total_tests, wrong_reads, total_tests)
                self.logger.info("{0:0.2f} reads per second".format(2*total_tests/(time.time()-start)))
                self.logger.info("Average read time {0:e}s".format((time.time()-start)/(2*total_tests)))
                break
            except Exception as ae:
                self.logger.debug(ae)
                failed_tests += 1

    def test_pa3_write_error_rate(self):
        TEST_PER_RUN = 10
        PRINT_INTERVAL = 10
        start = time.time()
        total_tests = 0
        failed_tests = 0
        last_read = start
        self.logger.setLevel('CRITICAL')
        while True:
            try:
                for _ in range(TEST_PER_RUN):
                    self.rdo.pa3.config_controller.set_cc_command_register(CcCmdOpcode.INIT_CONFIG, execute=0)
                    total_tests += 1

                if(time.time() - last_read) > PRINT_INTERVAL:
                    last_read = time.time()
                    self.logger.setLevel('INFO')
                    self.logger.info("Number of tests failed: %d/%d", failed_tests, total_tests)
                    self.logger.setLevel('CRITICAL')
            except KeyboardInterrupt as ki:
                self.logger.setLevel('INFO')
                self.logger.info("Test stopped with %s", ki)
                self.logger.info("Number of tests failed: %d/%d", failed_tests, total_tests)
                self.logger.info("{0:0.2f} reads per second".format(2*total_tests/(time.time()-start)))
                self.logger.info("Average read time {0:e}s".format((time.time()-start)/(2*total_tests)))

                break
            except Exception as ae:
                self.logger.debug(ae)
                failed_tests += 1

    def test_pa3_dump_config(self):
        PRINT_INTERVAL = 10
        start = time.time()
        total_tests = 0
        failed_tests = 0
        last_read = start
        self.logger.setLevel('CRITICAL')
        while True:
            total_tests += 1
            try:
                self.rdo.pa3.dump_config()

            except KeyboardInterrupt as ki:
                self.logger.setLevel('INFO')
                self.logger.info("Test stopped with %s", ki)
                self.logger.info("{0:0.2f} reads per second".format(total_tests/(time.time()-start)))
                self.logger.info("Average read time {0:e}s".format((time.time()-start)/(total_tests)))
                self.logger.info("Number of tests failed: %d/%d", failed_tests, total_tests)

                break
            except Exception as ae:
                self.logger.info(ae)
                failed_tests += 1
            if(time.time() - last_read) > PRINT_INTERVAL:
                last_read = time.time()
                self.logger.setLevel('INFO')
                self.logger.info("Number of tests failed: %d/%d", failed_tests, total_tests)
                self.logger.setLevel('CRITICAL')

    def test_pa3_dump_config_2_i2c(self):
        PRINT_INTERVAL = 10
        start = time.time()
        total_tests = 0
        failed_tests_1 = 0
        failed_tests_2 = 0
        last_read = start
        self.logger.setLevel('CRITICAL')
        cur_reg = 0
        failed_regs_1 = []
        failed_regs_2 = []
        while True:
            total_tests += 1
            try:
                self.rdo.pa3.set_i2c_channel(gbt_sca.ScaChannel.I2C0)
                for register in Pa3Register:
                    cur_reg = register
                    self.rdo.pa3.read_reg(address=register)

            except KeyboardInterrupt as ki:
                self.logger.setLevel('INFO')
                self.logger.info("Test stopped with %s", ki)
                self.logger.info("{0:0.2f} reads per second".format(total_tests/(time.time()-start)))
                self.logger.info("Average read time {0:e}s".format((time.time()-start)/(total_tests)))
                self.logger.info("Number of tests failed on i2c0: %d/%d", failed_tests_1, total_tests)
                self.logger.info("Number of tests failed on i2c5: %d/%d", failed_tests_2, total_tests)
                self.logger.info('Failing regs i2c0:')
                self.logger.info('\n'.join(starmap('{}: {}'.format, enumerate(failed_regs_1))))
                self.logger.info('Failing regs i2c5:')
                self.logger.info('\n'.join(starmap('{}: {}'.format, enumerate(failed_regs_2))))

                break
            except Exception as ae:
                self.logger.info(ae)
                failed_tests_1 += 1
                failed_regs_1.append(cur_reg)

            try:
                self.rdo.pa3.set_i2c_channel(gbt_sca.ScaChannel.I2C5)
                for register in Pa3Register:
                    cur_reg = register
                    self.rdo.pa3.read_reg(address=register)

            except KeyboardInterrupt as ki:
                self.logger.setLevel('INFO')
                self.logger.info("Test stopped with %s", ki)
                self.logger.info("{0:0.2f} reads per second".format(total_tests/(time.time()-start)))
                self.logger.info("Average read time {0:e}s".format((time.time()-start)/(total_tests)))
                self.logger.info("Number of tests failed on i2c0: %d/%d", failed_tests_1, total_tests)
                self.logger.info("Number of tests failed on i2c5: %d/%d", failed_tests_2, total_tests)
                self.logger.info('Failing regs i2c0:')
                self.logger.info('\n'.join(starmap('{}: {}'.format, enumerate(failed_regs_1))))
                self.logger.info('Failing regs i2c5:')
                self.logger.info('\n'.join(starmap('{}: {}'.format, enumerate(failed_regs_2))))

                break
            except Exception as ae:
                self.logger.info(ae)
                failed_tests_2 += 1
                failed_regs_2.append(cur_reg)

            if(time.time() - last_read) > PRINT_INTERVAL:
                last_read = time.time()
                self.logger.setLevel('INFO')
                self.logger.info("Number of tests failed on i2c0: %d/%d", failed_tests_1, total_tests)
                self.logger.info("Number of tests failed on i2c5: %d/%d", failed_tests_2, total_tests)
                self.logger.setLevel('CRITICAL')

    def test_sca_endurance(self):
        TEST_PER_RUN = 30
        PRINT_INTERVAL = 10
        start = time.time()
        total_tests = 0
        last_read = start
        try:
            while True:
                for _ in range(TEST_PER_RUN):
                    _ = self.rdo.sca.read_adcs()
                    _ = self.rdo.sca.read_gpio()
                    total_tests += 1

                if(time.time() - last_read) > PRINT_INTERVAL:
                    last_read = time.time()
                    self.logger.info("Number of Tests: %d", total_tests)
        except Exception as e:
            self.logger.info("Test stopped with %s", e)
            self.logger.info("Number of Tests: %d", total_tests)

    def setup_its_readout_test(self):
        self.cru.ttc.configure_emulator(heartbeat_period_bc=3564,
                                        heartbeat_wrap_value=8,
                                        heartbeat_keep=6,
                                        heartbeat_drop=2,
                                        periodic_trigger_period_bc=8)

        self.cru.bsp.disable_run()

        self.cru.dwrapper.configure_for_readout(data_link_list=self.data_link_list)

    def calibrate_gbtx2_idelay(self, rdo=0, time_btw_check_sec=0.5, range_start=0, range_stop=512):
        self.logger.info("Starting GBTx2 Idelay Calibration")
        rdo = self.rdo_list[rdo]
        prev_lol = 0
        results = 512*[0]
        for i in range(range_start,range_stop):
            if i % 20 == 0:
                self.logger.info(f"Checking idelay: {i}")

            rdo.gbtx2_controller.set_idelay(idelay_all=i)
            rdo._trigger_handler_monitor.reset_all_counters()
            prev_lol = rdo._trigger_handler_monitor.read_counters()['LOL_TIMEBASE']

            time.sleep(time_btw_check_sec)

            if prev_lol == rdo._trigger_handler_monitor.read_counters()['LOL_TIMEBASE'] and rdo.trigger_handler.is_timebase_synced():
                results[i] += 1

        if all(x == 0 for x in results):
            self.logger.error("Calibration FAILED: No settings could get signal to lock!")
            return False

        r = max((list(y) for (x,y) in itertools.groupby((enumerate(results)),operator.itemgetter(1)) if x == len(self.rdo_list)), key=len)
        low = r[0][0]
        high = r[-1][0]
        optimal = int((high - low)/2 + low)
        self.logger.info(f"Longest sequence of OK idelay is between {low} and {high}")
        self.logger.info(f"Optimal idelay value is {optimal}")


        self.logger.info(f"Setting optimal idelay value")
        rdo.gbtx2_controller.set_idelay(idelay_all=optimal)
        time.sleep(time_btw_check_sec)
        if rdo.trigger_handler.is_timebase_synced():
            self.logger.info(f"Calibration DONE with IDELAY: {optimal}")
            return True
        else:
            self.logger.error("Calibration FAILED: Timebase is not synced after setting optimal value")
            return False


    def calibrate_gbtx01_bitslips(self):
        assert self.use_rdo_usb, "USB connection is required to run the test"
        comm_usb = usb_communication.PyUsbComm(serialNr=USB_SERIAL_RDO)
        rdo_usb = ru_board.Xcku(comm_usb,
                                self.cru,
                                ru_main_revision=self.ru_main_revision,
                                ru_minor_revision=self.ru_minor_revision,
                                transition_board_version=self.ru_transition_board_version,
                                power_board_version=self.power_board_version,
                                power_board_filter_50Hz_ac_power_mains_frequency=self.power_board_filter_50hz_ac_power_mains_frequency,
                                powerunit_1_offset_avdd=None,
                                powerunit_1_offset_dvdd=None,
                                powerunit_2_offset_avdd=None,
                                powerunit_2_offset_dvdd=None,
                                layer=self.layer,
                                powerunit_resistance_offset_pt100=self.powerunit_resistance_offset_pt100)
        comm_gbt = self.comm_ruv0_cru
        comm_gbt.max_retries = 1
        rdo_gbt = ru_board.Xcku(comm_gbt,
                                self.cru,
                                ru_main_revision=self.ru_main_revision,
                                ru_minor_revision=self.ru_minor_revision,
                                transition_board_version=self.ru_transition_board_version,
                                power_board_version=self.power_board_version,
                                power_board_filter_50Hz_ac_power_mains_frequency=self.power_board_filter_50hz_ac_power_mains_frequency,
                                powerunit_1_offset_avdd=None,
                                powerunit_1_offset_dvdd=None,
                                powerunit_2_offset_avdd=None,
                                powerunit_2_offset_dvdd=None,
                                layer=self.layer,
                                powerunit_resistance_offset_pt100=self.powerunit_resistance_offset_pt100)
        githash = rdo_usb.identity.get_git_hash()
        for bitslip_rx in range(8):
            rdo_usb.gbtx01_controller.set_bitslip_rx(bitslip_rx)
            for bitslip_tx in range(8):
                rdo_usb.gbtx01_controller.set_bitslip_tx(bitslip_tx)
                rdo_usb.wait(100)
                self.logger.setLevel(logging.FATAL)
                try:
                    githash_read = rdo_gbt.identity.get_git_hash()
                    assert githash_read == githash, "githash mismatch expected {0} read {1}".format(githash,githash_read)
                    self.logger.info("RX {0}\tTX {1} OK".format(bitslip_rx, bitslip_tx))
                except:
                    self.logger.info("RX {0}\tTX {1} FAILED".format(bitslip_rx, bitslip_tx))
                finally:
                    self.logger.setLevel(logging.INFO)

    def calibrate_gbtx_idelay(self, gbtx_number):
        assert self.use_rdo_usb, "USB connection is required to run the test"
        assert gbtx_number in [0,2], "Only GBTx0 and GBTx2 can be calibrated"
        self.cru.comm.discardall_dp1(20)
        self.rdo.comm.discardall_dp1(20)
        # since we are sending random patterns,
        # make sure they are not interpreted as wishbone transactions
        self.cru.set_gbtx_forward_to_usb(0)
        self.cru.set_test_pattern(0)
        self.rdo.i2c_gbtx.gbtx_config(os.path.join(script_path, "../../modules/gbt/software/GBTx_configs/GBTx0_Config_RUv2.xml"), 0)
        self.rdo.i2c_gbtx.gbtx_config(os.path.join(script_path, "../../modules/gbt/software/GBTx_configs/GBTx2_Config_RUv2.xml"), 2)
        time.sleep(1)
        self.rdo.i2c_gbtx.gbtx_config(os.path.join(script_path, "../../modules/gbt/software/GBTx_configs/GBTx1_Config_RUv2.xml"), 1)
        time.sleep(1)
        # make sure GBTx connected to CRU
        if gbtx_number == 0:
            assert self.rdo.i2c_gbtx.read_gbtx_register(427, 0) == 15
        else:
            assert self.rdo.i2c_gbtx.read_gbtx_register(427, 2) == 15

        # set loopback mode
        self.rdo.gbtx01_controller.set_tx_pattern(3)
        self.rdo.gbtx2_controller.set_tx_pattern(3)

        # set PRBS pattern mode (requires branch JS_add_prbs_pattern in CRU emulator)
        self.cru.set_test_pattern(7)
        self.cru.reset_error_flags()
        st_flags = self.cru.get_status_flags()
        self.logger.info(st_flags)
        assert (st_flags['GbtRxDataErrorseenFlag'] == 0) and (st_flags['GbtRxReadyLostFlag'] == 0)
        # now read the original IDELAY tab (count) values
        if gbtx_number == 0:
            idelay = self.rdo.gbtx01_controller.get_idelay()
        else:
            idelay = self.rdo.gbtx2_controller.get_idelay()

        new_idelay = idelay.copy()
        # vary those until the error flags turn on
        for i in range(10):
            for j in range(idelay[i]):
                new_idelay[i] = idelay[i] - j
                if gbtx_number == 0:
                    self.rdo.gbtx01_controller.set_idelay(new_idelay)
                else:
                    self.rdo.gbtx2_controller.set_idelay(new_idelay)
                time.sleep(0.05)
                st_flags = self.cru.get_status_flags()
                if st_flags['GbtRxDataErrorseenFlag'] == 1:
                    break
            low = new_idelay[i] + 1
            new_idelay[i] = idelay[i]
            if gbtx_number == 0:
                self.rdo.gbtx01_controller.set_idelay(new_idelay)
            else:
                self.rdo.gbtx2_controller.set_idelay(new_idelay)
            self.cru.reset_error_flags()

            for j in range(idelay[i], 512):
                new_idelay[i] = j
                if gbtx_number == 0:
                    self.rdo.gbtx01_controller.set_idelay(new_idelay)
                else:
                    self.rdo.gbtx2_controller.set_idelay(new_idelay)
                st_flags = self.cru.get_status_flags()
                if st_flags['GbtRxDataErrorseenFlag'] == 1:
                    break
            if new_idelay[i] == 511:
                hi = new_idelay[i]
            else:
                hi = new_idelay[i] - 1
            # reset IDELAY values to original
            new_idelay[i] = idelay[i]
            if gbtx_number == 0:
                self.rdo.gbtx01_controller.set_idelay(idelay)
            else:
                self.rdo.gbtx2_controller.set_idelay(idelay)
            self.cru.reset_error_flags()
            self.logger.info("idelay {} current {:>3d} range {:>3d} to {:>3d}, middle {:>3d}"
                             .format(i, idelay[i], low, hi, int((hi-low)/2+low)))

    def calibrate_gbtx_phaseSel(self, gbtx_number):
        """Calibrate the phaseSel values of GBTx gbtx_number by determining the range of error free operation"""

        # i2c addresses of the phaseSel registers (triplicated)
        phaseSelAddr = [[69, 73, 77],     # Group 0 Ch 0
                        [67, 71, 75],     # Group 0 Ch 4
                        [93, 97, 101],    # Group 1 Ch 0
                        [91, 95, 99],     # Group 1 Ch 4
                        [117, 121, 125],  # Group 2 Ch 0
                        [115, 119, 123],  # Group 2 Ch 4
                        [141, 145, 149],  # Group 3 Ch 0
                        [139, 143, 147],  # Group 3 Ch 4
                        [165, 169, 173],  # Group 4 Ch 0
                        [163, 167, 171]]  # Group 4 Ch 4
        assert self.use_rdo_usb, "USB connection is required to run the test"

        self.cru.comm.discardall_dp1(20)
        self.rdo.comm.discardall_dp1(20)
        # since we are sending random patterns,
        # make sure they are not interpreted as wishbone transactions
        self.cru.set_gbtx_forward_to_usb(0)
        self.cru.set_test_pattern(0)
        # set loopback mode
        self.rdo.gbtx01_controller.set_tx_pattern(3)
        self.rdo.gbtx2_controller.set_tx_pattern(3)
        self.rdo.gbtx01_controller.set_tx1_pattern(3)
        # load config files
        self.rdo.i2c_gbtx.gbtx_config(os.path.join(script_path,"../../modules/gbt/software/GBTx_configs/GBTx0_Config_RUv2.xml"), 0)
        self.rdo.i2c_gbtx.gbtx_config(os.path.join(script_path,"../../modules/gbt/software/GBTx_configs/GBTx2_Config_RUv2.xml"), 2)
        time.sleep(1)
        self.rdo.i2c_gbtx.gbtx_config(os.path.join(script_path,"../../modules/gbt/software/GBTx_configs/GBTx1_Config_RUv2.xml"), 1)
        time.sleep(1)
        # make sure GBTx connected to CRU
        if (gbtx_number in [0, 1]):
            assert self.rdo.i2c_gbtx.read_gbtx_register(427, 0) == 15
        else:
            assert self.rdo.i2c_gbtx.read_gbtx_register(427, 2) == 15

        # set PRBS pattern mode (requires branch JS_add_prbs_pattern in CRU emulator)
        self.cru.set_test_pattern(7)
        self.cru.reset_error_flags()
        st_flags = self.cru.get_status_flags()
        self.logger.info(st_flags)
        assert (st_flags['GbtRxDataErrorseenFlag'] == 0) and (st_flags['GbtRxReadyLostFlag'] == 0)

        # read current phaseSel values and vary over whole range,
        # finding values where the error flags are 0
        for i in range(10):
            current = self.rdo.i2c_gbtx.read_gbtx_register(phaseSelAddr[i][0], gbtx_number)
            low = 0
            hi = 0
            foundLo = False
            foundHi = False
            for j in range(16):
                for k in range(3):
                    self.rdo.i2c_gbtx.write_gbtx_register(phaseSelAddr[i][k], j, gbtx_number)
                time.sleep(0.05)
                self.cru.reset_error_flags()
                time.sleep(0.5)
                st_flags = self.cru.get_status_flags()
                if (st_flags['GbtRxDataErrorseenFlag'] == 0) and (not foundLo):
                    low = j
                    foundLo = True
                elif (st_flags['GbtRxDataErrorseenFlag'] == 1) and foundLo and (not foundHi):
                    hi = j - 1
                    foundHi = True
            # reset phaseSel to original value
            for k in range(3):
                self.rdo.i2c_gbtx.write_gbtx_register(phaseSelAddr[i][k], current, gbtx_number)
            self.cru.reset_error_flags()
            self.logger.info("elink {}: current {:>2d} range {:>2d} to {:2d}, middle {:>2d}"
                             .format(i, current, low, hi, int((hi - low)/2 + low)))
        self.cru.set_test_pattern(0)
        self.cru.reset_error_flags()

    def test_powerunit_log_values(self, n_test=10000):
        """Checks for the power unit log values function and asserts if the read value is 0.
        The check aims at verifying the issue #81 reported by mmager"""
        errors=0
        start_time = time.time()
        for i in range(n_test):
            if not self.rdo.powerunit_1.log_values_modules(zero_volt_read_check=True):
                errors += 1
        msg = "Errors reported: {0}/{1} in {2:.2f}s".format(errors,n_test,time.time()-start_time)
        self.logger.info(msg)
        self.tg_notification(msg)

    def test_powerunit_i2c_errors(self, n_test=10000, unit=1):
        """Checks for the power unit i2c communication stability"""
        errors=0
        start_time = time.time()
        if unit==1:
            pu=self.rdo.powerunit_1
        else:
            pu=self.rdo.powerunit_2
        for i in range(n_test):
            try:
                pu.read_temperature(0)
            except KeyboardInterrupt:
                self.logger.info("Ctrl-c")
                break
            except Exception:
                errors += 1
            if (i % 1000) == 0:
                print(i)
        msg = "Errors reported: {0}/{1} in {2:.2f}s".format(errors,n_test,time.time()-start_time)
        self.logger.info(msg)

    def test_gbtx_i2c(self, rdo=0, use_xcku=False, chip=0, num_tests=10000):
        rdo = self.rdo_list[rdo]
        if use_xcku:
            gbtx = rdo.gbtxs_swt[chip]
        else:
            gbtx = rdo.gbtxs_sca[chip]
            rdo.sca.initialize(gbtx_i2c_speed=gbt_sca.ScaI2cSpeed.f1MHz)

        num_errors = 0

        regs = [253, 61, 60, 59, 58, 57, 56, 55]
        for i in range(num_tests):
            if i % 1000 == 0:
                print(f"Transaction: {i}")
            reg = regs[random.randint(0, len(regs)-1)]
            val = random.randint(0, 255)
            try:
                gbtx.write(reg, val)
                if gbtx.read(reg) != val:
                    num_errors += 1
            except gbt_sca.ScaI2cBadStatusError as e:
                self.logger.warning(f"Failed for {reg} value {val} \t {e}")
                num_errors += 1
                if e.is_leverr():
                    self.logger.warning(f"Bus is stuck, breaking test...")
                    break
            except ws_i2c_gbtx.XckuI2cBadStatusError as e:
                self.logger.warning(f"Failed for {reg} value {val} \t {e}")
                num_errors += 1

        # Return SCA GBTx I2C speed to default
        rdo.sca.initialize()
        assert num_errors == 0, f"Test failed with {num_errors} errors..."

    def set_gbtx_to_por(self):
        rdo = self.rdo_list[0]
        gbtx = rdo.gbtx2_swt
        regs = [
            #reg #por #minimal itsconf
            (27,  0xb7, 0x28, 0x28),
            (29,  0xff, 0x15, 0x15),
            (30,  0xdd, 0x15, 0x15),
            (31,  0x4f, 0x15, 0x15),
            (32,  0xbd, 0x66, 0x66),
            (34,  0xfb, 0x0d, 0x0d),
            (35,  0x7c, 0x42, 0xf2), # diff
            (37,  0xfe, 0x0f, 0x0f),
            (38,  0xff, 0x04, 0x04),
            (39,  0xff, 0x08, 0x08),
            (41,  0xfe, 0x20, 0x20),
            (46,  0xfe, 0x15, 0x15),
            (47,  0xda, 0x15, 0x15),
            (48,  0xfd, 0x15, 0x15),
            (50,  0xff, 0x07, 0x07),
            (52,  0xc6, 0x38, 0x3f), # diff
            (242, 0xf0, 0x3f, 0x3f),
            (243, 0xef, 0x3f, 0x3f),
            (244, 0xef, 0x38, 0x38),
            (281, 0xf7, 0x15, 0x15),
            (283, 0xff, 0x20, 0x00), # diff
            (313, 0xff, 0x4e, 0x4e),
            (314, 0xff, 0x4e, 0x4e),
            (315, 0xba, 0x4e, 0x4e),
        ]
        for reg in regs:
            gbtx.write(reg[0], reg[1])


    def test_swt_rate(self,total_reads=1e6, train_size=512):
        tested = 0
        start_time=time.time()
        while tested < total_reads:
            tested += train_size
            for _ in range(train_size):
                self.rdo.identity.get_git_hash(commitTransaction=False)
                self.rdo.flush()
            for _ in range(train_size):
                self.rdo.comm._do_read_dp1(8)
        tot_time=time.time()-start_time
        self.logger.info("{0} SWT read in {1:.6f} s: {2:.2f} Hz".format(tested, tot_time, 2/(tot_time/tested)))

    def test_prbs_gbtx2(self, mode=PrbsMode.PRBS7, runtime=(60*10)):
        """Runs a PRBS test on GBTx2 of the RUs. Only LTU supported. Switching CRU to local clock recommended."""
        self.logger.info("TEST_PRBS_GBTX2 : Starting test_prbs_gbtx2.")
        self.logger.info("TEST_PRBS_GBTX2 : Warning: LOL on RU GBTx0 can be seen if CRU uses on LTU-PON clock due to LTU configuration")
        self.logger.info("TEST_PRBS_GBTX2 : Switching CRU to local clock recommended.")
        mode = PrbsMode(mode)
        self.cru.initialize()
        for rdo in self.rdo_list:
            rdo.gbtx2_prbs_chk.set_mode(mode)
            rdo.gbtx2_prbs_chk.enable_prbs_test()
            initial_trigger_handler_enable = rdo.trigger_handler.is_enable()
            initial_trigger_handler_tts_src, tts_src_flags = rdo.trigger_handler.get_trigger_source()
            SEQUENCER_SELECTOR = 1
            rdo.trigger_handler.set_trigger_source(SEQUENCER_SELECTOR)
            rdo.trigger_handler.disable()
        self.log_all_lol_counters()
        self.ltu.enable_prbs(mode)
        time.sleep(1) # LOL expected when switching mode, wait a little to avoid getting WB errors
        self.cru.initialize()
        for rdo in self.rdo_list:
            rdo.gbtx2_prbs_chk.reset_errors()
            self.logger.info(f"RU: {rdo.get_gbt_channel()} Locked : {rdo.gbtx2_prbs_chk.is_locked()}\tErrors : {rdo.gbtx2_prbs_chk.get_errors()}")
        self.log_all_lol_counters()
        start_time=time.time()
        try:
            while time.time()-start_time < runtime:
                if time.time()-start_time < 30:
                    time.sleep(5)
                else:
                    time.sleep(30)
                for rdo in self.rdo_list:
                    self.logger.info(f"RU: {rdo.get_gbt_channel()} Locked : {rdo.gbtx2_prbs_chk.is_locked()}\tErrors : {rdo.gbtx2_prbs_chk.get_errors()}")
        except KeyboardInterrupt:
            self.logger.info("Ctrl-c")
        for rdo in self.rdo_list:
            self.logger.info(f"RU: {rdo.get_gbt_channel()} Locked : {rdo.gbtx2_prbs_chk.is_locked()}\tErrors : {rdo.gbtx2_prbs_chk.get_errors()}")
            rdo.gbtx2_prbs_chk.disable_prbs_test()
            rdo.trigger_handler.set_trigger_source(initial_trigger_handler_tts_src)
            if initial_trigger_handler_enable == 1:
                rdo.trigger_handler.enable()

        self.log_all_lol_counters()
        self.ltu.disable_prbs()
        time.sleep(1) # LOL expected when switching mode, wait a little to avoid getting WB errors
        self.cru.initialize()
        self.log_all_lol_counters()

    def _get_pu_list(self, pu_index_set, rdo=None):
        """Checks the pu_index_set and returns the list of powerunits"""
        for index in pu_index_set:
            assert index in [1,2]
        if len(pu_index_set) > 1:
            pu_index_set = set(pu_index_set)
            assert pu_index_set.issubset((1,2))
        if rdo is None:
            rdo = self.rdo
        pu_list = []
        if 1 in pu_index_set:
            pu_list.append(rdo.powerunit_1)
        if 2 in pu_index_set:
            pu_list.append(rdo.powerunit_2)
        return pu_list

    def _get_pu_module_list(self, powerunit_1_module_list, powerunit_2_module_list):
        return [powerunit_1_module_list, powerunit_2_module_list]

    def power_on_ob_stave(self,
                          module_list_lower=[0,1,2,3,4,5,6],
                          module_list_upper=[0,1,2,3,4,5,6],
                          avdd=1.82, dvdd=1.82,
                          avdd_current=1.5, dvdd_current=1.5,
                          bb=0,
                          internal_temperature_limit=30,
                          external_temperature_limit=30,
                          no_offset=False,
                          configure_chips=False,
                          compensate_v_drop=True,
                          rdo=None):
        """Powers off all modules on outer layer stave"""
        if rdo is None:
            rdo = self.rdo
        if self.layer is LayerList.MIDDLE:
            if len(module_list_lower)==6 and len(module_list_upper)==6:
                self.logger.warning("Powering on ML stave with default parameters, adjusting module list")
                module_list_lower=[0,1,2,3]
                module_list_upper=[0,1,2,3]
            self.power_on_ml_stave(module_list_lower=module_list_lower,
                                   module_list_upper=module_list_upper,
                                   avdd=avdd, dvdd=dvdd,
                                   avdd_current=avdd_current, dvdd_current=dvdd_current,
                                   bb=bb,
                                   internal_temperature_limit=internal_temperature_limit,
                                   external_temperature_limit=external_temperature_limit,
                                   no_offset=no_offset,
                                   configure_chips=configure_chips,
                                   compensate_v_drop=compensate_v_drop,
                                   rdo=rdo)
        elif self.layer is LayerList.OUTER:
            self.power_on_ol_stave(powerunit_1_module_list=module_list_lower,
                                   powerunit_2_module_list=module_list_upper,
                                   avdd=avdd, dvdd=dvdd,
                                   avdd_current=avdd_current, dvdd_current=dvdd_current,
                                   bb=bb,
                                   internal_temperature_limit=internal_temperature_limit,
                                   external_temperature_limit=external_temperature_limit,
                                   no_offset=no_offset,
                                   configure_chips=configure_chips,
                                   compensate_v_drop=compensate_v_drop,
                                   rdo=rdo)
        else:
            self.logger.error("Stave is not OB!")

    def power_on_ol_stave(self,
                          powerunit_1_module_list=[0,1,2,3,4,5,6],
                          powerunit_2_module_list=[0,1,2,3,4,5,6],
                          avdd=1.82, dvdd=1.82,
                          avdd_current=1.5, dvdd_current=1.5,
                          bb=0,
                          internal_temperature_limit=30,
                          external_temperature_limit=30,
                          internal_temperature_low_limit=10,
                          external_temperature_low_limit=10,
                          no_offset=False,
                          configure_chips=False,
                          compensate_v_drop=True,
                          rdo=None):
        """Powers on the OB connected to the power units with the index
        in pu_index_set

        module_list is a list of modules to be switched on.
                    Mapping is conform to powerunit channel mapping,
        avdd is the analogue supply voltage
        dvdd is the digital supply voltage
        avdd_current is the analogue supply voltage max current
        dvdd_current is the digital supply voltage max current
        bb is the backbias voltage
        configure_chips will configure sensors if True
        compensate_v_drop will compensate voltage drop across cable if True
        """
        if rdo is None:
            rdo = self.rdo
        dclk_phase = 45
        pu_index_set = (1,2)
        pu_list = self._get_pu_list(pu_index_set, rdo=rdo)
        try:
            module_list = self._get_pu_module_list(powerunit_1_module_list, powerunit_2_module_list)
            assert len(module_list)==len(pu_list)
            for pu_index, powerunit in enumerate(pu_list):
                if re.match(SUBRACK_REGEX, self.subrack):
                    powerunit.controller.disable_power_interlock()
                else:
                    powerunit.controller.disable_all_interlocks()
                time.sleep(0.1)  # let monitoring loop finish
                powerunit.initialize()
                powerunit.controller.enable_temperature_interlock(internal_temperature_limit=internal_temperature_limit,
                                                                  ext1_temperature_limit=external_temperature_limit,
                                                                  internal_temperature_low_limit=internal_temperature_low_limit,
                                                                  ext1_temperature_low_limit=external_temperature_low_limit)
                assert powerunit.controller.is_temperature_interlock_enabled(interlock=powerunit.interlock) is True
                time.sleep(0.5)  # ADC and RTD values take some time to initialize and read properly
                powerunit.controller.reset_tripped_latch()
                powerunit.log_values_modules(module_list=module_list[pu_index])
                assert not powerunit.controller.did_interlock_fire()
            self.logger.info("Stopping clock propagation")
            rdo.alpide_control.disable_dclk()
            for pu_index, powerunit in enumerate(pu_list):
                powerunit.setup_power_modules(module_list=module_list[pu_index],
                                          avdd=avdd,
                                          dvdd=dvdd,
                                          avdd_current=avdd_current,
                                          dvdd_current=dvdd_current,
                                          bb=bb,
                                          no_offset=no_offset)

                powerunit.power_on_modules(module_list=module_list[pu_index],
                                       backbias_en=(bb!=0))
                if len(module_list[pu_index]):
                    assert powerunit.controller.is_power_interlock_enabled()
                powerunit.log_values_modules(module_list=module_list[pu_index])
            self.logger.info(f"Propagating clock with {dclk_phase}")
            rdo.alpide_control.enable_dclk(phase=dclk_phase)
            time.sleep(0.3)
            for pu_index, powerunit in enumerate(pu_list):
                assert not powerunit.controller.did_interlock_fire(), f"Clock propagation provoked interlock!"
                assert powerunit.log_values_modules(module_list=module_list[pu_index], zero_volt_read_check=True), f"Clock propagation killed voltage => probably internal PU interlock."
                powerunit.log_values_modules(module_list=module_list[pu_index])
                self.logger.info(f"Internal Temperature {powerunit.controller.get_temperature(0):.2f} C")
                self.logger.info(f"Stave Temperature {powerunit.controller.get_temperature(1):.2f} C")
            ch = Alpide(rdo, chipid=0x0F)  # global broadcast
            if configure_chips:
                self.logger.info("Configuring chips...")
                self.initialize_chips_ob_stave(module_list_lower=[i+1 for i in range(7)], module_list_upper=[i+1 for i in range(7)], rdo=rdo)
                self.setup_sensors_ob_stave(module_list_lower=[i+1 for i in range(7)],
                                            module_list_upper=[i+1 for i in range(7)],
                                            avdd=avdd,
                                            dvdd=dvdd,
                                            rdo=rdo)
                self.logger.info("Chips configured!")
            if compensate_v_drop:
                cable_length = self.get_avg_cable_length(layer=LayerList.OUTER)
                for pu_index, powerunit in enumerate(pu_list):
                    powerunit.compensate_voltage_drops_ob(avdd=avdd, dvdd=dvdd, l=cable_length[pu_index], powered_module_list=module_list[pu_index])
                    time.sleep(0.1)
                    self.log_values_ob_stave(rdo=rdo)

        except Exception as e:
            self.logger.error("Power-on failed Exception")
            self.logger.error(e)
            self.logger.info("Power off!")
            self.power_off_ob_stave(rdo=rdo)
            self.logger.error("Printing Traceback and raising")
            raise e

    def power_on_ml_stave(self,
                          module_list_lower=[0,1,2,3],
                          module_list_upper=[0,1,2,3],
                          avdd=1.82, dvdd=1.82,
                          avdd_current=1.5, dvdd_current=1.5,
                          bb=0,
                          internal_temperature_limit=30,
                          external_temperature_limit=30,
                          internal_temperature_low_limit=10,
                          external_temperature_low_limit=10,
                          no_offset=False,
                          configure_chips=False,
                          compensate_v_drop=True,
                          rdo=None):
        """Powers on the OB connected to the power units with the index
        in pu_index_set

        module_list is a list of modules to be switched on.
                    Mapping is conform to powerunit channel mapping,
        avdd is the analogue supply voltage
        dvdd is the digital supply voltage
        avdd_current is the analogue supply voltage max current
        dvdd_current is the digital supply voltage max current
        bb is the backbias voltage
        configure_chips will configure sensors if True
        compensate_v_drop will compensate voltage drop across cable if True
        """
        module_list = module_list_lower + [module+4 for module in module_list_upper]
        if rdo is None:
            rdo = self.rdo
        dclk_phase = 45
        pu_index_set = [1]
        pu_list = self._get_pu_list(pu_index_set, rdo=rdo)
        try:
            for pu_index, powerunit in enumerate(pu_list):
                if re.match(SUBRACK_REGEX, self.subrack):
                    powerunit.controller.disable_power_interlock()
                else:
                    powerunit.controller.disable_all_interlocks()
                time.sleep(0.1)  # let monitoring loop finish
                powerunit.initialize()
                powerunit.controller.enable_temperature_interlock(internal_temperature_limit=internal_temperature_limit,
                                                                  ext1_temperature_limit=external_temperature_limit,
                                                                  ext2_temperature_limit=external_temperature_limit,
                                                                  internal_temperature_low_limit=internal_temperature_low_limit,
                                                                  ext1_temperature_low_limit=external_temperature_low_limit,
                                                                  ext2_temperature_low_limit=external_temperature_low_limit)
                time.sleep(0.5)  # ADC and RTD values take some time to initialize and read properly
                powerunit.controller.reset_tripped_latch()
                powerunit.log_values_modules(module_list=module_list)
                assert not powerunit.controller.did_interlock_fire()
            self.logger.info("Stopping clock propagation")
            rdo.alpide_control.disable_dclk()
            for pu_index, powerunit in enumerate(pu_list):
                powerunit.setup_power_modules(module_list=module_list,
                                          avdd=avdd,
                                          dvdd=dvdd,
                                          avdd_current=avdd_current,
                                          dvdd_current=dvdd_current,
                                          no_offset=no_offset,
                                          bb=bb)
                powerunit.power_on_modules(module_list=module_list,
                                       backbias_en=(bb!=0))
                powerunit.log_values_modules(module_list=module_list)
            self.logger.info(f"Propagating clock with {dclk_phase}")
            rdo.alpide_control.enable_dclk(phase=dclk_phase)
            time.sleep(0.3)
            for pu_index, powerunit in enumerate(pu_list):
                assert not powerunit.controller.did_interlock_fire(), f"Clock propagation provoked interlock!"
                assert powerunit.log_values_modules(module_list=module_list, zero_volt_read_check=True), f"Clock propagation killed voltage => probably internal PU interlock."
                powerunit.log_values_modules(module_list=module_list)
                self.logger.info(f"Internal Temperature {powerunit.controller.get_temperature(0):.2f} C")
                self.logger.info(f"Stave Temperature {powerunit.controller.get_temperature(1):.2f} C")
            ch = Alpide(rdo, chipid=0x0F)  # global broadcast
            if configure_chips:
                self.logger.info("Configuring chips...")
                self.initialize_chips_ob_stave(module_list_lower=[i+1 for i in range(4)], module_list_upper=[i+1 for i in range(4)], rdo=rdo)
                self.setup_sensors_ml_stave(module_list_lower=[i+1 for i in range(4)],
                                            module_list_upper=[i+1 for i in range(4)],
                                            rdo=rdo)
                self.logger.info("Chips configured!")
            if compensate_v_drop:
                cable_length = self.get_avg_cable_length(layer=LayerList.MIDDLE)
                for pu_index, powerunit in enumerate(pu_list):
                    powerunit.compensate_voltage_drops_ob(avdd=avdd, dvdd=dvdd, l=cable_length[pu_index], powered_module_list=module_list)
                    time.sleep(0.1)
                    self.log_values_ml_stave(rdo=rdo)

        except Exception as e:
            self.logger.error("Power-on failed Exception")
            self.logger.error(e)
            self.logger.info("Power off!")
            self.power_off_ml_stave()
            self.logger.error("Printing Traceback and raising")
            raise e

    def power_off_ml_stave(self,
                           disable_power_interlock=False,
                           rdo=None):
        """Powers off all the modules connected to the powerunit_1"""
        if rdo is None:
            rdo = self.rdo
        rdo.powerunit_1.log_values_modules(module_list=list(range(8)))
        rdo.powerunit_1.power_off_all(disable_power_interlock)
        self.logger.info("All off!!")
        rdo.wait(0xFFFFFF)
        time.sleep(1)
        rdo.powerunit_1.log_values_modules(module_list=list(range(8)))
        rdo.alpide_control.disable_dclk()

    def power_off_ol_stave(self,
                           disable_power_interlock=False,
                           rdo=None):
        """Powers off all the modules connected to the powerunit_1 and powerunit_2"""
        if rdo is None:
            rdo = self.rdo
        rdo.powerunit_1.log_values_modules(module_list=list(range(8)))
        rdo.powerunit_2.log_values_modules(module_list=list(range(8)))
        rdo.powerunit_1.power_off_all(disable_power_interlock)
        rdo.powerunit_2.power_off_all(disable_power_interlock)
        self.logger.info("All off!!")
        rdo.wait(0xFFFFFF)
        time.sleep(1)
        rdo.powerunit_1.log_values_modules(module_list=list(range(8)))
        rdo.powerunit_2.log_values_modules(module_list=list(range(8)))
        rdo.alpide_control.disable_dclk()

    def power_off_ob_stave(self,
                           disable_power_interlock=False,
                           rdo=None):
        """Powers off all modules on outer layer stave"""
        if rdo is None:
            rdo = self.rdo
        if self.layer is LayerList.MIDDLE:
            self.power_off_ml_stave(rdo=rdo, disable_power_interlock=disable_power_interlock)
        elif self.layer is LayerList.OUTER:
            self.power_off_ol_stave(rdo=rdo, disable_power_interlock=disable_power_interlock)
        else:
            self.logger.error("Stave is not OB!")

    def get_cable_length(self, rdo=None):
        """Returns exact cable length using power_cable_mapping"""
        if rdo is None:
            rdo = self.rdo
        stave = self.get_stave_number(rdo.get_gbt_channel())
        layer_number = self.get_layer(rdo.get_gbt_channel())
        cable_length = [0]*2
        for entry in power_cable_mapping.cable_length_lut[str(layer_number)]:
            if entry[0] == int(stave):
                if entry[1] == 'lower':
                    cable_length[0] = entry[2]+entry[3]
                elif entry[1] == 'upper':
                    cable_length[1] = entry[2]+entry[3]
                elif entry[1] == 'IB':
                    cable_length[0] = entry[2]+entry[3]
                else:
                    raise RuntimeError(f"invalid entry in power_cable_mapping: {entry[1]}")
        return cable_length

    def get_avg_cable_length(self, layer=None):
        """Returns approximate cable length for given layer (Inner, Middle, Outer),
           Values obtained from power_cable_mapping.py"""
        if layer is None:
            layer = self.layer
        cable_length = [0]*2
        if layer is LayerList.INNER:
            cable_length[0] = 2.65 + 4.65
        elif layer is LayerList.MIDDLE:
            cable_length[0] = 2.45 + 4.2
            cable_length[1] = 2.45 + 4.2
        elif layer is LayerList.OUTER:
            cable_length[0] = 2.15 + 4.5
            cable_length[1] = 2.15 + 4.5
        else:
            raise NotImplementedError
        return cable_length

    def check_trip_ob_stave(self,
                            powerunit_1_module_list=[0,1,2,3,4,5,6,7],
                            powerunit_2_module_list=[0,1,2,3,4,5,6,7],
                            rdo=None):
        """method to turn off all power and dclk if power to module trips
        returns True if the module is okay, false if it tripped
        """
        if rdo is None:
            rdo = self.rdo
        is_tripped = []
        is_tripped.append(rdo.powerunit_1.is_any_channel_tripped(module_list=powerunit_1_module_list))
        is_tripped.append(rdo.powerunit_2.is_any_channel_tripped(module_list=powerunit_2_module_list))
        if True in is_tripped:
            rdo.alpide_control.disable_dclk()
            self.logger.info("CLK off")
            return False
        else:
            return True

    def check_trip_ob_stave_bias(self,
                            powerunit_1_module_list=[0,1,2,3,4,5,6,7],
                            powerunit_2_module_list=[0,1,2,3,4,5,6,7],
                            rdo=None):
        """Checks if bias is tripped and if so, turns of power and dclk.
        Returns True if there is no trip, False if there is a trip.
        """
        if rdo is None:
            rdo = self.rdo
        if rdo.powerunit_1.is_bias_tripped(module_list=powerunit_1_module_list) or rdo.powerunit_2.is_bias_tripped(module_list=powerunit_2_module_list):
            rdo.alpide_control.disable_dclk()
            self.logger.info("CLK off")
            return False
        else:
            return True

    def log_values_ml_stave(self,
                            use_i2c=False,
                            rdo=None):
        """Logs currents and voltages of the PU of the ML stave"""
        if rdo is None:
            rdo = self.rdo
        rdo.powerunit_1.log_values_modules(module_list=list(range(8)), use_i2c=use_i2c)

    def log_values_ob_stave(self,
                            use_i2c=False,
                            rdo=None):
        """Logs currents and voltages of the PU of the OB stave"""
        if rdo is None:
            rdo = self.rdo
        rdo.powerunit_1.log_values_modules(module_list=list(range(7)), use_i2c=use_i2c)
        rdo.powerunit_2.log_values_modules(module_list=list(range(7)), use_i2c=use_i2c)

    def log_values(self,
                   rdo=None):
        if rdo is None:
            rdo = self.rdo

        if self.layer is LayerList.OUTER:
            self.log_values_ob_stave(rdo=rdo)
        elif self.layer is LayerList.MIDDLE:
            self.log_values_ml_stave(rdo=rdo)
        elif self.layer is LayerList.INNER:
            self.log_values_ib_stave(rdo=rdo)

    def check_temperature_ob_stave(self,
                                   trip_temperature=45,
                                   pu_index_set=[1],
                                   rdo=None):
        """Reads the temperature of each PT100 temperature sensors then,
        the temperature is too high, turns off the power supply and
        clock to each module

        returns if overtemperature occurred"""
        if rdo is None:
            rdo = self.rdo
        pu_list = self._get_pu_list(pu_index_set, rdo=rdo)

        overtemp_list = []
        for powerunit in pu_list:
            overtemp_list.append(powerunit.is_overtemperature(trip_temperature))

        overtemperature = False
        if True in overtemp_list:
            overtemperature = True
            self._handle_overtemperature_ob_stave(pu_index_set=pu_index_set, rdo=rdo)
        return overtemperature

    def _handle_overtemperature_ob_stave(self, pu_index_set=[1,2],
                                         rdo=None):
        """Handles the over-temperature"""
        if rdo is None:
            rdo = self.rdo
        pu_list = self._get_pu_list(pu_index_set, rdo=rdo)
        for powerunit in pu_list:
            powerunit.log_values_modules(module_list=[0,1,2,3,4,5,6,7])
            powerunit.power_off_all()
        rdo.alpide_control.disable_dclk()
        self.logger.info("CLK off")
        for powerunit in pu_list:
            powerunit.log_values_modules(module_list=[0,1,2,3,4,5,6,7])

    def check_any_trip_ob_stave(self,
                       pu_index_set=[1,2],
                       rdo=None):
        """Powers down stave and turns off clock if there is a ADDD, DVDD or bias trip, or if there is an overtemperature.
        Assumes all modules are powered correctly and the bias is on.
        """
        if rdo is None:
            rdo = self.rdo
        not_tripped = []
        module_list = [0,1,2,3,4,5,6]
        for powerunit in pu_index_set:
            if powerunit == 1:
                not_tripped.append(self.check_trip_ob_stave(powerunit_1_module_list=module_list, powerunit_2_module_list=[], rdo=rdo))
                not_tripped.append(self.check_trip_ob_stave_bias(powerunit_1_module_list=module_list, powerunit_2_module_list=[], rdo=rdo))
            elif powerunit == 2:
                not_tripped.append(self.check_trip_ob_stave_bias(powerunit_1_module_list=[], powerunit_2_module_list=module_list, rdo=rdo))
                not_tripped.append(self.check_trip_ob_stave(powerunit_1_module_list=[], powerunit_2_module_list=module_list, rdo=rdo))

        if False in not_tripped or self.check_temperature_ob_stave(pu_index_set=pu_index_set, rdo=rdo):
            self.logger.info("Trip occured. Powerunit involved in trip already powered off. Powering off all powerboard channels. This message will also appear if bias is off or not all modules are powered.")
            self.power_off_ob_stave()
        else:
            self.logger.info("AVDD, DVDD, bias not tripped. PT100 temperature below temperature threshold.")

    def _select_hs(self, lower=True, rdo=None):
        if rdo is None:
            rdo = self.rdo
            self.logger.warning("Fall back to default rdo!")
        if lower:
            chip_list = self.stave_ob_lower(gbt_ch=rdo.get_gbt_channel())
        else:
            chip_list = self.stave_ob_upper(gbt_ch=rdo.get_gbt_channel())
        assert isinstance(chip_list, dict), chip_list
        assert chip_list is not {}
        assert chip_list is not None
        return chip_list

    def initialize_chips_ob_stave(self,
                                  module_list_lower=[1],
                                  module_list_upper=[],
                                  rdo=None):
        if rdo is None:
            rdo = self.rdo
        chip_broadcast = self.stave_chip_broadcast(gbt_ch=rdo.get_gbt_channel())
        self._initialize_chips_ob_stave(module_list=module_list_lower,
                                        is_on_lower_hs=True,
                                        rdo=rdo)
        self._initialize_chips_ob_stave(module_list=module_list_upper,
                                        is_on_lower_hs=False,
                                        rdo=rdo)
        chip_broadcast.write_opcode(Opcode.RORST)

    def _initialize_chips_ob_stave(self,
                                   module_list=[1],
                                   is_on_lower_hs=True,
                                   rdo=None):
        if rdo is None:
            rdo = self.rdo
        chip_list = self._select_hs(is_on_lower_hs, rdo=rdo)
        for module in module_list:
            for _, chip in chip_list.items():
                if chip.is_on_module(module):
                    chip.initialize(grst=False, verbose=False)

    def get_excluded_chip_list_from_config(self, rdo):
        # read config file
        ob_staves_yml_path = os.path.join(script_path, "../config/ob_staves.yml")
        with open(ob_staves_yml_path, 'r') as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
            for entry in crate_mapping.subrack_lut[self.subrack]:
                layer = entry[crate_mapping.Fields.layer]
            stave_config = config['layer'][layer]['stave']
        stave_number = self.get_stave_number(gbt_channel=rdo.get_gbt_channel())
        excluded_chipid_ext = []
        if stave_number in stave_config:
            if 'excluded-chips' in stave_config[stave_number]:
                excluded_chipid_ext = stave_config[stave_number]['excluded-chips']
            else:
                self.logger.warning(f"stave {stave_number} has no excluded-chips")
        else:
            self.logger.warning(f"Stave {stave_number} not in {stave_config}")
        self.logger.info(f"Stave {stave_number}, excluded chipid from config: {excluded_chipid_ext}")
        return excluded_chipid_ext

    def test_chips_ml_stave(self,
                            module_list_lower=[1,2,3,4],
                            module_list_upper=[1,2,3,4],
                            nrtests=100,
                            rdo=None):
        return self.test_chips_ob_stave(module_list_lower=module_list_lower,
                                        module_list_upper=module_list_upper,
                                        nrtests=nrtests,
                                        rdo=rdo)

    def test_chips_ob_stave(self,
                            module_list_lower=[0,1,2,3,4,5,6],
                            module_list_upper=[0,1,2,3,4,5,6],
                            nrtests=100,
                            exclude_chips=False,
                            rdo=None):
        if rdo is None:
            rdo = self.rdo
        total_errors = {}
        try:
            errors_dict = self._test_chips_ob_stave(module_list=module_list_lower,
                                                    is_on_lower_hs=True,
                                                    nrtests=nrtests,
                                                    exclude_chips=exclude_chips,
                                                    rdo=rdo)
            total_errors.update(errors_dict)
            errors_dict = self._test_chips_ob_stave(module_list=module_list_upper,
                                                    is_on_lower_hs=False,
                                                    nrtests=nrtests,
                                                    exclude_chips=exclude_chips,
                                                    rdo=rdo)
            total_errors.update(errors_dict)
        except Exception as e:
            self.logger.error("Test interrupted by exception")
            self.logger.info(e, exc_info=True)
        return total_errors

    def _test_chips_ob_stave(self,
                             module_list=[1],
                             is_on_lower_hs=True,
                             nrtests=100,
                             exclude_chips=False,
                             rdo=None):
        if rdo is None:
            rdo = self.rdo
        chip_list = self._select_hs(is_on_lower_hs, rdo=rdo)
        total_errors = {}
        k_dict = {}
        if exclude_chips:
            excluded_chip_list = self.get_excluded_chip_list_from_config(rdo)
            for module in module_list:
                for _, chip in chip_list.items():
                    if chip.extended_chipid not in excluded_chip_list:
                        if chip.is_on_module(module):
                            k_dict[chip.extended_chipid] = 0
                            errors_dict, _ = self.test_chips(nrfirst=chip.extended_chipid,
                                                             nrlast=chip.extended_chipid,
                                                             nrtests=nrtests,
                                                             is_on_ob=True,
                                                             rdo=rdo)
                            total_errors.update(errors_dict)
        else:
            for module in module_list:
                for _, chip in chip_list.items():
                    if chip.is_on_module(module) and chip.is_outer_barrel_master():
                        for i in range(7):
                            k_dict[chip.extended_chipid+i] = 0
                        errors_dict, _ = self.test_chips(nrfirst=chip.extended_chipid,
                                                         nrlast=chip.extended_chipid+6,
                                                         nrtests=nrtests,
                                                         is_on_ob=True,
                                                         rdo=rdo)
                        total_errors.update(errors_dict)

        assert total_errors.keys() == k_dict.keys(), f"Keys differ {total_errors.keys()} != {k_dict.keys()}"
        return total_errors

    def test_cmu_dmu_errors_ml_stave(self,
                                     module_list_lower=[1,2,3,4],
                                     module_list_upper=[1,2,3,4],
                                     rdo=None):
        """Performs a read of the CMU/DMU error register for one ML stave"""
        return self.test_cmu_dmu_errors_ob_stave(module_list_lower=module_list_lower,
                                                 module_list_upper=module_list_upper,
                                                 rdo=rdo)

    def test_cmu_dmu_errors_ob_stave(self,
                                     module_list_lower=[0,1,2,3,4,5,6],
                                     module_list_upper=[0,1,2,3,4,5,6],
                                     rdo=None):
        """Performs a read of the CMU/DMU error register for one OB stave"""
        if rdo is None:
            rdo = self.rdo
        total_errors = {}
        try:
            errors_dict = self._test_cmu_dmu_errors_ob_stave(module_list=module_list_lower,
                                                             is_on_lower_hs=True,
                                                             rdo=rdo)
            total_errors.update(errors_dict)
            errors_dict = self._test_cmu_dmu_errors_ob_stave(module_list=module_list_upper,
                                                             is_on_lower_hs=False,
                                                             rdo=rdo)
            total_errors.update(errors_dict)
        except Exception as e:
            self.logger.error("Test interrupted by exception")
            self.logger.info(e, exc_info=True)
        return total_errors

    def _test_cmu_dmu_errors_ob_stave(self,
                                      module_list=[1],
                                      is_on_lower_hs=True,
                                      rdo=None):
        """Performs a read of the CMU/DMU error register for one half stave on the OB"""
        if rdo is None:
            rdo = self.rdo
        chip_list = self._select_hs(is_on_lower_hs, rdo=rdo)
        total_errors = {}
        k_dict = {}
        for module in module_list:
            for _, chip in chip_list.items():
                if chip.is_on_module(module) and chip.is_outer_barrel_master():
                    for i in range(7):
                        k_dict[chip.extended_chipid+i] = 0
                        errors_dict = self.test_cmu_dmu_errors(nrfirst=chip.extended_chipid,
                                                               nrlast=chip.extended_chipid+6,
                                                               is_on_ob=True,
                                                               rdo=rdo)
                    total_errors.update(errors_dict)
        assert total_errors.keys() == k_dict.keys(), f"Keys differ {total_errors.keys()} != {k_dict.keys()}"
        return total_errors

    def initialize_readout_ob_stave(self,
                                    module_list_lower=[1],
                                    module_list_upper=[],
                                    rdo=None):
        """Sets up and configure the pll of the master chips"""
        locked = []
        locked += self._initialize_readout_ob_stave(module_list=module_list_lower,
                                                    is_on_lower_hs=True,
                                                    rdo=rdo)
        locked += self._initialize_readout_ob_stave(module_list=module_list_upper,
                                                    is_on_lower_hs=False,
                                                    rdo=rdo)
        return locked

    def _initialize_readout_ob_stave(self,
                                     module_list=[1],
                                     is_on_lower_hs=True,
                                     rdo=None):
        """Sets up and configure the pll of the master chips"""
        if rdo is None:
            rdo = self.rdo
        chip_list = self._select_hs(is_on_lower_hs, rdo=rdo)
        locked = []
        for module in module_list:
            for _, chip in chip_list.items():
                if chip.is_on_module(module) and chip.is_outer_barrel_master():
                    locked.append(chip.initialize_readout(PLLDAC=8,
                                                          DriverDAC=8,
                                                          PreDAC=8,
                                                          PLLDelayStages=4))
        return locked


    def setup_prbs_test_ob_stave(self,
                                 module_list_lower=[1],
                                 module_list_upper=[],
                                 rdo=None):
        """Set up the prbs test for the GPIOs (verifying that it is activated).
        chips is a list of chipids"""
        self._setup_prbs_test_ob_stave(rdo=rdo)
        time.sleep(1)
        self.verify_prbs_test_activation_ob_stave(module_list_lower=module_list_lower,
                                                  module_list_upper=module_list_upper,
                                                  rdo=rdo)

    def _setup_prbs_test_ob_stave(self,
                                  rdo=None):
        """Set up the prbs test for the GPIOs (wihtout verifying that it is activated).
        chips is a list of chipids"""
        if rdo is None:
            rdo = self.rdo
        rdo.gpio.enable_data(False)
        chip_broadcast = self.stave_chip_broadcast(gbt_ch=rdo.get_gbt_channel())
        chip_broadcast.propagate_prbs(PrbsRate=1) # 400 Mbps
        rdo.gpio.enable_prbs(enable=True, commitTransaction=True)
        rdo.gpio.reset_prbs_counter()

    def _propagate_prbs_ob_stave(self, module_list=[1], is_on_lower_hs=True,
                                 rdo=None):
        """Set up the prbs test for the GPIOs (wihtout verifying that it is activated).
        chips is a list of chipids"""
        if rdo is None:
            rdo = self.rdo
        chip_list = self._select_hs(is_on_lower_hs, rdo=rdo)
        for module in module_list:
            for _, chip in chip_list.items():
                if chip.is_on_module(module) and chip.is_outer_barrel_master():
                    chip.propagate_prbs(PrbsRate=1) # 400 Mbps

    def verify_prbs_test_activation_ob_stave(self,
                                             module_list_lower=[1],
                                             module_list_upper=[],
                                             rdo=None):
        """Verifies that the prbs is correcly activated"""
        nonvalid_prbs = []
        nonvalid_prbs += self._verify_prbs_test_activation_ob_stave(module_list=module_list_lower,
                                                                    is_on_lower_hs=True,
                                                                    rdo=rdo)
        nonvalid_prbs += self._verify_prbs_test_activation_ob_stave(module_list=module_list_upper,
                                                                    is_on_lower_hs=False,
                                                                    rdo=rdo)
        if nonvalid_prbs==[]:
            self.logger.info("PRBS correctly activated for all chips")
        else:
            self.logger.warning(f"PRBS NOT activated correctly for chipids {nonvalid_prbs}")

    def _verify_prbs_test_activation_ob_stave(self,
                                              module_list=[1],
                                              is_on_lower_hs=True,
                                              rdo=None):
        """Verifies that the prbs is correcly activated"""
        if rdo is None:
            rdo = self.rdo
        chip_list = self._select_hs(is_on_lower_hs, rdo=rdo)
        nonvalid_prbs = []
        for module in module_list:
            for _, chip in chip_list.items():
                if chip.is_on_module(module) and chip.is_outer_barrel_master():
                    lane = rdo.get_gpio_lane(chipid=chip.chipid,
                                             is_on_lower_hs=is_on_lower_hs)
                    counters = rdo.gpio.read_prbs_counter()
                    if counters[lane]!=0:
                        self.logger.warning(f"Prbs not correctly started for chipid {chip.chipid}: {counters[lane]}")
                    chip.propagate_clock(log_pll_lock=False)
                    counters = rdo.gpio.read_prbs_counter()
                    self.logger.debug(f"CHIPID {chip.chipid}: counters {counters}")
                    if counters[lane]==0:
                        self.logger.info(f"CHIPID {chip.chipid}: counters {counters}")
                        nonvalid_prbs.append(chip.chipid)
                    chip.propagate_prbs()
                    rdo.gpio.reset_prbs_counter()
                    counters = rdo.gpio.read_prbs_counter()
                    self.logger.debug(f"CHIPID {chip.chipid}: counters {counters}")
                    if counters[lane]!=0:
                        self.logger.warning(f"Prbs not correctly restarted for chipid {chip.chipid}: {counters[lane]} errors")
        return nonvalid_prbs

    def check_prbs_test_ob_stave(self,
                                 module_list_lower=[1,2,3,4,5,6,7],
                                 module_list_upper=[1,2,3,4,5,6,7],
                                 verbose=False,
                                 rdo=None):
        """Check the prbs test counters for ob stave"""
        prbs_errors = {}
        errors_lower = False
        errors_upper = False
        errors_lower, prbs_errors['lower'] = self._check_prbs_test_ob_stave(module_list=module_list_lower,
                                                                            is_on_lower_hs=True,
                                                                            verbose=verbose,
                                                                            rdo=rdo)
        errors_upper, prbs_errors['upper'] = self._check_prbs_test_ob_stave(module_list=module_list_upper,
                                                                           is_on_lower_hs=False,
                                                                           verbose=verbose,
                                                                           rdo=rdo)
        if True in [errors_lower, errors_upper]:
            self.logger.warning(f"Prbs errors present {prbs_errors}")
            return True
        else:
            return False

    def _check_prbs_test_ob_stave(self,
                                  module_list=[1],
                                  is_on_lower_hs=True,
                                  verbose=False,
                                  rdo=None):
        """Check the prbs test counters for ob stave"""
        if rdo is None:
            rdo = self.rdo
        chip_list = self._select_hs(is_on_lower_hs, rdo=rdo)
        chipid_prbs_errors = {}
        counters = rdo.gpio.read_prbs_counter()
        for module in module_list:
            for _, chip in chip_list.items():
                if chip.is_on_module(module) and chip.is_outer_barrel_master():
                    if chip.chipid in rdo.get_chip2connector_lut():
                        lane = rdo.get_gpio_lane(chipid=chip.chipid,
                                                      is_on_lower_hs=is_on_lower_hs)
                        if verbose:
                            self.logger.info(f"CHIPID {chip.chipid}: counters {counters[lane]}")
                        else:
                            self.logger.debug(f"CHIPID {chip.chipid}: counters {counters[lane]}")
                        chipid_prbs_errors[chip.chipid] = counters[lane]
        errors = False
        for key, value in chipid_prbs_errors.items():
            if value != 0:
                errors = True
        return errors, chipid_prbs_errors

    def scan_idelay_ob_stave(self,
                             stepsize=10, waittime=0.1, set_optimum=True,
                             enable_data_after=True,
                             rdo=None):
        """Scans the delays of the OB stave"""
        if rdo is None:
            rdo = self.rdo
        self._setup_prbs_test_ob_stave(rdo=rdo)
        optima,ranges=rdo.gpio.scan_idelays(stepsize=stepsize, waittime=waittime,
                                            set_optimum=set_optimum,
                                            verbose=True)
        if enable_data_after:
            chip_broadcast = self.stave_chip_broadcast(gbt_ch=rdo.get_gbt_channel())
            chip_broadcast.propagate_data()
        return optima,ranges

    def propagate_data_ob_stave(self,
                                module_list_lower=[1],
                                module_list_upper=[],
                                rdo=None):
        self._propagate_data_ob_stave(module_list=module_list_lower,
                                      is_on_lower_hs=True,
                                      rdo=rdo)
        self._propagate_data_ob_stave(module_list=module_list_upper,
                                      is_on_lower_hs=False,
                                      rdo=rdo)

    def _propagate_data_ob_stave(self,
                                 module_list=[1],
                                 is_on_lower_hs=True,
                                 rdo=None):
        if rdo is None:
            rdo = self.rdo
        chip_list = self._select_hs(is_on_lower_hs, rdo=rdo)
        for module in module_list:
            for _, chip in chip_list.items():
                if chip.is_on_module(module) and chip.is_outer_barrel_master():
                    chip.setreg_mode_ctrl(IBSerialLinkSpeed=0)
                    chip.propagate_data()

    def check_chip_temperature_ob_stave(self,
                                        module_list_lower=[1],
                                        module_list_upper=[],
                                        rdo=None):
        """Checks the temperature of the chips ADCS
        (requires the chips to have read the temperature at lease once before)"""
        max_increase = 5
        temperatures = self.get_chip_temperature_ob_stave(module_list_lower=module_list_lower,
                                                          module_list_upper=module_list_upper,
                                                          verbose=False,
                                                          rdo=rdo)
        overtemperature = False
        for hs in temperatures.keys():
            temp_dict = temperatures[hs]
            for chipid in temp_dict.keys():
                temp = temp_dict[chipid]
                if temp > max_increase:
                    overtemperature = True
                    self.logger.warning(f"overtemperature on {chipid}: {temp}")
        if overtemperature:
            self.logger.info("Powering off")
            self._handle_overtemperature_ob_stave(pu_index_set=[1,2], rdo=rdo)
        return overtemperature, temperatures

    def get_chip_temperature_ob_stave(self,
                                      module_list_lower=[1],
                                      module_list_upper=[],
                                      verbose=False,
                                      rdo=None):
        """gets the temperature of all the chips in a given OB module"""
        if rdo is None:
            rdo = self.rdo
        temperatures = {}
        self.logger.info("Reading ADCs...")
        temperatures["lower"] = self._get_chip_temperature_ob_stave(module_list=module_list_lower,
                                                                    is_on_lower_hs=True,
                                                                    verbose=verbose,
                                                                    rdo=rdo)
        temperatures["upper"] = self._get_chip_temperature_ob_stave(module_list=module_list_upper,
                                                                    is_on_lower_hs=False,
                                                                    verbose=verbose,
                                                                    rdo=rdo)
        return temperatures

    def _get_chip_temperature_ob_stave(self,
                                       module_list=[1],
                                       is_on_lower_hs=True,
                                       verbose=False,
                                       rdo=None):
        """gets the temperature of all the chips in a given OB module
        relative to the first measurement"""
        if rdo is None:
            rdo = self.rdo
        chip_list = self._select_hs(is_on_lower_hs, rdo=rdo)
        temperatures = {}
        for module in module_list:
            for _, chip in chip_list.items():
                if chip.is_on_module(module) and chip.is_outer_barrel_master():
                    temperatures[chip.extended_chipid] = chip.get_temperature_difference(verbose=verbose)
        if verbose:
            self.logger.info(f"Temperatures {temperatures}")
        return temperatures

    def get_chip_temperature_ib_stave(self, verbose=False):
        temperatures = {}
        for rdo in self.rdo_list:
            gbt_channel = rdo.get_gbt_channel()
            stave_ib = self.stave(gbt_channel)
            for chip in stave_ib:
                temperatures[gbt_channel, chip.chipid] = chip.get_temperature_difference(verbose=verbose)
        if verbose:
            self.logger.info(f"Temperatures {temperatures}")
        return temperatures

    def run_full_prbs_check_ob_stave(self,
                                     module_list_lower=[1,2,3,4,5,6,7],
                                     module_list_upper=[1,2,3,4,5,6,7],
                                     rdo=None,
                                     verbose=False):
        for rdo in self.rdo_list:
            self.initialize_chips_ob_stave(module_list_lower=module_list_lower,
                                           module_list_upper=module_list_upper,
                                           rdo=rdo)
            self.initialize_readout_ob_stave(module_list_lower=module_list_lower,
                                             module_list_upper=module_list_upper,
                                             rdo=rdo)
            self.scan_idelay_ob_stave(rdo=rdo)
            self.monitor_prbs_ob_stave(module_list_lower=module_list_lower,
                                       module_list_upper=module_list_upper,
                                       rdo=rdo)

    def monitor_prbs_ob_stave(self,
                              module_list_lower=[1],
                              module_list_upper=[],
                              max_temperature=35,
                              rdo=None):
        """Monitors prbs errors and temperature for the OB stave"""
        stop = False
        #first read to have reference temperature
        self.get_chip_temperature_ob_stave(module_list_lower=module_list_lower,
                                           module_list_upper=module_list_upper,
                                           rdo=rdo)
        self.logger.info("Periodic check, press \'q\', \'enter\' and wait to quit...")
        while not stop:
            try:
                self.log_values_ob_stave(rdo=rdo)
                if self.check_temperature_ob_stave(trip_temperature=max_temperature,
                                                   pu_index_set=[1,2],
                                                   rdo=rdo):
                    break
                overtemperature, adc_temperature = self.check_chip_temperature_ob_stave(module_list_lower=module_list_lower,
                                                                                        module_list_upper=module_list_upper,
                                                                                        rdo=rdo)
                self.logger.info(f"ADC temperature (offset from first measurement): {adc_temperature}")
                if overtemperature:
                    break
                errors_present = self.check_prbs_test_ob_stave(module_list_lower=module_list_lower,
                                                               module_list_upper=module_list_upper,
                                                               rdo=rdo)
                if not errors_present:
                    self.logger.info("Prbs test okay")
                key = heardKeypress()
                if key == 'q':
                    self.logger.info("quitting...")
                    stop = True
            except KeyboardInterrupt as ki:
                self.logger.info("quitting...")
                stop = True
            except:
                raise

    def measure_avdd_at_different_voltages(self, module=0, exclude_chips_list=[]):
        dvdd=2.05
        module_list = [module]
        self.rdo.powerunit_1.setup_power_modules(avdd=1.85, dvdd=dvdd, module_list=module_list)
        #self.rdo.powerunit_1.power_on_modules(module_list=module_list)
        self.rdo.powerunit_1.log_values_modules(module_list=module_list)
        for chipid, chip in enumerate(self.chips):
            if chipid not in exclude_chips_list:
                chip.calibrate_adc()
        pu_values = {}
        adc_values = {}
        for avdd in [1.65, 1.67, 1.69, 1.71, 1.73, 1.75, 1.77, 1.79]:
            self.logger.info(avdd)
            self.rdo.powerunit_1.setup_power_modules(avdd=avdd, dvdd=dvdd, module_list=module_list)
            pu_values[avdd] = self.rdo.powerunit_1.get_values_modules(module_list=module_list)[f"module_{module}_avdd_voltage"]
            meas = {}
            for chipid, chip in enumerate(self.chips):
                if chipid not in exclude_chips_list:
                    meas[chipid] = chip.measure_adc(adc_list=[2])
            adc_values[avdd] = meas
        self._analyse_avdd_meas(adc_values, pu_values)

    def _analyse_avdd_meas(self, adc_values, pu_values):
        """Analyses differences between direct and indirect measurement of avdd"""
        mean = {}
        std = {}
        for avdd in pu_values.keys():
            assert avdd in adc_values.keys()
            mean[avdd] = {}
            std[avdd] = {}
            avdd_ls = []
            avdd_indirect_ls = []
            for chipid in adc_values[avdd].keys():
                avdd_ls.append(adc_values[avdd][chipid]['AVDD'])
                avdd_indirect_ls.append(adc_values[avdd][chipid]['AVDD_indirect'])
            mean[avdd]['AVDD'] = round(np.mean(avdd_ls),3)
            std[avdd]['AVDD'] = round(np.std(avdd_ls, ddof=1),3)
            mean[avdd]['AVDD_indirect'] = round(np.mean(avdd_indirect_ls),3)
            std[avdd]['AVDD_indirect'] = round(np.std(avdd_indirect_ls, ddof=1),3)
            mean[avdd]['delta_AVDD'] = round(np.mean([avdd_indirect_ls[i]-avdd_ls[i] for i,_ in enumerate(avdd_ls)]),3)
            std[avdd]['delta_AVDD'] = round(np.std([avdd_indirect_ls[i]-avdd_ls[i] for i,_ in enumerate(avdd_ls)], ddof=1),3)
            self.logger.info(f"{avdd} V direct (mu)\t{mean[avdd]['AVDD']}\tindirect (mu)\t{mean[avdd]['AVDD_indirect']}\tdiff (mu)\t{mean[avdd]['delta_AVDD']}")
            self.logger.info(f"{avdd} V direct (std)\t{std[avdd]['AVDD']}\tindirect (std)\t{std[avdd]['AVDD_indirect']}\tdiff (std)\t{std[avdd]['delta_AVDD']}")
        return mean, std

    def calibrate_voltage_offset_all_powerunits(self):
        raise DeprecationWarning("use calculate_voltage_offset instead")

    def test_pb_overtemperature(self):
        """Logs the temperature of the powerboard and checks the status of the power channels"""
        while True:
            try:
                self.rdo_list[1].powerunit_1.log_values_modules(module_list=[0,1,2,3,4,5,6,7])
                time.sleep(0.5)
            except KeyboardInterrupt:
                self.logger.info("Stopping test now")
            except:
                raise

    def update_pu_offsets(self, layer=None, rdo=None):
        """Prints the power unit offset to a yml file. Yml file saved in ../config/powerunit_offsets, with the following format: L<layer number>_<stave number>.yml
        """

        if layer is None:
            layer = self.layer
        else:
            layer = LayerList[layer]

        self.load_powerunit_offset_file()

        for rdo in self.rdo_list:
            offsets = self.calculate_voltage_offset(layer=layer, rdo=rdo)
            self._pu_calibration.update(offsets)

        with open(self._pu_calibration_fpath, 'w') as json_output_file:
          json.dump(obj=self._pu_calibration, fp=json_output_file, sort_keys=True, indent=4)

    def calculate_voltage_offset(self, avdd=1.82, dvdd=1.82, layer=None, rdo=None):
        """ Calculates the voltage offset between the digital potentiometer and the adc on the powerboard.
        """
        if rdo is None:
            rdo = self.rdo
        if layer is None:
            layer = self.layer
        else:
            layer = layer

        module_list = [0,1,2,3,4,5,6,7]
        if layer is LayerList.OUTER:
            pu_index_set = [1,2]
            self.power_on_ol_stave(powerunit_1_module_list=module_list, powerunit_2_module_list=module_list, rdo=rdo, avdd=avdd, dvdd=dvdd, no_offset=True, compensate_v_drop=False)
        elif layer is LayerList.MIDDLE:
            pu_index_set = [1]
            self.power_on_ml_stave(rdo=rdo, avdd=avdd, dvdd=dvdd, no_offset=True, compensate_v_drop=False)
        elif layer is LayerList.INNER:
            self.power_on_ib_stave(rdo=rdo, avdd=avdd, dvdd=dvdd, no_offset=True,
                                   internal_temperature_limit=30,
                                   compensate_v_drop=False,
                                   check_interlock=False)
            pu_index_set = [1]
            time.sleep(2)  # allow the system to settle
        elif layer is LayerList.NO_PT100:
            self.logger.warning("If your setup has no PT100, please specify the layer as an argment to the method. e.g. ./testbench.py caclulate_voltage_offset --layer=INNER")
            raise NotImplementedError
        else:
            self.logger.warning("INVALID LAYER. Must be OUTER, MIDDLE or INNER. NO_PT100 is not possible!")
            raise NotImplementedError

        pu_names = [rdo.identity.get_stave_name(), f"{rdo.identity.get_stave_name()}_2"]

        pu_list = self._get_pu_list(pu_index_set, rdo=rdo)
        offsets = {}
        for index, powerunit in enumerate(pu_list):
            offsets_temp = powerunit.powerunit_offset(avdd=avdd, dvdd=dvdd, module_list=module_list)
            offsets_temp["offset_avdd"] = offsets_temp.pop("avdd")
            offsets_temp["offset_dvdd"] = offsets_temp.pop("dvdd")
            if layer is LayerList.INNER:
                for i in range(1,8):
                    offsets_temp["offset_avdd"][i] = "0x12"
                    offsets_temp["offset_dvdd"][i] = "0x12"
            offsets.update({pu_names[index]: offsets_temp})

        if self.layer is LayerList.OUTER:
            self.power_off_ob_stave(rdo=rdo)
        elif self.layer is LayerList.MIDDLE:
            self.power_off_ml_stave(rdo=rdo)
        elif self.layer is LayerList.INNER:
            self.power_off_ib_stave(rdo=rdo, disable_power_interlock=True)
        else:
            raise NotImplementedError

        return offsets

    def measure_cable_resistance(self, module_list=[0,1,2,3,4,5,6], verbose=True, powerunit_number=1, cable_length=6.65, disable_manchester=True, driver_dac=12, pre_dac=12, pll_dac=12, rdo=None):
        """
        Calculates the voltage drop from the intended on chip voltage to the chip ADC. Method
        uses voltage measured with on chip ADC and so suffers from inaccuracies
        in on chip ADC. FOR OB ONLY - resistances already implemented for IB.
        """
        if rdo is None:
            rdo = self.rdo
        assert powerunit_number in [1,2]
        pu_list = self._get_pu_list([powerunit_number], rdo=rdo)
        pu = pu_list[0]
        assert len(pu_list) == 1
        chip_list = [16,24,32,40,48,56,64,72,80,88,96,104,112,120] # master chips
        pb = {'dv':0., 'av':0., 'di':0., 'ai':0.}
        chip_voltage = {i:{'dv':0., 'av':0.} for i in chip_list}
        chip_voltage['avg'] = {'dv':0., 'av':0.}
        avdd=1.72
        dvdd=1.72
        if powerunit_number == 1:
            self.power_on_ol_stave(powerunit_1_module_list=module_list, powerunit_2_module_list=[], avdd=avdd, dvdd=dvdd, rdo=rdo)
        elif powerunit_number == 2:
            self.power_on_ol_stave(powerunit_1_module_list=[], powerunit_2_module_list=module_list, avdd=avdd, dvdd=dvdd, rdo=rdo)
        self.initialize_chips_ob_stave(module_list_lower=[1,2,3,4,5,6,7], module_list_upper=[1,2,3,4,5,6,7], rdo=rdo)

        self.setup_sensors_ob_stave(module_list_lower=[1,2,3,4,5,6,7],
                                    module_list_upper=[1,2,3,4,5,6,7],
                                    disable_manchester=disable_manchester,
                                    driver_dac=driver_dac,
                                    pre_dac=pre_dac,
                                    pll_dac=pll_dac,
                                    avdd=avdd,
                                    dvdd=dvdd,
                                    rdo=rdo)

        time.sleep(1)

        meas = pu.get_values_module(0)
        for s in ['d', 'a']:
            pb[s+'v'] = pu._code_to_vpower(meas['module_0_'+s+'vdd_voltage'])
            pb[s+'i'] = pu._code_to_i(meas['module_0_'+s+'vdd_current'])

        for chipid in chip_list:
            if powerunit_number == 1:
                r = self.chips_ob[chipid].measure_adc(adc_list=[0,1,2,3])
            elif powerunit_number == 2:
                r = self.chips_ob[chipid+128].measure_adc(adc_list=[0,1,2,3])
            for s in ['dv', 'av']:
                chip_voltage[chipid][s] = r[s.upper()+'DD']-r[s.upper()+'SS']
                chip_voltage['avg'][s] += chip_voltage[chipid][s]
        for s in ['dv', 'av']:
            chip_voltage['avg'][s] = chip_voltage['avg'][s] / len(chip_list)

        self.power_off_ob_stave(rdo=rdo)
        time.sleep(3)

        if verbose:
            self.logger.info(f"voltage drop avdd: {avdd - chip_voltage['avg']['av']}. voltage drop dvdd: {dvdd - chip_voltage['avg']['dv']}")
            self.logger.info('R_d = {:.3f} R'.format(1000.*(pb['dv']-chip_voltage['avg']['dv'])/pb['di']))
            self.logger.info('R_a = {:.3f} R'.format(1000.*(pb['av']-chip_voltage['avg']['av'])/pb['ai']))
            for chipid in chip_list:
                self.logger.info('R_d = {:.3f} R'.format(1000.*(pb['dv']-chip_voltage['avg']['dv'])/pb['di']))
                self.logger.info('R_a = {:.3f} R'.format(1000.*(pb['av']-chip_voltage['avg']['av'])/pb['ai']))

    def check_chip_voltage_ob(self, module_list=[1,2,3,4,5,6,7], exclude_chips_list=[0], rdo=None):
        """
        Logs AVDD and DVDD with on chip ADCs for Outer Barrel staves.
        """
        if rdo is None:
            rdo = self.rdo
        pu_index_set = (1,2)
        pu_list = self._get_pu_list(pu_index_set, rdo=rdo)
        for powerunit in pu_list:
            for module in module_list:
                meas = powerunit.get_values_module(module)
                dv = powerunit._code_to_vout(meas[f"module_{module}_dvdd_voltage"])
                av = powerunit._code_to_vout(meas[f"module_{module}_avdd_voltage"])
                di = powerunit._code_to_i(meas[f"module_{module}_dvdd_current"])
                ai = powerunit._code_to_i(meas[f"module_{module}_avdd_current"])

        self.logger.info("------------------ On chip ADC voltages ----------------")
        chip_list = self.chips_ob
        adcs = {i:{'AVDD':0., 'DVDD':0.} for i in chip_list}
        self.initialize_chips_ob_stave(module_list_lower=module_list, module_list_upper=module_list)
        with open('onChipDigVoltages.txt', 'w+') as f:
            f.write(' ')
        with open('onChipAnaVoltages.txt', 'w+') as ff:
            ff.write(' ')
        with open('chipIds.txt', 'w+') as fff:
            fff.write(' ')
        for chipid in chip_list:
            self.logger.info(f"chipid: {chipid}")
            if chipid not in exclude_chips_list:
                chip_list[chipid].calibrate_adc()
                adc_list = ['AVDD', 'DVDD']
                adcs[chipid]['AVDD'] = chip_list[chipid].measure_adc(adc_list=[AdcIndex.AVDD])
                adcs[chipid]['DVDD'] = chip_list[chipid].measure_adc(adc_list=[AdcIndex.DVDD])
                with open('onChipDigVoltages.txt', 'a') as f:
                    print(adcs[chipid]['DVDD']['DVDD'], file=f)
                with open('onChipAnaVoltages.txt', 'a') as ff:
                    print(adcs[chipid]['AVDD']['AVDD'], file=ff)
                with open('chipIds.txt', 'a') as fff:
                    print(chipid, file=fff)

    def test_swt_all(self, nrtests=1000, use_ru=True):
        """Tests the SWT (Write/Read if use_ru, else checks the loopback)"""
        if not use_ru:
            self.logger.warning("A loopback is supposed to be active for the test to work!")
        self.cru.reset_sc_cores()
        for rdo in self.rdo_list:
            self.logger.info(f"RDO on channel {rdo.get_gbt_channel()}")
            rdo.test_swt(nrtests=nrtests, use_ru=use_ru)

    def test_radmon_issue_515(self, rdo=None, nrtests=10000):
        if rdo is None:
            rdo = self.rdo
        rdo.radmon.reset_all_counters()
        for i in range(nrtests):
            rdo._datalane_monitor_ob.reset_all_counters()
            if rdo.identity.is_ib():
                rdo.alpide_control.read_chip_reg(0, 0)
            else:
                rdo.alpide_control.read_chip_reg(0, 24)
        if rdo.radmon.is_xcku_without_seus():
            self.logger.info("Test succeeded without errors")
            return True
        else:
            self.logger.error(f"Test failed with {rdo.radmon.read_counters()['FULL_DESIGN']} errors")
            return False

    def produce_issue_515(self, nrtests=10):
        nr_faults = 0
        power_on = self.power_on_ol_stave
        power_off = self.power_off_ol_stave

        for i in range(nrtests):
            self.program_all_xcku()
            time.sleep(0.5)
            power_on(compensate_v_drop=False)
            time.sleep(0.5)

            if not self.test_radmon_issue_515():
                nr_faults += 1

            power_off()

        if nr_faults > 0:
            self.logger.error(f"Test failed with {nr_faults} errors")
            return False
        else:
            self.logger.info("Test succeeded without errors")

    def test_pu_controller_issue_176(self,
                                     internal_temperature_limit=26,
                                     internal_temperature_low_limit=10,
                                     avdd=1.95, dvdd=1.95,
                                     avdd_current=1.5, dvdd_current=1.5):
        """Tests for the problem described in issue 176
        (https://gitlab.cern.ch/alice-its-wp10-firmware/RU_mainFPGA/issues/176):
        - Enables several power board modules
        - makes one of them trip
        - then tries to turn off all modules
        - then checks that all modules are disabled"""

        rdo = self.rdo
        bb = 0
        module_list = [1, 2, 3, 4]
        turn_off_module = 2

        pwr_enable_mask = 0
        bias_enable_mask = 0
        ad_enable_mask = 0
        for module in module_list:
            if bb != 0:
                bias_enable_mask = bias_enable_mask | (0x1 << module)
            pwr_enable_mask = pwr_enable_mask | (0x1 << module)
            ad_enable_mask = ad_enable_mask | (0x3 << (module * 2))
        mask = ~(0x1 << (turn_off_module * 2))
        turn_off_mask = ad_enable_mask & mask

        rdo.powerunit_1.initialize()
        rdo.powerunit_1.controller.enable_temperature_interlock(internal_temperature_limit=internal_temperature_limit,
                                                                internal_temperature_low_limit=internal_temperature_low_limit)
        rdo.powerunit_1.setup_power_modules(module_list=module_list, check_interlock=False,
                                        avdd=avdd, dvdd=dvdd, bb=bb,
                                        avdd_current=avdd_current, dvdd_current=dvdd_current)
        rdo.powerunit_1.power_on_modules(module_list=module_list,
                                     backbias_en=(bb!=0),
                                     check_interlock=False)

        # now enable the power interlock with the modules powered in the masks
        rdo.powerunit_1.controller.enable_power_bias_interlock(pwr_enable_mask, bias_enable_mask)

        self.logger.info("After powering all:")
        pwr_enable, bias_enable = rdo.powerunit_1.log_enable_status()
        assert (pwr_enable == ad_enable_mask) and (bias_enable == bias_enable_mask), "Enable masks incorrrect after powering all"

        # now disable one bit to make it trip in modules 1-4
        self.logger.info(f"Now tripping module {turn_off_module}")
        rdo.powerunit_1.enable_power_with_mask(turn_off_mask)
        time.sleep(0.1)  # wait a little to let the masks take effect
        tripped_pwr = rdo.powerunit_1.controller.get_tripped_power_enables()
        self.logger.info(f"Power enables that tripped: 0x{tripped_pwr:x}")
        assert tripped_pwr == turn_off_mask, "Tripped power enables incorrect"

        mask = ~(0x2 << (turn_off_module * 2))
        pwr_tripped_expected = turn_off_mask & mask
        self.logger.info("After trip:")
        pwr_enable, bias_enable = rdo.powerunit_1.log_enable_status()
        assert (pwr_enable == pwr_tripped_expected) and (bias_enable == 0), "Enable masks incorrrect after trip"

        self.logger.info("Now trying to disable all")
        rdo.powerunit_1.enable_power_with_mask(0)
        time.sleep(0.1)  # wait a little to let the mask take effect
        self.logger.info("After disabling all:")
        pwr_enable, bias_enable = rdo.powerunit_1.log_enable_status()
        assert (pwr_enable == 0) and (bias_enable == 0), "Enable masks incorrrect after disabling all"

        rdo.powerunit_1.power_off_all(disable_power_interlock=True)
        time.sleep(1)
        rdo.powerunit_1.log_values_modules()
        self.logger.info("All off!")
        return True

    def full_eye(self,
                 driver_dac=0x8,
                 pre_dac=0x8,
                 pll_dac=0x8,
                 pll_stages=4,
                 chipids=[0,1,2,3,4,5,6,7,8],
                 transceivers=[0,1,2,3,4,5,6,7,8],
                 test_use_prbs_scan=True,
                 eyescan_file='eyescan_flp',
                 eyescan_transceiver=0,
                 eyescan_hsteps=16,
                 eyescan_vsteps=16,
                 vertical_range=3,
                 eyescan_init_prescale=6,
                 eyescan_final_prescale=8,
                 eyescan_skip_center=True,
                 rdo=None):
        """Runs a full eye adaptive scan on the eyescan_transceiver.
        In parallel it runs DAQ/PRBS on all the other selected chips.

        chips configuration: (the usuals)
            driver_dac
            pre_dac
            pll_dac
            pll_stages

        setup_configuration:
            chipids:      Active Sensors
            transceivers: Active Transceivers
            rdo:          Readout unit (for iteration)

        test_configuration:
            test_use_prbs_scan: Run PRBS pattern on sensor during scan

        eyescan_configuration:
            eyescan_file:           Filename root (reserved)
            eyescan_transceiver:    Transceiver to be used for the scan
            eyescan_hsteps:         Number of horizontal points
            eyescan_vsteps:         Number of vertical points
            vertical_range:         Voltage resolution per code: 00 -> 1.5mV, 01 -> 1.8mV, 10 -> 2.2mV, 11 -> 2.8mV
            eyescan_init_prescale:  Starting prescale. Max Nr. samples per point: 20 * 2**16 * 2**(1 + prescale)
            eyescan_final_prescale: Maximum Prescale to scan to
            eyescan_skip_center:    Skip Center points (after successive 0 samples are found on this Prescale, following points are ignored)
        """
        max_retries = 10
        okay = False
        retries = 0
        while not okay and retries <= max_retries:
            self._setup_eye(driver_dac=driver_dac,
                            pre_dac=pre_dac,
                            pll_dac=pll_dac,
                            pll_stages=pll_stages,
                            chipids=chipids,
                            transceivers=transceivers,
                            test_use_prbs_scan=test_use_prbs_scan,
                            rdo=rdo)
            eyescan, okay = self._check_eye(eyescan_transceiver=eyescan_transceiver,
                                            vertical_range=vertical_range,
                                            rdo=rdo)
            retries += 1
            if not okay:
                self.logger.warning("setup failed, trying again!")
        if not okay:
            msg = f"Setup failed after {max_retries} retries, Stopping test!"
            self.logger.error(msg)
            raise RuntimeError(msg)
        alpide_settings = (driver_dac,pre_dac,pll_dac,pll_stages)
        self._get_eye(eyescan=eyescan,
                      chipids=chipids,
                      transceivers=transceivers,
                      eyescan_transceiver=eyescan_transceiver,
                      eyescan_file=eyescan_file,
                      eyescan_hsteps=eyescan_hsteps,
                      eyescan_vsteps=eyescan_vsteps,
                      eyescan_init_prescale=eyescan_init_prescale,
                      eyescan_final_prescale=eyescan_final_prescale,
                      eyescan_skip_center=eyescan_skip_center,
                      alpide_settings=alpide_settings,
                      rdo=rdo)

    def check_eye_start_errors(self,
                               chipids,
                               test_use_prbs_scan=True,
                               rdo=None):
        if rdo is None:
            rdo = self.rdo

        if test_use_prbs_scan:
            return sum(self.check_prbs_test_gth(chips=chipids,
                                                rdo=rdo))
        else:
            raise NotImplementedError("Update to new readout!")
            # TODO: update
            #decode_errors = rdo.datapath_monitor_ib.read_counters(counters=['DECODE_ERROR_COUNT'])
            all_errors = 0
            raise NotImplementedError("Update to new readout!")
            # TODO: update
            #for lane,count in decode_errors:
                # if count['DECODE_ERROR_COUNT'] > 0:
                #     self.logger.error("Link %d: %d Decoding Errors observed", lane, count['DECODE_ERROR_COUNT'])
                #     all_errors += count['DECODE_ERROR_COUNT']
            return all_errors

    def _setup_eye(self,
                   pll_dac=0x8,
                   driver_dac=0x8,
                   pre_dac=0x8,
                   pll_stages=4,
                   chipids=[0,1,2,3,4,5,6,7,8],
                   transceivers=[0,1,2,3,4,5,6,7,8],
                   test_use_prbs_scan=True,
                   rdo=None
                   ):
        if rdo is None:
            rdo = self.rdo
        assert isinstance(chipids, (list,tuple))
        assert isinstance(transceivers, (list,tuple))
        assert len(set(chipids))==len(set(transceivers))

        rdo.initialize()
        rdo.gth.set_transceivers(transceivers)
        ch = Alpide(rdo, chipid=0x0F)
        ch.reset()
        self.setup_sensors(disable_manchester=0,
                           pll_dac=pll_dac, pll_stages=pll_stages,
                           driver_dac=driver_dac, pre_dac=pre_dac)
        self.setup_readout(rdo=rdo)
        if test_use_prbs_scan:
            self.setup_prbs_test_gth(chipids, rdo=rdo)
        # Check prbs is setup properly
        time.sleep(2)
        assert self.check_eye_start_errors(chipids=chipids, test_use_prbs_scan=test_use_prbs_scan, rdo=rdo) == 0, "Errors in Stream: Not set up?"

    def _check_eye(self,
                   eyescan_transceiver=0,
                   vertical_range=3,
                   rdo=None
                   ):
        if rdo is None:
            rdo = self.rdo

        transceiver = 0
        rdo.gth.set_transceivers([eyescan_transceiver])
        eyescan = ru_eyescan.EyeScanGth(rdo.gth, vertical_range=vertical_range)
        eyescan.initialize()
        eyescan._eye_scan_point_setup(offset_h=0,offset_v=0,prescale=0,ut_sign=0,readback=True,verbose=True)
        eyescan._eye_scan_point_start()
        time.sleep(0.3)
        okay = False
        if eyescan._is_eye_scan_point_done():
            if eyescan._read_counts()[1]==0:
                okay = True
        return eyescan, okay

    def _get_eye(self,
                 eyescan,
                 eyescan_transceiver=0,
                 chipids=[0,1,2,3,4,5,6,7,8],
                 transceivers=[0,1,2,3,4,5,6,7,8],
                 eyescan_file='eyescan_flp',
                 eyescan_hsteps=16,
                 eyescan_vsteps=16,
                 eyescan_init_prescale=6,
                 eyescan_final_prescale=8,
                 eyescan_skip_center=True,
                 test_use_prbs_scan=True,
                 alpide_settings=(8,8,8,4),
                 rdo=None
                 ):
        if rdo is None:
            rdo = self.rdo
        assert isinstance(chipids, (list,tuple))
        assert isinstance(transceivers, (list,tuple))
        assert len(set(chipids))==len(set(transceivers))
        assert eyescan_transceiver in transceivers

        # Adaptive eye scanning with PRBS in background on all chips
        rdo.gth.set_transceivers(transceivers)
        rdo.datapath_monitor_ib.reset_all_counters()
        rdo.gth.reset_prbs_counter()
        start = time.time()

        rdo.gth.set_transceivers([eyescan_transceiver])

        # Adaptive Eye scanning
        func = None
        #func = bathtub_func
        folder_path = os.path.join(script_path, "eyes")
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        _,l,st=rdo.identity.get_decoded_fee_id()
        d,p,c,s = alpide_settings
        filename = os.path.join(folder_path, f"L{l}_{st:02}_{eyescan_file}_d{d:01x}p{p:01x}c{c:01x}s{s}_chip_{eyescan_transceiver}_vr{eyescan.eyescan_vs_range}.csv")
        resume = True
        verbose = False

        data = eyescan.eye_scan_adaptive(v_steps=eyescan_vsteps,
                                         h_steps=eyescan_hsteps,
                                         prescale=eyescan_init_prescale,
                                         ber=eyescan_final_prescale,
                                         resume=resume,
                                         output_file_name=filename,
                                         verbose=verbose,
                                         func=func,
                                         no_center=eyescan_skip_center)

        rdo.gth.set_transceivers(transceivers)
        errors = self.check_eye_start_errors(chipids=chipids, test_use_prbs_scan=test_use_prbs_scan, rdo=rdo)
        self.logger.info(f"After {time.time()-start:.2f} s, {errors} errors")

    def test_trigger(self, num_trigger=10):
        self.cru.initialize()
        self.ltu.send_eoc()
        self.ltu.send_eot()
        time.sleep(0.1) # Wait for EOX to be received before resetting counter
        for rdo in self.rdo_list:
            rdo.initialize()
            # TODO: Fix
            raise NotImplementedError("Update to new readout!")
            # #rdo.trigger_handler.set_trigger_source_mask(0x2)
            # rdo.trigger_handler.set_opcode_gating(1)
            # rdo.trigger_handler.reset_counters()
            # rdo.gbtx0_swt.setreg_coarse_delay(2,4)
            # assert rdo.gbtx0_swt.getreg_coarse_delay(2) == 4, "Coarse delay not properly set"
        self.ltu.send_sot()
        self.ltu.send_physics_trigger(rate=1000, num=num_trigger, start_stop=False)
        time.sleep(1)
        self.ltu.send_eot()
        time.sleep(0.1)
        echoed_0 = None
        for rdo in self.rdo_list:
            counters = rdo.trigger_handler.read_counters()
            # TODO: Fix
            raise NotImplementedError("Update to new readout!")
            # #rdo.trigger_handler.set_trigger_source_mask(0x7)
            # rdo.trigger_handler.set_opcode_gating(0)
            # orbits = counters["ORBIT"]
            # echoed = counters["TRIGGER_ECHOED"]
            # if echoed_0 is None:
            #     echoed_0 = echoed
            #     gbt_ch_0 = gbt_ch
            # for counter, value in counters.items():
            #     if counter in ["TRIGGER_FIFO_0_FULL", "TRIGGER_FIFO_0_OVERFLOW", "TRIGGER_FIFO_1_FULL", "TRIGGER_FIFO_1_OVERFLOW", "TRIGGER_FIFO_2_FULL", "TRIGGER_FIFO_2_OVERFLOW", "DEAD_00", "DEAD_01"]:
            #         continue
            #     elif counter in ["TF"]:
            #         if value == 0:
            #             self.logger.warning(f"RU {gbt_ch}: {counter} not greater than 0")
            #         elif value != math.floor(orbits/256) and value != math.floor(orbits/256)+1:
            #             self.logger.warning(f"RU {gbt_ch}: {counter} should be same as floor(orbits/256) (+1): {math.floor(orbits/256)} (+1), was {value}")
            #     elif counter in ["ORBIT", "HBA"]:
            #         if value == 0:
            #             self.logger.warning(f"RU {gbt_ch}: {counter} not greater than 0")
            #         elif value != orbits:
            #             self.logger.warning(f"RU {gbt_ch}: {counter} should be same as orbits: {orbits}, was {value}")
            #     elif counter in ["TRIGGER_IGNORED"]:
            #         if value == 0:
            #             self.logger.warning(f"RU {gbt_ch}: {counter} not greater than 0")
            #         elif value != orbits-echoed:
            #             self.logger.warning(f"RU {gbt_ch}: {counter} should be same as orbits-echoed: {orbits-echoed}, was {value}")
            #     elif counter in ["HBR"]:
            #         if value == 0:
            #             self.logger.warning(f"RU {gbt_ch}: {counter} not greater than 0")
            #         elif value != orbits-echoed+1:
            #             self.logger.warning(f"RU {gbt_ch}: {counter} should be same as orbits-echoed+1: {orbits-echoed+1}, was {value}")
            #     elif counter in ["PROCESSED_TRIGGERS"]:
            #         if value != num_trigger+orbits:
            #             self.logger.warning(f"RU {gbt_ch}: Number of {counter} should be {num_trigger+orbits}, was {value}")
            #     elif counter in ["SOT", "EOT"]:
            #         if value != 1:
            #             self.logger.warning(f"RU {gbt_ch}: Number of {counter} should be 1, was {value}")
            #     elif counter in ["PHYSICS", "TRIGGER_GATED"]:
            #         if value != num_trigger:
            #             self.logger.warning(f"RU {gbt_ch}: Number of {counter} should be {num_trigger}, was {value}")
            #     elif counter in ["TRIGGER_ECHOED"]:
            #         if value != echoed_0:
            #             self.logger.warning(f"RU {gbt_ch}: {counter} not same as on RU {gbt_ch_0}, should be {echoed_0}, was {value}")
            #     else:
            #         if value != 0:
            #             self.logger.warning(f"RU {gbt_ch}: {counter} should be 0, was {value}")
            # self.logger.info(f"RU {gbt_ch}: Trigger test completed")

    def can_hlp_test_loop(self, githash_expect, wait_time=60, rdo=None):
        """Run several CAN transactions in a loop"""
        assert self.use_can_comm, "Can only be run with CAN communication"

        if rdo is None:
            rdo = self.rdo

        rdo.comm.bus.set_filters()
        rdo.comm.enable_rderr_exception()
        rdo.comm.reset_hlp_error_counters()

        read_attempts = 0
        read_success = 0
        write_attempts = 0
        write_success = 0
        total_tests = 0
        failed_tests = 0

        start = time.time()
        self.logger.info(f"wait {wait_time} seconds")

        while (time.time() - start) < wait_time:
            try:
                test_failed = False
                total_tests += 1

                # read githash and compare to expected value
                githash_read = rdo.identity.get_git_hash()
                read_attempts += 2
                if githash_read == githash_expect:
                    read_success += 2
                else:
                    test_failed = True

                # write and read a random number to the CAN test register:
                rand_data = random.randint(0, 0xffff)
                write_attempts += 1
                rdo.can_hlp.write(ws_can_hlp.WsCanHlpAddress.TEST_REG, rand_data)
                read_attempts += 1
                read_data = rdo.can_hlp.read(ws_can_hlp.WsCanHlpAddress.TEST_REG)
                if rand_data == read_data:
                    write_success += 1
                    read_success += 1
                else:
                    test_failed = True

                if test_failed:
                    failed_tests += 1

            except WishboneReadError:
                failed_tests += 1

            except KeyboardInterrupt:
                self.logger.info("keyboard interrupt")
                break

        self.logger.info(f"Number of failed test iterations: {failed_tests}/{total_tests}")
        self.logger.info(f"Successful reads: {read_success}/{read_attempts}")
        self.logger.info(f"Successful writes: {write_success}/{write_attempts}")

        self.logger.info(f"Wrong reponses: {rdo.comm.get_wrong_response_count()}")
        self.logger.info(f"Wrong IDs: {rdo.comm.get_wrong_id_count()}")

        self.logger.info(f"{(total_tests/(time.time()-start)):0.2f} test iterations per second")
        self.logger.info(f"{((read_attempts+write_attempts)/(time.time()-start)):0.2f} attempted transactions per second")
        self.logger.info(f"{(read_success+write_success)/(time.time()-start):0.2f} successful transactions per second")
        self.logger.info(f"Average test iteration attempt time {(time.time()-start)/(total_tests):e}s")
        self.logger.info(f"Average transaction attempt time {(time.time()-start)/(read_attempts+write_attempts):e}s")

        try:
            self.logger.info("")
            self.logger.info(f"can_reg_rx_msg_count: {rdo.can_hlp.get_rx_msg_count()}")
            self.logger.info("can_reg_tx_msg_count: {rdo.can_hlp.get_tx_msg_count()}")
            self.logger.info(f"can_reg_read_count: {rdo.can_hlp.get_hlp_read_count()}")
            self.logger.info(f"can_reg_write_count: {rdo.can_hlp.get_hlp_write_count()}")
            self.logger.info(f"can_reg_status_alert_count: {rdo.can_hlp.get_hlp_status_alert_count()}")
            self.logger.info(f"can_reg_unknown_count: {rdo.can_hlp.get_hlp_unknown_count()}")

        except Exception:
            self.logger.error("Got exception while reading count registers after test.")

    def submit_log_entry(self, test, comment):
        """
        Creates a Logbook object if necessary,
        submits the log entry to ALICE ITS RUN3 logbook
        """
        if self.logbook is None:
            self.logbook = logbook.Logbook(subrack=self.subrack,
                                           group='WP10',
                                           dry=False)
        self.logbook.submit_log_entry(test=test, comment=comment)

    def monitor_lol(self, sleep=60):
        """Monitors GBTx loss of lock on clock received from the CRU.
        Tries to identify issues, logs and tries to resume the test"""
        monitor = True
        test = 'Monitor LOL'
        self.initialize_all_rdos()
        self.cru.initialize()
        names = {rdo.get_gbt_channel():rdo.identity.get_stave_name() for rdo in self.rdo_list}
        self.logger.info(f'Staves under observation: {names}')
        self.log_all_lol_counters()
        while monitor:
            try:
                global_lol, single_lol = self.is_any_lol()
                single_lol = {names[k]: v for k,v in single_lol.items()}
                if global_lol:
                    msg = 'GLOBAL LOL observed.'
                    msg += '\tIt might be related to https://gitlab.cern.ch/alice-its-wp10-firmware/CRU_ITS/issues/113\n'
                    msg += f'\tGlobal LOL {global_lol}\n'
                    msg += f'\tPer RU LOL {single_lol}\n'
                    msg += f'\tStaves are gbt_channel:stave=>{names}\n'
                    self.logger.error(msg)
                    self.submit_log_entry(test,msg)
                elif True in single_lol.values():
                    lol_channels = [k for k,value in single_lol.items() if value is True]
                    msg = f'SINGLE LOL observed for channels {lol_channels}\n'
                    msg += '\tIt might be related to https://gitlab.cern.ch/alice-its-wp10-firmware/CRU_ITS/issues/91\n'
                    msg += f'\tGlobal LOL {global_lol}\n'
                    msg += f'\tPer RU LOL {single_lol}\n'
                    msg += f'\tStaves are gbt_channel:stave=>{names}\n'
                    self.logger.error(msg)
                    self.submit_log_entry(test,msg)
                else:
                    self.logger.info(f"All good: global LOL = {global_lol}, single LOL = {single_lol}")
                time.sleep(sleep)
            except KeyboardInterrupt:
                # User action
                self.logger.info("KeyboardInterrupt: exiting...")
                monitor = False
                try:
                    self.cru.initialize()
                    self.log_all_lol_counters()
                except TimeoutError:
                    # initialise fails during test stop. Log and abort
                    self.logger.error("CRU not initialising after test stop.")
                    self.logger.error("RUs might be powered off. Aborting...")
                    self.logger.error("CRU might be in a bad state!")
            except TimeoutError:
                # intialise fails during test: retry and continue
                self.logger.error("CRU not initialising during test.")
                self.logger.error(f"RUs might be powered off. Waiting {sleep} s and then retrying...")
                time.sleep(sleep)
                try:
                    self.cru.initialize()
                except TimeoutError:
                    # retry for initialise after {sleep} s, abort if fails again
                    self.logger.error("CRU not initialising after retry")
                    self.logger.error("RUs might be powered off. Aborting...")
                    self.logger.error("CRU might be in a bad state!")
                    monitor = False
            except Exception as e:
                # Generic error
                self.logger.error("Non cathegorised error occurred.")
                self.logger.error(e)
                self.logger.error(f"Waiting {sleep} s and then trying to initialize CRU...")
                time.sleep(sleep)
                try:
                    self.cru.initialize()
                except TimeoutError:
                    # retry for initialise after {sleep} s, abort if fails again
                    self.logger.error("CRU not initialising...")
                    self.logger.error("RUs might be powered off. Aborting...")
                    self.logger.error("CRU might be in a bad state!")
                    monitor = False
        self.logger.info("Done")

    def read_cru_status(self):
        """Logging utility to record o2-roc-status into a log entry.
        Be aware of CRU_ITS#152 causing troubles in case of parallel execution of o2-roc-status
        on different endpoints of the same CRU."""
        self.logger.info(f"Running o2-roc-status on {self.cru_sn} and {self.cru_sn}:1")
        msg = os.popen(f"o2-roc-list-cards; o2-roc-status --id={self.cru_sn} --onu-status; o2-roc-status --id={self.cru_sn}:1 --onu-status").read()
        self.logger.info(msg)

    def measure_ib_cable_resistance(self, json_file_name=None, check_interlock=True, rdo=None):
        if rdo is None:
            rdo = self.rdo
            # setup the powerunit offsets
            _, layer, stave = rdo.identity.get_decoded_fee_id()
            self.load_powerunit_offset_file()
            offsets = self.get_powerunit_offsets(layer_number=layer, stave_number=stave)
            rdo.powerunit_1.set_voltage_offset(offsets[1]["avdd"], offsets[1]["dvdd"])
        else:
            gbt_channel = rdo.get_gbt_channel()
            layer = self.get_layer(gbt_channel)
            stave = self.get_stave_number(gbt_channel)

        ru_name = f"L{layer}_{stave:02}"
        pu_values = {}
        chip_values = {}
        avdd = 1.65
        dvdd = 1.65
        chipids = sorted(range(9))

        pu_values[ru_name] = {'dv':[0.,0.], 'av':[0.,0.], 'di':[0.,0.], 'ai':[0.,0.]}
        chip_values[ru_name] = {i:{'dv':[0.,0.], 'av':[0.,0.]} for i in list(range(9)) + ['avg']}

        self.power_on_ib_stave(avdd=avdd, dvdd=dvdd,
                               internal_temperature_limit=30,
                               compensate_v_drop=False,
                               check_interlock=check_interlock)
        self.logger.info(f"Supply voltages set to AVDD: {avdd} V, DVDD: {dvdd} V")

        chips = [Alpide(rdo, chipid=i) for i in chipids]
        ch_bc = Alpide(rdo, chipid=0xF)  # broadcast
        ch_bc.write_opcode(Opcode.GRST)
        ch_bc.write_opcode(Opcode.PRST)
        ch_bc.setreg_mode_ctrl(1, 1, 1, 2, 1, 1, 0, 0)  # disable clock gating
        ch_bc.setreg_cmu_and_dmu_cfg(PreviousChipID=0x0,
                                     InitialToken=0x1,
                                     DisableManchester=0x1,
                                     EnableDDR=0x1)

        for istep in [0, 1]:
            if istep == 0:
                ch_bc.setreg_IBIAS(0)  # get as little analogue current as possible
            else:
                ch_bc.setreg_dtu_cfg(1, 1, 0, 8, 0, 0)  # turn on PLL
                ch_bc.setreg_dtu_dacs(8, 15, 15)  # get as much digital current as possible
                ch_bc.setreg_IBIAS(100)
            time.sleep(2)  # allow the system to settle
            meas = rdo.powerunit_1.get_power_adc_values(0)
            for s in ['d', 'a']:
                pu_values[ru_name][s + "v"][istep] = rdo.powerunit_1._code_to_vpower(meas[f"{s}vdd_voltage"])
                pu_values[ru_name][s + "i"][istep] = rdo.powerunit_1._code_to_i(meas[f"{s}vdd_current"])
            self.logger.info(ru_name + " " + str(pu_values[ru_name]))
            inputs = {"AVSS":0, "DVSS":1, "AVDD":2, "DVDD":3}
            vadc_all = {f"CHIP_{i:02d}":{adc:[] for adc in list(inputs.keys()) + ["AVDD_indirect"]} for i in chipids}
            # direct measurements
            for adc in inputs.keys():
                ch_bc.setreg_adc_ctrl(Mode=0, SelInput=inputs[adc], SetIComp=2, RampSpd=1, CompOut=0,
                                      DiscriSign=0, HalfLSBTrim=0, commitTransaction=True)
                ch_bc.setreg_cmd(CommandRegisterOpcode.ADCMEASURE, commitTransaction=True)
                time.sleep(0.0055)  # min+0.5 ms just in case
                for ch in chips:
                    vadc_all[f"CHIP_{ch.chipid:02d}"][adc].append(ch.getreg_adc_avss_value()[0])

            for chid in range(8, -1, -1):
                vadc = vadc_all[f"CHIP_{chid:02d}"]
                vadc = {k:sum(v) / len(v) for k,v in vadc.items() if len(v)}
                for s in ["dv", "av"]:
                    chip_values[ru_name][chid][s][istep] = 2. * 0.823e-3 * (vadc[s.upper() + 'DD'] - vadc[s.upper() + "SS"])
                    chip_values[ru_name]["avg"][s][istep] += chip_values[ru_name][chid][s][istep]
            for s in ["dv", "av"]:
                chip_values[ru_name]["avg"][s][istep] /= 9.
            self.logger.info(ru_name + " avg " + str(chip_values[ru_name]["avg"]))

        # Now calculate the results
        res = {}
        r = {i:{} for i in ["avg"] + [c for c in range(9)]}
        for i in r.keys():
            for s in ["d", "a"]:
                r[i][f"{s}vdd"] = round(1000. * (chip_values[ru_name][i][s + 'v'][0] - chip_values[ru_name][i][s + 'v'][1]) /
                                        (pu_values[ru_name][s + 'i'][1] - pu_values[ru_name][s + 'i'][0]), 3)

        self.logger.info(f"Rel:    DVDD = {r['avg']['dvdd']:.3f} R   AVDD = {r['avg']['avdd'] :.3f} R")
        for i in range(9):
            self.logger.info(f"Chip {i}: DVDD = {r[i]['dvdd']:.3f} R   AVDD = {r[i]['avdd']:.3f} R")
        res[ru_name] = r['avg']
        self.logger.info(f"Stave {ru_name} cable resistance: {r['avg']}")
        self.logger.info('Cable resistance measurement results\n' + json.dumps(res, indent=4))

        if json_file_name is not None:
            with open(json_file_name, "w") as json_file:
                json.dump(res, json_file, indent=4)

    def setup_readout_dry_standalone(self, trigger_period=0xDEC, inner=True, reset_other_th=True):
        """ Setup RU to be used with standalone LTU and o2-readout-exe
        """
        self.clean_all_datapaths()
        self.cru.ul_common.reset_all()
        if reset_other_th:
            self.reset_trigger_handler()
        for rdo in self.rdo_list:
            rdo.reset_daq_counters()
            rdo.trigger_handler.enable()
            rdo.trigger_handler.setup_for_continuous_mode(trigger_period_bc=trigger_period)

            rdo.trigger_handler.enable_packer(0)
            rdo.trigger_handler.enable_packer(1)
            if inner:
                rdo.trigger_handler.enable_packer(2)

    def setup_readout_calibration_standalone(self, ru_start, ru_stop, time_frames=None, test_time=None, continuous=True, trigger_period=0xDEC, inner=False):
        """ Start RU calibration run to be used with standalone o2-readout-exe

            Specify the RUs of the crate to be specifed, e.g. ru_start=0 ru_stop=6, enables RU 0-5.
        """

        assert time_frames != None or test_time != None, f"Either time_frames or test_time must be set"
        assert time_frames == None or test_time == None, f"Either time_frames or test_time bust be unset"

        self.clean_all_datapaths()
        self.reset_trigger_handler()
        for rdo in self.rdo_list[ru_start:ru_stop]:
            rdo.trigger_handler.sequencer_disable()
            rdo.trigger_handler.enable()
            rdo.trigger_handler.setup_for_continuous_mode(trigger_period_bc=trigger_period)

            rdo.trigger_handler.enable_packer(0)
            rdo.trigger_handler.enable_packer(1)
            if inner:
                rdo.trigger_handler.enable_packer(2)

            if continuous:
                rdo.trigger_handler.sequencer_set_mode_continuous()
            else:
                rdo.trigger_handler.sequencer_set_mode_triggered()

            if time_frames != None:
                rdo.trigger_handler.sequencer_set_number_of_timeframes(time_frames)
            else:
                rdo.trigger_handler.sequencer_set_number_of_timeframes_infinite(1)

            rdo.trigger_handler.sequencer_set_number_of_hb_per_timeframe(256)
            rdo.trigger_handler.sequencer_set_number_of_hba_per_timeframe(256)
            rdo.trigger_handler.sequencer_set_trigger_mode_periodic()
            rdo.trigger_handler.set_trigger_source(1)

        for rdo in self.rdo_list[ru_start:ru_stop]:
            rdo.trigger_handler.disable_timebase_sync()

        for rdo in self.rdo_list[ru_start:ru_stop]:
            rdo.trigger_handler.sequencer_enable()

        time.sleep(5)

        for rdo in self.rdo_list[ru_start:ru_stop]:
            if time_frames != None:
                while not rdo.trigger_handler.sequencer_is_done_timeframes():
                    time.sleep(5)
            else:
                time.sleep(test_time-5)

        for rdo in self.rdo_list[ru_start:ru_stop]:
            rdo.trigger_handler.sequencer_disable()


    def reset_trigger_handler(self):
        for rdo in self.rdo_list:
            rdo.trigger_handler.disable()
            rdo.trigger_handler.enable_timebase_sync()
            rdo.trigger_handler.reset_readout_master()
            rdo.trigger_handler.set_trigger_source(0)
            rdo.trigger_handler.set_opcode_gating(True)
            rdo.trigger_handler.setup_for_continuous_mode(trigger_period_bc=0xDEC)
            rdo.trigger_handler.disable_packer(0)
            rdo.trigger_handler.disable_packer(1)
            rdo.trigger_handler.disable_packer(2)

    def set_all_gbtx_idelay(self, gbtx01=450, gbtx2=450):
        for rdo in self.rdo_list:
            rdo.gbtx01_controller.set_idelay(idelay_all=gbtx01)
            rdo.gbtx2_controller.set_idelay(idelay_all=gbtx2)

def _get_local_config_file_name(filepath):
    """Adds the _local to the filename"""
    assert filepath[-4:] == ".yml", f"Config file should have .yml extention. You entered {filepath}"
    return filepath[:-4] + '_local.yml'




def parse_gbt_link_dictionaries(link_dictionary):
    """
    Parses the link dictionary from the yml file.
    The input dictionary should be format like

    {gbtx0_channel: (gbtx1_channel,gbtx2_channel,trg_channel)}
    - tuple can be replaced by None
    e.g. {gbtx_channel:None}
    RU has only SWT fibre connected

    - trg_channel can be omitted
    e.g. {gbtx0_channel: (gbtx1_channel,gbtx2_channel)}
    trg_channel is not connected on CRU

    - gbtx2_channel can be omitted if also trigger is also omitted.
      In this case there is no need to pass the tuple.
    e.g. {gbtx0_channel: (gbtx1_channel)}
    or   {gbtx0_channel: gbtx1_channel}
    only gbtx0 and gbtx1 are connected.
    """
    ctrl_and_data_link_list = []
    only_data_link_list = []
    trg_link_list = []

    if len(link_dictionary) > 0:
        MAX_CRU_CHANNELS = cru_board.MAX_CHANNELS
        for gbtx0, v in link_dictionary.items():
            assert gbtx0 in range(MAX_CRU_CHANNELS), f"Link {gbtx0} is not in range({MAX_CRU_CHANNELS})"
            try:
                gbtx1, gbtx2, trg = _parse_gbt_link_instance(v)
            except ValueError as ve:
                msg = f"Failed configuring link {gbtx0} for error: {ve}"
                raise ValueError(msg)
            ctrl_and_data_link_list.append(gbtx0)
            if gbtx1 is not None:
                assert gbtx1 in range(MAX_CRU_CHANNELS), f"Link {gbtx0}: GBTx1 value {gbtx1} is not in range({MAX_CRU_CHANNELS})"
                only_data_link_list.append(gbtx1)
            if gbtx2 is not None:
                assert gbtx2 in range(MAX_CRU_CHANNELS), f"Link {gbtx0}: GBTx2 value {gbtx2} is not in range({MAX_CRU_CHANNELS})"
                only_data_link_list.append(gbtx2)
            if trg is not None:
                assert trg in range(MAX_CRU_CHANNELS), f"Link {gbtx0}: TRG value {trg} is not in range({MAX_CRU_CHANNELS})"
                trg_link_list.append(trg)
    return ctrl_and_data_link_list, only_data_link_list, trg_link_list


def _int_or_none(v):
    """Helper function assigning None or int"""
    if v is None or v=='None':
        return None
    elif isinstance(v, int):
        return v
    else:
        raise ValueError(f"Value {v} of type {type(v)} can only be int, None, or \'None\'")


def _parse_gbt_link_instance(value):
    """
    Parses the information about the data_link_list and trigger_link_list

    raises ValueError
    """
    gbtx1 = gbtx2 = trg = None
    if value is None or value=='None':
        pass
    elif isinstance(value, int):
        gbtx1 = value
    elif isinstance(value, (tuple, list)):
        if len(value)==1:
            gbtx1 = _int_or_none(value[0])
        elif len(value)==2:
            gbtx1 = _int_or_none(value[0])
            gbtx2 = _int_or_none(value[1])
        elif len(value)==3:
            gbtx1 = _int_or_none(value[0])
            gbtx2 = _int_or_none(value[1])
            trg   = _int_or_none(value[2])
        else:
            raise ValueError(f"Incorrect len for tuple: {len(value)}")
    else:
        raise ValueError(f"Incorrect value {value} of type {type(value)}: can only be None, \'None\', int, or tuple/list")
    return gbtx1, gbtx2, trg


def configure_testbench(config_file_path, run_standalone, check_yml=False):
    ret_dict = {}
    if check_yml: # Initialises what can fail
        CRU_SN = None
        CHECK_CRU_HASH = True
        CTRL_AND_DATA_LINK_LIST = []
        ONLY_DATA_LINK_LIST = []
        TRIGGER_LINK_LIST = []
        LTU_HOSTNAME = None
        RU_MAIN_REVISION = None
        RU_MINOR_REVISION = None
        RU_TRANSITION_BOARD_VERSION = None
        POWER_BOARD_VERSION = None
        POWER_BOARD_FILTER_50HZ_AC_POWER_MAINS_FREQUENCY = None
        POWERUNIT_RESISTANCE_OFFSET_PT100 = None
        LAYER = None
        SUBRACK = None
        CRU_TYPE = None
        USE_RDO_USB = None
        USE_CAN_COMM = None

    config_file = os.path.realpath(config_file_path)
    local_config_file = _get_local_config_file_name(config_file)
    # First try a local config file
    if os.path.isfile(local_config_file):
        config_file = local_config_file
    else:
        # if that doesn't exist, try the default config file name
        if not os.path.isfile(config_file):
            if check_yml:
                warnings.warn(f"{config_file_path} not found")
            else:
                raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), config_file)
    with open(config_file) as cfg:
        cfg_data = yaml.load(cfg, Loader=yaml.SafeLoader)

    try:
        CRU_SN = cfg_data['CRU_SN']
    except KeyError:
        msg = f"Option CRU_SN not present in config file {config_file}"
        if check_yml:
            warnings.warn(msg)
        else:
            raise ValueError(msg)

    try:
        int(CRU_SN) # serial number should be int - checks agains PCIe input
    except:
        msg = f"Invalid value {CRU_SN} for option CRU_SN in config file {config_file}, must be integer value"
        if check_yml:
            warnings.warn(msg)
        else:
            raise ValueError(msg)

    try:
        CRU_TYPE = CruType[cfg_data['CRU_TYPE']]
    except KeyError:
        try:
            msg = f"Invalid value {cfg_data['CRU_TYPE']} for option CRU_TYPE in {config_file}, not in {list(CruType)}"
        except KeyError:
            msg = f"Option CRU_TYPE not present in config file {config_file}"
        if check_yml:
            warnings.warn(msg)
        else:
            raise ValueError(msg)

    try:
        CHECK_CRU_HASH = cfg_data['CHECK_CRU_HASH']
    except KeyError:
        msg = f"Option CHECK_CRU_HASH not present in config file {config_file}"
        if check_yml:
            warnings.warn(msg)
        else:
            raise ValueError(msg)

    try:
        EXPECTED_CRU_GITHASH = cfg_data['EXPECTED_CRU_GITHASH']
    except KeyError:
        msg = f"Option EXPECTED_CRU_GITHASH not present in config file {config_file}"
        if check_yml:
            warnings.warn(msg)
        else:
            raise ValueError(msg)

    try:
        int(EXPECTED_CRU_GITHASH) # serial number should be int - checks agains PCIe input
    except:
        msg = f"Invalid value {EXPECTED_CRU_GITHASH} for option EXPECTED_CRU_GITHASH in config file {config_file}, must be integer value"
        if check_yml:
            warnings.warn(msg)
        else:
            raise ValueError(msg)


    try:
        USE_RDO_USB = bool(cfg_data['USE_RDO_USB'])
    except KeyError:
        msg = f"Option USE_RDO_USB not present in config file {config_file}"
        if check_yml:
            warnings.warn(msg)
        else:
            raise ValueError(msg)

    if USE_RDO_USB:
        if (CRU_TYPE != CruType.NONE) and (CRU_TYPE != CruType.RUv0):
            msg = f"Option USE_RDO_USB can only be used with CruType.NONE or CruType.RUv0: file {config_file}"
            if check_yml:
                warnings.warn(msg)
            else:
                raise ValueError(msg)

    try:
        CTRL_AND_DATA_LINK_LIST, ONLY_DATA_LINK_LIST, TRIGGER_LINK_LIST = parse_gbt_link_dictionaries(cfg_data['LINK_DICT'])
    except ValueError as ve:
        msg = f"Error on converting option LINK_DICT in config file {config_file} to separate lists: {ve}"
        if check_yml:
            warnings.warn(msg)
            CTRL_AND_DATA_LINK_LIST = ONLY_DATA_LINK_LIST = TRIGGER_LINK_LIST = []
        else:
            raise ValueError(msg)
    except KeyError:
        msg = f"Option LINK_DICT not present in config file {config_file}"
        if check_yml:
            warnings.warn(msg)
        else:
            raise ValueError(msg)

    try:
        USE_CAN_COMM = bool(cfg_data['USE_CAN_COMM'])
    except KeyError:
        msg = f"Option USE_CAN_COMM not present in config file {config_file}"
        if check_yml:
            warnings.warn(msg)
        else:
            raise ValueError(msg)

    if USE_CAN_COMM:
        if CRU_TYPE != CruType.NONE:
            msg = f"Option USE_CAN_COMM can only be used with CruType.NONE: file {config_file}"
            if check_yml:
                warnings.warn(msg)
            else:
                raise ValueError(msg)

        CRU_SN     = None
        CRU_TYPE       = CruType.NONE
        #CTRL_AND_DATA_LINK_LIST = [] # Used to prepare the CAN node id list
        ONLY_DATA_LINK_LIST = []
        TRIGGER_LINK_LIST   = []

    try:
        LTU_HOSTNAME = cfg_data['LTU_HOSTNAME']
    except KeyError:
        msg = f"Option LTU_HOSTNAME not present in config file {config_file}"
        if check_yml:
            warnings.warn(msg)
        else:
            raise ValueError(msg)

    try:
        RU_MAIN_REVISION = cfg_data['RU_MAIN_REVISION']
    except KeyError:
        msg = f"Option RU_MAIN_REVISION not present in config file {config_file}"
        if check_yml:
            warnings.warn(msg)
        else:
            raise ValueError(msg)

    try:
        RU_MINOR_REVISION = cfg_data['RU_MINOR_REVISION']
    except KeyError:
        msg = f"Option RU_MINOR_REVISION not present in config file {config_file}"
        if check_yml:
            warnings.warn(msg)
        else:
            raise ValueError(msg)

    if (RU_MAIN_REVISION, RU_MINOR_REVISION) not in [(1,1),(2,0),(2,1)]:
        msg = f"Invalid value combination of options RU_MAIN_REVISION.RU_MINOR_REVISION {RU_MAIN_REVISION}.{RU_MINOR_REVISION} in config file {config_file}, not in {[1.1, 2.0, 2.1]}"
        if check_yml:
            warnings.warn(msg)
        else:
            raise ValueError(msg)

    try:
        RU_TRANSITION_BOARD_VERSION = ru_transition_board.TransitionBoardVersion[cfg_data['RU_TRANSITION_BOARD_VERSION']]
    except KeyError:
        try:
            msg = f"Invalid value {cfg_data['RU_TRANSITION_BOARD_VERSION']} for option RU_TRANSITION_BOARD_VERSION in {config_file}, not in {list(ru_transition_board.TransitionBoardVersion)}"
        except KeyError:
            msg = f"Option RU_TRANSITION_BOARD_VERSION not present in config file {config_file}"
        if check_yml:
            warnings.warn(msg)
        else:
            raise ValueError(msg)

    try:
        POWER_BOARD_VERSION = power_unit.PowerUnitVersion[cfg_data['POWER_BOARD_VERSION']]
    except KeyError:
        try:
            msg = f"Invalid value {cfg_data['POWER_BOARD_VERSION']} for option POWER_BOARD_VERSION in {config_file}, not in {list(power_unit.PowerUnitVersion)}"
        except KeyError:
            msg = f"Option POWER_BOARD_VERSION not present in config file {config_file}"
        if check_yml:
            warnings.warn(msg)
        else:
            raise ValueError(msg)

    try:
        POWER_BOARD_FILTER_50HZ_AC_POWER_MAINS_FREQUENCY = cfg_data['POWER_BOARD_FILTER_50HZ_AC_POWER_MAINS_FREQUENCY']
    except KeyError:
        msg = f"Option POWER_BOARD_FILTER_50HZ_AC_POWER_MAINS_FREQUENCY not present in config file {config_file}"
        if check_yml:
            warnings.warn(msg)
        else:
            raise ValueError(msg)

    try:
        POWERUNIT_RESISTANCE_OFFSET_PT100 = cfg_data['POWERUNIT_RESISTANCE_OFFSET_PT100']
    except KeyError:
        msg = f"Option POWERUNIT_RESISTANCE_OFFSET_PT100 not present in config file {config_file}"
        if check_yml:
            warnings.warn(msg)
        else:
            raise ValueError(msg)

    try:
        LAYER = LayerList[cfg_data['LAYER']]
    except KeyError:
        try:
            msg = f"Invalid value {cfg_data['LAYER']} for option LAYER in {config_file}, not in {list(LayerList)}"
        except KeyError:
            msg = f"Option LAYER not present in config file {config_file}"
        if check_yml:
            warnings.warn(msg)
        else:
            raise ValueError(msg)

    try:
        HOSTNAME = cfg_data['HOSTNAME']
    except KeyError:
        msg = f"Option HOSTNAME not present in config file {config_file}"
        if check_yml:
            warnings.warn(msg)
        else:
            raise ValueError(msg)
    if not (check_yml or USE_CAN_COMM): # it can be run everywhere
        assert os.uname().nodename in HOSTNAME, f"This testbench can only run on {HOSTNAME}. You are currently on {os.uname().nodename}"

    try:
        SUBRACK = cfg_data['SUBRACK']
    except KeyError:
        msg = f"Option SUBRACK not present in config file {config_file}"
        if check_yml:
            warnings.warn(msg)
        else:
            raise ValueError(msg)
    if str(SUBRACK).lower() == "none":
        SUBRACK = None
    else:
        if SUBRACK not in crate_mapping.subrack_lut.keys():
            msg = f"Invalid value {SUBRACK} for option SUBRACK in config file {config_file}, not in crate_mapping."
            if check_yml:
                warnings.warn(msg)
            else:
                raise ValueError(msg)

    if run_standalone:
        tb = Testbench(cru_sn=CRU_SN,
                       check_cru_hash=CHECK_CRU_HASH,
                       expected_cru_githash=EXPECTED_CRU_GITHASH,
                       ctrl_and_data_link_list=CTRL_AND_DATA_LINK_LIST,
                       only_data_link_list=ONLY_DATA_LINK_LIST,
                       trigger_link_list=TRIGGER_LINK_LIST,
                       ru_main_revision=RU_MAIN_REVISION, ru_minor_revision=RU_MINOR_REVISION,
                       ru_transition_board_version=RU_TRANSITION_BOARD_VERSION,
                       power_board_version=POWER_BOARD_VERSION,
                       power_board_filter_50hz_ac_power_mains_frequency=POWER_BOARD_FILTER_50HZ_AC_POWER_MAINS_FREQUENCY,
                       powerunit_resistance_offset_pt100=POWERUNIT_RESISTANCE_OFFSET_PT100,
                       layer=LAYER,
                       ltu_hostname=LTU_HOSTNAME,
                       subrack=SUBRACK,
                       cru_type=CRU_TYPE,
                       use_rdo_usb=USE_RDO_USB,
                       use_can_comm=USE_CAN_COMM,
                       run_standalone=run_standalone)
        return tb
    else: # for daq_test
        ret_dict['CRU_SN'] = CRU_SN
        ret_dict['CTRL_AND_DATA_LINK_LIST'] = CTRL_AND_DATA_LINK_LIST
        ret_dict['ONLY_DATA_LINK_LIST'] = ONLY_DATA_LINK_LIST
        ret_dict['TRIGGER_LINK_LIST'] = TRIGGER_LINK_LIST
        ret_dict['LTU_HOSTNAME'] = LTU_HOSTNAME
        ret_dict['RU_MAIN_REVISION'] = RU_MAIN_REVISION
        ret_dict['RU_MINOR_REVISION'] = RU_MINOR_REVISION
        ret_dict['RU_TRANSITION_BOARD_VERSION'] = RU_TRANSITION_BOARD_VERSION
        ret_dict['POWER_BOARD_VERSION'] = POWER_BOARD_VERSION
        ret_dict['POWER_BOARD_FILTER_50HZ_AC_POWER_MAINS_FREQUENCY'] = POWER_BOARD_FILTER_50HZ_AC_POWER_MAINS_FREQUENCY
        ret_dict['POWERUNIT_RESISTANCE_OFFSET_PT100'] = POWERUNIT_RESISTANCE_OFFSET_PT100
        ret_dict['LAYER'] = LAYER
        ret_dict['SUBRACK'] = SUBRACK
        ret_dict['CRU_TYPE'] = CRU_TYPE
        ret_dict['USE_RDO_USB'] = USE_RDO_USB
        ret_dict['USE_CAN_COMM'] = USE_CAN_COMM
        return ret_dict


if __name__ == "__main__":
    RUN_STANDALONE=True
    config_file_path = os.path.join(script_path, '../config/testbench.yml')
    tb = configure_testbench(config_file_path=config_file_path,
                             run_standalone=RUN_STANDALONE)

    try:
        fire.Fire(tb)
    except Exception:
        raise
    finally:
        tb.stop()
