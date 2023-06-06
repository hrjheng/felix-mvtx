#!/usr/bin/env python

import setThisPath

import I2C
from I2C import I2c

import time

class Si5338(I2c) :
    def __init__(self, pcie_id, bar_ch, base_add, chip_add, file_name, dump_file='/tmp/si5338_i2c.txt', debug = None):
        """
        Default constructor
        """
        self.file_dump = open(dump_file, 'w')
        self.file_name = file_name
        self.i2cInit(pcie_id, bar_ch, base_add, chip_add)

    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def configRefClk(self, debug = None):
        """ Configure reference input clock coming from the CRU """

        # These values configure the stable 40 MHz input clock (coming from the CRU). 
        # If not configured the input clock frequency is random and not correct, so
        # the PLL won't lock (the PLL_LOL signal asserts when the two PFD inputs 
        # have a frequency difference > 1000 ppm.)
        
        # Parameters:
        # 0x022c002X: config register address of ref clock and SMA monitor outputs
        # 0x11000000:  40 MHz
        # 0x11010000: 120 MHz
        # 0x11020000: 240 MHz

        # disabled for now - do not modify refclk output settings from i2c script
        # self.rocWr(0x022c0020, 0x11000000)
        # self.rocWr(0x022c0024, 0x11000000)

    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def resetPLL(self, debug = None):
        """
        Reset PLL
        """
        reg_add = 0xf6
        data = 0x02
        self.writeI2C(reg_add, data)
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------  
    def readPLL(self, debug = None):
        """
        Read PLL registers
        """
        self.file_dump.write('#REGISTER_MAP\n')
        for i in range(0, 255):
            val = self.readI2C(i)
            self.file_dump.write('%3d,%02Xh\n' % (i, val))
            
            print('REG : ', i)
    #--------------------------------------------------------------------------------
    
    #--------------------------------------------------------------------------------
    def disableAllClockOut(self, debug = None):
        """
        DISABLE ALL CLOCK OPUTPUT
        Set OEB_ALL = 1 reg230[4]
        REG 230 = 0xE6
        """
        reg_add = 0xe6
        data = 0x10
        self.writeI2C(reg_add, data)
        
        self.file_dump.write('----------------------------------\n')
        self.file_dump.write('Disable Clock out\n')
        self.file_dump.write('----------------------------------\n')

        val = self.readI2C(reg_add)
        ret = self.checkData(reg_add, data, val, self.file_dump)
        self.printRes('Disable Clock out', ret)
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def pauseLOL(self, debug = None):
        """
        PAUSE LOL
        Set DIS_LOL = 1 reg241[7]
        REG 241 = 0xF1
        """
        reg_add = 0xf1
        data = 0x80
        
        self.writeI2C(reg_add, data)
        
        self.file_dump.write('----------------------------------\n')
        self.file_dump.write('Pause LOL\n')
        self.file_dump.write('----------------------------------\n')

        val = self.readI2C(reg_add)
        ret = self.checkData(reg_add, data, val, self.file_dump)
        self.printRes('Pause LOL', ret)
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def configureInput(self, debug = None):
        """
        Configuring INPUT
        REG 6 - 28 - 29 - 30
        """
        reg_add_list = (0x06, 0x1c, 0x1d, 0x1e)
        #data_list    = (0x96, 0x90, 0xb0)
        data_list =  []
        data_list = self.getDataFromFile(reg_add_list, self.file_name)
        
        self.file_dump.write('----------------------------------\n')
        self.file_dump.write('Configure Input\n')
        self.file_dump.write('----------------------------------\n')
        
        # reg 0x06 has different write mask
        val = self.readI2C(0x06)        
        self.writeI2C(0x06, (data_list[0] & 0x1D) | val)
        val = self.readI2C(0x06)            
        ret = self.checkData(0x06, data_list[0], val, self.file_dump)

        if ret == 1:
            self.printRes('Configure Input', ret)
        

        for i in range(1, len(reg_add_list)):
            self.writeI2C(reg_add_list[i], data_list[i])

            val = self.readI2C(reg_add_list[i])
            
            ret = self.checkData(reg_add_list[i], data_list[i], val, self.file_dump)
            if ret == 1:
                self.printRes('Configure Input', ret)

        if ret == 0:
            self.printRes('Configure Input', ret)
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def configurePLL(self, debug = None):
        """
        Configuring the PLL
        REG 48 - 49 - 50 - 51
        """
        reg_add_list = (0x30, 0x31, 0x32, 0x33)
        #data_list    = (0x2f, 0x90, 0xc5, 0x07)
        data_list = []
        data_list = self.getDataFromFile(reg_add_list, self.file_name)
        
        self.file_dump.write('----------------------------------\n')
        self.file_dump.write('configurePLL\n')
        self.file_dump.write('----------------------------------\n')
        
        for i in range(len(reg_add_list)):
            self.writeI2C(reg_add_list[i], data_list[i])

            val = self.readI2C(reg_add_list[i])
            ret = self.checkData(reg_add_list[i], data_list[i], val, self.file_dump)
            if ret == 1:
                self.printRes('Configure PLL', ret)

        if ret == 0:
            self.printRes('Configure PLL', ret)
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def configureSynth(self, debug = None):
        """
        Configuring first and second stage synthesizer
        REG 97 - 98 - 99 - 100 - 101 - 102 - 103 - 104 - 105 - 106
        """
        reg_add_list = (0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6a)
        #data_list    = (0x00, 0x2e, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00)
        data_list = []
        data_list = self.getDataFromFile(reg_add_list, self.file_name)
    
        self.file_dump.write('----------------------------------\n')
        self.file_dump.write('configure Synt\n')
        self.file_dump.write('----------------------------------\n')
    
        for i in range(len(reg_add_list)-1):
            self.writeI2C(reg_add_list[i], data_list[i])

            val = self.readI2C(reg_add_list[i])
            ret = self.checkData(reg_add_list[i], data_list[i], val, self.file_dump)
            if ret == 1:
                self.printRes('Configure Synt', ret)

        # reg 0x6a has different write mask
        val = self.readI2C(0x6a)        
        self.writeI2C(0x6a, (data_list[-1] & 0xBF) | val)
        val = self.readI2C(0x6a)            
        ret = self.checkData(0x6a, data_list[-1], val, self.file_dump)
        if ret == 1:
            self.printRes('Configure Synt', ret)

    
        if ret == 0:
            self.printRes('Configure Synt', ret)
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def configureMSN(self, debug = None):
        """
        Configure MSN
        REG 53 - 54 - 55 - 56 - 57 - 58 - 59 - 60 - 61 - 62
        """
        reg_add_list = (0x35, 0x36, 0x37, 0x38, 0x39, 0x3a, 0x3b, 0x3c, 0x3d, 0x3e)
        #data_list    = (0x00, 0x1c, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00)
        data_list = []
        data_list = self.getDataFromFile(reg_add_list, self.file_name)
        
        self.file_dump.write('----------------------------------\n')
        self.file_dump.write('configure MSN\n')
        self.file_dump.write('----------------------------------\n')
        
        for i in range(len(reg_add_list)-1):
            self.writeI2C(reg_add_list[i], data_list[i])

            val = self.readI2C(reg_add_list[i])
            ret = self.checkData(reg_add_list[i], data_list[i], val, self.file_dump)
            if ret == 1:
                self.printRes('Configure MSN', ret)

        # reg 0x3e has write mask 0x3F instead of 0xFF
        val = self.readI2C(0x3e)        
        self.writeI2C(0x3e, (data_list[-1] & 0x3F) | val)
        val = self.readI2C(0x3e)            
        ret = self.checkData(0x3e, data_list[-1], val, self.file_dump)
        if ret == 1:
            self.printRes('Configure MSN', ret)

                
        if ret == 0:
            self.printRes('Configure MSN', ret)
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def configureMS0(self, debug = None): 
        """
        Configure MS0
        REG 64 - 65 - 66 - 67 - 68 - 69 - 70 - 71 - 72 - 73
        """
        reg_add_list = (0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49)
        #data_list    = (0x00, 0x08, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00)
        data_list = []
        data_list = self.getDataFromFile(reg_add_list, self.file_name)
        
        self.file_dump.write('----------------------------------\n')
        self.file_dump.write('configure MS0\n')
        self.file_dump.write('----------------------------------\n')
        
        for i in range(len(reg_add_list)-1):
            self.writeI2C(reg_add_list[i], data_list[i])
            val = self.readI2C(reg_add_list[i])
            ret = self.checkData(reg_add_list[i], data_list[i], val, self.file_dump)
            if ret == 1:
                self.printRes('Configure MS0', ret)

        # reg 0x49 has write mask 0x3F instead of 0xFF
        val = self.readI2C(0x49)        
        self.writeI2C(0x49, (data_list[-1] & 0x3F) | val)
        val = self.readI2C(0x49)            
        ret = self.checkData(0x49, data_list[-1], val, self.file_dump)
        if ret == 1:
            self.printRes('Configure MS0', ret)

                
        if ret == 0:
            self.printRes('Configure MS0', ret)
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def configureMS1(self, debug = None):
        """
        Configure MS1
        REG 75 - 76 - 77 - 78 - 79 - 80 - 81 - 82 - 83 - 84
        """
        reg_add_list = (0x4b, 0x4c, 0x4d, 0x4e, 0x4f, 0x50, 0x51, 0x52, 0x53, 0x54)
        #data_list    = (0x00, 0x03, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00)
        data_list = []
        data_list = self.getDataFromFile(reg_add_list, self.file_name)
        
        self.file_dump.write('----------------------------------\n')
        self.file_dump.write('configure MS1\n')
        self.file_dump.write('----------------------------------\n')
        
        for i in range(len(reg_add_list)-1):
            self.writeI2C(reg_add_list[i], data_list[i])

            val = self.readI2C(reg_add_list[i])
            ret = self.checkData(reg_add_list[i], data_list[i], val, self.file_dump)
            if ret == 1:
                self.printRes('Configure MS1', ret)

        # reg 0x54 has write mask 0x3F instead of 0xFF
        val = self.readI2C(0x54)        
        self.writeI2C(0x54, (data_list[-1] & 0x3F) | val)
        val = self.readI2C(0x54)            
        ret = self.checkData(0x54, data_list[-1], val, self.file_dump)
        if ret == 1:
            self.printRes('Configure MS1', ret)


        if ret == 0:
            self.printRes('Configure MS1', ret)
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def configureMS2(self, debug = None):
        """
        Configure MS2
        REG 86 - 87 - 88 - 89 - 90 - 91 - 92 - 93 - 94 - 95
        """
        reg_add_list = (0x56, 0x57, 0x58, 0x59, 0x5a, 0x5b, 0x5c, 0x5d, 0x5e, 0x5f)
        #data_list    = (0x00, 0x0a, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00)
        data_list = []
        data_list = self.getDataFromFile(reg_add_list, self.file_name)
        
        self.file_dump.write('----------------------------------\n')
        self.file_dump.write('configure MS2\n')
        self.file_dump.write('----------------------------------\n')
        
        for i in range(len(reg_add_list)-1):
            self.writeI2C(reg_add_list[i], data_list[i])

            val = self.readI2C(reg_add_list[i])
            ret = self.checkData(reg_add_list[i], data_list[i], val, self.file_dump)
            if ret == 1:
                self.printRes('Configure MS2', ret)
        
        # reg 0x5f has write mask 0x3F instead of 0xFF
        val = self.readI2C(0x5f)        
        self.writeI2C(0x5f, (data_list[-1] & 0x3F) | val)
        val = self.readI2C(0x5f)            
        ret = self.checkData(0x5f, data_list[-1], val, self.file_dump)
        if ret == 1:
            self.printRes('Configure MS2', ret)

        if ret == 0:
            self.printRes('Configure MS2', ret)
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def configurePhase(self, debug = None):
        """
        Configuring phase
        REG 52 - 63 - 109 - 110 - 113 - 114 - 117 - 118 - 122
        """
        reg_add_list = (0x34, 0x3f, 0x6d, 0x6e, 0x71, 0x72, 0x75, 0x76, 0x7a)
        data_list = []
        data_list = self.getDataFromFile(reg_add_list, self.file_name)
        
        self.file_dump.write('----------------------------------\n')
        self.file_dump.write('configure Phase\n')
        self.file_dump.write('----------------------------------\n')
        
        # reg 0x34 and 0x3f have write mask 0x7F instead of 0xFF
        # Bits [6:5] and [1:0] are self-clearing in case of 10b or 11b values
        for i in [0,1]:
            val = self.readI2C(reg_add_list[i])        
            self.writeI2C(reg_add_list[i], (data_list[i] & 0x7F) | val)
            val = self.readI2C(reg_add_list[i])
            lower = (data_list[i] & 0x2) >> 1
            upper = (data_list[i] & 0x40) >> 6
            if lower == 1 or upper == 1:
                tmpdata = ((data_list[i] & 0x9C) | [data_list[i] & 0x3, 0x0][lower]) | ([data_list[i] & 0x60, 0x0][upper])
                ret = self.checkData(reg_add_list[i], tmpdata, val, self.file_dump)
            else:
                ret = self.checkData(reg_add_list[i], data_list[i], val, self.file_dump)
            if ret == 1:
                self.printRes('Configure Phase', ret)
            

        for i in range(2,len(reg_add_list)):
            self.writeI2C(reg_add_list[i], data_list[i])

            val = self.readI2C(reg_add_list[i])
            ret = self.checkData(reg_add_list[i], data_list[i], val, self.file_dump)
            if ret == 1:
                self.printRes('configure Phase', ret)
                
        if ret == 0:
            self.printRes('configure Phase', ret)

    def configureMisc(self):
        # writing miscellaneous registers

        # Write the fllowing register with bitmask 0xFF
        reg_add_list = [31,  32,  33,  34,  35,  40,
                        107, 111, 112, 115, 116, 119, 120, 121, 
                        123, 124, 125, 126, 127, 128, 152, 153, 
                        154, 155, 156, 157, 255]

        reg_add_list = sorted(reg_add_list + [i for i in range(160,218)])

        data_list = []
        data_list = self.getDataFromFile(reg_add_list, self.file_name)

        self.file_dump.write('----------------------------------\n')
        self.file_dump.write('configure MISC\n')
        self.file_dump.write('----------------------------------\n')
        
        for i in range(len(reg_add_list)):
            self.writeI2C(reg_add_list[i], data_list[i])

            val = self.readI2C(reg_add_list[i])
            ret = self.checkData(reg_add_list[i], data_list[i], val, self.file_dump)
            if ret == 1:
                self.printRes('configure MISC', ret)
                
        if ret == 0:
            self.printRes('configure MISC', ret)

        # registers with different bitmask
        for reg_add in [36, 37, 38, 39]:
            val = self.readI2C(reg_add) & 0x1F
            self.writeI2C(reg_add,self.getDataFromFile([reg_add],self.file_name)[0] | val)

        for reg_add in [41, 74, 85, 108]:
            val = self.readI2C(reg_add) & 0x7F
            self.writeI2C(reg_add,self.getDataFromFile([reg_add],self.file_name)[0] | val)

        for reg_add in [129, 158, 159]:
            val = self.readI2C(reg_add) & 0x0F
            self.writeI2C(reg_add,self.getDataFromFile([reg_add],self.file_name)[0] | val)

        reg_add = 27 
        val = self.readI2C(reg_add) & 0x80
        self.writeI2C(reg_add,self.getDataFromFile([reg_add],self.file_name)[0] | val)

        reg_add = 42
        val = self.readI2C(reg_add) & 0x3F
        self.writeI2C(reg_add,self.getDataFromFile([reg_add],self.file_name)[0] | val)

        reg_add = 95
        val = self.readI2C(reg_add) & 0x3F
        self.writeI2C(reg_add,self.getDataFromFile([reg_add],self.file_name)[0] | val)

        reg_add = 226
        val = self.readI2C(reg_add) & 0x04
        self.writeI2C(reg_add,self.getDataFromFile([reg_add],self.file_name)[0] | val)

        reg_add = 242
        val = self.readI2C(reg_add) & 0x02
        self.writeI2C(reg_add,self.getDataFromFile([reg_add],self.file_name)[0] | val)


    


    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def validateClock(self, debug = None):
        """
        Validate input clock status
        reg 218 = 0xda
        Bit mapping
        [4] PLL_LOL 
        [3] LOS_FDBK (loss of signal on feedback clock from IN5, 6 or IN4
        [2] LOS_CLKIN (loss of signal on input clock from IN1, 2 or IN3
        [0] SYS_CAL (device calibration in process)
        """
        reg_add = 0xda
        
        # wait while there's no input clock
        # works only if external clock is used e.g. no internal oscillator
        while ((self.readI2C(218) >> 2) & 1) == 1:
            print('Loss of signal on input clk, waiting...')
            print(bin(self.readI2C(218)))
            time.sleep(1)

        val = self.readI2C(218)
        print('\t Validate clock  --  OK')
        self.file_dump.write('----------------------------------\n')
        self.file_dump.write('Validate Clock\n')
        self.file_dump.write('----------------------------------\n')
        self.file_dump.write('RD %X\n' % val)
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def configurePLLLocking(self, debug = None):
        """
        Configure PLL LOCKING
        Set FCAL_OVRD_EN = 0 reg49[7]
        REG49 = 0x31
        """
        reg_add = 0x31
        data = 0x10
        self.writeI2C(reg_add, data)
        
        self.file_dump.write('----------------------------------\n')
        self.file_dump.write('Configure PLL locking\n')
        self.file_dump.write('----------------------------------\n')

        val = self.readI2C(reg_add)
        ret = self.checkData(reg_add, data, val, self.file_dump)
        self.printRes('Configure PLL locking', ret)
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def initiatePLLLocking(self, debug = None):
        """
        Initiate PLL LOCKING
        Set SOFT_RESET = 1 reg246[1]
        REG246 = 0xf6
        A soft reset will not download any pre-programmed NVM and will not change
        any register values in RAM
        The Soft reset performs the following sequence
        1) all output off except if programmed to be always on
        2) Internal calibration are done
        3) 25 ms is allowed for the PLL to lock
        4) Turn on all outputs that were off in step 1
        """
        reg_add = 0xf6
        data = 0x02
        self.writeI2C(reg_add, data)
        
        self.file_dump.write('----------------------------------\n')
        self.file_dump.write('Initiate PLL locking\n')
        self.file_dump.write('----------------------------------\n')

        # WAIT FOR 25 ms ... at least
        time.sleep(1000.0 / 1000.0)

        #check soft reset AFTER 25ms wait
        val = self.readI2C(reg_add)
        ret = self.checkData(reg_add, data, val, self.file_dump)
        self.printRes('Initiate PLL locking', ret)
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def restartLOL(self, debug = None):
        """
        RESTART LOL
        Set DIS_LOL = 0 reg241[7]
        Set reg241[6:0] to 0x65
        REG241 = 0xF1
        """
        reg_add = 0xf1
        data = 0x65
        self.writeI2C(reg_add, data)
        
        self.file_dump.write('----------------------------------\n')
        self.file_dump.write('Restart LOL\n')
        self.file_dump.write('----------------------------------\n')

        val = self.readI2C(reg_add)
        ret = self.checkData(reg_add, data, val, self.file_dump)
        self.printRes('Restart LOL', ret)
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def confirmPLLLocked(self, debug = None):
        """
        PLL is locked when PLL_LOL, SYS_CAL, and all other alarms are cleared
        """
        max_wait = 0
        reg_add = 0xda
        while True:
            val = self.readI2C(reg_add)
        
            val = int(val)
            sys_cal = val & 0x1
            los_clkin = (val >> 2) & 0x1
            los_fdbk = (val >> 3) & 0x1
            pll_lol = (val >> 4) & 0x1
            if (pll_lol == 0):
                break
            max_wait = max_wait + 1
            if max_wait == 10:
                print(' --- PLL not locked --- ')
                break
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def copyFCALvalues(self, debug = None) :
        # check first the values in the registers
        reg_add = 0xed
        val = self.readI2C(reg_add)
        #print '237 ', hex(val)
        reg_add = 0xec
        val = self.readI2C(reg_add)
        #print '236 ', hex(val)
        reg_add = 0xeb
        val = self.readI2C(reg_add)
        #print '235 ', hex(val)
        
        reg_add = 0x2f
        val = self.readI2C(reg_add)
        #print '47 ', hex(val)
        reg_add = 0x2e
        val = self.readI2C(reg_add)
        #print '46 ', hex(val)
        reg_add = 0x2d
        val = self.readI2C(reg_add)
        #print '45 ', hex(val)
        
        
        # Copy registers as follows:
        
        # 237[1:0] to 47[1:0]
        reg_r = 0x2f
        val_l = self.readI2C(0xed) & 0x3
        val_r = (self.readI2C(reg_r) >> 2) << 2 | val_l
        self.writeI2C(reg_r, val_r)
        val = self.readI2C(reg_r)
        ret = self.checkData(reg_r, val_r, val, self.file_dump)
        self.printRes('reg 237', ret)
        
        # 236[7:0] to 46[7:0]
        reg_r = 0x2e
        val_l = self.readI2C(0xec)
        self.writeI2C(reg_r, val_l)
        val = self.readI2C(reg_r)
        ret = self.checkData(reg_r, val_l, val, self.file_dump)
        self.printRes('reg 236', ret)
        
        # 235[7:0] to 45[7:0]
        reg_r = 0x2d
        val_l = self.readI2C(0xeb)
        self.writeI2C(reg_r, val_l)
        val = self.readI2C(reg_r)
        ret = self.checkData(reg_r, val_l, val, self.file_dump)
        self.printRes('reg 235', ret)

        # 0x14 to 47[7:2]
        reg_r = 0x2f
        val_r = (self.readI2C(reg_r) & 0x3) | 0x14
        self.writeI2C(reg_r, val_r)
        val = self.readI2C(reg_r)
        ret = self.checkData(reg_r, val_r, val, self.file_dump)
        self.printRes('reg 237up', ret)

    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def setPLLuseFCAL(self, debug = None):
        reg_add = 0x31

        data = 0x80    
        prev = self.readI2C(reg_add) & 0x7F
        data = data | prev 

        self.writeI2C(reg_add, data)
        
        self.file_dump.write('----------------------------------\n')
        self.file_dump.write('set PLL use FCAL\n')
        self.file_dump.write('----------------------------------\n')

        val = self.readI2C(reg_add)
        ret = self.checkData(reg_add, data, val, self.file_dump)
        self.printRes('set PLL use FCAL', ret)
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def enableAllOutput(self, debug = None):
        """
        ENABLE ALL OUTPUT
        Set OEB_ALL reg230[4]
        REG230 = 0xE6
        """
        reg_add = 0xe6
        prev = self.readI2C(reg_add) & 0xEF
        data = 0x00 | prev

        self.writeI2C(reg_add, data)
        
        self.file_dump.write('----------------------------------\n')
        self.file_dump.write('enable Ouput\n')
        self.file_dump.write('----------------------------------\n')

        val = self.readI2C(reg_add)
        ret = self.checkData(reg_add, data, val, self.file_dump)
        self.printRes('enable Ouput', ret)
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def closeFile(self, debug = None):
        self.file_dump.close()
    #--------------------------------------------------------------------------------
