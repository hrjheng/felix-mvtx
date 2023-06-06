import time
import csv

import I2C
from I2C import I2c



class Si534x(I2c) :
    def __init__(self, pcie_id, bar_ch, base_add, chip_add, file_name, dump=None, debug = None):
        """
        Default constructor
        """
        if dump:
            self.file_dump = open(dump, 'w')
        else:
            self.file_dump = None

        self.regmapfile = file_name
        self.i2cInit(pcie_id, bar_ch, base_add, chip_add)
        self.regmap = None


    def readRegmap(self):
        """ Read register map generated by ClockBuilder Pro """

        self.regmap = []
        with open(self.regmapfile) as fp:
            for line in fp:
                if line[0] == '#' or "Address" in line:
                    continue
                else:
                    self.regmap.append([int(x, 0) for x in line.split(',')])

    def configurePll(self):
        """ Writing register values generated by ClockBuilder Pro """

        self.readRegmap()

        self.resetI2C()
        # switch to page 0
        self.writeI2C(0x01, 0)

        # todo check device ready at 0x00FE
        currentPage = 0

        for reg in self.regmap:
            # change page if needed
            nextPage = reg[0] >> 8
            if nextPage != currentPage:
                self.resetI2C()

                self.writeI2C(0x01, nextPage)
                #print "Change to page", hex(nextPage)
                currentPage = nextPage
            #print hex(reg[0]), hex(reg[1])

            self.resetI2C()

            self.writeI2C(reg[0]&0xFF, reg[1])
            #print hex(self.readI2C(reg[0]&0xFF))
            if reg[0] == "0x0540":
                time.sleep(1)

        self.resetI2C()


    def readPllConfig(self):
        """ Read register values """

        self.resetI2C()
        # start on page 0
        self.writeI2C(0x01, 0)

        pages = [0, 1, 2, 3, 4, 5, 6, 7, 9]
        for i, page in enumerate(pages):
            print("page", page, i)
            for reg in range(2,16):
                #self.resetI2C()
                print(hex(reg), hex(self.readI2C(reg)))

            # change page if needed
            self.writeI2C(0x01, i+1)


    def resetPll(self, hardReset=False):
        """ Reset PLL """

        self.resetI2C()
        # switch to page 0
        self.writeI2C(0x01, 0)

        if hardReset:
            self.writeI2C(0x1E, 0x2)
        else: # Soft reset and calibration
            self.writeI2C(0x1C, 0x1)


    def getInputInfo(self, show=False):
        """ Reports about enabled and selected inputs """

        self.resetI2C()
        self.writeI2C((0x0001), 5)
        clkSwitchMode = self.readI2C(0x36) & 0x3
        clkSelMode = self.readI2C(0x2A) & 0x1
        clkSel = self.readI2C(0x2A) >> 1 & 0x3

        if show:
            print("Clock switch mode is {}".format(["Manual", "Automatic non-revertive", "Automatic revertive", "Reserved"][clkSwitchMode]))
            print("Clock selection is {} controlled".format(["pin", "register"][clkSelMode]))
            print("Input clock {} is selected".format(clkSel))

        return (clkSwitchMode, clkSelMode, clkSel)

    def reportStatus(self, showSticky = False):
        """ check all status registers for error """

        self.resetI2C()
        # switch to page 0
        self.writeI2C(0x01, 0)

        val = self.readI2C(0x0C)  # - device is calibrating, no signal at XAXB pins XAXB_ERR, SMBUS_TIMEOUT
        print("     SYSINCAL : ", ["OK", "NOT OK - Device is calibrating"][val & 0x1])
        print("      LOSXAXB : ", ["OK", "NOT OK - No signal at XAXB pins"][(val >> 1) & 0x1])
        print("     XAXB_ERR : ", ["OK", "NOT OK - Problem with locking to XAXB signal"][(val >> 3) & 0x1])
        print("SMBUS_TIMEOUT : ", ["OK", "NOT OK - SMBus timeout error"][(val >> 5 ) & 0x1])

        val = self.readI2C(0x0D)  # - clock LOS, OOF
        for i in range(4):
            print("      LOS IN%d : "%i, ["OK", "NOT OK - clock input IN%d Loss Of Signal" % i][(val >> i) & 0x1])
        for i in range(4):
            print("      OOF IN%d : "%i, ["OK", "NOT OK - clock input IN%d Out Of Frequency" % i][(val >> (i+4)) & 0x1])

        val = self.readI2C(0x0E)  # - DSPLL out of lock or holdover
        print("          LOL : ", ["OK", "NOT OK - DSPLL is out of lock"][(val >> 1) & 0x1])
        print("         HOLD : ", ["OK", "NOT OK - DSPLL is in holdover (or freerun)"][(val >> 5) & 0x1])

        val = self.readI2C(0x0F)  # - DSPLL internal calibration is busy
        print("      CAL_PLL : ", ["OK", "NOT OK - DSPLL internal clibration is busy"][(val >> 5) & 0x1])

        if showSticky:
            print("\n Sticky bits")
            val = self.readI2C(0x11)  # - sticky bits
            print("     SYSINCAL_FLG : ", ["OK", "NOT OK - Device is calibrating"][val & 0x1])
            print("      LOSXAXB_FLG : ", ["OK", "NOT OK - No signal at XAXB pins"][(val >> 1 ) & 0x1])
            print("     XAXB_ERR_FLG : ", ["OK", "NOT OK - Problem with locking to XAXB signal"][(val >> 3) & 0x1])
            print("SMBUS_TIMEOUT_FLG : ", ["OK", "NOT OK - SMBus timeout error"][(val >> 5) & 0x1])

            val = self.readI2C(0x12)  # - sticky bits
            for i in range(4):
                print("          LOS_FLG : ", ["OK", "NOT OK - clock input IN%d Loss Of Signal" % i][(val >> i) & 0x1])
            for i in range(4):
                print("          OOF_FLG : ", ["OK", "NOT OK - clock input IN%d Out Of Frequency" % i][(val >> (i+4)) & 0x1])

            val = self.readI2C(0x13)  # - sticky bits
            print("          LOL_FLG : ", ["OK", "NOT OK - DSPLL was out of lock"][(val >> 1 )& 0x1])
            print("         HOLD_FLG : ", ["OK", "NOT OK - DSPLL was in holdover (or freerun)"][(val >> 5)  & 0x1])


            val = self.readI2C(0x14)  # - sticky bits
            print("      CAL_PLL_FLG : ", ["OK", "NOT OK - DSPLL internal clibration was busy"][(val >> 5) & 0x1])

        self.getInputInfo(True)


    def clearSticky(self):
        """ Clear sticky status bits """

        val = self.readI2C(0x11)  # - sticky bits
        val = val & 0xD4
        self.writeI2C(0x11, val)

        val = self.readI2C(0x12)  # - sticky bits
        self.writeI2C(0x12, 0x0)

        val = self.readI2C(0x13)  # - sticky bits
        val = val & 0xDD
        self.writeI2C(0x13, val)

        val = self.readI2C(0x14)  # - sticky bits
        val = val & 0xDF

        self.writeI2C(0x14, val)

    #--------------------------------------------------------------------------------
    def closeFile(self, debug = None):
        self.file_dump.close()
    #--------------------------------------------------------------------------------
