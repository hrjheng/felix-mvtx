#!/usr/bin/env python

import setThisPath

import I2C
from I2C import I2c

class Max1619(I2c) :
    def __init__(self, pcie_id, bar_ch, base_add, chip_add, debug = None):
        self.i2cInit(pcie_id, bar_ch, base_add, chip_add)
        self.lastTempLocal = None
        self.lastTempRemote = None
        self.lastStatusByte = None
        self.lastConfigByte = None
        self.lastConversionByte = None

        # RLTS = Read Local Temperature
        # RRTE = Read Remote Temperature
        # RSL  = Read Status Byte
        # RCL  = Read Configuration Byte
        # RCRA = Read Conversion rate byte
        self.RLTS_ADDRESS = 0
        self.RRTE_ADDRESS = 1
        self.RSL_ADDRESS = 2
        self.RCL_ADDRESS = 3
        self.RCRA_ADDRESS = 4

        # RRTM = Read Remote Tmax Limit
        # RRTH = Read Remote Thyst Limit
        # RRHI = Read Remote Thigh Limit
        # RRLS = Read Remote Tlow Limit
        self.RRTM_ADDRESS = 16
        self.RRTH_ADDRESS = 17
        self.RRHI_ADDRESS = 7
        self.RRLS_ADDRESS = 8

        # WCA  = Write Configuration Byte
        # WCRW = Write Conversion Rate Byte
        # WRTM = Write Remote Tmax Limit
        # WRTH = Write Remote Thyst Limit 
        # WRHA = Write Remote Thigh Limit 
        # WRLN = Write Remote Tlow Limit
        self.WCA_ADDRESS = 9
        self.WCRW_ADDRESS = 10
        self.WRTM_ADDRESS = 18
        self.WRTH_ADDRESS = 19
        self.WRHA_ADDRESS = 13
        self.WRLN_ADDRESS = 14

        # OSHT = One Shot Command
        self.OSHT_ADDRESS = 15

        # SPOR   = Write software POR
        # WADD   = Write Address
        # MFG_ID = Read Manufacturer ID Code
        # DEV_ID = Read Device ID Code
        self.SPOR_ADDRESS = 252
        self.WADD_ADDRESS = 253
        self.MFG_ID_ADDRESS = 254
        self.DEV_ID_ADDRESS = 255

    #--------------------------------------------------------------------------------
    def readMFGID(self, debug = None):
        """
        Read Manufacturer ID Code
        """
        ret = self.readI2C(self.MFG_ID_ADDRESS)
        return ret
    #--------------------------------------------------------------------------------
    #--------------------------------------------------------------------------------
    def readDEVID(self, debug = None):
        """
        Read Device ID Code
        """
        ret = self.readI2C(self.DEV_ID_ADDRESS)
        return ret
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def readLocalTemperature(self, debug = None):
        """
        Read Local Temperature 
        """
        ret = self.readI2C(self.RLTS_ADDRESS)
        self.lastTempLocal = ret
        return ret
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def readRemoteTemperature(self, debug = None):
        """
        Read Remote Temperature 
        """
        ret = self.readI2C(self.RRTE_ADDRESS)
        self.lastTempRemote = ret
        return ret
    #--------------------------------------------------------------------------------
    
    #--------------------------------------------------------------------------------
    def writeConversionRate(self, frequency, debug = None):
        """
        WriteConversionRate(between 0 and 7)
        """
        reg = self.WCRW_ADDRESS
        if frequency > 7:
            frequency = 3
            ret = self.writeI2C(reg, frequency)
            reg = self.RCRA_ADDRESS
            ret = self.readI2C(reg)
            return ret
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def readConversionRate(self, debug = None):
        """
        Read Conversion rate byte
        """
        reg = self.RCRA_ADDRESS
        ret =  self.readI2C(reg)
        self.lastConversionByte = ret 
        return ret
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def readStatusByte(self, debug = None):
        """
        Read Status Byte 
        """
        reg = self.RSL_ADDRESS
        ret = self.readI2C(reg)
        self.lastStatusByte = ret
        return ret
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def readConfigurationByte(self, debug = None):
        """
        Read Configuration Byte 
        """
        reg = self.RCL_ADDRESS
        ret = self.readI2C(reg)
        self.lastConfigByte = ret
        return ret



