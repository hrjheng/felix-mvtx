"""Class for accessing, configuring and controlling the DDG
"""

import os
from ROCEXT import *
from cru_table import *

class Ddg(RocExt):
    def __init__(self, pcie_opened_ch, verbose):
        RocExt.__init__(self,verbose)
        RocExt.ch = pcie_opened_ch
        
        self.ctrlAddr = CRUADD['add_ddg_ctrl']
        self.ctrlAddr2 = CRUADD['add_ddg_ctrl2']
        self.ctrlAddr3 = CRUADD['add_ddg_ctrl3']
        self.trgMaskAddr = CRUADD['add_ddg_trgmask']



    def reset(self):
        """ Reset DDG """

        self.rocRdMWr(self.ctrlAddr, 31, 1, 0x1)
        self.rocRdMWr(self.ctrlAddr, 31, 1, 0x0)
        


    def configStream(self, mode="continuous"):
        """ Select between continuous or packetized stream """

        if mode == "continuous":
            self.rocRdMWr(self.ctrlAddr, 0, 1, 0x0)
        elif mode == "packet":
            self.rocRdMWr(self.ctrlAddr, 0, 1, 0x1)
        else:
            raise ValueError("Possible stream modes are continuous or packet")



    def useTpcEmu(self, useTpc=False):
        """ Enable TPC data format in continuous mode """

        if useTpc:
            self.rocRdMWr(self.ctrlAddr, 16, 1, 0x1)
        else:
            self.rocRdMWr(self.ctrlAddr, 16, 1, 0x0)



    def configPackets(self, rndSize=False, payloadLimit=508, rndRange=512, rndIdleBtw=False, rndIdleIn=False, trigger="internal", idleLength=4):
        """ 
        Configure packets:
         * Random packet sizes
         * Max size of payload in words
         * Size range of random sized packets
         * Random IDLE words between packets
         * If fixed, the number of IDLEs between packets (max 1023)
         * Random IDLE words in payload
         * Trigger mode: internal or ttc
        """

       # Save pause state for later
        pauseState = self.rocRd(self.ctrlAddr) >> 8 & 0x1
        self.pause()


        self.configStream("packet")


        # Random packet sizes
        if rndSize:
            self.rocRdMWr(self.ctrlAddr, 1, 1, 0x1)
        else:
            self.rocRdMWr(self.ctrlAddr, 1, 1, 0x0)
        
        # Random IDLE words between packets
        if rndIdleBtw:
            oldval = oldval | 0x4
            self.rocRdMWr(self.ctrlAddr, 2, 1, 0x1)
        else:
            self.rocRdMWr(self.ctrlAddr, 2, 1, 0x0)
        
        # Random IDLE words in payload
        if rndIdleIn:
            self.rocRdMWr(self.ctrlAddr, 3, 1, 0x1)
        else:
            self.rocRdMWr(self.ctrlAddr, 3, 1, 0x0)
        
        # Select trigger mode
        if trigger == "internal":
            self.rocRdMWr(self.ctrlAddr, 4, 1, 0x0)
        elif trigger == "ttc":
            self.rocRdMWr(self.ctrlAddr, 4, 1, 0x1)
        else:
            raise ValueError("Possible trigger modes are: internal or ttc")

        # Max size of payload in GBT words (0 - 511)
        self.rocRdMWr(self.ctrlAddr2, 16, 9, payloadLimit)

        # Set number of IDLEs between packets (0 to 1023)
        self.rocRdMWr(self.ctrlAddr2, 0, 10, idleLength) 

        # Set size range of random sized packets
        self.rocRdMWr(self.ctrlAddr3, 0, 9, rndRange-1)

        # Restore pause state
        self.rocRdMWr(self.ctrlAddr, 8, 1, pauseState)


    def selectTriggerBit(self, mask):
        """ Select which TTCPON bit triggers the packets 
        
        Args: 
         - mask: 32 bit mask (ANDed with TTYPE)

        """

        self.rocWr(self.trgMaskAddr, mask)
        newMask = self.rocRd(self.trgMaskAddr)
        self.vprint(hex(newMask))


    def pause(self):
        """ Pause packet sending """
        
        self.rocRdMWr(self.ctrlAddr, 8, 1, 0x1)

        
    def resume(self):
        """ Resume packet sending """

        self.rocRdMWr(self.ctrlAddr, 8, 1, 0x0)


    def sentPackets(self):
        """ Read number of sent packets (32-bit counter) """

        return self.rocRd(CRUADD['add_ddg_pkt_cnt'])        


    def missedTriggers(self):
        """ Read number of missed triggers (32-bit counter)"""

        return self.rocRd(CRUADD['add_ddg_trgmiss_cnt'])        


  
    
