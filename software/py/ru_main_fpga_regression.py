""" Regression test list for Xcku"""

import collections
import logging
import random
import sys
import time
import traceback
import unittest
import os
import can

script_path = os.path.dirname(os.path.realpath(__file__))
modules_path = os.path.join(
    script_path,
    '../../modules/board_support_software/software/py/')
sys.path.append(modules_path)
from module_includes import *

from alpide_control import WsAlpideControlAddress
from alpide_control_monitor import WsAlpideControlMonitorAddress
from can_hlp_comm import CanHlpComm
from communication import WishboneReadError
from gbtx_controller import WsGbtxControllerAddress

from ru_mmcm_gbtx_rxrdy_monitor import WsMmcmGbtxRxrdyMonitorAddress
from i2c_gbtx_monitor import WsI2cGbtxMonitorAddress
from pu_monitor import PuMonitorAddress
from pALPIDE import Alpide, Opcode, CommandRegisterOpcode, Addr
from power_unit import WbI2cPuAddress, WbI2cPuAuxAddress, PowerUnitVersion
from pu_controller import WsPuControllerAddress
from ru_board import XckuModuleid, Ruv0CruModuleid
from ru_gpio_monitor import GpioMonitor
from trigger_handler import WsTriggerHandlerAddress, TriggerSource
from trigger_handler_monitor import WsTriggerHandlerMonitorAddress
from userdefinedexceptions import ChipidMismatchError
from wishbone_wait import WsWishboneWaitAddress
from ws_can_hlp import WsCanHlpAddress
from ws_can_hlp_monitor import WsCanHlpMonitorAddress
from ws_gbtx_flow_monitor import WsGbtxFlowMonitorAddress
from ws_gbt_prbs_chk import WsGbtPrbsChkAddress
from ws_identity import WsIdentityAddress, CounterType, FeeIdLayerId, FeeIdLayerMask
from ws_clock_health_status import WsClockHealthStatusAddress
from ws_system_reset_control import WsSystemResetControlAddress
from ws_master_monitor import WsMasterMonitorAddress
from pa3_fifo import Pa3FifoAddress
from ws_i2c_gbtx import WsI2cGbtxAddress
from ru_data_lane import DataLaneAddress

import communication
import events
import power_unit
import pprint
import ru_board
import ru_eyescan
import ru_gbt_packer
import ru_transition_board
import simulation_if
import trigger
import usb_communication
import ws_gbt_packer_monitor
import ws_radiation_monitor

SERIAL_CRU = "000001"
SERIAL_RDO = "000000"

CAN_NODE_ID = 0xAA
CANBUS_SIM_IF = "vcan0"
CANBUS_HW_IF = "can0"

#################################
# Diagnostic
############################################
#import importlib
#ht_exist = importlib.util.find_spec("hanging_threads")
#if ht_exist:
#    from hanging_threads import start_monitoring
#    monitoring_thread = start_monitoring()
############################################
###########################################

# TODO: Move to configuration file
if "SIM_CI" in os.environ:
    SIMULATION = True
else:
    SIMULATION = False

SIMULATE_CRU = False
DUMP_DP2_DATA = False

if SIMULATION:

    USB_MASTER = False
    CONNECTOR_GTH = 4
    CONNECTOR_GPIO = 0
    CONNECTORS = [CONNECTOR_GTH]
    SENSOR_LIST = [1]

    GTH_LIST = list(range(9))
    GTH_CONNECTOR_LUT = {i : CONNECTOR_GTH for i in SENSOR_LIST}
    GPIO_CONNECTOR_LUT = {i : CONNECTOR_GPIO for i in SENSOR_LIST}
    GPIO_LIST = [0,1,7,8,14,15,21,22] # Stimulates all the connectors
    GPIO_SENSORS_PER_LANE = {i:7 for i in GPIO_LIST}
    GPIO_SENSOR_MASK = {i:0x0 for i in GPIO_LIST}
    GITHASH = 0xBADCAFE
    USE_LTU = True
    USE_ALL_UPLINKS = True # 3 for IB, 2 for OB

    LAYER = 3

    # CAN simulation requires vcan (virtual socketcan interface), not available on windows
    if os.name == "nt":
        USE_CAN = False
    else:
        USE_CAN = False
        #USE_CAN = True

        # Check that vcan interface is actually available, ignore CAN tests if not
        # Needs to be done here before test classes have been defined, it is too late to
        # disable tests in __main__.
        #try:
        #    canbus_test = can.Bus(CANBUS_SIM_IF, bustype='socketcan', receive_own_messages=False)
        #    canbus_test.shutdown()
        #except OSError as e:
        #    if e.strerror == "No such device":
        ##        print(f"CAN interface {CANBUS_SIM_IF} for simulation not available, continuing without CANbus")
        #        print(f"it can be instantiated following the instructions in modules/dcs_canbus/README.md")
        #        print(f"   in the CANbus Regression on RU_mainFPGA section")

        #        USE_CAN = False
        #    else:
        #        raise

    RU_MAIN_REVISION = 2
    RU_MINOR_REVISION = 1
    RU_TRANSITION_BOARD_VERSION = ru_transition_board.TransitionBoardVersion.V2_5

    POWER_BOARD_VERSION = PowerUnitVersion.PROTOTYPE
    POWER_BOARD_FILTER_50HZ_AC_POWER_MAINS_FREQUENCY = True
    POWERUNIT_RESISTANCE_OFFSET_PT100 = 3.4
    POWERUNIT_1_OFFSET_AVDD = [0x1D,0x1D,0x1D,0x1A,0x1B,0x1D,0x1B,0x1C]
    POWERUNIT_1_OFFSET_DVDD = [0x1B,0x1B,0x1B,0x1D,0x19,0x1D,0x1C,0x1D]
    POWERUNIT_2_OFFSET_AVDD = [0x1B,0x1D,0x1C,0x20,0x1C,0x1D,0x1D,0x1D]
    POWERUNIT_2_OFFSET_DVDD = [0x1B,0x1F,0x1C,0x1C,0x1A,0x1B,0x1D,0x1C]

else:
    # CAN simulation requires socketcan interface, not available on windows
    if os.name == "nt":
        USE_CAN = False
    else:
        USE_CAN = False
        #USE_CAN = TRUE

        # Check that can interface is actually available, ignore CAN tests if not
        # Needs to be done here before test classes have been defined, it is too late to
        # disable tests in __main__.
        #try:
        #    canbus_test = can.Bus(CANBUS_HW_IF, bustype='socketcan', receive_own_messages=False)
        #    canbus_test.shutdown()
        #except OSError as e:
        #    if e.strerror == "No such device":
        #        print("CAN interface {} for hardware not available, continuing without CANbus".format(CANBUS_HW_IF))
        #        USE_CAN = False
        #    else:
        #        raise

    CONNECTOR_GTH = 4
    CONNECTOR_GPIO = 1

    # fill in according to what modules are connected here:
    CONNECTORS = [CONNECTOR_GTH, CONNECTOR_GPIO] # first connector is used for connector_lut

    SENSOR_LIST = list(range(9))
    GTH_CONNECTOR_LUT = {i : CONNECTOR_GTH for i in SENSOR_LIST}
    GPIO_CONNECTOR_LUT = {i : CONNECTOR_GPIO for i in SENSOR_LIST}

    RU_MAIN_REVISION = 2
    RU_MINOR_REVISION = 1
    RU_TRANSITION_BOARD_VERSION = ru_transition_board.TransitionBoardVersion.V2_5

    POWER_BOARD_VERSION = PowerUnitVersion.PROTOTYPE
    POWER_BOARD_FILTER_50HZ_AC_POWER_MAINS_FREQUENCY = True
    POWERUNIT_RESISTANCE_OFFSET_PT100 = 3.4
    POWERUNIT_1_OFFSET_AVDD = [0x1D,0x1D,0x1D,0x1A,0x1B,0x1D,0x1B,0x1C]
    POWERUNIT_1_OFFSET_DVDD = [0x1B,0x1B,0x1B,0x1D,0x19,0x1D,0x1C,0x1D]
    POWERUNIT_2_OFFSET_AVDD = [0x1B,0x1D,0x1C,0x20,0x1C,0x1D,0x1D,0x1D]
    POWERUNIT_2_OFFSET_DVDD = [0x1B,0x1F,0x1C,0x1C,0x1A,0x1B,0x1D,0x1C]

    EXCLUDE_GPIO_LIST = [12]
    EXCLUDE_GTH_LIST = []

    LAYER = 3

    GPIO_SENSOR_MASK = ru_transition_board.select_transition_board(ru_main_revision=RU_MAIN_REVISION,
                                                                                  transition_board_version=RU_TRANSITION_BOARD_VERSION).gpio_sensor_mask

    if CONNECTOR_GPIO in CONNECTORS:
        GPIO_LIST = [gpio for gpio in ru_transition_board.select_transition_board(ru_main_revision=RU_MAIN_REVISION,
                                                                                  transition_board_version=RU_TRANSITION_BOARD_VERSION).gpio_subset_map[CONNECTOR_GPIO] if gpio not in EXCLUDE_GPIO_LIST]
    else:
        GPIO_LIST = []

    if CONNECTOR_GTH in CONNECTORS:
        GTH_LIST = [gth for gth in range(9) if gth not in EXCLUDE_GTH_LIST]
    else:
        GTH_LIST = []

    GPIO_SENSORS_PER_LANE = {i:1 for i in GPIO_LIST}

    GITHASH = 0x2afbc2e0
    USB_MASTER = False
    USE_LTU = False
    USE_ALL_UPLINKS = False

boardGlobal = None
boardGlobal_usb = None
boardGlobal_can = None
cru0Global = None
cru1Global = None
cru2Global = None
ltuGlobal = None

sim_comm = None
sim_serv = None
can_comm = None
comm0 = None
comm1 = None
comm2 = None
serv = None

def tearDownModule():
    if can_comm is not None:
        can_comm.close() # Close first as it is always waiting on data

    if SIMULATION:
        if comm0 is not None:
            comm0.close()
        if USE_ALL_UPLINKS and (comm1 is not None):
            comm1.close()
        if comm2 is not None:
            comm2.close()
        if sim_comm is not None:
            sim_comm.close()
        if USB_MASTER and (comm_usb is not None):
            comm_usb.close()
        if sim_serv is not None:
            sim_serv.stop()
    else:
        if comm0 is not None:
            comm0.close_connections()

    if serv is not None:
        serv.stop()


def setUpModule():
    boardGlobal.trigger_handler.set_trigger_source(TriggerSource.GBTx2)


def chunk_list(seq, num=3):
    """Chunks the seq in num approximately equal lists"""
    assert len(set(seq))==len(seq), "seq {}".format(seq)

    k, m = divmod(len(seq), num)
    out = [seq[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(num)]

    tot = [i for ls in out for i in ls]
    assert len(tot)==len(seq), "tot {}, seq {}".format(tot, seq)
    assert len(set(tot))==len(tot), "tot {}, seq {}".format(tot, seq)
    return out


class TestcaseBase(unittest.TestCase):

    connector = None

    def setUp(self):
        assert boardGlobal is not None, "Board not properly defined"
        self.board = boardGlobal
        self.board_usb = boardGlobal_usb
        self.board_can = boardGlobal_can

        self.board.enable_chip2connector_lut(False)
        if USB_MASTER:
            self.board_usb.enable_chip2connector_lut(False)

        self.cru0 = cru0Global
        self.cru1 = cru1Global
        self.cru2 = cru2Global
        self.ltu = ltuGlobal

    def shortDescription(self):
        return None # Disables printing of docstrings for each test

    def send_trigger(self, triggerType=0x10, bc=0xabc, orbit=0x43215678, force_cru=False, sync=True, commitTransaction=True):
        if force_cru:
            if SIMULATION and not SIMULATE_CRU:
                comm0.send_trigger(triggerType, bc, orbit)
            else:
                self.cru0.send_trigger(triggerType, bc, orbit, commitTransaction)
        else:
            if SIMULATION:
                comm2.send_trigger(triggerType, bc, orbit)
                if sync:
                    comm0.send_idle(1)
            else:
                self.ltu.send_trigger(triggerType, bc, orbit, commitTransaction)

    def send_idle_trigger(self, value=1, force_cru=False, sync=True, commitTransaction=False):
        """waits for 25 ns in sim or hw
        sends idles on the selected trigger link

        NOTE: commit transaction is false by default"""
        assert value > 0
        if force_cru:
            if SIMULATION and not SIMULATE_CRU:
                # an idle lasts for 1 40 MHz clock cycle
                comm0.send_idle(value)
            else:
                # wait values are at steps of 160 MHz clock
                self.cru0.wait(4*value, commitTransaction=commitTransaction)
        else:
            if SIMULATION:
                comm2.send_idle(value)
                if sync:
                    comm0.send_idle(value)
            else:
                self.cru0.wait(4*value, commitTransaction=commitTransaction)
                #self.ltu.send_trigger(triggerType=0, bc=0, orbit=0, commitTransaction=commitTransaction)

    def send_bc_counter(self, value=1, start_bc=0, start_orbit=0, bc_wrap=3564, force_cru=False, sync=True, commitTransaction=False):
        """waits for 25 ns in sim or hw
        sends bc counter on the trigger link if LTU, otherwise idles

        NOTE: commit transaction is false by default"""
        assert value > 0
        if force_cru:
            if SIMULATION and not SIMULATE_CRU:
                # an idle lasts for one 40 MHz clock cycle
                gbtx0_sim_comm.send_idle(value)
            else:
                # wait values are at steps of 160 MHz clock
                self.cru0.wait(4 * value, commitTransaction=commitTransaction)
        else:
            if SIMULATION:
                comm2.send_bc_counter(value, start_bc, start_orbit, bc_wrap)
                if sync:
                    comm0.send_idle(value)
            else:
                self.cru0.wait(4 * value, commitTransaction=commitTransaction)

    def flush_trigger(self, force_cru=False):
        """Flush communication for trigger source"""
        if force_cru:
            if SIMULATION and not SIMULATE_CRU:
                comm0.flush()
            else:
                self.cru0.comm.flush()
        else:
            if SIMULATION:
                comm2.flush()
            else:
                self.ltu.comm.flush()

    def send_idle(self, value=1, commitTransaction=False):
        """waits for 25 ns in sim or hw

        NOTE: commit transaction is false by default"""
        assert value > 0
        if SIMULATION and not SIMULATE_CRU:
            # an idle lasts for 1 40 MHz clock cycle
            comm0.send_idle(value)
        else:
            # wait values are at steps of 160 MHz clock
            self.cru0.wait(4 * value, commitTransaction=commitTransaction)

    def send_invalid_swt(self, value=1):
        if SIMULATION and not SIMULATE_CRU:
            comm0.send_invalid_swt(value)

    def send_start_of_triggered(self, bc=0, orbit=0x43215678, sync=True, commitTransaction=True):
        """Sends a SOT trigger"""
        triggerType = (1 << trigger.BitMap.SOT) + (1 << trigger.BitMap.HB) + (1 << trigger.BitMap.TF) + (1 << trigger.BitMap.ORBIT)
        self.send_trigger(triggerType=triggerType, bc=bc, orbit=orbit, sync=sync, commitTransaction=commitTransaction)

    def send_end_of_triggered(self, bc=0, orbit=0x43215678, sync=True, commitTransaction=True):
        """Sends a EOT trigger"""
        triggerType = (1 << trigger.BitMap.EOT) + (1 << trigger.BitMap.HB) + (1 << trigger.BitMap.TF) + (1 << trigger.BitMap.ORBIT)
        self.send_trigger(triggerType=triggerType, bc=bc, orbit=orbit, sync=sync, commitTransaction=commitTransaction)

    def send_start_of_continuous(self, bc=0, orbit=0x43215678, sync=True, commitTransaction=True):
        """Sends a SOC trigger"""
        triggerType = (1 << trigger.BitMap.SOC) + (1 << trigger.BitMap.HB) + (1 << trigger.BitMap.TF) + (1 << trigger.BitMap.ORBIT)
        self.send_trigger(triggerType=triggerType, bc=bc, orbit=orbit, sync=sync, commitTransaction=commitTransaction)

    def send_end_of_continuous(self, bc=0, orbit=0x43215678, sync=True, commitTransaction=True):
        """Sends a EOC trigger"""
        triggerType = (1 << trigger.BitMap.EOC) + (1 << trigger.BitMap.HB) + (1 << trigger.BitMap.TF) + (1 << trigger.BitMap.ORBIT)
        self.send_trigger(triggerType=triggerType, bc=bc, orbit=orbit, sync=sync, commitTransaction=commitTransaction)

    def send_heartbeat(self, bc=0, orbit=0x43215678, sync=True, commitTransaction=True):
        """Sends a HB trigger"""
        triggerType = (1 << trigger.BitMap.HB) | (1 << trigger.BitMap.ORBIT)
        self.send_trigger(triggerType=triggerType, bc=bc, orbit=orbit, sync=sync, commitTransaction=commitTransaction)

    def send_heartbeat_reject(self, bc=0, orbit=0x43215678, sync=True, commitTransaction=True):
        """Sends a HB trigger"""
        triggerType = (1 << trigger.BitMap.HB) | (1 << trigger.BitMap.ORBIT) | (1 << trigger.BitMap.HBr)
        self.send_trigger(triggerType=triggerType, bc=bc, orbit=orbit, sync=sync, commitTransaction=commitTransaction)

    def send_ferst(self, bc=0, orbit=0x43215678, sync=True, commitTransaction=True):
        """Sends a Ferst trigger"""
        triggerType = (1 << trigger.BitMap.FE_RST) | (1 << trigger.BitMap.HB) | (1 << trigger.BitMap.ORBIT) | (1 << trigger.BitMap.HBr) | (1 << trigger.BitMap.TF)
        self.send_trigger(triggerType=triggerType, bc=bc, orbit=orbit, sync=sync, commitTransaction=commitTransaction)

    def sync(self):
        """Reads a board register to align simulator and software"""
        self.flush_trigger()
        self.board.read(1,1)

    def provoke_timebase_lol(self, num_lols=5, start_orbit=0):
        self.board.trigger_handler.enable_timebase_sync()
        self.assertFalse(self.board.trigger_handler.is_timebase_synced(), f"Timebase should be out of sync")
        for lol in range(start_orbit, start_orbit + num_lols):
            for bc in range(20):
                self.send_heartbeat(bc=bc, orbit=lol)
        for i in range(5):
            self.send_heartbeat(bc=0, orbit=start_orbit+num_lols-1)


class TestWishboneSlaves(TestcaseBase):
    """Test functions related to wishbone slaves (not directly the slave functionality)"""
    modules_tested = set()
    modules_skipped = set()

    def _check_bad_results(self, bad_writes, bad_reads, tot_writes=None, tot_reads=None):
        ret = self.board.comm._read_all_bytes(log=False)
        results = communication._get_wb_reads(ret)
        for val in results:
            with self.assertRaises(WishboneReadError, msg=f"\tExpecting a read error for: module {XckuModuleid(int(val[0]) >> 8 & 0x7F)} address {int(val[0]) & 0xFF:#04X}\n"):
                self.board.comm._check_result(val, log=False)
        counters = self.board.master_monitor.read_counters(('WR_ERRORS', 'RD_ERRORS', 'WR_OPERATIONS', 'RD_OPERATIONS'))
        if tot_writes is not None:
            tot_writes += 1 # when starting a latch, the write operations is increased (i.e. when latching)
        self.assertEqual(counters['WR_ERRORS'], bad_writes, "Incorrect number of Write errors")
        self.assertEqual(counters['RD_ERRORS'], bad_reads, "Incorrect number of Read errors")
        if tot_writes is not None and tot_reads is not None:
            self.assertEqual(counters['WR_OPERATIONS'], tot_writes, "Incorrect number of Write operations")
            self.assertEqual(counters['RD_OPERATIONS'], tot_reads, "Incorrect number of Read operations")

    def _slave_test(self, registers, writeValue=0x80, restore=True, skip_illegal_address=False, ignore_unaccounted=False):
        """Test slave addresses. Registers given in the form (module,address,READ,WRITE)"""
        expected_addr = []
        restore_idx = []
        unique_add = set()
        for module_id, address, rd, wr in registers:
            assert not address in unique_add, f"Duplicate entry for address {address} in {XckuModuleid(module_id)}"
            self.modules_tested.add(XckuModuleid(module_id))
            unique_add.add(address)
            if wr:
                if restore and rd:
                    self.board.read(module_id, address, commitTransaction=False)
                    restore_idx.append(len(expected_addr))
                    expected_addr.append(address)
                self.board.write(module_id, address, writeValue,
                                 commitTransaction=False)
            if rd:
                self.board.read(module_id, address, commitTransaction=False)
                expected_addr.append(address)
        self.board.flush()
        results = self.board.comm.read_results()
        result_addr = [addr & 0xFF for addr, data in results]
        if not ignore_unaccounted:
            self.assertEqual(len(unique_add), max(unique_add) + 1,
                             f"One or more addresses unaccounted for in list {unique_add}")
        self.assertEqual(expected_addr, result_addr,
                         "Address read mismatch")

        # test illegal states
        self.board.master_monitor.reset_all_counters(commitTransaction=False)
        tot_writes = 0
        bad_writes = 0
        tot_reads = 0
        bad_reads = 0
        for module_id, address, rd, wr in registers:
            if not wr:
                self.board.write(module_id, address, writeValue,
                                 commitTransaction=False)
                bad_writes += 1
                tot_writes += 1
            if not rd:
                self.board.read(module_id, address, commitTransaction=False)
                bad_reads += 1
                tot_reads += 1

        self.board.flush()
        self._check_bad_results(bad_writes, bad_reads, tot_writes, tot_reads)

        # test illegal address
        if not skip_illegal_address:
            self.board.master_monitor.reset_all_counters(commitTransaction=False)
            tot_writes = bad_writes = 1
            tot_reads = bad_reads = 1
            module_id = registers[0][0]
            self.board.write(module_id, len(registers) + 1, writeValue,
                             commitTransaction=False)
            self.board.read(module_id, len(registers) + 1, commitTransaction=False)
            self.board.flush()
            self._check_bad_results(bad_writes, bad_reads, tot_writes, tot_reads)

        # restore old state
        for module_id, address, rd, wr in registers:
            if wr and restore and rd:
                restore_val = results[restore_idx.pop(0)][1]
                self.board.write(module_id, address, restore_val, commitTransaction=False)
        self.board.flush()

    ### Common test methods

    def _test_counter_monitor(self, module_id, nr_counters):
        """Read/write from slaves derrived from the ws_counter_monitor slave"""
        registers  = [(module_id, 0, False, True)]
        registers += [(module_id, 1, False, True)]
        registers += [(module_id, i, True,  False) for i in range(2, nr_counters + 2)]
        if nr_counters + 2 < 256:
            registers += [(module_id, nr_counters + 2, False, False)]
        self._slave_test(registers, skip_illegal_address=True)

    def _test_gbtx(self, module_id):
        """Read/write from ws_gbt_controller"""
        assert module_id in [XckuModuleid.GBTX0, XckuModuleid.GBTX2]
        self.modules_skipped.add(module_id)
        self.skipTest("Bad override") # TODO: Check in HW
        registers  = [(module_id, 0x00, False,  False )]
        registers += [(module_id, 0x01, False,  False )]
        registers += [(module_id, 0x02, True,  True )]
        registers += [(module_id, 0x03, True,  True )]
        registers += [(module_id, 0x04, True,  True )]
        registers += [(module_id, 0x05, True,  True )]
        registers += [(module_id, 0x06, True,  True )]
        registers += [(module_id, 0x07, True,  True )]
        registers += [(module_id, 0x08, True,  True )]
        registers += [(module_id, 0x09, True,  True )]
        registers += [(module_id, 0x0A, True,  True )]
        registers += [(module_id, 0x0B, True,  True )]
        registers += [(module_id, 0x0C, True,  False)]
        registers += [(module_id, 0x0D, True,  False)]
        registers += [(module_id, 0x0E, True,  False)]
        registers += [(module_id, 0x0F, True,  False)]
        registers += [(module_id, 0x10, True,  False)]
        registers += [(module_id, 0x11, True,  False)]
        registers += [(module_id, 0x12, True,  False)]
        registers += [(module_id, 0x13, True,  False)]
        registers += [(module_id, 0x14, True,  False)]
        registers += [(module_id, 0x15, True,  False)]
        registers += [(module_id, 0x16, False, True )] # killing the core
        registers += [(module_id, 0x17, True,  True )]
        registers += [(module_id, 0x18, False, True )] # killing the core
        registers += [(module_id, 0x19, True,  False)]
        registers += [(module_id, 0x1A, True,  False)]
        if module_id == XckuModuleid.GBTX0: # Register only valid for GBTx01 Controller
            registers += [(module_id, 0x1B, True,  False)]
        self._slave_test(registers)

    def _test_datalane_monitor(self, module_id, lanes):
        nr_counters = self.board._datalane_monitor_ib.nr_counter_regs * len(lanes)
        self._test_counter_monitor(module_id, nr_counters)

    def test_datalane_monitor_ib(self):
        """Read/write from alpide_datalane_monitor slave for IB"""
        self._test_datalane_monitor(XckuModuleid.DATALANE_MONITOR_IB, self.board._datalane_monitor_ib.default_lanes)

    def test_datalane_monitor_ob_1(self):
        """Read/write from data path monitor slave 1 for OB"""
        self._test_datalane_monitor(XckuModuleid.DATALANE_MONITOR_OB_1, self.board._datalane_monitor_ob_1.default_lanes)

    def test_datalane_monitor_ob_2(self):
        """Read/write from data path monitor slave 2 for OB"""
        self._test_datalane_monitor(XckuModuleid.DATALANE_MONITOR_OB_2, self.board._datalane_monitor_ob_2.default_lanes)

    def _test_gbt_packer_monitor(self, module_id):
        nr_counters = len(ws_gbt_packer_monitor.WsGbtPackerMonitorAddress) - 2
        self._test_counter_monitor(module_id, nr_counters)

    def test_radiation_monitor(self):
        nr_counters = len(ws_radiation_monitor.WsRadiationMonitorAddress) - 2
        self._test_counter_monitor(XckuModuleid.RADMON, nr_counters)

    def _add_dead_regs(self, module_id, regs):
        return [(module_id, i.value, False, False) for i in regs if i.name.startswith("DEAD")]

    def _test_pu_main(self, module_id):
        """Read/write from i2c_pu"""
        assert module_id in [XckuModuleid.I2C_PU1, XckuModuleid.I2C_PU2]
        #                                                                      rd     wr)
        registers  = [(module_id, WbI2cPuAddress.InternalRegister           , True,  True)]
        registers += [(module_id, WbI2cPuAddress.TempThreshConfigAddress    , False, True)]
        registers += [(module_id, WbI2cPuAddress.ThresCurrAddress_0         , False, True)]
        registers += [(module_id, WbI2cPuAddress.ThresCurrAddress_1         , False, True)]
        registers += [(module_id, WbI2cPuAddress.ThresCurrAddress_2         , False, True)]
        registers += [(module_id, WbI2cPuAddress.ThresCurrAddress_3         , False, True)]
        registers += [(module_id, WbI2cPuAddress.PotPowerAddress_0          , False, True)]
        registers += [(module_id, WbI2cPuAddress.PotPowerAddress_1          , False, True)]
        registers += [(module_id, WbI2cPuAddress.PotPowerAddress_2          , False, True)]
        registers += [(module_id, WbI2cPuAddress.PotPowerAddress_3          , False, True)]
        registers += [(module_id, WbI2cPuAddress.PotBiasAddress             , False, True)]
        registers += [(module_id, WbI2cPuAddress.ADCAddressSetup_0          , False, True)]
        registers += [(module_id, WbI2cPuAddress.ADCAddressSetup_1          , False, True)]
        registers += [(module_id, WbI2cPuAddress.ADCAddressSetup_2          , False, True)]
        registers += [(module_id, WbI2cPuAddress.ADCAddressSetup_3          , False, True)]
        registers += [(module_id, WbI2cPuAddress.ADCBiasAddressSetup        , False, True)]
        registers += [(module_id, WbI2cPuAddress.ADCAddress_0               , False, True)]
        registers += [(module_id, WbI2cPuAddress.ADCAddress_1               , False, True)]
        registers += [(module_id, WbI2cPuAddress.ADCAddress_2               , False, True)]
        registers += [(module_id, WbI2cPuAddress.ADCAddress_3               , False, True)]
        registers += [(module_id, WbI2cPuAddress.ADCBiasAddress             , False, True)]
        registers += [(module_id, WbI2cPuAddress.Reserved_0                 , False, True)]
        registers += [(module_id, WbI2cPuAddress.IOExpanderBiasAddress      , False, True)]
        registers += [(module_id, WbI2cPuAddress.TempThreshRdAddress        , False, True)]
        registers += [(module_id, WbI2cPuAddress.ADCAddress_0_Read          , False, True)]
        registers += [(module_id, WbI2cPuAddress.ADCAddress_1_Read          , False, True)]
        registers += [(module_id, WbI2cPuAddress.ADCAddress_2_Read          , False, True)]
        registers += [(module_id, WbI2cPuAddress.ADCAddress_3_Read          , False, True)]
        registers += [(module_id, WbI2cPuAddress.ADCBiasAddress_Read        , False, True)]
        registers += [(module_id, WbI2cPuAddress.Reserved_1                 , False, True)]
        registers += [(module_id, WbI2cPuAddress.IOExpanderBiasAddress_Read , False, True)]
        registers += [(module_id, WbI2cPuAddress.TempThreshRdAddress_Read   , False, True)]
        registers += [(module_id, WbI2cPuAddress.I2CDataEmptyAddress        , True,  False)]
        registers += [(module_id, WbI2cPuAddress.I2CDataAddress             , True,  False)]
        self._slave_test(registers)

    def _test_pu_controller(self, module_id):
        """Read/write from pu_controller"""
        assert module_id in [XckuModuleid.I2C_PU1_CONTROLLER, XckuModuleid.I2C_PU2_CONTROLLER]
        #                                                                      rd     wr)
        registers  = [(module_id, i, True, True) for i in range(WsPuControllerAddress.LIMIT_TEMP0, WsPuControllerAddress.LIMIT_TEMP0 + 3)]
        registers += [(module_id, i, True, False) for i in range(WsPuControllerAddress.TEMP_PT0, WsPuControllerAddress.TEMP_PT0 + 3)]
        registers += [(module_id, WsPuControllerAddress.FIFO_RST,              False, True)]
        registers += [(module_id, WsPuControllerAddress.TRIPPED_LTCH,          True,  True)]
        registers += [(module_id, WsPuControllerAddress.ENABLE_PWR,            True,  False)]
        registers += [(module_id, WsPuControllerAddress.ENABLE_BIAS,           True,  False)]
        registers += [(module_id, WsPuControllerAddress.ENABLE_MASK,           True,  True)]
        registers += [(module_id, WsPuControllerAddress.TEMP_INTERLOCK_ENABLE, True,  True)]
        registers += [(module_id, WsPuControllerAddress.PWR_INTERLOCK_ENABLE,  True,  True)]
        registers += [(module_id, i, True, True) for i in range(WsPuControllerAddress.LO_LIMIT_TEMP0, WsPuControllerAddress.LO_LIMIT_TEMP0 + 3)]
        registers += [(module_id, i, True, False) for i in range(WsPuControllerAddress.ADC_00, WsPuControllerAddress.ADC_00 + 35)]
        registers += [(module_id, WsPuControllerAddress.TRIPPED_PWR,           True,  False)]
        registers += [(module_id, WsPuControllerAddress.TRIPPED_BIAS,          True,  False)]
        registers += [(module_id, WsPuControllerAddress.TRIPPED,               True,  False)]
        registers += [(module_id, WsPuControllerAddress.MAX_ADC,               True,  True)]
        self._slave_test(registers)

    def _test_pu_aux(self, module_id):
        assert module_id in [XckuModuleid.I2C_PU1_AUX, XckuModuleid.I2C_PU2_AUX]
        #                                                                            rd,     wr
        registers  = [(module_id, WbI2cPuAuxAddress.Reserved,                       True,  True)]
        registers += [(module_id, WbI2cPuAuxAddress.IOExpanderPowerAddress_0,       False, True)]
        registers += [(module_id, WbI2cPuAuxAddress.IOExpanderPowerAddress_1,       False, True)]
        registers += [(module_id, WbI2cPuAuxAddress.IOExpanderPowerAddress_0_Read,  False, True)]
        registers += [(module_id, WbI2cPuAuxAddress.IOExpanderPowerAddress_1_Read,  False, True)]
        registers += [(module_id, WbI2cPuAuxAddress.I2CDataEmptyAddress,            True, False)]
        registers += [(module_id, WbI2cPuAuxAddress.I2CDataAddress,                 True, False)]
        registers += self._add_dead_regs(module_id, WbI2cPuAuxAddress)
        self._slave_test(registers)

    ### Slave tests

    def test_zzz_check_all_modules_tested(self):
        dead_modules = set([x for x in XckuModuleid if x.name.startswith("DEAD")])
        all_modules = self.modules_tested | self.modules_skipped | dead_modules
        missing_modules = [x for x in XckuModuleid if x not in all_modules]
        assert len(missing_modules) == 0, f"Some modules not present in slave test {missing_modules}"

    def test_wsmstr_gbtx(self):
        """Read/write from ws_master_monitor slave"""
        nr_counters = len(WsMasterMonitorAddress) - 2
        self._test_counter_monitor(XckuModuleid.MASTER_GBTX_MONITOR, nr_counters)

    def test_wsidentity(self):
        """Read/write from ws_identity slave"""
        registers = [
            #                                                                rd     wr
            (XckuModuleid.IDENTITY, WsIdentityAddress.GITHASH_LSB         , True, False),
            (XckuModuleid.IDENTITY, WsIdentityAddress.GITHASH_MSB         , True, False),
            (XckuModuleid.IDENTITY, WsIdentityAddress.SEED                , True, False),
            (XckuModuleid.IDENTITY, WsIdentityAddress.OS_LSB              , True, False),
            (XckuModuleid.IDENTITY, WsIdentityAddress.DIPSWITCH_VAL       , True, False),
            (XckuModuleid.IDENTITY, WsIdentityAddress.DNA_CHUNK_0         , True, False),
            (XckuModuleid.IDENTITY, WsIdentityAddress.DNA_CHUNK_1         , True, False),
            (XckuModuleid.IDENTITY, WsIdentityAddress.DNA_CHUNK_2         , True, False),
            (XckuModuleid.IDENTITY, WsIdentityAddress.DNA_CHUNK_3         , True, False),
            (XckuModuleid.IDENTITY, WsIdentityAddress.DNA_CHUNK_4         , True, False),
            (XckuModuleid.IDENTITY, WsIdentityAddress.DNA_CHUNK_5         , True, False),
            (XckuModuleid.IDENTITY, WsIdentityAddress.UPTIME_MSB          , True, False),
            (XckuModuleid.IDENTITY, WsIdentityAddress.UPTIME_CSB          , True, False),
            (XckuModuleid.IDENTITY, WsIdentityAddress.UPTIME_LSB          , True, False),
            (XckuModuleid.IDENTITY, WsIdentityAddress.TIME_SINCE_RESET_MSB, True, False),
            (XckuModuleid.IDENTITY, WsIdentityAddress.TIME_SINCE_RESET_CSB, True, False),
            (XckuModuleid.IDENTITY, WsIdentityAddress.TIME_SINCE_RESET_LSB, True, False)
         ]
        registers += self._add_dead_regs(XckuModuleid.IDENTITY, WsIdentityAddress)
        self._slave_test(registers)

    def test_ws_clock_health_status(self):
        """Read/write from ws_clock_health_status slave"""
        registers = [
            #                                                                                                  rd     wr
            (XckuModuleid.CLOCK_HEALTH_STATUS, WsClockHealthStatusAddress.RESET_CLOCK_HEALTH_FLAGS           , False, True),
            (XckuModuleid.CLOCK_HEALTH_STATUS, WsClockHealthStatusAddress.CONFIG_RESET                       , True,  True),
            (XckuModuleid.CLOCK_HEALTH_STATUS, WsClockHealthStatusAddress.CLOCK_HEALTH_FLAGS                 , True,  False),
            (XckuModuleid.CLOCK_HEALTH_STATUS, WsClockHealthStatusAddress.TIMEBASE_EVENT_TIMESTAMP_UPTIME_LSB, True,  False),
            (XckuModuleid.CLOCK_HEALTH_STATUS, WsClockHealthStatusAddress.TIMEBASE_EVENT_TIMESTAMP_UPTIME_CSB, True,  False),
            (XckuModuleid.CLOCK_HEALTH_STATUS, WsClockHealthStatusAddress.TIMEBASE_EVENT_TIMESTAMP_UPTIME_MSB, True,  False),
            (XckuModuleid.CLOCK_HEALTH_STATUS, WsClockHealthStatusAddress.CLK_EVENT_TIMESTAMP_UPTIME_LSB     , True,  False),
            (XckuModuleid.CLOCK_HEALTH_STATUS, WsClockHealthStatusAddress.CLK_EVENT_TIMESTAMP_UPTIME_CSB     , True,  False),
            (XckuModuleid.CLOCK_HEALTH_STATUS, WsClockHealthStatusAddress.CLK_EVENT_TIMESTAMP_UPTIME_MSB     , True,  False),
            (XckuModuleid.CLOCK_HEALTH_STATUS, WsClockHealthStatusAddress.TIMEBASE_EVENT_TIMESTAMP_ORBIT_LSB , True,  False),
            (XckuModuleid.CLOCK_HEALTH_STATUS, WsClockHealthStatusAddress.TIMEBASE_EVENT_TIMESTAMP_ORBIT_MSB , True,  False),
            (XckuModuleid.CLOCK_HEALTH_STATUS, WsClockHealthStatusAddress.CLK_EVENT_TIMESTAMP_ORBIT_LSB      , True,  False),
            (XckuModuleid.CLOCK_HEALTH_STATUS, WsClockHealthStatusAddress.CLK_EVENT_TIMESTAMP_ORBIT_MSB      , True,  False)
         ]
        registers += self._add_dead_regs(XckuModuleid.CLOCK_HEALTH_STATUS, WsClockHealthStatusAddress)
        self._slave_test(registers)

    def test_ws_system_reset_control(self):
        """Read/write from ws_system_reset_control slave"""
        registers = [
            #                                                                                           rd     wr
            (XckuModuleid.SYSTEM_RESET_CONTROL, WsSystemResetControlAddress.RESET_CAN_WB              , False, True),
            (XckuModuleid.SYSTEM_RESET_CONTROL, WsSystemResetControlAddress.RESET_WB_INTERCON         , False, True),
            (XckuModuleid.SYSTEM_RESET_CONTROL, WsSystemResetControlAddress.RESET_WB_SLAVES           , False, True),
            (XckuModuleid.SYSTEM_RESET_CONTROL, WsSystemResetControlAddress.RESET_PU_1                , False, True),
            (XckuModuleid.SYSTEM_RESET_CONTROL, WsSystemResetControlAddress.RESET_PU_2                , False, True),
            (XckuModuleid.SYSTEM_RESET_CONTROL, WsSystemResetControlAddress.RESET_I2C_GBT             , False, True),
            (XckuModuleid.SYSTEM_RESET_CONTROL, WsSystemResetControlAddress.RESET_DATAPATH            , False, True),
            (XckuModuleid.SYSTEM_RESET_CONTROL, WsSystemResetControlAddress.RESET_READOUT_MASTER      , False, True),
            (XckuModuleid.SYSTEM_RESET_CONTROL, WsSystemResetControlAddress.RESET_GBT_PACKER          , False, True),
            (XckuModuleid.SYSTEM_RESET_CONTROL, WsSystemResetControlAddress.RESET_PA3_FIFO            , False, True),
            (XckuModuleid.SYSTEM_RESET_CONTROL, WsSystemResetControlAddress.RESET_ALPIDE_CONTROL      , False, True)
         ]
        registers += self._add_dead_regs(XckuModuleid.SYSTEM_RESET_CONTROL, WsSystemResetControlAddress)
        self._slave_test(registers, skip_illegal_address=True, ignore_unaccounted=True)

    def test_gth_control(self):
        """Read/write from gth control aka alpide_frontend_ib_wishbone slave"""
        registers  = [(XckuModuleid.GTH_CONTROL, i, True, True)  for i in [0,2,5,7,8]]
        registers += [(XckuModuleid.GTH_CONTROL, i, True, False) for i in [1,3,4,6]]
        self._slave_test(registers)

    def test_alpide_control(self):
        """Read/write from alpide_control_wishbone slave"""
        registers = [
            #                                                                                      rd     wr
            (XckuModuleid.ALPIDE_CONTROL, WsAlpideControlAddress.WRITE_CTRL                     , False, True),
            (XckuModuleid.ALPIDE_CONTROL, WsAlpideControlAddress.WRITE_ADDRESS                  , True , True),
            (XckuModuleid.ALPIDE_CONTROL, WsAlpideControlAddress.WRITE_DATA                     , True , True),
            (XckuModuleid.ALPIDE_CONTROL, WsAlpideControlAddress.PHASE_FORCE                    , True , True),
            (XckuModuleid.ALPIDE_CONTROL, WsAlpideControlAddress.READ_STATUS                    , True , False),
            (XckuModuleid.ALPIDE_CONTROL, WsAlpideControlAddress.READ_DATA                      , True , False),
            (XckuModuleid.ALPIDE_CONTROL, WsAlpideControlAddress.MANCHESTER_RX_DETECTED         , True , False),
            (XckuModuleid.ALPIDE_CONTROL, WsAlpideControlAddress.SET_DCTRL_TX_MASK              , True , True),
            (XckuModuleid.ALPIDE_CONTROL, WsAlpideControlAddress.MANCHESTER_TX_EN               , True , True),
            (XckuModuleid.ALPIDE_CONTROL, WsAlpideControlAddress.SET_DCTRL_INPUT                , True , True),
            (XckuModuleid.ALPIDE_CONTROL, WsAlpideControlAddress.AUTO_PHASE_OFFSET              , True , True),
            (XckuModuleid.ALPIDE_CONTROL, WsAlpideControlAddress.WAIT_CYCLES                    , True , True),
            (XckuModuleid.ALPIDE_CONTROL, WsAlpideControlAddress.SET_DCLK_PARALLEL_0            , True , True),
            (XckuModuleid.ALPIDE_CONTROL, WsAlpideControlAddress.SET_DCLK_PARALLEL_1            , True , True),
            (XckuModuleid.ALPIDE_CONTROL, WsAlpideControlAddress.SET_DCLK_PARALLEL_2            , True , True),
            (XckuModuleid.ALPIDE_CONTROL, WsAlpideControlAddress.SET_DCLK_PARALLEL_3            , True , True),
            (XckuModuleid.ALPIDE_CONTROL, WsAlpideControlAddress.SET_DCLK_PARALLEL_4            , True , True),
            (XckuModuleid.ALPIDE_CONTROL, WsAlpideControlAddress.DB_FIFO_DATA                   , True , False),
            (XckuModuleid.ALPIDE_CONTROL, WsAlpideControlAddress.DB_FIFO_EMPTY                  , True , False),
            (XckuModuleid.ALPIDE_CONTROL, WsAlpideControlAddress.DB_FIFO_RDCOUNT                , True , False)
        ]
        registers += self._add_dead_regs(XckuModuleid.ALPIDE_CONTROL, WsAlpideControlAddress)
        self._slave_test(registers)
        self.chip = Alpide(self.board, chipid=SENSOR_LIST[0])
        self.chip.setreg_cmd(Command=Opcode.GRST, commitTransaction=False)
        self.chip.setreg_cmd(Command=CommandRegisterOpcode.CMUCLRERR, commitTransaction=False)
        self.board.flush()

    def test_alpide_control_monitor(self):
        """Read/write from alpide control module"""
        nr_counters = len(WsAlpideControlMonitorAddress)-2
        self._test_counter_monitor(XckuModuleid.ALPIDE_CONTROL_MONITOR, nr_counters)

    def test_i2c_gbt(self):
        """Read/write from i2c_gbt slave"""
        #                                                                     rd    wr
        registers  = [(XckuModuleid.I2C_GBT, WsI2cGbtxAddress.ADDRESS_GBTX0, True, True)]
        registers += [(XckuModuleid.I2C_GBT, WsI2cGbtxAddress.ADDRESS_GBTX1, True, True)]
        registers += [(XckuModuleid.I2C_GBT, WsI2cGbtxAddress.ADDRESS_GBTX2, True, True)]
        registers += [(XckuModuleid.I2C_GBT, WsI2cGbtxAddress.DATA,          True, True)]
        registers += [(XckuModuleid.I2C_GBT, WsI2cGbtxAddress.RESET,         False,True)]
        registers += [(XckuModuleid.I2C_GBT, WsI2cGbtxAddress.SNIFF_I2C,     True, False)]
        registers += [(XckuModuleid.I2C_GBT, WsI2cGbtxAddress.DB_FIFO_DATA,  True, False)]
        registers += [(XckuModuleid.I2C_GBT, WsI2cGbtxAddress.DB_FIFO_EMPTY, True, False)]
        registers += [(XckuModuleid.I2C_GBT, WsI2cGbtxAddress.DB_FIFO_RDCNT, True, False)]
        self._slave_test(registers)

    def test_i2c_pu(self):
        """Read/write from i2c_pu1 slave"""
        self._test_pu_main(XckuModuleid.I2C_PU1)
        self._test_pu_main(XckuModuleid.I2C_PU2)

    def test_pu_controller(self):
        """Read/write from pu_controller wishbone slaves"""
        self._test_pu_controller(XckuModuleid.I2C_PU1_CONTROLLER)
        self._test_pu_controller(XckuModuleid.I2C_PU2_CONTROLLER)

    def test_pu_aux(self):
        """Read/write from pu_controller wishbone slaves"""
        self._test_pu_aux(XckuModuleid.I2C_PU1_AUX)
        self._test_pu_aux(XckuModuleid.I2C_PU2_AUX)

    def test_gbtx0(self):
        """Read/write from GBTx01 slave"""
        self._test_gbtx(XckuModuleid.GBTX0)

    def test_gbtx2(self):
        """Read/write from GBTx2 slave"""
        self._test_gbtx(XckuModuleid.GBTX2)

    def test_fw_wait(self):
        """Read/write from wishbone_wait slave"""
        #                                                                     rd     wr
        registers = [
            (XckuModuleid.FW_WAIT, WsWishboneWaitAddress.WAIT_VALUE,          False, True),
            (XckuModuleid.FW_WAIT, WsWishboneWaitAddress.RST_CTRL_CNTRS,      False, True),
            (XckuModuleid.FW_WAIT, WsWishboneWaitAddress.READ_WAIT_EXEC_CNTR, True,  False)
        ]
        self._slave_test(registers)



    def test_sysmon(self):
        """Read/write from sysmon slave"""
        self.modules_skipped.add(XckuModuleid.SYSMON)
        self.skipTest("SYSMON does not allow to write on its own reg 0x00")
        registers = [
            (XckuModuleid.SYSMON, 0x00, False, False),
            (XckuModuleid.SYSMON, 0x01, False, True),
            (XckuModuleid.SYSMON, 0x02, True,  True),
        ]
        self._slave_test(registers)

    def test_gbtx_flow_monitor(self):
        """Read/write from gbtx_flow_monitor slave"""
        nr_counters = len(WsGbtxFlowMonitorAddress)-2
        self._test_counter_monitor(XckuModuleid.GBTX_FLOW_MONITOR, nr_counters)

    def test_ws_usb_if(self):
        """Read/write from ws_usb_if slave"""
        if not USB_MASTER:
            self.modules_tested.add(XckuModuleid.USB_IF)
            self.skipTest("No USB Master -> Cannot test ws_usb_if")
        registers  = [(XckuModuleid.USB_IF, i, False, True)  for i in [0]]
        registers += [(XckuModuleid.USB_IF, i, True,  True)  for i in [7]]
        registers += [(XckuModuleid.USB_IF, i, True,  False) for i in range(1, 6+1)]
        registers += [(XckuModuleid.USB_IF, i, True,  False) for i in range(8, 13+1)]
        self._slave_test(registers)

    def test_wsmstr_usb(self):
        """Read/write from ws_master_monitor slave for USB"""
        if not USB_MASTER:
            self.modules_tested.add(XckuModuleid.MASTER_USB_MONITOR)
            self.skipTest("No USB Master -> Cannot test wsmstr_usb")
        nr_counters = len(WsMasterMonitorAddress)-2
        self._test_counter_monitor(XckuModuleid.MASTER_USB_MONITOR, nr_counters)

    def test_trigger_handler(self):
        """Read/write from trigger_handler slave"""
        #                                                                                   rd     wr
        registers = [
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.ENABLE                 , True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.TRIGGER_PERIOD         , True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.PULSE_nTRIGGER         , True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.TRIGGER_MIN_DISTANCE   , True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.OPERATING_MODE         , True,  False),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.OPCODE_GATING          , True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.TRIGGER_DELAY          , True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.ENABLE_PACKER_0        , True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.ENABLE_PACKER_1        , True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.ENABLE_PACKER_2        , True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.TRIG_SOURCE            , True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.SOX_ORBIT_LSB          , True,  False),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.SOX_ORBIT_MSB          , True,  False),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.SEQ_NUM_HB_PER_TF      , True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.ENABLE_TIMEBASE_SYNC   , True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.TIMEBASE_SYNCED        , True,  False),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.SEQ_ENABLE             , True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.SEQ_CONTINUOUS_N_TRG   , True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.SEQ_NUM_TF             , True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.SEQ_NUM_HBA_PER_TF     , True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.SEQ_PT_MODE            , True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.SEQ_PT_PERIOD          , True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.RM_RO_RESET            , True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.FLUSH_FIFO             , True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.IGNORE_TRG_IN_CONT_MODE, True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.INTERNAL_TRG_GRANT_LSB , True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.INTERNAL_TRG_GRANT_CSB , True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.INTERNAL_TRG_GRANT_MSB , True,  True),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.FIFO_EMPTY             , True,  False),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.EOX_ORBIT_LSB          , True,  False),
            (XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress.EOX_ORBIT_MSB          , True,  False),
        ]
        registers += self._add_dead_regs(XckuModuleid.TRIGGER_HANDLER, WsTriggerHandlerAddress)
        self._slave_test(registers, writeValue=0x00)

    def test_trigger_handler_monitor(self):
        """Read/write from trigger_handler_monitor slave"""
        nr_counters = len(WsTriggerHandlerMonitorAddress) - 2
        self._test_counter_monitor(XckuModuleid.TRIGGER_HANDLER_MONITOR, nr_counters)

    def test_gpio_frontend(self):
        """Read/write from gpio control aka alpide_frontend_ob_wishbone slave"""
        NR_LANES=self.board.gpio.NR_TRANSCEIVERS
        registers =  [(XckuModuleid.GPIO_CONTROL, i, True,  True)  for i in [0,1]]
        registers += [(XckuModuleid.GPIO_CONTROL, i, True,  False) for i in [2,3]]
        registers += [(XckuModuleid.GPIO_CONTROL, i, True,  True)  for i in range(4, 17)]
        registers += [(XckuModuleid.GPIO_CONTROL, i, True,  False) for i in range(17, 17+NR_LANES)]
        registers += [(XckuModuleid.GPIO_CONTROL, i, False, False) for i in range(17+NR_LANES, 49)]
        self._slave_test(registers)

    def test_gth_monitor(self):
        """Read/write from gth_monitor slave for IB"""
        nr_counters = self.board._gth_monitor.nr_counter_regs * len(self.board._gth_monitor.default_lanes)
        self._test_counter_monitor(XckuModuleid.GTH_MONITOR, nr_counters)

    def test_gpio_monitor(self):
        """Read/write from gpio_monitor slave for OB"""
        nr_counters = self.board._gpio_monitor.nr_counter_regs * len(self.board._gpio_monitor.default_lanes)
        self._test_counter_monitor(XckuModuleid.GPIO_MONITOR, nr_counters)

    def _test_data_lane(self, module_id):
        registers = []
        registers += [(module_id, i, True, True) for i in range(0,self.board.lanes_ib.addr_list.ERROR_SIGNATURE_0)]
        registers += [(module_id, i, True, False) for i in range(self.board.lanes_ib.addr_list.ERROR_SIGNATURE_0,
                                                                 len(self.board.lanes_ib.addr_list))]
        self._slave_test(registers, writeValue=0x00)
        self.modules_skipped.add(module_id)

    def test_data_lane_ib(self):
        self._test_data_lane(XckuModuleid.DATA_LANE_IB)

    def test_data_lane_ob(self):
        self._test_data_lane(XckuModuleid.DATA_LANE_OB)

    def test_calibration_lane(self):
        module_id = XckuModuleid.CALIBRATION_LANE
        registers = []
        registers += [(module_id,i,True,True) for i in range(self.board.calibration_lane.addr_list.USER_FIELD_2+1)]
        registers += [(module_id,self.board.calibration_lane.addr_list.RESET,False,True)]
        self._slave_test(registers, writeValue=0x00)

    def test_readout_master(self):
        module_id = XckuModuleid.READOUT_MASTER
        registers = []
        registers += [(module_id, i, True, True) for i in range(self.board.readout_master.addr_list.MAX_NOK_LANES.value+1)]
        registers += [(module_id, i, True, False) for i in range(self.board.readout_master.addr_list.IB_FAULTY_LANES.value,len(self.board.readout_master.addr_list))]
        self._slave_test(registers, writeValue=0x00)

    def test_gbt_packer(self):
        #                                                                                   rd     wr
        registers = [
            (XckuModuleid.GBT_PACKER, ru_gbt_packer.GbtPackerAddress.TIMEOUT_TO_START     , True,  True),
            (XckuModuleid.GBT_PACKER, ru_gbt_packer.GbtPackerAddress.TIMEOUT_START_STOP   , True,  True),
            (XckuModuleid.GBT_PACKER, ru_gbt_packer.GbtPackerAddress.TIMEOUT_IN_IDLE      , True,  True),
            (XckuModuleid.GBT_PACKER, ru_gbt_packer.GbtPackerAddress.RESET                , True,  True),
            (XckuModuleid.GBT_PACKER, ru_gbt_packer.GbtPackerAddress.GBTX_FIFO_EMPTY      , True,  False),
            (XckuModuleid.GBT_PACKER, ru_gbt_packer.GbtPackerAddress.LANE_FIFO_EMPTY      , True,  False)]
        registers += self._add_dead_regs(XckuModuleid.GBT_PACKER, ru_gbt_packer.GbtPackerAddress)
        self._slave_test(registers, writeValue=0x00)

    def test_gbt_packer_0_monitor(self):
        """Read/write from GBT 0 packer monitor"""
        self._test_gbt_packer_monitor(XckuModuleid.GBT_PACKER_0_MONITOR)

    def test_gbt_packer_1_monitor(self):
        """Read/write from GBT 1 packer monitor"""
        self._test_gbt_packer_monitor(XckuModuleid.GBT_PACKER_1_MONITOR)

    def test_gbt_packer_2_monitor(self):
        """Read/write from GBT 2 packer monitor"""
        self._test_gbt_packer_monitor(XckuModuleid.GBT_PACKER_2_MONITOR)

    def test_drp_bridge(self):
        """Read/write from drp_bridge slave"""
        registers =  [(XckuModuleid.GTH_DRP, 0, False, False)]
        registers += [(XckuModuleid.GTH_DRP, 1, False, True)]
        registers += [(XckuModuleid.GTH_DRP, 2, True,  True)]
        self._slave_test(registers, writeValue=0x00)

    def test_mmcm_gbtx_rxrdy_monitor(self):
        """Read/write from mmcm_gbtx_rxrdy_monitor slave"""
        nr_counters = len(WsMmcmGbtxRxrdyMonitorAddress) - 2
        self._test_counter_monitor(XckuModuleid.MMCM_GBTX_RXRDY_MONITOR, nr_counters)

    def test_wsmstr_can(self):
        """Read/write from ws_master_monitor slave"""
        nr_counters = len(WsMasterMonitorAddress) - 2
        self._test_counter_monitor(XckuModuleid.MASTER_CAN_MONITOR, nr_counters)

    def test_can_hlp(self):
        """Read/write from CAN HLP slave"""
        #                                                             rd     wr
        registers = [
            (XckuModuleid.CAN_HLP, WsCanHlpAddress.CTRL,              True,  True),
            (XckuModuleid.CAN_HLP, WsCanHlpAddress.STATUS,            True,  False),
            (XckuModuleid.CAN_HLP, WsCanHlpAddress.CAN_PROP_SEG,      True,  True),
            (XckuModuleid.CAN_HLP, WsCanHlpAddress.CAN_PHASE_SEG1,    True,  True),
            (XckuModuleid.CAN_HLP, WsCanHlpAddress.CAN_PHASE_SEG2,    True,  True),
            (XckuModuleid.CAN_HLP, WsCanHlpAddress.CAN_SJW,           True,  True),
            (XckuModuleid.CAN_HLP, WsCanHlpAddress.CAN_CLK_SCALE,     True,  True),
            (XckuModuleid.CAN_HLP, WsCanHlpAddress.CAN_TEC,           True,  False),
            (XckuModuleid.CAN_HLP, WsCanHlpAddress.CAN_REC,           True,  False),
            (XckuModuleid.CAN_HLP, WsCanHlpAddress.TEST_REG,          True,  True),
            (XckuModuleid.CAN_HLP, WsCanHlpAddress.FSM_STATES,        True,  False)
        ]
        self._slave_test(registers)

    def test_can_hlp_monitor(self):
        """Read/write from CAN HLP monitor slave"""
        nr_counters = len(WsCanHlpMonitorAddress) - 2
        self._test_counter_monitor(XckuModuleid.CAN_HLP_MONITOR, nr_counters)

    def test_i2c_monitor(self):
        """Read/Write test from i2c_monitor slaves"""
        # GBTx I2C monitor
        nr_counters = len(WsI2cGbtxMonitorAddress) - 2
        self._test_counter_monitor(XckuModuleid.I2C_MONITOR_GBTX, nr_counters)

        # PU I2C monitors
        nr_counters = len(PuMonitorAddress) - 2
        self._test_counter_monitor(XckuModuleid.MONITOR_PU1_MAIN, nr_counters)
        self._test_counter_monitor(XckuModuleid.MONITOR_PU1_AUX,  nr_counters)
        self._test_counter_monitor(XckuModuleid.MONITOR_PU2_MAIN, nr_counters)
        self._test_counter_monitor(XckuModuleid.MONITOR_PU2_AUX,  nr_counters)

    def test_gbtx2_prbs_chk(self):
        """Read/write from PRBS checker slave"""
        registers =  [(XckuModuleid.GBTX2_PRBS_CHK, WsGbtPrbsChkAddress.RST_LATCH, False, True)]
        registers += [(XckuModuleid.GBTX2_PRBS_CHK, WsGbtPrbsChkAddress.CONTROL,   True,  True)]
        registers += [(XckuModuleid.GBTX2_PRBS_CHK, WsGbtPrbsChkAddress.ERRORS,    True,  False)]
        self._slave_test(registers)

    def test_pa3_fifo_mon(self):
        """Read/write from pa3_fifo_monitor slave"""
        nr_counters = len(self.board._pa3fifo_monitor.registers) - 2
        self._test_counter_monitor(XckuModuleid.PA3_FIFO_MONITOR, nr_counters)

    def test_pa3_fifo(self):
        """Read/write from pa3_fifo_wb_slave"""
        registers =  [(XckuModuleid.PA3_FIFO, Pa3FifoAddress.WR_FIFO_DATA,  False, True)]
        registers += [(XckuModuleid.PA3_FIFO, Pa3FifoAddress.FIFO_RESET,    False, True)]
        registers += self._add_dead_regs(XckuModuleid.PA3_FIFO, Pa3FifoAddress)
        self._slave_test(registers)


class TestWishboneMaster(TestcaseBase):
    """Test functions related to the wishbone master"""

    def test_access_nonexist(self):
        """Communicates with the last valid address of the Xcku"""
        self.board.write(63, 0x00, 0x00, commitTransaction=False)
        self.board.read(63, 0x00, commitTransaction=False)
        self.board.flush()
        with self.assertRaises(WishboneReadError):
            self.board.comm.read_results()

class TestSystemResetControl(TestcaseBase):

    def test_reset_swt_wb(self):
        """Test whether a reset of the SWT WB modules via SWT breaks a subsequent WB transaction"""
        self.board.system_reset_control.reset_swt_wb(commitTransaction=False)
        self.sync()
        self.board.identity.get_git_hash()


    def test_reset_wb_intercon(self):
        """Test whether a reset of the WB intercon breaks a subsequent WB transaction"""
        self.board.system_reset_control.reset_wb_intercon(commitTransaction=False)
        self.board.identity.get_git_hash()

class TestWsClockHealthStatus(TestcaseBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        board = boardGlobal
        board.trigger_handler.enable()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        board = boardGlobal
        board.trigger_handler.disable()

    def test_lol_timebase_config_reset_enable_th(self):
        self.board.clock_health_status.set_config_reset_enable_th()
        self.board.clock_health_status.clear_config_reset_sox()
        assert not self.board.clock_health_status.is_lol_timebase_set(), "LOL Timebase should not be set"
        # Check that sticky gets set when trigger handler is disabled
        self.board.trigger_handler.disable()
        self.provoke_timebase_lol(num_lols=1, start_orbit=500)
        assert self.board.clock_health_status.is_lol_timebase_set(), "LOL Timebase should be set"
        # Ensure that sticky is reset on SOR
        self.board.trigger_handler.enable()
        assert not self.board.clock_health_status.is_lol_timebase_set(), "LOL Timebase should not be set"
        # Check that sticky gets set when trigger handler is enabled
        self.provoke_timebase_lol(num_lols=1, start_orbit=1000)
        assert self.board.clock_health_status.is_lol_timebase_set(), "LOL Timebase should be set"
        # Ensure that sticky is reset on write to reset register
        self.board.clock_health_status.reset_clock_health_flags()
        assert not self.board.clock_health_status.is_lol_timebase_set(), "LOL Timebase should not be set"
        self.board.trigger_handler.enable()
        self.board.clock_health_status.clear_config_reset_enable_th()
        self.board.clock_health_status.set_config_reset_sox()

    def test_lol_timebase_config_reset_sox(self):
        self.board.clock_health_status.clear_config_reset_enable_th()
        self.board.clock_health_status.set_config_reset_sox()
        assert not self.board.clock_health_status.is_lol_timebase_set(), "LOL Timebase should not be set"
        # Check that sticky gets set when trigger handler is disabled
        self.board.trigger_handler.disable()
        self.provoke_timebase_lol(num_lols=1, start_orbit=2000)
        assert self.board.clock_health_status.is_lol_timebase_set(), "LOL Timebase should be set"
        # Ensure that sticky is not reset on Trigger Handler enable
        self.board.trigger_handler.enable()
        assert self.board.clock_health_status.is_lol_timebase_set(), "LOL Timebase should be set"
        # Ensure that sticky is reset on SoX
        self.send_start_of_continuous()
        self.send_idle(3)
        assert not self.board.clock_health_status.is_lol_timebase_set(), "LOL Timebase should not be set"
        self.send_end_of_continuous()
        # Check that sticky gets set when trigger handler is enabled
        self.provoke_timebase_lol(num_lols=1, start_orbit=3000)
        assert self.board.clock_health_status.is_lol_timebase_set(), "LOL Timebase should be set"
        # Ensure that sticky is reset on write to reset register
        self.board.clock_health_status.reset_clock_health_flags()
        assert not self.board.clock_health_status.is_lol_timebase_set(), "LOL Timebase should not be set"
        self.board.trigger_handler.enable()

    def test_timebase_event_timestamp(self):
        assert self.board.clock_health_status.get_timebase_event_timestamp_uptime() == 0x0, "Timestamp should be zero"
        # Check that timestamp is set to nonzero when lol_timebase
        self.provoke_timebase_lol(num_lols=1, start_orbit=5000)
        assert self.board.clock_health_status.get_timebase_event_timestamp_uptime() != 0x0, "Timestamp should be non-zero"
        assert self.board.clock_health_status.get_timebase_event_timestamp_uptime() == self.board.clock_health_status.get_timebase_event_timestamp_uptime(), "Timestamp should be static"
        assert self.board.clock_health_status.get_timebase_event_timestamp_orbit() == 5000, f"Timestamp should be value of orbit {5000}, was: {self.board.clock_health_status.get_timebase_event_timestamp_orbit()}"
        # Ensure that timestamp get reset
        self.board.clock_health_status.reset_clock_health_flags()
        assert self.board.clock_health_status.get_timebase_event_timestamp_uptime() == 0x0, "Timestamp should be zero"
        assert self.board.clock_health_status.get_timebase_event_timestamp_orbit() == 0x0, "Timestamp should be zero"

    def test_clk_event_timestamp(self):
        self.send_start_of_continuous()
        assert self.board.clock_health_status.get_clk_event_timestamp_uptime() == 0x0, "Timestamp should be zero"
        # Check that timestamp is set to nonzero when lol_clk
        sim_comm.set_pa3_in(los=1, lol=1)
        assert self.board.clock_health_status.get_clk_event_timestamp_uptime() != 0x0, "Timestamp should be non-zero"
        assert self.board.clock_health_status.get_clk_event_timestamp_orbit() != 0x0, "Timestamp should be non-zero"
        assert self.board.clock_health_status.get_clk_event_timestamp_uptime() == self.board.clock_health_status.get_clk_event_timestamp_uptime(), "Timestamp should be static"
        assert self.board.clock_health_status.get_clk_event_timestamp_orbit() == self.board.clock_health_status.get_clk_event_timestamp_orbit(), "Timestamp should be static"
        # Ensure that timestamp get reset
        self.board.clock_health_status.reset_clock_health_flags()
        assert self.board.clock_health_status.get_clk_event_timestamp_uptime() == 0x0, "Timestamp should be zero"
        assert self.board.clock_health_status.get_clk_event_timestamp_orbit() == 0x0, "Timestamp should be zero"
        sim_comm.set_pa3_in(los=0, lol=0)

class TriggerHandlerBaseTest:
    class TestTriggerHandler(TestcaseBase):
        @classmethod
        def setUpClass(cls):
            super().setUpClass()
            board = boardGlobal
            board.trigger_handler.enable(commitTransaction=False)
            board.trigger_handler.set_trigger_minimum_distance(1, commitTransaction=False)
            board.readout_master.set_ib_enabled_lanes(lanes=0, commitTransaction=False)
            board.readout_master.set_ob_enabled_lanes(lanes=0, commitTransaction=False)
            board.read(1,1) # Sync

        @classmethod
        def tearDownClass(cls):
            super().tearDownClass()
            board = boardGlobal
            board.trigger_handler.disable(commitTransaction=False)
            board.trigger_handler.set_trigger_minimum_distance(0xf0, commitTransaction=False)
            board.readout_master.set_ib_enabled_lanes(lanes=0x1ff, commitTransaction=False)
            board.readout_master.set_ob_enabled_lanes(lanes=0xfffffff, commitTransaction=True)

        def setUp(self):
            super().setUp()
            self.mode = 'none'
            self.board.trigger_handler.set_ignore_trg_in_cont_mode(value=0x0, commitTransaction=False)
            self.sync()

        def _test_send_trigger_in_mode(self):
            assert self.mode in ['triggered', 'none']
            if self.mode == 'none':
                expected_trigger = 0
            else:
                expected_trigger = 1
            IDLE_TIME = 20
            self.board.alpide_control.reset_counters(commitTransaction=False)
            self.board.trigger_handler.reset_counters(commitTransaction=False)
            self.sync()
            self.send_trigger(commitTransaction=False)
            self.send_idle_trigger(IDLE_TIME, commitTransaction=True)
            self.send_idle(3)
            alpide_control_counters = self.board.alpide_control.read_counters(('OPCODE', 'TRIGGER_SENT'))
            trigger_handler_counters = self.board.trigger_handler.read_counters('TRIGGER_SENT')
            for value in ['OPCODE', 'TRIGGER_SENT']:
                self.assertEqual(alpide_control_counters[value], expected_trigger, msg="Wrong counter {2} value, got {0}, expected {1}".format(alpide_control_counters[value], expected_trigger, value))
            self.assertEqual(
                trigger_handler_counters['TRIGGER_SENT'], expected_trigger,
                "Not all Triggers sent: {0}/{1}".format(trigger_handler_counters['TRIGGER_SENT'], expected_trigger))

        def _test_mode(self, expect_triggered=0, expect_continuous=0, startup=False):
            """Checks if the is in the correct state"""
            assert expect_continuous | 1 == 1
            assert expect_triggered | 1 == 1
            if startup:
                extramsg = ' at startup'
            else:
                extramsg = ''
            self.send_idle(3)
            expect = {'is_triggered':expect_triggered, 'is_continuous':expect_continuous}
            mode, modedict = self.board.trigger_handler.get_operating_mode()
            self.assertEqual(modedict, expect, msg="Mode is not correct{3}: expect {0}, got {1}. Dict: {2}".format(expect, mode, modedict, extramsg))

        def test_debug_fifo(self):
            self.skipTest(f"Test is only ran manually by commenting out this line")
            self.provoke_timebase_lol(num_lols=1, start_orbit=5000)
            self.send_idle(10)
            print(self.board.trigger_handler.get_debug_fifo())

        def test_ignored_triggers(self):
            """Test that the triggers are ignored"""
            if self.mode in ['continuous', 'triggered']:
                # in those modes triggers are echoed instead of ignored
                self.skipTest(f"Triggers are echoed instead of ignored in mode '{self.mode}'")
            IDLE_TIME = 2
            IGNORE_LIST = [trigger.BitMap.ORBIT, trigger.BitMap.HC, trigger.BitMap.PP, trigger.BitMap.CAL, trigger.BitMap.TF, trigger.BitMap.PHYSICS]
            self.board.trigger_handler.reset_counters(commitTransaction=False)
            self.sync()
            for trig in IGNORE_LIST:
                triggerType = 1 << trig
                self.send_trigger(triggerType=triggerType, bc=0xabc, orbit=0x43215678, commitTransaction=False)
                self.send_idle_trigger(IDLE_TIME, commitTransaction=False)
            self.flush_trigger()
            self.send_idle(3)
            trigger_handler_counters = self.board.trigger_handler.read_counters('TRIGGER_IGNORED')
            self.assertEqual(trigger_handler_counters['TRIGGER_IGNORED'], len(IGNORE_LIST), "Not enough ignored triggers got/expected {}/{}".format(trigger_handler_counters['TRIGGER_IGNORED'], len(IGNORE_LIST)))

        def test_echoed_triggers(self):
            """Test that the triggers are echoed"""
            if self.mode in ['continuous_reject', 'none', 'triggered_reject']:
                # in those modes triggers are ignored instead of echoed
                self.skipTest(f"Triggers are ignored instead of echoed in mode '{self.mode}'")
            IDLE_TIME = 4
            ECHO_LIST = [trigger.BitMap.ORBIT, trigger.BitMap.HC, trigger.BitMap.PP, trigger.BitMap.CAL, trigger.BitMap.TF]
            if self.mode == 'continuous':
                ECHO_LIST.append(trigger.BitMap.PHYSICS)
            else:
                ECHO_LIST.append(trigger.BitMap.HB)
            self.send_idle(3)
            self.board.trigger_handler.reset_counters(commitTransaction=False)
            self.sync()
            for trig in ECHO_LIST:
                triggerType = 1 << trig
                self.send_trigger(triggerType=triggerType, bc=0xabc, orbit=0x43215678, commitTransaction=False)
                self.send_idle_trigger(IDLE_TIME, commitTransaction=False)
            self.send_idle_trigger(IDLE_TIME, commitTransaction=False)
            self.flush_trigger()
            self.send_idle(3)
            trigger_handler_counters = self.board.trigger_handler.read_counters('TRIGGER_ECHOED')
            self.assertEqual(trigger_handler_counters['TRIGGER_ECHOED'], len(ECHO_LIST), "Not enough echoed triggers got/expected {}/{}".format(trigger_handler_counters['TRIGGER_ECHOED'], len(ECHO_LIST)))

        def test_ignored_triggers_in_cont(self):
            """Test that the triggers are ignored in continuous mode when setting is enabled"""
            if self.mode in ['triggered', 'continuous_reject', 'none', 'triggered_reject']:
                # in those modes, the ignore trigger configuration is not used
                self.skipTest(f"ignore_trg_in_cont_mode not used in '{self.mode}'")
            IDLE_TIME = 2
            IGNORE_LIST = [trigger.BitMap.ORBIT, trigger.BitMap.HC, trigger.BitMap.PP, trigger.BitMap.CAL, trigger.BitMap.TF, trigger.BitMap.PHYSICS]
            self.board.trigger_handler.reset_counters(commitTransaction=False)
            self.board.trigger_handler.set_ignore_trg_in_cont_mode(value=0x1, commitTransaction=False)
            self.sync()
            for trig in IGNORE_LIST:
                triggerType = 1 << trig
                self.send_trigger(triggerType=triggerType, bc=0xabc, orbit=0x43215678, commitTransaction=False)
                self.send_idle_trigger(IDLE_TIME, commitTransaction=False)
            self.flush_trigger()
            self.send_idle(3)
            trigger_handler_counters = self.board.trigger_handler.read_counters('TRIGGER_IGNORED')
            self.assertEqual(trigger_handler_counters['TRIGGER_IGNORED'], len(IGNORE_LIST), "Not enough ignored triggers got/expected {}/{}".format(trigger_handler_counters['TRIGGER_IGNORED'], len(IGNORE_LIST)))

        def test_send_soc(self):
            """Sends a SOC, expect nothing, except in none mode"""
            self.send_start_of_continuous()
            self.send_idle(3)
            _, mode = self.board.trigger_handler.get_operating_mode()
            self.assertEqual(mode['is_triggered'], self.mode in ['triggered', 'triggered_reject'])
            self.assertEqual(mode['is_continuous'], self.mode in ['continuous', 'continuous_reject', 'none'])
            if self.mode == 'none':
                self.send_end_of_continuous()

        def test_send_eoc(self):
            """Sends a EOC, expect nothing"""
            self.send_end_of_continuous()
            self.send_idle(3)
            _, mode = self.board.trigger_handler.get_operating_mode()
            self.assertFalse(mode['is_continuous'])
            self.assertEqual(mode['is_triggered'], self.mode in ['triggered', 'triggered_reject'])

        def test_send_sot(self):
            """Sends a SOT, expect nothing, except in none mode"""
            self.send_start_of_triggered()
            self.send_idle(3)
            _, mode = self.board.trigger_handler.get_operating_mode()
            self.assertEqual(mode['is_continuous'], self.mode in ['continuous', 'continuous_reject'])
            self.assertEqual(mode['is_triggered'], self.mode in ['triggered', 'triggered_reject', 'none'])
            if self.mode == 'none':
                self.send_end_of_triggered()

        def test_send_eot(self):
            """Sends a EOT, expect nothing"""
            self.send_end_of_triggered()
            self.send_idle(3)
            _, mode = self.board.trigger_handler.get_operating_mode()
            self.assertFalse(mode['is_triggered'])
            self.assertEqual(mode['is_continuous'], self.mode in ['continuous', 'continuous_reject'])

        def test_send_ferst(self):
            """Sends a FErst, expect nothing"""
            self.send_ferst()
            self.send_idle(3)
            trigger_handler_counters = self.board.trigger_handler.read_counters('FERST')
            self.assertEqual(trigger_handler_counters['FERST'], 1, "No FErst trigger registered.")

class TestTriggerHandlerNoMode(TriggerHandlerBaseTest.TestTriggerHandler):
    """Tests relative to the trigger handler in no mode (i.e. inactive)"""

    def test_send_trigger_reject(self):
        """Send one PhT trigger out of mode, none expected"""
        self._test_send_trigger_in_mode()

    def test_ro_no_det(self):
        """ Checks if the RO_NO_DET mode is set correctly based on enabling Trigger Handler and gating opcodes"""
        self.board.trigger_handler.disable()
        self.assertTrue(self.board.trigger_handler.is_ro_no_det(), f"Trigger Handler should be RO_NO_DET when disabled")
        self.assertFalse(self.board.trigger_handler.is_ro_with_det(), f"Trigger Handler should not be RO_WITH_DET when disabled")
        self.board.trigger_handler.set_opcode_gating(1)
        self.assertTrue(self.board.trigger_handler.is_ro_no_det(), f"Trigger Handler should be RO_NO_DET when disabled AND opcode gating")
        self.assertFalse(self.board.trigger_handler.is_ro_with_det(), f"Trigger Handler should not be RO_WITH_DET when disabled AND opcode gating")
        self.board.trigger_handler.enable()
        self.assertTrue(self.board.trigger_handler.is_ro_no_det(), f"Trigger Handler should be RO_NO_DET when opcode gating")
        self.assertFalse(self.board.trigger_handler.is_ro_with_det(), f"Trigger Handler should not be RO_WITH_DET when opcode gating")
        self.board.trigger_handler.set_opcode_gating(0)
        self.assertFalse(self.board.trigger_handler.is_ro_no_det(), f"Trigger Handler should not be RO_NO_DET when not opcode gating nor disabled")
        self.assertTrue(self.board.trigger_handler.is_ro_with_det(), f"Trigger Handler should be RO_WITH_DET when not opcode gating nor disabled")

    def test_timebase_sync(self):
        """ Checks that timebase gets synced and then lost the expected number of times """
        self.board.trigger_handler.disable()
        self.board.trigger_handler.enable_timebase_sync()
        self.assertFalse(self.board.trigger_handler.is_timebase_synced(), f"Timebase should be out of sync")
        self.provoke_timebase_lol(num_lols=5)
        self.assertFalse(self.board.trigger_handler.is_timebase_synced(), f"Timebase should be out of sync")
        trigger_handler_counters = self.board.trigger_handler.read_counters('LOL_TIMEBASE')
        self.assertEqual(trigger_handler_counters['LOL_TIMEBASE'], 5, f"LOL was not expected value: {trigger_handler_counters['LOL_TIMEBASE']}, expected: 5")
        self.board.trigger_handler.enable()

    def test_mode_status_continuous(self):
        """Checks if the fsm enters correctly in continuous mode"""
        self._test_mode(expect_triggered=0, expect_continuous=0, startup=True)
        self.send_start_of_continuous()
        self._test_mode(expect_triggered=0, expect_continuous=1)
        self.send_end_of_continuous()
        self._test_mode(expect_triggered=0, expect_continuous=0)

    def test_mode_status_triggered(self):
        """Checks if the fsm enters correctly in triggered mode"""
        self._test_mode(expect_triggered=0, expect_continuous=0, startup=True)
        self.send_start_of_triggered()
        self._test_mode(expect_triggered=1, expect_continuous=0)
        self.send_end_of_triggered()
        self._test_mode(expect_triggered=0, expect_continuous=0)


class TestTriggerHandlerTriggeredMode(TriggerHandlerBaseTest.TestTriggerHandler):
    """Tests relative to the trigger handler in triggered mode"""

    def setUp(self):
        super().setUp()
        self.mode = 'triggered'
        self.send_start_of_triggered(commitTransaction=True)

    def tearDown(self):
        super().tearDown()
        self.send_end_of_triggered(commitTransaction=True)

    def test_send_trigger(self):
        """Send one PhT trigger in trigger mode, expect one"""
        self._test_send_trigger_in_mode()

    def test_trigger_too_close_reject(self):
        """Sends multiple triggers in triggered mode too close in time,
        with a different bc, should not generate a trigger to sensor"""
        EXPECTED_TRIGGER_NR = 1
        EXPECTED_TRIGGER_ECHOED_NR = 1
        IDLE_TIME = 10
        self.board.trigger_handler.set_trigger_minimum_distance(20, commitTransaction=False)
        self.board.alpide_control.reset_counters(commitTransaction=False)
        self.board.trigger_handler.reset_counters(commitTransaction=False)
        self.sync()
        self.send_trigger(commitTransaction=False)
        self.send_idle_trigger(1, commitTransaction=False)
        self.send_trigger(bc=0x123, commitTransaction=False)
        self.send_idle_trigger(IDLE_TIME, commitTransaction=True)
        self.send_idle(3)
        alpide_control_counters = self.board.alpide_control.read_counters('TRIGGER_SENT')
        trigger_handler_counters = self.board.trigger_handler.read_counters(('TRIGGER_SENT', 'TRIGGER_ECHOED'))
        self.board.trigger_handler.set_trigger_minimum_distance(1, commitTransaction=False)
        self.sync()
        self.assertEqual(
            trigger_handler_counters['TRIGGER_SENT'], EXPECTED_TRIGGER_NR,
            "Not all Triggers sent: {0}/{1}".format(trigger_handler_counters['TRIGGER_SENT'], EXPECTED_TRIGGER_NR))
        self.assertEqual(
            alpide_control_counters['TRIGGER_SENT'], EXPECTED_TRIGGER_NR,
            "Not all Triggers sent: {0}/{1}".format(alpide_control_counters['TRIGGER_SENT'], EXPECTED_TRIGGER_NR))
        self.assertEqual(
            trigger_handler_counters['TRIGGER_ECHOED'], EXPECTED_TRIGGER_ECHOED_NR,
            "Triggers not sent not correct: {0}/{1}".format(trigger_handler_counters['TRIGGER_ECHOED'], EXPECTED_TRIGGER_ECHOED_NR))

    def test_send_multiple_triggers(self, trigger_nr=10):
        """Sends multiple triggers in triggered mode properly spaced"""
        assert trigger_nr > 0
        IDLE_TIME = 20
        self.board.alpide_control.reset_counters(commitTransaction=False)
        self.board.trigger_handler.reset_counters(commitTransaction=False)
        self.sync()
        for _ in range(trigger_nr):
            self.send_trigger(commitTransaction=False)
            self.send_idle_trigger(IDLE_TIME, commitTransaction=False)
        self.flush_trigger()
        self.send_idle(3)
        alpide_control_counters = self.board.alpide_control.read_counters('TRIGGER_SENT')
        trigger_handler_counters = self.board.trigger_handler.read_counters(('TRIGGER_SENT', 'TRIGGER_ECHOED'))
        self.assertEqual(
            alpide_control_counters['TRIGGER_SENT'], trigger_nr,
            "Not all Triggers sent: {0}/{1}".format(alpide_control_counters['TRIGGER_SENT'], trigger_nr))
        self.assertEqual(
            trigger_handler_counters['TRIGGER_SENT'], trigger_nr,
            "Not all Triggers sent: {0}/{1}".format(trigger_handler_counters['TRIGGER_SENT'], trigger_nr))
        EXPECTED_TRIGGER_ECHOED_NR = 0
        self.assertEqual(
            trigger_handler_counters['TRIGGER_ECHOED'], EXPECTED_TRIGGER_ECHOED_NR,
            "Triggers not sent not correct: {0}/{1}".format(trigger_handler_counters['TRIGGER_ECHOED'], EXPECTED_TRIGGER_ECHOED_NR))

    def test_send_pulse(self):
        """Test sending a pulse"""
        expected_pulse = 1
        expected_trigger = 0
        IDLE_TIME = 10
        self.board.trigger_handler.configure_to_send_pulses(commitTransaction=False)
        self.board.alpide_control.reset_counters(commitTransaction=False)
        self.board.trigger_handler.reset_counters(commitTransaction=False)
        self.sync()
        self.send_trigger(commitTransaction=False)
        self.send_idle_trigger(IDLE_TIME, commitTransaction=True)
        self.send_idle(3)
        alpide_control_counters = self.board.alpide_control.read_counters(('TRIGGER_SENT', 'OPCODE', 'PULSE_SENT'))
        trigger_handler_counters = self.board.trigger_handler.read_counters('TRIGGER_SENT')
        self.board.trigger_handler.configure_to_send_triggers(commitTransaction=False)
        self.sync()
        self.assertEqual(trigger_handler_counters['TRIGGER_SENT'], expected_pulse,
                         "Not all Pulses sent: {0}/{1}".format(trigger_handler_counters['TRIGGER_SENT'], expected_pulse))
        for value in ['OPCODE', 'PULSE_SENT']:
            self.assertEqual(alpide_control_counters[value], expected_pulse, msg="Wrong counter {2} value, got {0}, expected {1}".format(alpide_control_counters[value], expected_pulse, value))
        self.assertEqual(alpide_control_counters['TRIGGER_SENT'], expected_trigger, msg="Wrong counter expected_trigger value, got {0}, expected {1}".format(alpide_control_counters['TRIGGER_SENT'], expected_trigger))

    def test_trigger_gating(self):
        """test sending a trigger when gating, expect no trigger sent"""
        expected_trigger = 0
        expected_gated_trigger = 1
        IDLE_TIME = 30
        self.board.trigger_handler.set_opcode_gating(1, commitTransaction=False)
        self.board.alpide_control.reset_counters(commitTransaction=False)
        self.board.trigger_handler.reset_counters(commitTransaction=False)
        self.sync()
        self.send_trigger(commitTransaction=False)
        self.send_idle_trigger(IDLE_TIME, commitTransaction=True)
        self.send_idle(3)
        alpide_control_counters = self.board.alpide_control.read_counters('TRIGGER_SENT')
        trigger_handler_counters = self.board.trigger_handler.read_counters(('TRIGGER_SENT', 'TRIGGER_GATED'))
        self.board.trigger_handler.set_opcode_gating(0, commitTransaction=False)
        self.sync()
        self.send_heartbeat(commitTransaction=True) # Gating only ends on HB
        self.assertEqual(trigger_handler_counters['TRIGGER_SENT'], expected_trigger,
                         "Too many triggers sent: {0}/{1}".format(trigger_handler_counters['TRIGGER_SENT'], expected_trigger))
        self.assertEqual(trigger_handler_counters['TRIGGER_GATED'], expected_gated_trigger,
                         "Not all trigger gated: {0}/{1}".format(trigger_handler_counters['TRIGGER_GATED'], expected_gated_trigger))
        self.assertEqual(alpide_control_counters['TRIGGER_SENT'], expected_trigger, msg="Wrong counter expected_trigger value, got {0}, expected {1}".format(alpide_control_counters['TRIGGER_SENT'], expected_trigger))


class TestTriggerHandlerContinuousMode(TriggerHandlerBaseTest.TestTriggerHandler):
    """Tests relative to the trigger handler in continuous mode with a SOC and HB together"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        board = boardGlobal
        cls.trigger_period = 20
        board.trigger_handler.set_trigger_period(cls.trigger_period, commitTransaction=False)
        board.read(1,1) # sync

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        board = boardGlobal
        board.trigger_handler.set_trigger_period(0x37B, commitTransaction=False)
        board.read(1,1) # sync

    def setUp(self):
        super().setUp()
        self.send_start_of_continuous(commitTransaction=True)
        self.mode = 'continuous'

    def tearDown(self):
        super().tearDown()
        self.send_end_of_continuous()

    def test_send_hb(self):
        """Sends a HB, expect triggers"""
        TESTS = 2
        expected_triggers_min = TESTS
        expected_ignored_triggers = 0
        IDLE_TIME = 2 # Set shorter than trigger period to only get HBs
        self.board.alpide_control.reset_counters(commitTransaction=False)
        self.board.trigger_handler.reset_counters(commitTransaction=False)
        self.sync()
        for _ in range(expected_triggers_min):
            self.send_idle_trigger(IDLE_TIME, commitTransaction=False)
            self.send_heartbeat(commitTransaction=False)
        self.flush_trigger()
        self.send_idle(3)
        trigger_handler_counters = self.board.trigger_handler.read_counters(('TRIGGER_SENT', 'TRIGGER_ECHOED', 'TRIGGER_GATED', 'TRIGGER_IGNORED'))
        alpide_control_counters = self.board.alpide_control.read_counters(('OPCODE', 'TRIGGER_SENT'))
        for value in ['OPCODE', 'TRIGGER_SENT']:
            self.assertGreater(alpide_control_counters[value], expected_triggers_min, f"Wrong counter {value} value {alpide_control_counters[value]} expected at least {expected_triggers_min}")
        self.assertGreater(trigger_handler_counters['TRIGGER_SENT'], expected_triggers_min, f"Wrong counter {'TRIGGER_SENT'} value {trigger_handler_counters['TRIGGER_SENT']} expected at least {expected_triggers_min}")
        for value in ['TRIGGER_IGNORED', 'TRIGGER_ECHOED', 'TRIGGER_GATED']:
            self.assertEqual(trigger_handler_counters[value], expected_ignored_triggers, f"Wrong counter {value} value {trigger_handler_counters[value]} expected {expected_ignored_triggers}")

    def test_send_hbr(self):
        """Sends a HBr, expect no triggers"""
        TESTS = 2
        expected_ignored_triggers = TESTS
        expected_triggers = 0
        IDLE_TIME = int(self.trigger_period*1.2)-1 # Set longer than trigger period
        self.send_heartbeat_reject(commitTransaction=False)
        self.send_idle_trigger(IDLE_TIME, commitTransaction=True) # delay a bit after HBr so last triggers to alpide control have arrived
        self.board.alpide_control.reset_counters(commitTransaction=False)
        self.board.trigger_handler.reset_counters(commitTransaction=False)
        self.sync()
        for _ in range(TESTS):
            self.send_idle_trigger(IDLE_TIME, commitTransaction=False)
            self.send_heartbeat_reject(commitTransaction=False)
        self.send_idle_trigger(IDLE_TIME, commitTransaction=False)
        self.flush_trigger()
        self.send_idle(3)
        trigger_handler_counters = self.board.trigger_handler.read_counters(('TRIGGER_SENT', 'TRIGGER_ECHOED', 'TRIGGER_GATED', 'TRIGGER_IGNORED'))
        alpide_control_counters = self.board.alpide_control.read_counters(('OPCODE', 'TRIGGER_SENT'))
        for value in ['OPCODE', 'TRIGGER_SENT']:
            self.assertEqual(alpide_control_counters[value], expected_triggers, f"Wrong counter {value} value {alpide_control_counters[value]} expected {expected_triggers}")
        for value in ['TRIGGER_SENT', 'TRIGGER_ECHOED', 'TRIGGER_GATED']:
            self.assertEqual(trigger_handler_counters[value], expected_triggers, f"Wrong counter {value} value {trigger_handler_counters[value]} expected {expected_triggers}")
        self.assertEqual(trigger_handler_counters['TRIGGER_IGNORED'], expected_ignored_triggers, f"Wrong counter {'TRIGGER_IGNORED'} value {trigger_handler_counters['TRIGGER_IGNORED']} expected {expected_ignored_triggers}")

    def test_internal_trigger(self):
        """Test that triggers are sent automatically in between heartbeats"""
        expected_triggers_min = 4
        expected_ignored_triggers = 0
        IDLE_TIME = self.trigger_period*(expected_triggers_min)
        self.board.alpide_control.reset_counters(commitTransaction=False)
        self.board.trigger_handler.reset_counters(commitTransaction=False)
        self.sync()
        self.send_idle_trigger(IDLE_TIME, commitTransaction=True)
        self.send_idle(3)
        trigger_handler_counters = self.board.trigger_handler.read_counters(('TRIGGER_SENT', 'TRIGGER_ECHOED', 'TRIGGER_GATED', 'TRIGGER_IGNORED'))
        alpide_control_counters = self.board.alpide_control.read_counters(('OPCODE', 'TRIGGER_SENT'))
        for value in ['OPCODE', 'TRIGGER_SENT']:
            self.assertGreater(alpide_control_counters[value], expected_triggers_min, f"Wrong counter {value} value {alpide_control_counters[value]} expected at least {expected_triggers_min}")
        for value in ['TRIGGER_IGNORED', 'TRIGGER_ECHOED', 'TRIGGER_GATED']:
            self.assertEqual(trigger_handler_counters[value], expected_ignored_triggers, f"Wrong counter {value} value {trigger_handler_counters[value]} expected {expected_ignored_triggers}")
        self.assertGreater(trigger_handler_counters['TRIGGER_SENT'], expected_triggers_min, f"Wrong counter {'TRIGGER_SENT'} value {trigger_handler_counters['TRIGGER_SENT']} expected at least {expected_triggers_min}")

    def test_internal_trigger_grant(self):
        """Test internal triggers sent while an internal trigger mask is active"""

        expected_triggers = 8
        masked_internal_triggers = 2
        expected_difference = masked_internal_triggers * 2  # 2 HB frames times 2 triggers masked
        IDLE_TIME = self.trigger_period * expected_triggers - 2

        # First stop internal triggers by sending EOC
        self.send_end_of_continuous(commitTransaction=True)

        # Send internal triggers for 2 HB frames (total of 2*8 = 16 triggers)
        self.board.trigger_handler.set_internal_trigger_grant(0xFFFFFFFFFFFF, commitTransaction=False)
        self.board.alpide_control.reset_counters(commitTransaction=False)
        self.board.trigger_handler.reset_counters(commitTransaction=True)
        self.sync()
        self.send_start_of_continuous(commitTransaction=False)
        self.send_idle_trigger(IDLE_TIME, commitTransaction=False)
        self.send_heartbeat(commitTransaction=False)
        self.send_idle_trigger(IDLE_TIME, commitTransaction=False)
        self.send_end_of_continuous(commitTransaction=False)
        self.flush_trigger()
        self.send_idle(3)
        th_counters_nomask = self.board.trigger_handler.read_counters(('TRIGGER_SENT'))

        # Send internal triggers for 2 HB frames with 2 internal triggers masked for each HB frame (total = 2*(8 - 2) = 12)
        self.board.trigger_handler.set_internal_trigger_grant(0xFFFFFFFFFFFA, commitTransaction=False)
        self.board.alpide_control.reset_counters(commitTransaction=False)
        self.board.trigger_handler.reset_counters(commitTransaction=False)
        self.sync()
        self.send_start_of_continuous(commitTransaction=False)
        self.send_idle_trigger(IDLE_TIME, commitTransaction=False)
        self.send_heartbeat(commitTransaction=False)
        self.send_idle_trigger(IDLE_TIME, commitTransaction=False)
        self.send_end_of_continuous(commitTransaction=False)
        self.flush_trigger()
        self.send_idle(3)
        th_counters_masked = self.board.trigger_handler.read_counters(('TRIGGER_SENT'))

        # Reset previous conndition and start again
        self.board.trigger_handler.set_internal_trigger_grant(0xFFFFFFFFFFFF, commitTransaction=True)
        self.send_start_of_continuous(commitTransaction=True)

        # Calculate difference and check
        actual_diff = th_counters_nomask['TRIGGER_SENT'] - th_counters_masked['TRIGGER_SENT']
        self.assertEqual(actual_diff, expected_difference,
                         f"Wrong difference f{actual_diff}. Expected f{th_counters_nomask['TRIGGER_SENT']} - f{th_counters_masked['TRIGGER_SENT']} = f{expected_difference}")

    def test_trigger_gating(self):
        """Test that triggers are gated when opcode gating is enabled"""
        expected_gated_triggers_min = 2
        expected_echoed_triggers = 2 # 1 PhT + 1 EOC
        expected_ignored_triggers = 0
        IDLE_TIME = self.trigger_period*expected_gated_triggers_min
        self.board.trigger_handler.set_opcode_gating(1, commitTransaction=False)
        self.board.alpide_control.reset_counters(commitTransaction=False)
        self.board.trigger_handler.reset_counters(commitTransaction=False)
        self.sync()
        self.send_trigger(commitTransaction=False)
        self.send_idle_trigger(IDLE_TIME, commitTransaction=True)
        self.send_end_of_continuous(commitTransaction=True) # Gating only ends on HB, prevents assertions firing
        self.board.trigger_handler.set_opcode_gating(0, commitTransaction=False)
        self.sync()
        self.send_idle(3)
        trigger_handler_counters = self.board.trigger_handler.read_counters(('TRIGGER_SENT', 'TRIGGER_ECHOED', 'TRIGGER_GATED', 'TRIGGER_IGNORED'))
        alpide_control_counters = self.board.alpide_control.read_counters(('OPCODE', 'TRIGGER_SENT'))
        for value in ['OPCODE', 'TRIGGER_SENT']:
            self.assertEqual(alpide_control_counters[value], expected_ignored_triggers, f"Wrong counter {value} value {alpide_control_counters[value]} expected at least {expected_ignored_triggers}")
        for value in ['TRIGGER_SENT', 'TRIGGER_IGNORED']:
            self.assertEqual(trigger_handler_counters[value], expected_ignored_triggers, f"Wrong counter {value} value {trigger_handler_counters[value]} expected {expected_ignored_triggers}")
        self.assertGreater(trigger_handler_counters['TRIGGER_GATED'], expected_gated_triggers_min, f"Wrong counter {'TRIGGER_GATED'} value {trigger_handler_counters['TRIGGER_GATED']} expected at least {expected_gated_triggers_min}")
        self.assertEqual(trigger_handler_counters['TRIGGER_ECHOED'], expected_echoed_triggers, f"Wrong counter {'TRIGGER_ECHOED'} value {trigger_handler_counters['TRIGGER_ECHOED']} expected {expected_echoed_triggers}")

    def test_internal_trigger_in_coincidence_with_pht_trigger(self):
        """Tests that trigger is not ignored when in coincidence"""
        if SIMULATION:
            TESTS = 10
        else:
            TESTS = 1000
        expected_sent_min = TESTS
        expected_ignored_triggers = 0
        expected_echoed_triggers = 1 # 1 EOC
        IDLE_TIME = self.trigger_period-1
        self.send_idle_trigger(1, commitTransaction=False)
        self.send_heartbeat_reject(commitTransaction=False) # Reject first to avoid triggers between reset and first HBa
        self.send_idle_trigger(IDLE_TIME, commitTransaction=True) # delay a bit after HBr so last triggers to alpide control have arrived
        self.send_idle(3)
        self.board.alpide_control.reset_counters(commitTransaction=False)
        self.board.trigger_handler.reset_counters(commitTransaction=False)
        self.sync()
        self.send_heartbeat(commitTransaction=False)
        for _ in range(TESTS):
            self.send_idle_trigger(IDLE_TIME, commitTransaction=False)
            self.send_trigger(commitTransaction=False)
        self.send_idle_trigger(IDLE_TIME, commitTransaction=False)
        self.send_end_of_continuous(commitTransaction=False)
        self.send_idle_trigger(IDLE_TIME*10, commitTransaction=False)
        self.flush_trigger()
        self.send_idle(3)
        trigger_handler_counters = self.board.trigger_handler.read_counters(('TRIGGER_SENT', 'TRIGGER_ECHOED', 'TRIGGER_GATED', 'TRIGGER_IGNORED'))
        alpide_control_counters = self.board.alpide_control.read_counters(('OPCODE', 'TRIGGER_SENT'))
        for value in ['OPCODE', 'TRIGGER_SENT']:
            self.assertGreater(alpide_control_counters[value], expected_sent_min, f"Wrong counter {value} value {alpide_control_counters[value]} expected at least {expected_sent_min}")
        for value in ['TRIGGER_GATED', 'TRIGGER_IGNORED']:
            self.assertEqual(trigger_handler_counters[value], expected_ignored_triggers, f"Wrong counter {value} value {trigger_handler_counters[value]} expected {expected_ignored_triggers}")
        self.assertGreater(trigger_handler_counters['TRIGGER_SENT'], expected_sent_min, f"Wrong counter {'TRIGGER_SENT'} value {trigger_handler_counters['TRIGGER_SENT']} expected at least {expected_sent_min}")
        self.assertEqual(trigger_handler_counters['TRIGGER_ECHOED'], expected_echoed_triggers, f"Wrong counter {'TRIGGER_ECHOED'} value {trigger_handler_counters['TRIGGER_ECHOED']} expected {expected_echoed_triggers}")


class TestGbtxFlowMonitor(TestcaseBase):
    """Class to verify the behaviour of the gbtx flow monitor wishbone slave"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        board = boardGlobal
        board.trigger_handler.enable(commitTransaction=False)
        board.trigger_handler.set_trigger_minimum_distance(1, commitTransaction=False)
        board.readout_master.set_ib_enabled_lanes(lanes=0, commitTransaction=False)
        board.readout_master.set_ob_enabled_lanes(lanes=0, commitTransaction=False)
        board.read(1,1) # Sync

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        board = boardGlobal
        board.trigger_handler.disable(commitTransaction=False)
        board.trigger_handler.set_trigger_minimum_distance(0xf0, commitTransaction=False)
        board.readout_master.set_ib_enabled_lanes(lanes=0x1ff, commitTransaction=False)
        board.readout_master.set_ob_enabled_lanes(lanes=0xfffffff, commitTransaction=True)

    def test_swt(self):
        """Check that the SWTs are counted correctly"""
        self.board.gbtx_flow_monitor.reset_all_counters(commitTransaction=True)
        self.send_idle(25)
        NR_READS = 10
        for _ in range(NR_READS):
            self.board.read(1,1,commitTransaction=False)
        self.board.read_all()

        # first latch counters
        self.board.gbtx_flow_monitor.latch_all_counters(commitTransaction=True)
        self.send_idle(25)

        # Now read
        counters = self.board.gbtx_flow_monitor.read_counters(counters=('DOWNLINK0_SWT', 'UPLINK0_SWT'), latch_first=False)

        expected_swt_downlink = NR_READS + 3 # 3 for latch, wait, reset-latch
        self.assertEqual(counters['DOWNLINK0_SWT'], expected_swt_downlink,
                         "SWT counter 'DOWNLINK0_SWT' is not correct")

        expected_swt_uplink = NR_READS
        self.assertEqual(counters['UPLINK0_SWT'], expected_swt_uplink,
                         "SWT counter 'UPLINK0_SWT' is not correct")

    @unittest.skipIf(type(comm0) is not simulation_if.Wb2GbtxComm, "Comm not Wb2GbtxComm -> Cannot test invalid SWT")
    def test_invalid_swt(self):
        """Checks that invalid swt is ignored and counted"""
        self.board.gbtx_flow_monitor.reset_all_counters(commitTransaction=True)
        self.send_idle(25)
        NR_INVALID_SWT = 100
        self.send_invalid_swt(NR_INVALID_SWT)

        # first latch counters
        self.board.gbtx_flow_monitor.latch_all_counters(commitTransaction=True)
        self.send_idle(25)

        # Now read
        counters = self.board.gbtx_flow_monitor.read_counters(counters=('DOWNLINK0_SWT_INV'), latch_first=False)

        self.assertEqual(counters['DOWNLINK0_SWT_INV'], NR_INVALID_SWT,
                         "SWT counter 'DOWNLINK0_SWT_INV' is not correct")

    def test_trigger_gbtx2(self):
        """Check that the GBTx2 triggers are counted correctly"""
        self.board.gbtx_flow_monitor.reset_all_counters(commitTransaction=False)
        self.sync()
        NR_TRIGGERS = 10
        IDLE_TIME = 2
        for _ in range(NR_TRIGGERS):
            self.send_trigger(commitTransaction=False)
            self.send_idle_trigger(value=IDLE_TIME, commitTransaction=False)
        self.send_idle_trigger(value=IDLE_TIME, commitTransaction=False)
        self.flush_trigger()
        counters = self.board.gbtx_flow_monitor.read_counters(counters=('DOWNLINK2_TRG'))
        self.assertEqual(counters['DOWNLINK2_TRG'],
                         NR_TRIGGERS,
                        f"TRG counter 'DOWNLINK2_TRG' is not correct")

    def test_sop_eop(self):
        """Check that the SOPs/EOPs are counted correctly"""
        self.board.gbtx_flow_monitor.reset_all_counters(commitTransaction=True)
        self.sync()
        self.send_start_of_triggered(commitTransaction=False)
        self.send_idle_trigger(commitTransaction=False)
        self.send_end_of_triggered(commitTransaction=True)
        self.send_idle(100)
        counters = self.board.gbtx_flow_monitor.read_counters(counters=('UPLINK0_SOP', 'UPLINK1_SOP', 'UPLINK2_SOP', 'UPLINK0_EOP', 'UPLINK1_EOP', 'UPLINK2_EOP'))

        expected_sop_eop = 2 + 2 # SOT open/close EOT open/close
        for value in ['UPLINK0_SOP', 'UPLINK1_SOP', 'UPLINK2_SOP', 'UPLINK0_EOP', 'UPLINK1_EOP', 'UPLINK2_EOP']:
            self.assertEqual(counters[value], expected_sop_eop, f"Counter {value} is not correct")

class TestWsIdentity(TestcaseBase):
    """Class to verify the behaviour of the identity wishbone slave"""

    def test_read_gitghash(self):
        #"""Reads the git hash"""
        githash = self.board.identity.get_git_hash()
        if SIMULATION:
            ghash_expected = GITHASH
            self.assertEqual(githash, ghash_expected,
                             "Returned value {0:08X} different than expected {1:08X}".format(ghash_expected,githash))

    def test_os(self):
        #"""Reads the OS compilation code"""
        build_os = self.board.identity.get_os()
        if SIMULATION:
            build_os_expected = 0xaffe
            self.assertEqual(build_os, build_os_expected,
                             "Returned value {0} different than expected {1}".format(build_os, build_os_expected))
        else:
            build_os_expected = list(range(3))
            self.assertIn(build_os, build_os_expected,
                          "Returned value {0} not in expected list {1}".format(build_os, build_os_expected))

    def test_dipswitch(self):
        #"""Reads the dipswitch value"""
        dipval = self.board.identity.get_dipswitch()
        if SIMULATION:
            dip_expected = 0x2AB
            self.assertEqual(dipval, dip_expected,
                             "Returned value {0} different than expected {1}".format(dipval, dip_expected))

    def test_dna(self):
        #"""Reads the DNA code"""
        dna = self.board.identity.get_dna()
        if SIMULATION:
            dna_expected = 0x76543210FEDCBA9876543210
            self.assertEqual(dna, dna_expected,
                             "Returned value {0} different than expected {1}".format(dna, dna_expected))

    def test_uptime(self):
        _, initial, final = self.board.identity.get_delta_time(wait=50,cnt_type=CounterType.UPTIME)
        self.assertGreater(final, initial, f"The uptime counter did not increment correctly, initial: 0x{initial:012x} final: 0x{final:012x}")

    def test_time_since_reset(self):
        _, initial, final = self.board.identity.get_delta_time(wait=50,cnt_type=CounterType.TIME_SINCE_RESET)
        self.assertGreater(final, initial, f"The time since reset counter did not increment correctly, initial: 0x{initial:012x} final: 0x{final:012x}")


@unittest.skipIf(len(GTH_LIST) == 0 and len(GPIO_LIST) == 0, "No Lanes active")
class TestDatapath_MonitoritorModules(TestcaseBase):
    def _test_dpmon_all(self,dpmon):
        dpmon.reset_all_counters(False)
        counters = dpmon.read_counters()
        self.assertEqual(len(counters), len(dpmon.lanes))
        for idx, _ in enumerate(dpmon.lanes):
            for counter in dpmon.counter_mapping:
                self.assertIn(counter,counters[idx])
                self.assertEqual(0,counters[idx][counter], f"counter nonzero, index{idx}")

    def _test_dpmon_lane(self,dpmon,lane):
        dpmon.reset_all_counters(False)
        counters = dpmon.read_counters(lanes=lane)
        self.assertEqual(len(counters),1)
        for counter in dpmon.counter_mapping:
            self.assertIn(counter,counters[0])
            self.assertEqual(0,counters[0][counter])

    @unittest.skipIf(len(GTH_LIST) == 0, "No GTH Lanes active")
    def test_dpmon_gth_all(self):
        self._test_dpmon_all(self.board.datapath_monitor_ib)

    @unittest.skipIf(len(GPIO_LIST) == 0, "No GPIO Lanes active")
    def test_dpmon_gpio_all(self):
        self._test_dpmon_all(self.board.datapath_monitor_ob)

    @unittest.skipIf(len(GTH_LIST) == 0, "No GTH Lanes active")
    def test_dpmon_gth_lane(self):
        self._test_dpmon_lane(self.board.datapath_monitor_ib,self.board.datapath_monitor_ib.lanes[0])

    @unittest.skipIf(len(GPIO_LIST) == 0, "No GPIO Lanes active")
    def test_dpmon_gpio_lane_first(self):
        self._test_dpmon_lane(self.board.datapath_monitor_ob,self.board.datapath_monitor_ob.lanes[0])

    @unittest.skipIf(len(GPIO_LIST) == 0, "No GPIO Lanes active")
    def test_dpmon_gpio_lane_last(self):
        self._test_dpmon_lane(self.board.datapath_monitor_ob,self.board.datapath_monitor_ob.lanes[-1])


class TestTransceiverFrontend(TestcaseBase):

    @classmethod
    def setUpClass(cls):
        if SIMULATION:
            sim_comm.disable_cable_length_randomization()

        board = boardGlobal
        board.trigger_handler.enable()

    @classmethod
    def tearDownClass(cls):
        if SIMULATION:
            sim_comm.enable_cable_length_randomization()
            sim_comm.set_dipswitches(feeid=CAN_NODE_ID) # reset dipswitches
        board = boardGlobal
        board.trigger_handler.disable()

    def setUp(self):
        super().setUp()
        self.logger = None
        self.chips = [Alpide(self.board, chipid=i) for i in SENSOR_LIST]
        self.board.initialize_gbtx0()
        self.chips[0].reset()
        self.board.gpio.enable_data(False)
        self.board.gth.enable_data(False)
        self.GBT_PACKER_TMR = False

        self.board.trigger_handler.disable_packer(packer=0,commitTransaction=False)
        self.board.trigger_handler.disable_packer(packer=1,commitTransaction=False)
        self.board.trigger_handler.disable_packer(packer=2,commitTransaction=False)
        self.board.flush()

    def tearDown(self):
        super(TestTransceiverFrontend, self).tearDown()

        self.board.trigger_handler.disable_packer(packer=0,commitTransaction=False)
        self.board.trigger_handler.disable_packer(packer=1,commitTransaction=False)
        self.board.trigger_handler.disable_packer(packer=2,commitTransaction=False)

        self.board.flush()

    def setup_chips(self, IBSerialLinkSpeed=2):
        self.__class__.setup_chips_static(self.chips, IBSerialLinkSpeed)

    @classmethod
    def setup_chips_static(cls, chips, IBSerialLinkSpeed=2):
        for chip in chips:
            chip.initialize(disable_manchester=1, grst=False, cfg_ob_module=False)
            chip.setreg_dtu_dacs(PLLDAC=8, DriverDAC=8, PreDAC=8)
            for pll_off_sig in [0, 1, 0]:
                chip.setreg_dtu_cfg(VcoDelayStages=1,
                                  PllBandwidthControl=1,
                                  PllOffSignal=pll_off_sig,
                                  SerPhase=8,
                                  PLLReset=0,
                                  LoadENStatus=0)

            chip.board.write_chip_opcode(Opcode.RORST)
            chip.setreg_fromu_cfg_1(
                MEBMask=0,
                EnStrobeGeneration=0,
                EnBusyMonitoring=1,
                PulseMode=0,
                EnPulse2Strobe=0,
                EnRotatePulseLines=0,
                TriggerDelay=0)

            chip.setreg_fromu_cfg_3(FrameGap=0x800)
            chip.setreg_fromu_pulsing_2(PulseDuration=0xFF)
            chip.setreg_fromu_pulsing1(PulseDelay=0xF)

            chip.mask_all_pixels()
            chip.pulse_all_pixels_disable()
            chip.region_control_register_mask_all_double_columns(broadcast=True)

            chip.setreg_mode_ctrl(ChipModeSelector=1,
                                EnClustering=1,
                                MatrixROSpeed=1,
                                IBSerialLinkSpeed=IBSerialLinkSpeed,
                                EnSkewGlobalSignals=1,
                                EnSkewStartReadout=1,
                                EnReadoutClockGating=1,
                                EnReadoutFromCMU=0)


    def check_event_readout(self,nr_events, nr_noevent_triggers, lanes, cru):
        with self.assertLogs(logging.getLogger("events"), level=logging.INFO) as cm:
            event_count, errors = events.check_event_readout_new(cru,nr_events, nr_events + nr_noevent_triggers,
                                                             lanes,True,None)
            warnings = []
            for rec in cm.records:
                logging.getLogger("check_event_readout").log(rec.levelno,rec.getMessage())
                warnings.append(rec.levelno > logging.INFO)
            self.logger.info("check_event_readout: processed {} events with {} errors". format(event_count, errors))
            self.assertFalse(all(warnings),"Event readout logged Warning or Error")
            self.assertEqual(0,errors, "Errors in event stream")
            return event_count


@unittest.skipIf(len(GPIO_LIST) == 0, "No GPIO Lanes active")
class TestTransceiverGpioFrontend(TestTransceiverFrontend):

    @classmethod
    def setUpClass(cls):
        super(TestTransceiverGpioFrontend, cls).setUpClass()
        board = boardGlobal
        board.gpio.enable_data(False)
        connector_lut = board.get_chip2connector_lut()
        board.enable_chip2connector_lut(False)
        board.set_chip2connector_lut(GPIO_CONNECTOR_LUT)
        chips = [Alpide(boardGlobal, chipid=i) for i in SENSOR_LIST]
        cls.setup_chips_static(chips,2)
        for chip in chips:
            chip.propagate_prbs(PrbsRate=1)
        lanes_en = 0
        for lane in GPIO_LIST:
            lanes_en |= 1<<lane
        board.readout_master.set_ob_enabled_lanes(lanes_en)

        board.gpio.enable_prbs(enable=True, commitTransaction=True)
        board.gpio.reset_prbs_counter()
        if SIMULATION:
            cls.gpio_idelays = {i : 305 for i in GPIO_LIST}
        else:
            cls.gpio_idelays = board.gpio.subset(GPIO_LIST).scan_idelays(10,0.1,True,verbose=True)
        board.enable_chip2connector_lut(False)
        board.set_chip2connector_lut(connector_lut)
        if SIMULATION:
            L5_42 = 0xAA # set dipswitches for OB stave
            sim_comm.set_dipswitches(feeid=L5_42)

    @classmethod
    def tearDownClass(cls):
        super(TestTransceiverGpioFrontend, cls).tearDownClass()

    def setUp(self):
        super(TestTransceiverGpioFrontend, self).setUp()
        self.logger = logging.getLogger("TestTransceiverGpioFrontend")

        self.connector_lut = self.board.get_chip2connector_lut()
        self.board.enable_chip2connector_lut(False)
        self.board.set_chip2connector_lut(GPIO_CONNECTOR_LUT)

        lanes_en = self.board.readout_master.get_ob_enabled_lanes()
        self.board.readout_master.set_ob_enabled_lanes(0,commitTransaction=False)
        self.board.readout_master.set_ob_enabled_lanes(lanes_en,commitTransaction=False)

        self.board.gpio.enable_data(False)
        if USE_ALL_UPLINKS:
            ls_0, ls_1= chunk_list(GPIO_LIST, num=2)
            ls_2 = []
            assert len(ls_0) > 0
            assert len(ls_1) > 0
            assert len(ls_2) == 0
            self.board.trigger_handler.enable_packer(packer=0, commitTransaction=False)
            self.board.trigger_handler.enable_packer(packer=1, commitTransaction=False)
            self.board.trigger_handler.disable_packer(packer=2, commitTransaction=False)
        else:
            # only re-enable non default from setup
            self.board.trigger_handler.enable_packer(packer=0, commitTransaction=False)
        self.board.flush()

        for tr,idelay in self.__class__.gpio_idelays.items():
            self.board.gpio.subset([tr]).load_idelay(idelay)

    def tearDown(self):
        super(TestTransceiverGpioFrontend, self).tearDown()
        self.board.gpio.enable_alignment(enable=False,commitTransaction=True)
        self.board.enable_chip2connector_lut(False)
        self.board.set_chip2connector_lut(self.connector_lut)

    def test_idelay(self):
        self.setup_chips(IBSerialLinkSpeed=0)
        self.board.gpio.load_idelay(0xFF)
        self.board.wait(1000)
        self.board.gpio.load_idelay(0x1FF)
        self.board.wait(1000)
        # test setting of only partial transceivers
        transceivers_temp = self.board.gpio.get_transceivers()[:]
        self.board.gpio.set_transceivers(transceivers_temp[::2])
        self.board.gpio.load_idelay(0xFF)
        self.board.wait(1000)
        self.board.gpio.set_transceivers(transceivers_temp[1::2])
        self.board.gpio.load_idelay(0x80)
        self.board.wait(1000)
        self.board.gpio.set_transceivers(transceivers_temp)
        self.board.gpio.load_idelay(0x00)
        self.board.wait(1000)
        self.board.read(1,1)

    def test_data(self):
        self.setup_chips(IBSerialLinkSpeed=0)
        for chip in self.chips:
            chip.propagate_data()

        self.board.gpio.initialize()

        aligned = self.board.gpio.align_transceivers()
        self.assertTrue(aligned, "GPIO module could not align to all modules: {0}".format(self.board.gpio.is_aligned()))

        # discard old data
        self.assertTrue(self.cru0.comm.discardall_dp2(20), "Could not discard data from dataport")
        if USE_ALL_UPLINKS:
            self.assertTrue(self.cru1.comm.discardall_dp2(20), "Could not discard data from dataport cru1")

        NR_TRIGGERS = 3
        NR_CHANNELS = len(GPIO_LIST)

        events_per_trigger = {i:0 for i in GPIO_LIST}
        for lane in GPIO_LIST:
            events_per_trigger[lane] = GPIO_SENSORS_PER_LANE[lane]

        NR_EVENTS = {lane: NR_TRIGGERS * ept for lane,ept in events_per_trigger.items()}

        self.board.datapath_monitor_ob.reset_all_counters(commitTransaction=False)
        self.board.gbt_packer.reset_all_counters(commitTransaction=False)
        self.board.alpide_control.reset_counters(commitTransaction=False)
        self.board.wait(1000,commitTransaction=False)
        counters = self.board.datapath_monitor_ob.read_all_counters()
        for i in range(NR_CHANNELS):
            for name,val in counters[i].items():
                self.assertEqual(val,0,"Before Trigger. Lane {0}, Counter {1}, Value {2} not zero".format(GPIO_LIST[i],name,val))

        self.board.gpio.enable_data(True)

        trigger_min_dist = self.board.trigger_handler.get_trigger_minimum_distance()
        self.board.trigger_handler.set_trigger_minimum_distance(1)
        self.sync()
        self.send_start_of_triggered(commitTransaction=False)
        IDLE_TIME = 1000
        for i in range(NR_TRIGGERS):
            self.send_trigger(commitTransaction=False)
            self.send_idle_trigger(IDLE_TIME, commitTransaction=False)
        self.send_end_of_triggered(commitTransaction=False)
        self.sync()
        self.board.trigger_handler.set_trigger_minimum_distance(trigger_min_dist)

        alpide_control_counters = self.board.alpide_control.read_counters('TRIGGER_SENT')
        self.assertEqual(
            alpide_control_counters['TRIGGER_SENT'], NR_TRIGGERS, "Not all Triggers sent: {0}/{1}".format(alpide_control_counters['TRIGGER_SENT'], NR_TRIGGERS))

        # check Event counter

        events_received = False
        retries = 0

        while not events_received and retries < 20:
            self.board.wait(1000, commitTransaction=False)
            event_counters = self.board.datapath_monitor_ob.read_counter(counter="LANE_FIFO_STOP")
            if not isinstance(event_counters,collections.abc.Iterable):
                event_counters = [event_counters]
            events_received = all(
                [trig == NR_EVENTS[lane] for lane,trig in zip(GPIO_LIST,event_counters)])
            retries += 1

        counters = self.board.datapath_monitor_ob.read_all_counters()
        gbt0_counters = self.board._gbt_packer_0_monitor.read_counters()
        if USE_ALL_UPLINKS:
            gbt1_counters = self.board._gbt_packer_1_monitor.read_counters()

        zero_counters = [
            # LANE
            "u8B10B_OOT",
            "u8B10B_OOT_FATAL",
            "u8B10B_OOT_TOLERATED",
            "PROTOCOL_ERROR",
            "BUSY_EVENT",
            "BUSY_VIOLATION",
            "BCID_MISMATCH",
            "DETECTOR_TIMEOUT",
            "RATE_OCCUPANCY_LIMIT",
            "LANE_FIFO_OVERFLOW",
            "LANE_FIFO_ERROR",
            "LANE_TIMEOUT",
            # GPIO
            "8b10b_OOT_ERROR",
        ]

        for i in range(NR_CHANNELS):
            for cntr_name in zero_counters:
                msg = "After Trigger: Lane {0}, Counter {1} is Off. All: {2}"
                self.assertEqual(counters[i][cntr_name],0, msg.format(i,cntr_name,pprint.pformat(counters)))

           # Start/Stop counters only show upper 16 bit of 24 bit counter, cut nr_triggers
            self.assertEqual(counters[i]["LANE_FIFO_START"],NR_TRIGGERS,
                             msg.format(i,"LANE_FIFO_START",pprint.pformat(counters)))
            self.assertEqual(counters[i]["LANE_FIFO_STOP"],NR_TRIGGERS,
                             msg.format(i,"LANE_FIFO_STOP",pprint.pformat(counters)))
            self.assertEqual(event_counters[i], NR_TRIGGERS, "Lane {0}, Not all Events received".format(GPIO_LIST[i]))

        EXPECTED_TRIGGERS = NR_TRIGGERS+2 # NR_TRIGGERS + SOT + EOT
        EXPECTED_xOP = 4 # SOT (1 HBF => 2 PACKETS), EOT (1 HBF => 2 PACKETS)
        EXPECTED_PACKET_DONE = NR_TRIGGERS # NR_TRIGGERS producing data
        EXPECTED_PACKET_EMPTY = 0 # All triggers sent expect data

        self.assertEqual(gbt0_counters['TRIGGER_READ'],EXPECTED_TRIGGERS,"GBT0 Packer, incorrect number of Triggers read")
        self.assertEqual(gbt0_counters['SOP_SENT'],EXPECTED_xOP,"GBT0 Packer, incorrect number of SOP sent")
        self.assertEqual(gbt0_counters['EOP_SENT'],EXPECTED_xOP,"GBT0 Packer, incorrect number of EOP sent")
        self.assertEqual(gbt0_counters['PACKET_DONE'],EXPECTED_PACKET_DONE,"GBT0 Packer, incorrect number of PACKET_DONE sent")
        self.assertEqual(gbt0_counters['PACKET_EMPTY'],EXPECTED_PACKET_EMPTY,"GBT0 Packer, incorrect number of PACKET_EMPTY sent")

        self.assertEqual(gbt0_counters['PACKET_TIMEOUT'],0,"GBT0 Packer, PACKET_TIMEOUT Non-Zero")
        self.assertEqual(gbt0_counters['FIFO_FULL'],0,"GBT0 Packer, FIFO_FULL Non-Zero")
        self.assertEqual(gbt0_counters['FIFO_OVERFLOW'],0,"GBT0 Packer, FIFO_OVERFLOW Non-Zero")

        if USE_ALL_UPLINKS:
            self.assertEqual(gbt1_counters['TRIGGER_READ'],EXPECTED_TRIGGERS,"GBT1 Packer, incorrect number of Triggers read")
            self.assertEqual(gbt1_counters['SOP_SENT'],EXPECTED_xOP,"GBT1 Packer, incorrect number of SOP sent")
            self.assertEqual(gbt1_counters['EOP_SENT'],EXPECTED_xOP,"GBT1 Packer, incorrect number of EOP sent")
            self.assertEqual(gbt1_counters['PACKET_DONE'],EXPECTED_PACKET_DONE,"GBT1 Packer, incorrect number of PACKET_DONE sent")
            self.assertEqual(gbt1_counters['PACKET_EMPTY'],EXPECTED_PACKET_EMPTY,"GBT1 Packer, incorrect number of PACKET_EMPTY sent")

            self.assertEqual(gbt1_counters['PACKET_TIMEOUT'],0,"GBT1 Packer, PACKET_TIMEOUT Non-Zero")
            self.assertEqual(gbt1_counters['FIFO_FULL'],0,"GBT1 Packer, FIFO_FULL Non-Zero")
            self.assertEqual(gbt1_counters['FIFO_OVERFLOW'],0,"GBT1 Packer, FIFO_OVERFLOW Non-Zero")

        check_list = [i+int(i/7)+0x40 for i in GPIO_LIST]
        # TODO: To be updated, see #289
        # event_count = self.check_event_readout(nr_events=NR_TRIGGERS, nr_noevent_triggers=2, lanes=check_list, cru=self.cru0)
        # if USE_ALL_UPLINKS:
        #     event_count += self.check_event_readout(nr_events=NR_TRIGGERS, nr_noevent_triggers=2, lanes=check_list, cru=self.cru1)
        # all_expected_events = sum(events_per_trigger.values()) * NR_TRIGGERS
        # self.assertEqual(event_count, all_expected_events, "Total Event count mismatch")

        # Reset counters, check if still zero
        zero_counters = [
            # LANE
            "u8B10B_OOT",
            "u8B10B_OOT_FATAL",
            "u8B10B_OOT_TOLERATED",
            "PROTOCOL_ERROR",
            "BUSY_EVENT",
            "BUSY_VIOLATION",
            "DATA_OVERRUN",
            "BCID_MISMATCH",
            "DETECTOR_TIMEOUT",
            "RATE_OCCUPANCY_LIMIT",
            "LANE_FIFO_OVERFLOW",
            "LANE_FIFO_START",
            "LANE_FIFO_STOP",
            "LANE_FIFO_ERROR",
            "LANE_TIMEOUT",
            # GPIO
            "8b10b_OOT_ERROR",
        ]

        self.board.datapath_monitor_ob.reset_all_counters()
        self.board.wait(1000)
        counters = self.board.datapath_monitor_ob.read_all_counters()
        for i in range(NR_CHANNELS):
            for cntr_name in zero_counters:
                msg = f"At end, after reset: Lane {i}, Counter {cntr_name} not zero. All: {pprint.pformat(counters)}"
                self.assertEqual(counters[i][cntr_name],0, msg)

    def test_prbs400(self):
        self.setup_chips(IBSerialLinkSpeed=3)
        for ch in self.chips:
            ch.propagate_prbs(PrbsRate=1)

        self.board.wait(500, commitTransaction=False)
        self.sync()

        self.board.gpio.initialize()

        self.board.gpio.enable_prbs(enable=True, commitTransaction=True)
        self.board.gpio.reset_prbs_counter()

        # Read counters
        self.board.wait(5000)

        prbs_errors = self.board.gpio.read_prbs_counter()
        print(prbs_errors)
        for cnt, link in zip(prbs_errors, self.board.gpio.transceivers):
            self.assertEqual(0, cnt, "PRBS Error on Link {0}".format(link))

        # Set chip back to normal mode -> expect errors
        for ch in self.chips:
            ch.propagate_data(commitTransaction=False)
        self.board.wait(1000, commitTransaction=True)
        # back to PRBS sending mode
        for ch in self.chips:
            ch.propagate_prbs(PrbsRate=1, commitTransaction=True)

        prbs_errors = self.board.gpio.read_prbs_counter(self)
        for cnt, link in zip(prbs_errors, self.board.gpio.transceivers):
            self.assertNotEqual(
                0, cnt, "No PRBS Error on Link {0}. Errors expected".format(link))

        # check Counter reset operation

        self.board.gpio.reset_prbs_counter(commitTransaction=True)
        self.board.wait(1000, commitTransaction=True)

        prbs_errors = self.board.gpio.read_prbs_counter()
        for cnt, link in zip(prbs_errors, self.board.gpio.transceivers):
            self.assertEqual(0, cnt, "PRBS Error on Link {0}".format(link))


@unittest.skipIf(len(GTH_LIST) == 0, "No GTH Lanes active")
class TestTransceiverGthFrontend(TestTransceiverFrontend):
    @classmethod
    def setUpClass(cls):
        super(TestTransceiverGthFrontend, cls).setUpClass()

        board = boardGlobal
        lanes_en = 0
        for lane in GTH_LIST:
            lanes_en |= 1<<lane
        board.readout_master.set_ib_enabled_lanes(lanes_en)

        if SIMULATION:
            L0_12 = 0x0C # set dipswitches for IB stave
            sim_comm.set_dipswitches(feeid=L0_12)

    @classmethod
    def tearDownClass(cls):
        super(TestTransceiverGthFrontend, cls).tearDownClass()

    def test_eyescan(self):
        transceivers = list(self.board.gth.get_transceivers())
        self.board.gth.set_transceivers([0])
        eyescan = ru_eyescan.EyeScanGth(self.board.gth)

        eyescan.initialize()
        self.board.gth.set_transceivers(transceivers)

    def setUp(self):
        super(TestTransceiverGthFrontend, self).setUp()
        self.logger = logging.getLogger("TestTransceiverFrontend")

        self.board.enable_chip2connector_lut(False)
        lanes_en = self.board.readout_master.get_ib_enabled_lanes()
        self.board.readout_master.set_ib_enabled_lanes(0,commitTransaction=False)
        self.board.readout_master.set_ib_enabled_lanes(lanes_en,commitTransaction=False)

        self.board.gth.enable_data(enable=False,commitTransaction=True)
        self.board.gth.enable_alignment(enable=False,commitTransaction=True)
        if USE_ALL_UPLINKS:
            ls_0, ls_1, ls_2 = chunk_list(GTH_LIST)
            assert len(ls_0) > 0
            assert len(ls_1) > 0
            assert len(ls_2) > 0
            self.board.trigger_handler.enable_packer(packer=0, commitTransaction=False)
            self.board.trigger_handler.enable_packer(packer=1, commitTransaction=False)
            self.board.trigger_handler.enable_packer(packer=2, commitTransaction=False)
        else:
            self.board.trigger_handler.enable_packer(packer=0, commitTransaction=False)
        self.board.flush()
        self.connector_lut = self.board.get_chip2connector_lut()
        self.board.enable_chip2connector_lut(False)
        self.board.set_chip2connector_lut(GTH_CONNECTOR_LUT)

    def tearDown(self):
        super(TestTransceiverGthFrontend, self).tearDown()
        self.board.gth.enable_data(enable=False,commitTransaction=True)
        self.board.gth.enable_alignment(enable=False,commitTransaction=True)

        self.board.enable_chip2connector_lut(False)
        self.board.set_chip2connector_lut(self.connector_lut)

    def test_drp(self):
        """Test DRP interface"""
        ES_SDATA_MASK = (0x4D, 0x4C, 0x4B, 0x4A, 0x49)
        transceivers = list(self.board.gth.get_transceivers())
        data = 42
        self.setup_chips()
        initialized = self.board.gth.initialize()
        self.assertTrue(initialized, "Reset_done not received from GTH module")

        for tr in transceivers:
            self.board.gth.set_transceivers([tr])
            for addr in ES_SDATA_MASK:
                self.board.gth.write_drp(addr, data + addr)
            for addr in ES_SDATA_MASK:
                rb = self.board.gth.read_drp(addr)
                self.assertEqual(
                    rb, data + addr, "DRP Write/Read mismatch on Transceiver {0}".format(tr))
        self.board.gth.set_transceivers(transceivers)

    def test_data(self):
        NR_TRIGGERS=3
        NR_CHANNELS = len(self.board.gth.get_transceivers())
        counters, gbt0_counters, gbt1_counters, gbt2_counters = self._test_data_initial(nr_triggers=NR_TRIGGERS, nr_channels=NR_CHANNELS)
        for i in range(NR_CHANNELS):
            msg = f"After Trigger: Lane {0}, Counter {1} is off. All: {pprint.pformat(2)}"
            self.assertEqual(counters[i]["LANE_FIFO_START"],NR_TRIGGERS,
                             msg.format(i,"LANE_FIFO_START",pprint.pformat(counters)))
            self.assertEqual(counters[i]["LANE_FIFO_STOP"],NR_TRIGGERS,
                             msg.format(i,"LANE_FIFO_STOP",pprint.pformat(counters)))

        EXPECTED_TRIGGERS = NR_TRIGGERS+2 # NR_TRIGGERS + SOT + EOT
        EXPECTED_xOP = 4 # SOT (1 HBF => 2 PACKETS), EOT (1 HBF => 2 PACKETS)
        EXPECTED_PACKET_DONE = NR_TRIGGERS # NR_TRIGGERS producing data
        EXPECTED_PACKET_EMPTY = 0 # All triggers sent expect data

        self.assertEqual(gbt0_counters['TRIGGER_READ'],EXPECTED_TRIGGERS,"GBT0 Packer, incorrect number of Triggers read")
        self.assertEqual(gbt0_counters['SOP_SENT'],EXPECTED_xOP,"GBT0 Packer, incorrect number of SOP sent")
        self.assertEqual(gbt0_counters['EOP_SENT'],EXPECTED_xOP,"GBT0 Packer, incorrect number of EOP sent")
        self.assertEqual(gbt0_counters['PACKET_DONE'],EXPECTED_PACKET_DONE,"GBT0 Packer, incorrect number of PACKET_DONE sent")
        self.assertEqual(gbt0_counters['PACKET_EMPTY'],EXPECTED_PACKET_EMPTY,"GBT0 Packer, incorrect number of PACKET_EMPTY sent")

        self.assertEqual(gbt0_counters['PACKET_TIMEOUT'],0,"GBT0 Packer, PACKET_TIMEOUT Non-Zero")
        self.assertEqual(gbt0_counters['FIFO_FULL'],0,"GBT0 Packer, FIFO_FULL Non-Zero")
        self.assertEqual(gbt0_counters['FIFO_OVERFLOW'],0,"GBT0 Packer, FIFO_OVERFLOW Non-Zero")

        if USE_ALL_UPLINKS:
            self.assertEqual(gbt1_counters['TRIGGER_READ'],EXPECTED_TRIGGERS,"GBT1 Packer, incorrect number of Triggers read")
            self.assertEqual(gbt1_counters['SOP_SENT'],EXPECTED_xOP,"GBT1 Packer, incorrect number of SOP sent")
            self.assertEqual(gbt1_counters['EOP_SENT'],EXPECTED_xOP,"GBT1 Packer, incorrect number of EOP sent")
            self.assertEqual(gbt1_counters['PACKET_DONE'],EXPECTED_PACKET_DONE,"GBT1 Packer, incorrect number of PACKET_DONE sent")
            self.assertEqual(gbt1_counters['PACKET_EMPTY'],EXPECTED_PACKET_EMPTY,"GBT1 Packer, incorrect number of PACKET_EMPTY sent")

            self.assertEqual(gbt1_counters['PACKET_TIMEOUT'],0,"GBT1 Packer, PACKET_TIMEOUT Non-Zero")
            self.assertEqual(gbt1_counters['FIFO_FULL'],0,"GBT1 Packer, FIFO_FULL Non-Zero")
            self.assertEqual(gbt1_counters['FIFO_OVERFLOW'],0,"GBT1 Packer, FIFO_OVERFLOW Non-Zero")

            self.assertEqual(gbt2_counters['TRIGGER_READ'],EXPECTED_TRIGGERS,"GBT2 Packer, incorrect number of Triggers read")
            self.assertEqual(gbt2_counters['SOP_SENT'],EXPECTED_xOP,"GBT2 Packer, incorrect number of SOP sent")
            self.assertEqual(gbt2_counters['EOP_SENT'],EXPECTED_xOP,"GBT2 Packer, incorrect number of EOP sent")
            self.assertEqual(gbt2_counters['PACKET_DONE'],EXPECTED_PACKET_DONE,"GBT2 Packer, incorrect number of PACKET_DONE sent")
            self.assertEqual(gbt2_counters['PACKET_EMPTY'],EXPECTED_PACKET_EMPTY,"GBT2 Packer, incorrect number of PACKET_EMPTY sent")

            self.assertEqual(gbt2_counters['PACKET_TIMEOUT'],0,"GBT2 Packer, PACKET_TIMEOUT Non-Zero")
            self.assertEqual(gbt2_counters['FIFO_FULL'],0,"GBT2 Packer, FIFO_FULL Non-Zero")
            self.assertEqual(gbt2_counters['FIFO_OVERFLOW'],0,"GBT2 Packer, FIFO_OVERFLOW Non-Zero")

        # TODO: To be updated, see #289
        # event_count = self.check_event_readout(nr_events=NR_TRIGGERS, nr_noevent_triggers=2, lanes=list(range(0x20, 0x20 + NR_CHANNELS)), cru=self.cru0)
        # if USE_ALL_UPLINKS:
        #     event_count += self.check_event_readout(nr_events=NR_TRIGGERS, nr_noevent_triggers=2, lanes=list(range(0x20, 0x20 + NR_CHANNELS)), cru=self.cru1)
        #     event_count += self.check_event_readout(nr_events=NR_TRIGGERS, nr_noevent_triggers=2, lanes=list(range(0x20, 0x20 + NR_CHANNELS)), cru=self.cru2)
        # all_expected_events = NR_TRIGGERS * NR_CHANNELS
        # self.assertEqual(event_count, all_expected_events, "Total Event count mismatch")

        # Reset counters, check if still zero
        zero_counters = [
            # LANE
            "u8B10B_OOT",
            "u8B10B_OOT_FATAL",
            "u8B10B_OOT_TOLERATED",
            "PROTOCOL_ERROR",
            "BUSY_EVENT",
            "BUSY_VIOLATION",
            "DATA_OVERRUN",
            "BCID_MISMATCH",
            "DETECTOR_TIMEOUT",
            "RATE_OCCUPANCY_LIMIT",
            "LANE_FIFO_OVERFLOW",
            "LANE_FIFO_START",
            "LANE_FIFO_STOP",
            "LANE_FIFO_ERROR",
            "LANE_TIMEOUT",
            # GTH
            "CPLL_LOCK_LOSS",
            "CDR_LOCK_LOSS",
            "ALIGNED_LOSS",
            "REALIGNED",
            "8b10b_OOT_ERROR",
        ]
        self.board.datapath_monitor_ib.reset_all_counters()
        self.board.wait(1000)
        counters = self.board.datapath_monitor_ib.read_all_counters()
        for i in range(NR_CHANNELS):
            for cntr_name in zero_counters:
                msg = f"At end, after reset: Lane {i}, Counter {cntr_name} not zero. All: {pprint.pformat(counters)}"
                self.assertEqual(counters[i][cntr_name],0, msg)


    def _test_oot(self,oot_ndisp=False):
        """Used in out of table test and issue 207,
        The parameter oot_ndisp selects the pattern to be transmitted.
        If True  then a pattern triggering OOT error will be transmitted.
        If False then a pattern triggering disparity error will be transmitted."""
        self.setup_chips()
        for ch in self.chips:
            ch.propagate_comma()

        initialized = self.board.gth.initialize()
        self.assertTrue(initialized, "Reset_done not received from GTH module")
        self.board.wait(500)
        locked = self.board.gth.is_cdr_locked()
        self.assertNotIn(False, locked, "Not all CDR circuits are locked")
        aligned = self.board.gth.align_transceivers()
        self.assertTrue(aligned, "GTH module could not align to all modules")

        if oot_ndisp:
            pattern = 0b1111111111_1111111111_1111111111 # pattern not in UG576 v1.6, Table A-1 and A-2: i.e OOT
        else:
            pattern = 0b1010101010_1010101010_1010101010 # pattern not in UG576 v1.6, Table A-1 and A-2. This pattern causes disparity errors
        for ch in self.chips:
            ch.propagate_pattern(pattern)
        self.board.datapath_monitor_ib.reset_all_counters()
        self.board.gth.enable_data()
        self.board.wait(1000)
        self.board.gth.enable_data(enable=False)

    def test_8b10b_out_of_table(self):
        NR_CHANNELS = len(self.board.gth.get_transceivers())
        self._test_oot(oot_ndisp=True)
        counters = self.board.datapath_monitor_ib.read_counters(counters=['8b10b_OOT_ERROR'])
        for i in range(NR_CHANNELS):
            for name,val in counters[i].items():
                self.assertGreater(val,0,f"Lane {i}, Counter {name}, Value {val} is zero")

    @unittest.skip("See #293: fails when wiring trigger to lanes, debug and reactivate")
    def test_issue_207(self):
        """Tests issue 207 by running test_oot (introducing junk in datapath) and then the first part of the test_data"""
        self._test_oot()
        self.setUp()
        NR_TRIGGERS=1
        NR_CHANNELS = len(self.board.gth.get_transceivers())
        self._test_data_initial(nr_triggers=NR_TRIGGERS, nr_channels=NR_CHANNELS)

    def test_gth_initialize(self):
        self.setup_and_initialize()

    def setup_and_initialize(self):
        """Initial GTH and ALPIDE setup for multiple tests"""
        self.setup_chips()

        initialized = self.board.gth.initialize()
        self.assertTrue(initialized, "Reset_done not received from GTH module")

        self.board.wait(500)

        locked = self.board.gth.is_cdr_locked()
        self.assertNotIn(False, locked, "Not all CDR circuits are locked")

        aligned = self.board.gth.align_transceivers()
        self.assertTrue(aligned, "GTH module could not align to all modules: {0}".format(self.board.gth.is_aligned()))

        # discard old data
        self.assertTrue(self.cru0.comm.discardall_dp2(20), "Could not discard data from dataport cru0")
        if USE_ALL_UPLINKS:
            self.assertTrue(self.cru1.comm.discardall_dp2(20), "Could not discard data from dataport cru1")
            self.assertTrue(self.cru2.comm.discardall_dp2(20), "Could not discard data from dataport cru2")

        # disable alignment
        self.board.gth.enable_alignment(False)
        self.board.gth.enable_data(True)

    def _test_data_initial(self, nr_triggers, nr_channels):
        """Subtest for testing test_data and test_issue_207"""
        self.setup_and_initialize()

        NR_TRIGGERS = nr_triggers
        NR_CHANNELS = nr_channels

        self.board.datapath_monitor_ib.reset_all_counters(commitTransaction=False)
        self.board.gbt_packer.reset_all_counters(commitTransaction=False)
        self.board.alpide_control.reset_counters(commitTransaction=False)
        self.board.wait(1000,commitTransaction=False)
        counters = self.board.datapath_monitor_ib.read_all_counters()
        zero_counters = [
            # LANE
            "u8B10B_OOT",
            "u8B10B_OOT_FATAL",
            "u8B10B_OOT_TOLERATED",
            "PROTOCOL_ERROR",
            "BUSY_EVENT",
            "BUSY_VIOLATION",
            "DATA_OVERRUN",
            "BCID_MISMATCH",
            "DETECTOR_TIMEOUT",
            "RATE_OCCUPANCY_LIMIT",
            "LANE_FIFO_OVERFLOW",
            "LANE_FIFO_START",
            "LANE_FIFO_STOP",
            "LANE_FIFO_ERROR",
            "LANE_TIMEOUT",
            # GTH
            "CPLL_LOCK_LOSS",
            "CDR_LOCK_LOSS",
            "ALIGNED_LOSS",
            "REALIGNED",
        ]
        for i in range(NR_CHANNELS):
            for cntr_name in zero_counters:
                msg = f"After Trigger: Lane {i}, Counter {cntr_name} not 0. All: {pprint.pformat(counters)}"
                self.assertEqual(counters[i][cntr_name],0, msg)

        self.board.gth.enable_data(True)

        trigger_min_dist = self.board.trigger_handler.get_trigger_minimum_distance()
        self.board.trigger_handler.set_trigger_minimum_distance(1)
        self.sync()

        self.send_start_of_triggered(commitTransaction=False)
        IDLE_TIME = 1000
        for i in range(NR_TRIGGERS):
            self.send_trigger(commitTransaction=False)
            self.send_idle_trigger(IDLE_TIME, commitTransaction=False)
        self.send_end_of_triggered(commitTransaction=False)
        self.sync()

        self.board.trigger_handler.set_trigger_minimum_distance(trigger_min_dist)

        alpide_control_counters = self.board.alpide_control.read_counters('TRIGGER_SENT')
        self.assertEqual(
            alpide_control_counters['TRIGGER_SENT'], NR_TRIGGERS, f"Not all Triggers sent: {alpide_control_counters['TRIGGER_SENT']}/{NR_TRIGGERS}")

        # check Event counter
        events_received = False
        retries = 0

        while not events_received and retries < 10:
            self.board.wait(1000, commitTransaction=False)
            event_counters = self.board.datapath_monitor_ib.read_counter(range(NR_CHANNELS), "LANE_FIFO_STOP")
            if not isinstance(event_counters,collections.abc.Iterable):
                event_counters = [event_counters]
            events_received = all(
                [trig == NR_TRIGGERS for trig in event_counters])
            retries += 1

        counters = self.board.datapath_monitor_ib.read_all_counters()

        gbt0_counters = self.board._gbt_packer_0_monitor.read_counters(latch_first=True)
        if USE_ALL_UPLINKS:
            gbt1_counters = self.board._gbt_packer_1_monitor.read_counters(latch_first=False)
            gbt2_counters = self.board._gbt_packer_2_monitor.read_counters(latch_first=False)
        else:
            gbt1_counters = []
            gbt2_counters = []

        zero_counters = [
            # LANE
            "u8B10B_OOT",
            "u8B10B_OOT_FATAL",
            "u8B10B_OOT_TOLERATED",
            "PROTOCOL_ERROR",
            "BUSY_EVENT",
            "BUSY_VIOLATION",
            "DATA_OVERRUN",
            "BCID_MISMATCH",
            "DETECTOR_TIMEOUT",
            "RATE_OCCUPANCY_LIMIT",
            "LANE_FIFO_OVERFLOW",
            "LANE_FIFO_ERROR",
            "LANE_TIMEOUT",
            # GTH
            "CPLL_LOCK_LOSS",
            #"CDR_LOCK_LOSS", #TODO MB: Investigate source of CDR lock loss. Deactivate for now
            "ALIGNED_LOSS",
            "REALIGNED",
            "8b10b_OOT_ERROR",
        ]
        for i in range(NR_CHANNELS):
            for cntr_name in zero_counters:
                msg = "After Trigger: Lane {0}, Counter {1} is Off. All: {2}"
                self.assertEqual(counters[i][cntr_name],0, msg.format(i,cntr_name,pprint.pformat(counters)))
        return counters, gbt0_counters, gbt1_counters, gbt2_counters

    @unittest.skip("Transceiver locks to deactivated stream...")
    def test_locks(self):
        self.setup_chips()
        for ch in self.chips:
            ch.propagate_comma()

        initialized = self.board.gth.initialize()
        self.assertTrue(initialized, "Reset_done not received from GTH module")

        self.board.wait(500)

        locked = self.board.gth.is_cdr_locked()
        self.assertNotIn(False, locked, "Not all CDR circuits are locked")

        aligned = self.board.gth.align_transceivers()
        self.board.gth.enable_alignment(False)

        for ch in self.chips:
            ch.reset_pll()
            ch.setreg_dtu_cfg(PllOffSignal=1)

        self.board.wait(65535)
        aligned = self.board.gth.is_aligned()
        self.assertNotIn(True,aligned, "GTH module aligned to deactivated stream")

        self.board.wait(1000)
        for ch in self.chips:
            ch.setreg_mode_ctrl(IBSerialLinkSpeed=1)  # 600 Mbps
            ch.setreg_dtu_cfg(PllOffSignal=0)
            ch.reset_pll()

        cdr_lock_counters = self.board.datapath_monitor_ib.read_counter(
            range(9), "CDR_LOCK_LOSS")
        self.assertNotIn(0,cdr_lock_counters,"Expected a CDR lock loss event")
        aligned_lock_counters = self.board.datapath_monitor_ib.read_counter(
            range(9), "ALIGNEDLOSS")
        self.assertNotIn(0,aligned_lock_counters,"Expected a ALIGNED lock loss event")

        locked = self.board.gth.is_cdr_locked()
        self.assertNotIn(False, locked, "Not all CDR circuits are locked")

        aligned = self.board.gth.is_aligned()
        self.assertNotIn(False,aligned, "GTH module not aligned anymore")

    def test_prbs1200(self):
        self.setup_chips()
        for ch in self.chips:
            ch.propagate_prbs(PrbsRate=0)

        self.board.wait(500)
        initialized = self.board.gth.initialize()
        self.assertTrue(initialized, "Reset_done not received from GTH module")

        self.board.wait(250)
        locked = self.board.gth.is_cdr_locked()
        self.assertNotIn(False, locked, "Not all CDR circuits are locked")

        self.board.gth.enable_prbs(enable=True, commitTransaction=True)
        self.board.gth.reset_prbs_counter()

        # Read counters
        self.board.wait(100)

        prbs_errors = self.board.gth.read_prbs_counter(self)
        for cnt, link in zip(prbs_errors, self.board.gth.transceivers):
            self.assertEqual(0, cnt, "PRBS Error on Link {0}".format(link))

        # Set chip back to normal mode -> expect errors
        for ch in self.chips:
            ch.propagate_data(commitTransaction=False)
        self.board.wait(300, commitTransaction=False)
        # back to PRBS sending mode
        for ch in self.chips:
            ch.propagate_prbs(PrbsRate=0, commitTransaction=True)

        prbs_errors = self.board.gth.read_prbs_counter(self)
        for cnt, link in zip(prbs_errors, self.board.gth.transceivers):
            self.assertNotEqual(
                0, cnt, "No PRBS Error on Link {0}. Errors expected".format(link))

        # check Counter reset operation

        self.board.gth.reset_prbs_counter(commitTransaction=True)
        self.board.wait(200, commitTransaction=True)

        prbs_errors = self.board.gth.read_prbs_counter(self)
        for cnt, link in zip(prbs_errors, self.board.gth.transceivers):
            self.assertEqual(0, cnt, "PRBS Error on Link {0}".format(link))


@unittest.skipIf(not USB_MASTER, "No USB Master -> Cannot test dual master")
class TestWishboneDualMaster(TestcaseBase):

    def test_multiaccess_write(self):
        self.board.alpide_control.reset_counters()
        self.board_usb.read(1, 1)
        self.board.read(1, 1) # Sync both interfaces
        NR_WRITES = 10
        for i in range(NR_WRITES):
            self.board.alpide_control.write_chip_opcode(Opcode.RORST, commitTransaction=False)
            self.board.read(1 ,1 ,commitTransaction=False)
            self.board_usb.alpide_control.write_chip_opcode(Opcode.RORST, commitTransaction=False)
            self.board_usb.read(1, 1, commitTransaction=False)

        self.board.flush()
        self.board_usb.flush()
        result_cru = self.board.comm.diagnose_read_results()
        result_usb = self.board_usb.comm.diagnose_read_results()

        rderrors_cru = 0
        rderrors_usb = 0

        for err, addr, _ in result_cru:
            if err:
                rderrors_cru += 1
            self.assertEqual(addr, 0x0101, "Read from CRU: Address incorrect")
        for err, addr, _ in result_usb:
            if err:
                rderrors_usb += 1
            self.assertEqual(addr, 0x0101, "Read from USB: Address incorrect")

        if rderrors_cru + rderrors_usb > 0:
            print(f"{rderrors_cru} + {rderrors_usb} Read Errors on CRU or USB registered. Data_CRU: {result_cru}, Data_USB: {result_usb}")
        # check that both interfaces still work, and that all writes were received
        self.assertEqual(self.board.alpide_control.read_counters('OPCODE')['OPCODE'], 2*NR_WRITES,
                         "Write Execution Mismatch. (Not all chip opcodes performed)")
        self.assertEqual(self.board_usb.alpide_control.read_counters('OPCODE')['OPCODE'], 2*NR_WRITES,
                         "Write Execution Mismatch. (Not all chip opcodes performed)")

    def test_interleaved_reads(self):
        NR_LANES = 2 # DUT
        offset = self.board._datalane_monitor_ib.COUNTER_OFFSET
        counters_per_lane = len(self.board._datalane_monitor_ib.registers)-offset
        dead_regs = [r-offset for r in self.board._datalane_monitor_ib.registers if r.name.startswith('DEAD')]
        datapath_monitor_testlist = [offset+reg+counters_per_lane*lane for lane in range(NR_LANES) for reg in range(counters_per_lane) if reg not in dead_regs]
        testlist = [(XckuModuleid.DATALANE_MONITOR_IB,i) for i in datapath_monitor_testlist] + [(1,1), (1,0)]

        self.board.wait(100, commitTransaction=False) # sync
        for mod, addr in testlist:
            self.board.read(mod, addr, commitTransaction=False)
        for mod, addr in reversed(testlist):
            self.board_usb.read(mod, addr, commitTransaction=False)

        self.board.flush()
        self.board_usb.flush()

        result_usb = list(reversed(self.board_usb.comm.read_results()))
        result_cru = self.board.comm.read_results()

        self.assertEqual(result_usb, result_cru, "Same Read sequence leads to different results for both wishbone masters")

    def test_timeouts(self):
        _, githash_ref = self.board.read(1,1)

        # cause timeouts on both interfaces
        self.board.write(100, 1, 0)
        self.board_usb.write(100, 1, 0)

        with self.assertRaises(WishboneReadError, msg="Error for illegal read not raised"):
            self.board.read(100, 1)
        with self.assertRaises(WishboneReadError, msg="Error for illegal read not raised"):
            self.board_usb.read(100, 1)
        # check that read still works
        _, gh_cru = self.board.read(1, 1)
        _, gh_usb = self.board_usb.read(1, 1)

        self.assertEqual(gh_cru, githash_ref, "CRU comm0 githash mismatch")
        self.assertEqual(gh_usb, githash_ref, "USB comm0 githash mismatch")

    def test_usb_multiread(self):
        """Test for issue #132"""
        self.board_usb.master_monitor.read_counters()
        self.board_usb.trigger_handler.read_counters()


class TestSysmon(TestcaseBase):
    @unittest.skipIf(SIMULATION, "Invalid sim model")
    def test_getTemperature(self):
        rv = self.board.sysmon.get_temperature()
        self.assertTrue(15.0 < rv < 95.0, "Read value is {0}".format(rv))

    @unittest.skipIf(SIMULATION, "Invalid sim model")
    def test_getVccInt(self):
        rv = self.board.sysmon.get_vcc_int()
        self.assertTrue(0.855 < rv < 1.045, "Read value is {0}".format(rv))

    @unittest.skipIf(SIMULATION, "Invalid sim model")
    def test_getVccAux(self):
        rv = self.board.sysmon.get_vcc_aux()
        self.assertTrue(1.62 < rv < 1.98, "Read value is {0}".format(rv))

    @unittest.skipIf(SIMULATION, "Invalid sim model")
    def test_getVccBram(self):
        rv = self.board.sysmon.get_vcc_bram()
        self.assertTrue(0.855 < rv < 1.045, "Read value is {0}".format(rv))

    def test_getOtStatus(self):
        rv = self.board.sysmon.get_ot_status()
        self.assertFalse(rv)

    def test_enableOtProtection(self):
        # Get the current status of register 0x41
        self.board.sysmon.set_drp_address(0x41)
        data1 = self.board.sysmon.get_drp_data()

        # Run tested method
        self.board.sysmon.enable_ot_protection()

        # Get the current status of register 0x41
        self.board.sysmon.set_drp_address(0x41)
        data2 = self.board.sysmon.get_drp_data()

        # Data must be equal except the last bit, the last bit must be 0
        self.assertEqual(data1 & ~0x01, data2 & ~0x01)
        self.assertEqual(data2 & 0x01, 0x00)

    def test_disableOtProtection(self):
        # Get the current status of register 0x41
        self.board.sysmon.set_drp_address(0x41)
        data1 = self.board.sysmon.get_drp_data()

        # Run tested method
        self.board.sysmon.disable_ot_protection()

        # Get the current status of register 0x41
        self.board.sysmon.set_drp_address(0x41)
        data2 = self.board.sysmon.get_drp_data()

        # Data must be equal except the last bit, the last bit must be 1
        self.assertEqual(data1 & ~0x01, data2 & ~0x01)
        self.assertEqual(data2 & 0x01, 0x01)

    @unittest.skipIf(SIMULATION, "Invalid sim model")
    def test_getVcc_ALPIDE_3v3(self):
        rv = self.board.sysmon.get_vcc_alpide_3v3()
        self.assertTrue(2.97 < rv < 3.63, "Read value is {0}".format(rv))

    @unittest.skipIf(SIMULATION, "Invalid sim model")
    def test_getVcc_SCA_1v5(self):
        rv = self.board.sysmon.get_vcc_sca_1v5()
        self.assertTrue(1.35 < rv < 1.65, "Read value is {0}".format(rv))


@unittest.skipIf(not SIMULATION, "Check for correct I2C addresses in hardware")
class TestI2C(TestcaseBase):

    @classmethod
    def setUpClass(self):
        super().setUpClass()
        boardGlobal.powerunit_1.controller.set_temperature_interlock_enable_mask(0)
        boardGlobal.powerunit_2.controller.set_temperature_interlock_enable_mask(0)

    def test_i2c_gbtx(self):
        self.board.i2c_gbtx.reset_counters()
        self.board.i2c_gbtx.write_gbtx_register(gbtx_index=0, register=0x1234, value=0x0056, check=False, commitTransaction=False)  # write to GBTx0 address 0x1234
        self.board.i2c_gbtx._write_data(0x00BC, False)  # write to GBTx0 address 0x1235 (auto-increment)
        self.board.i2c_gbtx._write_data(0x0042, False)  # write to GBTx0 address 0x1236 (auto-increment)
        self.board.i2c_gbtx.write_gbtx_register(gbtx_index=1, register=0xabcd, value=0x00ef, check=False, commitTransaction=False)  # write to GBTx1 address 0xabcd
        self.board.i2c_gbtx.write_gbtx_register(gbtx_index=2, register=0x5678, value=0x00ab, check=False, commitTransaction=False)  # write to GBTx2 address 0x5678

        rb = self.board.i2c_gbtx.read_gbtx_register(gbtx_index=0, register=0x1236, check=False)  # read from GBTx0 address 0x1236
        self.assertEqual(rb, 0x42, "I2C readback failed: expected 0x0042 got {0:#06x}".format(rb))
        rb = self.board.i2c_gbtx.read_gbtx_register(gbtx_index=0, register=0x1234, check=False)  # read from GBTx0 address 0x1234
        self.assertEqual(rb, 0x56, "I2C readback failed: expected 0x0056 got {0:#06x}".format(rb))
        rb = self.board.i2c_gbtx._read_data()  # read from GBTx0 address 0x1235
        self.assertEqual(rb, 0xBC, "I2C readback failed: expected 0x00bc got {0:#06x}".format(rb))

        rb = self.board.i2c_gbtx.read_gbtx_register(gbtx_index=1, register=0xabcd, check=False)  # read from GBTx1 address 0xabcd
        self.assertEqual(rb, 0xef, "I2C readback failed: expected 0x00ef got {0:#06x}".format(rb))

        rb = self.board.i2c_gbtx.read_gbtx_register(gbtx_index=2, register=0x5678, check=False)  # read from GBTx2 address 0x5678
        self.assertEqual(rb, 0xab, "I2C readback failed: expected 0x00ab got {0:#06x}".format(rb))

        # read the i2c monitor counters
        counters = self.board.i2c_gbtx.read_counters()
        completed_bytes = counters['completed_byte_count']
        self.assertEqual(completed_bytes, 45, "I2C completed_byte_count wrong, expected 45 got {}".format(completed_bytes))
        for key in counters:
            if key != 'completed_byte_count':
                self.assertEqual(counters[key], 0)

    def _test_i2c_pu(self, powerunit):
        # do a "dummy" read from I2C to assure that the monitoring loops are finished,
        # since they might have just been turned off
        powerunit.aux.do_read_transaction(WbI2cPuAuxAddress.IOExpanderPowerAddress_0_Read)

        # now reset the counters for aux bus
        powerunit.aux_monitor.reset_all_counters()

        # write and read aux I2C bus (slave with 0 address 1 data byte)
        powerunit.aux.write(WbI2cPuAuxAddress.IOExpanderPowerAddress_0, 0x5678)
        rb = powerunit.aux.do_read_transaction(WbI2cPuAuxAddress.IOExpanderPowerAddress_0_Read)
        self.assertEqual(rb, 0x78, "I2C readback failed: expected 0x0078 got {0:#06x}".format(rb))

        # read the i2c monitor counters
        counters = powerunit.aux_monitor.read_counters()
        completed_bytes = counters['completed_byte_count']
        self.assertEqual(completed_bytes, 4, "I2C completed_byte_count wrong, expected 4 got {}".format(completed_bytes))
        for key in counters:
            if key != 'completed_byte_count':
                self.assertEqual(counters[key], 0, counters)

        # do a "dummy" read from I2C to assure that the monitoring loops are finished,
        # since they might have just been turned off
        powerunit.do_read_transaction(WbI2cPuAddress.IOExpanderBiasAddress_Read)

        # reset the counters before starting
        powerunit.main_monitor.reset_all_counters()

        # write and read main I2C bus (slave with 0 address 1 data byte)
        powerunit.write(WbI2cPuAddress.IOExpanderBiasAddress, 0x1234)
        rb = powerunit.do_read_transaction(WbI2cPuAddress.IOExpanderBiasAddress_Read)
        self.assertEqual(rb, 0x34, "I2C readback failed: expected 0x0034 got {0:#06x}".format(rb))

        # write and read main I2C bus (slave with 1 byte write, 2 byte read)
        powerunit.write(WbI2cPuAddress.ADCAddress_0, 0xa9)
        rb = powerunit.do_read_transaction(WbI2cPuAddress.ADCAddress_0_Read)
        # expect the last byte written to be in both MSB and LSB (simple I2C slave with just 1 byte memory)
        self.assertEqual(rb, 0xa9a9, "I2C readback failed: expected 0xa9a9 got {0:#06x}".format(rb))

        # read the i2c monitor counters
        counters = powerunit.main_monitor.read_counters()
        completed_bytes = counters['completed_byte_count']
        self.assertEqual(completed_bytes, 9, "I2C completed_byte_count wrong, expected 9 got {}".format(completed_bytes))
        for key in counters:
            if key != 'completed_byte_count':
                self.assertEqual(counters[key], 0, counters)

    def test_i2c_pu1(self):
        self._test_i2c_pu(self.board.powerunit_1)

    def test_i2c_pu2(self):
        self._test_i2c_pu(self.board.powerunit_2)


class AlpideControlBaseTest:

    class TestAlpideControl(TestcaseBase):
        chipid = None

        def configure_test(self, connector, chipid):
            self.connector = connector
            self.chipid = chipid

        def setUp(self):
            super().setUp()
            self.board.alpide_control.disable_manchester_tx()
            self.ch = Alpide(self.board, chipid=self.chipid)
            self.ch.reset()

        def tearDown(self):
            self.board.alpide_control.disable_manchester_tx()
            self.ch.setreg_cmu_and_dmu_cfg(PreviousChipID=self.chipid & 0xF,
                                           InitialToken=0,
                                           DisableManchester=True,
                                           EnableDDR=1)

        def _test_chip_read_write(self):
            self.ch.write_reg(0x19, 0x4242, commitTransaction=True,
                              readback=True, log=False, verbose=False)
            self.ch.write_reg(0x19, 0xDEAD, commitTransaction=True,
                              readback=True, log=False, verbose=False)
            self.ch.write_reg(0x19, 0xAAAA, commitTransaction=True,
                              readback=True, log=False, verbose=False)
            self.ch.write_reg(0x19, 0x5555, commitTransaction=True,
                              readback=True, log=False, verbose=False)

        def _test_manchester_settings(self, manchesterTx=True, manchesterRx=True):
            if manchesterTx:
                self.board.alpide_control.enable_manchester_tx()
            else:
                self.board.alpide_control.disable_manchester_tx()
            self.ch.setreg_cmu_and_dmu_cfg(PreviousChipID=self.chipid & 0xF,
                                           InitialToken=0,
                                           DisableManchester=not manchesterRx,
                                           EnableDDR=1
                                           )
            self.board.wait(10)
            self._test_chip_read_write()
            self.board.alpide_control.disable_manchester_tx()
            self.ch.setreg_cmu_and_dmu_cfg(PreviousChipID=self.chipid & 0xF,
                                           InitialToken=0,
                                           DisableManchester=True,
                                           EnableDDR=1
                                           )

        def _test_reads(self, manchester_rx=True, test_number=30,
                        assert_manchester=False):
            """Tests readback alpide chips with given parameters (tx/rx manchester)
            """
            value0 = 0xAA
            value1 = 0x55
            self.ch.setreg_cmu_and_dmu_cfg(PreviousChipID=self.chipid & 0xF,
                                           InitialToken=0,
                                           DisableManchester=not manchester_rx,
                                           EnableDDR=1, commitTransaction=False
                                           )
            self.board.wait(10, commitTransaction=False)
            self.ch.setreg_dtu_test_2(DIN0=value0, DIN1=value1, commitTransaction=False)
            self.board.wait(10, commitTransaction=False)
            for i in range(test_number):
                ret = self.ch.getreg_dtu_test_2()[1]
                manchester_detected = self.board.alpide_control.get_manchester_rx_detected()
                self.assertEqual(value0, ret['DIN0'], msg=f"Readback differs set {value0:#04X} get {ret['DIN0']:#04X} on iteration {i}")
                self.assertEqual(value1, ret['DIN1'], msg=f"Readback differs set {value1:#04X} get {ret['DIN1']:#04X} on iteration {i}")
                if assert_manchester:
                    self.assertEqual(manchester_detected, manchester_rx, msg=f"Manchester not detected correctly (get {manchester_detected}, set {manchester_rx} on iteration {i})")
            self.ch.setreg_cmu_and_dmu_cfg(PreviousChipID=self.chipid & 0xF,
                                           InitialToken=0,
                                           DisableManchester=True,
                                           EnableDDR=1
                                           )

        def test_dctrl_dac_range(self):
            self.ch.setreg_dac_settings_cmu_io_buffers(
                DCTRLDriver=0x2, DCTRLReceiver=0xA)
            self._test_chip_read_write()
            self.ch.setreg_dac_settings_cmu_io_buffers(
                DCTRLDriver=0x8, DCTRLReceiver=0xA)
            self._test_chip_read_write()
            self.ch.setreg_dac_settings_cmu_io_buffers(
                DCTRLDriver=0xF, DCTRLReceiver=0xA)
            self._test_chip_read_write()

        def test_manchester_tx_on_rx_on(self):
            self._test_manchester_settings(True, True)

        def test_manchester_tx_on_rx_off(self):
            self._test_manchester_settings(True, False)

        def test_manchester_tx_off_rx_on(self):
            self._test_manchester_settings(False, True)

        def test_manchester_tx_off_rx_off(self):
            self._test_manchester_settings(False, False)

        def test_multiple_reads_rx_manchester(self):
            self._test_reads(manchester_rx=True)

        def test_multiple_reads_rx_no_manchester(self):
            self._test_reads(manchester_rx=False)

        def test_dclk_phases(self):
            for phase in range(0, 360, 45):
                for index in range(5):
                    self.board.alpide_control.set_dclk_parallel(index=index, phase=phase, commitTransaction=False)
                self.board.alpide_control.flush()
                for index in range(5):
                    ret = self.board.alpide_control.get_dclk_parallel(index=index)
                    self.assertEqual(ret, phase, msg=f"phase_set mismatch {ret} instead of {phase} on index {index}")
            for index in range(5):
                self.board.alpide_control.set_dclk_parallel(index=index, phase=180, commitTransaction=False)
            self.board.alpide_control.flush()
            self.ch.reset()

        def test_CMU_error_status(self):
            self.ch.getreg_dtu_pll_lock_2()
            dataread, ret = self.ch.getreg_cmu_and_dmu_status()
            self.assertEqual(ret["CMUErrorsCounter"], 0, msg=f"CMU errors are {ret['CMUErrorsCounter']:#04X} instead of 0 {dataread:#06X}")
            self.assertEqual(ret["CMUTimeOutCounter"], 0, msg=f"CMU Timeout errors are {ret['CMUTimeOutCounter']:#04X} instead of 0 {dataread:#06X}")
            self.assertEqual(ret["CMUOpCounter"], 0, msg=f"CMU Unknown Opcode errors are {ret['CMUOpCounter']:#04X} instead of 0 {dataread:#06X}")

        def test_counters(self):
            self.ch.getreg_dtu_pll_lock_2(commitTransaction=False)
            self.board.alpide_control.reset_counters(commitTransaction=False)
            ret = self.board.alpide_control.read_counters()
            for key, value in ret.items():
                self.assertEqual(value, 0, msg=f"Wrong counter {key} value, got {value}, expected 0")
            self.ch.getreg_dtu_pll_lock_2(commitTransaction=False)
            ret = self.board.alpide_control.read_counters()
            expect_1 = ['READ_OPCODE', 'READ_DONE']
            for key, value in ret.items():
                if key in expect_1:
                    self.assertEqual(value, 1, msg=f"Wrong counter {key} value, got {value}, expected 1")
                else:
                    self.assertEqual(value, 0, msg=f"Wrong counter {key} value, got {value}, expected 0")

        def test_readback_wait_cycles(self):
            """Test readback of initial wait register"""
            value = self.board.alpide_control.get_wait_cycles()
            test_value = 5
            self.board.alpide_control.set_wait_cycles(test_value, commitTransaction=False)
            rd_value = self.board.alpide_control.get_wait_cycles()
            self.assertEqual(rd_value, test_value, msg=f"Wrong counter value, got {rd_value}, expected {test_value}")
            self.board.alpide_control.set_wait_cycles(value)

        def test_read_done_counter(self):
            """Tests if the read_done counter is counting correctly"""
            self.board.alpide_control.reset_counters(commitTransaction=False)
            counters = self.board.alpide_control.read_counters('READ_DONE')
            self.assertEqual(counters['READ_DONE'], 0)
            reads = 10
            for _ in range(reads):
                self.ch.getreg_cmd()
            counters = self.board.alpide_control.read_counters(('READ_DONE', 'CHIPID_MISMATCH'))
            self.assertEqual(counters['READ_DONE'], reads)
            self.assertEqual(counters['CHIPID_MISMATCH'], 0)

        def _test_db_fifo(self, disable_manchester):
            self.ch.setreg_cmu_and_dmu_cfg(PreviousChipID=self.chipid & 0xF,
                                           InitialToken=0,
                                           DisableManchester=disable_manchester,
                                           EnableDDR=1, commitTransaction=False)
            self.ch.setreg_dtu_test_2(DIN0=0xAB, DIN1=0xCD, commitTransaction=False)
            self.ch.getreg_dtu_test_2()
            ret = self.board.alpide_control.dump_db_fifo(stop_at=3) # avoids x in sim
            for r in ret:
                print(f"0b{r:08b}")

        def test_dclk_propagation(self):
            """
            Checks if the dclk is propagated to the correct dctrl
            This testcase addresses https://gitlab.cern.ch/alice-its-wp10-firmware/RU_mainFPGA/issues/158
            """
            self.board.alpide_control.disable_dclk(index=self.connector,commitTransaction=False)
            logging.getLogger('Module Id 4: ALPIDE CONTROL').setLevel(logging.CRITICAL)
            with self.assertRaises(ChipidMismatchError, msg='Chip is responding with DCLK disabled!'):
                self.ch.getreg_cmd()
            logging.getLogger('Module Id 4: ALPIDE CONTROL').setLevel(logging.WARNING)
            self.board.alpide_control.enable_dclk(index=self.connector, commitTransaction=False)
            self.board.wait(0xFF, commitTransaction=False)
            self.ch.reset(commitTransaction=False)
            self.assertEqual(self.ch.getreg_cmd()[0], 0)

        @unittest.skip("Only for module verification, not really a test")
        def test_db_fifo(self):
            self._test_db_fifo(disable_manchester=1)

        @unittest.skip("Only for module verification, not really a test")
        def test_db_fifo_manchester(self):
            self._test_db_fifo(disable_manchester=0)


@unittest.skipIf(0 not in CONNECTORS, "No Chip Connected")
class TestAlpideControl0(AlpideControlBaseTest.TestAlpideControl):

    def setUp(self):
        self.configure_test(connector=0, chipid=SENSOR_LIST[0])
        super().setUp()


@unittest.skipIf(1 not in CONNECTORS, "No Chip Connected")
class TestAlpideControl1(AlpideControlBaseTest.TestAlpideControl):

    def setUp(self):
        self.configure_test(connector=1, chipid=SENSOR_LIST[0])
        super().setUp()


@unittest.skipIf(2 not in CONNECTORS, "No Chip Connected")
class TestAlpideControl2(AlpideControlBaseTest.TestAlpideControl):

    def setUp(self):
        self.configure_test(connector=2, chipid=SENSOR_LIST[0])
        super().setUp()


@unittest.skipIf(3 not in CONNECTORS, "No Chip Connected")
class TestAlpideControl3(AlpideControlBaseTest.TestAlpideControl):

    def setUp(self):
        self.configure_test(connector=3, chipid=SENSOR_LIST[0])
        super().setUp()


@unittest.skipIf(4 not in CONNECTORS, "No Chip Connected")
class TestAlpideControl4(AlpideControlBaseTest.TestAlpideControl):

    def setUp(self):
        self.configure_test(connector=4, chipid=SENSOR_LIST[0])
        super().setUp()


@unittest.skip("deactivate")
class TestPythonScripts(TestcaseBase):

    def _function_call_routine(self):
        self.board.check_git_hash(expected_git_hash=GITHASH)
        self.board.wait(100)
        counters = self.board.datapath_monitor_ib.read_all_counters()

    def _function_read_counters(self):
        counters_datamon = self.board.datapath_monitor_ib.read_all_counters()
        counters_alpide_control = self.board.alpide_control.read_counters()
        counters_cru = self.cru0.read_counters()

        ch = Alpide(self.board,chipid=SENSOR_LIST[0]) #global broadcast
        seu_error_counter = ch.read_reg(Addr.SEU_ERROR_COUNTER)
        lock = ch.getreg_dtu_pll_lock_1()[1]
        lock_counter = lock['LockCounter']
        lock_status = lock['LockStatus']
        lock_flag = lock['LockFlag']

        powerunit = self.board.powerunit_1

        latch_status = powerunit.get_power_enable_status()
        bias_latch_status = powerunit.get_bias_enable_status()
        adc_power = powerunit.read_power_adc()
        adc_bias = powerunit.read_bias_adc()

    def test_githash(self):
        NR_TESTS = 1000
        keys = {
            self.board.read(65,0,commitTransaction=True):"CRU 1 0" ,
            self.board.read(65,1,commitTransaction=True):"CRU 1 1" ,
            self.board.read(1,0,commitTransaction=True):"RDO 1 0" ,
            self.board.read(1,1,commitTransaction=True):"RDO 1 1",
            self.board.read(3,0,commitTransaction=True):"RDO 3 0"
        }
        for i in range(NR_TESTS):
            self.board.read(65,0,commitTransaction=False)
            #self.board.read(3,0,commitTransaction=False)
            self.board.read(1,0,commitTransaction=False)
            self.board.read(65,1,commitTransaction=False)
            self.board.read(1,1,commitTransaction=False)
        self.board.flush()
        results = self.board.read_all()
        result_set = {}
        for r in results:
            if r not in result_set:
                result_set[r] = 0
            result_set[r] += 1
        print(["{0}: {1}".format(keys[k],v) for k,v in result_set.items()])
        for k,x in result_set.items():
            self.assertEqual(NR_TESTS,x,"Address {0}, counter not {1}".format(k,NR_TESTS))


    def _function_readout_setup(self):
        #setup all chips
        ch = Alpide(self.board,chipid=0x0F) #global broadcast
        ch.reset()
        self.board.gth.initialize(check_reset_done=False)
        ch.initialize(disable_manchester=1,grst=False,cfg_ob_module=False)
        ch.setreg_dtu_dacs(PLLDAC=8,DriverDAC=8,PreDAC=8)
        for pll_off_sig in [0,1,0]:
            ch.setreg_dtu_cfg(VcoDelayStages=1,
                              PllBandwidthControl = 1,
                              PllOffSignal=pll_off_sig,
                              SerPhase=8,
                              PLLReset=0,
                              LoadENStatus=0)

        ch.board.write_chip_opcode(Opcode.RORST)

        ch.setreg_fromu_cfg_1(
                           MEBMask=0,
                           EnStrobeGeneration=0,
                           EnBusyMonitoring=1,
                           PulseMode=0,
                           EnPulse2Strobe=0,
                           EnRotatePulseLines=0,
                           TriggerDelay=0)

        ch.setreg_fromu_pulsing_2(PulseDuration=0xFF)
        ch.setreg_fromu_pulsing1(PulseDelay=0xF)

        ch.mask_all_pixels()
        ch.region_control_register_mask_all_double_columns(broadcast=True)

        ch.setreg_mode_ctrl(ChipModeSelector=1,
                            EnClustering=1,
                            MatrixROSpeed=1,
                            IBSerialLinkSpeed=3,
                            EnSkewGlobalSignals=1,
                            EnSkewStartReadout=1,
                            EnReadoutClockGating=1,
                            EnReadoutFromCMU=0)

        self.board.wait(1000)
        initialized = self.board.gth.initialize()
        self.assertTrue(initialized, "Reset_done not received from GTH module")
        self.board.wait(100)
        locked = self.board.gth.is_cdr_locked()
        self.assertNotIn(False, locked, "Not all CDR circuits are locked")
        self.board.gth.align_transceivers(check_aligned=False)
        self.board.wait(255)
        aligned = self.board.gth.is_aligned()
        self.assertTrue(aligned, "GTH module could not align to all modules")
        self.board.datapath_monitor_ib.reset_all_counters()
        counters = self.board.datapath_monitor_ib.read_all_counters()
        for idx,c in enumerate(counters):
            for cntr,val in c.items():
                self.assertEqual(0,val,"Counter {0} non-zero after reset".format(idx))
        self.board.gth.enable_data()


    def _test_prefetch_function(self,func):
        self.board.comm.start_recording()
        func()
        sequence = self.board.comm.stop_recording()
        print("Length of prefetch sequence: {0}".format(len(sequence)))
        self.board.comm.prefetch()
        func()
        self.assertTrue(self.board.comm.prefetch_mode,"Prefetch mode False, should be True")
        with self.assertLogs(self.board.comm.logger,logging.ERROR):
            self.board.check_git_hash(expected_git_hash=GITHASH)
            self.assertFalse(self.board.comm.prefetch_mode,"Prefetch mode True, should be False")

    def test_prefetch_githash(self):
        self._test_prefetch_function(self.test_githash)

    def test_prefetch_counters(self):
        self._test_prefetch_function(self._function_read_counters)

    def test_prefetch_basic_communication(self):
        self._test_prefetch_function(self._function_call_routine)
    def test_prefetch_sensor_datareadout(self):
        self._test_prefetch_function(self._function_readout_setup)


@unittest.skip("add sca in regression")
class TestScaReset(TestcaseBase):
    def setUp(self):
        super(TestScaReset, self).setUp()
        self.board.wait(1000,commitTransaction=False) # sync

    def test_reset(self):
        """Asserts reset via SCA, it tries to read, expect fail, deassert reset, expect correct read"""
        read_lists = [(1,0), (1,1)]

        # reset is active
        self.cru0.sca.set_xcku_reset(1)
        for mod,addr in read_lists:
            with self.assertRaises(WishboneReadError, msg="Error for read during reset not raised"):
                self.board.read(mod,addr)

        # reset is deactivated
        self.cru0.sca.set_xcku_reset(0)
        for mod,addr in read_lists:
            self.board.read(mod,addr)


@unittest.skip("Dummytest for exit code verification")
class TestSimExitHandling(TestcaseBase):
    def test_1_pass(self):
        _, githash_ref = self.board.read(1,1)

    @unittest.skip("Failure disabled")
    def test_2_fail(self):
        self.assertEqual(0,1,"Failure provoked")


@unittest.skipIf(SIMULATION and not SIMULATE_CRU,"Needs CRU functionality to test")
class TestCRUSWTRaceCondition(TestcaseBase):
    def setUp(self):
        super().setUp()
        self.logger = logging.getLogger("TestRaceCondition")

    def _test_register(self,module,address,mask=0):
        if SIMULATION:
            NR_TESTS = 10
        else:
            NR_TESTS = 100
        error_counts = 0
        _, base_value = self.board.read(module,address)
        base_value_test = ~(base_value&0xffff)&mask
        self.board.gbtx_flow_monitor.reset_all_counters()
        self.send_idle(50)
        self.cru0.reset_counters()
        for i in range(NR_TESTS):
            self.board.write(module,address,base_value_test)
            self.send_end_of_triggered()
            self.cru0.wait(20)
            _, value_rb = self.board.read(module,address)
            self.board.write(module,address,base_value)
            if value_rb != base_value_test:
                error_counts += 1
                self.logger.info("Iteration {0}. Mismatch. {1}/{2}".format(i,value_rb,base_value_test))

        cru_counter = self.cru0.read_counters()['gbt_wr_swt_counter']
        self.board.gbtx_flow_monitor.latch_all_counters(commitTransaction=False)
        self.send_idle(50)
        gbtx_counters = self.board.gbtx_flow_monitor.read_counters(counters=('SWT_DOWNLINK0'), latch_first=False)

        swt_counter = gbtx_counters['SWT_DOWNLINK0']

        self.logger.info("SWT Counter value: {0}".format(swt_counter))
        self.logger.info("Cru counter: {0}".format(cru_counter))

        self.assertEqual(cru_counter,3*NR_TESTS,"CRU SWT wr counter mismatch (3* Number of Tests)")
        self.assertEqual(swt_counter,3*NR_TESTS+2,"SWT counter mismatch (should be 3* Number of Tests + 2 (counter latching))")

        self.assertEqual(error_counts,0,"Value rb failed")

    def test_set_dctrl_mask(self):
        self._test_register(XckuModuleid.ALPIDE_CONTROL,WsAlpideControlAddress.SET_DCTRL_TX_MASK,0x1F)

    def test_set_trigger_period(self):
        self._test_register(XckuModuleid.TRIGGER_HANDLER,WsTriggerHandlerAddress.TRIGGER_PERIOD,0x0FFF)

    def test_gbtx2_idelay(self):
        self._test_register(XckuModuleid.GBTX2,WsGbtxControllerAddress.SET_IDELAY_VALUE0,0x1FF)


@unittest.skipIf(not USE_CAN, "CAN not available")
class TestCanbus(TestcaseBase):
    """This test uses can_comm directly to read and write via CAN.
    The normal board.comm (SWT) is also used to configure CAN for increased bitrate for simulation,
    and to read out githash so we can compare it with the same value read via CAN bus."""

    def test_canbus(self):
        ghash_expected = GITHASH

        if SIMULATION:
            can_comm.set_node_id(CAN_NODE_ID)

            # Configure CAN bus for 4 Mbit to speed up simulation
            # We also have to reduce the number of time quantas to
            # 10 to be able to achieve that bit rate.
            self.board.can_hlp.set_prop_segment_time_quanta_count(3)
            self.board.can_hlp.set_phase_segment1_time_quanta_count(3)
            self.board.can_hlp.set_phase_segment2_time_quanta_count(3)
            self.board.can_hlp.set_bitrate(4000000, hw_supported_only=False)

            # Wait for 5 us to give the CAN controller some time to reconfigure
            self.board.wait(800, commitTransaction=False)
            self.sync()

        else:
            # Use FEE ID set with DIP switches as CAN node ID
            fee_id = self.board.identity.get_fee_id()
            can_comm.set_node_id(fee_id)

            # Get githash with board's comm object (typically USB)
            ghash_expected = self.board.identity.get_git_hash()


        githash = self.board_can.identity.get_git_hash()

        self.assertEqual(githash, ghash_expected,
                         "Returned value {0:08X} different than expected {1:08X}".format(ghash_expected, githash))

        hlp_test_reg_expect = random.randint(0, 2 ** 16 - 1)

        self.board_can.can_hlp.write(WsCanHlpAddress.TEST_REG, hlp_test_reg_expect)

        can_test_reg = self.board_can.can_hlp.read(WsCanHlpAddress.TEST_REG)

        self.assertEqual(can_test_reg, hlp_test_reg_expect,
                         "Returned value {0:08X} different than expected {1:08X}".format(hlp_test_reg_expect, can_test_reg))

        # Set bit rate back to default settings (16 time quantas and 250 kbps)
        self.board.can_hlp.set_prop_segment_time_quanta_count(6)
        self.board.can_hlp.set_phase_segment1_time_quanta_count(5)
        self.board.can_hlp.set_phase_segment2_time_quanta_count(4)
        clock_scale_250kbps = self.board.can_hlp.get_possible_bitrates(hw_supported_only=False)[250000]
        self.board.can_hlp.set_can_clock_scale(clock_scale_250kbps)


#@unittest.skipIf(not SIMULATION,"Only available in simulation.")
@unittest.skip("To be moved to readout_tb")
class TestFeeIdIssue210(TestcaseBase):
    @classmethod
    def tearDownClass(self):
        sim_comm.set_dipswitches(feeid=CAN_NODE_ID)

    def _test_single_feeid(self,feeid):
        if SIMULATION:
            sim_comm.set_dipswitches(feeid)
        else:
            raise NotImplementedError

        #self.board.identity.get_fee_id(commitTransaction=False)
        #self.board.gbt_packer_0.get_fee_id(commitTransaction=False)
        #self.board.gbt_packer_1.get_fee_id(commitTransaction=False)
        #self.board.gbt_packer_2.get_fee_id(commitTransaction=False)
        #reg_list = [WsIdentityAddress.DIPSWITCH_VAL,ru_gbt_packer.GbtPackerAddress.FEE_ID,ru_gbt_packer.GbtPackerAddress.FEE_ID,ru_gbt_packer.GbtPackerAddress.FEE_ID]
        #module_list = [XckuModuleid.IDENTITY,XckuModuleid.GBT_PACKER_0,XckuModuleid.GBT_PACKER_1,XckuModuleid.GBT_PACKER_2]

        #self.board.flush()
        #results = self.board.comm.read_results()
        #assert len(results) == len(reg_list) == len(module_list)
        #for i, address in enumerate(reg_list):
        #    module = module_list[i]
        #    assert ((results[i][0] >> 8) & 0x7f) == module, \
        #            "Requested to read module {0}, but got result for module {1}, iteration {2}".format(module, ((results[i][0] >> 8) & 0x7f), i)
        #    assert (results[i][0] & 0xff) == address.value, \
        #            "Requested to read address {0}, but got result for address {1}, iteration {2}".format(address.value, (results[i][0] & 0xff), i)
        #id_feeid = results[module_list.index(XckuModuleid.IDENTITY)][1]>>2
        #gbt0_feeid = results[module_list.index(XckuModuleid.GBT_PACKER_0)][1]
        #gbt1_feeid = results[module_list.index(XckuModuleid.GBT_PACKER_1)][1]
        #gbt2_feeid = results[module_list.index(XckuModuleid.GBT_PACKER_2)][1]

        #_,layer,stave  = self.board.identity.decode_fee_id(id_feeid)
        #layer0,gbt_link0,stave0 = self.board.gbt_packer_0.decode_fee_id(gbt0_feeid)
        #layer1,gbt_link1,stave1 = self.board.gbt_packer_1.decode_fee_id(gbt1_feeid)
        #layer2,gbt_link2,stave2 = self.board.gbt_packer_2.decode_fee_id(gbt2_feeid)

        #self.assertEqual(layer,layer0,"Layer mismatch")
        #self.assertEqual(layer,layer1,"Layer mismatch")
        #self.assertEqual(layer,layer2,"Layer mismatch")

        #self.assertEqual(0,gbt_link0,"Gbt link mismatch")
        #self.assertEqual(1,gbt_link1,"Gbt link mismatch")
        #self.assertEqual(2,gbt_link2,"Gbt link mismatch")

        #self.assertEqual(stave,stave0,"Stave mismatch")
        #self.assertEqual(stave,stave1,"Stave mismatch")
        #self.assertEqual(stave,stave2,"Stave mismatch")

    def test_feeids_L0(self):
        """Test different FEE IDs.
        Full coverage would take 30 minutes of regression, so sample is limited to a third.
        The factor 3 is chosen to allow toggling of bit 0 of FEEID"""
        feeid_list = [FeeIdLayerId.L0|i for i in range(0,(~FeeIdLayerMask.L0&0xFF)+1,3)]
        for feeid in feeid_list:
            self._test_single_feeid(feeid)

    def test_feeids_L1(self):
        feeid_list = [FeeIdLayerId.L1|i for i in range(0,(~FeeIdLayerMask.L1&0xFF)+1,3)]
        for feeid in feeid_list:
            self._test_single_feeid(feeid)

    def test_feeids_L2(self):
        feeid_list = [FeeIdLayerId.L2|i for i in range(0,(~FeeIdLayerMask.L2&0xFF)+1,3)]
        for feeid in feeid_list:
            self._test_single_feeid(feeid)

    def test_feeids_L3(self):
        feeid_list = [FeeIdLayerId.L3|i for i in range(0,(~FeeIdLayerMask.L3&0xFF)+1,3)]
        for feeid in feeid_list:
            self._test_single_feeid(feeid)

    def test_feeids_L4(self):
        feeid_list = [FeeIdLayerId.L4|i for i in range(0,(~FeeIdLayerMask.L4&0xFF)+1,3)]
        for feeid in feeid_list:
            self._test_single_feeid(feeid)

    def test_feeids_L5(self):
        feeid_list = [FeeIdLayerId.L5|i for i in range(0,(~FeeIdLayerMask.L5&0xFF)+1,3)]
        for feeid in feeid_list:
            self._test_single_feeid(feeid)

    def test_feeids_L6(self):
        feeid_list = [FeeIdLayerId.L6|i for i in range(0,(~FeeIdLayerMask.L6&0xFF)+1,3)]
        for feeid in feeid_list:
            self._test_single_feeid(feeid)

class TestAaaSimSpeed(TestcaseBase):

    def test_sim_speed(self):
        self.sync() # Make sure connection with sim is present.
        sync_time_ar = []
        for _ in range(10):
            start = time.time()
            self.board.mmcm_gbtx_rxrdy_monitor.reset_all_counters(commitTransaction=False)
            self.sync()
            end = time.time()
            sync_time_ar.append(end - start)

        wait_time_ar = []
        for _ in range(10):
            start = time.time()
            self.board.wait(160, commitTransaction=False) # 1 us sim time
            self.sync()
            end = time.time()
            wait_time_ar.append(end - start)
        print(f"Sync time: {min(sync_time_ar):.4f} 1us wait time: {min(wait_time_ar) - min(sync_time_ar):.4f}")

    @unittest.skipIf(not USB_MASTER, "USB not available.")
    def test_usb_sim_speed(self):
        self.sync() # Make sure connection with sim is present.
        self.board_usb.read(1,1)
        sync_time_ar = []
        for _ in range(10):
            start = time.time()
            self.board_usb.mmcm_gbtx_rxrdy_monitor.reset_all_counters(commitTransaction=False)
            self.board_usb.read(1,1)
            end = time.time()
            sync_time_ar.append(end - start)

        wait_time_ar = []
        for _ in range(10):
            start = time.time()
            self.board_usb.wait(160, commitTransaction=False) # 1 us sim time
            self.board_usb.read(1,1)
            end = time.time()
            wait_time_ar.append(end - start)
        print(f"Sync time: {min(sync_time_ar):.4f} 1us wait time: {min(wait_time_ar) - min(sync_time_ar):.4f}")


if __name__ == '__main__':

    timeout = 1

    # setup logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    log_file = "Xcku_regression.log"
    log_file_errors = "Xcku_regression_errors.log"

    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)

    fh2 = logging.FileHandler(log_file_errors)
    fh2.setLevel(logging.ERROR)

    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    formatter_ch = logging.Formatter(
        "%(name)s - %(levelname)s - %(message)s")

    fh.setFormatter(formatter)
    fh2.setFormatter(formatter)
    ch.setFormatter(formatter_ch)

    logger.addHandler(fh)
    logger.addHandler(fh2)
    logger.addHandler(ch)

    try:
        if SIMULATION:
            if SIMULATE_CRU:
                sim_serv = simulation_if.SimulationServer()
                gbt0_sim = simulation_if.GbtCruGbtxBridge(server=sim_serv.server)
                comm0 = simulation_if.UsbCommSim()
                if USE_ALL_UPLINKS:
                    raise NotImplementedError
                sim_serv.start()
            else:
                comm0 = simulation_if.Wb2GbtxComm(gbtxnum=0, create_raw_data_files=DUMP_DP2_DATA)
                gbtx0_sim_comm = comm0
                if USE_ALL_UPLINKS:
                    comm1 = simulation_if.Wb2GbtxComm(gbtxnum=1, create_raw_data_files=DUMP_DP2_DATA)
                comm2 = simulation_if.Wb2GbtxComm(gbtxnum=2, create_raw_data_files=DUMP_DP2_DATA)
                gbtx2_sim_comm = comm2
            if USB_MASTER:
                comm_usb = simulation_if.UsbCommSim()
            else:
                comm_usb=comm0

            if USE_CAN:
                can_comm = CanHlpComm(can_if=CANBUS_SIM_IF,
                                      timeout_ms=simulation_if.GLOBAL_READ_TIMEOUT*1000,
                                      sim=True)
                can_comm.set_node_id(CAN_NODE_ID)

            sim_comm = simulation_if.SimComm()

        else:
            serv = usb_communication.UsbCommServer(
                executable=os.path.join(script_path,
                "../../modules/usb_if/software/usb_comm_server/build/usb_comm"),
                serial=SERIAL_CRU)
            serv.start()
            time.sleep(0.5)
            comm0 = usb_communication.NetUsbComm(Timeout=timeout)
            if USB_MASTER:
                comm_usb = usb_communication.PyUsbComm(serialNr=SERIAL_RDO)
            else:
                comm_usb = comm0

            if USE_CAN:
                can_comm = CanHlpComm(can_if=CANBUS_HW_IF, timeout_ms=5000, sim=False)
                can_comm.set_node_id(CAN_NODE_ID)


        # TODO: Add LTU control


        comm0_prefetch = communication.PrefetchCommunication(comm0)
        comm0_prefetch.enable_rderr_exception()

        comm_usb_prefetch = communication.PrefetchCommunication(comm_usb)
        comm_usb_prefetch.enable_rderr_exception()

        cru0Global = ru_board.RUv0_CRU(comm0_prefetch,
                                  sca_is_on_ruv1=False,
                                  sca_is_on_ruv2_0=True)
        if USE_ALL_UPLINKS:
            cru1Global = ru_board.RUv0_CRU(comm1,
                                      sca_is_on_ruv1=False,
                                      sca_is_on_ruv2_0=True)
            cru2Global = ru_board.RUv0_CRU(comm2,
                                      sca_is_on_ruv1=False,
                                      sca_is_on_ruv2_0=True)

        if USE_LTU: # TODO: Define interface for LTU
            ltuGlobal = ru_board.RUv0_CRU(comm2,
                                      sca_is_on_ruv1=False,
                                      sca_is_on_ruv2_0=True)
        else:
            ltuGlobal = cru0Global

        boardGlobal = ru_board.Xcku(comm0_prefetch,
                                    cru0Global,
                                    ru_main_revision=RU_MAIN_REVISION,
                                    ru_minor_revision=RU_MINOR_REVISION,
                                    transition_board_version=RU_TRANSITION_BOARD_VERSION,
                                    layer=LAYER,
                                    power_board_version=power_unit.PowerUnitVersion.PROTOTYPE,
                                    power_board_filter_50Hz_ac_power_mains_frequency=True,
                                    powerunit_resistance_offset_pt100=POWERUNIT_RESISTANCE_OFFSET_PT100,
                                    powerunit_1_offset_avdd=POWERUNIT_1_OFFSET_AVDD,
                                    powerunit_1_offset_dvdd=POWERUNIT_1_OFFSET_DVDD,
                                    powerunit_2_offset_avdd=POWERUNIT_2_OFFSET_AVDD,
                                    powerunit_2_offset_dvdd=POWERUNIT_2_OFFSET_DVDD)

        if SIMULATE_CRU:
            cru0Global.write(Ruv0CruModuleid.GBT_FPGA, 2, 0)
            cru0Global.write(Ruv0CruModuleid.GBT_FPGA, 0, 1)
            cru0Global.write(Ruv0CruModuleid.GBT_FPGA, 0, 0x60)
        if USB_MASTER:
            boardGlobal_usb = ru_board.Xcku(comm_usb_prefetch,
                                            cru0Global,
                                            ru_main_revision=RU_MAIN_REVISION,
                                            ru_minor_revision=RU_MINOR_REVISION,
                                            transition_board_version=RU_TRANSITION_BOARD_VERSION,
                                            layer=LAYER,
                                            power_board_version=power_unit.PowerUnitVersion.PROTOTYPE,
                                            power_board_filter_50Hz_ac_power_mains_frequency=True,
                                            powerunit_resistance_offset_pt100=POWERUNIT_RESISTANCE_OFFSET_PT100,
                                            powerunit_1_offset_avdd=POWERUNIT_1_OFFSET_AVDD,
                                            powerunit_1_offset_dvdd=POWERUNIT_1_OFFSET_DVDD,
                                            powerunit_2_offset_avdd=POWERUNIT_2_OFFSET_AVDD,
                                            powerunit_2_offset_dvdd=POWERUNIT_2_OFFSET_DVDD)
        if USE_CAN:
            boardGlobal_can = ru_board.Xcku(can_comm,
                                            None,
                                            ru_main_revision=RU_MAIN_REVISION,
                                            ru_minor_revision=RU_MINOR_REVISION,
                                            transition_board_version=RU_TRANSITION_BOARD_VERSION,
                                            layer=LAYER,
                                            power_board_version=power_unit.PowerUnitVersion.PROTOTYPE,
                                            power_board_filter_50Hz_ac_power_mains_frequency=True,
                                            powerunit_resistance_offset_pt100=POWERUNIT_RESISTANCE_OFFSET_PT100,
                                            powerunit_1_offset_avdd=POWERUNIT_1_OFFSET_AVDD,
                                            powerunit_1_offset_dvdd=POWERUNIT_1_OFFSET_DVDD,
                                            powerunit_2_offset_avdd=POWERUNIT_2_OFFSET_AVDD,
                                            powerunit_2_offset_dvdd=POWERUNIT_2_OFFSET_DVDD)

        connection_lut = {sensor: CONNECTORS[0] for sensor in SENSOR_LIST}
        connection_lut[0x0F]=CONNECTORS[0]
        boardGlobal.set_chip2connector_lut(connection_lut)

    # general setup
        if SIMULATION:
            sim_comm.set_dipswitches(feeid=CAN_NODE_ID)
        boardGlobal.gth.set_transceivers(GTH_LIST)
        boardGlobal.datapath_monitor_ib.set_lanes(GTH_LIST)
        boardGlobal.gpio.set_transceivers(GPIO_LIST)
        boardGlobal.datapath_monitor_ob.set_lanes(GPIO_LIST)
        boardGlobal.alpide_control.enable_dclk()
    except:
        traceback.print_exc(file=sys.stdout)
        tearDownModule()
        sys.exit(1)

    try:
        logger.info("Start Test")
        unittest.main(verbosity=2, exit=True)
    except KeyboardInterrupt:
        traceback.print_exc(file=sys.stdout)
        tearDownModule()
        sys.exit(1)
    print("End test")
