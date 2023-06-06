import argparse

from cru_table import *
from ROCEXT import *
from GBT import *
from DWRAPPER import *
from TTC import Ttc
from BSP import Bsp
from DDG import Ddg
from RO_CTRL import Ro_ctrl

class Cru(RocExt):
        def __init__(self, pcie_id, ch_range="all", verbose=False):
                RocExt.__init__(self,verbose)
                self.openROC(pcie_id, 2)

                self.gbt=Gbt(self._roc, ch_range, verbose)
                self.ttc = Ttc(self._roc, pcie_id, verbose)
                self.bsp = Bsp(self._roc, pcie_id, verbose)
                self.ro_ctrl = Ro_ctrl(self._roc, pcie_id, verbose)
                self.dwrapper=Dwrapper(self._roc, ch_range, 2, verbose)
                self.ddg = Ddg(self._roc, verbose)
                self.verbose = verbose

        def setGbtTxMux(self,channel):
                """ selects the TX GBT mux channel (DDG, TTC, or SC)"""
                if channel=="ttc":
                        sel=0
                elif channel=="ddg":
                        sel=1
                elif channel=="swt":
                        sel=2
                else:
                        raise ValueError("Invalid select option for GBT mux")

                for entry in self.gbt.links:
                                index, wrapper, bank, link, baseAddr = entry
                                reg=(index//16) # 2 bit per link, 16 links per reg
                                bit_offset=(index%16)*2
                                # print (index, wrapper, bank, link)
                                self.rocRdMWr(CRUADD['add_bsp_info_usertxsel']+reg*4,bit_offset, 2, sel)

        def getGbtTxMux(self):
                """ Gets TX GBT mux state for each link """

                muxes = []
                for entry in self.gbt.links:
                        index, wrapper, bank, link, baseAddr = entry
                        reg=(index//16) # 2 bit per link, 16 links per reg
                        bit_offset=(index%16)*2
                        txsel = (self.rocRd(CRUADD['add_bsp_info_usertxsel']+reg*4) >> bit_offset) & 0x3
                        
                        if txsel == 0:   
                                mux = "TTC"+":"+self.ttc.getDownstreamData()
                        elif txsel == 1: 
                                mux = "DDG"
                        elif txsel == 2: 
                                mux = "SWT"
                        else:
                                mux = "N/A"

                        if (self.rocRd(self.gbt.getRxCtrlAddress(wrapper, bank, link)) >> 16) & 0x1 == 1:
                                mux += ":SHORTCUT"

                        self.vprint("Link {}:  tx gbt mux: {}".format(index, mux))
                        muxes.append((index, mux))

                return muxes

        def report(self):
                """ Reports configured settings """

                self.ttc.printPllClockSel()
                print("------------------------------")

                modes = self.gbt.getGbtMode()
                muxes = self.getGbtTxMux()
                loopbacks = self.gbt.getLoopback()
                datapathModes = []
                numAllLinks = len(self.gbt.getLinkList())
                halfNumAllLinks = numAllLinks//2
                for entry in self.gbt.links:                        
                        index = entry[0]
                        dwrap = index // halfNumAllLinks
                        index = index % halfNumAllLinks
                        datapathModes.append((index, self.dwrapper.getGbtDatapathLink(dwrap, index)))

                enabledLinks = self.dwrapper.getEnabledLinks(numAllLinks)

                print("".rjust(9)        +"      GBT".rjust(9)+"      GBT".rjust(9)+"  Internal".rjust(10)+"\t"+"       ".rjust(11)+"\t"+"Datapath".rjust(10)+"\t"+"  Enabled in".rjust(12))
                print("Link ID ".rjust(9)+"  TX mode".rjust(9)+"  RX mode".rjust(9)+"  loopback".rjust(10)+"\t"+"GBT mux".rjust(11)+"\t"+"    mode".rjust(10)+"\t"+"    datapath".rjust(12))
                print("-----------------------------------------------------------------------------------------")
                for i in range(len(modes)):
                        print("Link {} :{}{}{}\t{}\t{}\t{}".format(modes[i][0].rjust(2), modes[i][1].rjust(9), modes[i][2].rjust(9), loopbacks[i].rjust(10), muxes[i][1].rjust(11), datapathModes[i][1].rjust(10), enabledLinks[i].rjust(12)))
                print("------------------------------")
                self.gbt.getTotalNumOfLinks()
                print("------------------------------")
                self.ttc.getClockFreq()
                self.gbt.getRefFrequencies()


