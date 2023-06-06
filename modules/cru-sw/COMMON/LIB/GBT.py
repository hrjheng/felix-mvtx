from __future__ import print_function
import argparse
from ROCEXT import *
from cru_table import *


class Gbt(RocExt):
  def __init__(self, pcie_opened_roc, ch_range="all", verbose=False):
        RocExt.__init__(self,verbose)
        RocExt._roc=pcie_opened_roc

        self.numOfWrappers = self.getWrapperCount()
        self.linkIds = []
        self.links = self.getFilteredLinkList(ch_range)
        self.verbose = verbose


  def getWrapperCount(self):
    """ Self.Gets number of GBT wrappers """
    wrapperCount = 0

    for i in range(0, 2) :
      # If the clock counter (reg11) is running we accept it as a valid gbt wrapper
      reg11a = self.rocRd(self.getGlobalRegAddress(i) + CRUADD['add_gbt_wrapper_clk_cnt'])
      reg11b = self.rocRd(self.getGlobalRegAddress(i) + CRUADD['add_gbt_wrapper_clk_cnt'])

      if(reg11a != reg11b) : wrapperCount += 1

    return wrapperCount



  def getBaseAddress(self, wrapper) :
    return [CRUADD['add_gbt_wrapper0'],CRUADD['add_gbt_wrapper1'] ][wrapper]



  def getGlobalRegAddress(self, wrapper):
    """ Return global register address of the specified GBT wrapper """
    return self.getBaseAddress(wrapper) + CRUADD['add_gbt_wrapper_gregs']



  def getAtxPllRegAddress(self, wrapper, reg) :
    """ Return ATX PLL register address of the specified GBT wrapper """
    return self.getBaseAddress(wrapper) + CRUADD['add_gbt_wrapper_atx_pll'] + 4 * reg



  def getBankPllRegAddress(self, wrapper, bank):
    """ Return fPLL base address of the specified GBT bank """
    return self.getBaseAddress(wrapper) + \
      CRUADD['add_gbt_wrapper_bank_offset'] * (bank+1) + \
      CRUADD['add_gbt_bank_fpll']



  def getRxCtrlAddress(self, wrapper, bank, link):
    """ Return RX control register address of the specified GBT link"""

    return self.getBaseAddress(wrapper) + \
      CRUADD['add_gbt_wrapper_bank_offset'] * (bank+1) + \
      CRUADD['add_gbt_bank_link_offset'] * (link+1) + \
      CRUADD['add_gbt_link_regs_offset'] + \
      CRUADD['add_gbt_link_rx_ctrl_offset']



  def getTxCtrlAddress(self, wrapper, bank, link):
    """ Return TX control register address of the specified GBT link"""

    return self.getBaseAddress(wrapper) + \
      CRUADD['add_gbt_wrapper_bank_offset'] * (bank+1) + \
      CRUADD['add_gbt_bank_link_offset'] * (link+1) + \
      CRUADD['add_gbt_link_regs_offset'] + \
      CRUADD['add_gbt_link_tx_ctrl_offset']



  def getDataErrorCnt(self, wrapper, bank, link):
    """ Return Data-Not-Locked error counter of the specified GBT link"""

    return self.rocRd(self.getBaseAddress(wrapper) + \
                      CRUADD['add_gbt_wrapper_bank_offset'] * (bank+1) + \
                      CRUADD['add_gbt_bank_link_offset'] * (link+1) + \
                      CRUADD['add_gbt_link_regs_offset'] + \
                      CRUADD['add_gbt_link_data_errcnt_offset'])



  def getStatusAddress(self, wrapper, bank, link):
    """ Return status register  of the specified GBT link"""

    return self.getBaseAddress(wrapper) + \
      CRUADD['add_gbt_wrapper_bank_offset'] * (bank+1) + \
      CRUADD['add_gbt_bank_link_offset'] * (link+1) + \
      CRUADD['add_gbt_link_regs_offset'] + \
      CRUADD['add_gbt_link_status']



  def getRxClkCnt(self, wrapper, bank, link):
    """ Return RX clock frequency of the specified GBT link"""

    return self.rocRd(self.getBaseAddress(wrapper) + \
                      CRUADD['add_gbt_wrapper_bank_offset'] * (bank+1) + \
                      CRUADD['add_gbt_bank_link_offset'] * (link+1) + \
                      CRUADD['add_gbt_link_regs_offset'] + \
                      CRUADD['add_gbt_link_rxclk_cnt'])



  def getTxClkCnt(self, wrapper, bank, link):
    """ Return TX clock frequency of the specified GBT link"""

    return self.rocRd(self.getBaseAddress(wrapper) + \
                      CRUADD['add_gbt_wrapper_bank_offset'] * (bank+1) + \
                      CRUADD['add_gbt_bank_link_offset'] * (link+1) + \
                      CRUADD['add_gbt_link_regs_offset'] + \
                      CRUADD['add_gbt_link_txclk_cnt'])



  def getRxErrorCnt(self, wrapper, bank, link):
    """ Return RX error counter register  of the specified GBT link"""

    return self.rocRd(self.getBaseAddress(wrapper) + \
                      CRUADD['add_gbt_wrapper_bank_offset'] * (bank+1) + \
                      CRUADD['add_gbt_bank_link_offset'] * (link+1) + \
                      CRUADD['add_gbt_link_regs_offset'] + \
                      CRUADD['add_gbt_link_rx_err_cnt'])



  def getSourceSelectAddress(self, wrapper, bank, link):
    """ Return source select register  of the specified GBT link"""

    return self.getBaseAddress(wrapper) + \
      CRUADD['add_gbt_wrapper_bank_offset'] * (bank+1) + \
      CRUADD['add_gbt_bank_link_offset'] * (link+1) + \
      CRUADD['add_gbt_link_regs_offset'] + \
      CRUADD['add_gbt_link_source_sel']


  def getXcvrRegAddress(self, wrapper, bank, link, reg) :
    """ At beginning used blindly (assuming links in roder), and later on link rempapping)"""
    return self.getBaseAddress(wrapper) + CRUADD['add_gbt_wrapper_bank_offset'] * (bank+1) + CRUADD['add_gbt_bank_link_offset']  *(link+1)+ CRUADD['add_gbt_link_xcvr_offset'] + 4 * reg


  #------------------------------------------------------------------------------

  def getWrapperLinkList(self, wrapper) :
    links = []
    wrapperConfig = self.rocRd(self.getGlobalRegAddress(wrapper) + CRUADD['add_gbt_wrapper_conf0'])

    for bank in range(6) : 
      lpb = self.mid(wrapperConfig, 4 + 4 * bank, 4) # recover each char to determine the number of links per bank
      if (lpb == 0):
        break
      for link in range(lpb) : # for each gbt_link in bank (not in order!)
        baseAddress = self.getXcvrRegAddress(wrapper, bank, link, 0)
        links.append([wrapper, bank, link, baseAddress])
    
    newLinks=links[:]
    for l in range(len(links)): # reorder link list to match physicak implementation (check firmware to have a clarification)
      origWrapper,origBank,origLink,origBA=links[l]
      newPos=(l-origBank*6)*2+12*int(origBank/2)+ (origBank % 2)
      newLinks[newPos]=links[l]
      #print ('orig Link {} in {}, new pos={}'.format(l,links[l],newPos))
    
    #for l in range(len(links)):
      #print ('link #{} in new link={}'.format(l,newLinks[l]))

    return newLinks

  #------------------------------------------------------------------------------

  def getLinkList(self) :
    """ Constructs the link list (wrapper,bank, link)"""
    links = []
    for wrapper in range(self.numOfWrappers) :
      newlinks = self.getWrapperLinkList(wrapper)
      links += newlinks
    return links

  def getNumOfLinksPerBank(self):
     """ Return the number of links per bank in each wrapper """
     data =[]
     for wrapper in range(self.numOfWrappers):
       addr = self.getGlobalRegAddress(wrapper) + CRUADD['add_gbt_wrapper_conf0']
       data.append(self.mid(self.rocRd(addr),4,24))
       print ("g_NUM_OF_LINKS: x\"%06x\"" % (data[wrapper]))
     return data

  def isGBTWrapper(self,doPrint=False):
     """ Checks the wrapper type (TRD or GBT)"""
     detType=[]
     for wrapper in range(self.numOfWrappers):
        addr = self.getGlobalRegAddress(wrapper) + CRUADD['add_gbt_wrapper_conf1']
        data = self.rocRd(addr)
        detType.append(hex(self.mid(data, 12, 12)))
     if doPrint:
        print ("Link code {} found(s) (0xB69=GBT, 0x978=TRD)".format(detType))
     if '0xb69' in detType:
        return True
     else:
        return False

  def getGBTWrapperType(self,doPrint=False):
     """ Checks the GBT wrapper type (wide or dynamic)"""
     if not self.isGBTWrapper():
        raise ValueError("Not a GBT wrapper")
     gbtType=[]
     for wrapper in range(self.numOfWrappers):
        addr = self.getGlobalRegAddress(wrapper) + CRUADD['add_gbt_wrapper_conf1']
        data = self.rocRd(addr)
        gbtType.append(hex(self.mid(data, 8, 4))) #
     if doPrint:
        print ("GBT wrapper type {} found(s) (0x5=wide, 0xA=dynamic)".format(gbtType))
     if '0x5' in gbtType:
        return 'wide'
     else:
        return 'dynamic'
  def getTotalNumOfLinks(self):
     """ Return the total number of links """
     numOfLinks = 0
     for wrapper in range(self.numOfWrappers):
        addr = self.getGlobalRegAddress(wrapper) + CRUADD['add_gbt_wrapper_conf1']
        data = self.rocRd(addr)
        numOfLinks += self.mid(data, 24, 8)
        print ("%d link(s) found in total" % numOfLinks)
     return numOfLinks

  def printLinkStatus(self):
     """ Prints the GBT link status """
     loopbacks = self.getLoopback()

     for i, entry in enumerate(self.links):
        index, wrapper, bank, link, baseAddress = entry
        if self.linkLocked[i]:
            print (" Link %s : %s" % (("%d" % index).rjust(3), "UP  "), end='')
        else:
            print (" Link %s : %s" % (("%d" % index).rjust(3), "DOWN"), end='')

        if loopbacks[i] == "YES":
          print("%s" % "Currently in internal loopback".rjust(50))
        else:
          print("")

        linkOk = sum(x==1 for x in self.linkLocked)
     print (" Status: %d/%d link is up\n" % (linkOk, len(self.links)))

  def checkLinkLockStatus(self):
     """ Checks and prints the GBT link lock status """
     # the link is locked is the rx_frequency = tx_frequency and the GBT ready bit is on
     self.linkLocked = [0]*len(self.links)
     for i, entry in enumerate(self.links):
        index, wrapper, bank, link, baseAddress = entry
        addr = self.getStatusAddress(wrapper, bank, link)
        data = self.rocRd(addr)
        txfreq = self.getTxClkCnt(wrapper, bank, link)
        rxfreq = self.getRxClkCnt(wrapper, bank, link)
        # the frequency is compared within a range (-2,2) MHz, insensitive to the measure fluctuation
        if txfreq - rxfreq <= 2 and rxfreq - txfreq <= 2:
          self.linkLocked[i] = self.mid( data,13, 1 ) # 1 = locked, 0 = down
        else:
          self.linkLocked[i] = 0

        if (self.verbose):
           PHY_DOWN = self.mid( data,14, 1 )
           DATA_LAYER_DOWN = self.mid( data,15, 1 )

           print ("=================================================================")
           print ("\t\tLink #{}: Wrapper {} - Bank {} - Link {}".format(index, wrapper, bank, link))
           print ("-----------------------------------------------------------------")
           print ("           Status bit\t        |           Sticky bit\t\t")
           print (" Bank PLL locked : %s\t        |    Phy up        : %s \t" % (["NO", "YES"][self.mid(data, 8, 1)],["NO","YES"][ ~PHY_DOWN]))
           print (" Locked to data  : %s\t        |    Data layer up : %s \t" % (["NO", "YES"][self.linkLocked[i]],  ["NO","YES"][ ~DATA_LAYER_DOWN]))
           print (" TX clock frequency: %.2f MHz" % (txfreq / 1e6))
           print (" RX clock frequency: %.2f MHz" % (rxfreq / 1e6))
           print ("")

     self.getNumOfLinksPerBank()
     
     if (not self.verbose): # Just report total number of links
        self.getTotalNumOfLinks()

     self.printLinkStatus()

     return self.linkLocked
  #------------------------------------------------------------------------------

  def getFilteredLinkList(self, ch_range):
    """ Self.Get user specified list of links """

    allLinks = self.getLinkList()
    if (ch_range == "all"):
      #self.linkIds = range(len(allLinks))
      #return allLinks
      return [[i,] + allLinks[i] for i in range(len(allLinks))]

    if (ch_range.find("-") > -1):
      r0 = int(ch_range.split("-")[0])
      r1 = int(ch_range.split("-")[1])
      if r0 > r1 or r0 < 0 or r1 > len(allLinks)-1:
        raise ValueError("Link index out of range, max link index is %d" % (len(allLinks)-1))
      #self.linkIds = range(r0, r1+1)
      #return allLinks[r0:r1+1]
      return [[i,] + allLinks[i] for i in range(r0, r1+1)]

    links = []
    for i in ch_range.split(","):
      if int(i) < 0 or int(i) > len(allLinks)-1:
        raise ValueError("Link index out of range, max link index is %d" % (len(allLinks)-1))
      #self.linkIds.append(int(i))
      #links.append(allLinks[int(i)])
      links.append([int(i),] + allLinks[int(i)])
    return links

  def getLinkIndices(self):
    """ Get logical indices of the links """

    return [link[0] for link in self.links]


    #------------------------------------------------------------------------------

  def atxref(self, refclk) :
      if (refclk > 4):
          raise ValueError("Invalid refclk input: %d (should be between 0 and 4)" % (refclk))

      print ("Setting ATX PLL refclk to refclk%d".format(refclk))
      lookup_reg_addr = 0x113 + refclk
      reg112 = self.rocRd(self.getAtxPllRegAddress(0, 0x112))
      data = self.rocRd(self.getAtxPllRegAddress(0, lookup_reg_addr))
      print ("(0x112) = 0x%02x updated with value 0x{:02x}".format(reg112, data))
      self.rocWr(self.getAtxPllRegAddress(0, 0x112), data)


  def fpllref(self, refclk, baseAddress = 0) :
      if (refclk > 4):
          raise ValueError("Invalid refclk input: {} (should be between 0 and 4)".format(refclk))

      if (baseAddress != 0) : self.fpllref0(baseAddress, refclk)
      else:
        prevWrapper = -1
        prevBank = -1
        for entry in self.links:
          index, wrapper, bank, link, baseAddress = entry
          if (prevWrapper != wrapper) or (prevBank != bank) :
            self.fpllref0(self.getBankPllRegAddress(wrapper, bank), refclk)
            prevWrapper = wrapper
            prevBank = bank



  def cdrref(self, refclk) :
      if (refclk > 4):
          raise ValueError("Invalid refclk input: {} (should be between 0 and 4)".format(refclk))

      self.vprint("Setting CDRs refclk to refclk{}".format(refclk))
      for entry in self.links:
          index, wrapper, bank, link, baseAddress = entry
          lookup_reg_addr = 0x16A + refclk
          reg141 = self.rocRd(self.getXcvrRegAddress(wrapper, bank, link, 0x141))
          data = self.rocRd(self.getXcvrRegAddress(wrapper, bank, link, lookup_reg_addr))
          self.vprint("  ({}:{}:{}:{}) : (0x141) = 0x{:02x} updated with value 0x{:02x}".format(index, wrapper, bank, link, reg141, data))
          self.rocWr(self.getXcvrRegAddress(wrapper, bank, link, 0x141), data)
      self.vprint(" ")


  def atxcal(self, baseAddress = 0) :
    if (baseAddress != 0) : self.atxcal0(baseAddress)
    else :
      for wrapper in range(self.numOfWrappers) :
        self.atxcal0(self.getAtxPllRegAddress(wrapper, 0x000))



  def fpllcal(self, baseAddress = 0, configCompensation = True):
    if (baseAddress != 0) : self.fpllcal0(baseAddress, configCompensation)
    else :
      prevWrapper = -1
      prevBank = -1
      for entry in self.links:
        index, wrapper, bank, link, baseAddress = entry
        self.vprint("({}:{}:{}:{})".format(index, wrapper, bank, link))
        if (prevWrapper != wrapper) or (prevBank != bank) :
          self.fpllcal0(self.getBankPllRegAddress(wrapper, bank), configCompensation)
          prevWrapper = wrapper
          prevBank = bank



  def rxcal(self):
    """ Calibrate XCVR RX """

    self.vprint("Starting XCVR RX calibration")

    for entry in self.links:
      index, wrapper, bank, link, baseAddress = entry

      self.rxcal0(baseAddress)

    self.vprint("  Calibration completed")
    self.vprint(" ")



  def txcal(self):
    """ Calibrate XCVR TX for all links """

    self.vprint("Starting XCVR TX calibration")

    for entry in self.links:
      index, wrapper, bank, link, baseAddress = entry

      self.txcal0(baseAddress)

    self.vprint("  Calibration completed")
    self.vprint(" ")

  #------------------------------------------------------------------------------


  def cntrst(self) :
    """ Reset error counter in specified links """

    for entry in self.links:
      index, wrapper, bank, link, baseAddress = entry
      self.rocRdMWr(self.getSourceSelectAddress(wrapper, bank, link), 6, 1, 0x1) # set error counter reset
      self.rocRdMWr(self.getSourceSelectAddress(wrapper, bank, link), 6, 1, 0x0) # release error counter reset
      self.vprint("Error counter reset for link {} (in wrapper: {}, bank: {}, link: {}".format(index, wrapper, bank, link))


  #------------------------------------------------------------------------------


  def cntinit(self) :
    """ Reset error counter for all links being present in the card """
    self.cntrst()


  #------------------------------------------------------------------------------

  def getFecCnt(self, wrapper,bank,link):
    """ Return number of corrected error for a specific GBT link (16 bit max)"""

    return self.rocRd(self.getBaseAddress(wrapper) + \
      CRUADD['add_gbt_wrapper_bank_offset'] * (bank+1) + \
      CRUADD['add_gbt_bank_link_offset'] * (link+1) + \
      CRUADD['add_gbt_link_regs_offset'] + \
      CRUADD['add_gbt_link_fec_monitoring'])


  #------------------------------------------------------------------------------
  def getRefFrequencies(self):
    """ Get GBT wrappers reference clocks frequencies """
    reffreq=[]
    for i in range(self.getWrapperCount()):
       reffreq.append(self.rocRd(self.getGlobalRegAddress(i) + CRUADD['add_gbt_wrapper_refclk0_freq']))
       reffreq.append(self.rocRd(self.getGlobalRegAddress(i) + CRUADD['add_gbt_wrapper_refclk1_freq']))
       reffreq.append(self.rocRd(self.getGlobalRegAddress(i) + CRUADD['add_gbt_wrapper_refclk2_freq']))
       reffreq.append(self.rocRd(self.getGlobalRegAddress(i) + CRUADD['add_gbt_wrapper_refclk3_freq']))
       message=("Wrapper {}: | ".format(i))
       for j in range(4):
          message=message+("ref freq{} {:.2f} MHz  | ".format(j,(reffreq[j] / 1e6)).rjust(27))
       print (message)


  def stat(self, infiniteLoop=False, stat="all"):
    """ Print the number of test pattern reception and/or FEC errors for each link """
    t0 = int(time.time())

    if infiniteLoop:
        limit = -1
    else:
        limit = 6

    j = 0
    try:
        while j != limit:
          column = 0
          txt = ""
          for entry in self.links:
            index, wrapper, bank, link, baseAddress = entry
            data = self.rocRd(self.getStatusAddress(wrapper, bank, link))
            pll_lock = self.mid(data, 8, 1)
            rx_is_lockedtodata = self.mid(data, 10, 1)
            RXDATA_ERROR_CNT_O = self.getRxErrorCnt(wrapper, bank, link)
            s_DataLayerUp = self.mid( self.rocRd(self.getStatusAddress(wrapper, bank, link)),11, 1 ) 
            s_GbtPhyUp = self.mid( self.rocRd(self.getStatusAddress(wrapper, bank, link)),13, 1 )
           
            if stat=="fec" or stat=="all":
                FecVal = self.getFecCnt(wrapper, bank, link)

            if (j == 0) : #title
                if (column == 0) : txt += "% 16s" % ("seconds")
                if stat=="fec":
                    txt += "% 16s" % ("fec:" + str(index))
                elif stat=="all":
                    txt += ("% 25s" % ("RX EC/FEC #" + str(index) + "   ")).rjust(25)
                elif stat=="cnt":
                    txt += ("% 16s" % ("error:" + str(index) )).rjust(16)
            else :
              tmptxt = ""
              if (column == 0) : tmptxt += "% 16d" % (int(time.time()) - t0)
              if stat!="fec":
                  if (pll_lock == 0) : tmptxt += "% 16s" % ("pll_lock")
                  elif (s_DataLayerUp==0) : tmptxt += "% 16s" % ("s_datadown")
                  elif (s_GbtPhyUp==0) : tmptxt += "% 16s" % ("s_GbtPhyDown")
                  elif (rx_is_lockedtodata == 0) : tmptxt += "% 16s" % ("lockedtodata")
                  else : tmptxt += "% 16d" % (RXDATA_ERROR_CNT_O)
              
              if stat=="all":
                txt += (tmptxt + "/" + ("%5d" % (FecVal)).rjust(5)).rjust(25)
              elif stat=="fec":
                txt += (tmptxt +"%16d" % (FecVal)) 
              elif stat=="cnt":
                txt += tmptxt
            column += 1
          print(txt)
          sleep(1)
          j = j + 1

    except KeyboardInterrupt:
        return


  #------------------------------------------------------------------------------


  def internalDataGenerator(self, value) :
    """ Select the GBT tx source inside the link. Can be upstream (0) or internal pattern generator (1). """
    for entry in self.links:
      index, wrapper, bank, link, baseAddress = entry
      self.rocRdMWr(self.getSourceSelectAddress(wrapper, bank, link), 1, 1, value)
      self.rocRdMWr(self.getSourceSelectAddress(wrapper, bank, link), 2, 1, value)


  def resetAllLinks(self) :
    """ Reset all GBT links (pulsing) """
    for entry in self.links:
      index, wrapper, bank, link, baseAddress = entry
      self.rocRdMWr(self.getSourceSelectAddress(wrapper, bank, link), 0, 1, 1) # activate reset
      self.rocRdMWr(self.getSourceSelectAddress(wrapper, bank, link), 0, 1, 0) # release


  #------------------------------------------------------------------------------


  def txcountertype(self, mode) :
    """ Select the test counter type 30bit/8bit. the 8bit type is for MID """
    for wrapper in range(self.numOfWrappers) :
      if (mode == "30bit"):
        self.rocRdMWr(self.getBaseAddress(wrapper)+CRUADD['add_gbt_wrapper_gregs']+CRUADD['add_gbt_wrapper_test_control'], 7, 1, 0x0)
      elif (mode == "8bit") :
        self.rocRdMWr(self.getBaseAddress(wrapper)+CRUADD['add_gbt_wrapper_gregs']+CRUADD['add_gbt_wrapper_test_control'], 7, 1, 0x1)
      else :
        print ("invalid tx counter type : {} (only 30bit and 8 bit allowed)".format(mode))
      self.vprint(("TX counter type {} set ".format(mode)))


  #------------------------------------------------------------------------------

  def rxpatternmask(self, himask,medmask,lomask) :
    """ Define the checking mask on the rx side when in test pattern mode. This works only when the counter is in 8 bit mode. """
    for entry in self.links:
      index, wrapper, bank, link, baseAddress = entry
      current_add=self.getBaseAddress(wrapper) + CRUADD['add_gbt_wrapper_bank_offset'] * (bank+1) + \
                CRUADD['add_gbt_bank_link_offset'] * (link+1) +  CRUADD['add_gbt_link_regs_offset'] + CRUADD['add_gbt_link_mask_hi']
      self.rocWr(current_add,himask)

      current_add=self.getBaseAddress(wrapper) + CRUADD['add_gbt_wrapper_bank_offset'] * (bank+1) + \
                CRUADD['add_gbt_bank_link_offset'] * (link+1) +  CRUADD['add_gbt_link_regs_offset'] + CRUADD['add_gbt_link_mask_med']
      self.rocWr(current_add,medmask)

      current_add=self.getBaseAddress(wrapper) + CRUADD['add_gbt_wrapper_bank_offset'] * (bank+1) + \
                CRUADD['add_gbt_bank_link_offset'] * (link+1) +  CRUADD['add_gbt_link_regs_offset'] + CRUADD['add_gbt_link_mask_lo']
      self.rocWr(current_add,lomask)

  #------------------------------------------------------------------------------


  def patternmode(self, mode) :
    """ GBT test pattern mode, either static or counter """
    for entry in self.links:
      index, wrapper, bank, link, baseAddress = entry
      if (mode == "counter") :
        self.rocRdMWr(self.getSourceSelectAddress(wrapper, bank, link), 5, 1, 0x0)
        self.vprint("Pattern {} set for link {} (in wrapper: {}, bank: {}, link: {}".format(mode,index, wrapper, bank, link))
      elif (mode == "static") :
        self.rocRdMWr(self.getSourceSelectAddress(wrapper, bank, link), 5, 1, 0x1)
        self.vprint("Pattern {} set for link {} (in wrapper: {}, bank: {}, link: {}".format(mode,index, wrapper, bank, link))
      else :
        print ("invalid pattern mode: {} (only counter and static allowed)".format(mode))


  #------------------------------------------------------------------------------


  def loopback(self, value) :
    """ Sets the same internal loopback mode for all the links """

    allLinks = self.getFilteredLinkList("all")
    for entry in allLinks:
      index, wrapper, bank, link, baseAddress = entry
      self.rocRdMWr(self.getSourceSelectAddress(wrapper, bank, link), 4, 1, value)

  def getLoopback(self):
    """ Reports whether internal loopback is used or not """
    loopbacks = []
    for entry in self.links:
      index, wrapper, bank, link, baseAddress = entry
      loopbacks.append(["NO", "YES"][self.rocRd(self.getSourceSelectAddress(wrapper, bank, link)) >> 4 & 0x1])

    return loopbacks


  def useDDGshortcut(self, value=True) :
    """ Enables the DDG shortcut (the data to TX are used as GBT rx for the rest of the design """
    for entry in self.links:
      index, wrapper, bank, link, baseAddress = entry
      self.rocRdMWr(self.getRxCtrlAddress(wrapper, bank, link), 16, 1, (0,1)[value==True])

    if value:
      self.vprint("Shortcut enabled")
    else:
      self.vprint("Shortcut disabled")


  #------------------------------------------------------------------------------


  def txmode(self, mode) :
    """ Select the GBT transmit mode (when in dynamic select mode). Can be gbt or wb (wide bus). """
    if not self.isGBTWrapper():
        raise ValueError("Not a GBT wrapper")

    for entry in self.links:
      index, wrapper, bank, link, baseAddress = entry
      if (mode == "gbt") :
        if self.getGBTWrapperType()!='dynamic':
            raise ValueError("GBT wrapper is wide only")
        self.rocRdMWr(self.getTxCtrlAddress(wrapper, bank, link),8 ,1,0)

      elif (mode == "wb") :
        self.rocRdMWr(self.getTxCtrlAddress(wrapper, bank, link),8 ,1,1)

      else :
        raise ValueError("invalid tx mode: {} (only gbt and wb are allowed)".format(mode))

  def rxmode(self, mode) :
    """ Select the GBT receive mode (when in dynamic select mode). Can be gbt or wb (wide bus). """
    if not self.isGBTWrapper():
        raise ValueError("Not a GBT wrapper")
    for entry in self.links :
      index, wrapper, bank, link, baseAddress = entry
      if (mode == "gbt") :
        if self.getGBTWrapperType()!='dynamic':
            raise ValueError("GBT wrapper is wide only")
        self.rocRdMWr(self.getRxCtrlAddress(wrapper, bank, link),8 ,1,0)
      elif (mode == "wb") :
        self.rocRdMWr(self.getRxCtrlAddress(wrapper, bank, link),8 ,1,1)
      else :
        raise ValueError("invalid rx mode: {} (only gbt and wb allowed)".format(mode))


  def getGbtMode(self) :
    """ Gets configured GBT mode for each link """

    modes = []
    if not self.isGBTWrapper():
      print("TRD wrappers are implemented instead of GBT wrappers")
      for entry in self.links :
        index, wrapper, bank, link, baseAddress = entry
        modes.append((str(index), "--", "--"))

        return modes

    if self.getGBTWrapperType()!='dynamic':
      for entry in self.links :
        index, wrapper, bank, link, baseAddress = entry
        self.vprint("Link {} RX mode: {}, TX mode: {}".format(str(index), "WB", "WB"))
        modes.append((str(index), "WB", "WB"))
    else:
      for entry in self.links :
        index, wrapper, bank, link, baseAddress = entry

        rxctrl = self.rocRd(self.getRxCtrlAddress(wrapper, bank, link))
        if  ((rxctrl >> 8) & 0x1) ==1:
          rxmode = "WB"
        else:
          rxmode = "GBT"

        txctrl = self.rocRd(self.getTxCtrlAddress(wrapper, bank, link))
        if ((txctrl >> 8) & 0x1) == 1:
          txmode = "WB"
        else:
          txmode = "GBT"


        self.vprint("Link {}:  RX mode {}, TX mode {}".format(str(index), rxmode, txmode))
        modes.append((str(index), txmode, rxmode))

    return modes

  def init(self) :
    # enable GBT-FPGA TX VALID to be generated in GBT-FPGA TX clock domain

    for entry in self.links:
      index, wrapper, bank, link, baseAddress = entry
      self.rocWr(self.getSourceSelectAddress(wrapper, bank, link), 0x00000042) # clear error counters
      self.rocWr(self.getSourceSelectAddress(wrapper, bank, link), 0x00000006)
      self.rocWr(self.getTxCtrlAddress(wrapper, bank, link), 0x0)
      self.rocWr(self.getRxCtrlAddress(wrapper, bank, link), 0x0)

    #for entry in self.getFilteredLinkList("all"):
    for entry in self.links:
      index, wrapper, bank, link, baseAddress = entry
      self.rocRdMWr(self.getXcvrRegAddress(wrapper, bank, link, 0x007), 2, 1, 0)
      self.rocRdMWr(self.getXcvrRegAddress(wrapper, bank, link, 0x00A), 4, 1, 0)



  def lbtest(self, lb) :
    print ("GBT -> GBT mode:")
    self.init()
    self.internalDataGenerator(1)
    self.patternmode("counter")
    self.loopback(lb)
    self.txmode("gbt")
    self.rxmode("gbt")
    self.cntrst()
    self.stat("cnt")
    print ("GBT -> WB mode:")
    self.rxmode("wb")
    self.cntrst()
    self.stat("cnt")
    print ("WB -> WB mode:")
    self.txmode("wb")
    self.cntrst()
    self.stat("stat")

  def RstError(self) :
    """ Reset the GBT synchro error indicator """
    for entry in self.links:
      index, wrapper, bank, link, baseAddress = entry
      current_add = self.getBaseAddress(wrapper) \
                  + CRUADD['add_gbt_wrapper_bank_offset'] * (bank+1) \
                  + CRUADD['add_gbt_bank_link_offset'] * (link+1) \
                  + CRUADD['add_gbt_link_regs_offset'] \
                  + CRUADD['add_gbt_link_clr_errcnt']
#      print("%x" % current_add)
      self.rocWr(current_add,0)


  def downlinkcal(self, gbt_mode, dataGenerator = False):
    """ Set up GBT downlink """

    self.vprint("Setting up downlink datapath")

    if dataGenerator:
      self.internalDataGenerator(1)
    else:
      self.internalDataGenerator(0) # forward data, change to gbt.internalDataGenerator(1) to use the gbt data generator instead

    self.txmode(gbt_mode)
    self.rxmode(gbt_mode)



if __name__ == '__main__' :

  commands = ["init"       ,"cntrst",
              "stat"    ,"loopback","internalDataGenerator",
              "patternmode","txmode"  ,"rxmode","atxref",
              "fpllref"    ,"cdrref"  ,"atxcal",
              "fpllcal"    ,"txcal"   ,"rxcal",
              "lbtest"     ]

  parser = argparse.ArgumentParser()
  parser.add_argument("-i", "--id", required=True, help="card ID")
  parser.add_argument("-c", "--command",  choices=commands, metavar="COM",required=True, help=", ".join(commands))
  parser.add_argument("-l", "--links", default="all", help="specifiy link IDs, eg. all, 1-4 or 1,3,4,16")
  parser.add_argument("-g", "--gbt-mode", choices=["gbt", "wb", "raw"], help="GBT mode: gbt, wb or raw")
  parser.add_argument("-x", "--gbt-pattern", choices=["gbt", "gbtx"], help="select GBT payload pattern tailored to receiver's GBT implementation: gbt or gbtx")
  parser.add_argument("-p", "--pattern", choices=["static", "counter"], help="pattern generator mode")
  parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true", default=False)
  parser.add_argument("-d", "--data", help="value to be written to register")
  parser.add_argument("-r", "--refclk", type=int, help="reference clock value")

  args = parser.parse_args()
  if args.command == None:
    parser.error("No command is specified")
  #if args.command != "atxcal" and args.command != "fpllcal" and not args.links:
  #  parser.error('The --link flag must be set with the specified command')
  if (args.command == "txmode" or args.command == "rxmode") and args.gbt_mode == None:
    parser.error("The --gbt-mode flag must be set with the specified command")
  if args.command == "patternmode" and args.pattern == None:
    parser.error("The --pattern flag must be set with the specified command")
  if args.command == ("atxref" or args.command == "fpllref" or args.command == "cdrref"):
    if args.refclk == None:
      parser.error("The --refclk flag must be set with the specified command")
    elif args.refclk < 0 or args.refclk > 4:
      parser.error("--refclk argument value must be 1-4")
  if args.command == "lbtest" and args.data == None:
    parser.error("Missing -d/--data parameter to set rx_seriallpben [0|1]")


  #gbt = Gbt(args.id, args.links, args.verbose)


  if   (args.command == "init")       : gbt.init()
  elif (args.command == "cntrst")     : gbt.cntrst()
  elif (args.command == "stat")    :
    if int(args.data) == 1:
      gbt.stat(True)
    else:
      gbt.stat()
  elif (args.command == "loopback")   : gbt.loopback(int(args.data))
  elif (args.command == "internalDataGenerator")      : gbt.internalDataGenerator(int(args.data))
  elif (args.command == "patternmode"): gbt.patternmode(args.pattern)
  elif (args.command == "txmode")     : gbt.txmode(args.gbt_mode)
  elif (args.command == "rxmode")     : gbt.rxmode(args.gbt_mode)
  elif (args.command == "atxref")     : gbt.atxref(args.refclk)
  elif (args.command == "fpllref") : gbt.fpllref(args.refclk)
  elif (args.command == "cdrref")     : gbt.cdrref(args.refclk)
  elif (args.command == "atxcal")     : gbt.atxcal() #todo baseaddress param
  elif (args.command == "fpllcal")    : gbt.fpllcal() #todo baseaddress param
  elif (args.command == "txcal")      : gbt.txcal()
  elif (args.command == "rxcal")      : gbt.rxcal()
  elif (args.command == "lbtest")     : gbt.lbtest(int(args.data))

  
