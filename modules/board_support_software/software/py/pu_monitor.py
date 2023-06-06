"""Class to implement the capabilities of the I2C PU monitor module"""

from enum import IntEnum, unique
from counter_monitor import WsCounterMonitor


@unique
class PuMonitorAddress(IntEnum):
    """Memory mapping for the i2c_monitor"""
    LATCH_COUNTERS             = 0x00
    RESET_COUNTERS             = 0x01
    COUNTER_COMPLETED_BYTE_LSB = 0x02
    COUNTER_COMPLETED_BYTE_MSB = 0x03
    COUNTER_AL_ERROR_LSB       = 0x04
    COUNTER_AL_ERROR_MSB       = 0x05
    COUNTER_NOACK_ERROR_LSB    = 0x06
    COUNTER_NOACK_ERROR_MSB    = 0x07
    COUNTER_REQ_FIFO_OVF_LSB   = 0x08
    COUNTER_REQ_FIFO_OVF_MSB   = 0x09
    COUNTER_RES_FIFO_OVF_LSB   = 0x0a
    COUNTER_RES_FIFO_OVF_MSB   = 0x0b
    COUNTER_RES_FIFO_UFL_LSB   = 0x0c
    COUNTER_RES_FIFO_UFL_MSB   = 0x0d


class PuMonitor(WsCounterMonitor):
    """Wishbone slave for monitoring PU I2C statistics counters"""

    def __init__(self, moduleid, board_obj):
        super(PuMonitor, self).__init__(moduleid=moduleid, name="PU Monitor", board_obj=board_obj, registers=PuMonitorAddress)

    def read_counters(self, reset_after=False, commitTransaction=True):
        """Read all counters inside the PuMonitor wishbone slave"""
        results = list(self._get_counters(latch_first=True, reset_after=reset_after, commitTransaction=commitTransaction).values())
        ret = {}
        if commitTransaction:
            ret['completed_byte_count'] = results[PuMonitorAddress.COUNTER_COMPLETED_BYTE_LSB-2] |\
                                          ((results[PuMonitorAddress.COUNTER_COMPLETED_BYTE_MSB-2]) << 16)
            ret['arbitration_lost_error_count'] = results[PuMonitorAddress.COUNTER_AL_ERROR_LSB-2] |\
                                                  ((results[PuMonitorAddress.COUNTER_AL_ERROR_MSB-2]) << 16)
            ret['noack_error_count'] = results[PuMonitorAddress.COUNTER_NOACK_ERROR_LSB-2] |\
                                       ((results[PuMonitorAddress.COUNTER_NOACK_ERROR_MSB-2]) << 16)
            ret['request_fifo_overflow_count'] = results[PuMonitorAddress.COUNTER_REQ_FIFO_OVF_LSB-2] |\
                                                 ((results[PuMonitorAddress.COUNTER_REQ_FIFO_OVF_MSB-2]) << 16)
            ret['result_fifo_overflow_count'] = results[PuMonitorAddress.COUNTER_RES_FIFO_OVF_LSB-2] |\
                                                ((results[PuMonitorAddress.COUNTER_RES_FIFO_OVF_MSB-2]) << 16)
            ret['result_fifo_underflow_count'] = results[PuMonitorAddress.COUNTER_RES_FIFO_UFL_LSB-2] |\
                                                ((results[PuMonitorAddress.COUNTER_RES_FIFO_UFL_MSB-2]) << 16)
        return ret
