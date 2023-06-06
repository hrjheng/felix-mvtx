"""Readout unit implementation of the Board interface."""


from collections import OrderedDict
from enum import IntEnum, unique
import json

import logging
import os
import random
import time
import warnings
import yaml
import can_hlp_comm
import usb_communication

script_path = os.path.dirname(os.path.realpath(__file__))

from alpide_control import AlpideControl
from alpide_control_monitor import AlpideControlMonitor
from drp_bridge import DrpBridge
from gbtx_controller import GBTxController
from ru_mmcm_gbtx_rxrdy_monitor import RuMmcmGbtxRxrdyMonitor
from i2c_gbtx_monitor import WsI2cGbtxMonitor
from pu_monitor import PuMonitor
from pa3_fifo import Pa3Fifo
from pa3_fifo_monitor import Pa3FifoMonitor
from power_unit import PowerUnit, PowerUnitAux
from pu_controller import PuController
from ru_calibration_lane import CalibrationLane
from ru_data_lane import DataLane
from ru_data_lane_monitor import DataLaneMonitor
from ru_dualdatapath_monitor import DatapathMonitorDualSplitAtLane, DatapathMonitorDualSplitCounters
from ru_gbt_packer import GbtPacker, GbtPackerAddress
from ru_gpio_monitor import GpioMonitor
from ru_gth_monitor import GthMonitor
from ru_readout_master import ReadoutMaster
from ru_transceiver import GthFrontend, GpioFrontend
from sca_ru import Sca_RU
from sysmon import Sysmon
from trigger_handler import TriggerHandler
from trigger_handler_monitor import TriggerHandlerMonitor
from wishbone_wait import WishboneWait
from ws_can_hlp import WsCanHlp
from ws_can_hlp_monitor import WsCanHlpMonitor
from ws_gbt_packer_monitor import GbtPackerMonitor
from ws_gbtx_flow_monitor import GbtxFlowMonitor
from ws_gbt_prbs_chk import WsGbtPrbsChk
from ws_i2c_gbtx import WsI2cGbtx, XckuI2cBadStatusError
from ws_identity import WsIdentity
from ws_clock_health_status import WsClockHealthStatus
from ws_system_reset_control import WsSystemResetControl
from ws_master_monitor import WsMasterMonitor
from ws_radiation_monitor import WsRadiationMonitor
from ws_usb_if import WsUsbif
from scrubbing_status import ScrubbingRUStatus

import gbtx
import gbt_sca
import proasic3
from proasic3_enums import FlashSelectICOpcode
from sca_o2 import Sca_O2
import ru_transition_board
import trigger
import git_hash_lut
from cru_swt_communication import CruSwtCommunication
from flx_swt_communication import FlxSwtCommunication
from sca_flx import Sca_flx
from flx_card import FlxCard


class ConfigurationMemoryMapping(object):
    """configuration register mapping"""
    alpide_vdd_on = 0


class ReadoutBoard:
    def __init__(self, comm):
        self.comm = comm
        self.logger = logging.getLogger(f"ReadoutBoard {self.get_gbt_channel()}")
        self.sca = None
        self.pa3 = None
        self.identity = None

    def initialize(self, reenable_forward_to_usb=1):
        """Initialize the readout board,
        parameter reenable_forward_to_usb is only used for RUv0"""
        pass

    def _lock_comm(self):
        self.comm._lock_comm()

    def _unlock_comm(self, force=False):
        self.comm._unlock_comm(force)

    def get_gbt_channel(self):
        """Returns the GBT channels the RU is connected to"""
        if type(self.comm) in [CruSwtCommunication, FlxSwtCommunication]:
            return self.comm.get_gbt_channel()
        else:
            return -1

    # Wishbone access functions
    def write(self, mod, addr, data, commitTransaction=True):
        """Write to specific register on the board"""
        self.comm.register_write(mod, addr, data)
        if commitTransaction:
            self.flush()

    def read(self, mod, addr, commitTransaction=True):
        """Read from specific register on the board and return tuple of reg and value"""
        self.comm.register_read(mod, addr)
        if commitTransaction:
            val = self.flush_and_read_results(expected_length=1)
            return (val[0][0], val[0][1])
        else:
            return None, None

    def read_loopback(self, mod, addr, data, commitTransaction=True):
        """Simulates a read when one of the loopback is active (CRU, GBTx, XCKU)"""
        self.comm.register_read_custom_data(mod, addr, data)
        if commitTransaction:
            return self.flush_and_read_results()
        else:
            return None

    def flush(self):
        """Flush communication buffer."""
        self.comm.flush()

    def read_results(self):
        return self.comm.read_results()

    def flush_and_read_results(self, expected_length=None):
        ret = self.comm.flush_and_read_results()
        if (expected_length is not None) and (len(ret) != expected_length):
            self.logger.warning(f"Unexpected length of result: {len(ret)}, expected length {expected_length}")
        return ret

    def read_all(self):
        """Read all pending results."""
        ret = self.comm.flush_and_read_results()
        data = []
        for item in ret:
            data.append(item[1])
        return data

    def feeid(self):
        feeid, layer, stave_nr = self.identity.get_decoded_fee_id()
        self.logger.info(f"FEE ID 0x{feeid:02X}, Layer {layer:01}, Stave NR {stave_nr:02}")

    def dna(self):
        dna_rdo = self.identity.get_dna()
        sn = self.identity.get_sn()
        if self.identity.is_2_1():
            self.logger.info(f"DNA:\t0x{dna_rdo:024X}, SN {sn:03d}, RUv2.1")
        elif self.identity.is_2_0():
            self.logger.info(f"DNA:\t0x{dna_rdo:024X}, SN {sn:03d}, RUv2.0")
        else:
            self.logger.warning(f"DNA:\t0x{dna_rdo:024X}, MISSING SERIAL NUMBER IN LUT")

    def git_hash(self):
        return self.identity.get_git_hash()

    def git_tag(self):
        raise NotImplementedError("function is defined in child classes")

    def version(self, get_pa3=True):
        msg = f"XCKU Version: \t0x{self.git_hash():07X}\t{self.git_tag()}"
        if get_pa3:
            pa3_git_hash = self.pa3.githash()
            if pa3_git_hash in git_hash_lut.pa3_githash2ver_lut:
                pa3_version = git_hash_lut.pa3_githash2ver_lut[pa3_git_hash]
            else:
                pa3_version = f"v{self.pa3.version(verbose=False)} (unofficial, self reported)"
            msg += f", PA3 Version:\t{pa3_version} 0x{pa3_git_hash:07X}"
        self.logger.info(msg)

    def uptime(self):
        ut = self.identity.get_uptime()
        tsr = self.identity.get_time_since_reset()
        self.logger.info(f"Uptime {ut:.3f} s or {ut/3600:.2f} h Since reset {tsr:.3f} s or {tsr/3600:.2f} h")

    def program_xcku_and_retry(self):
        """Program the XCKU FPGA and retries with the 4 possible FLASH blocks upon failure"""
        if type(self.comm) in [CruSwtCommunication, FlxSwtCommunication]:
            for chip_num, use_gold in ((x, y) for x in [1,2] for y in [False,True]):
                success = self.program_xcku(use_gold, chip_num)
                if success:
                    return True
            return False
        else:
            self.logger.warning("No SCA comm - Cannot program XCKU over PA3!")
            return False

    def program_xcku(self, use_gold=False, chip_num=1):
        success = self.pa3.program_xcku_and_check(use_gold=use_gold, chip_num=chip_num)
        time.sleep(2.5)
        if success:
            if not self.sca.is_xcku_programmed():
                success = False
                self.logger.error("PA3 reported success, but SCA does not see XCKU up")
        if not success:
            self.logger.error(f"Program XCKU failed with use_gold: {use_gold} chip_num: {chip_num}")
            return False
        else:
            self.logger.info(f"Program XCKU succeeded with use_gold: {use_gold} chip_num: {chip_num}")
            return True


@unique
class XckuModuleid(IntEnum):
    """Slave addresses for the RU Wisbone modules"""
    MASTER_GBTX_MONITOR      = 0
    IDENTITY                 = 1
    GTH_CONTROL              = 2
    DATALANE_MONITOR_IB      = 3
    ALPIDE_CONTROL           = 4
    I2C_GBT                  = 5
    I2C_PU1                  = 6
    I2C_PU2                  = 7
    GBTX0                    = 8
    GBTX2                    = 9
    FW_WAIT                  = 10
    RADMON                   = 11
    SYSMON                   = 12
    GBTX_FLOW_MONITOR        = 13
    USB_IF                   = 14
    MASTER_USB_MONITOR       = 15
    TRIGGER_HANDLER          = 16
    TRIGGER_HANDLER_MONITOR  = 17
    GPIO_CONTROL             = 18
    DATALANE_MONITOR_OB_1    = 19
    DATALANE_MONITOR_OB_2    = 20
    GBT_PACKER               = 21
    GTH_MONITOR              = 22
    GTH_DRP                  = 23
    GBT_PACKER_0_MONITOR     = 24
    GPIO_MONITOR             = 25
    MMCM_GBTX_RXRDY_MONITOR  = 26
    MASTER_CAN_MONITOR       = 27
    CAN_HLP                  = 28
    CAN_HLP_MONITOR          = 29
    GBT_PACKER_1_MONITOR     = 30
    SYSTEM_RESET_CONTROL     = 31
    GBT_PACKER_2_MONITOR     = 32
    CLOCK_HEALTH_STATUS      = 33
    I2C_MONITOR_GBTX         = 34
    I2C_PU1_AUX              = 35
    I2C_PU2_AUX              = 36
    I2C_PU1_CONTROLLER       = 37
    I2C_PU2_CONTROLLER       = 38
    MONITOR_PU1_MAIN         = 39
    MONITOR_PU1_AUX          = 40
    MONITOR_PU2_MAIN         = 41
    MONITOR_PU2_AUX          = 42
    GBTX2_PRBS_CHK           = 43
    PA3_FIFO                 = 44
    ALPIDE_CONTROL_MONITOR   = 45
    PA3_FIFO_MONITOR         = 46
    DATA_LANE_IB             = 47
    DATA_LANE_OB             = 48
    CALIBRATION_LANE         = 49
    READOUT_MASTER           = 50
    DEAD_00                  = 51


class Xcku(ReadoutBoard):
    GBTx0_CHARGEPUMP_DEFAULT = 15

    from ru_flashing import flash_write_configfile_to_block, flash_write_scrubfile_to_block, \
                            flash_write_file_to_block, flash_bitfiles_to_block, flash_bitfiles_to_all_blocks, \
                            get_bad_blocks, _check_bad_block_list, _check_block_validity
    from ru_scrubbing import configure_scrub_location, _configure_scrub_imagelocation, _configure_scrub_location, _configure_scrub_location_page0, run_scrub_cycle, \
                             _run_scrub_cycle, _run_scrub_cycle_location, _run_scrub_cycle_page0, \
                             run_scrub_loop, update_scrubbing_status_files, \
                             get_pa3_post_scrub_metrics, determine_post_scrub_status, \
                             check_scrub_ok, check_and_update_scrub_status_iter_locations, reflash_scrub_block, _reflash_scrub_block_location, _reflash_scrub_block_page0, \
                             reflash_all_critical_locations, flash_all_not_programmed_locations, check_scrub_and_reflash, \
                             create_and_store_new_scrubbing_status, load_scrubbing_status

    """Board implementation for Readout unit"""
    def __init__(self, comm, cru,
                 ru_main_revision,
                 ru_minor_revision,
                 transition_board_version,
                 power_board_version,
                 powerunit_resistance_offset_pt100,
                 powerunit_1_offset_avdd,
                 powerunit_1_offset_dvdd,
                 powerunit_2_offset_avdd,
                 powerunit_2_offset_dvdd,
                 layer,
                 power_board_filter_50Hz_ac_power_mains_frequency=True):
        super(Xcku, self).__init__(comm)
        self.logger = logging.getLogger(f"RU {self.get_gbt_channel()} XCKU")

        if comm is None:
            self.logger.error("RU comm is None!")
        self.comm = comm
        self.ru_main_revision = ru_main_revision
        self.ru_minor_revision = ru_minor_revision

        self._add_modules(power_board_version,
                          powerunit_resistance_offset_pt100,
                          powerunit_1_offset_avdd,
                          powerunit_1_offset_dvdd,
                          powerunit_2_offset_avdd,
                          powerunit_2_offset_dvdd,
                          layer,
                          power_board_filter_50Hz_ac_power_mains_frequency)

        if type(self.comm) != can_hlp_comm.CanHlpComm:

            self.cru = cru

            # For when CRU is RUv0-emulator
            # The RU SCA and PA3 objects are reachable only through "CRU" USB comm interface
            if type(cru) == RUv0_CRU:
                self.sca = cru.sca
                self.pa3 = cru.pa3
            elif type(cru) == FlxCard:
                self.sca = Sca_flx(comm=comm, is_on_ruv1=self.is_ruv1(), is_on_ruv2_0=self.is_ruv2_0())
                self.pa3 = proasic3.ProAsic3(sca=self.sca, gbt_channel=self.get_gbt_channel())
            else:
                self.sca = Sca_O2(comm=comm, is_on_ruv1=self.is_ruv1(), is_on_ruv2_0=self.is_ruv2_0())
                self.pa3 = proasic3.ProAsic3(sca=self.sca, gbt_channel=self.get_gbt_channel())

            self.gbtx0_sca = gbtx.GBTx(index=0, board=None, sca=self.sca)
            self.gbtx1_sca = gbtx.GBTx(index=1, board=None, sca=self.sca)
            self.gbtx2_sca = gbtx.GBTx(index=2, board=None, sca=self.sca)
            self.gbtxs_sca = [self.gbtx0_sca, self.gbtx1_sca, self.gbtx2_sca]

        self.gbtx0_swt = gbtx.GBTx(index=0, board=self, sca=None)
        self.gbtx1_swt = gbtx.GBTx(index=1, board=self, sca=None)
        self.gbtx2_swt = gbtx.GBTx(index=2, board=self, sca=None)
        self.gbtxs_swt = [self.gbtx0_swt, self.gbtx1_swt, self.gbtx2_swt]

        self._chip2connector_lut = None
        self.chip2connector_enabled = False

        self.tb = None
        self.init_transition_board(transition_board_version=transition_board_version,
                                   ru_main_revision=ru_main_revision)

        self.scrubbing_status = None

    def is_ruv1(self):
        return self.ru_main_revision==1

    def is_ruv2_0(self):
        return (self.ru_main_revision==2 and self.ru_minor_revision==0)

    def _add_modules(self,
                     power_board_version,
                     powerunit_resistance_offset_pt100,
                     powerunit_1_offset_avdd,
                     powerunit_1_offset_dvdd,
                     powerunit_2_offset_avdd,
                     powerunit_2_offset_dvdd,
                     layer,
                     power_board_filter_50Hz_ac_power_mains_frequency=True):
        """Adds all the modules to the class"""
        self._drp_bridge = DrpBridge(board_obj=self, moduleid=XckuModuleid.GTH_DRP)
        self.gth = GthFrontend(board_obj=self, moduleid=XckuModuleid.GTH_CONTROL,drp_bridge_module=self._drp_bridge)
        self.LANES_IB = self.gth.NR_TRANSCEIVERS
        self._datalane_monitor_ib = DataLaneMonitor(board_obj=self, moduleid=XckuModuleid.DATALANE_MONITOR_IB,lanes=list(range(self.LANES_IB)))
        self.lanes_ib = DataLane(board_obj=self, moduleid=XckuModuleid.DATA_LANE_IB)
        self._gth_monitor = GthMonitor(board_obj=self, moduleid=XckuModuleid.GTH_MONITOR,lanes=list(range(self.LANES_IB)))
        self.identity = WsIdentity(moduleid=XckuModuleid.IDENTITY, board_obj=self)
        self.clock_health_status = WsClockHealthStatus(moduleid=XckuModuleid.CLOCK_HEALTH_STATUS, board_obj=self)
        self.system_reset_control = WsSystemResetControl(moduleid=XckuModuleid.SYSTEM_RESET_CONTROL, board_obj=self)
        self.datapath_monitor_ib = DatapathMonitorDualSplitCounters(self._datalane_monitor_ib,self._gth_monitor)
        self.gpio = GpioFrontend(board_obj=self, moduleid=XckuModuleid.GPIO_CONTROL)
        self.lanes_ob = DataLane(board_obj=self, moduleid=XckuModuleid.DATA_LANE_OB)
        self.LANES_OB = self.gpio.NR_TRANSCEIVERS
        self._datalane_monitor_ob_1 = DataLaneMonitor(board_obj=self, moduleid=XckuModuleid.DATALANE_MONITOR_OB_1,
                                                      lanes = list(range(14)))
        self._datalane_monitor_ob_2 = DataLaneMonitor(board_obj=self, moduleid=XckuModuleid.DATALANE_MONITOR_OB_2,
                                                      lanes = list(range(14,self.LANES_OB)), offset=14)
        self._datalane_monitor_ob = DatapathMonitorDualSplitAtLane(self._datalane_monitor_ob_1,self._datalane_monitor_ob_2)
        self._gpio_monitor = GpioMonitor(board_obj=self, moduleid=XckuModuleid.GPIO_MONITOR,lanes=list(range(self.LANES_OB)))
        self.datapath_monitor_ob = DatapathMonitorDualSplitCounters(self._datalane_monitor_ob, self._gpio_monitor)
        self.calibration_lane = CalibrationLane(board_obj=self, moduleid=XckuModuleid.CALIBRATION_LANE)
        self.readout_master = ReadoutMaster(board_obj=self, moduleid=XckuModuleid.READOUT_MASTER)
        self._can_hlp_monitor = WsCanHlpMonitor(moduleid=XckuModuleid.CAN_HLP_MONITOR, board_obj=self)
        self.can_hlp = WsCanHlp(moduleid=XckuModuleid.CAN_HLP, board_obj=self, monitor_module=self._can_hlp_monitor)
        self.master_can_monitor = WsMasterMonitor(moduleid=XckuModuleid.MASTER_CAN_MONITOR, board_obj=self)
        self.master_monitor = WsMasterMonitor(moduleid=XckuModuleid.MASTER_GBTX_MONITOR, board_obj=self)
        self.wait_module = WishboneWait(moduleid=XckuModuleid.FW_WAIT, board_obj=self)
        self._alpide_control_monitor = AlpideControlMonitor(board_obj=self, moduleid=XckuModuleid.ALPIDE_CONTROL_MONITOR)
        self.alpide_control = AlpideControl(moduleid=XckuModuleid.ALPIDE_CONTROL, board_obj=self, monitor_module=self._alpide_control_monitor)
        self._i2c_gbtx_monitor = WsI2cGbtxMonitor(board_obj=self, moduleid=XckuModuleid.I2C_MONITOR_GBTX)
        self.i2c_gbtx = WsI2cGbtx(board_obj=self, moduleid=XckuModuleid.I2C_GBT, monitor_module=self._i2c_gbtx_monitor)
        self.gbtx01_controller = GBTxController(board_obj=self, moduleid=XckuModuleid.GBTX0)
        self.gbtx2_controller = GBTxController(board_obj=self, moduleid=XckuModuleid.GBTX2)
        self.radmon = WsRadiationMonitor(moduleid=XckuModuleid.RADMON, board_obj=self)
        self.sysmon = Sysmon(board_obj=self, moduleid=XckuModuleid.SYSMON)
        self.gbtx_flow_monitor = GbtxFlowMonitor(board_obj=self, moduleid=XckuModuleid.GBTX_FLOW_MONITOR)
        self.master_usb = WsMasterMonitor(moduleid=XckuModuleid.MASTER_USB_MONITOR, board_obj=self)
        self.usb_if = WsUsbif(moduleid=XckuModuleid.USB_IF, board_obj=self)
        self._gbt_packer_0_monitor = GbtPackerMonitor(board_obj=self, moduleid=XckuModuleid.GBT_PACKER_0_MONITOR)
        self._gbt_packer_1_monitor = GbtPackerMonitor(board_obj=self, moduleid=XckuModuleid.GBT_PACKER_1_MONITOR)
        self._gbt_packer_2_monitor = GbtPackerMonitor(board_obj=self, moduleid=XckuModuleid.GBT_PACKER_2_MONITOR)
        self.gbt_packer = GbtPacker(board_obj=self, moduleid=XckuModuleid.GBT_PACKER, monitor0=self._gbt_packer_0_monitor, monitor1=self._gbt_packer_1_monitor, monitor2=self._gbt_packer_2_monitor)
        self._trigger_handler_monitor = TriggerHandlerMonitor(moduleid=XckuModuleid.TRIGGER_HANDLER_MONITOR, board_obj=self)
        self.trigger_handler = TriggerHandler(moduleid=XckuModuleid.TRIGGER_HANDLER, board_obj=self, monitor_module=self._trigger_handler_monitor)
        self._pu_controller_1 = PuController(moduleid=XckuModuleid.I2C_PU1_CONTROLLER, board_obj=self)
        self._powerunit_aux_1 = PowerUnitAux(board_obj=self, moduleid=XckuModuleid.I2C_PU1_AUX)
        self._powerunit_main_monitor_1 = PuMonitor(board_obj=self, moduleid=XckuModuleid.MONITOR_PU1_MAIN)
        self._powerunit_aux_monitor_1 = PuMonitor(board_obj=self, moduleid=XckuModuleid.MONITOR_PU1_AUX)
        self.powerunit_1 = PowerUnit(moduleid=XckuModuleid.I2C_PU1,
                                     main_monitor_module=self._powerunit_main_monitor_1,
                                     auxiliary_module=self._powerunit_aux_1,
                                     aux_monitor_module=self._powerunit_aux_monitor_1,
                                     controller_module=self._pu_controller_1,
                                     board_obj=self,
                                     index=1,
                                     version=power_board_version,
                                     filter_50Hz_ac_power_mains_frequency=power_board_filter_50Hz_ac_power_mains_frequency,
                                     offset_avdd=powerunit_1_offset_avdd,
                                     offset_dvdd=powerunit_1_offset_dvdd,
                                     resistance_offset=powerunit_resistance_offset_pt100,
                                     layer=layer)
        self.powerunit_1.controller._init(power_unit_index=self.powerunit_1.index)
        self._pu_controller_2 = PuController(moduleid=XckuModuleid.I2C_PU2_CONTROLLER, board_obj=self)
        self._powerunit_main_monitor_2 = PuMonitor(board_obj=self, moduleid=XckuModuleid.MONITOR_PU2_MAIN)
        self._powerunit_aux_2 = PowerUnitAux(board_obj=self, moduleid=XckuModuleid.I2C_PU2_AUX)
        self._powerunit_aux_monitor_2 = PuMonitor(board_obj=self, moduleid=XckuModuleid.MONITOR_PU2_AUX)
        self.powerunit_2 = PowerUnit(moduleid=XckuModuleid.I2C_PU2,
                                     main_monitor_module=self._powerunit_main_monitor_2,
                                     auxiliary_module=self._powerunit_aux_2,
                                     aux_monitor_module=self._powerunit_aux_monitor_2,
                                     controller_module=self._pu_controller_2,
                                     board_obj=self,
                                     index=2,
                                     version=power_board_version,
                                     filter_50Hz_ac_power_mains_frequency=power_board_filter_50Hz_ac_power_mains_frequency,
                                     offset_avdd=powerunit_2_offset_avdd,
                                     offset_dvdd=powerunit_2_offset_dvdd,
                                     resistance_offset=powerunit_resistance_offset_pt100,
                                     layer=layer)
        self.powerunit_2.controller._init(power_unit_index=self.powerunit_2.index)
        self.mmcm_gbtx_rxrdy_monitor = RuMmcmGbtxRxrdyMonitor(board_obj=self, moduleid=XckuModuleid.MMCM_GBTX_RXRDY_MONITOR)

        self._pa3fifo_monitor = Pa3FifoMonitor(board_obj=self, moduleid=XckuModuleid.PA3_FIFO_MONITOR)
        self.pa3fifo = Pa3Fifo(board_obj=self, moduleid=XckuModuleid.PA3_FIFO, monitor_module=self._pa3fifo_monitor)
        self.gbtx2_prbs_chk = WsGbtPrbsChk(board_obj=self, moduleid=XckuModuleid.GBTX2_PRBS_CHK)

        self._modules = [self.identity,
                         self.i2c_gbtx,
                         self.alpide_control,
                         self.sysmon,
                         self._drp_bridge,
                         self.gth,
                         self.gpio,
                         self.wait_module,
                         self.lanes_ib,
                         self.lanes_ob,
                         self.calibration_lane,
                         self.readout_master,
                         self.can_hlp,
                         self.gbtx01_controller,
                         self.gbtx2_controller,
                         self.gbt_packer,
                         self.trigger_handler,
                         self.usb_if,
                         self.pa3fifo]
        self._monitor_modules = [self.master_monitor,
                                 self.radmon,
                                 self.gbtx_flow_monitor,
                                 self.master_usb,
                                 self.master_can_monitor,
                                 self._gbt_packer_0_monitor,
                                 self._gbt_packer_1_monitor,
                                 self._gbt_packer_2_monitor,
                                 self._trigger_handler_monitor,
                                 self.mmcm_gbtx_rxrdy_monitor,
                                 self._can_hlp_monitor,
                                 self._i2c_gbtx_monitor,
                                 self._powerunit_main_monitor_1,
                                 self._powerunit_aux_monitor_1,
                                 self._powerunit_main_monitor_2,
                                 self._powerunit_aux_monitor_2,
                                 self.datapath_monitor_ib,
                                 self.datapath_monitor_ob,
                                 self._alpide_control_monitor,
                                 self._pa3fifo_monitor]

    def initialize(self, reenable_forward_to_usb=1, use_xcku=True, initialize_gbtx12=True):
        """Initialize the readout board,
        parameter reenable_forward_to_usb is only used for RUv0"""
        self.initialize_gbtx0(use_xcku=use_xcku)
        if initialize_gbtx12:
            self.initialize_gbtx(use_xcku=use_xcku, check=False, readback=False, verbose=False, gbtx_index=2, minimal="Internal")
            self.initialize_gbtx(use_xcku=use_xcku, check=False, readback=False, verbose=False, gbtx_index=1, minimal="External")
            self.initialize_gbtx(use_xcku=use_xcku, check=False, verbose=False, gbtx_index=2)
            self.initialize_gbtx(use_xcku=use_xcku, check=False, verbose=False, gbtx_index=1)

    def is_initialized(self):
        """Verifies that the value loaded matches with the value in the configuration.
        See CRU_ITS#155"""
        gbtx0_chargepump_setting = self.get_gbtx0_chargepump_custom_settings()
        return gbtx0_chargepump_setting <= self.gbtx0_swt.get_phase_detector_charge_pump()

    def sc_core_reset(self, ultrascale_write_f=None, reset_pa3=False, reset_force=False):
        if type(self.comm) != can_hlp_comm.CanHlpComm:
            if type(self.comm) == FlxSwtCommunication:
                self.cru.reset_sc_core(None)
            else:
                self.cru.reset_sc_core(self.get_gbt_channel())
            self.sca.initialize()
            self.pa3.initialize(ultrascale_write_f=ultrascale_write_f, reset=reset_pa3, reset_force=reset_force)

    def git_tag(self):
        return git_hash_lut.get_ru_version(self.identity.get_git_hash())

    def get_gbtx0_chargepump_custom_settings(self):
        """Returns the GBTx0 custom settings or default if they do not exist.
        It access the board to get the RU serial number
        """
        try:
            serial = self.identity.get_sn()
        except AssertionError:
            self.logger.warning("Could not access SN: proceeding with default settings")
            serial = None
        if serial is None: # default for failed read or SN not found
            return self.GBTx0_CHARGEPUMP_DEFAULT
        else:
            # expect to be launched from software/py/.
            yml_path = os.path.join(script_path,"../../../../software/config/ru_gbtx0_chargepump_custom.yml")
            if not os.path.isfile(yml_path):
                self.logger.warning(f"{yml_path} not existing. Fallback to default")
                return self.GBTx0_CHARGEPUMP_DEFAULT
            else:
                # File exists: open and check if value is there
                with open(yml_path, 'r') as f:
                    custom = yaml.load(f, Loader=yaml.FullLoader)
                    if serial in custom.keys():
                        custom_cp_dac = custom[serial]['cp_dac']
                        if custom_cp_dac in range(16):
                            return custom_cp_dac
                        else:
                            self.logger.warning(f"Invalid value {custom_cp_dac} found in YML file. Fallback to default")
                            return self.GBTx0_CHARGEPUMP_DEFAULT
                    else: # Not in YML, use default
                        return self.GBTx0_CHARGEPUMP_DEFAULT

    def gbtx0_update_delay(self,delay=0x8):
        ELINK_0_DELAY_REG = (69,73,77) # paPhaseSelectGroup0Ch0
        gbtx_registers = ELINK_0_DELAY_REG
        gbtx_num = 0
        for reg in gbtx_registers:
            self.write(XckuModuleid.I2C_GBT, gbtx_num, reg, commitTransaction=False)
            self.write(XckuModuleid.I2C_GBT, 3, delay, commitTransaction=True)

    def clean_datapath(self):
        """Cleans the RU datapath"""
        self.trigger_handler.disable() # holds the trigger handler FSM in reset
        self.trigger_handler.sequencer_disable()
        self.gbt_packer.reset()
        self.gth.set_transceivers(list(range(9))) # select all the GTH
        self.gth.enable_data(enable=False) # Disable data in GTH (uses flag above)
        self.gpio.set_transceivers(list(range(28))) # select all the GPIOs
        self.gpio.enable_data(enable=False) # Disable data in GPIO (uses flag above)
        self.readout_master.reset_ib_lanes()
        self.readout_master.reset_ob_lanes()
        self.trigger_handler.reset_readout_master() # Resets the readout master internal flags
        self.trigger_handler.enable() # releases the trigger handler FSM

    def get_trigger_rates(self):
        th_cnt_pre = self.trigger_handler.read_counters()
        gbt_cnt_pre = self.gbt_packer.read_counters()
        time.sleep(2)
        th_cnt_post = self.trigger_handler.read_counters()
        gbt_cnt_post = self.gbt_packer.read_counters()
        return th_cnt_pre,th_cnt_post,gbt_cnt_pre,gbt_cnt_post

    def format_trigger_rates(self):
        th_cnt_pre,th_cnt_post,gbt_cnt_pre,gbt_cnt_post = self.get_trigger_rates()
        th_nums = self.trigger_handler.get_nums(th_cnt_pre,th_cnt_post)
        th_rates = self.trigger_handler.get_rates(th_nums)

        gbt_nums = self.gbt_packer.get_nums(gbt_cnt_pre[0],gbt_cnt_post[0])
        gbt_rates = self.gbt_packer.get_rates(gbt_nums, th_nums)
        return self.trigger_handler.format_rates(th_rates) + "\n\t\t\t\t\t" + self.gbt_packer.format_rates(gbt_rates)

    def log_trigger_rates(self):
        self.logger.info(self.format_trigger_rates())

    def log_clock_event(self):
        self.dna()
        self.uptime()
        self.logger.info(self.clock_health_status.get_clock_health_flags())

        if self.clock_health_status.is_any_clock_health_flags_set():
            self.logger.info(f"Clock event timestamp: {self.clock_health_status.get_clk_event_timestamp_uptime()}")
            d = {}
            d['lol'],d['c1b'],d['c2b'] = self.pa3.loss_of_lock_counter.get()
            self.logger.info(f"PA LOL counters: {d['lol']} C1B {d['c1b']} C2B {d['c2b']}")

        if self.clock_health_status.is_lol_timebase_set():
            self.logger.info(f"Timebase event timestamp: {self.clock_health_status.get_timebase_event_timestamp_uptime()}")
            self.logger.info(f"Timebase LOL counter: {self.trigger_handler.read_counters()['LOL_TIMEBASE']}")

    # ALPIDE-RELATED

    def set_chip2connector_lut(self,lut):
        """Set the mapping between chip and its connector at the RU in form of a Dictionary {chipid:connector}"""
        assert self.chip2connector_enabled == False, f"Re-enabling chip2connector lut: was {self._chip2connector_lut}"
        self._chip2connector_lut = lut
        self.chip2connector_enabled = True

    def get_chip2connector_lut(self):
        """Return the mapping between chip and its connector"""
        return self._chip2connector_lut

    def update_chip2connector_lut(self, lut):
        """updates the mapping between chip and its connector at the RU in form
        of a Dictionary {chipid:connector}"""
        old_lut_keys = self._chip2connector_lut.keys()
        assert self._chip2connector_lut is not None
        for key in old_lut_keys:
            assert key not in lut.keys()
        self._chip2connector_lut.update(lut)

    def enable_chip2connector_lut(self, enable=True):
        """Enable/disable automatic chip to connector mapping"""
        self.chip2connector_enabled = enable

    def write_chip_reg(self, address, data, extended_chipid, commitTransaction=True, readback=None):
        self.alpide_control.write_chip_reg(address, data, extended_chipid, commitTransaction, readback)

    def read_chip_reg(self, address, extended_chipid, disable_read=False, commitTransaction=True):
        return self.alpide_control.read_chip_reg(address, extended_chipid, disable_read, commitTransaction)

    def write_chip_opcode(self, opcode, extended_chipid=0xF,commitTransaction=True):
        self.alpide_control.write_chip_opcode(opcode=opcode, extended_chipid=extended_chipid, commitTransaction=commitTransaction)

    # WAIT

    def wait(self, wait_value, commitTransaction=True):
        """Implements the wait function of the Alpide Control wishbone slave"""
        self.wait_module.wait(wait_value, commitTransaction=commitTransaction)

    # IDENTITY

    def check_git_hash(self, expected_git_hash=None):
        """gets git hash"""
        self.identity.check_git_hash(expected_git_hash=expected_git_hash)

    def check_git_hash_and_date(self, expected_git_hash=None):
        warnings.warn("check_git_hash_and_date() is deprecated; use check_git_hash().", DeprecationWarning)
        self.check_git_hash(expected_git_hash=expected_git_hash)

    def get_dna(self):
        """Gets the FPGA DNA value"""
        return self.identity.get_dna()

    def get_sn(self):
        """Gets the FPGA DNA value"""
        return self.identity.get_sn()

    # from testbench

    def init_transition_board(self, transition_board_version, ru_main_revision):
        """Instantiate a transition board based on the RU version"""
        self.tb = ru_transition_board.select_transition_board(transition_board_version=transition_board_version,
                                                              ru_main_revision=ru_main_revision)

    def gth_subset(self, transceivers):
        """Defines a subset of transceivers
        Transceivers is a list of lanes (in range(9))"""
        assert set(transceivers).issubset(set(list(range(self.LANES_IB))))
        self.gth.set_transceivers(transceivers)
        self.datapath_monitor_ib.set_lanes(transceivers)

    def gpio_subset(self, transceivers):
        """Sets the transceivers
        Transceivers is a list of lanes (in range(28))"""
        assert set(transceivers).issubset(set(list(range(self.LANES_OB))))
        self.gpio.set_transceivers(transceivers)
        self.datapath_monitor_ob.set_lanes(transceivers)

    def gpio_subset_ob(self,transceivers):
        raise DeprecationWarning("Deprecated method, use gpio subset instead")

    def get_gpio_lane(self, chipid, is_on_lower_hs=True):
        if is_on_lower_hs:
            extended_chipid = chipid
        else: # On upper HS
            extended_chipid = 1<<7 | chipid
        lane = self.tb.get_gpio_lane(connector=self._chip2connector_lut[extended_chipid],
                                     chipid=chipid)
        return lane

    def get_gpio_connector(self, extended_chipid):
        connector=self._chip2connector_lut[extended_chipid]
        return connector

    def initialize_gbtx0(self, use_xcku=True):
        gbtx0_chargepump_setting = self.GBTx0_CHARGEPUMP_DEFAULT
        if use_xcku:
            gbtx = self.gbtx0_swt
        else:
            gbtx = self.gbtx0_sca
        gbtx.set_phase_detector_charge_pump(gbtx0_chargepump_setting)
        time.sleep(0.1)
        self.cru.reset_sc_core(self.get_gbt_channel())
        time.sleep(0.1)
        if gbtx.get_phase_detector_charge_pump() != gbtx0_chargepump_setting:
            self.logger.error("Setting charge pump failed")

    def _initialize_gbtx_swt(self, config_path, gbtx, check, readback, verbose, pre_check_fsm=True, use_xml=False, minimal=False):
        gbtx_configured = False
        readback_ok = True
        i2c_bad_status_error = False
        try:
            gbtx_configured, already_configured = gbtx.configure(filename=config_path, check=check, pre_check_fsm=pre_check_fsm, use_xml=use_xml, minimal=minimal)
        except XckuI2cBadStatusError:
            i2c_bad_status_error = True

        if readback and not already_configured:
            readback_ok = gbtx.check_config(filename=config_path, use_xml=use_xml, minimal=minimal)
            log = f"\n\t\t\tReadback OK\t\t{readback_ok}"
        else:
            log = ""

        if not minimal and (not gbtx_configured or i2c_bad_status_error or not readback_ok):
            self.logger.error(
                              f"GBTx{gbtx.get_index()} configuration FAILED with SWT\n"
                              f"\t\t\tGBTx Configured\t\t{gbtx_configured}\n"
                              f"\t\t\tI2C Bad Status Error\t{i2c_bad_status_error}\n"
                              f"{log}"
                              )
            success = False
        else:
            if verbose and not minimal:
                self.logger.info(f"GBTx{gbtx.get_index()} configuration succeded with SWT")
            elif verbose and minimal:
                self.logger.info(f"GBTx{gbtx.get_index()} minimal configuration succeded with SWT")
            success = True
        return success

    def _initialize_gbtx_sca(self, config_path, gbtx, check, readback, verbose, pre_check_fsm=True, use_xml=False, minimal=False):
        gbtx_configured = False
        readback_ok = True
        i2c_bad_status_error = False
        try:
            gbtx_configured, already_configured = gbtx.configure(filename=config_path, check=check, pre_check_fsm=pre_check_fsm, use_xml=use_xml, minimal=minimal)
        except gbt_sca.ScaI2cBadStatusError:
            i2c_bad_status_error = True

        if readback and not already_configured:
            readback_ok = gbtx.check_config(filename=config_path, use_xml=use_xml, minimal=minimal)
            log = f"\n\t\t\tReadback OK\t\t{readback_ok}"
        else:
            log = ""

        if not minimal and (not gbtx_configured or i2c_bad_status_error or not readback_ok):
            self.logger.error(f"GBTx{gbtx.get_index()} configuration FAILED with SCA\n"
                              f"\t\t\tGBTx Configured\t\t{gbtx_configured}\n"
                              f"\t\t\tI2C Bad Status Error\t{i2c_bad_status_error}\n"
                              f"{log}")
            success = False
        else:
            if verbose and not minimal:
                self.logger.info(f"GBTx{gbtx.get_index()} configuration succeded with SCA")
            elif verbose and minimal:
                self.logger.info(f"GBTx{gbtx.get_index()} minimal configuration succeded with SCA")
            success =True
        return success

    def initialize_gbtx(self,
                        check=True,
                        readback=True,
                        use_xcku=True,
                        verbose=True,
                        pre_check_fsm=True,
                        gbtx_index=1,
                        filename=None,
                        minimal=False):

        if filename is None:
            filename = os.path.join(script_path, f"../../../gbt/software/GBTx_configs/GBTx{gbtx_index}_Config_ITS.txt")

        if use_xcku:
            success = self._initialize_gbtx_swt(filename, self.gbtxs_swt[gbtx_index], check, readback, verbose, pre_check_fsm, minimal=minimal)
        else:
            success = self._initialize_gbtx_sca(filename, self.gbtxs_sca[gbtx_index], check, readback, verbose, pre_check_fsm, minimal=minimal)
        return success

    def initialize_gbtx12(self,
                          check=False,
                          readback=True,
                          use_xcku=True,
                          verbose=True,
                          pre_check_fsm=True,
                          xml_gbtx1_RUv1_1=os.path.join(script_path, "../../../gbt/software/GBTx_configs/GBTx1_Config_RUv1_1.xml"),
                          xml_gbtx2_RUv1_1=os.path.join(script_path, "../../../gbt/software/GBTx_configs/GBTx2_Config_RUv1_1.xml"),
                          xml_gbtx1_RUv2_x=os.path.join(script_path, "../../../gbt/software/GBTx_configs/GBTx1_Config_RUv2.xml"),
                          xml_gbtx2_RUv2_x=os.path.join(script_path, "../../../gbt/software/GBTx_configs/GBTx2_Config_RUv2.xml")):
        """Configures the GBTx1 and GBTx2 on the RU"""
        if self.ru_main_revision == 1:
            config1=xml_gbtx1_RUv1_1
            config2=xml_gbtx2_RUv1_1
        else:
            config1=xml_gbtx1_RUv2_x
            config2=xml_gbtx2_RUv2_x

        if use_xcku:
            success1 = self._initialize_gbtx_swt(config1, self.gbtx1_swt, check, readback, verbose, pre_check_fsm, use_xml=True)
            success2 = self._initialize_gbtx_swt(config2, self.gbtx2_swt, check, readback, verbose, pre_check_fsm, use_xml=True)
        else:
            success1 = self._initialize_gbtx_sca(config1, self.gbtx1_sca, check, readback, verbose, pre_check_fsm, use_xml=True)
            success2 = self._initialize_gbtx_sca(config2, self.gbtx2_sca, check, readback, verbose, pre_check_fsm, use_xml=True)
        return success1 and success2

    def test_swt(self, nrtests=1000, use_ru=True, verbose=False):
        """Writes one SWT with a random value and reads it back.
        The test is repeated nrtests times.

        If use_ru=True it assumes standard operation
        If use_ru=False it assumes one of the loopbacks to be active before running the test"""

        start_time = time.time()
        total_errors = 0
        CRU_WR_COUNTER_DEPTH = 256

        if use_ru:
            _, start_value = self.read(mod=XckuModuleid.GBT_PACKER, addr=GbtPackerAddress.TIMEOUT_TO_START)
            self.master_monitor.reset_all_counters()
            self.gbtx_flow_monitor.reset_all_counters()
        r = 0
        try:
            for i in range(nrtests):
                if use_ru:
                    if (2*nrtests + total_errors + 2) % CRU_WR_COUNTER_DEPTH == 0:
                        # CRU counter wraps around.
                        # Check here that it did.
                        # The SWT passing there depend on the test running
                        # 2 SWT per test (WR/RD)
                        # 1 SWT for the second read in case of error
                        # 2 SWT for resetting the counters
                        if type(self.comm).__name__ == 'CruSwtCommunication':
                            _, swt_status = self.comm._read_swt_status()
                            assert swt_status['swt_writes'] == 0, f"swt_status not correct {swt_status}"
                            assert swt_status['swt_words_available'] == 0, f"swt_status not correct {swt_status}"
                            assert swt_status['gbt_channel'] == self.get_gbt_channel(), f"swt_status not correct {swt_status}"
                else:
                    if (nrtests + total_errors) % CRU_WR_COUNTER_DEPTH == 0:
                         # CRU counter wraps around.
                         # Check here that it did. The SWT passing there depend on the test running and the number of errors (there is a retry there)
                         # 1 SWT per test (RD)
                         # 1 SWT for the second read in case of error
                        if type(self.comm).__name__ == 'CruSwtCommunication':
                            _, swt_status = self.comm._read_swt_status()
                            assert swt_status['swt_writes'] == 0
                            assert swt_status['swt_words_available'] == 0
                            assert swt_status['gbt_channel'] == self.get_gbt_channel()

                previous_val = r
                r = random.randrange(0, 1 << 16)
                if use_ru:
                    self.write(mod=XckuModuleid.GBT_PACKER, addr=GbtPackerAddress.TIMEOUT_TO_START, data=r)
                    _, read_val = self.read(mod=XckuModuleid.GBT_PACKER, addr=GbtPackerAddress.TIMEOUT_TO_START)
                else:
                    read_val = self.read_loopback(mod=XckuModuleid.GBT_PACKER, addr=GbtPackerAddress.TIMEOUT_TO_START, data=r)
                if r != read_val:
                    self.logger.error(f"iteration {i}: read val doesn't match; write: {r} read: {read_val} (previous_val {previous_val})")
                    if use_ru:
                        _, read_val = self.read(mod=XckuModuleid.GBT_PACKER, addr=GbtPackerAddress.TIMEOUT_TO_START)
                    else:
                        read_val = self.read_loopback(mod=XckuModuleid.GBT_PACKER, addr=GbtPackerAddress.TIMEOUT_TO_START, data=r)
                    self.logger.error(f"re-iteration {i} write: {r} read: {read_val} (previous_val {previous_val})")
                    total_errors += 1
                    if type(self.comm).__name__ == 'CruSwtCommunication':
                        # To be used only with the RU connected to a CRU
                        self.comm.log_swt_status()
                elif verbose:
                    self.logger.info(f"{r} matched {read_val}")

        except KeyboardInterrupt as ki:
            if verbose:
                self.logger.info("Keyboard Interrupt")
        if use_ru:
            counters = self.gbtx_flow_monitor.read_counters()
            expected_counters = {'DOWNLINK0_SWT': 2*nrtests+total_errors+3, # takes into account the latch+wait+reset latch of the counters
                                 'UPLINK0_SWT': nrtests+total_errors,
                                 'DOWNLINK0_OVERFLOW': 0, 'UPLINK0_OVERFLOW': 0}
            counters = {key: counters[key] for key in expected_counters.keys()}
            msg = f"GBTx Flow Monitor Counters: DOWNLINK0_SWT: {counters['DOWNLINK0_SWT']}, UPLINK0_SWT: {counters['UPLINK0_SWT']}, DOWNLINK0_OVERFLOW: {counters['DOWNLINK0_OVERFLOW']}, UPLINK0_OVERFLOW: {counters['UPLINK0_OVERFLOW']}"
            if counters != expected_counters:
                self.logger.error(msg)
            counters = self.master_monitor.read_counters()
            counters = {key: counters[key] for key in ['WR_ERRORS', 'RD_ERRORS', 'SEE_ERRORS']}
            if counters != {key:0 for key in counters.keys()}:
                self.logger.error(f"Master Monitor Counters: {counters}")
        elapsed_time = time.time() - start_time
        if verbose:
            self.logger.info(f"Done. Total errors: {total_errors}. Elapsed time {elapsed_time:.1f} s")
        if use_ru:
            self.write(mod=XckuModuleid.GBT_PACKER, addr=GbtPackerAddress.TIMEOUT_TO_START, data=start_value)
        return total_errors

    # DUMP CONFIG

    def dump_config(self):
        # need to decrease logging, since we have a lot of DEAD registers

        config_str = ""
        config_str += self.dump_config_only()
        config_str += self.dump_monitor_only()

        return config_str

    def dump_config_only(self):
        # Only dump firmware config modules

        current_level = self.comm.logger.getEffectiveLevel()
        self.comm.logger.setLevel(logging.CRITICAL)

        config_str = "-- XCKU configuration --\n"
        for mod in self._modules:
            config_str += f"-- Module {mod.name} -- Mod ID {mod.moduleid} \n"
            try:
                config_str += mod.dump_config()
            except:
                self.logger.error(f"Dump config failed for module {mod.moduleid}")
                config_str += f"-- Module {mod.name} -- Mod ID {mod.moduleid} -- FAILED \n"

        # reset the current_level
        self.comm.logger.setLevel(current_level)
        return config_str

    def dump_monitor_only(self):
        # Only dump monitor modules

        current_level = self.comm.logger.getEffectiveLevel()
        self.comm.logger.setLevel(logging.CRITICAL)

        config_str = "-- XCKU monitor --\n"
        for mod in self._monitor_modules:
            config_str += f"-- Module {mod.name} -- Mod ID {mod.moduleid} \n"
            try:
                config_str += mod.dump_config()
            except:
                self.logger.error(f"Dump config failed for module {mod.moduleid}")
                config_str += f"-- Module {mod.name} -- Mod ID {mod.moduleid} -- FAILED \n"

        # reset the current_level
        self.comm.logger.setLevel(current_level)
        return config_str

    def reset_counters(self, commitTransaction=True):
        """Resets the counters used for daq"""
        self.reset_daq_counters(commitTransaction=commitTransaction)
        raise DeprecationWarning("Use reset_daq_counters instead!")

    def reset_daq_counters(self, commitTransaction=True):
        """Resets the counters used for daq"""
        self.alpide_control.reset_counters(commitTransaction=False)
        self.gbtx_flow_monitor.reset_all_counters(commitTransaction=False)
        self.trigger_handler.reset_counters(commitTransaction=False)
        self.datapath_monitor_ib.reset_all_counters(commitTransaction=False)
        self.datapath_monitor_ob.reset_all_counters(commitTransaction=False)
        self.gbt_packer.reset_all_counters(commitTransaction=False)
        if commitTransaction:
            self.flush()

    def reset_all_counters(self, commitTransaction=True):
        """resets all monitor modules"""
        for mod in self._monitor_modules:
            try:
                mod.reset_all_counters(commitTransaction=False)
            except Exception as e:
                self.logger.error(f"reset_monitor failed for module {mod.moduleid}: printing traceback")
                self.logger.error(e)
        if commitTransaction:
            self.flush()

    # NotImplemented

    def power_on_chip(self, avdd=1.8, dvdd=1.8, backbias=None):
        raise NotImplementedError

    def set_chip_voltage(self, avdd=1.8, dvdd=1.8, backbias=None):
        raise NotImplementedError

    def power_off_chip(self):
        raise NotImplementedError

    def log_currents(self):
        raise NotImplementedError

    def recover(self):
        """ Test routine for the recovery procedure """
        self.logger.warning("Readout Unit recovery - this is for testing/debugging only - implement only for IB")
        # could use identity module to switch between IB/ML/OL behaviour

        self.logger.info(self.trigger_handler.dump_config())
        self.logger.info(self.lanes_ib.dump_config())
        self.logger.info(self.readout_master.dump_config())
        self.logger.info(self.gbt_packer.dump_config())
        self.logger.info(self.gbt_packer.read_counters())

        self.trigger_handler.set_opcode_gating(True)
        time.sleep(1)

        self.logger.info(self.trigger_handler.dump_config())
        self.logger.info(self.lanes_ib.dump_config())
        self.logger.info(self.readout_master.dump_config())
        self.logger.info(self.gbt_packer.dump_config())
        self.logger.info(self.gbt_packer.read_counters())

        self.gth.enable_data(False)
        self.gth.reset_gth()
        while not self.gth.is_reset_done():
            time.sleep(0.1)

        ### Add your chip recovery here

        self.gth.enable_alignment(True)
        time.sleep(1)
        self.trigger_handler.reset_readout_master()

        self.logger.info(self.trigger_handler.dump_config())
        self.logger.info(self.lanes_ib.dump_config())
        self.logger.info(self.readout_master.dump_config())
        self.logger.info(self.gbt_packer.dump_config())
        self.logger.info(self.gbt_packer.read_counters())

        time.sleep(1)
        self.gth.enable_data(True)
        self.logger.info("\n\n\n GTH re-enabled\n\n\n\n")
        self.logger.info(self.trigger_handler.dump_config())
        self.logger.info(self.lanes_ib.dump_config())
        self.logger.info(self.readout_master.dump_config())
        self.logger.info(self.gbt_packer.dump_config())
        self.logger.info(self.gbt_packer.read_counters())

        self.trigger_handler.set_opcode_gating(False)

        self.logger.info(self.trigger_handler.dump_config())
        self.logger.info(self.lanes_ib.dump_config())
        self.logger.info(self.readout_master.dump_config())
        self.logger.info(self.gbt_packer.dump_config())
        self.logger.info(self.gbt_packer.read_counters())


class WsGbtFpgaAddress(IntEnum):
    """memory mapping for the GBT_FPGA wishbone slave derived from gbt_fpga_wb_wrapper.vhd"""

    # Reads
    STATUS_FLAGS              = 0x00
    RX_IS_DATA                = 0x01
    RXDATA_ERROR_CNT_LSB      = 0x03
    RXDATA_ERROR_CNT_MSB      = 0x04
    LINK_ERROR_CNT_LSB        = 0x05
    LINK_ERROR_CNT_MSB        = 0x06
    LINK_ERROR_DISCR_LSB      = 0x07
    LINK_ERROR_DISCR_MSB      = 0x08
    GBT_TX_CNT_LSB            = 0x09
    GBT_TX_CNT_MSB            = 0x0a
    GBT_RX_SOP_CNT_LSB        = 0x0b
    GBT_RX_SOP_CNT_MSB        = 0x0c
    GBT_RX_EOP_CNT_LSB        = 0xd
    GBT_RX_EOP_CNT_MSB        = 0x0e
    GBT_RX_SWT_CNT_LSB        = 0x0f
    GBT_RX_SWT_CNT_MSB        = 0x10
    GBT_TX_SWT_CNT_LSB        = 0x11
    GBT_TX_SWT_CNT_MSB        = 0x12
    GBT_TX_DATAVALID_CNT_LSB  = 0x13
    GBT_TX_DATAVALID_CNT_MSB  = 0x14
    GBT_SWT_MISMATCH_CNT0_LSB = 0x15
    GBT_SWT_MISMATCH_CNT0_MSB = 0x16
    GBT_SWT_MISMATCH_CNT1_LSB = 0x17
    GBT_SWT_MISMATCH_CNT1_MSB = 0x18
    GBT_SWT_MISMATCH_CNT2_LSB = 0x19
    GBT_SWT_MISMATCH_CNT2_MSB = 0x1a
    GBT_SWT_MISMATCH_CNT3_LSB = 0x1b
    GBT_SWT_MISMATCH_CNT3_MSB = 0x1c
    RX_FEC_CNT_LSB            = 0x1d
    RX_FEC_CNT_MSB            = 0x1e
    RX_BITSMODIFIED_CNT_LSB   = 0x1f
    RX_BITSMODIFIED_CNT_MSB   = 0x20
    # Writes
    CONTROL_RESETS            = 0x00
    TEST_PATTERN_SEL          = 0x02
    COUNTER_RESETS            = 0x03
    GBT_USB_ENABLE            = 0x04
    GBT_FIFO_15_00            = 0x0b
    GBT_FIFO_31_16            = 0x0c
    GBT_FIFO_47_32            = 0x0d
    GBT_FIFO_63_48            = 0x0e
    GBT_FIFO_79_64            = 0x0f


class Ruv0CruModuleid(IntEnum):
    CRU_OFFSET = 0x40
    MASTER_MONITOR =  CRU_OFFSET + 0
    IDENTITY       =  CRU_OFFSET + 1
    SCA            =  CRU_OFFSET + 2
    GBT_FPGA       =  CRU_OFFSET + 3
    WAIT           =  CRU_OFFSET + 4


class RUv0_CRU(ReadoutBoard):
    """Board implementation for Readout unit"""

    def __init__(self, comm,
                 sca_is_on_ruv1,
                 sca_is_on_ruv2_0):
        super(RUv0_CRU, self).__init__(comm)
        self.logger = logging.getLogger("RUv0 CRU")

        self.comm = comm
        self.wait_module = WishboneWait(moduleid=Ruv0CruModuleid.WAIT, board_obj=self)
        self.identity = WsIdentity(moduleid=Ruv0CruModuleid.IDENTITY, board_obj=self)
        self.master_monitor = WsMasterMonitor(moduleid=Ruv0CruModuleid.MASTER_MONITOR, board_obj=self)
        self.sca = Sca_RU(moduleid=Ruv0CruModuleid.SCA, board_obj=self,
                          is_on_ruv1=sca_is_on_ruv1, is_on_ruv2_0=sca_is_on_ruv2_0)
        self.pa3 = proasic3.ProAsic3(sca=self.sca, gbt_channel=None)

        self.gbtx0 = gbtx.GBTx(index=0, board=None, sca=self.sca)
        self.gbtx1 = gbtx.GBTx(index=1, board=None, sca=self.sca)
        self.gbtx2 = gbtx.GBTx(index=2, board=None, sca=self.sca)
        self.gbtxs = [self.gbtx0, self.gbtx1, self.gbtx2]

    def initialize(self, reenable_forward_to_usb=1, gbt_ch=None):
        """Initialize the readout board"""
        # activate GBTX transmission
        assert reenable_forward_to_usb in range(2)
        self.set_gbtx_forward_to_usb(0)
        self.comm.discardall_dp1()
        self.comm.discardall_dp2()
        self.initialize_gbtx()
        self.sca.initialize()
        if reenable_forward_to_usb:
            self.set_gbtx_forward_to_usb(1)
        self.reset_counters()

    def reset_sc_core(self, channel):
        pass

    def reset_sc_cores(self):
        pass

    def git_tag(self):
        return git_hash_lut.get_ruv0_cru_version(self.identity.get_git_hash())

    def initialize_gbtx(self, commitTransaction=True):
        NR_RETRIES = 100
        # set pattern mode 0
        self.write(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.TEST_PATTERN_SEL, 0, commitTransaction=False)
        # reset GBT_FPGA
        self.write(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.CONTROL_RESETS, 0x1, commitTransaction=True)
        # set correct FIFO mode and reset error flags
        self.write(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.CONTROL_RESETS, 0x78, commitTransaction=commitTransaction)

        rx_ready = False
        for _ in range(NR_RETRIES):
            rx_ready = self.is_gbt_rx_ready()
            if rx_ready:
                break
            else:
                time.sleep(0.25)
        if not rx_ready:
            msg = "GBT_FPGA could not reset GBT_FPGA (RX_READY is False)"
            self.logger.error(msg)
            raise Exception(msg)

    def is_gbt_rx_ready(self):
        _, read = self.read(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.STATUS_FLAGS)
        return (read & (1<< 3)) > 0

    def send_gbtx_data_frame(self, data, commitTransaction=True):
        self.write(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.GBT_FIFO_15_00, data & 0xFFFF, commitTransaction=False)
        self.write(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.GBT_FIFO_31_16, data>>16, commitTransaction=False)
        self.write(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.GBT_FIFO_79_64, 0x8000, commitTransaction=False)
        if commitTransaction:
            self.flush()

    def send_trigger(self, triggerType=0x10, bc=0xabc, orbit=0x43215678, commitTransaction=True):
        """Sends a trigger to the XCKU through the GBTx
        NOTE: orbit is 32 bit in ITS upgrade but is limited to 31 bits for the CRU design"""
        assert triggerType | 0xFFF == 0xFFF
        assert bc | 0xFFF == 0xFFF
        assert orbit | 0x7FFFFFFF  == 0x7FFFFFFF
        self.write(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.GBT_FIFO_15_00, (triggerType & 0xFFFF),commitTransaction=False)
        self.write(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.GBT_FIFO_31_16, ((triggerType>>16)&0xFFFF),commitTransaction=False)
        self.write(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.GBT_FIFO_47_32, (bc&0xFFF),commitTransaction=False)
        self.write(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.GBT_FIFO_63_48, (orbit&0xFFFF),commitTransaction=False)
        self.write(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.GBT_FIFO_79_64, (0x8000 | ((orbit>>16)&0x7FFF)),commitTransaction=commitTransaction)

    def send_start_of_triggered(self, bc=0xabc, orbit=0x43215678, commitTransaction=True):
        """Sends a SOT trigger"""
        triggerType = 1 << trigger.BitMap.SOT
        self.send_trigger(triggerType=triggerType, bc=bc, orbit=orbit,commitTransaction=commitTransaction)

    def send_end_of_triggered(self, bc=0xabc, orbit=0x43215678, commitTransaction=True):
        """Sends a EOT trigger"""
        triggerType = 1 << trigger.BitMap.EOT
        self.send_trigger(triggerType=triggerType, bc=bc, orbit=orbit,commitTransaction=commitTransaction)

    def send_start_of_continuous(self, bc=0xabc, orbit=0x43215678, commitTransaction=True):
        """Sends a SOC trigger"""
        triggerType = 1 << trigger.BitMap.SOC
        self.send_trigger(triggerType=triggerType, bc=bc, orbit=orbit,commitTransaction=commitTransaction)

    def send_heartbeat(self, bc=0xabc, orbit=0x43215678, commitTransaction=True):
        """Sends a SOC trigger"""
        triggerType = 1 << trigger.BitMap.HB
        self.send_trigger(triggerType=triggerType, bc=bc, orbit=orbit, commitTransaction=commitTransaction)

    def send_end_of_continuous(self, bc=0xabc, orbit=0x43215678, commitTransaction=True):
        """Sends a EOC trigger"""
        triggerType = 1 << trigger.BitMap.EOC
        self.send_trigger(triggerType=triggerType, bc=bc, orbit=orbit, commitTransaction=commitTransaction)

    def write_gbtx(self, module, address, data, commitTransaction=True):
        """Writes to the gbtx interface on the RDO board"""
        assert module < 64
        self.write(mod=module, addr=address, data=data, commitTransaction=commitTransaction)

    def read_gbtx(self, module, address, commitTransaction=True):
        assert module < 64
        return self.read(mod=module, addr=address, commitTransaction=commitTransaction)

    def read_gbtx_data_from_usb(self, size, rawoutfile=None):
        """size is expressed in gbt packages"""
        results = []
        data = self.comm.read_dp2(size*3*4)
        if rawoutfile:
            rawoutfile.write(data)
        retries = 0
        max_retries = 10
        # GBT usb data is defined as multiple of 3 words (12 bytes), read more bytes
        while len(data) % 3 != 0 and retries < max_retries:
            data += self.comm.read_dp2(4)
            retries += 1
        #print(["{0:08X}".format(d) for d in data])
        if len(data) % 3 != 0:
            self.logger.error("RUv0_CRU.read_gbtx_datapath_from_usb: Could not read multiple of 3 words: Data loss?")
        for i in range(0,len(data),3):
            idx_data3 = i+0
            idx_data2 = i+1
            idx_data1 = i+2

            datavalid = data[idx_data3]>>31 == 1
            channel_data = bytearray(10)
            channel_data[0] = int((data[idx_data3] >>8)&0xFF)
            channel_data[1] = data[idx_data3]&0xFF
            for j in range(4):
                channel_data[5-j] = (data[idx_data2] >> (j*8))&0xFF
                channel_data[9-j] = (data[idx_data1] >> (j*8))&0xFF
            results.append((datavalid, channel_data))
        return results

    def read_gbtx_data_from_board(self, size, rawoutfile=None):
        return(self.read_gbtx_data_from_usb(size=size, rawoutfile=rawoutfile))

    def wait(self, wait_value, commitTransaction=True):
        """Implements the wait function of the alpide control wishbone slave"""
        self.wait_module.wait(wait_value, commitTransaction=commitTransaction)

    def read_counters(self):
        for i in range(WsGbtFpgaAddress.GBT_TX_CNT_LSB, WsGbtFpgaAddress.RX_FEC_CNT_LSB):
            self.read(Ruv0CruModuleid.GBT_FPGA, i, commitTransaction=False)
        self.flush()
        results = self.read_all()

        gbt_wr_counter = results[0] | (results[1]<<16)
        gbt_sop_counter = results[2] | (results[3]<<16)
        gbt_eop_counter = results[4] | (results[5]<<16)
        gbt_swt_counter = results[6] | (results[7]<<16)
        gbt_wr_swt_counter = results[8] | (results[9]<<16)
        gbt_data_valid_counter = results[10] | (results[11]<<16)
        gbt_swt_mismatch_counter0 = results[12] | (results[13]<<16)
        gbt_swt_mismatch_counter1 = results[14] | (results[15]<<16)
        gbt_swt_mismatch_counter2 = results[16] | (results[17]<<16)
        gbt_swt_mismatch_counter3 = results[18] | (results[19]<<16)
        counters = OrderedDict([
            ("gbt_wr_counter", gbt_wr_counter),
            ("gbt_sop_counter", gbt_sop_counter),
            ("gbt_eop_counter", gbt_eop_counter),
            ("gbt_swt_counter", gbt_swt_counter),
            ("gbt_wr_swt_counter", gbt_wr_swt_counter),
            ("gbt_data_valid_counter", gbt_data_valid_counter), # Gbt Write DV counter (nr Triggers)
            ("gbt_swt_mismatch_counter0", gbt_swt_mismatch_counter0),
            ("gbt_swt_mismatch_counter1", gbt_swt_mismatch_counter1),
            ("gbt_swt_mismatch_counter2", gbt_swt_mismatch_counter2),
            ("gbt_swt_mismatch_counter3", gbt_swt_mismatch_counter3)
        ])

        self.logger.debug("CRU write counter: {0}, sop counter: {1}, eop counter: {2}, swt counter: {3}".format)
        return counters

    def reset_counters(self):
        self.write(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.COUNTER_RESETS, 0xFFFF)

    def set_gbtx_forward_to_usb(self, value, commitTransaction=True):
        assert value in range(2)
        self.write(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.GBT_USB_ENABLE, value, commitTransaction=commitTransaction)

    def dump_config(self):
        config_str = "-- RUv0_CRU configuration --\n"

        config_str += "-- Module {0} --\n".format(Ruv0CruModuleid.MASTER_MONITOR)
        config_str += self.master_monitor.dump_config()

        config_str += "-- Module {0} --\n".format(Ruv0CruModuleid.IDENTITY)
        config_str += self.identity.dump_config()
        return config_str

    def check_git_hash(self, expected_git_hash=None):
        """gets git hash"""
        self.identity.check_git_hash(expected_git_hash=expected_git_hash)

    def check_git_hash_and_date(self, expected_git_hash=None):
        warnings.warn("check_git_hash_and_date() is deprecated; use check_git_hash().", DeprecationWarning)
        self.check_git_hash(expected_git_hash=expected_git_hash)

    def get_dna(self):
        """Gets the FPGA DNA value"""
        self.identity.get_dna()

    def get_microprocessor_counters(self, reg_num, reg_wid=32):
        """Gets the register values from SPI"""
        values = [0] * reg_num

        self.sca._write_spi(0x01, 0x00, reg_wid, 0)

        for i in range(reg_num-1):
            values[i] = self.sca._write_spi(0x01, 0x00, reg_wid, i+1)

        values[reg_num-1] = self.sca._write_spi(0x01, 0x00, reg_wid, 0)

        return values

    def set_test_pattern(self, value, commitTransaction=True):
        """Set the Tx/Rx test pattern"""
        assert (value | 0x7) == 0x7, "pattern value must be between 0 and 7"
        self.write(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.TEST_PATTERN_SEL, value, commitTransaction=commitTransaction)

    def get_test_pattern(self):
        """Read test pattern value"""
        _, val = self.read(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.TEST_PATTERN_SEL)
        return val

    def reset_gbt_fpga(self):
        "General Reset of the GBT_FPGA IP"
        self.write(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.CONTROL_RESETS, 0x1, commitTransaction=True)

    def reset_error_flags(self, commitTransaction=True):
        """Reset Latch Flags for DataErrorSeen and GBT ReadyLost"""
        self.write(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.CONTROL_RESETS, 0x18, commitTransaction=commitTransaction)

    def get_status_flags(self):
        """Read status and error flags for GBT_FPGA IP"""
        _, status_flags = self.read(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.STATUS_FLAGS)
        ret = OrderedDict([
            ("MGTLinkReady", status_flags & 0x1),
            ("RxWordClockReady", (status_flags >> 1) & 0x1),
            ("RxFrameClockReady", (status_flags >> 2) & 0x1),
            ("GbtRxReady", (status_flags >> 3) & 0x1),
            ("RxIsData", (status_flags >> 4) & 0x1),
            ("GbtRxReadyLostFlag", (status_flags >> 5) & 0x1),
            ("GbtRxDataErrorseenFlag", (status_flags >> 6) & 0x1)
        ])
        return ret

    def get_data_error_counter(self):
        """Read the count of data mismatches reported from the gbt_fpga pattern checker"""
        self.read(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.RXDATA_ERROR_CNT_LSB, commitTransaction=False)
        self.read(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.RXDATA_ERROR_CNT_MSB, commitTransaction=False)
        self.flush()
        results = self.read_all()
        return results[0] | (results[1] << 16)

    def get_link_error_counter(self):
        """Read the count of 40Mhz clock cycles where gbt_ready is 0 as reported by the gbt_fpga core"""
        self.read(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.LINK_ERROR_CNT_LSB, commitTransaction=False)
        self.read(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.LINK_ERROR_CNT_MSB, commitTransaction=False)
        self.flush()
        results = self.read_all()
        return results[0] | (results[1] << 16)

    def get_link_error_counter_dis(self):
        """Read the (discriminated)count of transitions from 1 to 0
        in the gbt_ready signal reported by the gbt_fpga core"""
        self.read(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.LINK_ERROR_DISCR_LSB, commitTransaction=False)
        self.read(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.LINK_ERROR_DISCR_MSB, commitTransaction=False)
        self.flush()
        results = self.read_all()
        return results[0] | (results[1] << 16)

    def get_fec_counter(self):
        """Read the count of GBT words modified by the Forward Error Correction (FEC)"""
        self.read(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.RX_FEC_CNT_LSB, commitTransaction=False)
        self.read(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.RX_FEC_CNT_MSB, commitTransaction=False)
        self.flush()
        results = self.read_all()
        return results[0] | (results[1] << 16)

    def get_bitsmodified_counter(self):
        """Read the count of bits corrected by the Forward Error Correction module of the gbt_fpga"""
        self.read(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.RX_BITSMODIFIED_CNT_LSB, commitTransaction=False)
        self.read(Ruv0CruModuleid.GBT_FPGA, WsGbtFpgaAddress.RX_BITSMODIFIED_CNT_MSB, commitTransaction=False)
        self.flush()
        results = self.read_all()
        return results[0] | (results[1] << 16)
