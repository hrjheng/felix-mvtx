"""Datapath monitor module for Reading out Lane counters"""

import collections
import collections.abc
from enum import IntEnum, unique
from counter_monitor import WsCounterMonitor
from communication import WishboneReadError


class FrontendMonitor(WsCounterMonitor):
    """Monitor for Frontend status counters"""
    def __init__(self, name, registers, moduleid, board_obj, lanes,
                 wb_register_mapping, counter_mapping, counter_order, counter_transform,
                 offset=0):
        """Initialises the module

        # WB slave general
        name:      string,  used for logger
        registers: IntEnum, registers mapping
        moduleid:  Int,     Identifier of the wishbone module
        board_obj  Xcku,    Readout Unit main FPGA board object

        # Frontend monitor general
        lanes      Int,     Number of lanes
        offset     Int,     Lane offset in case of split counter per lane

        # Detailed memory mapping
        wb_register_mapping: list, list of register (string with name of register) per lane
        counter_mapping:     list, list of counters (string with name of register) per lane.
                                    if <BASENAME>{_LOW|_LSB|_HIGH|_MSB} register is present, add here only <BASENAME>
                                    if <COUNTB>_X_<COUNTA> register is present, add both <COUNTB> and <COUNTA>
        counter_order:       dict, {"<COUTNER_NAME>":[<LIST OF REGISTERS TO READ>]}
        counter_trasform:    dict, {"COUTNER_NAME": (lambda wb_regs: wb_regs[<REGISTER_TO_READ>] & <PART_OF_REGISTER_TO_USE> | ...)}

        """
        super(FrontendMonitor, self).__init__(moduleid=moduleid,board_obj=board_obj, name=name, registers=registers)
        self.COUNTER_OFFSET = 2
        self.lanes = lanes
        self.default_lanes = lanes[:]
        self.offset = offset
        self._construct_register_mapping(wb_register_mapping,
                                         counter_mapping,
                                         counter_order,
                                         counter_transform)

    def _construct_register_mapping(self,
                                    wb_register_mapping,
                                    counter_mapping,
                                    counter_order,
                                    counter_transform):
        """Assigns the correct register mapping to the module

        wb_register_mapping: list, list of register (string with name of register) per lane
        counter_mapping:     list, list of counters (string with name of register) per lane.
                                    if <BASENAME>{_LOW|_LSB|_HIGH|_MSB} register is present, add here only <BASENAME>
                                    if <COUNTB>_X_<COUNTA> register is present, add both <COUNTB> and <COUNTA>
        counter_order:       dict, {"<COUTNER_NAME>":[<LIST OF REGISTERS TO READ>]}
        counter_trasform:    dict, {"COUTNER_NAME": (lambda wb_regs: wb_regs[<REGISTER_TO_READ>] & <PART_OF_REGISTER_TO_USE> | ...)}
        """
        # list of registers per lane
        assert isinstance(wb_register_mapping,(list,tuple)), "wb_register_mapping should be a list or tuple"
        self.wb_register_mapping = wb_register_mapping
        self.nr_counter_regs = len(self.wb_register_mapping)
        self.nr_regs = self.nr_counter_regs * len(self.default_lanes)

        # list of counters per lane.
        # If a counter is present with a *_HIGH and *_LOW version, only add the basename here.
        # If a register contains two registers (<COUNTB>_X_<COUNTA>), then add both
        assert isinstance(counter_mapping,(list,tuple)), "counter_mapping should be a list or tuple"
        self.counter_mapping = counter_mapping

        # Dict of counters per lane.
        # {"COUTNER_NAME":[<LIST OF REGISTERS TO READ>]}
        assert isinstance(counter_order,(dict)), "counter_order should be a list or tuple"
        for c in counter_order.keys():
            assert c in self.counter_mapping
        self.counter_order = counter_order

        # Dict of counters per lane.
        # Transformation to apply to the read registers
        # {"COUTNER_NAME": (lambda wb_regs: wb_regs[<REGISTER_TO_READ>] & <PART_OF_REGISTER_TO_USE> | ...)}
        for c in counter_transform.keys():
            assert c in self.counter_mapping
        assert isinstance(counter_order,(dict)), "counter_trasform should be a list or tuple"
        self.counter_transform = counter_transform

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
                       self.nr_counter_regs*self.get_lane_idx(lane)+self.nr_counter_regs + self.COUNTER_OFFSET):
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
        if not isinstance(counters,collections.abc.Iterable):
            counters = [ counters ]

        if self._is_master_monitor or force_latch:
            self.latch_all_counters(commitTransaction=False)
        registers = self._to_register_mapping(counters)
        offsets = [self.wb_register_mapping.index(reg) for reg in registers]
        for lane in lanes:
            self.logger.debug(f"lane: {lane}: {self.nr_counter_regs} * {self.get_lane_idx(lane)} + {self.COUNTER_OFFSET}")
            lane_idx = self.nr_counter_regs * self.get_lane_idx(lane) + self.COUNTER_OFFSET
            for offset in offsets:
                self.logger.debug(f"lane: {lane}: lane_idx {lane_idx} + offset {offset}")
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
            lane_idx = self.get_lane_idx(lane) # in module, i.e. in range(14)
            for address in self.registers:
                if address not in [self.registers.RESET_COUNTERS, self.registers.LATCH_COUNTERS]:
                    name = address.name
                    add = address.value + (len(self.registers)-self.COUNTER_OFFSET)*lane_idx
                    try:
                        value = self.read(add)
                        config_str += f"    - {name} : {value:#04X}\n"
                    except WishboneReadError:
                        config_str += f"    - {name} : FAILED\n"
        self.board.comm.enable_rderr_exception()
        return config_str
