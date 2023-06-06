import time
from enum import IntEnum

from roc import Roc


class I2cCmdRegBits(IntEnum):
    """Definition of command register bits"""
    Reset = 0x8
    Scan  = 0x4
    Read  = 0x2
    Write = 0x1


class CruI2c(Roc):
    """
    Class to implement I2C transactions on the CRUADD, ported from ReadoutCard code:
    please see https://github.com/AliceO2Group/ReadoutCard/blob/master/src/Cru/I2c.cxx
    """
    def __init__(self, pcie_opened_roc, pcie_id, base_add, chip_add):
        """
        Class constructor. Init the I2C communication
        """
        Roc.__init__(self)
        self.set_roc(pcie_opened_roc)
        self.pcie_id = pcie_id

        self.i2c_cfg = base_add
        self.i2c_cmd = base_add + 4
        self.i2c_dat = base_add + 16

        self.chip_add = chip_add

        self.start_chip_add = 0x00
        self.end_chip_add = 0x7f

    def i2c_update_chip_address(self, chip_add):
        """
        Method to update the chip add
        """
        self.chip_add = chip_add

    def reset_i2c(self):
        """
        Reset the I2C core
        """
        self.roc_write(self.i2c_cmd, I2cCmdRegBits.Reset)
        self.roc_write(self.i2c_cmd, 0x0)

    def wait_i2c_ready(self):
        """
        Wait for the I2C CORE to be ready
        """
        max = 0
        val = 0
        while val == 0:
            val = self.roc_read(self.i2c_dat)
            val = (val >> 31) & 0x1
            time.sleep(1.0 / 10000.0)
            max = max + 1
            if max == 10:
                break

        return val

    def read_i2c(self, reg_add):
        """
        Function to execute an I2C READ operation.
        """
        val_32 = (self.chip_add << 16) + (reg_add << 8) + 0x0
        self.roc_write(self.i2c_cfg, val_32)
        #
        self.roc_write(self.i2c_cmd, I2cCmdRegBits.Read)
        self.roc_write(self.i2c_cmd, 0x0)
        #
        self.wait_i2c_ready()
        val = self.roc_read(self.i2c_dat)
        # The I2C data is only bit [7:0]
        val = val & 0xff
        return val

    def write_i2c(self, reg_add, data):
        """
        Function to execute a I2C WRITE operation.
        """
        val_32 = (self.chip_add << 16) | (reg_add << 8) | data
        self.roc_write(self.i2c_cfg, int(val_32))
        #
        self.roc_write(self.i2c_cmd, I2cCmdRegBits.Write)
        self.roc_write(self.i2c_cmd, 0x0)
        #
        self.wait_i2c_ready()

    def scan_i2c(self):
        """
        Function to execute an I2C scan.
        It returns the number of chips found of the I2C bus
        """
        valid_addresses = self.get_chip_addresses()
        chip_found = len(valid_addresses)

        return chip_found

    def get_chip_addresses(self):
        """Function to execute an I2C scan to find valid addresses"""
        chip_addresses = []
        for i in range(self.start_chip_add, self.end_chip_add + 1):
            self.reset_i2c()
            val32 = (i << 16) | 0x0000
            self.roc_write(self.i2c_cfg, int(val32))

            self.roc_write(self.i2c_cmd, I2cCmdRegBits.Write)
            self.roc_write(self.i2c_cmd, 0x0)

            self.wait_i2c_ready()
            addr_value = self.roc_read(self.i2c_dat)
            if addr_value >> 31 == 0x1:
                chip_addresses.append(addr_value)

        return addr_value
