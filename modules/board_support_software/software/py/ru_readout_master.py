# coding: utf-8

"""file implementing the control for the readout_master wishbone slave"""

import warnings

from collections import OrderedDict
from enum import IntEnum, unique

from wishbone_module import WishboneModule

@unique
class ReadoutMasterAddress(IntEnum):
    """memory mapping for the readout_master got from readout_master_wishbone_pkg.vhd"""
    IB_ENABLED_LANES      = 0
    OB_ENABLED_LANES_LSB  = 1
    OB_ENABLED_LANES_MSB  = 2
    MAX_NOK_LANES         = 3
    IB_FAULTY_LANES       = 4
    OB_FAULTY_LANES_LSB   = 5
    OB_FAULTY_LANES_MSB   = 6
    STATUS                = 7
    IB_NOK_LANES          = 8
    OB_NOK_LANES_LSB      = 9
    OB_NOK_LANES_MSB      = 10


@unique
class StatusBitMapping(IntEnum):
    """Bit mapping for the status register
    From  readout_master_wishbone_pkg.vhd"""
    FERO_OKAY                = 0
    NO_PENDING_DETECTOR_DATA = 1
    NO_PENDING_LANE_DATA     = 2


class ReadoutMaster(WishboneModule):
    """wishbone slave used to configure the readout masters"""

    def __init__(self, moduleid, board_obj):
        super(ReadoutMaster, self).__init__(moduleid=moduleid, board_obj=board_obj,
                                            name="readout master")
        self.addr_list = ReadoutMasterAddress

    def set_ib_enabled_lanes(self, lanes, commitTransaction=True):
        """Sets the lanes enabled for the IB"""
        assert lanes | 0xFFFF == 0xFFFF
        self.write(self.addr_list.IB_ENABLED_LANES, lanes, commitTransaction=commitTransaction)

    def get_ib_enabled_lanes(self, commitTransaction=True):
        """Gets the lanes enabled for the IB"""
        self._request_ib_enabled_lanes()
        if commitTransaction:
            results = self.board.flush_and_read_results(expected_length=1)
            return self._format_ib_enabled_lanes(results)
        else:
            return None

    def _request_ib_enabled_lanes(self):
        """WB read request"""
        self.read(self.addr_list.IB_ENABLED_LANES, commitTransaction=False)

    def _format_ib_enabled_lanes(self, results):
        assert len(results) == 1
        ret = 0
        for i, address in enumerate([self.addr_list.IB_ENABLED_LANES]):
            assert ((results[i][0] >> 8) & 0x7f) == self.moduleid, \
                    "Requested to read module {0}, but got result for module {1}, iteration {2}".format(self.moduleid, ((results[i][0] >> 8) & 0x7f), i)
            assert (results[i][0] & 0xff) == address.value, \
                    "Requested to read address {0}, but got result for address {1}, iteration {2}".format(address.value, (results[i][0] & 0xff), i)
            ret = results[i][1]
        return ret

    def set_ob_enabled_lanes(self, lanes, commitTransaction=True):
        """Sets the lanes enabled for the OB"""
        assert lanes | 0xFFF_FFFF == 0xFFF_FFFF
        self.write(self.addr_list.OB_ENABLED_LANES_LSB, (lanes>>0)  & 0xFFFF, commitTransaction=False)
        self.write(self.addr_list.OB_ENABLED_LANES_MSB, (lanes>>16) & 0xFFFF, commitTransaction=commitTransaction)

    def get_ob_enabled_lanes(self, commitTransaction=True):
        """Gets the lanes enabled for the OB"""
        self._request_ob_enabled_lanes()
        if commitTransaction:
            results = self.board.flush_and_read_results(expected_length=2)
            return self._format_ob_enabled_lanes(results)
        else:
            return None

    def _request_ob_enabled_lanes(self):
        """WB read request"""
        for address in [self.addr_list.OB_ENABLED_LANES_MSB, self.addr_list.OB_ENABLED_LANES_LSB]:
            self.read(address, commitTransaction=False)

    def _format_ob_enabled_lanes(self, results):
        assert len(results) == 2
        ret = 0
        for i, address in enumerate([self.addr_list.OB_ENABLED_LANES_MSB, self.addr_list.OB_ENABLED_LANES_LSB]):
            assert ((results[i][0] >> 8) & 0x7f) == self.moduleid, \
                    "Requested to read module {0}, but got result for module {1}, iteration {2}".format(self.moduleid, ((results[i][0] >> 8) & 0x7f), i)
            assert (results[i][0] & 0xff) == address.value, \
                    "Requested to read address {0}, but got result for address {1}, iteration {2}".format(address.value, (results[i][0] & 0xff), i)
            ret = results[i][1] | ret<<16
        return ret

    def set_max_nok_lanes_number(self, value, commitTransaction=True):
        """Sets the max number of lanes to be in error to result in stop of triggers sent"""
        assert value in range(self.board.LANES_OB+1), f"Invalid value {value} not in range({self.board.LANES_OB+1})"
        self.write(self.addr_list.MAX_NOK_LANES, value, commitTransaction=commitTransaction)

    def get_max_nok_lanes_number(self, commitTransaction=True):
        """Gets the max number of lanes to be in error to result in stop of triggers sent"""
        warnings.warn("Functionality is not implemented in RTL: whatever you read here has no effect", RuntimeWarning)
        self._request_max_nok_lanes_number()
        if commitTransaction:
            results = self.board.flush_and_read_results(expected_length=1)
            return self._format_max_nok_lanes_number(results)
        else:
            return None

    def _request_max_nok_lanes_number(self):
        """WB read request"""
        self.read(self.addr_list.MAX_NOK_LANES, commitTransaction=False)

    def _format_max_nok_lanes_number(self, results):
        assert len(results) == 1
        ret = 0
        for i, address in enumerate([self.addr_list.MAX_NOK_LANES]):
            assert ((results[i][0] >> 8) & 0x7f) == self.moduleid, \
                    "Requested to read module {0}, but got result for module {1}, iteration {2}".format(self.moduleid, ((results[i][0] >> 8) & 0x7f), i)
            assert (results[i][0] & 0xff) == address.value, \
                    "Requested to read address {0}, but got result for address {1}, iteration {2}".format(address.value, (results[i][0] & 0xff), i)
            ret = results[i][1]
        return ret

    def reset_ib_lanes(self):
        """Toggles the enabled of all the IB lanes"""
        self.set_ib_enabled_lanes(0)
        self.set_ib_enabled_lanes(0x1FF)

    def reset_ob_lanes(self):
        """Toggles the enabled of all the OB lanes"""
        self.set_ob_enabled_lanes(0)
        self.set_ob_enabled_lanes(0xFFF_FFFF)

    def get_ib_faulty_lanes(self, commitTransaction=True):
        """Gets the lanes faulty for the IB"""
        self._request_ib_faulty_lanes()
        if commitTransaction:
            results = self.board.flush_and_read_results(expected_length=1)
            return self._format_ib_faulty_lanes(results)
        else:
            return None

    def _request_ib_faulty_lanes(self):
        """WB read request"""
        self.read(self.addr_list.IB_FAULTY_LANES, commitTransaction=False)

    def _format_ib_faulty_lanes(self, results):
        assert len(results) == 1
        ret = 0
        for i, address in enumerate([self.addr_list.IB_FAULTY_LANES]):
            assert ((results[i][0] >> 8) & 0x7f) == self.moduleid, \
                    "Requested to read module {0}, but got result for module {1}, iteration {2}".format(self.moduleid, ((results[i][0] >> 8) & 0x7f), i)
            assert (results[i][0] & 0xff) == address.value, \
                    "Requested to read address {0}, but got result for address {1}, iteration {2}".format(address.value, (results[i][0] & 0xff), i)
            ret = results[i][1]
        return ret

    def get_ob_faulty_lanes(self, commitTransaction=True):
        """Gets the lanes faulty for the OB"""
        self._request_ob_faulty_lanes()
        if commitTransaction:
            results = self.board.flush_and_read_results(expected_length=2)
            return self._format_ob_faulty_lanes(results)
        else:
            return None

    def _request_ob_faulty_lanes(self):
        """WB read request"""
        for address in [self.addr_list.OB_FAULTY_LANES_MSB, self.addr_list.OB_FAULTY_LANES_LSB]:
            self.read(address, commitTransaction=False)

    def _format_ob_faulty_lanes(self, results):
        assert len(results) == 2
        ret = 0
        for i, address in enumerate([self.addr_list.OB_FAULTY_LANES_MSB, self.addr_list.OB_FAULTY_LANES_LSB]):
            assert ((results[i][0] >> 8) & 0x7f) == self.moduleid, \
                    "Requested to read module {0}, but got result for module {1}, iteration {2}".format(self.moduleid, ((results[i][0] >> 8) & 0x7f), i)
            assert (results[i][0] & 0xff) == address.value, \
                    "Requested to read address {0}, but got result for address {1}, iteration {2}".format(address.value, (results[i][0] & 0xff), i)
            ret = results[i][1] | ret<<16
        return ret

    def get_status(self, commitTransaction=True):
        """Returns the status register"""
        self._request_status()
        if commitTransaction:
            results = self.board.flush_and_read_results(expected_length=1)
            return self._format_status(results)
        else:
            return None

    def _request_status(self):
        """WB read request"""
        self.read(self.addr_list.STATUS, commitTransaction=False)

    def _format_status(self, results):
        assert len(results) == 1
        ret = 0
        for i, address in enumerate([self.addr_list.STATUS]):
            assert ((results[i][0] >> 8) & 0x7f) == self.moduleid, \
                    "Requested to read module {0}, but got result for module {1}, iteration {2}".format(self.moduleid, ((results[i][0] >> 8) & 0x7f), i)
            assert (results[i][0] & 0xff) == address.value, \
                    "Requested to read address {0}, but got result for address {1}, iteration {2}".format(address.value, (results[i][0] & 0xff), i)
            ret = results[i][1]
        decoded = OrderedDict()
        for bit in StatusBitMapping:
            decoded[bit.name] = (ret>>bit.value) & 1
        return (ret,decoded)

    def get_ib_nok_lanes(self, commitTransaction=True):
        """Gets the lanes nok for the IB"""
        self._request_ib_nok_lanes()
        if commitTransaction:
            results = self.board.flush_and_read_results(expected_length=1)
            return self._format_ib_nok_lanes(results)
        else:
            return None

    def _request_ib_nok_lanes(self):
        """WB read request"""
        self.read(self.addr_list.IB_NOK_LANES, commitTransaction=False)

    def _format_ib_nok_lanes(self, results):
        assert len(results) == 1
        ret = 0
        for i, address in enumerate([self.addr_list.IB_NOK_LANES]):
            assert ((results[i][0] >> 8) & 0x7f) == self.moduleid, \
                    "Requested to read module {0}, but got result for module {1}, iteration {2}".format(self.moduleid, ((results[i][0] >> 8) & 0x7f), i)
            assert (results[i][0] & 0xff) == address.value, \
                    "Requested to read address {0}, but got result for address {1}, iteration {2}".format(address.value, (results[i][0] & 0xff), i)
            ret = results[i][1]
        return ret

    def get_ob_nok_lanes(self, commitTransaction=True):
        """Gets the lanes nok for the OB"""
        self._request_ob_nok_lanes()
        if commitTransaction:
            results = self.board.flush_and_read_results(expected_length=2)
            return self._format_ob_nok_lanes(results)
        else:
            return None

    def _request_ob_nok_lanes(self):
        """WB read request"""
        for address in [self.addr_list.OB_NOK_LANES_MSB, self.addr_list.OB_NOK_LANES_LSB]:
            self.read(address, commitTransaction=False)

    def _format_ob_nok_lanes(self, results):
        assert len(results) == 2
        ret = 0
        for i, address in enumerate([self.addr_list.OB_NOK_LANES_MSB, self.addr_list.OB_NOK_LANES_LSB]):
            assert ((results[i][0] >> 8) & 0x7f) == self.moduleid, \
                    "Requested to read module {0}, but got result for module {1}, iteration {2}".format(self.moduleid, ((results[i][0] >> 8) & 0x7f), i)
            assert (results[i][0] & 0xff) == address.value, \
                    "Requested to read address {0}, but got result for address {1}, iteration {2}".format(address.value, (results[i][0] & 0xff), i)
            ret = results[i][1] | ret<<16
        return ret

    def dump_config(self):
        """Dump the modules state and configuration as a string"""
        config_str = f"--- {self.name} module ---\n"
        self.board.comm.disable_rderr_exception()
        for address in self.addr_list:
            name = address.name
            try:
                value = self.read(address.value)
                config_str += "    - {0} : {1:#06X}\n".format(name, value)
            except:
                config_str += "    - {0} : FAILED\n".format(name)
        self.board.comm.enable_rderr_exception()
        return config_str
