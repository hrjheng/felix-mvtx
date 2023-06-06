"""Implements the control for the pa3_fifo_monitor wishbone slave"""

from enum import IntEnum, unique
from counter_monitor import WsCounterMonitor

@unique
class Pa3FifoMonitorAddress(IntEnum):
    """Memory mapping for the pa3_fifo_monitor taken from pa3_fifo_monitor_pkg.vhd"""
    LATCH_COUNTERS      = 0x00
    RESET_COUNTERS      = 0x01
    FIFO_WRITE          = 0x02
    FIFO_READ           = 0x03
    FIFO_UNDERFLOW      = 0x04
    FIFO_OVERFLOW       = 0x05

class Pa3FifoMonitor(WsCounterMonitor):
    """Wishbone slave for monitoring the PA3 FIFO"""

    def __init__(self, moduleid, board_obj):
        super(Pa3FifoMonitor, self).__init__(moduleid=moduleid, name="PA3 FIFO Monitor", board_obj=board_obj, registers=Pa3FifoMonitorAddress)
