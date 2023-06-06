"""Flags in the ALPIDE chip trailer as per P61 of the ALPIDE operation manual"""


from enum import IntEnum, unique


@unique
class TrailerFlag(IntEnum):
    BUSY_TRANSITION    = 0 # indication that the BUSY was asserted during the readout of the frame in question.
    STROBE_EXTENDED    = 1 # indication that the framing window for the event of question was extended due to the reception of an external trigger.
    FLUSHED_INCOMPLETE = 2 # indication that a MEB slice was flushed in order to ensure that the MATRIX always has a free memory bank for storing new events. Observed in Continuous mode only.
    BUSY_VIOLATION     = 3 # indication that the chip is replying with an empty data packet due to saturation of data processing capabilities.
