"""Class to implement the capabilities of the CAN HLP monitor module"""

from enum import IntEnum, unique
from counter_monitor import WsCounterMonitor


@unique
class WsCanHlpMonitorAddress(IntEnum):
    """Memory mapping for the can_hlp_monitor"""
    LATCH_COUNTERS       = 0x00
    RESET_COUNTERS       = 0x01
    HLP_READ_LOW         = 0x02
    HLP_READ_HIGH        = 0x03
    HLP_WRITE_LOW        = 0x04
    HLP_WRITE_HIGH       = 0x05
    CAN_TX_MSG_SENT_LOW  = 0x06
    CAN_TX_MSG_SENT_HIGH = 0x07
    CAN_RX_MSG_RECV_LOW  = 0x08
    CAN_RX_MSG_RECV_HIGH = 0x09
    HLP_STATUS           = 0x0a
    HLP_ALERT            = 0x0b
    HLP_UNKNOWN          = 0x0c
    HLP_LENGTH_ERROR     = 0x0d
    HLP_MSG_DROPPED      = 0x0e
    CAN_TX_ACK_ERROR     = 0x0f
    CAN_TX_ARB_LOST      = 0x10
    CAN_TX_BIT_ERROR     = 0x11
    CAN_TX_RETRANSMIT    = 0x12
    CAN_RX_CRC_ERROR     = 0x13
    CAN_RX_FORM_ERROR    = 0x14
    CAN_RX_STUFF_ERROR   = 0x15
    HLP_NODE_ID_ERROR    = 0x16
    CAN_TX_FAILED        = 0x17

class WsCanHlpMonitor(WsCounterMonitor):
    """Wishbone slave for monitoring CAN HLP statistics counters"""

    def __init__(self, moduleid, board_obj):
        super(WsCanHlpMonitor, self).__init__(moduleid=moduleid, name="CAN HLP Monitor", board_obj=board_obj, registers=WsCanHlpMonitorAddress)
