#!/usr/bin/env python

import setThisPath

import abc


class MinipodBase(object):
    """ Base class for minipod RX/TX classes """
    
    __metaclass__ = abc.ABCMeta

    aux = None
    
    def __init__(self, pcie_id, bar_ch, base_add, chip_add, debug = None):
        """ Class constructor. Inits I2C communication. """

        self.i2cInit(pcie_id, bar_ch, base_add, chip_add)
        self.logfile_id = open('log.txt', 'w+')
        self.pcie_id = pcie_id
        self.bar_ch = bar_ch
        self.page = 0

    def __del__(self):
        self.logfile_id.close()

    def id(self):
        print(self.__class__.__name__)


    def setPage(self, page):
        self.page = page
        self.writeI2C(127, page)


    def extractBits(val):
        """ Extract bits of input byte """
        bit = [ (val >> i) & 1 for i in range(0, 8) ]
        return bit


    def twos_comp(val, bits):
        """compute the 2's compliment of int value val"""
        if (val & (1 << (bits - 1))) != 0: # if sign bit is set e.g., 8bit: 128-255
            val = val - (1 << bits)        # compute negative value
        return val


    def printReg(self, reg_add, val, bits, unique_txt = ''):
        if self.page == 0:
            reg_values = self.aux.reg_values_page0
        else:
            reg_values = self.aux.reg_values_page1

        reg_data = reg_values[reg_add]

        if len(reg_data[0]) == 0:
            print(unique_txt, file=self.logfile_id)
        else:
            print(reg_data[0][0]+hex(reg_add)+reg_data[0][1]+hex(val)+reg_data[0][2]+unique_txt, file=self.logfile_id)

        if unique_txt != '':
            print('', file=self.logfile_id)

        for i in range(1, len(reg_data)):
            indent = '\t\t\t\t\t\t'
            bit_idx = reg_data[i][0]
            info = reg_data[i][1]
            flags = reg_data[i][2]
            channel = reg_data[i][3]

            if(len(flags) == 4):
                bit1 = bits[bit_idx]
                bit0 = bits[bit_idx - 1]
                bin_val = int(str(bit1) + str(bit0), 2) #convert to binary then to integer
                bits2str = str(bit1)+' '+str(bit0)
            else:
                bin_val = bits[bit_idx]
                bits2str = str(bits[bit_idx])

            # if channel id is valid print it
            if(channel != None):
                indent = indent + 'CH ' + str(channel) + ' |'
            print(indent,  info, '|', flags[ bin_val ], '| '+bits2str, file=self.logfile_id)
            if len(reg_data) > 1:
                print('', file=self.logfile_id)

    
    def singleRead(self, reg_add, **kwargs):
        """ Reads single register, optionally prints register data """

        val = self.readI2C(reg_add)
        
        if 'extractBits' in kwargs:
            bits = self.extractBits(val)
        else:
            bits = 0

        if 'to_log_file' in kwargs:
            unique_txt = ''
            if 'unique_txt' in kwargs:
                unique_txt = kwargs['unique_txt']
            self.printReg(reg_add, val, bits, unique_txt)
            
        return val

    def doubleRead(self, reg_add, f,  **kwargs):
        """ Reads two adjacent registers and returns (reg value 1, reg value 2, f(reg value 1, reg value 2), optionally prints results """

        val1 = self.readI2C(reg_add)
        val2 = self.readI2C(reg_add+1)
        result = f(val1, val2)
        if 'extractBits' in kwargs:
            bits1 = self.extractBits(val1)
            bits2 = self.extractBits(val2)
        else:
            bits1 = 0
            bits2 = 0
            
        if 'to_log_file' in kwargs:
            self.printReg(reg_add, val1, bits1)
            if 'printResultIn' in kwargs:
                self.printReg(reg_add+1, val2, bits2, str(result) + kwargs['printResultIn']+'')
            else:
                self.printReg(reg_add+1, val2, bits2, '')

        return (val1, val2, result)

    def minipodReport(self, debug = None):
        """Report about minipod with given address"""

        self.resetI2C()
        self.setPage(0)

        print('\n\n')
        print('-------------------------')
        print(self.__class__.__name__, " ADD = ",hex(self.chip_add))
        print('-------------------------')

        self.minipodBasics()        
        self.minipodFeatures()
        self.minipodVendorDetails()
        self.minipodThresholds()
        self.minipodParameters()
        self.minipodFlags()
        self.minipodConfigRegs()
        self.minipodMaskRegs()



    def minipodFullReport(self, start_add, end_add, debug = None):
        """Report about a range of minipod addresses"""

        print('-------------------------------')
        print(self.__class__.__name__, ': Full report')
        print('PCIe ', self.pcie_id)
        print('BAR  ', hex(self.bar_ch))
        print('-------------------------------')
        print('')

        for current_add in range(start_add, end_add):
            self.minipodReport(current_add)



    def minipodBasics(self, debug = None):
        """Show minipod basics"""

        print(self.aux.basicsHeader, file=self.logfile_id)
        
        # get type identifier
        self.singleRead(128, to_log_file=True)


        # get module description
        self.singleRead(129, to_log_file=True, extractBits=True)
    

        # get required power supplies
        self.singleRead(130, to_log_file=True, extractBits=True)


        # get max short-term operating case temperature
        casetemp = self.singleRead(131)
        self.printReg(131, casetemp, 0, '\n\t\t\t\t\t\t'+str(casetemp)+' degC')


        # get minimum signal rate per channel
        min_sigrate = self.singleRead(132)
        self.printReg(132, min_sigrate, 0, '\n\t\t\t\t\t\t'+str(min_sigrate*100)+' Mb/s')


        # get maximum signal rate per channel
        max_sigrate = self.singleRead(133)
        self.printReg(133, max_sigrate, 0, '\n\t\t\t\t\t\t'+str(max_sigrate*100)+' Mb/s')


        # get nominal wavelength
        (reg1, reg2, nominal_wavelen) = self.doubleRead(134, (lambda x,y : (x << 8) + y))
        self.printReg(134, reg1, 0)
        self.printReg(135, nominal_wavelen, 0, str(nominal_wavelen/20)+' nm')
          

        # get wavelength tolerance
        (reg1, reg2, wavelen_tol) = self.doubleRead(136, (lambda x,y : (x << 8) + y))
        self.printReg(136, nominal_wavelen, 0)
        self.printReg(137, wavelen_tol, 0, str(wavelen_tol/200)+' nm')


        # print to standard output
        regvals = ''.join(chr(self.readI2C(x)) for x in range(152, 157))
        print('BASIC\tMAKE[',  regvals,']')

        regvals = ''.join(str(chr(self.readI2C(x))) for x in range(176, 179))

        print('\tPART[',       regvals,           ']')
        print('\tCASETMP[',    casetemp,           '] degC')
        print('\tSIG RATE[',   max_sigrate*100,'~', min_sigrate*100, '] Mb/s')
        print('\tWAVELENGTH[', nominal_wavelen/20, '] nm')
        print('\tTOLERANCE[',  wavelen_tol/200,    '] nm')

   

    def minipodFeatures(self, debug = None):
        """Show minipod features"""

        print(self.aux.featuresHeader, file=self.logfile_id)

        for reg_add in range(138, 144):
            self.singleRead(reg_add, to_log_file=True, extractBits=True)



    def minipodVendorDetails(self, debug = None):
        """Print minipod vendor details to logfile"""

        print(self.aux.vendorDetailsHeader, file=self.logfile_id)

        for i in range(0, len(self.aux.vendorDetails)):
            print(self.aux.vendorDetails[i][0], file=self.logfile_id)
            self.formatVendorDetails(self.aux.vendorDetails[i][1][0], self.aux.vendorDetails[i][1][1])


    def formatVendorDetails(self, start_reg, end_reg, debug = None):
        for reg in range(start_reg, end_reg):
            if reg >= 168 and reg <=171:
                val = hex(self.readI2C(reg))
            else:
                val = chr(self.readI2C(reg))
            print('\t\t\t', hex(reg), '\t[',val,']', file=self.logfile_id)


    def getTemperature(self):
        """ Returns internal temperature of the minipod """

        return self.doubleRead(28, lambda x,y: self.twos_comp(x, 8) + y * 0.00390625)[2]

         
        
    @abc.abstractmethod
    def minipodThresholds(self, debug = None):
        raise NotImplementedError


    @abc.abstractmethod
    def minipodParameters(self, debug = None):
        raise NotImplementedError


    @abc.abstractmethod
    def minipodFlags(self, debug = None):
        raise NotImplementedError


    @abc.abstractmethod
    def minipodConfigRegs(self, debug = None):
        raise NotImplementedError


    @abc.abstractmethod
    def minipodMaskRegs(self, debug = None):
        raise NotImplementedError

