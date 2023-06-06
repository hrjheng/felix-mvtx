import sys
import time
from time import sleep

from cru_table import *

import ROC
from ROC import Roc

import UTILS
from UTILS import Utils

class Swt (Utils, Roc):
    def __init__(self, pcie_id, bar_ch, gbt_ch, board):
        """
        Class constructor. Init the addresses and the file name
        """
        self.openROC(pcie_id, bar_ch)      
        
        self.base_add = CRUADD['add_gbt_sc']
        self.wr_word_l = CRUADD['add_gbt_swt_wr_l']
        self.wr_word_m = CRUADD['add_gbt_swt_wr_m']
        self.wr_word_h = CRUADD['add_gbt_swt_wr_h']

        self.rd_word_l = CRUADD['add_gbt_swt_rd_l']
        self.rd_word_m = CRUADD['add_gbt_swt_rd_m']
        self.rd_word_h = CRUADD['add_gbt_swt_rd_h']

        self.rd_word_mon = CRUADD['add_gbt_swt_mon']
        
        self.swt_word_wr = CRUADD['add_gbt_swt_cmd']
        self.swt_word_rd = CRUADD['add_gbt_swt_cmd']
        # set the channel
        self.rocWr(CRUADD['add_gbt_sc_link'], gbt_ch)


    #--------------------------------------------------------------------------------
    def wr(self, swt_word):
        """
        WRITE SWT WORD
        """
        l = swt_word & 0xffffffff
        m = (swt_word >> 32) & 0xffffffff
        h = swt_word >> 64
        self.rocWr(self.wr_word_l, l)
        self.rocWr(self.wr_word_m, m)
        self.rocWr(self.wr_word_h, h)
        # WR
        self.rocWr(self.swt_word_wr, 0x1)
        self.rocWr(self.swt_word_wr, 0x0)
        
        mon = self.rocRd(self.rd_word_mon)
        
        print('WR - MON %8s' % (hex(mon)))

    #--------------------------------------------------------------------------------
    def rd(self):
        """
        READ SWT WORD
        """
        # RD
        self.rocWr(self.swt_word_rd, 0x2)
        self.rocWr(self.swt_word_rd, 0x0)
        
        l = self.rocRd(self.rd_word_l)
        m = self.rocRd(self.rd_word_m)
        h = self.rocRd(self.rd_word_h)
        
        swt_rd = l + (m << 32) + (h << 64)
        
        mon = self.rocRd(self.rd_word_mon)
        
        print('RD - DATA %20s \nMON %8s' % (hex(swt_rd), hex(mon)))
                  
    #--------------------------------------------------------------------------------
    def reset(self):
        # Reset the CORE
        self.rocWr(CRUADD['add_gbt_sc_rst'], 0x1)
        self.rocWr(CRUADD['add_gbt_sc_rst'], 0x0)
        
