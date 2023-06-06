import sys

import time
from time import sleep

import UTILS
from UTILS import Utils

import ROC
from ROC import Roc

class I2c(Utils, Roc) :
    def __init__(self, pcie_id, bar_ch, base_add, chip_add, debug = None):
        """
        Class constructore. Init the I2C communication
        """
        self.openROC(pcie_id, bar_ch, debug)

        self.i2c_cfg = base_add
        self.i2c_cmd = base_add + 4
        self.i2c_dat = base_add + 16

        self.chip_add = chip_add

        self.start_chip_add = 0x00
        self.end_chip_add = 0x7f

    def i2cInit(self, pcie_id, bar_ch, base_add, chip_add, debug = None):
        """
        Class constructore. Init the I2C communication
        """
        self.openROC(pcie_id, bar_ch, debug)

        self.i2c_cfg = base_add
        self.i2c_cmd = base_add + 4
        self.i2c_dat = base_add + 16

        self.chip_add = chip_add

        self.start_chip_add = 0x00
        self.end_chip_add = 0x7f

    def i2cUpdateChipAdd(self, chip_add, debug = None) :
        """
        Method to update the chip add
        """
        self.chip_add = chip_add

    def resetI2C(self, debug = None):
        """
        Reset the I2C core
        """
        self.rocWr(self.i2c_cmd, 0x8)
        self.rocWr(self.i2c_cmd, 0x0)

    def waitI2Cready(self, debug = None):
        """
        Wait for the I2C CORE to be ready
        """
        max = 0
        val = 0
        while (val == 0) :
            val = self.rocRd(self.i2c_dat)
            val = (val >> 31) & 0x1
            sleep(1.0 / 10000.0)
            max = max + 1
            if max == 10:
                break

        return val

    def readI2C(self, reg_add, debug = None):
        """
        Function to execute an I2C READ operation.
        """
        val_32 = (self.chip_add << 16) + (reg_add << 8) + 0x0
        self.rocWr(self.i2c_cfg, val_32)
        #
        self.rocWr(self.i2c_cmd, 0x2)
        self.rocWr(self.i2c_cmd, 0x0)
        #
        self.waitI2Cready()
        val = self.rocRd(self.i2c_dat)
        # The I2C data is only bit [7:0]
        val = val & 0xff
        return val

    def writeI2C(self, reg_add, data, debug = None):
        """
        Function to execute a I2C WRITE operation.
        """
        val_32 = (self.chip_add << 16) | (reg_add << 8) | data
        self.rocWr(self.i2c_cfg, int(val_32))
        #
        self.rocWr(self.i2c_cmd, 0x1)
        self.rocWr(self.i2c_cmd, 0x0)
        #
        self.waitI2Cready()


    def scanI2C(self, debug = None):
        """
        Function to execute an I2C scan.
        It returns the number of chips found of the I2C bus
        """
        chip_found = 0
        for i in range(self.start_chip_add, self.end_chip_add  + 1) :
            self.resetI2C()
            val_32 = (i << 16) | 0x0
            self.rocWr(self.i2c_cfg, int(val_32))
            #
            self.rocWr(self.i2c_cmd, 0x4)
            self.rocWr(self.i2c_cmd, 0x0)
            #
            self.waitI2Cready()
            val = self.rocRd(self.i2c_dat)
            val = self.uns(val)
            if val >> 31 == 0x1:
                print('ADD ', hex(i), ' CHIP FOUND [', hex(val),']')
                chip_found += 1
            else :
                sys.stdout.write('0x%X\r' % self.chip_add)
                sys.stdout.flush()

        return chip_found
