import sys
import time
from time import sleep

from cru_table import *

import ROC
from ROC import Roc

import UTILS
from UTILS import Utils

class Ic (Utils, Roc):
    def __init__(self, pcie_id, bar_ch, gbt_ch, debug = None):
        """
        Class constructor. Init the addresses and the file name
        """
        self.openROC(pcie_id, bar_ch, debug)

        self.base_add = 0x00F00000
        #if gbt_ch == 0 :
        #    self.base_add = 0x04224000
        #elif gbt_ch == 1:
        #    self.base_add = 0x04244000
        #elif gbt_ch == 2:
        #    self.base_add = 0x04264000
        #elif gbt_ch == 3:
        #    self.base_add = 0x04284000
        #else :
        #    self.base_add = 0x04224000
        
        self.wr_add_data = self.base_add + 0x20
        self.wr_add_cfg = self.base_add + 0x24
        self.wr_add_cmd = self.base_add + 0x28

        self.rd_add_data = self.base_add + 0x30

        # set the channel
        self.rocWr(CRUADD['add_gbt_sc_link'], gbt_ch, debug)
        # Reset the CORE
        self.rocWr(CRUADD['add_gbt_sc_rst'], 0x1, debug)
        self.rocWr(CRUADD['add_gbt_sc_rst'], 0x0, debug)

        # by default set it to 0x7
        self.rocWr(self.wr_add_cfg, 0x3, debug)
        
    #--------------------------------------------------------------------------------
    def wr(self, reg, data, debug = None):
        """
        Write data to IC
        DATA 8 bit
        REG ADD 16 bit

        in the current implementation you can write 1 word at the time
        """
        reg_add = reg & 0xffff
        data = (data & 0xff) << 16

        data = data + reg_add
        
        # Write to the FIFO
        self.rocWr(self.wr_add_data, data, debug)
        self.rocWr(self.wr_add_cmd, 0x1, debug)
        self.rocWr(self.wr_add_cmd, 0x0, debug)
        # Execute the WR SM
        self.rocWr(self.wr_add_cmd, 0x4, debug)
        self.rocWr(self.wr_add_cmd, 0x0, debug)
        time.sleep(0.01)
        # Read the status of the FIFO
        tmp = self.rocRd(self.rd_add_data, debug)
        gbt_add = (tmp >> 8) & 0xff
        data = tmp &  0xff
        empty = (tmp >> 16) & 0x1
        ready = (tmp >> 31) & 0x1
        print('ADD %s - DATA %s - EMPTY %s - READY %s' % (hex(gbt_add), hex(data), empty, ready))
        time.sleep(0.01)
      
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def wrGBTI2Cadd(self, data, debug = None):
        """
        Set the I2C GBT register
        """
        self.rocWr(self.wr_add_cfg, data, debug)
    #--------------------------------------------------------------------------------

    #--------------------------------------------------------------------------------
    def rd(self, reg, data, debug = None) :
        """
        Read the IC reply
        """
        reg_add = reg & 0xffff
        data = (data & 0xff) << 16
        
        data = data + reg_add
        
        # Write to the FIFO
        self.rocWr(self.wr_add_data, data, debug)
        self.rocWr(self.wr_add_cmd, 0x1, debug)
        self.rocWr(self.wr_add_cmd, 0x0, debug)
        time.sleep(0.01)
        # Start the RD SM
        self.rocWr(self.wr_add_cmd, 0x8, debug)
        self.rocWr(self.wr_add_cmd, 0x0, debug)
        time.sleep(0.01)
        # Pulse the read
        self.rocWr(self.wr_add_cmd, 0x2, debug)
        self.rocWr(self.wr_add_cmd, 0x0, debug)
        time.sleep(0.01)
        tmp = self.rocRd(self.rd_add_data, debug)
        gbt_add = (tmp >> 8) & 0xff
        data = tmp &  0xff
        empty = (tmp >> 16) & 0x1
        ready = (tmp >> 31) & 0x1
        print('RD: ADD %s - DATA %s - EMPTY %s - READY %s' % (hex(gbt_add), hex(data), empty, ready))
        return data
    #--------------------------------------------------------------------------------
    
    def rdfifo(self, debug = None) :
        tmp = self.rocRd(self.rd_add_data, debug)
        gbt_add = (tmp >> 8) & 0xff
        data = tmp &  0xff
        empty = (tmp >> 16) & 0x1
        ready = (tmp >> 31) & 0x1
        print('ADD %s - DATA %s - EMPTY %s - READY %s' % (hex(gbt_add), hex(data), empty, ready))
        self.rocWr(self.wr_add_cmd, 0x2, debug)
        self.rocWr(self.wr_add_cmd, 0x0, debug)
        tmp = self.rocRd(self.rd_add_data, debug)
        gbt_add = (tmp >> 8) & 0xff
        data = tmp &  0xff
        empty = (tmp >> 16) & 0x1
        ready = (tmp >> 31) & 0x1
        print('ADD %s - DATA %s - EMPTY %s - READY %s' % (hex(gbt_add), hex(data), empty, ready))

    def rdsm(self, debug = None):
         # Start the RD SM
        self.rocWr(self.wr_add_cmd, 0x8, debug)
        self.rocWr(self.wr_add_cmd, 0x0, debug)
        
