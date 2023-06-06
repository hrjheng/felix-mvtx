"""file implementing the control for the data_lane wishbone slave"""

import warnings

from enum import IntEnum, unique
from wishbone_module import WishboneModule

@unique
class DataLaneAddress(IntEnum):
    """memory mapping for the data_lane got from data_lane_wishbone_pkg.vhd"""
    DETECTOR_TIMEOUT_LSB   = 0
    DETECTOR_TIMEOUT_MSB   = 1
    STRIP_DATA_CONTROL     = 2
    SUPPRESS_EMPTY_CONTROL = 3
    ERROR_SIGNATURE_0      = 4
    ERROR_SIGNATURE_1      = 5
    ERROR_SIGNATURE_2      = 6
    ERROR_SIGNATURE_3      = 7
    ERROR_SIGNATURE_4      = 8
    ERROR_SIGNATURE_5      = 9
    ERROR_SIGNATURE_6      = 10
    ERROR_SIGNATURE_7      = 11
    ERROR_SIGNATURE_8      = 12
    ERROR_SIGNATURE_9      = 13
    ERROR_SIGNATURE_10     = 14
    ERROR_SIGNATURE_11     = 15
    ERROR_SIGNATURE_12     = 16
    ERROR_SIGNATURE_13     = 17
    ERROR_SIGNATURE_14     = 18
    ERROR_SIGNATURE_15     = 19
    ERROR_SIGNATURE_16     = 20
    ERROR_SIGNATURE_17     = 21
    ERROR_SIGNATURE_18     = 22
    ERROR_SIGNATURE_19     = 23
    ERROR_SIGNATURE_20     = 24
    ERROR_SIGNATURE_21     = 25
    ERROR_SIGNATURE_22     = 26
    ERROR_SIGNATURE_23     = 27
    ERROR_SIGNATURE_24     = 28
    ERROR_SIGNATURE_25     = 29
    ERROR_SIGNATURE_26     = 30
    ERROR_SIGNATURE_27     = 31
    DEBUG_FIFO_LANE_0      = 32
    DEBUG_FIFO_LANE_1      = 33
    DEBUG_FIFO_LANE_2      = 34
    DEBUG_FIFO_LANE_3      = 35
    DEBUG_FIFO_LANE_4      = 36
    DEBUG_FIFO_LANE_5      = 37
    DEBUG_FIFO_LANE_6      = 38
    DEBUG_FIFO_LANE_7      = 39
    DEBUG_FIFO_LANE_8      = 40
    DEBUG_FIFO_LANE_9      = 41
    DEBUG_FIFO_LANE_10     = 42
    DEBUG_FIFO_LANE_11     = 43
    DEBUG_FIFO_LANE_12     = 44
    DEBUG_FIFO_LANE_13     = 45
    DEBUG_FIFO_LANE_14     = 46
    DEBUG_FIFO_LANE_15     = 47
    DEBUG_FIFO_LANE_16     = 48
    DEBUG_FIFO_LANE_17     = 49
    DEBUG_FIFO_LANE_18     = 50
    DEBUG_FIFO_LANE_19     = 51
    DEBUG_FIFO_LANE_20     = 52
    DEBUG_FIFO_LANE_21     = 53
    DEBUG_FIFO_LANE_22     = 54
    DEBUG_FIFO_LANE_23     = 55
    DEBUG_FIFO_LANE_24     = 56
    DEBUG_FIFO_LANE_25     = 57
    DEBUG_FIFO_LANE_26     = 58
    DEBUG_FIFO_LANE_27     = 59


@unique
class StripDataControlBit(IntEnum):
    """Enum for discriminating the bits of the STRIP_DATA_CONTROL register"""
    ALLOW = 0


@unique
class SuppressEmptyControlBit(IntEnum):
    """Enum for discriminating the bits of the SUPPRESS_EMPTY_CONTROL register"""
    ALLOW = 0


@unique
class ErrorFifoLaneBit(IntEnum):
    """Enum for discriminating the bits of the DEBUG_FIFO_LANE_* register"""
    DATA       = 0
    BYTE_ERR   = 8
    LANE_NOK   = 9
    EMPTY      = 15


class DataLane(WishboneModule):
    """wishbone slave used to configure the data lanes"""

    def __init__(self, moduleid, board_obj):
        super(DataLane, self).__init__(moduleid=moduleid, board_obj=board_obj,
                                       name="data lane")
        self.addr_list = DataLaneAddress

    def set_detector_timeout(self, timeout, commitTransaction=True):
        """Sets the detector timeout in 6.25 ns units"""
        assert timeout | 0xFFFF_FFFF == 0xFFFF_FFFF
        self.write(self.addr_list.DETECTOR_TIMEOUT_LSB, (timeout>>0)  & 0xFFFF, commitTransaction=False)
        self.write(self.addr_list.DETECTOR_TIMEOUT_MSB, (timeout>>16) & 0xFFFF, commitTransaction=commitTransaction)

    def get_detector_timeout(self, commitTransaction=True):
        """Gets detector timeout in 6.25 ns units"""
        self._request_detector_timeout()
        if commitTransaction:
            results = self.board.flush_and_read_results(expected_length=2)
            return self._format_detector_timeout(results)

    def _request_detector_timeout(self):
        """WB read request"""
        for address in [self.addr_list.DETECTOR_TIMEOUT_MSB, self.addr_list.DETECTOR_TIMEOUT_LSB]:
            self.read(address, commitTransaction=False)

    def _format_detector_timeout(self, results):
        assert len(results) == 2
        ret = 0
        for i, address in enumerate([self.addr_list.DETECTOR_TIMEOUT_MSB, self.addr_list.DETECTOR_TIMEOUT_LSB]):
            assert ((results[i][0] >> 8) & 0x7f) == self.moduleid, \
                    "Requested to read module {0}, but got result for module {1}, iteration {2}".format(self.moduleid, ((results[i][0] >> 8) & 0x7f), i)
            assert (results[i][0] & 0xff) == address.value, \
                    "Requested to read address {0}, but got result for address {1}, iteration {2}".format(address.value, (results[i][0] & 0xff), i)
            ret = results[i][1] | ret<<16
        return ret

    def set_strip_data_control(self, allow, commitTransaction=True):
        """Sets the strip data control registers"""
        assert allow | 1 == 1, "Wrong input width"
        data = allow<<StripDataControlBit.ALLOW
        self.write(self.addr_list.STRIP_DATA_CONTROL, data, commitTransaction=commitTransaction)

    def get_strip_data_control(self, commitTransaction=True):
        """Returns the settings of the strip data control register"""
        self._request_strip_data_control()
        if commitTransaction:
            results = self.board.flush_and_read_results(expected_length=1)
            return self._format_strip_data_control(results)

    def _request_strip_data_control(self):
        """WB read request"""
        self.read(self.addr_list.STRIP_DATA_CONTROL, commitTransaction=False)

    def _format_strip_data_control(self, results):
        assert len(results) == 1
        ret = {}
        for i, address in enumerate([self.addr_list.STRIP_DATA_CONTROL]):
            assert ((results[i][0] >> 8) & 0x7f) == self.moduleid, \
                    "Requested to read module {0}, but got result for module {1}, iteration {2}".format(self.moduleid, ((results[i][0] >> 8) & 0x7f), i)
            assert (results[i][0] & 0xff) == address.value, \
                    "Requested to read address {0}, but got result for address {1}, iteration {2}".format(address.value, (results[i][0] & 0xff), i)
            raw = results[i][1]
            ret['allow'] = (raw >> StripDataControlBit.ALLOW) & 1
        return ret

    def set_suppress_empty_control(self, allow, commitTransaction=True):
        """Sets the suppress empty control registers"""
        warnings.warn("Functionality is not implemented in RTL: whatever you write here will have no effect", RuntimeWarning)
        assert allow | 1 == 1, "Wrong input width"
        data = allow<<SuppressEmptyControlBit.ALLOW
        self.write(self.addr_list.SUPPRESS_EMPTY_CONTROL, data, commitTransaction=commitTransaction)

    def get_suppress_empty_control(self, commitTransaction=True):
        """Returns the settings of the suppress empty control register"""
        warnings.warn("Functionality is not implemented in RTL: whatever you read here has no effect", RuntimeWarning)
        self._request_suppress_empty_control()
        if commitTransaction:
            results = self.board.flush_and_read_results(expected_length=1)
            return self._format_suppress_empty_control(results)

    def _request_suppress_empty_control(self):
        """WB read request"""
        self.read(self.addr_list.SUPPRESS_EMPTY_CONTROL, commitTransaction=False)

    def _format_suppress_empty_control(self, results):
        assert len(results) == 1
        ret = {}
        for i, address in enumerate([self.addr_list.SUPPRESS_EMPTY_CONTROL]):
            assert ((results[i][0] >> 8) & 0x7f) == self.moduleid, \
                    "Requested to read module {0}, but got result for module {1}, iteration {2}".format(self.moduleid, ((results[i][0] >> 8) & 0x7f), i)
            assert (results[i][0] & 0xff) == address.value, \
                    "Requested to read address {0}, but got result for address {1}, iteration {2}".format(address.value, (results[i][0] & 0xff), i)
            raw = results[i][1]
            ret['allow'] = (raw >> SuppressEmptyControlBit.ALLOW) & 1
        return ret

    def get_error_signature(self, lane, commitTransaction=True):
        return self.read(DataLaneAddress.ERROR_SIGNATURE_0+lane, commitTransaction=commitTransaction)

    def get_debug_fifo_lane(self, lane, commitTransaction=True):
        """Returns the list of data from the debug fifo for the selected fifo"""
        done = False
        ret = []
        while not done:
            self._request_debug_fifo_lane(lane)
            if commitTransaction:
                results = self.board.flush_and_read_results(expected_length=1)
                r = self._format_debug_fifo_lane(lane, results)
                if r['empty']:
                    done=True
                else:
                    ret.append(r)
            else:
                done = True
        return ret

    def _request_debug_fifo_lane(self, lane):
        """WB read request"""
        assert lane in range(self.board.LANES_OB), f"Invalid value {lane} not in range{self.board.LANES_OB}"
        self.read(self.addr_list.DEBUG_FIFO_LANE_0+lane, commitTransaction=False)

    def _format_debug_fifo_lane(self, lane, results):
        assert len(results) == 1
        ret = {}
        for i, address in enumerate([self.addr_list.DEBUG_FIFO_LANE_0+lane]):
            assert ((results[i][0] >> 8) & 0x7f) == self.moduleid, \
                    "Requested to read module {0}, but got result for module {1}, iteration {2}".format(self.moduleid, ((results[i][0] >> 8) & 0x7f), i)
            assert (results[i][0] & 0xff) == address, \
                    "Requested to read address {0}, but got result for address {1}, iteration {2}".format(address, (results[i][0] & 0xff), i)
            raw = results[i][1]
            ret['data']  = f"{(raw >> ErrorFifoLaneBit.DATA) & 2**(ErrorFifoLaneBit.BYTE_ERR-ErrorFifoLaneBit.DATA)-1:#04x}"
            ret['byte_err'] = (raw >> ErrorFifoLaneBit.BYTE_ERR) & 1
            ret['lane_nok'] = (raw >> ErrorFifoLaneBit.LANE_NOK) & 1
            ret['empty'] = (raw >> ErrorFifoLaneBit.EMPTY) & 1
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
