from ROC import *

class RocExt(Roc):
    """ Extension of ROC py to add some tools
    PCIe channel must be opened to use some of the methods!
    """
    def __init__(self, verbose=False):
        self.verbose = verbose

    def vprint(self, text):
        """ Print if verbose flag is set """
        if self.verbose:
          print (" {}".format(text))

    def mid(self, data, pos, width) :
        mask = pow(2, width) - 1
        result = (data >> pos) & mask
        return result


    def rocRdMWr(self, addr, pos, width, value):
        """ Read-Modify-Write width number of bit """
        mask = (pow(2, width) - 1) << pos
        data0 = self.rocRd(addr)
        data1 = (data0 & ~mask) | ((value << pos) & mask)
        self.rocWr(addr, data1)

    def waitForBit(self, address, position, value):
        """ Waits for a single bit until timeout (500 ms) """
        t0 = time.time()
        timeout = t0 + 0.5 # 500 ms timout

        while True:
          data = self.rocRd(address)
          bit = self.mid(data, position, 1)
          if (bit == value):
                break

          if (time.time() >= timeout) :
                print ("cru::hw::waitForBit (0x{:08x}, {}, {}) - TIMEOUT".format(address, position, value))
                break

        return bit

    def atxcal0(self, baseAddress):
        """ Calibrate ATX PLL """

        self.vprint("Starting ATX PLL calibration")

        id = self.rocRd(baseAddress + 4 * 0x200)

        self.vprint("  BaseAddress: 0x%08X, Identifier: 0x%02X" % (baseAddress, id))
        self.vprint("  Requesting internal configuration bus user access...")

        # Set ATX PLL to feedback compensation mode (0x110[2] = 0'b1)
        self.rocRdMWr(baseAddress + 4 * 0x110, 2, 1, 0x1)

        # a. Do direct write of 0x02 to address  0x000 to request access to internal configuration bus (do not use RMW).
        self.rocWr(baseAddress + 4 * 0x000, 0x02)

        # b. Read bit[2] of 0x280 to check it is zero (user has control)
        self.waitForBit(baseAddress + 4 * 0x280, 2, 0)

        # c. Do RMW 0x01 with mask 0x01 to address 0x100 to enable ATX PLL calibration
        self.vprint("  Waiting for calibration done...")
        self.rocRdMWr(baseAddress + 4 * 0x100, 0, 1, 0x1)

        # d. Do RMW 0x01 with mask 0xFF to address 0x000 to let the PreSice doing the calibration
        self.rocRdMWr(baseAddress + 4 * 0x000, 0, 8, 0x01)

        # e. Read bit[1] of 0x280 to become 0
        t0 = time.time()
        self.waitForBit(baseAddress + 4 * 0x280, 1, 0)
        self.vprint("  ATX PLL Calibration completed")
        self.vprint("    Elapsed time:  %0.2f ms" % ((time.time() - t0) * 1e3))
        self.vprint(" ")

        # f. When bit[1] of 0x28 is 0 ATX PLL calibration has been completed.

        # Set ATX PLL to feedback compensation mode (0x110[2] = 0'b0)
        self.rocRdMWr(baseAddress + 4 * 0x110, 2, 1, 0x0)


    def fpllref0(self, baseAddress, refclk):
        if (refclk > 4):
            raise ValueError("Invalid refclk input: {} (should be between 0 and 4)".format(refclk))

        self.vprint("Setting fPLLs refclk to refclk{}".format(refclk))

        lookup_reg_addr_0 = 0x117 + refclk
        lookup_reg_addr_1 = 0x11D + refclk
        current114 = self.rocRd(baseAddress + 4 * 0x114)
        current11C = self.rocRd(baseAddress + 4 * 0x11C)
        new114 = self.rocRd(baseAddress + 4 * lookup_reg_addr_0)
        new11C = self.rocRd(baseAddress + 4 * lookup_reg_addr_1)
        self.vprint("({}) : (0x114) = 0x{:02x} updated with value 0x{:02x}".format(baseAddress, current114, new114))
        self.vprint("({}) : (0x11C) = 0x{:02x} updated with value 0x{:02x}".format(baseAddress, current11C, new11C))
        self.rocRdMWr(baseAddress + 4 * 0x114, 0, 8, new114)
        self.rocRdMWr(baseAddress + 4 * 0x11C, 0, 8, new11C)


    def fpllcal0(self, baseAddress, configCompensation = True) :
        self.vprint("Starting fPLL calibration")

        id = self.rocRd(baseAddress + 4 * 0x200)
        self.vprint("BaseAddress: 0x{:08X}, Identifier: 0x{:02X}".format(baseAddress, id))

        # Set fPLL to direct feedback mode (0x126[0] = 1'b1)
        self.rocRdMWr(baseAddress + 4 * 0x126, 0, 1, 0x1)

        self.vprint("Requesting internal configuration bus user access ...")

        # a. Do direct write of 0x02 to address  0x000 to request access to internal configuration bus (do not use RMW).
        #self.rocWr(baseAddress + 4 * 0x000, 0x02)
        self.rocRdMWr(baseAddress + 4 * 0x000, 0, 8, 0x02)

        # b. Read bit[2] of 0x280 to check it is zero (user has control)
        self.waitForBit(baseAddress + 4 * 0x280, 2, 0)

        # c. Do RMW 0x02 with mask 0x02 to address 0x100 to enable fPLL calibration
        self.vprint("Waiting for calibration done ...")
        self.rocRdMWr(baseAddress + 4 * 0x100, 1, 1, 0x1)

        # d. Do RMW 0x01 with mask 0xFF to address 0x000 to let the PreSice doing the calibration
        # rmw $m $base_addr 0x000 0xFF 0x01
        self.rocRdMWr(baseAddress + 4 * 0x000, 0, 8, 0x01)

        # e. Read bit[1] of 0x280 to become 0
        t0 = time.time()
        self.waitForBit(baseAddress + 4 * 0x280, 1, 0)
        self.vprint(" %0.2f ms" % ((time.time() - t0) * 1e3))

        # f. When bit[1] of 0x28 is 0 ATX PLL calibration has been completed.

        # Set fPLL to feedback compensation mode (0x126[0] = 0'b0)
        if configCompensation:
                self.rocRdMWr(baseAddress + 4 * 0x126, 0, 1, 0x0)

        #sleep(2)

        pll_locked = self.mid(self.rocRd(baseAddress + 4 * 0x280), 0, 1)
        self.vprint("pll_locked: %s" % ["FAILED", "OK"][pll_locked])


    def rxcal0(self, baseAddress):
        """ Calibrate XCVR RX """

        # a. Do direct write of 0x02 to address  0x000 to request access to internal configuration bus (do not use RMW).
        self.rocWr(baseAddress + 4 * 0x000, 0x02)

        # b. Read bit[2] of 0x280 to check it is zero (user has control)
        self.waitForBit(baseAddress + 4 * 0x280, 2, 0)

        # c. Do RMW 0x00 with mask 0x10 to address 0x281 to set bit 4 to zero to mask out tx_cal_busy.
        self.rocRdMWr(baseAddress + 4 * 0x281, 4, 1, 0x0)

        # d. Do RMW 0x02 with mask 0x42 to address 0x100 to set the Rx calibration bit. (note: bit[6] needs to be masked as well).).
        self.rocRdMWr(baseAddress + 4 * 0x100, 1, 1, 0x1)
        self.rocRdMWr(baseAddress + 4 * 0x100, 6, 1, 0x0)

        # e. Set the rate switch flag register for PMA Rx calibration (*)

        # f. Do RMW 0x01 with mask 0xFF to address 0x000 to let the PreSice doing the calibration
        self.rocRdMWr(baseAddress + 4 * 0x000, 0, 8, 0x01)

        # g. Read bits [1] of 0x281 to become 0
        t0 = time.time()
        self.waitForBit(baseAddress + 4 * 0x281, 1, 0)
        dt = " %0.2f ms" % ((time.time() - t0) * 1e3)

        # g. When bit[1] of 0x281 is 0 receiver calibration has been completed

        # i. Do RMW 0x10 with mask 0x10 to address 0x281 to set bit 4 to one again to enable again the tx_cal_busy.

        self.rocRdMWr(baseAddress + 4 * 0x281, 4, 1, 0x1)

        self.vprint("  - base: 0x{:08X} - RX recalibration time: {}".format(baseAddress, dt))

    def txcal0(self, baseAddress):
        """ Calibrate XCVR TX """

        # a. Do direct write of 0x02 to address  0x000 to request access to internal configuration bus (do not use RMW).
        self.rocWr(baseAddress + 4 * 0x000, 0x02)

        # b. Read bit[2] of 0x280 to check it is zero (user has control)
        self.waitForBit(baseAddress + 4 * 0x280, 2, 0)

        # c. Do RMW 0x00 with mask 0x20 to address 0x281 to set bit 5 to zero to mask out rx_cal_busy.
        self.rocRdMWr(baseAddress + 4 * 0x281, 5, 1, 0x0)

        # d. Do RMW 0x20 with mask 0x60 to address 0x100 to set the Tx calibration bit (note: bit[6] needs to be masked as well).).
        self.rocRdMWr(baseAddress + 4 * 0x100, 5, 1, 0x1)
        self.rocRdMWr(baseAddress + 4 * 0x100, 6, 1, 0x0)

        # e. Do RMW 0x01 with mask 0xFF to address 0x000 to let the PreSice doing the calibration
        self.rocRdMWr(baseAddress + 4 * 0x000, 0, 8, 0x01)

        # f. Read bit [0] of 0x281 to become 0
        t0 = time.time()
        self.waitForBit(baseAddress + 4 * 0x281, 0, 0)
        dt = " %0.2f ms" % ((time.time() - t0) * 1e3)

        # g. When bit[0] of 0x281 is 0 transmitter calibration has been completed

        # h. Do RMW 0x20 with mask 0x20 to address 0x281 to set bit 5 to one again to enable again the rx_cal_busy.
        self.rocRdMWr(baseAddress + 4 * 0x281, 5, 1, 0x1)

        self.vprint("  - base: 0x{:08X} - TX recalibration time: {}".format(baseAddress, dt))
