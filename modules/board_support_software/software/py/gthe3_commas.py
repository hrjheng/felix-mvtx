"""List of commas as defined in UG576 v1.6 table A-2"""

from enum import IntEnum, unique

@unique
class K28(IntEnum):
    p0 = 0b001111_0100
    m0 = 0b110000_1011
    p1 = 0b001111_1001
    m1 = 0b110000_0110
    p2 = 0b001111_0101
    m2 = 0b110000_1010
    p3 = 0b001111_0011
    m3 = 0b110000_1100
    p4 = 0b001111_0010
    m4 = 0b110000_1101
    p5 = 0b001111_1010
    m5 = 0b110000_0101
    p6 = 0b001111_0110
    m6 = 0b110000_1001
    p7 = 0b001111_1000
    m7 = 0b110000_0111

@unique
class K23(IntEnum):
    p7 = 0b111010_1000
    m7 = 0b000101_0111

@unique
class K27(IntEnum):
    p7 = 0b110110_1000
    m7 = 0b001001_0111

@unique
class K29(IntEnum):
    p7 = 0b101110_1000
    m7 = 0b010001_0111

@unique
class K30(IntEnum):
    p7 = 0b011110_1000
    m7 = 0b100001_0111
