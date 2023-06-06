"""File describing the trigger types while the trigger hanlder class is not present"""

from enum import IntEnum, unique

@unique
class BitMap(IntEnum):
    """Trigger bit mapping as from gbtx_pkg.vhd"""
    ORBIT   = 0  # Orbit
    HB      = 1  # Heartbeat
    HBr     = 2  # Heartbeat reject (if 0: HB accept, if 1 HB reject)
    HC      = 3  # Health check
    PHYSICS = 4  # Physics Trigger
    PP      = 5  # Prepulse
    CAL     = 6  # Calibration
    SOT     = 7  # Start of triggered data
    EOT     = 8  # End of triggered data
    SOC     = 9  # Start of Continuous Data
    EOC     = 10 # End of Continuous Data
    TF      = 11 # Time Frame delimiter
    FE_RST  = 12 # Front end reset
    RT      = 13 # Run type
    RS      = 14 # Run status
