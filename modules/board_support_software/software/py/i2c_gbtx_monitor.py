"""Class to implement the capabilities of the I2C GBTx monitor module"""

from enum import IntEnum, unique
from counter_monitor import WsCounterMonitor


@unique
class WsI2cGbtxMonitorAddress(IntEnum):
    """Memory mapping for the i2c_monitor"""
    LATCH_COUNTERS             = 0x00
    RESET_COUNTERS             = 0x01
    COUNTER_COMPLETED_BYTE_LSB = 0x02
    COUNTER_COMPLETED_BYTE_MSB = 0x03
    COUNTER_AL_ERROR_LSB       = 0x04
    COUNTER_AL_ERROR_MSB       = 0x05
    COUNTER_NOACK_ERROR_LSB    = 0x06
    COUNTER_NOACK_ERROR_MSB    = 0x07


class WsI2cGbtxMonitor(WsCounterMonitor):
    """Wishbone slave for monitoring GBTx I2C statistics counters"""

    def __init__(self, moduleid, board_obj):
        super(WsI2cGbtxMonitor, self).__init__(moduleid=moduleid, name="GBTx I2C Monitor", board_obj=board_obj, registers=WsI2cGbtxMonitorAddress)

    def read_counters(self, reset_after=False, commitTransaction=True):
        """Read all counters inside the I2cGbtxMonitor wishbone slave"""
        results = list(self._get_counters(latch_first=True, reset_after=reset_after, commitTransaction=commitTransaction).values())
        ret = {}
        if commitTransaction:
            ret['completed_byte_count'] = results[WsI2cGbtxMonitorAddress.COUNTER_COMPLETED_BYTE_LSB-2] |\
                                          ((results[WsI2cGbtxMonitorAddress.COUNTER_COMPLETED_BYTE_MSB-2]) << 16)
            ret['arbitration_lost_error_count'] = results[WsI2cGbtxMonitorAddress.COUNTER_AL_ERROR_LSB-2] |\
                                                  ((results[WsI2cGbtxMonitorAddress.COUNTER_AL_ERROR_MSB-2]) << 16)
            ret['noack_error_count'] = results[WsI2cGbtxMonitorAddress.COUNTER_NOACK_ERROR_LSB-2] |\
                                       ((results[WsI2cGbtxMonitorAddress.COUNTER_NOACK_ERROR_MSB-2]) << 16)
        return ret
