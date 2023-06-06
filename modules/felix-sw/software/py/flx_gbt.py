"""MVTX implementation of the GBT.
The file is meant to provide user usable functions for the FLX defined class
"""

import logging

from flx_roc import Roc
from flx_table import FLXADD


class FlxGbt(Roc):
    """MVTX-defined wrapper for GBT"""

    def __init__(self, flx_opened_roc, ch_range):
        """Init method for GBT"""

        Roc.__init__(self)
        self.set_roc(flx_opened_roc)

        self._max_links_per_endpoint = self.roc_read(FLXADD['add_num_channels'])
        self._max_links = self._max_links_per_endpoint * 2
        self._aligned_channels = self.roc_read(FLXADD['add_gbt_align_done'])
        #assert self._aligned_channels > 0, "Non-align GBT link was found, is the RU powered on or connected?"

        #self.num_of_wrappers = self.get_wrapper_count()
        #self.link_ids = []
        self.links = self.get_filtered_link_list(ch_range)

        self.name = "GBT"
        self.logger = logging.getLogger(f"{self.name}")

    def initialize(self):
        """Initializes the module for the MVTX operation"""
        self.disable_rx_data_emu()
        self.disable_tx_data_emu()

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
                raise ValueError(f"Link index out of range, max link index is {len(all_links) - 1}")
            links.append([int(i),] + all_links[int(i)])
        return links

    def get_link_list(self):
        """ Construct the list of aligned links"""
        links = []
        for link in range(self._max_links):
            links.append([link])
        return links

    def get_link_indices(self):
        """ Get logical indices of the links """
        return [link[0] for link in self.links]

    def _set_gbt_data_emu(self, is_tx=True, enable=True):
        """Enable/disable data emulation for RX or TX links"""
        add   = FLXADD['add_gbt_tx_data_emu'] if is_tx else FLXADD['add_gbt_rx_data_emu']
        value = 0xFFFFFFFFFFFF if enable else (0x0)
        self.roc_write(add,value)

    def enable_rx_data_emu(self):
        """Enable data emulation"""
        self._set_gbt_data_emu(is_tx=False, enable=True)

    def enable_tx_data_emu(self):
        """Enable data emulation"""
        self._set_gbt_data_emu(is_tx=True, enable=True)

    def disable_rx_data_emu(self):
        """Enable data emulation"""
        self._set_gbt_data_emu(is_tx=False, enable=False)

    def disable_tx_data_emu(self):
        """Enable data emulation"""
        self._set_gbt_data_emu(is_tx=True, enable=False)

    def set_links(self, links):
        """Sets the internal links parameter"""
        assert isinstance(links, (list, tuple, set))
        channel_range = ",".join(list(map(str, set(links))))
        self.links = self.get_filtered_link_list(ch_range=channel_range)
        assert sorted(links) == sorted(self.get_link_indices()), "Expecting {} getting {}".format(links, self.get_link_indices())
