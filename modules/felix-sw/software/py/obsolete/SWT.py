import sys
import time
from time import sleep

from flx_table import *

from flx_roc import Roc

class Swt (Roc):
    def __init__(self, card_nr, lock_mask , gbt_ch):
        """
        Class constructor. Init the addresses and the file name
        """
        self.open_card(card_nr, lock_mask)

        # set the channel
        self.roc_write(FLXADD['add_gbt_sc_link'], gbt_ch)
        # Check GBT TRG/SWT Fanout
        gbt_mux_cfg = self.roc_read(0x6720)
        assert ((gbt_mux_cfg >> gbt_ch) & 0x1) == 0, f"GBT channel {gbt_ch} is not configured as a SWT channel"
        # Disable GBT emulation data for both ToHost and ToFE fanout
        self.roc_rmw(0x6700, gbt_ch, 1 , 0) #toHost fanout
        self.roc_rmw(0x6710, gbt_ch, 1 , 0) #toFE   fanout

        self.wr_word_l = FLXADD['add_gbt_swt_wr_l']
        self.wr_word_h = FLXADD['add_gbt_swt_wr_h']

        self.rd_word_l = FLXADD['add_gbt_swt_rd_l']
        self.rd_word_h = FLXADD['add_gbt_swt_rd_h']

        self.rd_word_mon = FLXADD['add_gbt_swt_mon']

        self.swt_word_wr = FLXADD['add_gbt_swt_cmd']
        self.swt_word_rd = FLXADD['add_gbt_swt_cmd']


    #--------------------------------------------------------------------------------
    def wr(self, swt_word):
        """
        WRITE SWT WORD
        """
        l = swt_word & 0xffffffffffffffff
        h = swt_word >> 64
        self.roc_write(self.wr_word_l, l)
        self.roc_write(self.wr_word_h, h)
        # WR
        self.roc_write(self.swt_word_wr, 0x1)
        self.roc_write(self.swt_word_wr, 0x0)

        mon = self.roc_read(self.rd_word_mon)

        print('WR - MON %8s' % (hex(mon)))

    #--------------------------------------------------------------------------------
    def rd(self):
        """
        READ SWT WORD
        """
        # RD
        self.roc_write(self.swt_word_rd, 0x2)
        self.roc_write(self.swt_word_rd, 0x0)

        l = self.roc_read(self.rd_word_l)
        h = self.roc_read(self.rd_word_h)

        swt_rd = l + (h << 64)

        mon = self.roc_read(self.rd_word_mon)

        print('RD - DATA %20s \nMON %8s' % (hex(swt_rd), hex(mon)))

    #--------------------------------------------------------------------------------
    def reset(self):
        # Reset the CORE
        self.roc_write(FLXADD['add_gbt_sc_rst'], 0x1)
        self.roc_write(FLXADD['add_gbt_sc_rst'], 0x0)

