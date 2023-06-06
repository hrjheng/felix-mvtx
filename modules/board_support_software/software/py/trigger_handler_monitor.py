"""Class to implement the trigger handler monitor wishbone slave abstraction layer"""

from counter_monitor import WsCounterMonitor
from enum import IntEnum, unique


@unique
class WsTriggerHandlerMonitorAddress(IntEnum):
    """memory mapping for trigger handler module"""
    LATCH_COUNTERS              = 0x00
    RESET_COUNTERS              = 0x01
    TRIGGER_SENT_LSB            = 0x02
    TRIGGER_SENT_MSB            = 0x03
    TRIGGER_ECHOED_LSB          = 0x04
    TRIGGER_FIFO_0_FULL         = 0x05
    TRIGGER_FIFO_0_OVERFLOW     = 0x06
    TRIGGER_FIFO_1_FULL         = 0x07
    TRIGGER_FIFO_1_OVERFLOW     = 0x08
    TRIGGER_FIFO_2_FULL         = 0x09
    TRIGGER_FIFO_2_OVERFLOW     = 0x0A
    DEAD_00                     = 0x0B
    DEAD_01                     = 0x0C
    PROCESSED_TRIGGERS_LSB      = 0x0D
    PROCESSED_TRIGGERS_MSB      = 0x0E
    TRIGGER_GATED_LSB           = 0x0F
    TRIGGER_GATED_MSB           = 0x10
    TRIGGER_CORRECTED_LSB       = 0x11
    TRIGGER_CORRECTED_MSB       = 0x12
    ORBIT_LSB                   = 0x13 # The following are bit counts of the trigger vector
    ORBIT_MSB                   = 0x14
    HB_LSB                      = 0x15 # Number of HBA is HB-HBR
    HB_MSB                      = 0x16
    HBR_LSB                     = 0x17
    HBR_MSB                     = 0x18
    HBC_LSB                     = 0x19
    HBC_MSB                     = 0x1A
    PHYSICS_LSB                 = 0x1B
    PHYSICS_MSB                 = 0x1C
    PP_LSB                      = 0x1D
    PP_MSB                      = 0x1E
    CAL_LSB                     = 0x1F
    CAL_MSB                     = 0x20
    SOT_LSB                     = 0x21
    SOT_MSB                     = 0x22
    EOT_LSB                     = 0x23
    EOT_MSB                     = 0x24
    SOC_LSB                     = 0x25
    SOC_MSB                     = 0x26
    EOC_LSB                     = 0x27
    EOC_MSB                     = 0x28
    TF_LSB                      = 0x29
    TF_MSB                      = 0x2A
    TRIGGER_ILLEGAL_MODE_SWITCH = 0x2B
    TRIGGER_IGNORED_LSB         = 0x2C
    TRIGGER_IGNORED_MSB         = 0x2D
    TRIGGER_ECHOED_MSB          = 0x2E
    FERST                       = 0x2F
    LOL_TIMEBASE                = 0x30


@unique
class CountersBitMapping(IntEnum):
    """bit mapping of the reset/latch counter registers"""
    TRIGGER_SENT                = 0
    TRIGGER_ECHOED              = 1
    TRIGGER_FIFO_0_FULL         = 2
    TRIGGER_FIFO_0_OVERFLOW     = 3
    TRIGGER_FIFO_1_FULL         = 4
    TRIGGER_FIFO_1_OVERFLOW     = 5
    TRIGGER_FIFO_2_FULL         = 6
    TRIGGER_FIFO_2_OVERFLOW     = 7
    PROCESSED_TRIGGERS          = 8
    TRIGGER_GATED               = 9
    TRIGGER_CORRECTED           = 10
    ORBIT                       = 11
    HB                          = 12
    HBR                         = 13
    HBC                         = 14
    PHYSICS                     = 15
    PP                          = 16
    CAL                         = 17
    SOT                         = 18
    EOT                         = 19
    SOC                         = 20
    EOC                         = 21
    TF                          = 22
    TRIGGER_ILLEGAL_MODE_SWITCH = 23
    TRIGGER_IGNORED             = 24
    FERST                       = 25
    LOL_TIMEBASE                = 26


class TriggerHandlerMonitor(WsCounterMonitor):
    """trigger handler monitor wishbone slave"""

    def __init__(self, moduleid, board_obj):
        super(TriggerHandlerMonitor, self).__init__(moduleid=moduleid, name="Trigger Handler Monitor", board_obj=board_obj, registers=WsTriggerHandlerMonitorAddress)
