import argparse
from ROCEXT import *
from cru_table import *
import time

class Dwrapper(RocExt):
        def __init__(self, pcie_opened_roc, ch_range="all", wrapperCount=2, verbose=False):
                RocExt.__init__(self,verbose)
                RocExt._roc = pcie_opened_roc

                self.verbose = verbose
                if wrapperCount==1:
                        self.wrapperAddList=[CRUADD['add_base_datapathwrapper0']]
                else:
                        self.wrapperAddList=[CRUADD['add_base_datapathwrapper0'],CRUADD['add_base_datapathwrapper1']]

                #self.linkEnableMask(0)

        def linkEnableMask(self, wrapper, mask):
                """ Enable individual input link (0 to 15), HBAM 13, HDM 14, user logic 15.
                
                Enabling User logic, deactivate the individual channels from readout.
                
                """
                self.enable_reg=mask

                self.rocWr(self.wrapperAddList[wrapper] + CRUADD['add_dwrapper_gregs']+CRUADD['add_dwrapper_enreg'], self.enable_reg)

        def linkEnableBit(self, wrapper, link):
                """ Enable individual input link (0 to 15), HBAM 13, HDM 14, user logic 15

                Enabling User logic, deactivate the individual channels from readout.
                
                """
                add=self.wrapperAddList[wrapper] + CRUADD['add_dwrapper_gregs']+CRUADD['add_dwrapper_enreg']
                self.rocRdMWr(add, link, 1, 1)
                self.enable_reg=self.rocRd(add)
                #print ('enable_reg {} {}'.format(hex(add),hex(self.enable_reg)))


        def getEnabledLinks(self, numAllLinks):
                """ Get which datapath links are enabled """

                enabledLinks = []
                for w in self.wrapperAddList:
                        add = w + CRUADD['add_dwrapper_gregs']+CRUADD['add_dwrapper_enreg']
                        config = self.rocRd(add)
                        enabledLinks += ["Enabled" if ((config >> i) & 0x1) == 1 else "Disabled" for i in range(0, numAllLinks//len(self.wrapperAddList))]

                # if 2 dwrapper, odd number of links
                if len(self.wrapperAddList) == 2 and numAllLinks % 2 == 1:
                        add = self.wrapperAddList[1] + CRUADD['add_dwrapper_gregs']+CRUADD['add_dwrapper_enreg']
                        config = self.rocRd(add)
                        enabledLinks += ["Enabled" if ((config >> (numAllLinks//2)) & 0x1) == 1 else "Disabled"]

                return enabledLinks


        def useDynamicOffset(self, wrapper, en):
                """ Enable dynamic offset setting of the RDH (instead of fixed 0x2000)
                """
                add=self.wrapperAddList[wrapper] + CRUADD['add_dwrapper_gregs']+CRUADD['add_dwrapper_enreg']
                if en:
                    self.rocRdMWr(add, 31, 1, 1)
                else:
                    self.rocRdMWr(add, 31, 1, 0)
                self.enable_reg=self.rocRd(add)
                #print ('enable_reg {} {}'.format(hex(add),hex(self.enable_reg)))


        def getBigFifoLvl(self,doPrint=False):
                """ Reads big FIFO level """
                retdat=[]
                for w in self.wrapperAddList:
                        retdat.append(self.rocRd(self, w + CRUADD['add_dwrapper_gregs']+CRUADD['add_dwrapper_bigfifo_lvl']))

                if doPrint:
                        print ('Big fifo level is/are {}'.format(retdat))

                return retdat

        def getStatistics(self,doPrint=False):
                """ Reads Statistics counters"""
                stats=[]
                stats.append([])
                for w in self.wrapperAddList:
                        stats[0].append(self.rocRd(self, w + CRUADD['add_dwrapper_gregs']+CRUADD['add_dwrapper_tot_words']))

                stats.append([])
                for w in self.wrapperAddList:
                        stats[1].append(self.rocRd(self, w + CRUADD['add_dwrapper_gregs']+CRUADD['add_dwrapper_drop_words']))

                stats.append([])
                for w in self.wrapperAddList:
                        stats[2].append(self.rocRd(self, w + CRUADD['add_dwrapper_gregs']+CRUADD['add_dwrapper_tot_pkts']))

                stats.append([])
                for w in self.wrapperAddList:
                        stats[3].append(self.rocRd(self, w + CRUADD['add_dwrapper_gregs']+CRUADD['add_dwrapper_drop_pkts']))

                if doPrint:
                        print ('Statistics wrapper # are (tot words, drop words, tot pkt, drop pkt) {}'.format(stats))

                return stats

        def getLastHB(self,doPrint=False):
                """ Reads last HB received """
                retdat=[]
                for w in self.wrapperAddList:
                        retdat.append(self.rocRd(self, w + CRUADD['add_dwrapper_gregs']+CRUADD['add_dwrapper_lastHBID']))

                if doPrint:
                        print ('Last HB received is/are {}'.format(retdat))

                return retdat

        def setGbtDatapathLink(self,wrap=0,link=0,is_GBT_pkt=0,RAWMAXLEN=0x1FC):
                """ Configures GBT datapath links"""
                if RAWMAXLEN>0x1FC:
                        raise ValueError("Payload length should be less or equal to 0x1FC")
                val=0
                val|=RAWMAXLEN
                val|=(is_GBT_pkt<<31)

                add=self.wrapperAddList[wrap] + CRUADD['add_datapathlink_offset']+CRUADD['add_datalink_offset']*link+CRUADD['add_datalink_ctrl']
                #print ('Link config #{} {} {}'.format(link, hex(add), hex(val)))
                self.rocWr(add, val)


        def getGbtDatapathLink(self, wrap, link):
                """ Gets GBT datapath link configurations """

                add=self.wrapperAddList[wrap] + CRUADD['add_datapathlink_offset']+CRUADD['add_datalink_offset']*link+CRUADD['add_datalink_ctrl']
                val = self.rocRd(add) >> 31
                if val == 1:
                        return "packet"
                else:
                        return "continuous"


        def getGbtDatapathLinkCounters(self, wrap, link):
                """ Gets GBT datapath link counters """

                add=self.wrapperAddList[wrap] + CRUADD['add_datapathlink_offset']+CRUADD['add_datalink_offset']*link+CRUADD['add_datalink_rej_pkt']
                rej_pkt=self.rocRd(add) 

                add=self.wrapperAddList[wrap] + CRUADD['add_datapathlink_offset']+CRUADD['add_datalink_offset']*link+CRUADD['add_datalink_acc_pkt']
                acc_pkt=self.rocRd(add) 

                add=self.wrapperAddList[wrap] + CRUADD['add_datapathlink_offset']+CRUADD['add_datalink_offset']*link+CRUADD['add_datalink_forced_pkt']
                forced_pkt=self.rocRd(add) 

                print ("rejected packet ={}, accepted packets={} and forced packets ={}".format(rej_pkt,acc_pkt,forced_pkt))


        def setFlowControl(self,wrap=0,allowReject=0):
                """ Configures the flow control """
                val=0
                val|=(allowReject<<0)

                add=self.wrapperAddList[wrap] + CRUADD['add_flowctrl_offset']+CRUADD['add_flowctrl_ctrlreg']
                #print ('Flow control {} {}'.format(hex(add), hex(val)))
                self.rocWr(add, val)
       
        def setTrigWindowSize(self,wrap=0,size=4000):
                """ Configures the trigger window size in GBT words """

                if size>4095:
                        raise ValueError("Trig size should be less or equal to 4095")
                add=self.wrapperAddList[wrap] + CRUADD['add_dwrapper_gregs']+CRUADD['add_dwrapper_trigsize']
                self.rocWr(add, size)
       
        def getFlowControlStatus(self,wrap=0):
                """ Returns the number of packet rejected/total in flow control """
                pkt_rej=self.rocRd(self.wrapperAddList[wrap] + CRUADD['add_flowctrl_offset']+CRUADD['add_flowctrl_pkt_rej'], val)
                pkt_tot=self.rocRd(self.wrapperAddList[wrap] + CRUADD['add_flowctrl_offset']+CRUADD['add_flowctrl_pkt_tot'], val)
                #print ('Flow control total packets {}, rejected packets {}'.format(pkt_tot,pkt_rej))
                return pkt_tot,pkt_rej

        def datagenerator_resetpulse(self):
                """ Resets data generator """
                for w in self.wrapperAddList:
                    add = w + CRUADD['add_dwrapper_gregs']+CRUADD['add_dwrapper_datagenctrl']
                    self.rocRdMWr(add,0 ,1,1) # bit 0 at 1
                    self.rocRdMWr(add,0 ,1,0) # bit 0 at 0
       
        def datagenerator_enable(self,en=True):
                """ Enable data generation (datagenerator) """
                for w in self.wrapperAddList:
                    add = w + CRUADD['add_dwrapper_gregs']+CRUADD['add_dwrapper_datagenctrl']
                    if (en):
                        self.rocRdMWr(add,1,1,1) # bit 1 at 1
                    else:
                        self.rocRdMWr(add,1,1,0) # bit 1 at 1
        
        def datagenerator_injerr(self):
                """ Request data generator to inject a fault """
                for w in self.wrapperAddList:
                    add = w + CRUADD['add_dwrapper_gregs']+CRUADD['add_dwrapper_datagenctrl']
                    self.rocRdMWr(add,2 ,1,1) # bit 2 at 1
                    self.rocRdMWr(add,2 ,1,0) # bit 2 at 0
       
        def datagenerator_randWr(self,en=True):
                """ Set random wr to wr duration in data generator """
                for w in self.wrapperAddList:
                    add = w + CRUADD['add_dwrapper_gregs']+CRUADD['add_dwrapper_datagenctrl']
                    if (en):
                        self.rocRdMWr(add,8 ,1,1) # bit 8 at 1
                    else:
                        self.rocRdMWr(add,8 ,1,0) # bit 8 at 0
       
        def datagenerator_fixedWrPeriod(self,val=0xF):
                """ Set wr to wr duration in data generator
                valid values are 0 to 15
                """
                if (val>15 or val<0) :
                    raise ValueError ('BAD write period value {} for datagenerator, must be >=0 and < 0xF'.format(val))

                for w in self.wrapperAddList:
                    add = w + CRUADD['add_dwrapper_gregs']+CRUADD['add_dwrapper_datagenctrl']
                    self.rocRdMWr(add,4 ,4,val)
       
        def use_datagenerator_source(self,en=True):
                """ Selects datagenerator as bigfifo input source """
                for w in self.wrapperAddList:
                    add = w + CRUADD['add_dwrapper_gregs']+CRUADD['add_dwrapper_datagenctrl']
                    if (en):
                        self.rocRdMWr(add,31 ,1,1) # bit 31 at 1
                    else:
                        self.rocRdMWr(add,31 ,1,0) # bit 31 at 0
       
       
        def getFlowControlStatus(self,wrap=0):
                """ Returns the number of packet rejected/total in flow control """
                pkt_rej=self.rocRd(self.wrapperAddList[wrap] + CRUADD['add_flowctrl_offset']+CRUADD['add_flowctrl_pkt_rej'], val)
                pkt_tot=self.rocRd(self.wrapperAddList[wrap] + CRUADD['add_flowctrl_offset']+CRUADD['add_flowctrl_pkt_tot'], val)
                #print ('Flow control total packets {}, rejected packets {}'.format(pkt_tot,pkt_rej))
                return pkt_tot,pkt_rej
