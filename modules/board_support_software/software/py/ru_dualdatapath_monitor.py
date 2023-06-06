"""Dual Datapath monitor modules for Reading out Lane counters"""

import collections
import collections.abc
import logging


class DatapathMonitorDual():
    """Abstract class to implement a dual monitor for split lane and split counter"""
    lanes = None
    counter_mapping = None

    def __init__(self, master_monitor, slave_monitor, name):
        self.moduleid = -1
        self.master_monitor = master_monitor
        self.slave_monitor = slave_monitor
        self.slave_monitor.set_as_slave_monitor()
        self.name = name
        self.logger = logging.getLogger(f"Module {self.name}")


    def set_lanes(self, lanes):
        """Sets the lanes internally"""
        self.lanes = lanes

    def get_lanes(self):
        return self.lanes

    def reset_all_counters(self,commitTransaction=True):
        """Reset all counters (master=>slave)"""
        self.master_monitor.reset_all_counters(commitTransaction)

    def latch_counters(self,commitTransaction=False):
        """Latches values into counters (master=>slave)"""
        self.master_monitor.latch_all_counters(commitTransaction)

    def reset_lane_counters(self,lane,commitTransaction=True):
        raise NotImplementedError

    def read_counters(self,lanes=None,counters=None):
        raise NotImplementedError

    def read_all_counters(self):
        """Read all counters of monitor"""
        return self.read_counters()

    def dump_config(self):
        """Dump the modules state and configuration as a string"""
        config_str = self.master_monitor.dump_config()
        config_str += self.slave_monitor.dump_config()
        return config_str


class DatapathMonitorDualSplitAtLane(DatapathMonitorDual):
    """Monitor for dual counters split at lane level:
    Master monitor all counters for the first half of the lanes
    Slave monitor all counters for the second half of the lanes
    As monitors are wired together, resetting/latching the master will also reset/latch the slave
    """
    def __init__(self,
                 master_monitor, slave_monitor,
                 name="Datapathmon_GPIO"):
        super(DatapathMonitorDualSplitAtLane, self).__init__(master_monitor,slave_monitor, name)
        self.lanes = master_monitor.get_lanes() + slave_monitor.get_lanes()
        self.counter_mapping = self.master_monitor.counter_mapping
        assert self.counter_mapping == self.master_monitor.counter_mapping == self.slave_monitor.counter_mapping
        self.logger.debug(f"counter_mapping: {self.counter_mapping}")

    def set_lanes(self,lanes):
        super(DatapathMonitorDualSplitAtLane, self).set_lanes(lanes)
        for dpmon,lanes_split in self._split_lane_access(lanes).items():
            dpmon.set_lanes(lanes_split)

    def _split_lane_access(self,lanes):
        parts = {self.master_monitor:list(),
                 self.slave_monitor:list()}
        for lane in lanes:
            if lane in self.master_monitor.get_default_lanes():
                parts[self.master_monitor].append(lane)
            else:
                parts[self.slave_monitor].append(lane)
        return parts

    def reset_lane_counters(self,lane,commitTransaction=True):
        """Reset all counters for lane i"""
        assert lane in self.lanes, "Lane not in range"
        parts = self._split_lane_access([lane])
        for mon,lanes in parts.items():
            for lane_idx in lanes:
                for i in range(mon.nr_counter_regs*lane_idx,mon.nr_counter_regs*lane_idx+mon.nr_counter_regs):
                    mon.write(i,1,commitTransaction=False)
        if commitTransaction:
            self.master_monitor.flush()

    def read_counters(self,lanes=None,counters=None):
        """Read Counters(array) from lanes(array)
        Returns a list (per lane) of OrderedDict() {counter_name:counter_value}
        """
        if lanes is None:
            lanes = self.lanes
        if not isinstance(lanes,collections.abc.Iterable):
            lanes = [ lanes ]

        parts = self._split_lane_access(lanes)
        results = []

        for mon,lane_parts in parts.items():
            self.logger.debug(f'{mon.name}: counters {counters}, lane_parts {lane_parts}')
            results.extend(mon.read_counters(lane_parts,counters))
        return results

    def read_counter(self,lanes=None,counter=None):
        if lanes is None:
            lanes = self.lanes
        if not isinstance(lanes,collections.abc.Iterable):
            lanes = [ lanes ]

        results = self.read_counters(lanes,[counter])
        results_reduced = [l[counter] for l in results]
        if(len(results_reduced) == 1):
            return results_reduced[0]
        else:
            return results_reduced


class DatapathMonitorDualSplitCounters(DatapathMonitorDual):
    """Monitor for dual counters split at counter level
    Master monitor contains certain counters for all the lanes
    Slave monitor contains different counters for all the lanes
    As monitors are wired together, resetting/latching the master will also reset/latch the slave
    """
    def __init__(self,
                 master_monitor, slave_monitor,
                 name="DualDatapathmon_GTH"):
        super(DatapathMonitorDualSplitCounters, self).__init__(master_monitor,slave_monitor,name)
        assert master_monitor.get_lanes() == slave_monitor.get_lanes()
        self.lanes = self.master_monitor.get_lanes()
        self.counter_mapping = self.master_monitor.counter_mapping + self.slave_monitor.counter_mapping
        self.logger.debug(f"counter_mapping: {self.counter_mapping}")

    def set_lanes(self,lanes):
        super(DatapathMonitorDualSplitCounters, self).set_lanes(lanes)
        for mon in [self.master_monitor, self.slave_monitor]:
            mon.set_lanes(lanes)

    def get_lanes(self):
        assert self.master_monitor.get_lanes() == self.slave_monitor.get_lanes() == self.lanes, f"master:\t{self.master_monitor.get_lanes()}\nslave:\t{self.slave_monitor.get_lanes()}\njoined:\t{self.get_lanes()}"
        return super(DatapathMonitorDualSplitCounters, self).get_lanes()

    def reset_lane_counters(self, lane, commitTransaction=True):
        """Reset all counters for lane i"""
        assert lane in self.lanes, "Lane not in range"
        for mon in [self.master_monitor, self.slave_monitor]:
            for i in range(mon.nr_counter_regs*lane,mon.nr_counter_regs*lane+mon.nr_counter_regs):
                mon.write(i,1,commitTransaction=False)
        if commitTransaction:
            self.master_monitor.flush()

    def _combine_counters(self, master_counters, slave_counters):
        """Combines the master and slave counters into a single dictionary

        in [{counters_master:value}], [{counters_slave:value}]
        out [{counter_<master|slave">:value}]"""
        assert len(master_counters)==len(slave_counters)
        assert self.master_monitor.lanes == self.slave_monitor.lanes
        out = master_counters
        for lane, counter_lane_dict in enumerate(out):
            for key, value in slave_counters[lane].items():
                assert key not in out[lane].keys(), f"{key} is a counter for master and slave monitor!"
                self.logger.debug(f'adding {key}:{value} to counter_lane_dict')
                counter_lane_dict[key] = value
        return out

    def _split_counters(self, counters):
        """Splits the list of counters between the master and slave monitor counters"""
        counters_master = []
        counters_slave = []

        for counter in counters:
            if counter in self.master_monitor.counter_mapping:
                counters_master.append(counter)
            elif counter in self.slave_monitor.counter_mapping:
                counters_slave.append(counter)
            else:
                raise RuntimeError(f"{counter} is not a valid counter.\nAllowed values: {self.master_monitor.counter_mapping+self.slave_monitor.counter_mapping}")
        return counters_master, counters_slave

    def read_counters(self, lanes=None, counters=None):
        """Read Counters(array) from lanes(array)"""
        if lanes is None:
            lanes = self.lanes
        if not isinstance(lanes,collections.abc.Iterable):
            lanes = [ lanes ]
        if counters is None:
            c_master = None
            c_slave = None
        else:
            if not isinstance(counters,(list,tuple)):
                counters = [ counters ]
            self.logger.debug(f'counters: {counters}')
            c_master, c_slave = self._split_counters(counters)
            self.logger.debug(f'c_master: {c_master}, c_slave: {c_slave}')

        master_counters = [collections.OrderedDict() for i in self.lanes]
        slave_counters = [collections.OrderedDict() for i in self.lanes]
        master_latched = False
        if c_master != []: # e.g. when only slave counters are requested
            master_counters = self.master_monitor.read_counters(lanes,c_master)
            self.logger.debug(f"master: {master_counters}")
            master_latched = True
        if c_slave != []: # e.g. when only master counters are requested
            slave_counters = self.slave_monitor.read_counters(lanes,c_slave, force_latch=not master_latched)
            self.logger.debug(f"slave: {slave_counters}")
        return self._combine_counters(master_counters, slave_counters)

    def read_counter(self,lanes=None,counter=None):
        assert counter is not None, "Please select a counter to read"
        if lanes is None:
            lanes = self.lanes
        if not isinstance(lanes,collections.abc.Iterable):
            lanes = [ lanes ]

        results = self.read_counters(lanes,[counter])
        results_reduced = [l[counter] for l in results]
        if(len(results_reduced) == 1):
            return results_reduced[0]
        else:
            return results_reduced
