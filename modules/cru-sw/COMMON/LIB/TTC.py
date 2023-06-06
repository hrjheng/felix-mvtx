import os
import inspect
from ROCEXT import *
from cru_table import *
from SI534X import Si534x

class Ttc(RocExt):
    def __init__(self, pcie_opened_roc, pcie_id, verbose=False):
        RocExt.__init__(self,verbose)
        self.pcie_id = pcie_id
        RocExt._roc = pcie_opened_roc
        self.max_bcid=3564-1


    def configPlls(self, clockingScheme):
        """ Configure external on-board PLLs according to the selected clocking scheme """

        chip_add = 0x68 # chip address is fixed

        # Avalon address of the pll's I2C bus
        si5345_1_addr = CRUADD['add_bsp_i2c_si5345_1']
        si5345_2_addr = CRUADD['add_bsp_i2c_si5345_2']
        si5344_addr = CRUADD['add_bsp_i2c_si5344']

        fileDir = os.path.dirname(os.path.realpath(inspect.getfile(Si534x)))
        fileDir = os.path.join(fileDir, 'register_maps')

        if clockingScheme == "local":
            regmap1 = os.path.join(fileDir, 'Si5345-RevD_local_pll1_zdb-Registers.txt')
            regmap2 = os.path.join(fileDir, 'Si5345-RevD_local_pll2_zdb-Registers.txt')
        else:
            # bring recovered PON RX clk to external PLL as reference
            self.setRefGen()

            regmap1 = os.path.join(fileDir, 'Si5345-RevD_ttc_pll1_zdb-Registers.txt')          
            regmap2 = os.path.join(fileDir, 'Si5345-RevD_ttc_pll2_zdb-Registers.txt')

        regmap3 = os.path.join(fileDir, 'Si5344-RevD-TFC_40-Registers.txt')

        p1 = Si534x(self.pcie_id, 2, si5345_1_addr, chip_add, regmap1)
        p2 = Si534x(self.pcie_id, 2, si5345_2_addr, chip_add, regmap2)
        p3 = Si534x(self.pcie_id, 2, si5344_addr, chip_add, regmap3)

        p1.resetI2C()
        p2.resetI2C()
        p3.resetI2C()

        p1.configurePll()
        p2.configurePll()
        p3.configurePll()

        sleep(2)


    def selectGlobal240(self, clockingScheme):
        """ Select between local oscillator and recovered PON RX clock """

        # Selection for the global 240 MHz clock (local or ttc) happens in the external PLLs
        self.configPlls(clockingScheme)

        add_clkctrl      = CRUADD['add_ttc_clkgen_clkctrl']
        add_set_locktoref = CRUADD['add_ttc_onu_ctrl']
        add_seldata      = CRUADD['add_ttc_data_ctrl']

        # Local mode
        if clockingScheme == "local":             
            self.rocWr(add_set_locktoref, 0)      # To force recovered clock to be the local refclk set it to '1'

            # select local data generator as global trigger data
            self.rocRdMWr(add_seldata, 0, 2, 0x2)

        # ttcpon mode
        else:
            self.rocWr(add_set_locktoref, 0)

            # select TTCPON data as global trigger data
            self.rocRdMWr(add_seldata, 0, 2, 0x0)


    def configPonTx(self, onuAddr, manualScan=False):
        """ Configure manually the fPLL providing 240 MHz refclk for PON TX 
	
        This can be achieved by phase scanning and checking the PHASEGOOD bit in the
        meantime. By default, it is done in the firmware.

        For the current PLL setup every 56th step jumps into a 'phase
        not good' position, the rest are 'phase good' (56 = M-counter
        of fPLL, 1 phase step is VCO period/4, see fPLL IP). This
        means that to find the _best_ position, 56/2 steps are needed
        after a 'phase not good'. However, after every ONU reset -
        which is always performed when running the startup script, see
        calibTTC() - one can see a large number of 'phase good' (much
        more than 56) this is to be understood.  """

        if not manualScan:
            # After booting it's high by default (=automatic scan
            # enabled), update anyway, in case startup script has been
            # run with manualScan option before
            self.rocRdMWr(CRUADD['add_ttc_clkgen_pllctrlonu'], 0, 1, 0x1)
        else:
            # Disable automatic phase scan
            self.rocRdMWr(CRUADD['add_ttc_clkgen_pllctrlonu'], 0, 1, 0x0)
    
            # Perform phase scan manually
            cnt = 0
            seenlow = False
    
            # Choose a large enough number as 'timeout' for finding a wrong phase position after reset
            steps = 50000
    
            for i in range(steps):
                # Toggle phase step bit
                self.rocWr(CRUADD['add_ttc_clkgen_pllctrlonu'], 0x00300000)
                self.rocWr(CRUADD['add_ttc_clkgen_pllctrlonu'], 0x00200000)
                
                onustat = self.rocRd(CRUADD["add_onu_user_logic"]+0xC)
           
                # Check if ONU status bits are all '1' (ONU operational bit is not necessary)
                # see onuCalibrationStatus() for each bit
                if onustat == 0xff or onustat == 0xf7:
                    cnt += 1
                elif onustat == 0xf5 or 0xfd:
                    cnt = 0
                    seenlow = True
                else:
                    cnt = 0
                
                # Find the middle of the 56 step 
                if seenlow and cnt == 28:
                    break
                
                if i == steps-1:
                    raise Exception("PON TX fPLL phase scan failed")


        # Assign ONU address
        self.rocRdMWr(CRUADD["add_onu_user_logic"], 1, 8, onuAddr)

        self.onuCalibrationStatus()

    def onuCalibrationStatus(self):
        """ Checks onu calibration status by reading the onu user register """

        calStatus = self.rocRd(CRUADD["add_onu_user_logic"]+0xc)
        onuAddr = self.rocRd(CRUADD["add_onu_user_logic"]) >> 1

        # Report calibration status
        self.vprint("PON calibration status:")
        self.vprint("  ONU address:\t%d\n   ---"%onuAddr)
        self.vprint("  ONU RX40 locked:\t"+["NOT OK","OK"][calStatus & 0x1])
        self.vprint("  ONU phase good:\t"+["NOT OK","OK"][(calStatus>>1) & 0x1])
        self.vprint("  ONU RX locked:\t"+["NOT OK","OK"][(calStatus>>2) & 0x1])
        self.vprint("  ONU operational:\t"+["NOT OK","OK"][(calStatus>>3) & 0x1])
        self.vprint("  ONU MGT TX ready:\t"+["NOT OK","OK"][(calStatus>>4) & 0x1])
        self.vprint("  ONU MGT RX ready:\t"+["NOT OK","OK"][(calStatus>>5) & 0x1])
        self.vprint("  ONU MGT TX pll lock:\t"+["NOT OK","OK"][(calStatus>>6) & 0x1])
        self.vprint("  ONU MGT RX pll lock:\t"+["NOT OK","OK"][(calStatus>>7) & 0x1])
        self.vprint("")


    def calibTTC(self):
        """ Run TTCPON calibrations """

        # Reset ONU core
        self.vprint("Resetting ONU core...")
        self.rocRdMWr(CRUADD['add_onu_user_logic'], 0, 1, 0x1)
        sleep(0.5)
        self.rocRdMWr(CRUADD['add_onu_user_logic'], 0, 1, 0x0)

        # Switch to refclk #0
        sel0 = self.rocRd(CRUADD['add_pon_wrapper_pll'] + 0x044c)
        self.rocWr(CRUADD['add_pon_wrapper_pll'] + 0x0448, sel0)

        # calibrate PON RX
        self.rxcal0(CRUADD['add_pon_wrapper_tx'])
        
        # calibrate fPLL
        add_pon_fpll = CRUADD['add_ttc_clkgen_onufpll']
        self.fpllref0(add_pon_fpll, 1) # Select refclk 1
        self.fpllcal0(add_pon_fpll, False)

        # calibrate ATX PLL
        self.atxcal0(CRUADD['add_pon_wrapper_pll'])

        # calibrate PON TX
        self.txcal0(CRUADD['add_pon_wrapper_tx'])
        self.vprint(" ")

        # wait some to settle things
        sleep(2)

        # Check MGT RX ready, RX locked and RX40 locked
        calStatus = self.rocRd(CRUADD["add_onu_user_logic"]+0xc)
        if (calStatus >> 5) & (calStatus >> 2) & calStatus & 0x1 != 1:
            raise Exception("PON RX calibration failed")


    def selectDownstreamData(self, downstreamData):
        """ Selects between CTP and pattern player output to forward """

        if downstreamData == "ctp":
            self.rocRdMWr(CRUADD['add_ttc_data_ctrl'], 16, 2, 0)
        elif downstreamData == "pattern":
            self.rocRdMWr(CRUADD['add_ttc_data_ctrl'], 16, 2, 1)
        elif downstreamData == "midtrg":
            self.rocRdMWr(CRUADD['add_ttc_data_ctrl'], 16, 2, 2)
        else:
            raise ValueError("Invalid downstream data source, valid source are ctp or pattern, router")

    def getDownstreamData(self):
        """ Prints the source of TTC downstream data """

        datactrl = (self.rocRd(CRUADD['add_ttc_data_ctrl']) >> 16) & 0x3

        if datactrl == 0:
            src = "CTP"
        elif datactrl == 1:
            src = "PATTERN"
        else:
            src = "MID TRG"

        return src

    def getHBTrigFromLTUCount(self):
        """ Get count of HB trigs received from LTU (32 bit counter) """
        return self.rocRd(CRUADD['add_ttc_hbtrig_ltu'])

    def getPHYSTrigFromLTUCount(self):
        """ Get count of PHYS trigs received from LTU (32 bit counter) """
        return self.rocRd(CRUADD['add_ttc_phystrig_ltu'])

    def getSOXEOXTrigFromLTUCount(self):
        """ Get count of SOx/EOx trigs received from LTU (2x 4 bit counter) """
        val=self.rocRd(CRUADD['add_ttc_eox_sox_ltu'])
        SOXcount=(val & 0XF)
        EOXcount=((val>>4) & 0XF)
        return SOXcount, EOXcount

    def loopTrigFromLTUCount(self):
        """ Continuously prints PHYS, SOx and EOx """

        print("PHYS".rjust(10) + "SOX".rjust(10) + "EOX".rjust(10))
        try:
            ofPhys = ofSox = ofEox = 0 # Number of overflows
            rsPhys = rsSox = rsEox = True
            phys = sox = eox = 0

            phys1 = self.getPHYSTrigFromLTUCount()
            (sox1, eox1) = self.getSOXEOXTrigFromLTUCount()

            while True:
                time.sleep(1)
                phys2 = self.getPHYSTrigFromLTUCount()
                (sox2, eox2) = self.getSOXEOXTrigFromLTUCount()

                physDiff = phys2 - phys1
                soxDiff = sox2 - sox1
                eoxDiff = eox2 - eox1

                # Dealing with overflowing counters..

                if physDiff == 0:
                    if ofPhys != 0: phys = ofPhys*(2**32)
                    rsPhys = True
                elif phys2 - phys1 > 0:
                    phys = physDiff + (2**32)*ofPhys
                    rsPhys = True
                else:
                    if rsPhys: ofPhys += 1
                    phys = physDiff + (2**32)*ofPhys
                    rsPhys = False

                if soxDiff == 0:
                    if ofSox != 0: sox = 16*ofSox
                    rsSox = True
                elif soxDiff > 0:
                    sox = soxDiff + 16*ofSox
                    rsSox = True
                else:
                    if rsSox: ofSox += 1
                    sox = soxDiff + 16*ofSox
                    rsSox = False

                if eoxDiff == 0:
                    if ofEox != 0: eox = 16*ofEox
                    rsEox = True
                elif eox2 - eox1 > 0:
                    eox = eoxDiff + 16*ofEox
                    rsEox = True
                else:
                    if rsEox: ofEox += 1
                    eox = eoxDiff + 16*ofEox
                    rsEox = False

                print(str(phys).rjust(10) + str(sox).rjust(10) + str(eox).rjust(10))

        except KeyboardInterrupt:
            return

#############################################
# Global gen methods
#############################################
    def setRefGen(self, freq = 240):
        """ Set output clock frequency of refgen module <refgen_id> """

        add_refgen = CRUADD['add_pon_wrapper_reg'] + 0x48

        # 0 freq -> forward input data
        # bit31 = '1' for write enable; data is registered on the rising edge of this bit
        refgen_freq = {40 : 0x80000000, 120 : 0x80000001, 240 : 0x80000002, 0 : 0x80000003}

        self.rocWr(add_refgen, 0x0)
        self.rocWr(add_refgen, refgen_freq[freq])

    def resetFpll(self):
        """ Reset global PON TX fPLL """

        add_clkctrl = CRUADD['add_ttc_clkgen_clkctrl']

        # assert and deassert reset bit
        self.rocRdMWr(add_clkctrl, 24, 1, 0x1)
        self.rocRdMWr(add_clkctrl, 24, 1, 0x0)


    def enableClock(self, enable=True):
        """ Enable/Disable 240 MHz clock coming from external jitter cleaner PLL """

        # Controlled output clock: #8 on SI5345_2

        chip_add = 0x68 # chip address is fixed
        si5345_2_addr = CRUADD['add_bsp_i2c_si5345_2']
        p2 = Si534x(self.pcie_id, 2, si5345_2_addr, chip_add, None)

        p2.resetI2C()
        p2.writeI2C((0x0001), 1)
        if enable:
            self.vprint("Enable global 240 MHz clock")
            p2.writeI2C(0x30, 0x6)
        else:
            self.vprint("Disable global 240 MHz clock")
            p2.writeI2C(0x30, 0x4)

    def printPllClockSel(self):
        """ Reports about enabled and selected clock inputs of the external PLL """

        # Note: Global clock is selected in SI5345_2

        chip_add = 0x68 # chip address is fixed
        si5345_2_addr = CRUADD['add_bsp_i2c_si5345_2']
        p2 = Si534x(self.pcie_id, 2, si5345_2_addr, chip_add, None)

        (clkSwitchMode, clkSelMode, clkSel) = p2.getInputInfo()

        print("{} clock is selected".format(["LOCAL", "TTC", "Unknown"][clkSel]))

    def reportPllOutput(self):
        """ Reports which outputs are enabled in the external PLLs """

        chip_add = 0x68 # chip address is fixed
        si5345_2_addr = CRUADD['add_bsp_i2c_si5345_2']
        si5345_1_addr = CRUADD['add_bsp_i2c_si5345_1']
        p2 = Si534x(self.pcie_id, 2, si5345_2_addr, chip_add, None)
        p1 = Si534x(self.pcie_id, 2, si5345_1_addr, chip_add, None)

        print("SI5345 #1")
        p1.resetI2C()
        p1.writeI2C((0x0001), 1)
        outputs = [0x08, 0x0D, 0x12, 0x17, 0x1C, 0x21, 0x26, 0x2B, 0x30, 0x3A]
        for i, output in enumerate(outputs):
            print("Output {} is: ".format(i) + ["Disabled", "Enabled"][p1.readI2C(output) > 1 & 0x1])

        print("")

        print("SI5345 #2")
        p2.resetI2C()
        p2.writeI2C((0x0001), 1)
        outputs = [0x08, 0x0D, 0x12, 0x17, 0x1C, 0x21, 0x26, 0x2B, 0x30, 0x3A]
        for i, output in enumerate(outputs):
            print("Output {} is: ".format(i) + ["Disabled", "Enabled"][p2.readI2C(output) > 1 & 0x1])


    def getClockFreq(self):
        """ Get clock frequencies as seens inside the TTC interface """
        message=("globalgen: | ")
        message+=("ttc240freq {:.2f} MHz | ".format((self.rocRd(CRUADD['add_ttc_clkgen_ttc240freq']) / 1e6)).rjust(27))
        message+=("glb240freq {:.2f} MHz | ".format((self.rocRd(CRUADD['add_ttc_clkgen_glb240freq']) / 1e6))).rjust(27)
        message+=("\npon ref  : | ")
        message+=("rx ref240freq {:.2f} MHz | ".format((self.rocRd(CRUADD['add_ttc_clkgen_rxref240freq']) / 1e6)).rjust(27))
        message+=("tx ref240freq {:.2f} MHz | ".format((self.rocRd(CRUADD['add_ttc_clkgen_txref240freq']) / 1e6))).rjust(27)
        message+=("clk not ok cnt     {} | ".format(self.rocRd(CRUADD['add_ttc_clkgen_clknotokcnt']))).rjust(27)
        print (message)
        #ckcount1=self.rocRd(CRUADD['add_ttc_clkgen_clknotokcnt'])
        #ckcount2=self.rocRd(CRUADD['add_ttc_clkgen_clknotokcnt'])
        #print ("Clock not ok count1: {} count2 {}".format(ckcount1,ckcount2))


#############################################
# CTP Emulator methods
#############################################

    def resetEmulator(self,doReset):
       """ Reset/disable CTP emulator """
       if (doReset):
         self.rocWr(CRUADD['add_ctp_emu_runmode'], 0x3) # go idle
         self.rocRdMWr(CRUADD['add_ctp_emu_ctrl'], 31,1,1)
       else:
         self.rocRdMWr(CRUADD['add_ctp_emu_ctrl'], 31,1,0)

    def setEmulatorTrigMode(self, mode):
       """ Put emulator in triggered mode """

       # always go through idle
       self.rocRdMWr(CRUADD['add_ctp_emu_runmode'],0,2,0x3)

       if mode=="periodic":
         self.rocRdMWr(CRUADD['add_ctp_emu_runmode'],0,2,0x1)
       elif mode=="manual":
         self.rocRdMWr(CRUADD['add_ctp_emu_runmode'],0,2,0x0)
       elif mode == "continuous":
         self.rocRdMWr(CRUADD['add_ctp_emu_runmode'],0,2,0x2)
       else:
         print ('invalid trigger mode, allowed are only periodic/manual/continuous')

    def doManualPhysTrig(self):
       """ Request one physical trigger, works only in manual triggered mode """
       self.rocRdMWr(CRUADD['add_ctp_emu_runmode'],8,1,0x01) # set bit
       self.rocRdMWr(CRUADD['add_ctp_emu_runmode'],8,1,0x00) # clear bit

    def setEmulatorContMode(self):
      """ Put emulator in continuous mode """
      self.rocRdMWr(CRUADD['add_ctp_emu_runmode'],0,2,0x3) # always go through idle
      self.rocRdMWr(CRUADD['add_ctp_emu_runmode'],0,2,0x2)

    def setEmulatorIdleMode(self):
      """ Put emulator in idle mode (generate SOX if running) """
      self.rocRdMWr(CRUADD['add_ctp_emu_runmode'],0,2,0x3) # always go through idle

    def setEmulatorStandaloneFlowControl(self,allow=False):
      """ Controls CTPemulator HBF rejection, when True activate internal flow control """
      self.rocRdMWr(CRUADD['add_ctp_emu_runmode'],2,1,allow)

    def setEmulatorBCMAX(self,BCMAX):
       """ Set Bunch Crossing ID max value (12 bit), will count from 0 to max BCID value  """
       if (BCMAX>self.max_bcid) :
          print ('BAD BCMAX value {}'.format(BCMAX))
       else:
         self.rocWr(CRUADD['add_ctp_emu_bc_max'], BCMAX)

    def setEmulatorHBMAX(self,HBMAX):
      """ Set Heart Bit ID max value (16 bit)  """
      if (HBMAX>(1<<16)-1) :
         print ('BAD HBMAX value {}'.format(HBMAX))
      else:
         self.rocWr(CRUADD['add_ctp_emu_hb_max'], HBMAX)

    def setEmulatorPrescaler(self,HBKEEP,HBDROP):
      """ Set Heart Bit frames to keep (16 bit) and to drop.
      
      Cycle always start with keep, then it alternates with HB to keep and to drop
      until the end of TimeFrame.
      Use a HBDROP larger than HBMAX to keep HBF only at the beginning of HBF
      """
      if (HBKEEP>(1<<16)-1 or HBKEEP<2) :
         raise ValueError ('BAD HBKEEP value  {}, must be >=2 and < 0xFFFF'.format(HBKEEP))

      if (HBDROP>(1<<16)-1 or HBDROP<2) :
         raise ValueError ('BAD HBDROP value {}, must be >=2 and < 0xFFFF'.format(HBDROP))

      self.rocWr(CRUADD['add_ctp_emu_prescaler'], (HBDROP<<16) | HBKEEP)

    def setEmulatorPHYSDIV(self,PHYSDIV):
      """ Generate physics trigger every PHYSDIV ticks (28 bit max), larger than 7 to activate  """
      if (PHYSDIV>(1<<28)-1) :
         print ('BAD PHYSDIV value {}'.format(PHYSDIV))
      else:
         self.rocWr(CRUADD['add_ctp_emu_physdiv'], PHYSDIV)

    def setEmulatorCALDIV(self,CALDIV):
      """ Generate calibration trigger every CALDIV ticks (28 bit max), larger than 18 to activate  """
      if (CALDIV>(1<<28)-1) :
         print ('BAD CALDIV value {}'.format(CALDIV))
      else:
         self.rocWr(CRUADD['add_ctp_emu_caldiv'], CALDIV)

    def setEmulatorHCDIV(self,HCDIV):
      """ Generate healthcheck trigger every HCDIV ticks (28 bit max), larger than 10 to activate  """
      if (HCDIV>(1<<28)-1) :
         print ('BAD HCDIV value {}'.format(HCDIV))
      else:
         self.rocWr(CRUADD['add_ctp_emu_hcdiv'], HCDIV)

    def setFBCT(self,FBCT_array):
      """ Set trigger at fixed bunch crossings. 9 values must always be transferred, a value of 0 deactivate the slot """
      if len(FBCT_array)!=9 :
         print ('BAD FBCT array length {}'.format(len(FBCT_array)))
      else:
         for val in FBCT_array:
            if val<0 or val >self.max_bcid:
              raise ValueError("Invalid FBCT value")
            if val==0: # deactivate FBCT
              newval=0
            elif val<=2: # compensate latency
              newval=self.max_bcid-(2-val)
            else:
              newval=val-2
            self.rocWr(CRUADD['add_ctp_emu_fbct'], newval)


#############################################
# Pattern player methods
#############################################

    def patplayerConfig(func):
      """ decorator for pattern player config methods """

      def configWrapper(self, *args, **kwargs):
        # start editing parameters
        self.rocRdMWr(CRUADD['add_patplayer_cfg'], 0, 1, 1)

        func(self, *args, **kwargs)

        # end editing parameters
        self.rocRdMWr(CRUADD['add_patplayer_cfg'], 0, 1, 0)

      return configWrapper


    @patplayerConfig
    def setIdlePattern(self, idlePattern):
      """ Patter player: Sets IDLE pattern """

      self.vprint("Setting IDLE pattern...")
      self.rocWr(CRUADD['add_patplayer_idlepat0'], idlePattern & 0xffffffff)
      self.rocWr(CRUADD['add_patplayer_idlepat1'], (idlePattern >> 32) & 0xffffffff)
      self.rocWr(CRUADD['add_patplayer_idlepat2'], (idlePattern >> 64) & 0xffff)

    @patplayerConfig
    def setSyncPattern(self, syncPattern):
      """ Patter player: Sets SYNC pattern """

      self.vprint("Setting SYNC pattern...")
      self.rocWr(CRUADD['add_patplayer_syncpat0'], syncPattern & 0xffffffff)
      self.rocWr(CRUADD['add_patplayer_syncpat1'], (syncPattern >> 32) & 0xffffffff)
      self.rocWr(CRUADD['add_patplayer_syncpat2'], (syncPattern >> 64) & 0xffff)

    @patplayerConfig
    def setResetPattern(self, resetPattern):
      """ Patter player: Sets RESET pattern """

      self.vprint("Setting RESET pattern...")
      self.rocWr(CRUADD['add_patplayer_rstpat0'], resetPattern & 0xffffffff)
      self.rocWr(CRUADD['add_patplayer_rstpat1'], (resetPattern >> 32) & 0xffffffff)
      self.rocWr(CRUADD['add_patplayer_rstpat2'], (resetPattern >> 64) & 0xffff)

    @patplayerConfig
    def configSync(self, syncLength=1, syncDelay=0):
      """ Pattern player: Configure length and delay of SYNC pattern """

      self.vprint("Setting SYNC length...")
      self.rocWr(CRUADD['add_patplayer_synccnt'], syncLength + syncDelay)

      self.vprint("Setting DELAY length...")
      self.rocWr(CRUADD['add_patplayer_delaycnt'], syncDelay)


    @patplayerConfig
    def configReset(self, resetLength=1):
      """ Pattern player: Configure length of RESET pattern """

      self.vprint("Setting RESET length...")
      self.rocWr(CRUADD['add_patplayer_rstcnt'], resetLength)

    @patplayerConfig
    def selectPatternTrig(self, syncTrig=3, resetTrig=3):
      """ Pattern player: Select from TTC_DATA[31:0] which bit to trigger
      the SYNC and RESET patterns """

      self.vprint("Setting trigger bits...")
      self.rocWr(CRUADD['add_patplayer_trigsel'], (resetTrig << 16) | syncTrig)


    def enableSyncAtStart(self, enable=False):
      """ Enable/disable automatically sending sync pattern when runenable goes high """

      if enable:
          self.rocRdMWr(CRUADD['add_patplayer_cfg'], 12, 1, 1)
      else:
          self.rocRdMWr(CRUADD['add_patplayer_cfg'], 12, 1, 0)


    def triggerReset(self):
      """ Pattern player: Trigger RESET pattern manually """

      self.rocRdMWr(CRUADD['add_patplayer_cfg'], 4, 1, 1)
      self.rocRdMWr(CRUADD['add_patplayer_cfg'], 4, 1, 0)


    def triggerSync(self):
      """ Pattern player: Trigger SYNC pattern manually """

      self.rocRdMWr(CRUADD['add_patplayer_cfg'], 8, 1, 1)
      self.rocRdMWr(CRUADD['add_patplayer_cfg'], 8, 1, 0)
