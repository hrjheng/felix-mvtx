"""WP10 implementation of the GBT.
The file is meant to provide user usable functions for the CRU defined class
"""

import logging
import time

from roc import Roc
from cru_table import CRUADD


class CruGbt(Roc):
    """
    WP10-defined wrapper for GBT
    several functions imported from equivalent class in cru-sw subtree
    """

    def __init__(self, pcie_opened_roc, ch_range):
        """Init method for GBT"""

        Roc.__init__(self)
        self.set_roc(pcie_opened_roc)

        self.num_of_wrappers = self.get_wrapper_count()
        self.link_ids = []
        self.links = self.get_filtered_link_list(ch_range)

        self.name = "GBT"
        self.logger = logging.getLogger(f"{self.name}")

    def initialize(self):
        """Initializes the module for the ITS operation"""
        self.disable_internal_data_generator()
        self.txmode("gbt")
        self.rxmode("gbt")
        self.loopback(0)
        self.patternmode("counter")

    # --- JS Imported from cru-sw ------------------------------
    def atxcal0(self, base_address):
        """ Calibrate ATX PLL """

        # Set ATX PLL to feedback compensation mode (0x110[2] = 0'b1)
        self.roc_rmw(base_address + 4 * 0x110, 2, 1, 0x1)

        # a. Do direct write of 0x02 to address  0x000 to request access to internal configuration bus (do not use RMW).
        self.roc_write(base_address + 4 * 0x000, 0x02)

        # b. Read bit[2] of 0x280 to check it is zero (user has control)
        self.wait_for_bit(base_address + 4 * 0x280, 2, 0)

        # c. Do RMW 0x01 with mask 0x01 to address 0x100 to enable ATX PLL calibration
        self.roc_rmw(base_address + 4 * 0x100, 0, 1, 0x1)

        # d. Do RMW 0x01 with mask 0xFF to address 0x000 to let the PreSice doing the calibration
        self.roc_rmw(base_address + 4 * 0x000, 0, 8, 0x01)

        # e. Read bit[1] of 0x280 to become 0
        self.wait_for_bit(base_address + 4 * 0x280, 1, 0)

        # f. When bit[1] of 0x28 is 0 ATX PLL calibration has been completed.

        # Set ATX PLL to feedback compensation mode (0x110[2] = 0'b0)
        self.roc_rmw(base_address + 4 * 0x110, 2, 1, 0x0)

    def fpllref0(self, base_address, refclk):
        assert 0 <= refclk < 5, f"Invalid refclk input: {refclk} (should be between 0 and 4)"

        lookup_reg_addr_0 = 0x117 + refclk
        lookup_reg_addr_1 = 0x11D + refclk
        new114 = self.roc_read(base_address + 4 * lookup_reg_addr_0)
        new11c = self.roc_read(base_address + 4 * lookup_reg_addr_1)
        self.roc_rmw(base_address + 4 * 0x114, 0, 8, new114)
        self.roc_rmw(base_address + 4 * 0x11C, 0, 8, new11c)

    def fpllcal0(self, base_address, config_compensation=True):
        # Set fPLL to direct feedback mode (0x126[0] = 1'b1)
        self.roc_rmw(base_address + 4 * 0x126, 0, 1, 0x1)

        # a. Do direct write of 0x02 to address  0x000 to request access to internal configuration bus (do not use RMW).
        self.roc_rmw(base_address + 4 * 0x000, 0, 8, 0x02)

        # b. Read bit[2] of 0x280 to check it is zero (user has control)
        self.wait_for_bit(base_address + 4 * 0x280, 2, 0)

        # c. Do RMW 0x02 with mask 0x02 to address 0x100 to enable fPLL calibration
        self.roc_rmw(base_address + 4 * 0x100, 1, 1, 0x1)

        # d. Do RMW 0x01 with mask 0xFF to address 0x000 to let the PreSice doing the calibration
        # rmw $m $base_addr 0x000 0xFF 0x01
        self.roc_rmw(base_address + 4 * 0x000, 0, 8, 0x01)

        # e. Read bit[1] of 0x280 to become 0
        self.wait_for_bit(base_address + 4 * 0x280, 1, 0)

        # f. When bit[1] of 0x28 is 0 ATX PLL calibration has been completed.

        # Set fPLL to feedback compensation mode (0x126[0] = 0'b0)
        if config_compensation:
            self.roc_rmw(base_address + 4 * 0x126, 0, 1, 0x0)

    def rxcal0(self, base_address):
        """ Calibrate XCVR RX """

        # a. Do direct write of 0x02 to address  0x000 to request access to internal configuration bus (do not use RMW).
        self.roc_write(base_address + 4 * 0x000, 0x02)

        # b. Read bit[2] of 0x280 to check it is zero (user has control)
        self.wait_for_bit(base_address + 4 * 0x280, 2, 0)

        # c. Do RMW 0x00 with mask 0x10 to address 0x281 to set bit 4 to zero to mask out tx_cal_busy.
        self.roc_rmw(base_address + 4 * 0x281, 4, 1, 0x0)

        # d. Do RMW 0x02 with mask 0x42 to address 0x100 to set the Rx calibration bit. (note: bit[6] needs to be masked as well).).
        self.roc_rmw(base_address + 4 * 0x100, 1, 1, 0x1)
        self.roc_rmw(base_address + 4 * 0x100, 6, 1, 0x0)

        # e. Set the rate switch flag register for PMA Rx calibration (*)

        # f. Do RMW 0x01 with mask 0xFF to address 0x000 to let the PreSice doing the calibration
        self.roc_rmw(base_address + 4 * 0x000, 0, 8, 0x01)

        # g. Read bits [1] of 0x281 to become 0
        self.wait_for_bit(base_address + 4 * 0x281, 1, 0)

        # g. When bit[1] of 0x281 is 0 receiver calibration has been completed

        # i. Do RMW 0x10 with mask 0x10 to address 0x281 to set bit 4 to one again to enable again the tx_cal_busy.
        self.roc_rmw(base_address + 4 * 0x281, 4, 1, 0x1)

    def txcal0(self, base_address):
        """ Calibrate XCVR TX """

        # a. Do direct write of 0x02 to address  0x000 to request access to internal configuration bus (do not use RMW).
        self.roc_write(base_address + 4 * 0x000, 0x02)

        # b. Read bit[2] of 0x280 to check it is zero (user has control)
        self.wait_for_bit(base_address + 4 * 0x280, 2, 0)

        # c. Do RMW 0x00 with mask 0x20 to address 0x281 to set bit 5 to zero to mask out rx_cal_busy.
        self.roc_rmw(base_address + 4 * 0x281, 5, 1, 0x0)

        # d. Do RMW 0x20 with mask 0x60 to address 0x100 to set the Tx calibration bit (note: bit[6] needs to be masked as well).).
        self.roc_rmw(base_address + 4 * 0x100, 5, 1, 0x1)
        self.roc_rmw(base_address + 4 * 0x100, 6, 1, 0x0)

        # e. Do RMW 0x01 with mask 0xFF to address 0x000 to let the PreSice doing the calibration
        self.roc_rmw(base_address + 4 * 0x000, 0, 8, 0x01)

        # f. Read bit [0] of 0x281 to become 0
        self.wait_for_bit(base_address + 4 * 0x281, 0, 0)

        # g. When bit[0] of 0x281 is 0 transmitter calibration has been completed

        # h. Do RMW 0x20 with mask 0x20 to address 0x281 to set bit 5 to one again to enable again the rx_cal_busy.
        self.roc_rmw(base_address + 4 * 0x281, 5, 1, 0x1)

    def get_wrapper_count(self):
        """ Self.Gets number of GBT wrappers """
        wrapper_count = 0

        for i in range(0, 2):
            # If the clock counter (reg11) is running we accept it as a valid gbt wrapper
            reg11a = self.roc_read(self.get_global_reg_address(i) + CRUADD['add_gbt_wrapper_clk_cnt'])
            reg11b = self.roc_read(self.get_global_reg_address(i) + CRUADD['add_gbt_wrapper_clk_cnt'])

            if reg11a != reg11b:
                wrapper_count += 1

        return wrapper_count

    def get_base_address(self, wrapper):
        return [CRUADD['add_gbt_wrapper0'], CRUADD['add_gbt_wrapper1']][wrapper]

    def get_global_reg_address(self, wrapper):
        """ Return global register address of the specified GBT wrapper """
        return self.get_base_address(wrapper) + CRUADD['add_gbt_wrapper_gregs']

    def get_atx_pll_reg_address(self, wrapper, reg):
        """ Return ATX PLL register address of the specified GBT wrapper """
        return self.get_base_address(wrapper) + CRUADD['add_gbt_wrapper_atx_pll'] + 4 * reg

    def get_bank_pll_reg_address(self, wrapper, bank):
        """ Return fPLL base address of the specified GBT bank """
        return self.get_base_address(wrapper) + \
            CRUADD['add_gbt_wrapper_bank_offset'] * (bank + 1) + \
            CRUADD['add_gbt_bank_fpll']

    def get_rx_ctrl_address(self, wrapper, bank, link):
        """ Return RX control register address of the specified GBT link"""
        return self.get_base_address(wrapper) + \
            CRUADD['add_gbt_wrapper_bank_offset'] * (bank + 1) + \
            CRUADD['add_gbt_bank_link_offset'] * (link + 1) + \
            CRUADD['add_gbt_link_regs_offset'] + \
            CRUADD['add_gbt_link_rx_ctrl_offset']

    def get_tx_ctrl_address(self, wrapper, bank, link):
        """ Return TX control register address of the specified GBT link"""
        return self.get_base_address(wrapper) + \
            CRUADD['add_gbt_wrapper_bank_offset'] * (bank + 1) + \
            CRUADD['add_gbt_bank_link_offset'] * (link + 1) + \
            CRUADD['add_gbt_link_regs_offset'] + \
            CRUADD['add_gbt_link_tx_ctrl_offset']

    def get_data_error_cnt(self, wrapper, bank, link):
        """ Return Data-Not-Locked error counter of the specified GBT link"""
        return self.roc_read(self.get_base_address(wrapper) + \
                             CRUADD['add_gbt_wrapper_bank_offset'] * (bank + 1) + \
                             CRUADD['add_gbt_bank_link_offset'] * (link + 1) + \
                             CRUADD['add_gbt_link_regs_offset'] +\
                             CRUADD['add_gbt_link_data_errcnt_offset'])

    def get_status_address(self, wrapper, bank, link):
        """ Return status register  of the specified GBT link"""
        return self.get_base_address(wrapper) + \
            CRUADD['add_gbt_wrapper_bank_offset'] * (bank + 1) + \
            CRUADD['add_gbt_bank_link_offset'] * (link + 1) + \
            CRUADD['add_gbt_link_regs_offset'] + \
            CRUADD['add_gbt_link_status']

    def get_rx_clk_cnt(self, wrapper, bank, link):
        """ Return RX clock frequency of the specified GBT link"""
        return self.roc_read(self.get_base_address(wrapper) + \
                             CRUADD['add_gbt_wrapper_bank_offset'] * (bank + 1) + \
                             CRUADD['add_gbt_bank_link_offset'] * (link + 1) + \
                             CRUADD['add_gbt_link_regs_offset'] + \
                             CRUADD['add_gbt_link_rxclk_cnt'])

    def get_tx_clk_cnt(self, wrapper, bank, link):
        """ Return TX clock frequency of the specified GBT link"""
        return self.roc_read(self.get_base_address(wrapper) + \
                             CRUADD['add_gbt_wrapper_bank_offset'] * (bank + 1) + \
                             CRUADD['add_gbt_bank_link_offset'] * (link + 1) + \
                             CRUADD['add_gbt_link_regs_offset'] + \
                             CRUADD['add_gbt_link_txclk_cnt'])

    def get_rx_error_cnt(self, wrapper, bank, link):
        """ Return RX error counter register  of the specified GBT link"""
        return self.roc_read(self.get_base_address(wrapper) + \
                             CRUADD['add_gbt_wrapper_bank_offset'] * (bank + 1) + \
                             CRUADD['add_gbt_bank_link_offset'] * (link + 1) + \
                             CRUADD['add_gbt_link_regs_offset'] + \
                             CRUADD['add_gbt_link_rx_err_cnt'])

    def get_source_select_address(self, wrapper, bank, link):
        """ Return source select register  of the specified GBT link"""
        return self.get_base_address(wrapper) + \
            CRUADD['add_gbt_wrapper_bank_offset'] * (bank + 1) + \
            CRUADD['add_gbt_bank_link_offset'] * (link + 1) + \
            CRUADD['add_gbt_link_regs_offset'] + \
            CRUADD['add_gbt_link_source_sel']

    def get_xcvr_reg_address(self, wrapper, bank, link, reg):
        """ At beginning used blindly (assuming links in roder), and later on link rempapping)"""
        return self.get_base_address(wrapper) + \
            CRUADD['add_gbt_wrapper_bank_offset'] * (bank + 1) + \
            CRUADD['add_gbt_bank_link_offset'] * (link + 1) + \
            CRUADD['add_gbt_link_xcvr_offset'] + 4 * reg

    # ------------------------------------------------------------------------------

    def get_wrapper_link_list(self, wrapper):
        links = []
        wrapper_config = self.roc_read(self.get_global_reg_address(wrapper) + CRUADD['add_gbt_wrapper_conf0'])

        for bank in range(6):
            lpb = self.mid(wrapper_config, 4 + 4 * bank, 4)  # recover each char to determine the number of links per bank
            if lpb == 0:
                break
            for link in range(lpb):  # for each gbt_link in bank (not in order!)
                base_address = self.get_xcvr_reg_address(wrapper, bank, link, 0)
                links.append([wrapper, bank, link, base_address])

        new_links = links[:]
        for l in range(len(links)):  # reorder link list to match physicak implementation (check firmware to have a clarification)
            _, orig_bank, _, _ = links[l]
            new_pos = (l - orig_bank * 6) * 2 + 12 * int(orig_bank / 2) + (orig_bank % 2)
            new_links[new_pos] = links[l]

        return new_links

    #  ------------------------------------------------------------------------------

    def get_link_list(self):
        """ Constructs the link list (wrapper,bank, link)"""
        links = []
        for wrapper in range(self.num_of_wrappers):
            newlinks = self.get_wrapper_link_list(wrapper)
            links += newlinks
        return links

    def get_num_of_links_per_bank(self):
        """ Return the number of links per bank in each wrapper """
        data = []
        for wrapper in range(self.num_of_wrappers):
            addr = self.get_global_reg_address(wrapper) + CRUADD['add_gbt_wrapper_conf0']
            data.append(self.mid(self.roc_read(addr), 4, 24))
        return data

    def is_gbt_wrapper(self):
        """ Checks the wrapper type (TRD or GBT)"""
        det_type = []
        for wrapper in range(self.num_of_wrappers):
            addr = self.get_global_reg_address(wrapper) + CRUADD['add_gbt_wrapper_conf1']
            data = self.roc_read(addr)
            det_type.append(hex(self.mid(data, 12, 12)))
        return '0xb69' in det_type

    def get_gbt_wrapper_type(self):
        """ Checks the GBT wrapper type (wide or dynamic)"""
        if not self.is_gbt_wrapper():
            raise ValueError("Not a GBT wrapper")
        gbt_type = []
        for wrapper in range(self.num_of_wrappers):
            addr = self.get_global_reg_address(wrapper) + CRUADD['add_gbt_wrapper_conf1']
            data = self.roc_read(addr)
            gbt_type.append(hex(self.mid(data, 8, 4)))
        if '0x5' in gbt_type:
            return 'wide'
        return 'dynamic'

    def get_total_num_of_links(self):
        """ Return the total number of links """
        num_of_links = 0
        for wrapper in range(self.num_of_wrappers):
            addr = self.get_global_reg_address(wrapper) + CRUADD['add_gbt_wrapper_conf1']
            data = self.roc_read(addr)
            num_of_links += self.mid(data, 24, 8)
        return num_of_links

    # ------------------------------------------------------------------------------

    def get_filtered_link_list(self, ch_range):
        """ Self.Get user specified list of links """

        all_links = self.get_link_list()
        if ch_range == "all":
            return [[i,] + all_links[i] for i in range(len(all_links))]

        if ch_range.find("-") > -1:
            r0 = int(ch_range.split("-")[0])
            r1 = int(ch_range.split("-")[1])
            if (r0 > r1) or (r0 < 0) or (r1 > len(all_links) - 1):
                raise ValueError(f"Link index out of range, max link index is {len(all_links) - 1}")
            return [[i,] + all_links[i] for i in range(r0, r1 + 1)]

        links = []
        for i in ch_range.split(","):
            if (int(i) < 0) or (int(i) > len(all_links) - 1):
                raise ValueError("Link index out of range, max link index is {len(all_links) - 1}")
            links.append([int(i),] + all_links[int(i)])
        return links

    def get_link_indices(self):
        """ Get logical indices of the links """
        return [link[0] for link in self.links]

    # ------------------------------------------------------------------------------

    def atxref(self, refclk):
        assert 0 <= refclk <= 4, f"Invalid refclk input: {refclk} (should be between 0 and 4)"

        lookup_reg_addr = 0x113 + refclk
        data = self.roc_read(self.get_atx_pll_reg_address(0, lookup_reg_addr))
        self.roc_write(self.get_atx_pll_reg_address(0, 0x112), data)

    def fpllref(self, refclk, base_address=0):
        assert 0 <= refclk <= 4, f"Invalid refclk input: {refclk} (should be between 0 and 4)"

        if base_address != 0:
            self.fpllref0(base_address, refclk)
        else:
            prev_wrapper = -1
            prev_bank = -1
            for entry in self.links:
                _, wrapper, bank, _, _ = entry
                if (prev_wrapper != wrapper) or (prev_bank != bank):
                    self.fpllref0(self.get_bank_pll_reg_address(wrapper, bank), refclk)
                    prev_wrapper = wrapper
                    prev_bank = bank

    def cdrref(self, refclk):
        assert 0 <= refclk <= 4, f"Invalid refclk input: {refclk} (should be between 0 and 4)"

        for entry in self.links:
            _, wrapper, bank, link, _ = entry
            lookup_reg_addr = 0x16A + refclk
            data = self.roc_read(self.get_xcvr_reg_address(wrapper, bank, link, lookup_reg_addr))
            self.roc_write(self.get_xcvr_reg_address(wrapper, bank, link, 0x141), data)

    def atxcal(self, base_address=0):
        if base_address != 0:
            self.atxcal0(base_address)
        else:
            for wrapper in range(self.num_of_wrappers):
                self.atxcal0(self.get_atx_pll_reg_address(wrapper, 0x000))

    def fpllcal(self, base_address=0, config_compensation=True):
        if base_address != 0:
            self.fpllcal0(base_address, config_compensation)
        else:
            prev_wrapper = -1
            prev_bank = -1
            for entry in self.links:
                _, wrapper, bank, _, base_address = entry
                if (prev_wrapper != wrapper) or (prev_bank != bank):
                    self.fpllcal0(self.get_bank_pll_reg_address(wrapper, bank), config_compensation)
                    prev_wrapper = wrapper
                    prev_bank = bank

    def rxcal(self):
        """ Calibrate XCVR RX """

        for entry in self.links:
            _, _, _, _, base_address = entry
            self.rxcal0(base_address)

    def txcal(self):
        """ Calibrate XCVR TX for all links """

        for entry in self.links:
            _, _, _, _, base_address = entry
            self.txcal0(base_address)

    # ------------------------------------------------------------------------------

    def cntrst(self):
        """ Reset error counter in specified links """

        for entry in self.links:
            _, wrapper, bank, link, _ = entry
            self.roc_rmw(self.get_source_select_address(wrapper, bank, link), 6, 1, 0x1)  # set error counter reset
            self.roc_rmw(self.get_source_select_address(wrapper, bank, link), 6, 1, 0x0)  # release error counter reset

    # ------------------------------------------------------------------------------

    def cntinit(self):
        """ Reset error counter for all links being present in the card """
        self.cntrst()

    # ------------------------------------------------------------------------------

    def get_fec_cnt(self, wrapper, bank, link):
        """ Return number of corrected error for a specific GBT link (16 bit max)"""
        return self.roc_read(self.get_base_address(wrapper) + \
                             CRUADD['add_gbt_wrapper_bank_offset'] * (bank + 1) + \
                             CRUADD['add_gbt_bank_link_offset'] * (link + 1) + \
                             CRUADD['add_gbt_link_regs_offset'] + \
                             CRUADD['add_gbt_link_fec_monitoring'])

    # ------------------------------------------------------------------------------

    def get_ref_frequencies(self):
        """ Get GBT wrappers reference clocks frequencies """
        reffreq = []
        for i in range(self.get_wrapper_count()):
            reffreq.append(self.roc_read(self.get_global_reg_address(i) + CRUADD['add_gbt_wrapper_refclk0_freq']))
            reffreq.append(self.roc_read(self.get_global_reg_address(i) + CRUADD['add_gbt_wrapper_refclk1_freq']))
            reffreq.append(self.roc_read(self.get_global_reg_address(i) + CRUADD['add_gbt_wrapper_refclk2_freq']))
            reffreq.append(self.roc_read(self.get_global_reg_address(i) + CRUADD['add_gbt_wrapper_refclk3_freq']))
            message = (f"Wrapper {i}: | ")
            for j in range(4):
                message = message + ("ref freq{} {:.2f} MHz  | ".format(j, (reffreq[j] / 1e6)).rjust(27))
            self.logger.info(message)

    def log_loopback_counters(self):
        loopback_counters = self.get_loopback_counters_and_check()
        for link, errors in loopback_counters.items():
            self.logger.info(f"Link {link}: {errors} errors")

    def get_loopback_counters_and_check(self):
        """ Returns all link counters and check for problems """
        counter_dict = {}
        for entry in self.links:
            i, wrapper, bank, link, _ = entry
            rxdata_error_cnt = self.get_rx_error_cnt(wrapper, bank, link)
            counter_dict[i] = rxdata_error_cnt

            data = self.roc_read(self.get_status_address(wrapper, bank, link))

            pll_lock = self.mid(data, 8, 1)
            rx_is_lockedtodata = self.mid(data, 10, 1)
            s_data_layer_up = self.mid(self.roc_read(self.get_status_address(wrapper, bank, link)), 11, 1)
            s_gbt_phy_up = self.mid(self.roc_read(self.get_status_address(wrapper, bank, link)), 13, 1)

            if pll_lock == 0:
                self.logger.warning(f"Link {i}: PLL is not locked!")
            if rx_is_lockedtodata == 0:
                self.logger.warning(f"Link {i}: RX is not locked ot data!")
            if s_data_layer_up == 0:
                self.logger.warning(f"Link {i}: is down!")
            if s_gbt_phy_up == 0:
                self.logger.warning(f"Link {i}: GBT PHY is down!")

        return counter_dict

    def stat(self, infinite_loop=False, stat="all", loop_limit=1):
        """ Print the number of test pattern reception and/or FEC errors for each link """
        t0 = int(time.time())

        if infinite_loop:
            limit = -1
        else:
            limit = loop_limit+1

        j = 0
        try:
            while j != limit:
                column = 0
                txt = ""
                for entry in self.links:
                    index, wrapper, bank, link, _ = entry
                    data = self.roc_read(self.get_status_address(wrapper, bank, link))
                    pll_lock = self.mid(data, 8, 1)
                    rx_is_lockedtodata = self.mid(data, 10, 1)
                    rxdata_error_cnt_o = self.get_rx_error_cnt(wrapper, bank, link)
                    s_data_layer_up = self.mid(self.roc_read(self.get_status_address(wrapper, bank, link)), 11, 1)
                    s_gbt_phy_up = self.mid(self.roc_read(self.get_status_address(wrapper, bank, link)), 13, 1)

                    if stat in ["fec", "all"]:
                        fec_val = self.get_fec_cnt(wrapper, bank, link)

                    if j == 0:  # title
                        if column == 0:
                            txt += "% 16s" % ("seconds")
                        if stat == "fec":
                            txt += "% 16s" % ("fec:" + str(index))
                        elif stat == "all":
                            txt += ("% 25s" % ("RX EC/FEC #" + str(index) + "   ")).rjust(25)
                        elif stat == "cnt":
                            txt += ("% 16s" % ("error:" + str(index))).rjust(16)
                    else:
                        tmptxt = ""
                        if column == 0:
                            tmptxt += "% 16d" % (int(time.time()) - t0)
                        if stat != "fec":
                            if pll_lock == 0:
                                tmptxt += "% 16s" % ("pll_lock")
                            elif s_data_layer_up == 0:
                                tmptxt += "% 16s" % ("s_datadown")
                            elif s_gbt_phy_up == 0:
                                tmptxt += "% 16s" % ("s_GbtPhyDown")
                            elif rx_is_lockedtodata == 0:
                                tmptxt += "% 16s" % ("lockedtodata")
                            else:
                                tmptxt += "% 16d" % (rxdata_error_cnt_o)

                        if stat == "all":
                            txt += (tmptxt + "/" + ("%5d" % (fec_val)).rjust(5)).rjust(25)
                        elif stat == "fec":
                            txt += (tmptxt +"%16d" % (fec_val))
                        elif stat == "cnt":
                            txt += tmptxt
                    column += 1
                print(txt)
                time.sleep(1.0)
                j = j + 1

        except KeyboardInterrupt:
            return

    # ------------------------------------------------------------------------------

    def internal_data_generator(self, value):
        """ Select the GBT tx source inside the link. Can be upstream (0) or internal pattern generator (1). """
        for entry in self.links:
            _, wrapper, bank, link, _ = entry
            self.roc_rmw(self.get_source_select_address(wrapper, bank, link), 1, 1, value)
            self.roc_rmw(self.get_source_select_address(wrapper, bank, link), 2, 1, value)

    def reset_all_links(self):
        """ Reset all GBT links (pulsing) """
        for entry in self.links:
            _, wrapper, bank, link, _ = entry
            self.roc_rmw(self.get_source_select_address(wrapper, bank, link), 0, 1, 1)  # activate reset
            self.roc_rmw(self.get_source_select_address(wrapper, bank, link), 0, 1, 0)  # release

    # ------------------------------------------------------------------------------

    def txcountertype(self, mode):
        """ Select the test counter type 30bit/8bit. the 8bit type is for MID """
        assert mode in ["30bi", "8bit"], f"invalid tx counter type : {mode} (only 30bit and 8 bit allowed)"
        for wrapper in range(self.num_of_wrappers):
            if mode == "30bit":
                self.roc_rmw(self.get_base_address(wrapper) + \
                             CRUADD['add_gbt_wrapper_gregs'] + \
                             CRUADD['add_gbt_wrapper_test_control'], 7, 1, 0x0)
            elif mode == "8bit":
                self.roc_rmw(self.get_base_address(wrapper) + \
                             CRUADD['add_gbt_wrapper_gregs'] + \
                             CRUADD['add_gbt_wrapper_test_control'], 7, 1, 0x1)

    # ------------------------------------------------------------------------------

    def rxpatternmask(self, himask, medmask, lomask):
        """ Define the checking mask on the rx side when in test pattern mode. This works only when the counter is in 8 bit mode. """
        for entry in self.links:
            _, wrapper, bank, link, _ = entry
            current_add = self.get_base_address(wrapper) + \
                          CRUADD['add_gbt_wrapper_bank_offset'] * (bank + 1) + \
                          CRUADD['add_gbt_bank_link_offset'] * (link + 1) + \
                          CRUADD['add_gbt_link_regs_offset'] + \
                          CRUADD['add_gbt_link_mask_hi']
        self.roc_write(current_add, himask)

        current_add = self.get_base_address(wrapper) + \
                      CRUADD['add_gbt_wrapper_bank_offset'] * (bank + 1) + \
                      CRUADD['add_gbt_bank_link_offset'] * (link + 1) + \
                      CRUADD['add_gbt_link_regs_offset'] + \
                      CRUADD['add_gbt_link_mask_med']
        self.roc_write(current_add, medmask)

        current_add = self.get_base_address(wrapper) + \
                      CRUADD['add_gbt_wrapper_bank_offset'] * (bank + 1) + \
                      CRUADD['add_gbt_bank_link_offset'] * (link + 1) + \
                      CRUADD['add_gbt_link_regs_offset'] + \
                      CRUADD['add_gbt_link_mask_lo']
        self.roc_write(current_add, lomask)

    # ------------------------------------------------------------------------------

    def patternmode(self, mode):
        """ GBT test pattern mode, either static or counter """
        assert mode in ["counter", "static"], f"invalid pattern mode: {mode} (only counter and static allowed)"
        for entry in self.links:
            _, wrapper, bank, link, _ = entry
            if mode == "counter":
                self.roc_rmw(self.get_source_select_address(wrapper, bank, link), 5, 1, 0x0)
            elif mode == "static":
                self.roc_rmw(self.get_source_select_address(wrapper, bank, link), 5, 1, 0x1)

    # ------------------------------------------------------------------------------

    def loopback(self, value):
        """ Sets the same internal loopback mode for all the links """

        all_links = self.get_filtered_link_list("all")
        for entry in all_links:
            _, wrapper, bank, link, _ = entry
            self.roc_rmw(self.get_source_select_address(wrapper, bank, link), 4, 1, value)

    def get_loopback(self):
        """ Reports whether internal loopback is used or not """
        loopbacks = []
        for entry in self.links:
            _, wrapper, bank, link, _ = entry
            loopbacks.append(["NO", "YES"][self.roc_read(self.get_source_select_address(wrapper, bank, link)) >> 4 & 0x1])

        return loopbacks

    def use_ddg_shortcut(self, value=True):
        """ Enables the DDG shortcut (the data to TX are used as GBT rx for the rest of the design """
        for entry in self.links:
            _, wrapper, bank, link, _ = entry
            self.roc_rmw(self.get_rx_ctrl_address(wrapper, bank, link), 16, 1, (0, 1)[value is True])

    # ------------------------------------------------------------------------------

    def txmode(self, mode):
        """ Select the GBT transmit mode (when in dynamic select mode). Can be gbt or wb (wide bus). """
        assert mode in ["gbt", "wb"], f"invalid tx mode: {mode} (only gbt and wb are allowed)"
        if not self.is_gbt_wrapper():
            raise ValueError("Not a GBT wrapper")

        for entry in self.links:
            index, wrapper, bank, link, base_address = entry
            if mode == "gbt":
                if self.get_gbt_wrapper_type() != 'dynamic':
                    raise ValueError("GBT wrapper is wide only")
                self.roc_rmw(self.get_tx_ctrl_address(wrapper, bank, link), 8, 1, 0)

            elif mode == "wb":
                self.roc_rmw(self.get_tx_ctrl_address(wrapper, bank, link), 8, 1, 1)

    def rxmode(self, mode):
        """ Select the GBT receive mode (when in dynamic select mode). Can be gbt or wb (wide bus). """
        assert mode in ["gbt", "wb"], f"invalid tx mode: {mode} (only gbt and wb are allowed)"
        if not self.is_gbt_wrapper():
            raise ValueError("Not a GBT wrapper")
        for entry in self.links:
            index, wrapper, bank, link, base_address = entry
            if mode == "gbt":
                if self.get_gbt_wrapper_type() != 'dynamic':
                    raise ValueError("GBT wrapper is wide only")
                self.roc_rmw(self.get_rx_ctrl_address(wrapper, bank, link), 8, 1, 0)
            elif mode == "wb":
                self.roc_rmw(self.get_rx_ctrl_address(wrapper, bank, link), 8, 1, 1)

    def get_gbt_mode(self):
        """ Gets configured GBT mode for each link """
        modes = []
        if not self.is_gbt_wrapper():
            for entry in self.links:
                index, wrapper, bank, link, _ = entry
                modes.append((str(index), "--", "--"))
            return modes

        if self.get_gbt_wrapper_type() != 'dynamic':
            for entry in self.links:
                index, wrapper, bank, link, _ = entry
                modes.append((str(index), "WB", "WB"))
        else:
            for entry in self.links:
                index, wrapper, bank, link, _ = entry

                rxctrl = self.roc_read(self.get_rx_ctrl_address(wrapper, bank, link))
                if ((rxctrl >> 8) & 0x1) == 1:
                    rxmode = "WB"
                else:
                    rxmode = "GBT"

                txctrl = self.roc_read(self.get_tx_ctrl_address(wrapper, bank, link))
                if ((txctrl >> 8) & 0x1) == 1:
                    txmode = "WB"
                else:
                    txmode = "GBT"

                modes.append((str(index), txmode, rxmode))

        return modes

    def init(self):
        # enable GBT-FPGA TX VALID to be generated in GBT-FPGA TX clock domain

        for entry in self.links:
            _, wrapper, bank, link, _ = entry
            self.roc_write(self.get_source_select_address(wrapper, bank, link), 0x00000042)  # clear error counters
            self.roc_write(self.get_source_select_address(wrapper, bank, link), 0x00000006)
            self.roc_write(self.get_tx_ctrl_address(wrapper, bank, link), 0x0)
            self.roc_write(self.get_rx_ctrl_address(wrapper, bank, link), 0x0)

        for entry in self.links:
            _, wrapper, bank, link, _ = entry
            self.roc_rmw(self.get_xcvr_reg_address(wrapper, bank, link, 0x007), 2, 1, 0)
            self.roc_rmw(self.get_xcvr_reg_address(wrapper, bank, link, 0x00A), 4, 1, 0)

    def lbtest(self, lb):
        self.init()
        self.internal_data_generator(1)
        self.patternmode("counter")
        self.loopback(lb)
        self.txmode("gbt")
        self.rxmode("gbt")
        self.cntrst()
        self.stat("cnt")
        print("GBT -> WB mode:")
        self.rxmode("wb")
        self.cntrst()
        self.stat("cnt")
        print("WB -> WB mode:")
        self.txmode("wb")
        self.cntrst()
        self.stat("stat")

    def rst_error(self):
        """ Reset the GBT synchro error indicator """
        for entry in self.links:
            _, wrapper, bank, link, _ = entry
            current_add = self.get_base_address(wrapper) \
                          + CRUADD['add_gbt_wrapper_bank_offset'] * (bank + 1) \
                          + CRUADD['add_gbt_bank_link_offset'] * (link + 1) \
                          + CRUADD['add_gbt_link_regs_offset'] \
                          + CRUADD['add_gbt_link_clr_errcnt']
            self.roc_write(current_add, 0)

    def downlinkcal(self, gbt_mode, data_generator=False):
        """ Set up GBT downlink """

        if data_generator:
            self.internal_data_generator(1)
        else:
            self.internal_data_generator(0)  # forward data, change to gbt.internal_data_generator(1) to use the gbt data generator instead

        self.txmode(gbt_mode)
        self.rxmode(gbt_mode)

    # ----------------  JS end of imported -----------------

    def enable_internal_data_generator(self):
        """Enables the GBT data generator"""
        self.internal_data_generator(1)

    def disable_internal_data_generator(self):
        """Disables the GBT data generator"""
        self.internal_data_generator(0)

    def set_links(self, links):
        """Sets the internal links parameter"""
        assert isinstance(links, (list, tuple, set))
        channel_range = ",".join(list(map(str, set(links))))
        self.links = self.get_filtered_link_list(ch_range=channel_range)
        assert sorted(links) == sorted(self.get_link_indices()), "Expecting {} getting {}".format(links, self.get_link_indices())
