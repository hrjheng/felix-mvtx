"""Implements the control for the gbtx_flow_monitor_wishbone slave"""

from enum import IntEnum, unique
from counter_monitor import WsCounterMonitor

@unique
class WsGbtxFlowMonitorAddress(IntEnum):
    """memory mapping for gbtx_flow_monitor_wishbone module taken from gbtx_flow_monitor_pkg.vhd"""
    LATCH_COUNTERS            = 0x00
    RESET_COUNTERS            = 0x01
    DOWNLINK0_SWT_LSB         = 0x02
    DOWNLINK0_SWT_MSB         = 0x03
    DOWNLINK0_SWT_INV_LSB     = 0x04
    DOWNLINK0_SWT_INV_MSB     = 0x05
    DOWNLINK0_TRG_LSB         = 0x06
    DOWNLINK0_TRG_MSB         = 0x07
    DOWNLINK0_OVERFLOW_LSB    = 0x08
    DOWNLINK0_OVERFLOW_MSB    = 0x09
    DOWNLINK2_TRG_LSB         = 0x0A
    DOWNLINK2_TRG_MSB         = 0x0B
    UPLINK0_SWT_LSB           = 0x0C
    UPLINK0_SWT_MSB           = 0x0D
    UPLINK0_SOP_LSB           = 0x0E
    UPLINK0_SOP_MSB           = 0x0F
    UPLINK0_EOP_LSB           = 0x10
    UPLINK0_EOP_MSB           = 0x11
    UPLINK0_OVERFLOW_LSB      = 0x12
    UPLINK0_OVERFLOW_MSB      = 0x13
    UPLINK1_SWT_LSB           = 0x14
    UPLINK1_SWT_MSB           = 0x15
    UPLINK1_SOP_LSB           = 0x16
    UPLINK1_SOP_MSB           = 0x17
    UPLINK1_EOP_LSB           = 0x18
    UPLINK1_EOP_MSB           = 0x19
    UPLINK2_SWT_LSB           = 0x1A
    UPLINK2_SWT_MSB           = 0x1B
    UPLINK2_SOP_LSB           = 0x1C
    UPLINK2_SOP_MSB           = 0x1D
    UPLINK2_EOP_LSB           = 0x1E
    UPLINK2_EOP_MSB           = 0x1F


class GbtxFlowMonitor(WsCounterMonitor):
    """GBTx flow monitor wishbone slave"""

    def __init__(self, moduleid, board_obj):
        super(GbtxFlowMonitor, self).__init__(moduleid=moduleid, name="GbtxFlowMonitor", board_obj=board_obj, registers=WsGbtxFlowMonitorAddress, pulsed=False, bit_mapped_reset=True, bit_mapped_latch=True)
