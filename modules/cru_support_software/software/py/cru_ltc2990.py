#!/usr/bin/env python

import logging

import time

from cru_i2c import CruI2c


class CruLtc2990(CruI2c):
    """
    WP10 port of LTC2990
    several functions imported from equivalent class in cru-sw subtree
    """

    VCC_MSB_ADD = 0xe
    VCC_LSB_ADD = 0xf
    TINT_MSB_ADD = 0x4
    TINT_LSB_ADD = 0x5
    V1_MSB_ADD = 0x6
    V1_LSB_ADD = 0x7
    V2_MSB_ADD = 0x8
    V2_LSB_ADD = 0x9
    V3_MSB_ADD = 0xa
    V3_LSB_ADD = 0xb
    V4_MSB_ADD = 0xc
    V4_LSB_ADD = 0xd

    def __init__(self, pcie_opened_roc, pcie_id, base_add, chip_add):
        """
        Default constructor
        """
        super(CruLtc2990, self).__init__(pcie_opened_roc=pcie_opened_roc,
                                          pcie_id=pcie_id,
                                          base_add=base_add,
                                          chip_add=chip_add)

        self.name = "LTC2990"
        self.logger = logging.getLogger("{0}".format(self.name))

        self.lastChipStatus = None
        self.lastControlReg = None

    def read_reg(self, add_h, add_l, checkReady=None):
        self.reset_i2c()
        max_read = 0
        dv = 0
        while dv == 0:
            val_l = self.read_i2c(add_l)
            val_h = self.read_i2c(add_h)
            dv = val_h >> 7
            val = (val_h << 8) | val_l
            max_read = max_read + 1
            if max_read == 10:
                break

        return val

    def calc_temperature(self, v):
        """
        To calculate temperature
        T = D[12:0]/16
        """
        v = v & 0x1fff
        val = self.two_comp13(v)
        val = val * 0.0625
        return val

    def calc_vcc(self, v):
        v = v & 0x3fff
        v = 2.5 + v * 305.18 * 1e-6
        return v

    def configure_chip_temperature(self):
        """
        Configure the chip to read 2 DIFF Voltages.
        Mode repeat
        Temp Celsius
        CONTROL REGISTER = 0x1 VALUE = 0x1D
        Mode[2:0] = 101 = TR1 and TR2
        Mode[4:3] = 11  = All Measurements per Mode[2:0]
        b7        = 0   = Temperature reported in Celsius
        b6        = 0   = Repeated Acquisition
        TRIGGER REGISTER = 0x2 VALUE = 0x7F (doesn't matter)
        Writing any value triggers a conversion. Data Returned reading this register address is the Status register
        """
        reg = 0x1d
        self.write_i2c(0x1, reg)

        reg = 0x7f
        self.write_i2c(0x2, reg)
        time.sleep(0.3)

    def configure_chip_volt_dif(self):
        reg = 0x1e
        self.write_i2c(0x1, reg)
        reg = 0x7f
        self.write_i2c(0x2, reg)
        time.sleep(0.3)

    def configure_chip_volt_single_ended(self):
        reg = 0x1f
        self.write_i2c(0x1, reg)
        reg = 0x7f
        self.write_i2c(0x2, reg)
        time.sleep(0.3)

    def calc_voltage(self, v):
        """
        VDIFFERENTIAL = D[14:0]  19.42 uV, if Sign = 0
        VDIFFERENTIAL = (~D[14:0] +1)  19.42 uV, if Sign = 1
        """
        v = v & 0x7fff
        val = self.two_comp15(v)
        val = val * 0.00030518
        return val

    def calc_diff_volt(self, v):
        rshunt = 0.003
        lsb_diff = 0.00001942
        factor = lsb_diff / rshunt

        val = - self.two_comp15(v)
        val = val * factor
        return val

    def check_chip_status(self):
        """
        BIT NAME                  OPERATION
        b7 0                      Always Zero
        b6 VCC   Ready            1 = VCC Register Contains New Data, 0 = VCC Register Read
        b5 V4    Ready            1 = V4 Register Contains New Data, 0 = V4 Register Read
        b4 V3, TR2, V3 - V4 Ready 1 = V3 Register Contains New Data, 0 = V3 Register Data Old
        b3 V2 Ready               1 = V2 Register Contains New Data, 0 = V2 Register Data Old
        b2 V1, TR1, V1  V2 Ready  1 = V1 Register Contains New Data, 0 = V1 Register Data Old
        b1 TINT Ready             1 = TINT Register Contains New Data, 0 = TINT Register Data Old
        b0 Busy*                  1= Conversion In Process, 0 = Acquisition Cycle Complete
        * In Repeat mode, Busy = 1 always
        """
        val = self.read_i2c(0x00)
        self.lastChipStatus = val
        return val

    def read_control_reg(self):
        """
        By DEFAULT = 0x0
        BIT NAME OPERATION
        b7 Temperature Format Temperature Reported In; Celsius = 0 (Default), Kelvin = 1
        b6 Repeat/Single Repeated Acquisition = 0 (Default), Single Acquisition = 1
        b5 Reserved Reserved
        b[4:3] Mode [4:3] Mode Description
              0 0        Internal Temperature Only (Default)
        b[2:0] Mode [2:0] Mode Description
              0 0 0      V1, V2, TR2 (Default)
        """
        val = self.read_i2c(0x01)
        self.lastControlReg = val
        return val

    def trigger_acq(self):
        self.write_i2c(0x2,0x1)

    def two_comp13(self, nb13bits):
        if nb13bits > 8191:
            print("Number is greater than 8191!!!")
            nb13bits = 8191

        if nb13bits <= 4095:
            return nb13bits
        else:
            return nb13bits - 8192

    def two_comp15(self, nb15bits):
        """
        All single-ended (V1,V2,V3,V4) or differential (V1-V2, V3-V4) tensions
        are in 15bits complemented to 2.
        So we need this conversion function
        """
        if nb15bits > 32767:
            print("Number is greater than 32767!!!")
            nb15bits = 32767
        if nb15bits <= 16383:
            return nb15bits
        else:
            return nb15bits - 32768
