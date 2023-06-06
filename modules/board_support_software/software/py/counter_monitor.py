"""Implements the control for the counter_monitor wishbone slave"""
import collections

from enum import IntEnum

from wishbone_module import WishboneModule
from communication import WishboneReadError

class WsCounterMonitorAddress(IntEnum):
    LATCH_COUNTERS = 0x00
    RESET_COUNTERS = 0x01

class WsCounterMonitor(WishboneModule):
    """Parent class for counter monitor slaves that use the counter_monitor.vhd WB slave"""

    def __init__(self, moduleid, name, board_obj, registers, pulsed=True, bit_mapped_reset=False, bit_mapped_latch=False):
        super(WsCounterMonitor, self).__init__(moduleid=moduleid, name=name, board_obj=board_obj)
        self.LATCH_CMD = 0x0001
        self.RESET_ONE_CMD = 0xF000
        self.RESET_ALL_CMD = 0xFFFF
        assert registers.LATCH_COUNTERS == WsCounterMonitorAddress.LATCH_COUNTERS
        assert registers.RESET_COUNTERS == WsCounterMonitorAddress.RESET_COUNTERS
        self.registers = registers
        self.counter_offset = 2
        self.counters, self.counters_32b, self.counters_8b_low, self.counters_8b_high = self._create_counter_lists()
        self._is_master_monitor = True # overridden when associated to a master into a slave_monitor
        # Compatibility setting for modules not yet converted to true counter_monitor
        self.pulsed = pulsed # Does RESET/LATCH return to 0 after setting, or do you need to toggle the bits
        self.bit_mapped_reset = bit_mapped_reset # Is the monitor using the bit mapping to reset individual counters or the integer value to reset a specific one
        self.bit_mapped_latch = bit_mapped_latch # Is the monitor using the bit mapping to latch individual counters or the integer value to latch a specific one
        self.LATCH_ALL_BIT_MAPPED_CMD = 0xFFFF # Latch all for bit mapped

    def set_as_master_monitor(self):
        self._is_master_monitor = True

    def set_as_slave_monitor(self):
        self._is_master_monitor = False

    def _create_counter_lists(self):
        counters = []
        counters_32b = collections.OrderedDict()
        counters_8b_low = collections.OrderedDict()
        counters_8b_high = collections.OrderedDict()
        for reg in [reg for reg in self.registers if ((reg != self.registers.LATCH_COUNTERS) and
                                                      (reg != self.registers.RESET_COUNTERS) and
                                                      (not reg.name.endswith('_MSB')) and
                                                      (not reg.name.endswith('_HIGH')) and
                                                      (not reg.name.startswith('DEAD_')))]:
            split = reg.name.find('_X_')
            if (reg.name.endswith('_LSB')):
                basename = reg.name[:-1*len('_LSB')]
                counters.append(basename)
                counters_32b[basename] = (basename + '_LSB', basename + '_MSB')
                self.logger.debug(f'strip lsb: {reg.name} -> {basename}')
            elif (reg.name.endswith('_LOW')):
                basename = reg.name[:-1*len('_LOW')]
                counters.append(basename)
                counters_32b[basename] = (basename + '_LOW', basename + '_HIGH')
                self.logger.debug(f'strip low: {reg.name} -> {basename}')
            elif split >= 0:
                counters.append(reg.name[:split])
                counters.append(reg.name[split+len('_X_'):])
                counters_8b_high[reg.name[:split]] = reg.name
                counters_8b_low[reg.name[split+len('_X_'):]] = reg.name
            else:
                counters.append(reg.name)
        return counters, counters_32b, counters_8b_low, counters_8b_high

    def _to_register_mapping(self, counters):
        if isinstance(counters, str):
            counters = [ counters ]
        mapped = []
        for c in counters:
            assert c in self.counters, f"Counter {c} not in counter mapping"
            if c in self.counters_32b:
                mapped.extend(self.counters_32b[c])
            elif c in self.counters_8b_low:
                mapped.append(self.counters_8b_low[c])
            elif c in self.counters_8b_high:
                mapped.append(self.counters_8b_high[c])
            else:
                mapped.append(c)
        mapped = list(dict.fromkeys(mapped)) # Remove duplicates
        return [self.registers[x] for x in mapped] # Return enum list

    def _process_counters(self, counters, wb_reg_data):
        if isinstance(counters, str):
            counters = [ counters ]
        ret = collections.OrderedDict()
        for c in counters:
            if c in self.counters_32b:
                ret[c] = wb_reg_data[self.counters_32b[c][0]] | \
                        (wb_reg_data[self.counters_32b[c][1]] << 16)
            elif c in self.counters_8b_low:
                ret[c] = wb_reg_data[self.counters_8b_low[c]] & 0xff
            elif c in self.counters_8b_high:
                ret[c] = (wb_reg_data[self.counters_8b_high[c]] >> 8) & 0xff
            else:
                ret[c] = wb_reg_data[c]
        return ret

    def reset_counter(self, register, commitTransaction=True):
        """Resets counter specified in 'register'"""
        if self.bit_mapped_reset:
            data = register
        else:
            assert (register | 0xff) == 0xff
            data = register | self.RESET_ONE_CMD
        self.write(WsCounterMonitorAddress.RESET_COUNTERS, data, commitTransaction=commitTransaction)
        if not self.pulsed:
            self.firmware_wait(5, commitTransaction=commitTransaction) # Makes sure the length of the pulse is passed properly to a 40MHz domain
            self.write(WsCounterMonitorAddress.RESET_COUNTERS, 0, commitTransaction=commitTransaction)

    def reset_all_counters(self, commitTransaction=True):
        """Resets all counters"""
        self.write(WsCounterMonitorAddress.RESET_COUNTERS, self.RESET_ALL_CMD, commitTransaction=commitTransaction)
        if not self.pulsed:
            self.firmware_wait(5, commitTransaction=commitTransaction) # Makes sure the length of the pulse is passed properly to a 40MHz domain
            self.write(WsCounterMonitorAddress.RESET_COUNTERS, 0, commitTransaction=commitTransaction)

    def latch_all_counters(self, commitTransaction=True):
        """Latches values of all counters into WB register"""
        if self.bit_mapped_latch:
            self.write(WsCounterMonitorAddress.LATCH_COUNTERS, self.LATCH_ALL_BIT_MAPPED_CMD, commitTransaction=commitTransaction)
        else:
            self.write(WsCounterMonitorAddress.LATCH_COUNTERS, self.LATCH_CMD, commitTransaction=commitTransaction)
        if not self.pulsed:
            self.firmware_wait(5, commitTransaction=commitTransaction) # Makes sure the length of the pulse is passed properly to a 40MHz domain
            self.write(WsCounterMonitorAddress.LATCH_COUNTERS, 0, commitTransaction=commitTransaction)

    def _get_counters(self, addresses=None, latch_first=False, reset_after=False, commitTransaction=True):
        """Gets the values of the counters in a counter monitor"""
        if addresses is None or addresses==self.registers:
            addresses = []
            for register in self.registers:
                if register not in [WsCounterMonitorAddress.RESET_COUNTERS, WsCounterMonitorAddress.LATCH_COUNTERS]:
                    addresses.append(register)
        else:
            for address in addresses:
                assert address in self.registers, f"Address {address} not in address table"
                assert address not in [WsCounterMonitorAddress.RESET_COUNTERS, WsCounterMonitorAddress.LATCH_COUNTERS], "Can't read from address {address}"
        if latch_first:
            self.latch_all_counters(commitTransaction=False)
        for address in addresses:
            self.read(address, commitTransaction=False)
        if reset_after:
            self.reset_all_counters(commitTransaction=False)
        ret = collections.OrderedDict()
        if commitTransaction:
            results = self.board.flush_and_read_results(expected_length=len(addresses))
            for i, address in enumerate(addresses):
                res_moduleid = ((results[i][0] >> 8) & 0x7f)
                res_address = (results[i][0] & 0xff)
                assert res_moduleid == self.moduleid, \
                    f"Requested to read module {self.moduleid}, but got result for module {res_moduleid}, iteration {i}"
                assert res_address == address, \
                    f"Requested to read address {address}, but got result for address {res_address}, iteration {i}"
                ret[self.registers(address).name] = results[i][1]
        return ret

    def read_counters(self, counters=None, latch_first=True, reset_after=False, commitTransaction=True):
        """Read all counters in a counter monitor"""
        if counters is None:
            counters = self.counters
        wb_regs = self._to_register_mapping(counters)
        results = self._get_counters(addresses=wb_regs, latch_first=latch_first, reset_after=reset_after, commitTransaction=commitTransaction)
        ret = collections.OrderedDict()
        if commitTransaction:
            ret = self._process_counters(counters, results)
        return ret

    def read_counter(self, counter, latch_first=True, reset_after=False, commitTransaction=True):
        """Reads a single counter, returns only the value"""
        assert isinstance(counter, str), "Read counter is only for a single counter"
        ret = self.read_counters(counters=counter, latch_first=latch_first, reset_after=reset_after, commitTransaction=commitTransaction)
        return list(ret.values())[0]

    def dump_config(self):
        """Dump the modules state and configuration as a string"""
        config_str = f"--- {self.name} module ---\n"
        config_str += f"    - {WsCounterMonitorAddress.RESET_COUNTERS.name} : Write only\n"
        config_str += f"    - {WsCounterMonitorAddress.LATCH_COUNTERS.name} : Write only\n"
        self.latch_all_counters(commitTransaction=False)
        self.board.comm.disable_rderr_exception()
        for address in self.registers:
            if address not in [WsCounterMonitorAddress.RESET_COUNTERS, WsCounterMonitorAddress.LATCH_COUNTERS]:
                try:
                    name = address.name
                    value = self.read(address.value)
                    config_str += f"    - {name} : {value:#04X}\n"
                except WishboneReadError:
                    config_str += "    - {0} : FAILED\n".format(name)
        self.board.comm.enable_rderr_exception()
        return config_str
