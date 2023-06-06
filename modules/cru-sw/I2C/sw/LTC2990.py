#!/usr/bin/env python

import setThisPath

import time
from time import sleep

import I2C
from I2C import I2c

class Ltc2990(I2c) :
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
    
    def __init__(self, pcie_id, bar_ch, base_add, chip_add, debug = None):
        """
        Default constructor
        """                
        self.i2cInit(pcie_id, bar_ch, base_add, chip_add)
        self.lastChipStatus = None
        self.lastControlReg = None
    
    def readReg(self, add_h, add_l, checkReady=None, debug = None):
        self.resetI2C()
        max_read = 0
        dv = 0
        while dv == 0:
            val_l = self.readI2C(add_l)
            val_h = self.readI2C(add_h)
            dv = val_h >> 7
            val = (val_h << 8) | val_l
            max_read = max_read + 1
            if max_read == 10:
                break
            
        return val

    def calcTemp(self, v, debug = None):
        """
        To calculate temperature
        T = D[12:0]/16
        """
        v = v & 0x1fff
        val = self.two_comp13(v)
        val = val * 0.0625
        return val

    def calcVcc(self, v, debug = None):
        v = v & 0x3fff
        v = 2.5 + v * 305.18 * 1e-6
        return v

    def configureChipTemp(self, debug = None):
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
        if debug:
            print('CONFIGURE CHIP FOR TEMP ADD [', hex(self.chip_add), ']')
        reg = 0x1d
        self.writeI2C(0x1, reg)
        if debug:
            val = self.readI2C(reg)
            self.checkVal(0x1, reg, val)
        
        reg = 0x7f
        self.writeI2C(0x2, reg)
        time.sleep(0.3)

    def configureChipVoltDif(self, debug = None):
        if debug:
            print('CONFIGURE CHIP FOR VOLT DIFF ADD [', hex(self.chip_add), ']')
        reg = 0x1e
        self.writeI2C(0x1, reg)
        if debug:
            val = selg.readI2C(reg)
            checkVal(0x1, reg, val)
        
        reg = 0x7f
        self.writeI2C(0x2, reg)
        time.sleep(0.3)

    def configureChipVoltSingleEnded(self, debug = None):
        if debug:
            print('CONFIGURE CHIP FOR VOLT SINGLE ENDED ADD [', hex(self.chip_add), ']')
        reg = 0x1f
        self.writeI2C(0x1, reg)
        if debug:
            val = self.readI2C(reg)
            self.checkVal(0x1, reg, val)
        
        reg = 0x7f
        self.writeI2C(0x2, reg)
        time.sleep(0.3)

    def calcVoltage(self, v, debug = None):
        """
        VDIFFERENTIAL = D[14:0]  19.42 uV, if Sign = 0
        VDIFFERENTIAL = (~D[14:0] +1)  19.42 uV, if Sign = 1
        """
        v = v & 0x7fff
        val = self.two_comp15(v)
        val = val * 0.00030518
        return val

    def calcDiffVolt(self, v, debug = None):
        rshunt = 0.003
        lsb_diff = 0.00001942
        factor = lsb_diff/rshunt
        
        val = - self.two_comp15(v)
        val = val * factor
        return val

    def checkChipStatus(self, debug= None):
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
        val = self.readI2C(0x00)
        self.lastChipStatus = val
        return val

    def readControlReg(self, debug = None):
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
        val = self.readI2C(0x01)
        self.lastControlReg = val
        return val

    def triggerAcq(self, debug = None):
        self.writeI2C(0x2,0x1)
