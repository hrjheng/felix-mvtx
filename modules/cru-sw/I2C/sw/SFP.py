"""Class to access the SFP+ module

The following parameters are available:
 - vendor
 - part number
 - serial number
 - temperature
 - Vcc
 - Tx bias
 - Tx power
 - Rx power

"""

import math
from time import sleep
from I2C import I2c
from cru_table import *

class Sfp(I2c):
    def __init__(self, pcie_id):
        """Init I2C for accessing SFP+"""

        self.i2cInit(pcie_id, 2, CRUADD['add_bsp_i2c_sfp1'], 0x50)



    def getVendor(self):
        """ Get SFP+ vendor name """

        self.chip_add = 0x50
        self.resetI2C()

        reg_bank = []
        for reg_addr in range(20,36,2):
            reg_value1 = self.readI2C(reg_addr)
            if(reg_value1==-1):
                raise ValueError
                
            reg_value2 = self.readI2C(reg_addr+1)
            reg_bank.append(reg_value1)
            reg_bank.append(reg_value2)
        vendor_name = ''.join(chr(i) for i in reg_bank)
        return vendor_name
        


    def getPartNumber(self):
        """ Get SFP+ part number """

        self.chip_add = 0x50
        self.resetI2C()

        reg_bank = []
        for reg_addr in range(40,56,2):
            reg_value1 = self.readI2C(reg_addr)
            if(reg_value1==-1):
                raise ValueError

            reg_value2 = self.readI2C(reg_addr+1)
            reg_bank.append(reg_value1)
            reg_bank.append(reg_value2)
        vendor_part_number = ''.join(chr(i) for i in reg_bank)
        return vendor_part_number



    def getSerialNumber(self):
        """ Get SFP+ serial number """

        self.chip_add = 0x50
        self.resetI2C()

        reg_bank = []
        for reg_addr in range(68,84,2):
            reg_value1 = self.readI2C(reg_addr)
            if(reg_value1==-1):
                raise ValueError

            reg_value2 = self.readI2C(reg_addr+1)
            reg_bank.append(reg_value1)
            reg_bank.append(reg_value2)
        vendor_serial_number = ''.join(chr(i) for i in reg_bank)
        return vendor_serial_number
        


    def getTemperature(self):
        """ Get SFP+ temperature in Celsius """
        
        self.chip_add = 0x51
        self.resetI2C()

        # Read digital diagnostic
        reg_bank = []
        reg_addr = 96
        reg_value1  = self.readI2C(reg_addr) # MSB
        if(reg_value1==-1):
            raise ValueError

        reg_value2 = self.readI2C(reg_addr+1) # LSB
        reg_bank.append(reg_value1)
        reg_bank.append(reg_value2)

        temp = (reg_bank[0]<<8) + reg_bank[1]

        # TEMPERATURE:
        # 1) Internally measured transceiver temperature. Represented
        # as a 16 bit signed twos complement value in increments of
        # 1/256 degrees Celsius
        if(temp&0x8000):
            sign = -1
            temp_conv = (temp ^ 0xFFFF) + 1
        else:
            sign = 1
            temp_conv = temp
        temp_conv = sign*temp_conv*(1.0/256.0) # UNIT: degrees Celsius

        return temp_conv
        


    def getVcc(self):
        """ Get SFP+ voltage in Volt """

        self.chip_add = 0x51
        self.resetI2C()

        # Read digital diagnostic
        reg_bank = []
        reg_addr = 98
        reg_value1  = self.readI2C(reg_addr) # MSB
        if(reg_value1==-1):
            raise ValueError

        reg_value2 = self.readI2C(reg_addr+1) # LSB
        reg_bank.append(reg_value1)
        reg_bank.append(reg_value2)

        vcc     = (reg_bank[0]<<8) + reg_bank[1]

        # SUPPLY VOLTAGE:
        # 2) Internally measured transceiver supply
        # voltage. Represented as a 16 bit unsigned integer with the
        # voltage defined as the full 16 bit value (0-65535) with LSB
        # equal to 100 uVolt
        vcc_conv = (vcc*100e-6) # UNIT: V

        return vcc_conv
        


    def getTxBias(self):
        """ Get SFP+ Tx Bias in mA """

        self.chip_add = 0x51
        self.resetI2C()
        
        # Read digital diagnostic
        reg_bank = []
        reg_addr = 100
        reg_value1 = self.readI2C(reg_addr) # MSB
        if(reg_value1==-1):
            raise ValueError

        reg_value2 = self.readI2C(reg_addr+1) # LSB
        reg_bank.append(reg_value1)
        reg_bank.append(reg_value2)

        tx_bias = (reg_bank[0]<<8) + reg_bank[1]	

        # TX BIAS CURRENT:
        # 3) Measured TX bias current in uA. Represented as a 16 bit
        # unsigned integer with the current defined as the full 16 bit
        # value (0-65535) with LSB equal to 2 uA
        tx_bias_conv = (tx_bias*2e-6)*1e3 # UNIT: mA

        return tx_bias_conv



    def getTxPower(self):
        """ Get SFP+ Tx Power in dBm """

        self.chip_add = 0x51
        self.resetI2C()

        # Read digital diagnostic
        reg_bank = []
        reg_addr = 102
        reg_value1  = self.readI2C(reg_addr) # MSB
        if(reg_value1==-1):
            raise ValueError

        reg_value2 = self.readI2C(reg_addr+1) # LSB
        reg_bank.append(reg_value1)
        reg_bank.append(reg_value2)

        tx_pwr  = (reg_bank[0]<<8) + reg_bank[1]

        # TX OUTPUT POWER:
        # 4) Measured TX output power in mW. Represented as a 16 bit
        # unsigned integer with the power defined as the full 16 bit
        # value (0-65535) with LSB equal to 0.1 uW
        tx_pwr_conv = 10*math.log10((tx_pwr * 0.1 * 1e-6)/1e-3) # UNIT: dBm

        return tx_pwr_conv



    def getRxPower(self):
        """ Get SFP+ Rx power in dBm """

        self.chip_add = 0x51
        self.resetI2C()

        # Read digital diagnostic
        reg_bank = []
        reg_addr = 104
        reg_value1 = self.readI2C(reg_addr) # MSB
        if(reg_value1==-1):
            raise ValueError

        reg_value2 = self.readI2C(reg_addr+1) # LSB
        reg_bank.append(reg_value1)
        reg_bank.append(reg_value2)

        rx_pwr  = (reg_bank[0]<<8) + reg_bank[1]

        # RX RECEIVED OPTICAL POWER:
        # 5) Measured RX received optical power in mW. Value can
        # represent either average received power or OMA depending
        # upon how bit 3 of byte 92 (A0h) is set. Represented as a 16
        # bit unsigned integer with the power defined as the full 16
        # bit value (0-65535) with LSB equal to 0.1 uW
        if(rx_pwr>0):
            rx_pwr_conv = 10*math.log10((rx_pwr * 0.1 * 1e-6)/1e-3) # UNIT: dBm
        else:
            rx_pwr_conv = -1*float('inf')

        return rx_pwr_conv
