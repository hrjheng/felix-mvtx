"""Implements the control for the ws_master_monitor wishbone slave"""

from enum import IntEnum, unique
from counter_monitor import WsCounterMonitor


@unique
class WsMasterMonitorAddress(IntEnum):
    """Memory mapping for the ws_master_monitor taken from ws_master_pkg.vhd"""
    LATCH_COUNTERS      = 0x00
    RESET_COUNTERS      = 0x01
    WR_ERRORS_LOW       = 0x02
    WR_ERRORS_HIGH      = 0x03
    RD_ERRORS_LOW       = 0x04
    RD_ERRORS_HIGH      = 0x05
    SEE_ERRORS_LOW      = 0x06
    SEE_ERRORS_HIGH     = 0x07
    WR_OPERATIONS_LOW   = 0x08
    WR_OPERATIONS_HIGH  = 0x09
    RD_OPERATIONS_LOW   = 0x0A
    RD_OPERATIONS_HIGH  = 0x0B


@unique
class CountersBitMapping(IntEnum):
    WR_ERRORS     = 0x00
    RD_ERRORS     = 0x01
    SEE_ERRORS    = 0x02
    WR_OPERATIONS = 0x03
    RD_OPERATIONS = 0x04


class WsMasterMonitor(WsCounterMonitor):
    """Wishbone slave instantiated inside the wishbone master handling the wishbone master monitoring"""

    def __init__(self, moduleid, board_obj):
        super(WsMasterMonitor, self).__init__(moduleid=moduleid, name="Wishbone Master Monitor", board_obj=board_obj, registers=WsMasterMonitorAddress)
