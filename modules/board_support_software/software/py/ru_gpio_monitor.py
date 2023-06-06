"""Datapath monitor module for Reading out GPIO counters"""

import collections
from enum import IntEnum, unique
from counter_monitor import WsCounterMonitor
from ru_frontend_monitor import FrontendMonitor


@unique
class WsGpioMonitorAddress(IntEnum):
    """Memory mapping for the alpide_datapath_monitor"""
    LATCH_COUNTERS                               = 0x00
    RESET_COUNTERS                               = 0x01
    d8b10b_OOT_ERROR_LOW                         = 0x02
    d8b10b_OOT_ERROR_HIGH                        = 0x03

class GpioMonitor(FrontendMonitor):
    """Monitor for Gpio status counters"""
    def __init__(self, moduleid,board_obj, lanes):
        super(GpioMonitor, self).__init__(moduleid=moduleid,
                                          board_obj=board_obj,
                                          lanes=lanes,
                                          name="Gpio Monitor",
                                          registers=WsGpioMonitorAddress,
                                          wb_register_mapping = [
                                              "d8b10b_OOT_ERROR_LOW",
                                              "d8b10b_OOT_ERROR_HIGH"],
                                          counter_mapping = [
                                              "8b10b_OOT_ERROR"],
                                          counter_order = {
                                              "8b10b_OOT_ERROR" : ["d8b10b_OOT_ERROR_LOW","d8b10b_OOT_ERROR_HIGH"]},
                                          counter_transform = {
                                              "8b10b_OOT_ERROR" : (lambda wb_regs: wb_regs["d8b10b_OOT_ERROR_HIGH"] << 16 | wb_regs["d8b10b_OOT_ERROR_LOW"])})
