"""Implements the control for the gbt_packer_monitor wishbone slave"""

from enum import IntEnum, unique
from counter_monitor import WsCounterMonitor

@unique
class WsGbtPackerMonitorAddress(IntEnum):
    """Memory mapping for the gbt_packer_monitor"""
    LATCH_COUNTERS                                     = 0x00
    RESET_COUNTERS                                     = 0x01
    TRIGGER_READ_LSB                                   = 0x02
    TRIGGER_READ_MSB                                   = 0x03
    SOP_SENT_LSB                                       = 0x04
    SOP_SENT_MSB                                       = 0x05
    EOP_SENT_LSB                                       = 0x06
    EOP_SENT_MSB                                       = 0x07
    PACKET_DONE_LSB                                    = 0x08
    PACKET_DONE_MSB                                    = 0x09
    PACKET_EMPTY_LSB                                   = 0x0A
    PACKET_EMPTY_MSB                                   = 0x0B
    FIFO_OVERFLOW_X_PACKET_TIMEOUT                     = 0x0C
    FIFO_FULL                                          = 0x0D
    PACKET_SPLIT_LSB                                   = 0x0E
    PACKET_SPLIT_MSB                                   = 0x0F
    IDLE_TIMEOUT_X_START_TIMEOUT                       = 0x10
    VIOLATION_START_X_STOP_TIMEOUT                     = 0x11
    VIOLATION_ACK_X_VIOLATION_STOP                     = 0x12
    VIOLATION_NO_VALID_STOP_X_VIOLATION_NO_VALID_START = 0x13
    VIOLATION_EMPTY                                    = 0x14


class GbtPackerMonitor(WsCounterMonitor):
    """Monitor for GBT packer counters"""

    def __init__(self, moduleid,board_obj):
        super(GbtPackerMonitor, self).__init__(moduleid=moduleid,board_obj=board_obj,name="GBT Packer Monitor", registers=WsGbtPackerMonitorAddress)
