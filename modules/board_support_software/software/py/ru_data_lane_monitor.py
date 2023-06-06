"""Datalane monitor module for Reading out Lane counters"""

import collections
import collections.abc
from enum import IntEnum, unique
from counter_monitor import WsCounterMonitor
from communication import WishboneReadError

@unique
class DatalaneMonitorAddress(IntEnum):
    """Memory mapping for the datalane_monitor"""
    LATCH_COUNTERS                         = 0
    RESET_COUNTERS                         = 1
    u8B10B_OOT                             = 2
    u8B10B_OOT_TOLERATED_LOW               = 3
    u8B10B_OOT_TOLERATED_HIGH              = 4
    u8B10B_OOT_IN_IDLE                     = 5
    PROTOCOL_ERROR                         = 6
    BUSY_EVENT                             = 7
    u8B10B_OOT_FATAL                       = 8
    BUSY_VIOLATION                         = 9
    DATA_OVERRUN_X_BCID_MISMATCH           = 10
    DETECTOR_TIMEOUT_X_LANE_FIFO_OVERFLOW  = 11
    RATE_OCCUPANCY_LIMIT                   = 12
    LANE_FIFO_START_LOW                    = 13
    LANE_FIFO_START_HIGH                   = 14
    LANE_FIFO_STOP_LOW                     = 15
    LANE_FIFO_STOP_HIGH                    = 16
    LANE_FIFO_ERROR_X_LANE_TIMEOUT         = 17


class DataLaneMonitor(WsCounterMonitor):
    wb_register_mapping = [
        "u8B10B_OOT",
        "u8B10B_OOT_TOLERATED_LOW",
        "u8B10B_OOT_TOLERATED_HIGH",
        "u8B10B_OOT_IN_IDLE",
        "PROTOCOL_ERROR",
        "BUSY_EVENT",
        "u8B10B_OOT_FATAL",
        "BUSY_VIOLATION",
        "DATA_OVERRUN_X_BCID_MISMATCH",
        "DETECTOR_TIMEOUT_X_LANE_FIFO_OVERFLOW",
        "RATE_OCCUPANCY_LIMIT",
        "LANE_FIFO_START_LOW",
        "LANE_FIFO_START_HIGH",
        "LANE_FIFO_STOP_LOW",
        "LANE_FIFO_STOP_HIGH",
        "LANE_FIFO_ERROR_X_LANE_TIMEOUT"
    ]
    nr_counter_regs = len(wb_register_mapping)

    """Monitor for Datalane status counters"""
    def __init__(self, moduleid,board_obj, lanes, offset=0):
        super(DataLaneMonitor, self).__init__(moduleid=moduleid,board_obj=board_obj,name="Datalane Monitor", registers=DatalaneMonitorAddress)

        self.COUNTER_OFFSET = 2

        self.lanes = lanes
        self.default_lanes = lanes[:]
        self.offset = offset

        self.nr_regs = self.nr_counter_regs * len(self.default_lanes)

        self.counter_mapping = [
            "u8B10B_OOT",
            "u8B10B_OOT_FATAL",
            "u8B10B_OOT_TOLERATED",
            "u8B10B_OOT_IN_IDLE",
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
        ]

        self.counter_order = {
             # 32 bit
            "LANE_FIFO_START"      : ["LANE_FIFO_START_LOW","LANE_FIFO_START_HIGH"],
            "LANE_FIFO_STOP"       : ["LANE_FIFO_STOP_LOW","LANE_FIFO_STOP_HIGH"],
            "u8B10B_OOT_TOLERATED"  : ["u8B10B_OOT_TOLERATED_LOW","u8B10B_OOT_TOLERATED_HIGH"],
            # 8 bit high
            "DATA_OVERRUN"        : ["DATA_OVERRUN_X_BCID_MISMATCH"],
            "DETECTOR_TIMEOUT"     : ["DETECTOR_TIMEOUT_X_LANE_FIFO_OVERFLOW"],
            "LANE_FIFO_ERROR"      : ["LANE_FIFO_ERROR_X_LANE_TIMEOUT"],
            # 8 bit low
            "BCID_MISMATCH"        : ["DATA_OVERRUN_X_BCID_MISMATCH"],
            "LANE_FIFO_OVERFLOW"   : ["DETECTOR_TIMEOUT_X_LANE_FIFO_OVERFLOW"],
            "LANE_TIMEOUT"         : ["LANE_FIFO_ERROR_X_LANE_TIMEOUT"],
        }

        self.counter_transform = {
            # 32 bit
            "LANE_FIFO_START"      : (lambda wb_regs: wb_regs["LANE_FIFO_START_HIGH"] << 16 | wb_regs["LANE_FIFO_START_LOW"]),
            "LANE_FIFO_STOP"       : (lambda wb_regs: wb_regs["LANE_FIFO_STOP_HIGH"] << 16 | wb_regs["LANE_FIFO_STOP_LOW"]),
            "u8B10B_OOT_TOLERATED"  : (lambda wb_regs: wb_regs["u8B10B_OOT_TOLERATED_HIGH"] << 16 | wb_regs["u8B10B_OOT_TOLERATED_LOW"]),
            # 8 bit high
            "DATA_OVERRUN"        : (lambda wb_regs: (wb_regs["DATA_OVERRUN_X_BCID_MISMATCH"]>>8) & 0xFF),
            "DETECTOR_TIMEOUT"     : (lambda wb_regs: (wb_regs["DETECTOR_TIMEOUT_X_LANE_FIFO_OVERFLOW"]>>8) & 0xFF),
            "LANE_FIFO_ERROR"      : (lambda wb_regs: (wb_regs["LANE_FIFO_ERROR_X_LANE_TIMEOUT"]>>8) & 0xFF),
            # 8 bit low
            "BCID_MISMATCH"        : (lambda wb_regs: wb_regs["DATA_OVERRUN_X_BCID_MISMATCH"] & 0xFF),
            "LANE_FIFO_OVERFLOW"   : (lambda wb_regs: wb_regs["DETECTOR_TIMEOUT_X_LANE_FIFO_OVERFLOW"] & 0xFF),
            "LANE_TIMEOUT"         : (lambda wb_regs: wb_regs["LANE_FIFO_ERROR_X_LANE_TIMEOUT"] & 0xFF),
        }


    def set_lanes(self,lanes):
        self.lanes = lanes

    def get_lanes(self):
        return self.lanes

    def get_default_lanes(self):
        return self.default_lanes

    def _to_register_mapping(self,counters):
        mapped = []
        for c in counters:
            assert c in self.counter_mapping, "Counter {0} not in counter mapping".format(c)
            if c in self.counter_order:
                for sc in self.counter_order[c]:
                    if sc not in mapped:
                        mapped.append(sc)
            else:
                mapped.append(c)
        return mapped

    def _process_counters(self,wb_regs,counters):
        counters_combined = collections.OrderedDict()
        for c in counters:
            if c in self.counter_transform:
                counters_combined[c] = self.counter_transform[c](wb_regs)
            else:
                counters_combined[c] = wb_regs[c]
        return counters_combined

    def get_lane_idx(self,lane):
        return lane - self.offset

    def reset_lane_counters(self,lane,commitTransaction=True):
        """Reset all counters for lane i"""
        assert lane in self.lanes , "Lane not in range"
        for i in range(self.nr_counter_regs*self.get_lane_idx(lane) + self.COUNTER_OFFSET,
                       self.nr_counter_regs*self.get_lane_idx(lane) + self.nr_counter_regs + self.COUNTER_OFFSET):
            reset_cmd = i & 0xFF
            self.reset_counter(reset_cmd, commitTransaction=False)
        if commitTransaction:
            self.flush()

    def read_counters(self,lanes=None,counters=None, force_latch=False):
        """Read Counters(array) from lanes(array)"""
        if lanes is None:
            lanes = self.lanes
        if not isinstance(lanes,collections.abc.Iterable):
            lanes = [ lanes ]
        if counters is None:
            counters = self.counter_mapping
        if isinstance(counters, str):
            counters = [ counters ]

        if self._is_master_monitor or force_latch:
            self.latch_all_counters(commitTransaction=False)
        registers = self._to_register_mapping(counters)
        offsets = [self.wb_register_mapping.index(reg) for reg in registers]
        for lane in lanes:
            lane_idx = self.nr_counter_regs * self.get_lane_idx(lane) + self.COUNTER_OFFSET
            for offset in offsets:
                self.read(lane_idx + offset, False)
        values = self.read_all()

        results = []
        nr_registers = len(registers)
        for idx,lane in enumerate(lanes):
            lane_regs = collections.OrderedDict()
            for reg_idx,reg in enumerate(registers):
                lane_regs[reg] = values[idx*nr_registers + reg_idx]
            results.append(self._process_counters(lane_regs,counters))

        return results

    def read_counter(self,lanes,counter):
        results = self.read_counters(lanes,[counter])
        results_reduced = [l[counter] for l in results]
        if(len(results_reduced) == 1):
            return results_reduced[0]
        else:
            return results_reduced

    def read_all_counters(self):
        """Read all counters of monitor"""
        return self.read_counters()

    def dump_config(self):
        """Dump the modules state and configuration as a string"""
        config_str = f"--- {self.name} module ---\n"
        config_str += f"    - {self.registers.RESET_COUNTERS.name} : Write only\n"
        config_str += f"    - {self.registers.LATCH_COUNTERS.name} : Write only\n"
        self.board.comm.disable_rderr_exception()
        self.latch_all_counters(commitTransaction=False)
        for lane in self.default_lanes:
            config_str += f"--- LANE {lane} ---\n"
            lane_idx = self.get_lane_idx(lane)  # in module, i.e. in range(14)
            for address in self.registers:
                if address not in [self.registers.RESET_COUNTERS, self.registers.LATCH_COUNTERS]:
                    name = address.name
                    add = address.value + (len(self.registers) - self.COUNTER_OFFSET) * lane_idx
                    try:
                        value = self.read(add)
                        config_str += f"    - {name} : {value:#04X}\n"
                    except WishboneReadError:
                        config_str += f"    - {name} : FAILED\n"
        self.board.comm.enable_rderr_exception()
        return config_str
