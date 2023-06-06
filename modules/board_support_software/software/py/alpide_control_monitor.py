"""Class to implement the alpide control monitor wishbone slave abstraction layer"""

from counter_monitor import WsCounterMonitor
from enum import IntEnum, unique


@unique
class WsAlpideControlMonitorAddress(IntEnum):
    """memory mapping for alpide control module"""
    LATCH_COUNTERS             = 0x00
    RESET_COUNTERS             = 0x01
    OPCODE_LOW                 = 0x02
    OPCODE_HIGH                = 0x03
    BROADCAST_LOW              = 0x04
    BROADCAST_HIGH             = 0x05
    TRIGGER_SENT_LOW           = 0x06
    TRIGGER_SENT_HIGH          = 0x07
    OPCODE_REJECTED_LOW        = 0x08
    OPCODE_REJECTED_HIGH       = 0x09
    PULSE_SENT_LOW             = 0x0A
    PULSE_SENT_HIGH            = 0x0B
    WRITE_OPCODE_LOW           = 0x0C
    WRITE_OPCODE_HIGH          = 0x0D
    READ_OPCODE_LOW            = 0x0E
    READ_OPCODE_HIGH           = 0x0F
    READ_DONE_LOW              = 0x10
    READ_DONE_HIGH             = 0x11
    CHIPID_MISMATCH_LOW        = 0x12
    CHIPID_MISMATCH_HIGH       = 0x13


@unique
class CountersBitMapping(IntEnum):
    """bit mapping of the reset/latch counter registers"""
    OPCODE                 = 0
    BROADCAST              = 1
    TRIGGER_SENT           = 2
    OPCODE_REJECTED        = 3
    PULSE_SENT             = 4
    WRITE_OPCODE           = 5
    READ_OPCODE            = 6
    READ_DONE              = 7
    CHIPID_MISMATCH        = 8


class AlpideControlMonitor(WsCounterMonitor):
    """alpide control monitor wishbone slave"""

    def __init__(self, moduleid, board_obj):
        super(AlpideControlMonitor, self).__init__(moduleid=moduleid, name="ALPIDE Control Monitor", board_obj=board_obj, registers=WsAlpideControlMonitorAddress)
