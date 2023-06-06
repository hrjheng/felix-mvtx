import argparse
import time
import re
from ROCEXT import *
from cru_table import *
from EEPROM import Eeprom


class Bsp(RocExt):
        def __init__(self, pcie_opened_roc, pcie_id, verbose=False):
                RocExt.__init__(self,verbose)
                RocExt._roc = pcie_opened_roc

                self.verbose = verbose

        def enableRun(self):
                """ Enable datataking """
                self.rocRdMWr(CRUADD['add_bsp_info_userctrl'], 0, 1, 0x1)

        def disableRun(self):
                """ Disable datataking """
                self.rocRdMWr(CRUADD['add_bsp_info_userctrl'], 0, 1, 0x0)

        def disableRun(self):
                """ Disable datataking """
                self.rocRdMWr(CRUADD['add_bsp_info_userctrl'], 0, 1, 0x0)

        def resetClockTree(self):
                """ activate the reset for TTC pon, GBT and dwrapper"""
                self.rocRdMWr(CRUADD['add_bsp_info_userctrl'], 0, 1, 0x0) # deactivate RUN enable

                # Reset ONU first..
                self.rocRdMWr(CRUADD['add_onu_user_logic'], 0, 1, 0x1) # activate onu reset
                sleep(1)
                self.rocRdMWr(CRUADD['add_onu_user_logic'], 0, 1, 0x0) # deactivate onu reset

                # ..then reset core
                self.rocRdMWr(CRUADD['add_bsp_info_userctrl'], 1, 1, 0x1) # activate core reset
                sleep(1)
                self.rocRdMWr(CRUADD['add_bsp_info_userctrl'], 1, 1, 0x0) # deactivate core reset


        def getShortHash(self,verbose=False):
                """ get firmware short hash numer (32 bit) """
                val = self.rocRd(CRUADD['add_bsp_info_shorthash'])
                if verbose:
                        print ('fw hash={}').format(hex(val))
                return val

        def getDirtyStatus(self,verbose=False):
                """ get firmware git dirty status at build time """
                if self.rocRd(CRUADD['add_bsp_info_dirtystatus'])!=0:
                        val=True
                else:
                        val=False
                if verbose:
                        print ('fw dirty={}').format(val)
                return val

        def getBuildDate(self,verbose=False):
                """ get firmware build date """
                val = self.rocRd(CRUADD['add_bsp_info_builddate'])
                if verbose:
                        print ('build date {}'.format(hex(val)))
                return val

        def getBuildTime(self,verbose=False):
                """ get firmware build time """
                val = self.rocRd(CRUADD['add_bsp_info_buildtime'])
                if verbose:
                        print ('build time {}'.format(hex(val)))
                return val

        def getChipID(self,verbose=False):
                """ get Altera chip ID """
                idlow = self.rocRd(CRUADD['add_bsp_hkeeping_chipid_low'])
                idhigh = self.rocRd(CRUADD['add_bsp_hkeeping_chipid_high'])
                if verbose:
                        print ('Altera chip ID=0x{:08x}{:08x}').format(idhigh,idlow)
                return idhigh,idlow

        def getFwInfo(self):
                """ Gets firmware information (hash number, build date and time and altera Chip Id """
                idhigh,idlow=self.getChipID()
                print ('=========================================================================================')
                print ('>>> Firmware short hash=0x{:08x}'.format(self.getShortHash()))
                print ('>>> Firmware is dirty status= {}'.format(self.getDirtyStatus()))
                print ('>>> Firmware build date and time={:08X}  {:06X}'.format(self.getBuildDate(),self.getBuildTime()))
                print ('>>> Altera chip ID=0x{:08x}-0x{:08x}'.format(idhigh,idlow))
                print ('=========================================================================================')

        def isClk240alive(self):
                """ Checks if clk240 is active or stopped """
                val1 = self.rocRd(CRUADD['add_bsp_hkeeping_spare_in'])
                val2 = self.rocRd(CRUADD['add_bsp_hkeeping_spare_in'])
                if val1==val2 :
                        print ('Clock 240 MHz is stopped')
                        return True
                else:
                        print ('Clock 240 MHz is running')
                        return True


        def setCRUid(self,val):
                """ Set the CRU ID to be added in the RDH (12 bit value) """
                if val<0 or val>(1<<12)-1:
                    raise ValueError("BSP: bad CRUid setting")
                self.rocRdMWr(CRUADD['add_bsp_info_userctrl'], 16, 12, val)



        def ledBlinkLoop(self,mask=0xF):
                """ blink front panel LED """
                if mask<0 or mask>0xF:
                    raise ValueError("BSP: bad LED blinking mask (4 bit max)")
                try:
                    while True:
                       #print ("Blink on")
                       self.rocRdMWr(CRUADD['add_bsp_info_userctrl'], 3, 4, mask) # toggle LED value
                       sleep(0.2)
                       #print ("Blink off")
                       self.rocRdMWr(CRUADD['add_bsp_info_userctrl'], 3, 4, 0) # back to normal
                       sleep(0.2)
                except KeyboardInterrupt:
                    self.rocRdMWr(CRUADD['add_bsp_info_userctrl'], 3, 4, 0) # back to normal
                    return



        def hwCompatibleFw(self, pcie_id):
                """ Returns True if firmware was targeted for current hardware, False otherwise """

                # UTF-8 encoded byte -> character:
                #  76 -> 'v'
                #  32 -> '2'
                #  30 -> '0'
                v20 = 0x763230
                v22 = 0x763232

                targetHw = self.rocRd(CRUADD['add_bsp_info_boardtype'])

                eeprom = Eeprom(pcie_id)

                hwInfo = eeprom.readContent()

                # re.search() returns Match object if there's a match, None otherwise
                hwIsV22 = re.search("p40_.v22",hwInfo)

                isCompatible = (targetHw == v22 and hwIsV22) or (targetHw == v20 and not hwIsV22)

                if not isCompatible:
                        print("WARNING: Firmware-hardware mismatch, ", end='')
                        if targetHw == v22:
                                print("hardware type: v2.0 (pre-production), firmware is targeted for v2.2")
                        else:
                                print("hardware type: v2.2 (production), firmware is targeted for v2.0")
                        print("WARNING: PON upstream will not work (downstream still works)")

                return isCompatible
