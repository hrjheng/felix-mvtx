"""Implements the control for the gbt_packer_monitor wishbone slave"""

from enum import IntEnum, unique
from counter_monitor import WsCounterMonitor

@unique
class WsRadiationMonitorAddress(IntEnum):
    """Memory mapping for the gbt_packer_monitor"""
    LATCH_COUNTERS                                     = 0x00
    RESET_COUNTERS                                     = 0x01
    GBTX01_X_ALP_CTRL                                  = 0x02
    WBM_X_GBTX2                                        = 0x03
    SYSMON_X_DP_FIFO                                   = 0x04
    DP_OB_X_DP_IB                                      = 0x05
    GBT_PKG_X_TRIGGER_HANDLER                          = 0x06
    CALIB_X_PA3_FIFO                                   = 0x07
    PU1_X_RM                                           = 0x08
    I2C_GBT_WRAPPER_X_PU2                              = 0x09
    CAN_HLP_X_CAN_WB_MASTER                            = 0x0A
    IDENTITY_X_SYSTEM_RESET_CONTROL                    = 0x0B
    FULL_DESIGN                                        = 0x0C


class WsRadiationMonitor(WsCounterMonitor):
    """Monitor for GBT packer counters"""

    def __init__(self, moduleid, board_obj):
        super(WsRadiationMonitor, self).__init__(moduleid=moduleid,board_obj=board_obj,name="Radiation Monitor", registers=WsRadiationMonitorAddress)


    def is_xcku_without_seus(self):
        return self.read_counters()['FULL_DESIGN'] == 0
