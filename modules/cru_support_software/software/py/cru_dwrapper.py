"""WP10 implementation of the DWRAPPER.
The file is meant to provide user usable functions for the CRU defined class
"""

from collections import OrderedDict

import logging

from roc import Roc
from cru_table import CRUADD


class CruDwrapper(Roc):
    """
    WP10-defined wrapper for DWRAPPER
    several functions imported from equivalent class in cru-sw subtree
    """

    def __init__(self, pcie_opened_roc, wrapper_count):
        """Init method for DWRAPPER"""
        Roc.__init__(self)
        self.set_roc(pcie_opened_roc)
        if wrapper_count == 1:
            self.wrapper_add_list = [CRUADD['add_base_datapathwrapper0']]
        else:
            self.wrapper_add_list = [CRUADD['add_base_datapathwrapper0'], CRUADD['add_base_datapathwrapper1']]

        self.name = "DWRAPPER"
        self.logger = logging.getLogger(f"{self.name}")
        self.data_link_list = None
        self._dwrappers_number = 2
        self._max_links_per_dwrapper = 12
        self._max_links_per_cru = 24
        self.enable_reg = None

    def initialize(self, data_link_list=None):
        """Initializes the module for the ITS operation"""
        if data_link_list is not None:
            self.set_data_link_list(data_link_list)

    # --------- JS imported from cru-sw -------------------------
    def link_enable_mask(self, wrapper, mask):
        """ Enable individual input link (0 to 15), HBAM 13, HDM 14, user logic 15.

            Enabling User logic, deactivate the individual channels from readout.

        """
        self.enable_reg = mask

        self.roc_write(self.wrapper_add_list[wrapper] + CRUADD['add_dwrapper_gregs'] + CRUADD['add_dwrapper_enreg'], self.enable_reg)

    def link_enable_bit(self, wrapper, link):
        """ Enable individual input link (0 to 15), HBAM 13, HDM 14, user logic 15

            Enabling User logic, deactivate the individual channels from readout.

        """
        add = self.wrapper_add_list[wrapper] + CRUADD['add_dwrapper_gregs'] + CRUADD['add_dwrapper_enreg']
        self.roc_rmw(add, link, 1, 1)
        self.enable_reg = self.roc_read(add)

    def get_enabled_links(self, num_all_links):
        """ Get which datapath links are enabled """

        enabled_links = []
        for w in self.wrapper_add_list:
            add = w + CRUADD['add_dwrapper_gregs'] + CRUADD['add_dwrapper_enreg']
            config = self.roc_read(add)
            enabled_links += ["Enabled" if ((config >> i) & 0x1) == 1 else "Disabled" for i in range(0, num_all_links // len(self.wrapper_add_list))]

        # if 2 dwrapper, odd number of links
        if len(self.wrapper_add_list) == 2 and num_all_links % 2 == 1:
            add = self.wrapper_add_list[1] + CRUADD['add_dwrapper_gregs'] + CRUADD['add_dwrapper_enreg']
            config = self.roc_read(add)
            enabled_links += ["Enabled" if ((config >> (num_all_links // 2)) & 0x1) == 1 else "Disabled"]

        return enabled_links

    def use_dynamic_offset(self, wrapper, en):
        """ Enable dynamic offset setting of the RDH (instead of fixed 0x2000)
        """
        add = self.wrapper_add_list[wrapper] + CRUADD['add_dwrapper_gregs'] + CRUADD['add_dwrapper_enreg']
        if en:
            self.roc_rmw(add, 31, 1, 1)
        else:
            self.roc_rmw(add, 31, 1, 0)
        self.enable_reg = self.roc_read(add)

    def get_big_fifo_lvl(self):
        """ Reads big FIFO level """
        retdat = []
        for w in self.wrapper_add_list:
            retdat.append(self.roc_read(w + CRUADD['add_dwrapper_gregs'] + CRUADD['add_dwrapper_bigfifo_lvl']))
        return retdat

    def get_statistics(self):
        """ Reads Statistics counters"""
        stats = []
        stats.append([])
        for w in self.wrapper_add_list:
            stats[0].append(self.roc_read(w + CRUADD['add_dwrapper_gregs'] + CRUADD['add_dwrapper_tot_words']))

        stats.append([])
        for w in self.wrapper_add_list:
            stats[1].append(self.roc_read(w + CRUADD['add_dwrapper_gregs'] + CRUADD['add_dwrapper_drop_words']))

        stats.append([])
        for w in self.wrapper_add_list:
            stats[2].append(self.roc_read(w + CRUADD['add_dwrapper_gregs'] + CRUADD['add_dwrapper_tot_pkts']))

        stats.append([])
        for w in self.wrapper_add_list:
            stats[3].append(self.roc_read(w + CRUADD['add_dwrapper_gregs'] + CRUADD['add_dwrapper_drop_pkts']))

        return stats

    def get_last_hb(self):
        """ Reads last HB received """
        retdat = []
        for w in self.wrapper_add_list:
            retdat.append(self.roc_read(w + CRUADD['add_dwrapper_gregs'] + CRUADD['add_dwrapper_lastHBID']))

        return retdat

    def set_gbt_datapath_link(self, wrap=0, link=0, is_gbt_pkt=0, RAWMAXLEN=0x1FC):
        """ Configures GBT datapath links"""
        assert RAWMAXLEN <= 0x1FC, "Payload length should be less or equal to 0x1FC"
        val = 0
        val |= RAWMAXLEN
        val |= (is_gbt_pkt << 31)

        add = self.wrapper_add_list[wrap] + CRUADD['add_datapathlink_offset'] + CRUADD['add_datalink_offset'] * link + \
              CRUADD['add_datalink_ctrl']
        self.roc_write(add, val)

    def get_gbt_datapath_link(self, wrap, link):
        """ Gets GBT datapath link configurations """
        add = self.wrapper_add_list[wrap] + CRUADD['add_datapathlink_offset'] + CRUADD['add_datalink_offset'] * link + \
              CRUADD['add_datalink_ctrl']
        val = self.roc_read(add) >> 31
        if val == 1:
            return "packet"
        return "continuous"

    def get_gbt_datapath_link_counters(self, wrap, link):
        """ Gets GBT datapath link counters """

        add = self.wrapper_add_list[wrap] + CRUADD['add_datapathlink_offset'] + CRUADD['add_datalink_offset'] * link + \
              CRUADD['add_datalink_rej_pkt']
        rej_pkt = self.roc_read(add)

        add = self.wrapper_add_list[wrap] + CRUADD['add_datapathlink_offset'] + CRUADD['add_datalink_offset'] * link + \
              CRUADD['add_datalink_acc_pkt']
        acc_pkt = self.roc_read(add)

        add = self.wrapper_add_list[wrap] + CRUADD['add_datapathlink_offset'] + CRUADD['add_datalink_offset'] * link + \
              CRUADD['add_datalink_forced_pkt']
        forced_pkt = self.roc_read(add)

        self.logger.info(f"rejected packet ={rej_pkt}, accepted packets={acc_pkt} and forced packets ={forced_pkt}")

    def set_flow_control(self, wrap=0, allow_reject=0):
        """ Configures the flow control """
        val = 0
        val |= (allow_reject << 0)

        add = self.wrapper_add_list[wrap] + CRUADD['add_flowctrl_offset'] + CRUADD['add_flowctrl_ctrlreg']
        self.roc_write(add, val)

    def set_trig_window_size(self, wrap=0, size=4000):
        """ Configures the trigger window size in GBT words """
        assert size < 4096, "Trig size should be less or equal to 4095"
        add = self.wrapper_add_list[wrap] + CRUADD['add_dwrapper_gregs'] + CRUADD['add_dwrapper_trigsize']
        self.roc_write(add, size)

    def get_flow_control_status(self, wrap=0):
        """ Returns the number of packet rejected/total in flow control """
        pkt_rej = self.roc_read(self.wrapper_add_list[wrap] + CRUADD['add_flowctrl_offset'] + CRUADD['add_flowctrl_pkt_rej'])
        pkt_tot = self.roc_read(self.wrapper_add_list[wrap] + CRUADD['add_flowctrl_offset'] + CRUADD['add_flowctrl_pkt_tot'])
        return pkt_tot, pkt_rej

    def datagenerator_resetpulse(self):
        """ Resets data generator """
        for w in self.wrapper_add_list:
            add = w + CRUADD['add_dwrapper_gregs'] + CRUADD['add_dwrapper_datagenctrl']
            self.roc_rmw(add, 0, 1, 1)  # bit 0 at 1
            self.roc_rmw(add, 0, 1, 0)  # bit 0 at 0

    def datagenerator_enable(self, en=True):
        """ Enable data generation (datagenerator) """
        for w in self.wrapper_add_list:
            add = w + CRUADD['add_dwrapper_gregs'] + CRUADD['add_dwrapper_datagenctrl']
            if en:
                self.roc_rmw(add, 1, 1, 1)  # bit 1 at 1
            else:
                self.roc_rmw(add, 1, 1, 0)  # bit 1 at 1

    def datagenerator_inj_err(self):
        """ Request data generator to inject a fault """
        for w in self.wrapper_add_list:
            add = w + CRUADD['add_dwrapper_gregs'] + CRUADD['add_dwrapper_datagenctrl']
            self.roc_rmw(add, 2, 1, 1)  # bit 2 at 1
            self.roc_rmw(add, 2, 1, 0)  # bit 2 at 0

    def datagenerator_rand_wr(self, en=True):
        """ Set random wr to wr duration in data generator """
        for w in self.wrapper_add_list:
            add = w + CRUADD['add_dwrapper_gregs'] + CRUADD['add_dwrapper_datagenctrl']
            if en:
                self.roc_rmw(add, 8, 1, 1)  # bit 8 at 1
            else:
                self.roc_rmw(add, 8, 1, 0)  # bit 8 at 0

    def datagenerator_fixed_wr_period(self, val=0xF):
        """ Set wr to wr duration in data generator
            valid values are 0 to 15
        """
        assert 0 <= val < 16, f"BAD write period value {val} for datagenerator, must be >=0 and < 0xF"

        for w in self.wrapper_add_list:
            add = w + CRUADD['add_dwrapper_gregs'] + CRUADD['add_dwrapper_datagenctrl']
            self.roc_rmw(add, 4, 4, val)

    def use_datagenerator_source(self, en=True):
        """ Selects datagenerator as bigfifo input source """
        for w in self.wrapper_add_list:
            add = w + CRUADD['add_dwrapper_gregs'] + CRUADD['add_dwrapper_datagenctrl']
            if en:
                self.roc_rmw(add, 31, 1, 1)  # bit 31 at 1
            else:
                self.roc_rmw(add, 31, 1, 0)  # bit 31 at 0

    # --------- JS end of import --------------------------------

    def set_data_link_list(self, data_link_list):
        """Configures the list of data links to activate the readout"""
        assert isinstance(data_link_list, list)
        for link in data_link_list:
            assert link in range(self._max_links_per_cru)
        self.data_link_list = data_link_list

    def configure_for_readout(self, data_link_list, enable_dynamic_offset=True):
        """Configures the two data wrappers for data taking"""
        if self.data_link_list is None:
            assert data_link_list is not None
        else:
            if data_link_list is not None and data_link_list != self.data_link_list:
                self.logger.warning("Ignoring value passed as parameter \'data_link_list\' {}, using the internal value instead {}".format(data_link_list, self.data_link_list))
            data_link_list = self.data_link_list

        data_link_list_dwrapper = self._split_list(data_link_list)
        for dwrapper in range(self._dwrappers_number):
            self._configure_links(dwrapper=dwrapper,
                                  data_link_list_dwrapper=data_link_list_dwrapper[dwrapper])
        # both dwrappers should be configured the same way:
        self.use_dynamic_offset(wrapper=0, en=enable_dynamic_offset)
        self.use_dynamic_offset(wrapper=1, en=enable_dynamic_offset)

    def _split_list(self, data_link_list):
        """Splits the data_link_list into the two dwrappers"""
        data_link_list_dwrapper = {}
        data_link_list_dwrapper[0] = [link for link in data_link_list if link < self._max_links_per_dwrapper]
        data_link_list_dwrapper[1] = [link for link in data_link_list if link >= self._max_links_per_dwrapper]
        return data_link_list_dwrapper

    def _configure_links(self, dwrapper, data_link_list_dwrapper):
        """Configures the links for the given dwrapper"""
        self.link_enable_mask(wrapper=dwrapper, mask=0)
        for link in data_link_list_dwrapper:
            if dwrapper == 1:
                link = link - self._max_links_per_dwrapper
            self.link_enable_bit(wrapper=dwrapper, link=link)
            self.set_gbt_datapath_link(wrap=dwrapper,
                                       link=link,
                                       is_gbt_pkt=1,
                                       RAWMAXLEN=0x1EA)
        self.set_flow_control(wrap=dwrapper, allow_reject=0)

    def get_dropped_packets(self):
        """Returns the total number of dropped packets in the CRU"""
        dropped_packets = 0
        for base_address in self.wrapper_add_list:  # Base address for the two wrappers
            address = base_address + CRUADD['add_dwrapper_drop_pkts']
            dropped_packets += self.roc_read(address)
        return dropped_packets

    def get_total_packets(self):
        """Returns the total number of total packets in the CRU"""
        total_packets = 0
        for base_address in self.wrapper_add_list:  # Base address for the two wrappers
            address = base_address + CRUADD['add_dwrapper_tot_pkts']
            total_packets += self.roc_read(address)
        return total_packets

    def get_last_hb_id(self):
        """Returns the last HB id for each dwrapper returned as a list"""
        last_hb_id = []
        for base_address in self.wrapper_add_list:  # Base address for the two wrappers
            address = base_address + CRUADD['add_dwrapper_lasthbid']
            last_hb_id.append(self.roc_read(address))
        return max(last_hb_id)

    def get_dwrapper_per_link(self, link):
        """Returns the dwrapper for a given link"""
        assert link in range(self._max_links_per_cru)
        if link < self._max_links_per_dwrapper:
            dwrapper = 0
        else:
            dwrapper = 1
        return dwrapper

    def get_rejected_packets(self, link):
        """Returns the rejected packets for the given link"""
        if self.data_link_list is None:
            assert link in range(self._max_links_per_cru)
        else:
            assert link in self.data_link_list
        dwrapper = self.get_dwrapper_per_link(link)
        base_address = self.wrapper_add_list[dwrapper]
        if dwrapper == 1:
            link = link - self._max_links_per_dwrapper
        add = base_address + CRUADD['add_datapathlink_offset'] + CRUADD['add_datalink_offset'] * link + CRUADD['add_datalink_rej_pkt']
        return self.roc_read(add)

    def get_accepted_packets(self, link):
        """Returns the accepted packets for the given link"""
        if self.data_link_list is None:
            assert link in range(self._max_links_per_cru)
        else:
            assert link in self.data_link_list
        dwrapper = self.get_dwrapper_per_link(link)
        base_address = self.wrapper_add_list[dwrapper]
        if dwrapper == 1:
            link = link - self._max_links_per_dwrapper
        add = base_address + CRUADD['add_datapathlink_offset'] + CRUADD['add_datalink_offset'] * link + CRUADD['add_datalink_acc_pkt']
        return self.roc_read(add)

    def get_forced_packets(self, link):
        """Returns the number packets which were forced (closed for missing EOP) for the given link"""
        if self.data_link_list is None:
            assert link in range(self._max_links_per_cru)
        else:
            assert link in self.data_link_list
        dwrapper = self.get_dwrapper_per_link(link)
        base_address = self.wrapper_add_list[dwrapper]
        if dwrapper == 1:
            link = link - self._max_links_per_dwrapper
        add = base_address + CRUADD['add_datapathlink_offset'] + CRUADD['add_datalink_offset'] * link + CRUADD['add_datalink_forced_pkt']
        return self.roc_read(add)

    def get_link_counters(self, link):
        """Returns a dictionary of counters for the given link"""
        ret = OrderedDict()
        ret['accepted_packets'] = self.get_accepted_packets(link=link)
        ret['rejected_packets'] = self.get_rejected_packets(link=link)
        ret['forced_packets']   = self.get_forced_packets(link=link)
        return ret

    def get_datapath_counters(self):
        """Returns the counters for all the links in self.data_link_list for the given wrapper"""
        ret = OrderedDict()
        for link in self.data_link_list:
            ret[link] = self.get_link_counters(link=link)
        return ret

    def is_dynamic_offset_enabled(self, dwrapper):
        """Return if dynamic offset is enabled"""
        add = self.wrapper_add_list[dwrapper] + CRUADD['add_dwrapper_gregs'] + CRUADD['add_dwrapper_enreg']
        val = self.roc_read(add)
        return val & 0x80000000 == 0x80000000
