"""Datapath monitor module for Reading out GTH counters"""

from enum import IntEnum, unique
from counter_monitor import WsCounterMonitor
from ru_frontend_monitor import FrontendMonitor


@unique
class WsGthMonitorAddress(IntEnum):
    """Memory mapping for the alpide_datapath_monitor"""
    LATCH_COUNTERS                               = 0x00
    RESET_COUNTERS                               = 0x01
    REALIGNED_X_CPLL_LOCK_LOSS                   = 0x02
    CDR_LOCK_LOSS                                = 0x03
    ALIGNED_LOSS                                 = 0x04
    d8b10b_OOT_ERROR_LOW                         = 0x05
    d8b10b_OOT_ERROR_HIGH                        = 0x06


class GthMonitor(FrontendMonitor):
    """Monitor for Gth status counters"""
    def __init__(self, moduleid, board_obj, lanes):
        super(GthMonitor, self).__init__(moduleid=moduleid,
                                         board_obj=board_obj,
                                         lanes=lanes,
                                         name="Gth Monitor",
                                         registers=WsGthMonitorAddress,
                                         wb_register_mapping = [
                                             "REALIGNED_X_CPLL_LOCK_LOSS",
                                             "CDR_LOCK_LOSS",
                                             "ALIGNED_LOSS",
                                             "d8b10b_OOT_ERROR_LOW",
                                             "d8b10b_OOT_ERROR_HIGH"],
                                         counter_mapping = [
                                             "CPLL_LOCK_LOSS",
                                             "REALIGNED",
                                             "CDR_LOCK_LOSS",
                                             "ALIGNED_LOSS",
                                             "8b10b_OOT_ERROR"],
                                         counter_order = {
                                             "CPLL_LOCK_LOSS" : ["REALIGNED_X_CPLL_LOCK_LOSS"],
                                             "REALIGNED" : ["REALIGNED_X_CPLL_LOCK_LOSS"],
                                             "8b10b_OOT_ERROR" : ["d8b10b_OOT_ERROR_LOW","d8b10b_OOT_ERROR_HIGH"]},
                                         counter_transform = {
                                             "CPLL_LOCK_LOSS" : (lambda wb_regs: wb_regs["REALIGNED_X_CPLL_LOCK_LOSS"] & 0xFF),
                                             "REALIGNED": (lambda wb_regs: (wb_regs["REALIGNED_X_CPLL_LOCK_LOSS"]>>8) & 0xFF),
                                             "CDR_LOCK_LOSS" : (lambda wb_regs: wb_regs["CDR_LOCK_LOSS"]),
                                             "ALIGNED_LOSS" : (lambda wb_regs: wb_regs["ALIGNED_LOSS"]),
                                             "8b10b_OOT_ERROR" : (lambda wb_regs: wb_regs["d8b10b_OOT_ERROR_HIGH"] << 16 | wb_regs["d8b10b_OOT_ERROR_LOW"])})
