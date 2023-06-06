"""MMCM and GBTx RX READY monitor module"""

from enum import IntEnum, unique
from counter_monitor import WsCounterMonitor

@unique
class WsMmcmGbtxRxrdyMonitorAddress(IntEnum):
    """Memory mapping for the MMCM GBTX_RDRDY"""
    LATCH_COUNTERS                  = 0x00
    RESET_COUNTERS                  = 0x01
    GBTX0_RXRDY_FALLING_EDGE        = 0x02
    GBTX2_RXRDY_FALLING_EDGE        = 0x03
    MMCM_GBTX0_LOCKED_FALLING_EDGE  = 0x04
    MMCM_OB_FX3_LOCKED_FALLING_EDGE = 0x05
    BUFGCTRL_SEL_GBTX0_FALLING_EDGE = 0x06
    GBTX0_RXRDY_RAISING_EDGE        = 0x07
    GBTX2_RXRDY_RAISING_EDGE        = 0x08
    MMCM_GBTX0_LOCKED_RAISING_EDGE  = 0x09
    MMCM_OB_FX3_LOCKED_RAISING_EDGE = 0x0A
    BUFGCTRL_SEL_GBTX0_RAISING_EDGE = 0x0B

class RuMmcmGbtxRxrdyMonitor(WsCounterMonitor):
    """MMCM and GBTx RX READY monitor module"""

    def __init__(self, moduleid, board_obj):
        super(RuMmcmGbtxRxrdyMonitor, self).__init__(moduleid=moduleid, name="MMCM and GBTx RX READY Monitor", board_obj=board_obj, registers=WsMmcmGbtxRxrdyMonitorAddress)
