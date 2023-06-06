"""Transceiver module for Xilinx GTX Transceiver functions"""
from enum import IntEnum, unique

import time
import collections
import traceback

from wishbone_module import WishboneModule

from ru_gthe3_channel_drp_mapping import Gthe3ChannelAddressAliases as gth_ch_add_a
from ru_gthe3_channel_drp_mapping import Gthe3ChannelAddress        as gth_ch_add
from ru_gthe3_channel_drp_mapping import Gthe3ChannelLow            as gth_ch_low
from ru_gthe3_channel_drp_mapping import Gthe3ChannelWidth          as gth_ch_width

from ru_gthe3_common_drp_mapping import Gthe3CommonAddressAliases as gth_cm_add_a
from ru_gthe3_common_drp_mapping import Gthe3CommonAddress        as gth_cm_add
from ru_gthe3_common_drp_mapping import Gthe3CommonLow            as gth_cm_low
from ru_gthe3_common_drp_mapping import Gthe3CommonWidth          as gth_cm_width


@unique
class GthFrontendAddress(IntEnum):
    ENABLE_ALIGNMENT   = 0
    ALIGNMENT_STATUS   = 1
    ENABLE_DATA        = 2
    GTH_RESET          = 5
    GTH_STATUS         = 6
    ENABLE_PRBS_CHECK  = 7
    PRBS_COUNTER_RESET = 8
    GTH_RX_RST_DONE_CNTR  = 9

class GTHReset(IntEnum):
    """GTH Reset selection bits"""
    ALL                 = 15
    RX_PLL_AND_DATAPATH = 14
    RX_DATAPATH         = 13

class GthFrontend(WishboneModule):
    """Software module for communicating with the alpide_frontend_ib_wishbone module."""
    NR_TRANSCEIVERS = 9

    def __init__(self,moduleid, board_obj, drp_bridge_module, transceivers=None):
        super(GthFrontend, self).__init__(moduleid=moduleid,board_obj=board_obj,name="GthFrontend")
        self._drp_bridge = drp_bridge_module
        self.transceivers = transceivers
        if self.transceivers is None:
            self.transceivers = list(range(self.NR_TRANSCEIVERS))

    def read_config(self):
        regs = ['enable_alignment','alignment_status','enable_data','gth_reset','gth_status']
        reg_idx = [0,1,2,5,6]
        for i in reg_idx:
            self.read(i,commitTransaction=False)
        results = self.read_all()

        result_dict = collections.OrderedDict()
        for reg,val in zip(regs,results):
            result_dict[reg]=val
        return result_dict

    def dump_config(self):
        """Dump the modules state and configuration as a string"""
        config_str = f"--- {self.name} module ---\n"
        self.board.comm.disable_rderr_exception()
        for address in GthFrontendAddress:
            name = address.name
            try:
                value = self.read(address.value)
                config_str += "    - {0} : {1:#06X}\n".format(name, value)
            except:
                config_str += "    - {0} : FAILED\n".format(name)
        # COMMON (not Implemented in bitfile yet)
        #drp = self.readback_common_drp()
        #config_str += f"--- DRP COMMON ---\n"
        #for address, value in drp.items():
        #    config_str += f"    - {address} : 0x{value:X}\n"
        drp = self.readback_all_channel_drp()
        for transceiver, drp_t in drp.items():
            config_str += f"--- DRP transceiver {transceiver} ---\n"
            for address, value in drp_t.items():
                config_str += f"    - {address} : 0x{value:X}\n"
        self.board.comm.enable_rderr_exception()
        return config_str

    def set_transceivers(self,transceivers):
        """Set array of transceivers to be addressed"""
        for transceiver in transceivers:
            assert transceiver < self.NR_TRANSCEIVERS, "Transceiver not in Range of Transceivers"
        self.transceivers=transceivers

    def get_transceivers(self):
        """Return board transceivers"""
        return self.transceivers

    def initialize(self, commitTransaction=True, check_reset_done=True, max_retries=10):
        """Initialise Transceiver: Reset GTH block, enable alignment"""
        self.enable_data(False,commitTransaction=commitTransaction)
        self.enable_alignment(False,commitTransaction=commitTransaction)
        self.reset_gth()
        if check_reset_done:
            if not commitTransaction:
                self.logger.warning("Check reset needs to read from board -> transaction will be flushed")
            self.firmware_wait(100,commitTransaction=False)
            reset_done = self.is_reset_done()
            retries = 0
            while not reset_done and retries < max_retries:
                self.firmware_wait(200,commitTransaction=True)
                time.sleep(1)
                reset_done = self.is_reset_done()
                retries += 1
            if not reset_done:
                self.logger.error("GTH: Reset not done!")
            else:
                self.logger.info("GTH: Reset done!")
        else:
            reset_done = True
            self.logger.warning("GTH: Reset done was NOT checked!")

        return reset_done

    def reset_gth(self, commitTransaction=True):
        """ Assert GTH Reset All """
        self.write(GthFrontendAddress.GTH_RESET, 1<<GTHReset.ALL, commitTransaction=False)
        self.firmware_wait(15, commitTransaction=False)
        self.write(GthFrontendAddress.GTH_RESET, 0, commitTransaction=commitTransaction)

    def reset_gth_rx_pll_and_datapath(self, commitTransaction=True):
        """ Assert GTH Reset RX PLL and Datapath """
        self.write(GthFrontendAddress.GTH_RESET, 1<<GTHReset.RX_PLL_AND_DATAPATH, commitTransaction=False)
        self.firmware_wait(15, commitTransaction=False)
        self.write(GthFrontendAddress.GTH_RESET, 0, commitTransaction=commitTransaction)

    def reset_gth_rx_datapath(self, commitTransaction=True):
        """ Assert GTH Reset RX PLL and Datapath """
        self.write(GthFrontendAddress.GTH_RESET, 1<<GTHReset.RX_DATAPATH, commitTransaction=False)
        self.firmware_wait(15, commitTransaction=False)
        self.write(GthFrontendAddress.GTH_RESET, 0, commitTransaction=commitTransaction)

    def reset_gth_ch(self, channel, commitTransaction=True):
        """ Assert GTH RXPMARESET for chosen channel """
        assert channel in range(9), f"Selected ch: {channel} not in {range(9)}"
        self.write(GthFrontendAddress.GTH_RESET, 1<<channel, commitTransaction=False)
        self.firmware_wait(15, commitTransaction=False)
        self.write(GthFrontendAddress.GTH_RESET, 0, commitTransaction=commitTransaction)


    def align_transceivers(self,check_aligned=True,max_retries=10):
        """Perform transceiver alignment procedure:
           * enable alignment
           * check that all transceivers are aligned
           * disable alignment
        """
        self.enable_alignment(True)
        if check_aligned:

            aligned = self.is_aligned()
            retries = 0
            while not all(aligned) and retries < max_retries:
                self.firmware_wait(100)
                aligned = self.is_aligned()
                retries += 1
            return all(aligned)
        else:
            return True

    def is_reset_done(self):
        """Return Reset status of GTH block"""
        status = self.read(GthFrontendAddress.GTH_STATUS)
        return status&(1<<15) > 0

    def is_cdr_locked(self):
        """Return cdr status for each transceiver as array"""
        status = self.read(GthFrontendAddress.GTH_STATUS)
        locked = [status&(1<<i)>0 for i in self.transceivers]
        return locked

    def is_aligned(self):
        """Return lock alignment status of each transceivers as array"""
        status = self.read(GthFrontendAddress.ALIGNMENT_STATUS)
        aligned = [status&(1<<i)>0 for i in self.transceivers]
        return aligned

    def get_gth_status(self):
        status = self.read(GthFrontendAddress.GTH_STATUS)
        value = {}
        value['reset_done'] = status&(1<<15)>0
        value['cdr_locked'] = status&0x1FF
        return value

    def get_gth_rx_reset_done_counter(self):
        return self.read(GthFrontendAddress.GTH_RX_RST_DONE_CNTR)

    def _get_transceiver_mask(self):
        """Return mask for addressed transceivers"""
        mask = 0
        for transceiver in self.transceivers:
            mask |= (1<<transceiver)
        return mask

    def _write_masked_reg(self,addr,flag,commitTransaction=True,readback=True):
        """Write to a register which needs to have a transceiver mask applied"""
        if(len(self.transceivers) < self.NR_TRANSCEIVERS) and readback:
            if not commitTransaction:
                self.logger.warning("Cannot have readback enabled with commitTransaction=False -> transaction will be committed")
                traceback.print_stack()
            reg = self.read(addr)
        else:
            reg = 0
        mask = self._get_transceiver_mask()

        if flag:
            reg |= mask
        else:
            reg &= ~mask
        self.write(addr,reg,commitTransaction=commitTransaction)

    def enable_alignment(self, enable=True,commitTransaction=True):
        """Enable alignment flag for Transceivers. Does not touch transceivers not in list"""
        self._write_masked_reg(GthFrontendAddress.ENABLE_ALIGNMENT,enable,commitTransaction)

    def enable_data(self,enable=True,commitTransaction=True):
        """Enable data flag for Transceivers. Does not touch transceivers not in list"""
        self._write_masked_reg(GthFrontendAddress.ENABLE_DATA,enable,commitTransaction)

    def reset_receivers(self,commitTransaction=True):
        """Reset Receivers paths for Transceivers"""
        self._write_masked_reg(GthFrontendAddress.GTH_RESET,True,commitTransaction,False)
        self.write(GthFrontendAddress.GTH_RESET,0,commitTransaction=commitTransaction)


    def enable_prbs(self, enable=True,commitTransaction=True):
        """Enable PRBS checker for Transceivers. Does not touch transceivers not in list"""
        self._write_masked_reg(GthFrontendAddress.ENABLE_PRBS_CHECK,enable,commitTransaction,True)

    def reset_prbs_counter(self,commitTransaction=True):
        """Reset internal Transceiver PRBS counter"""
        self._write_masked_reg(GthFrontendAddress.PRBS_COUNTER_RESET,flag=True,commitTransaction=False,readback=False)
        self.write(GthFrontendAddress.PRBS_COUNTER_RESET,0,commitTransaction)

    def read_prbs_counter(self,reset=False):
        """Read / log the total amount of Prbs errors since the last check"""
        for tr in self.transceivers:
            self.read_drp(0x15E,False,tr)
            self.read_drp(0x15F,False,tr)

        if reset:
            self.reset_prbs_counter(commitTransaction=False)

        results = self.read_all()
        prbs_errors = [results[i+1]<<15 | results[i] for i in range(0,len(results),2)]

        return prbs_errors

    def write_drp(self, address, data, commitTransaction=True,transceiver=None):
        """Write to the drp port. Set Transceiver via transceiver setting; defaults to self.transceivers[0]"""
        if transceiver is None:
            transceiver = self.transceivers[0]
        self._drp_bridge.write_drp(transceiver,address,data,commitTransaction)

    def read_drp(self, address, commitTransaction=True, transceiver=None):
        """Read from the drp port. Set Transceiver via transceiver setting; defaults to self.transceivers[0]"""
        if transceiver is None:
            transceiver = self.transceivers[0]
        return self._drp_bridge.read_drp(transceiver,address,commitTransaction)

    def _readback_drp_raw(self, transceiver):
        """Dumps the configuration in a dict {add:value}"""
        drp_readback = collections.OrderedDict()
        for addr in gth_ch_add_a: # each address is read only once
            self.read_drp(address=addr,commitTransaction=False,transceiver=transceiver)
        results = self.read_all()
        assert len(results) == len(gth_ch_add_a)
        result_idx = 0
        for addr in gth_ch_add_a:
            drp_readback[addr.value] = results[result_idx]
            result_idx+=1
        return drp_readback

    def readback_channel_drp(self, transceiver, test=False):
        drp_readback = collections.OrderedDict()
        if test:
            self.logger.warning("Data were not read from the GTH!")
            raw = collections.OrderedDict([(2, 0), (3, 6241), (4, 2078), (5, 6171), (6, 0), (9, 6168), (11, 0), (12, 1057), (14, 0), (15, 0), (16, 1825), (17, 0), (18, 0), (19, 17536), (20, 4096), (21, 0), (22, 0), (23, 608), (24, 61440), (25, 0), (26, 0), (27, 0), (28, 61444), (29, 6656), (30, 256), (31, 256), (32, 256), (33, 256), (34, 61696), (35, 256), (36, 61696), (37, 256), (38, 0), (39, 13311), (40, 394), (41, 488), (42, 33546), (43, 690), (44, 32900), (45, 24575), (46, 101), (47, 0), (48, 0), (49, 46), (50, 0), (51, 0), (52, 2), (53, 0), (54, 50), (55, 32768), (56, 2), (57, 4096), (58, 0), (60, 0), (61, 0), (62, 32768), (63, 0), (64, 0), (65, 0), (66, 0), (67, 0), (68, 0), (69, 0), (70, 0), (71, 0), (72, 0), (73, 0), (74, 0), (75, 0), (76, 0), (77, 0), (78, 15), (79, 15), (80, 0), (81, 57344), (82, 2), (83, 2560), (84, 0), (85, 9859), (86, 1404), (87, 80), (88, 32768), (89, 8224), (90, 0), (91, 31), (92, 48), (93, 0), (94, 0), (95, 2740), (96, 0), (97, 699), (98, 6528), (99, 32962), (100, 20600), (101, 62464), (102, 61560), (103, 32768), (104, 32996), (105, 4168), (106, 12296), (107, 8256), (108, 21518), (109, 48), (110, 8224), (111, 117), (112, 9), (113, 0), (114, 30659), (115, 2432), (116, 16912), (117, 0), (118, 960), (119, 6500), (120, 3584), (121, 0), (122, 12291), (123, 0), (124, 736), (125, 200), (126, 32908), (127, 40604), (128, 39060), (129, 37004), (130, 35462), (131, 33920), (132, 0), (133, 380), (137, 15), (138, 3), (139, 1537), (140, 2304), (141, 0), (142, 43520), (143, 51), (144, 3), (145, 63488), (146, 0), (147, 16384), (148, 0), (149, 61440), (151, 0), (152, 0), (153, 384), (154, 0), (155, 46336), (156, 2796), (157, 22376), (158, 32768), (159, 0), (160, 30832), (161, 0), (162, 0), (163, 0), (164, 2022), (165, 0), (166, 0), (167, 0), (168, 0), (169, 10), (170, 9380), (171, 10), (172, 0), (173, 6400), (174, 16384), (175, 0), (176, 0), (177, 8192), (178, 3), (179, 8192), (180, 16896), (181, 3), (182, 2048), (183, 8192), (184, 0), (185, 8192), (186, 60), (187, 2535), (188, 7), (189, 8448), (190, 26146), (191, 0), (192, 0), (193, 8192), (194, 0), (195, 4096), (196, 676), (197, 8192), (198, 32768), (199, 0), (200, 8192), (202, 0), (203, 26616), (204, 42156), (205, 3), (206, 0), (207, 8192), (336, 1792), (337, 0), (338, 0), (339, 0), (340, 0), (341, 0), (342, 0), (343, 0), (344, 0), (345, 0), (346, 0), (347, 0), (348, 0), (349, 0), (350, 0), (351, 0), (355, 0), (361, 0)])
        else:
            raw = self._readback_drp_raw(transceiver)

        for addr in gth_ch_add:
            drp_readback[addr] = (raw[addr.value]>>gth_ch_low[addr.name].value)&(2**gth_ch_width[addr.name].value-1)
        return drp_readback

    def _check_drp_channel_mapping(self):
        for addr in gth_ch_add:
            print(f"{addr.name:<30}: add {gth_ch_add[addr.name].value:>3} low {gth_ch_low[addr.name].value:>2} width {gth_ch_width[addr.name].value:>2}")

    def readback_all_channel_drp(self):
        """Read back all Valid DRP ports of all registered transceivers"""
        drp_readback = collections.OrderedDict()
        for transceiver in self.transceivers:
            drp_readback[transceiver] = self.readback_channel_drp(transceiver=transceiver)
        return drp_readback

    def readback_common_drp(self, transceiver, test=False):
        raise NotImplementedError("GTH Common not connected in GTH!")
        drp_readback = collections.OrderedDict()
        if test:
            self.logger.warning("Data were not read from the GTH!")
            raw = collections.OrderedDict()
        else:
            raw = self._readback_drp_raw(transceiver)

        for addr in gth_cm_add:
            drp_readback[addr] = (raw[addr.value]>>gth_cm_low[addr.name].value)&(2**gth_cm_width[addr.name].value-1)
        return drp_readback

    def _check_drp_common_mapping(self):
        for addr in gth_cm_add:
            print(f"{addr.name:<30}: add {gth_cm_add[addr.name].value:>3} low {gth_cm_low[addr.name].value:>2} width {gth_cm_width[addr.name].value:>2}")


@unique
class GpioFrontendAddress(IntEnum):
    ENABLE_ALIGNMENT_L   = 0
    ENABLE_ALIGNMENT_H   = 1
    ALIGNMENT_STATUS_L   = 2
    ALIGNMENT_STATUS_H   = 3
    ENABLE_REALIGN_L     = 4
    ENABLE_REALIGN_H     = 5
    ENABLE_DATA_L        = 6
    ENABLE_DATA_H        = 7
    IDELAY_VALUE         = 8
    IDELAY_LOAD_L        = 9
    IDELAY_LOAD_H        = 10
    ENABLE_PRBS_CHECK_L  = 11
    ENABLE_PRBS_CHECK_H  = 12
    INPUT_INVERTER_L     = 13
    INPUT_INVERTER_H     = 14
    PRBS_RESET_COUNTER_L = 15
    PRBS_RESET_COUNTER_H = 16
    PRBS_COUNTER_LANE_0  = 17
    PRBS_COUNTER_LANE_1  = 18
    PRBS_COUNTER_LANE_2  = 19
    PRBS_COUNTER_LANE_3  = 20
    PRBS_COUNTER_LANE_4  = 21
    PRBS_COUNTER_LANE_5  = 22
    PRBS_COUNTER_LANE_6  = 23
    PRBS_COUNTER_LANE_7  = 24
    PRBS_COUNTER_LANE_8  = 25
    PRBS_COUNTER_LANE_9  = 26
    PRBS_COUNTER_LANE_10 = 27
    PRBS_COUNTER_LANE_11 = 28
    PRBS_COUNTER_LANE_12 = 29
    PRBS_COUNTER_LANE_13 = 30
    PRBS_COUNTER_LANE_14 = 31
    PRBS_COUNTER_LANE_15 = 32
    PRBS_COUNTER_LANE_16 = 33
    PRBS_COUNTER_LANE_17 = 34
    PRBS_COUNTER_LANE_18 = 35
    PRBS_COUNTER_LANE_19 = 36
    PRBS_COUNTER_LANE_20 = 37
    PRBS_COUNTER_LANE_21 = 38
    PRBS_COUNTER_LANE_22 = 39
    PRBS_COUNTER_LANE_23 = 40
    PRBS_COUNTER_LANE_24 = 41
    PRBS_COUNTER_LANE_25 = 42
    PRBS_COUNTER_LANE_26 = 43
    PRBS_COUNTER_LANE_27 = 44


class GpioFrontend(WishboneModule):
    """Software module for communicating with the alpide_frontend_ob_wishbone module."""
    NR_TRANSCEIVERS = 28

    def __init__(self,moduleid,board_obj,transceivers=None):
        super().__init__(moduleid=moduleid,board_obj=board_obj,name="GPIOFrontend")
        self.transceivers = transceivers
        if self.transceivers is None:
            self.transceivers = list(range(self.NR_TRANSCEIVERS))

    def read_config(self):
        regs = ['enable_alignment1',
                'enable_alignment2',
                'alignment_status1',
                'alignment_status2',
                'enable_realignment1',
                'enable_realignment2',
                'enable_data1',
                'enable_data2',
                ]

        reg_idx = [0,1,2,3,4,5,6,7]

        for i in reg_idx:
            self.read(i,commitTransaction=False)
        results = self.read_all()

        result_dict = collections.OrderedDict()
        for reg,val in zip(regs,results):
            result_dict[reg]=val
        return result_dict

    def dump_config(self):
        """Dump the modules state and configuration as a string"""
        config_str = f"--- {self.name} module ---\n"
        self.board.comm.disable_rderr_exception()
        for address in GpioFrontendAddress:
            name = address.name
            try:
                value = self.read(address.value)
                config_str += "    - {0} : {1:#06X}\n".format(name, value)
            except:
                config_str += "    - {0} : FAILED\n".format(name)
        self.board.comm.enable_rderr_exception()
        return config_str

    def subset(self,transceivers):
        return GpioFrontend(self.moduleid,self.board,transceivers)

    def set_transceivers(self,transceivers):
        """Set array of transceivers to be addressed"""
        for transceiver in transceivers:
            assert transceiver < self.NR_TRANSCEIVERS, "Transceiver not in Range of Transceivers"
        self.transceivers=transceivers

    def get_transceivers(self):
        """Return board transceivers"""
        return self.transceivers

    def initialize(self,commitTransaction=True):
        """Initialise Transceiver: enable alignment"""
        self.enable_data(False,commitTransaction=commitTransaction)
        self.enable_alignment(False,commitTransaction=commitTransaction)
        return True

    def align_transceivers(self,check_aligned=True,max_retries=10):
        """Perform transceiver alignment procedure:
           * enable alignment
           * check that all transceivers are aligned
           * disable alignment
        """
        self.enable_alignment(True)
        self.enable_realign(True)
        if check_aligned:
            aligned = self.is_aligned()
            retries = 0
            while not all(aligned) and retries < max_retries:
                self.firmware_wait(100)
                aligned = self.is_aligned()
                retries += 1
            return all(aligned)
        else:
            return True

    def scan_idelays(self,stepsize=10,waittime=0.1,set_optimum=True,verbose=True):
        """Scan all Idelay values to find the best phase. Requires chips to be set up for PRBS400"""
        delays = list(range(0,512,stepsize))
        prbs_counters_all = collections.OrderedDict()

        for delay in delays:
            self.load_idelay(delay)
            self.reset_prbs_counter()
            time.sleep(waittime)
            prbs_counters = self.read_prbs_counter()
            prbs_counters_all[delay] = prbs_counters[:]
            if verbose:
                self.logger.info("Delay: {0:03d}: {1}".format(delay,",".join(["{0:5d}".format(c) for c in prbs_counters])))

        # find best delay
        best_delays_start = [-1]*len(self.transceivers)
        best_delays_end = [-2]*len(self.transceivers)
        current_delays_start = [None]*len(best_delays_start)
        prev_delay = delays[0]
        for delay, values in prbs_counters_all.items():
            for i,val in enumerate(values):
                if val == 0  and delay < delays[-1]:
                    if current_delays_start[i] is None:
                        current_delays_start[i] = delay
                else:
                    if current_delays_start[i] is not None:
                        current_range = prev_delay-current_delays_start[i]
                        best_range = best_delays_end[i]-best_delays_start[i]
                        if current_range > best_range:
                            best_delays_start[i] = current_delays_start[i]
                            best_delays_end[i] = prev_delay
                        current_delays_start[i] = None

            prev_delay=delay

        transceiver_optima = {}
        transceiver_ranges = {}
        for idx, tr in enumerate(self.get_transceivers()):
            if best_delays_start[idx] < 0:
                self.logger.warning("Transceiver {0:02d}: No delay found".format(tr))
                transceiver_optima[tr]=None
                transceiver_ranges[tr]=None
            else:
                start = best_delays_start[idx]
                end = best_delays_end[idx]
                mid = round((end+start)/2)
                open_range = end-start
                module = self.board.tb.gpio_lane2module_lut[tr]
                self.logger.info("Transceiver {0:02d}: Module: {5} Delay: {1:3d} ({2:3d} to {3:3d}, \"open\" range: {4:3d})"
                      .format(tr,mid,start,end,open_range,module))
                transceiver_optima[tr]=mid
                transceiver_ranges[tr]=open_range
                if set_optimum:
                    self.subset([tr]).load_idelay(transceiver_optima[tr])

        ####################################################################################
        # The following hack applies to L3_19/B-ML-Stave-062 where HS-L Module 0 Master 8  #
        # with extended chipId 24 on lane 6 has a stuck bit in the pattern generator.      #
        # Setting the delay to be the average of the two adjacent lanes works OK.          #
        # https://indico.cern.ch/event/942341/contributions/3959551/attachments/2084800/3502273/202007_L3_19_debug.pdf
        # https://alice-logbook.cern.ch/its-run3/date_online.php?p_cont=comd&p_cid=21282   #
        ####################################################################################
        stave_name = self.board.identity.get_stave_name()
        if stave_name == "L3_19":
            self.logger.warning("Aligning transceivers for L3_19!")
            transceiver_optima[6] = round((transceiver_optima[7] + transceiver_optima[5]) / 2.)
            self.logger.info(f"Transceiver 6 delay: {transceiver_optima[6]}")
            if set_optimum:
                self.subset([6]).load_idelay(transceiver_optima[6])
        ####################################################################################
        if stave_name == "L5_23":
            self.logger.warning("Aligning transceivers for L5_23, setting #13 to #12!")
            transceiver_optima[12] = transceiver_optima[13]
            self.logger.info(f"Transceiver 12 delay: {transceiver_optima[12]}")
            if set_optimum:
                self.subset([12]).load_idelay(transceiver_optima[12])

        if stave_name == "L3_21":
            self.logger.warning("Aligning transceivers for L3_21, setting #21 to #22!")
            transceiver_optima[21] = transceiver_optima[22]
            self.logger.info(f"Transceiver 21 delay: {transceiver_optima[21]}")
            if set_optimum:
                self.subset([21]).load_idelay(transceiver_optima[21])
        ####################################################################################
        #                                   End of hack                                    #
        ####################################################################################
        return transceiver_optima, transceiver_ranges

    def _read_hl(self,high,low):
        """Read high, low part of a register and return combined"""
        self.read(high,commitTransaction=False)
        self.read(low,commitTransaction=False)
        results = self.read_all()
        assert len(results) == 2, "Unexpected result length"
        result = results[0] << 16 | results[1]
        return result

    def is_aligned(self):
        """Return lock alignment status of each transceivers as array"""
        status = self._read_hl(GpioFrontendAddress.ALIGNMENT_STATUS_H,
                               GpioFrontendAddress.ALIGNMENT_STATUS_L)
        aligned = [status&(1<<i)>0 for i in self.transceivers]
        self.logger.debug(f"{aligned}")
        return aligned

    def _get_transceiver_mask(self):
        """Return mask for addressed transceivers"""
        mask = 0
        for transceiver in self.transceivers:
            mask |= (1<<transceiver)
        return mask

    def _write_masked_reg(self,addr_h, addr_l,flag,commitTransaction=True,readback=True):
        """Write to a register which needs to have a transceiver mask applied"""
        if(len(self.transceivers) < self.NR_TRANSCEIVERS) and readback:
            if not commitTransaction:
                self.logger.warning("Cannot have readback enabled with commitTransaction=False -> transaction will be committed")
                traceback.print_stack()
            reg = self._read_hl(addr_h,addr_l)
        else:
            reg = 0
        mask = self._get_transceiver_mask()

        if flag:
            reg |= mask
        else:
            reg &= ~mask
        reg_l = reg & 0xFFFF
        reg_h = (reg >> 16) & 0xFFFF

        self.write(addr_l,reg_l,commitTransaction=False)
        self.firmware_wait(10,commitTransaction=False)
        self.write(addr_h,reg_h,commitTransaction=commitTransaction)


    def enable_alignment(self, enable=True,commitTransaction=True):
        """Enable alignment flag for Transceivers. Does not touch transceivers not in list"""
        self._write_masked_reg(GpioFrontendAddress.ENABLE_ALIGNMENT_H,
                               GpioFrontendAddress.ENABLE_ALIGNMENT_L,
                               enable,commitTransaction)

    def enable_realign(self, enable=True,commitTransaction=True):
        """Enable realign flag for Transceivers. Does not touch transceivers not in list"""
        self._write_masked_reg(GpioFrontendAddress.ENABLE_REALIGN_H,
                               GpioFrontendAddress.ENABLE_REALIGN_L,
                               enable,commitTransaction)



    def enable_data(self,enable=True,commitTransaction=True):
        """Enable data flag for Transceivers. Does not touch transceivers not in list"""
        self._write_masked_reg(GpioFrontendAddress.ENABLE_DATA_H,
                               GpioFrontendAddress.ENABLE_DATA_L,
                               enable,commitTransaction)

    def load_idelay(self,value, commitTransaction=True):
        assert value <= 0x1FF, "Idelay value must be within 0:512"
        self.write(GpioFrontendAddress.IDELAY_VALUE,value,False)
        self._write_masked_reg(GpioFrontendAddress.IDELAY_LOAD_H,GpioFrontendAddress.IDELAY_LOAD_L,1,commitTransaction=False,readback=False)
        self.write(GpioFrontendAddress.IDELAY_LOAD_L,0,commitTransaction=False)
        self.write(GpioFrontendAddress.IDELAY_LOAD_H,0,commitTransaction=commitTransaction)

    def enable_prbs(self, enable=True,commitTransaction=True):
        """Enable PRBS checker for Transceivers. Does not touch transceivers not in list"""
        self._write_masked_reg(GpioFrontendAddress.ENABLE_PRBS_CHECK_H,
                               GpioFrontendAddress.ENABLE_PRBS_CHECK_L,
                               enable,commitTransaction,True)

    def set_input_inverter(self, value, commitTransaction=True):
        self.write(GpioFrontendAddress.INPUT_INVERTER_L, value & 0xFFFF, commitTransaction=commitTransaction)
        self.write(GpioFrontendAddress.INPUT_INVERTER_H, (value >> 16) & 0xFFFF, commitTransaction=commitTransaction)

    def reset_prbs_counter(self,commitTransaction=True):
        """Reset internal Transceiver PRBS counter"""
        self._write_masked_reg(GpioFrontendAddress.PRBS_RESET_COUNTER_H,
                               GpioFrontendAddress.PRBS_RESET_COUNTER_L,
                               flag=True,commitTransaction=False,readback=False)
        self.write(GpioFrontendAddress.PRBS_RESET_COUNTER_H,0,False)
        self.write(GpioFrontendAddress.PRBS_RESET_COUNTER_L,0,commitTransaction)

    def read_prbs_counter(self,reset=False):
        """Read / log the total amount of Prbs errors since the last check"""
        for tr in self.transceivers:
            self.read(GpioFrontendAddress.PRBS_COUNTER_LANE_0 + tr, commitTransaction = False)

        if reset:
            self.reset_prbs_counter(commitTransaction=False)

        results = self.read_all()
        prbs_errors = results

        return prbs_errors

    def set_lane_chip_mask(self,lane,mask,commitTransaction=True):
        """Set the chip mask for lane <lane>.
        A masked lane will not be considered for generating end of event for packaging
        """
        raise NotImplementedError("Obsolete")

    def get_lane_chip_mask(self,lane,commitTransaction=True):
        raise NotImplementedError("Obsolete")
