#!/usr/bin/env python

import setThisPath

"""
Minipod module for reading from and writing to Minipod's I2C addresses.

In the module 3 classes are defined:

Minipod: class for minipod RX specific functions, inherited from MinipodBase class (containing common 
features). It is the default class for the interface, but can change to TX mode during initialization

MinipodTx: class for minipod TX specific functions, inherited from MinipodBase class (containing common features)


"""

from I2C import *

from functools import partial, reduce
from itertools import chain

import MINIPODBASE as mp
from cru_table import *

# Default class is RX type, but it can be already change during init
class Minipod(I2c, mp.MinipodBase) : 
    def __init__(self, *args):
        """ Class constructor. """
        mp.MinipodBase.__init__(self, *args)

        self.resetI2C()
        
        val = self.readI2C(177)
        
        # 49 is utf-8 for '1' -> minipod is TX
        if val == 49: 
            self.aux = __import__("minipodtxaux")
            self.__class__ = MinipodTx
            
        # 50 is utf-8 for '2' -> minipod is RX
        elif val == 50: 
            self.aux = __import__("minipodrxaux")

        else:
            raise ValueError('Invalid minipod chip address is given!')

    @staticmethod
    def getMinipodAddresses(pcieid):
        """ returns a list with all the avaiable minipod cjip I2C addresses """

        chip_found = []
        
        # Scan for available minipods
        scan = I2c(pcieid, 2, CRUADD['add_bsp_i2c_minipods'], 0x0)
        for addr in range(scan.start_chip_add, scan.end_chip_add+1):
            scan.resetI2C()
            val_32 = (addr << 16) | 0x0
            scan.rocWr(scan.i2c_cfg, int(val_32))
            
            scan.rocWr(scan.i2c_cmd, 0x4)
            scan.rocWr(scan.i2c_cmd, 0x0)
            
            scan.waitI2Cready()
            
            val = scan.rocRd(scan.i2c_dat)
            val = scan.uns(val)
            if val >> 31 == 0x1:
                chip_found.append(addr)

        return chip_found

    def changeChip(self, chip_addr):
        self.i2cUpdateChipAdd(chip_addr)
        val = self.readI2C(177)
        if val == 49: # utf-8 for '1' -> TX
            self.aux = __import__("minipodtxaux")
            self.__class__ = MinipodTx
            
        elif val == 50: # utf-8 for '2' -> RX
            self.aux = __import__("minipodrxaux")

        else:
            raise ValueError('Invalid minipod chip address is given!')

        
    def minipodThresholds(self, debug = None):
        """Monitor minipod module thresholds"""

        print(self.aux.thresholdHeader, file=self.logfile_id)

        self.setPage(1)
        
        temperature = []
        values = []

        # get temperature alarm limits
        for reg_add in range(128, 132, 2):
            (reg1, reg2, result) = self.doubleRead(reg_add, (lambda x,y: self.twos_comp(x, 8) + y*0.00390625), to_log_file=True, printResultIn='degC') 
            values.append(reg1)
            values.append(reg2)
            temperature.append(result)

        values = []
        
        # get internal 3.3V and 2.5V alarm limits,       
        for reg_add in chain(range(144, 148, 2), range(152, 156, 2)):
            (reg1, reg2, result) = self.doubleRead(reg_add, lambda x,y: ((x << 8) + y)*0.0001, to_log_file=True, \
                                              printResultIn='V')
            values.append(result)

        # get RX optical power alarm limits
        for reg_add in range(184, 188, 2):
            (reg1, reg2, result) = self.doubleRead(reg_add, lambda x,y: ((x << 8) + y)*0.1, to_log_file=True, \
                                              printResultIn='uW')
            values.append(result)    
        
        # to standard output
        print(  'RANGE','  TEMP[',temperature[0],      '~',temperature[1],'] degC')
        print(          '\t3.3V[',values[0],'~',values[1],'] V')
        print(          '\t2.5V[',values[2],'~',values[3],'] V')
        print(          '\tPWR [',values[4],   '~',values[5],'] uW')

        self.setPage(0)



    def minipodParameters(self, debug = None):
        """Monitor minipod module parameters"""

        print(self.aux.parametersHeader, file=self.logfile_id)

        # get internal temperature
        int_temp = self.doubleRead(28, lambda x,y: self.twos_comp(x, 8) + y * 0.00390625, \
                              to_log_file=True, printResultIn='degC')[2]
        
        voltages = []
        powers = []
        
        # get internal 3.3V and 2.5V monitor values 
        for reg_add in range(32, 36, 2):
            (reg1, reg2, result) = self.doubleRead(reg_add, lambda x,y: ((x << 8) + y)*0.0001, to_log_file=True, \
                                              printResultIn='V')
            voltages.append(result)

        # get RX optical inputs
        for reg_add in range(64, 88, 2):
            (reg1, reg2, result) = self.doubleRead(reg_add, lambda x,y: ((x << 8) + y)*0.1, to_log_file=True, \
                                              printResultIn='V')
            powers.append(result)

        # get elapsed time
        timer = self.doubleRead(88, lambda x,y: ((x << 8) + y)*2, \
                           to_log_file=True, printResultIn='V')[2]

        # to standard output
        print(  'CURRENT',  'TEMP [', int_temp, '] degC')
        print(            '\tHIVOL[',voltages[0],'] V')
        print(            '\tLOVOL[',voltages[1],'] V')
        print(            '\tPWRo [',powers[0],'|',powers[1],'|',powers[2],'|',powers[3],'|',powers[4],'|',powers[5],'] uW')
        print(            '\t     [',powers[6],'|',powers[7],'|',powers[8],'|',powers[9],'|',powers[10],'|',powers[11],'] uW')
        print(            '\tETIME[',timer,'] hrs')



    def minipodFlags(self, debug = None):
        """Monitor minipod module flags"""

        print(self.aux.flagsHeader, file=self.logfile_id)

        alarms = [0]*4

        # get Rx channel LOS status for all channel 
        result = self.doubleRead(9, lambda x,y: ((x << 8) + y), \
                            to_log_file=True, extractBits=True)[2]
        
        alarms[0] = result & 0x0FFF

        (reg1, reg2, result) = self.doubleRead(13, lambda x,y: 0, \
                   to_log_file=True, extractBits=True)

        # get temperature alarm status
        alarms[1] = reg1 & 0xC0
        
        # get voltage alarm status
        alarms[2] = reg2 & 0xCC

        # get rx power alarm status
        power_alarms = []
        for reg_add in range(22, 28):
            val = self.singleRead(reg_add, to_log_file=True, extractBits=True)
            power_alarms.append(val & 0xCC)

        alarms[3] = reduce((lambda x, y: x & y), power_alarms)

        print('STATUS', end='')
        no_alarm = True
        for i in range(0, len(alarms)):
            if alarms[i] != 0:
                no_alarm = False
                print(self.aux.flagAlarms[i])

        if no_alarm:
            print('ALL OK')



    def minipodConfigRegs(self, debug = None):
        """ Monitor minipodp module configuration registers"""

        print(self.aux.configHeader, file=self.logfile_id)

        alarms = []

        # get rx channels' electrical output status
        for reg_add in range(92, 96, 2):
            result = self.doubleRead(reg_add, lambda x,y: ((x << 8) + y) & 0x0FFF, \
                                to_log_file=True, extractBits=True)[2]
            alarms.append(result)
 
        # get rate select status
        values = []
        for reg_add in range(96, 99):
            val = self.singleRead(reg_add, to_log_file=True, extractBits=True)
            values.append(val)
             
        alarms.append(reduce((lambda x, y: x & y), values))
                
        self.setPage(1)

        # get IntL pulse/static mode
        val = self.singleRead(225, to_log_file=True, extractBits=True)

        if (self.extractBits(val)[0] == 1):
            alarms.append(0)
        else:
            alarms.append(1)
             
        # get output polarity
        flip_chs = self.doubleRead(226, lambda x,y: ((x << 8) + y) & 0x0FFF, \
                              to_log_file=True, extractBits=True)[2]

        alarms.append(flip_chs)
        
        # get rx output amplitude control,
        #     rX Output De-emphasis Control
        values = []
        for reg_add in range(228, 240):
            val = self.singleRead(reg_add, to_log_file=True, extractBits=True)
            valu = val >> 4
            vall = val & 0x0F
            values.append(val)

            # rx output amplitude
            if reg_add < 234:
                print('\t\t\t\t\t\tCH', 11 - (reg_add-228)*2, self.aux.vppd[valu], bin(val), file=self.logfile_id)
                print('\t\t\t\t\t\tCH', 10 - (reg_add-228)*2, self.aux.vppd[vall], bin(val), file=self.logfile_id)
            # rx output de-emphasis
            else:
                if(reg_add == 238):#todo default is 3 or 4??
                    lvld=3*0.85714285714285714285714285714286
                    print('\t\t\t\t\t\tCH', 3,'| DE-EMPSIS LVL |',lvld,'db |',bin(valu), file=self.logfile_id)
                else:
                    lvl = (valu*0.85714285714285714285714285714286)            
                    print('\t\t\t\t\t\tCH', 11 - (reg_add-234)*2,'| DE-EMPSIS LVL |',lvl,'db |',bin(valu), file=self.logfile_id)

                lvl = (vall*0.85714285714285714285714285714286)            
                print('\t\t\t\t\t\tCH', 10 - (reg_add-234)*2,'| DE-EMPSIS LVL |',lvl,'db |',bin(vall), file=self.logfile_id)

        out_amp = reduce((lambda x, y: x & y), values[:7])
        if (out_amp == 0x44):
            alarms.append(0)
        else:
            alarms.append(1)

        de_empsis = reduce((lambda x, y: x & y), values[7:])
        if (de_empsis == 0x33):
            alarms.append(0)
        else:
            alarms.append(1)

        # to std output
        print('CHANNEL', end='')
        no_alarm = True
        for i in range(0, len(alarms)):
            if alarms[i] != 0:
                no_alarm = False
                print(self.aux.configAlarms[i])
        
        if no_alarm:
            print('\tALL OK')

        self.setPage(0)



    def minipodMaskRegs(self, debug = None):
        """Monitor minipod module mask registers"""

        print(self.aux.maskHeader, file=self.logfile_id)

        alarms = [0]*4

        # get channels' mask LOS
        alarms[0] = self.doubleRead(112, lambda x,y: ((x << 8) + y) & 0x0FFF, \
                              to_log_file=True, extractBits=True)[2]

        # get internal temperature alarm mask
        val = self.singleRead(116, to_log_file=True, extractBits=True)
        alarms[1] = val & 0xC0

        # get internal 3.3V and 2.5V alarm mask
        val = self.singleRead(117, to_log_file=True, extractBits=True)
        alarms[2] = val & 0xCC

        self.setPage(1)

        # get rx power alarm mask
        values = []
        for reg_add in range(250, 256):
            val = self.singleRead(reg_add, to_log_file=True, extractBits=True)
            values.append(val)

        alarms[3] = reduce((lambda x, y: x & y), values)

        # to std output
        print('MASK',end='')
        no_alarm = True
        for i in range(0, len(alarms)):
            if alarms[i] != 0:
                no_alarm = False
                print(maskAlarms[i])

        if no_alarm:
            print('\tALL OK')

        self.setPage(0)
                   




#==============================================
#==============================================
#==============================================
#==============================================





class MinipodTx(I2c, mp.MinipodBase) : 
    def __init__(self, *args):
        """ Class constructor. """
        mp.MinipodBase.__init__(self, *args)

        val = self.readI2C(177)
        if val == 49: # utf-8 for '1' -> TX
            self.aux = __import__("minipodtxaux")
            
        elif val == 50: # utf-8 for '2' -> RX
            self.aux = __import__("minipodrxaux")
            self.__class__ = Minipod
        else:
            raise ValueError('Invalid minipod chip address is given!')


    def changeChip(self, chip_addr):
        self.i2cUpdateChipAdd(chip_addr)
        val = self.readI2C(177)
        if val == 49: # utf-8 for '1' -> TX
            self.aux = __import__("minipodtxaux")
            
        elif val == 50: # utf-8 for '2' -> RX
            self.aux = __import__("minipodrxaux")
            self.__class__ = MinipodTx

        else:
            raise ValueError('Invalid minipod chip address is given!')



    def minipodThresholds(self, debug = None):
        """Monitor minipod module thresholds"""

        print(self.aux.thresholdHeader, file=self.logfile_id)

        self.setPage(1)
        
        temperature = []
        values = []

        # get temperature alarm limits
        for reg_add in range(128, 132, 2):
            (reg1, reg2, result) = self.doubleRead(reg_add, (lambda x,y: self.twos_comp(x, 8) + y*0.00390625), to_log_file=True, printResultIn='degC') 
            values.append(reg1)
            values.append(reg2)
            temperature.append(result)

        values = []
        
        # get internal 3.3V and 2.5V alarm limits,       
        for reg_add in chain(range(144, 148, 2), range(152, 156, 2)):
            (reg1, reg2, result) = self.doubleRead(reg_add, lambda x,y: ((x << 8) + y)*0.0001, to_log_file=True, \
                                              printResultIn='V')
            values.append(result)

        # get TX bias current alarm limits
        for reg_add in range(176, 180, 2):
            (reg1, reg2, result) = self.doubleRead(reg_add, lambda x,y: ((x << 8) + y)*2, to_log_file=True, \
                                              printResultIn='uA')
            values.append(result) 
            

        # get TX optical power alarm limits
        for reg_add in range(184, 188, 2):
            (reg1, reg2, result) = self.doubleRead(reg_add, lambda x,y: ((x << 8) + y)*0.1, to_log_file=True, \
                                              printResultIn='uW')
            values.append(result)    
        
        # to standard output
        print(  'RANGE','  TEMP [', temperature[0], '~', temperature[1],'] degC')
        print(          '\t3.3V [', values[0], '~', values[1], '] V')
        print(          '\t2.5V [', values[2], '~', values[3], '] V')
        print(          '\tBIASi[', values[4], '~', values[5], '] uA')
        print(          '\tPWR  [', values[6], '~', values[7], '] uW')

        self.setPage(0)
            


    def minipodParameters(self, debug = None):
        """Monitor minipod module parameters"""

        print(self.aux.parametersHeader, file=self.logfile_id)

        # get internal temperature
        int_temp = self.doubleRead(28, lambda x,y: self.twos_comp(x, 8) + y * 0.00390625, \
                              to_log_file=True, printResultIn='degC')[2]
        
        voltages = []
        powers = []
        bias = []
        
        # get internal 3.3V and 2.5V monitor values 
        for reg_add in range(32, 36, 2):
            (reg1, reg2, result) = self.doubleRead(reg_add, lambda x,y: ((x << 8) + y)*0.0001, to_log_file=True, \
                                              printResultIn='V')
            voltages.append(result)

        # get TX bias current monitor values 
        for reg_add in range(40, 64, 2):
            (reg1, reg2, result) = self.doubleRead(reg_add, lambda x,y: ((x << 8) + y)*2, to_log_file=True, \
                                                   printResultIn='uA')
            bias.append(result)

        # get TX light output monitor values
        for reg_add in range(64, 88, 2):
            (reg1, reg2, result) = self.doubleRead(reg_add, lambda x,y: ((x << 8) + y)*0.1, to_log_file=True, \
                                              printResultIn='V')
            powers.append(result)

        # get elapsed time
        timer = self.doubleRead(88, lambda x,y: ((x << 8) + y)*2, \
                           to_log_file=True, printResultIn='V')[2]

        # to standard output
        print(  'CURRENT',  'TEMP [', int_temp, '] degC')
        print(            '\tHIVOL[',voltages[0],'] V')
        print(            '\tLOVOL[',voltages[1],'] V')
        print(            '\tBIASi[',bias[0],'|',bias[1],'|',bias[2],'|',bias[3],'|',bias[4],'|',bias[5],'] uA')
        print(            '\t     [',bias[6],'|',bias[7],'|',bias[8],'|',bias[9],'|',bias[10],'|',bias[11],'] uA')
        print(            '\tPWRo [',powers[0],'|',powers[1],'|',powers[2],'|',powers[3],'|',powers[4],'|',powers[5],'] uW')
        print(            '\t     [',powers[6],'|',powers[7],'|',powers[8],'|',powers[9],'|',powers[10],'|',powers[11],'] uW')
        print(            '\tETIME[',timer,'] hrs')



    def minipodFlags(self, debug = None):
        """Monitor minipod module flags"""

        print(self.aux.flagsHeader, file=self.logfile_id)

        alarms = []

        # get Rx channel LOS status for all channel 
        result = self.doubleRead(9, lambda x,y: ((x << 8) + y), \
                            to_log_file=True, extractBits=True)[2]
        
        alarms.append(result & 0x0FFF)

        # get fault alarm status
        result = self.doubleRead(11, lambda x,y: ((x << 8) + y), \
                            to_log_file=True, extractBits=1)[2]

        alarms.append(result & 0x0FFF)


        # get temperature alarm status
        (reg1, reg2, result) = self.doubleRead(13, lambda x,y: 0, \
                   to_log_file=True, extractBits=True)

        alarms.append(reg1 & 0xC0)
        
        # get voltage alarm status
        alarms.append(reg2 & 0xCC)


        # get TX bias current alarm
        bias_alarms = []
        for reg_add in range(16, 22):
            val = self.singleRead(reg_add, to_log_file=True, extractBits=True)
            bias_alarms.append(val & 0xCC)

        alarms.append(reduce((lambda x, y: x & y), bias_alarms))

        # get rx power alarm status
        power_alarms = []
        for reg_add in range(22, 28):
            val = self.singleRead(reg_add, to_log_file=True, extractBits=True)
            power_alarms.append(val & 0xCC)

        alarms.append(reduce((lambda x, y: x & y), power_alarms))

        print('STATUS', end='')
        no_alarm = True
        for i in range(0, len(alarms)):
            if alarms[i] != 0:
                no_alarm = False
                print(self.aux.flagAlarms[i])

        if no_alarm:
            print('ALL OK')




    def minipodConfigRegs(self, debug = None):
        """ Monitor minipodp module configuration registers"""

        print(self.aux.configHeader, file=self.logfile_id)

        alarms = []

        # get tx channels' optical output status
        for reg_add in range(92, 96, 2):
            result = self.doubleRead(reg_add, lambda x,y: ((x << 8) + y) & 0x0FFF, \
                                to_log_file=True, extractBits=True)[2]
            alarms.append(result)
 

        # get margin activation mode
        marginmode = self.doubleRead(99, lambda x,y: ((x << 8) + y) & 0x0FFF, \
                                 to_log_file=True, extractBits=1)[2]
        alarms.append(marginmode)
                

        self.setPage(1)


        # get IntL pulse/static mode
        val = self.singleRead(225, to_log_file=True, extractBits=True)

        if (self.extractBits(val)[0] == 1):
            alarms.append(0)
        else:
            alarms.append(1)
             
        # get output polarity
        flip_chs = self.doubleRead(226, lambda x,y: ((x << 8) + y) & 0x0FFF, \
                              to_log_file=True, extractBits=True)[2]

        alarms.append(flip_chs)

        # get input equalization control
        values = []
        for reg_add in range(228, 234):#todo correct
            val = self.singleRead(reg_add, to_log_file=True)
            valu = val >> 4
            vall = val & 0x0F
            values.append(val)
            print('\t\t\t\t\t\tCH', 11 - (reg_add-228)*2, self.aux.db[valu], bin(val), file=self.logfile_id)
            print('\t\t\t\t\t\tCH', 10 - (reg_add-228)*2, self.aux.db[vall], bin(val), file=self.logfile_id)
  

        inp_equ = reduce((lambda x, y: x & y), values[:])
        if (inp_equ == 0x22):
            alarms.append(0)
        else:
            alarms.append(1)


        # to std output
        print('CHANNEL',end='')
        no_alarm = True
        for i in range(0, len(alarms)):
            if alarms[i] != 0:
                no_alarm = False
                print(self.aux.configAlarms[i])
        
        if no_alarm:
            print('\tALL OK')

        self.setPage(0)



    def minipodMaskRegs(self, debug = None):
        """Monitor minipod module mask registers"""

        print(self.aux.maskHeader, file=self.logfile_id)

        alarms = []

        # get channels' mask LOS
        alarms.append(self.doubleRead(112, lambda x,y: ((x << 8) + y) & 0x0FFF, \
                              to_log_file=True, extractBits=True)[2])

        # get mask fault tx
        alarms.append(self.doubleRead(114, lambda x,y: ((x << 8) + y) & 0x0FFF, \
                              to_log_file=True, extractBits=1)[2])    

        # get internal temperature alarm mask
        val = self.singleRead(116, to_log_file=True, extractBits=True)
        alarms.append(val & 0xC0)

        # get internal 3.3V and 2.5V alarm mask
        val = self.singleRead(117, to_log_file=True, extractBits=True)
        alarms.append(val & 0xCC)

        self.setPage(1)

        # get tx bias current mask
        bias = []
        for reg_add in range(244, 250):
            val = self.singleRead(reg_add, to_log_file=True, extractBits=True)
            bias.append(val)

        alarms.append(reduce((lambda x, y: x & y), bias))

        # get tx power alarm mask
        values = []
        for reg_add in range(250, 256):
            val = self.singleRead(reg_add, to_log_file=True, extractBits=True)
            values.append(val)

        alarms.append(reduce((lambda x, y: x & y), values))

        # to std output
        print('MASK', end='')
        no_alarm = True
        for i in range(0, len(alarms)):
            if alarms[i] != 0:
                no_alarm = False
                print(maskAlarms[i])

        if no_alarm:
            print('\tALL OK')

        self.setPage(0)
