"""WP10 implementation of the TTC.
The file is meant to provide user usable functions for the CRU defined class
"""

import logging
from enum import IntEnum

from roc import Roc

import cru_table
from cru_si534x import CruSi534x
from cru_si534x import Si5345ClockSelect

import math


class MuxDownstreamData(IntEnum):
    """TTC Multiplexer selection
    PATTERN_PLAYER = "pattern"
    CTP_EMULATOR   = "ctp"
    EXTERNAL_CTP   = "midtrg"
    """
    PATTERN_PLAYER = 0
    CTP_EMULATOR   = 1
    EXTERNAL_CTP   = 2

class CruTtc(Roc):
    """
    WP10-defined wrapper for TTC
    several functions imported from equivalent class in cru-sw subtree
    """

    def __init__(self, pcie_opened_roc, pcie_id):
        """Init method for TTC"""

        Roc.__init__(self)
        self.set_roc(pcie_opened_roc)
        self.max_bcid = 3564 - 1
        self.pcie_id = pcie_id


        # Note: Global clock is selected in SI5345_2
        chip_add = 0x68  # chip address is fixed
        si5345_2_addr = cru_table.CRUADD['add_bsp_i2c_si5345_2']
        self.pll2 = CruSi534x(pcie_opened_roc, pcie_id, 2, si5345_2_addr, chip_add)

        self.name = "TTC"
        self.logger = logging.getLogger(f"{self.name}")

        self._mux_downstream_data_key = {MuxDownstreamData.PATTERN_PLAYER : "pattern",
                                         MuxDownstreamData.CTP_EMULATOR   : "ctp",
                                         MuxDownstreamData.EXTERNAL_CTP   : "midtrg"}

    def initialize(self):
        """Initializes the module for the ITS operation"""
        pass

    # ----  JS Methods imported from cru-sw ----

    def reset_emulator(self, do_reset):
        """ Reset/disable CTP emulator """
        if do_reset:
            self.roc_write(cru_table.CRUADD['add_ctp_emu_runmode'], 0x3)  # go idle
            self.roc_rmw(cru_table.CRUADD['add_ctp_emu_ctrl'], 31, 1, 1)
        else:
            self.roc_rmw(cru_table.CRUADD['add_ctp_emu_ctrl'], 31, 1, 0)

    def set_emulator_trig_mode(self, mode):
        """ Put emulator in triggered mode """

        # always go through idle
        self.roc_rmw(cru_table.CRUADD['add_ctp_emu_runmode'], 0, 2, 0x3)

        if mode == "periodic":
            self.roc_rmw(cru_table.CRUADD['add_ctp_emu_runmode'], 0, 2, 0x1)
        elif mode == "manual":
            self.roc_rmw(cru_table.CRUADD['add_ctp_emu_runmode'], 0, 2, 0x0)
        elif mode == "continuous":
            self.roc_rmw(cru_table.CRUADD['add_ctp_emu_runmode'], 0, 2, 0x2)
        else:
            raise ValueError("invalid trigger mode, allowed are only periodic/manual/continuous")

    def do_manual_phys_trig(self):
        """ Request one physical trigger, works only in manual triggered mode """
        self.roc_rmw(cru_table.CRUADD['add_ctp_emu_runmode'], 8, 1, 0x01)  # set bit
        self.roc_rmw(cru_table.CRUADD['add_ctp_emu_runmode'], 8, 1, 0x00)  # clear bit

    def set_emulator_cont_mode(self):
        """ Put emulator in continuous mode """
        self.roc_rmw(cru_table.CRUADD['add_ctp_emu_runmode'], 0, 2, 0x3)  # always go through idle
        self.roc_rmw(cru_table.CRUADD['add_ctp_emu_runmode'], 0, 2, 0x2)

    def set_emulator_idle_mode(self):
        """ Put emulator in idle mode (generate SOX if running) """
        self.roc_rmw(cru_table.CRUADD['add_ctp_emu_runmode'], 0, 2, 0x3)  # always go through idle

    def set_emulator_standalone_flow_control(self, allow=False):
        """ Controls CTPemulator HBF rejection, when True activate internal flow control """
        self.roc_rmw(cru_table.CRUADD['add_ctp_emu_runmode'], 2, 1, allow)

    def set_emulator_bcmax(self, bcmax):
        """ Set Bunch Crossing ID max value (12 bit), will count from 0 to max BCID value  """
        assert bcmax <= self.max_bcid
        self.roc_write(cru_table.CRUADD['add_ctp_emu_bc_max'], bcmax)

    def set_emulator_hbmax(self, hbmax):
        """ Set Heart Bit ID max value (16 bit)  """
        assert hbmax < (1<<16)
        self.roc_write(cru_table.CRUADD['add_ctp_emu_hb_max'], hbmax)

    def set_emulator_prescaler(self, hbkeep, hbdrop):
        """ Set Heart Bit frames to keep (16 bit) and to drop.

        Cycle always start with keep, then it alternates with HB to keep and to drop
        until the end of TimeFrame.
        Use a HBDROP larger than HBMAX to keep HBF only at the beginning of HBF
        """
        assert 2 <= hbkeep < (1<<16)
        assert 2 <= hbdrop < (1<<16)
        self.roc_write(cru_table.CRUADD['add_ctp_emu_prescaler'], (hbdrop << 16) | hbkeep)

    def set_emulator_physdiv(self, physdiv):
        """ Generate physics trigger every PHYSDIV ticks (28 bit max), larger than 7 to activate  """
        assert physdiv < (1<<28)
        self.roc_write(cru_table.CRUADD['add_ctp_emu_physdiv'], physdiv)

    def get_emulator_physdiv(self):
        """ Returns physics trigger every PHYSDIV ticks (28 bit max), larger than 7 to activate  """
        return self.roc_read(cru_table.CRUADD['add_ctp_emu_physdiv'])

    def set_emulator_caldiv(self, caldiv):
        """ Generate calibration trigger every CALDIV ticks (28 bit max), larger than 18 to activate  """
        assert caldiv < (1<<28)
        self.roc_write(cru_table.CRUADD['add_ctp_emu_caldiv'], caldiv)

    def set_emulator_hcdiv(self, hcdiv):
        """ Generate healthcheck trigger every HCDIV ticks (28 bit max), larger than 10 to activate  """
        assert hcdiv < (1<<28)
        self.roc_write(cru_table.CRUADD['add_ctp_emu_hcdiv'], hcdiv)

    def set_fbct(self, fbct_array):
        """ Set trigger at fixed bunch crossings. 9 values must always be transferred, a value of 0 deactivate the slot """
        assert len(fbct_array) == 9
        for val in fbct_array:
            if val < 0 or val > self.max_bcid:
                raise ValueError("Invalid FBCT value")
            if val == 0:  # deactivate FBCT
                newval = 0
            elif val <= 2:  # compensate latency
                newval = self.max_bcid - (2 - val)
            else:
                newval = val - 2
                self.roc_write(cru_table.CRUADD['add_ctp_emu_fbct'], newval)

    def select_downstream_data(self, downstream_data):
        """ Selects between CTP and pattern player output to forward """

        if downstream_data == "ctp":
            self.roc_rmw(cru_table.CRUADD['add_ttc_data_ctrl'], 16, 2, 0)
        elif downstream_data == "pattern":
            self.roc_rmw(cru_table.CRUADD['add_ttc_data_ctrl'], 16, 2, 1)
        elif downstream_data == "midtrg":
            self.roc_rmw(cru_table.CRUADD['add_ttc_data_ctrl'], 16, 2, 2)
        else:
            raise ValueError("Invalid downstream data source, valid source are ctp or pattern, router")

    def get_downstream_data(self):
        """ Prints the source of TTC downstream data """

        datactrl = (self.roc_read(cru_table.CRUADD['add_ttc_data_ctrl']) >> 16) & 0x3
        if datactrl == 0:
            src = "CTP"
        elif datactrl == 1:
            src = "PATTERN"
        else:
            src = "MID TRG"
        return src

    def get_hb_trig_from_ltu_count(self):
        """ Get count of HB trigs received from LTU (32 bit counter) """
        return self.roc_read(cru_table.CRUADD['add_ttc_hbtrig_ltu'])

    def get_phys_trig_from_ltu_count(self):
        """ Get count of PHYS trigs received from LTU (32 bit counter) """
        return self.roc_read(cru_table.CRUADD['add_ttc_phystrig_ltu'])

    def get_sox_eox_trig_from_ltu_count(self):
        """ Get count of SOx/EOx trigs received from LTU (2x 4 bit counter) """
        val = self.roc_read(cru_table.CRUADD['add_ttc_eox_sox_ltu'])
        sox_count = (val & 0XF)
        eox_count = ((val>>4) & 0XF)
        return sox_count, eox_count

    # -------------------- JS end import -----------------------------------

    def configure_emulator(self,
                           heartbeat_period_bc,
                           heartbeat_wrap_value=8,
                           heartbeat_keep=3,
                           heartbeat_drop=2,
                           periodic_trigger_period_bc=8):
        """Configures the TTC emulator,
        refer to the individual functions for the input paramenters documentation"""
        self.set_reset_value(value=1)
        self.set_mux_downstream(MuxDownstreamData.CTP_EMULATOR)
        self.set_emulator_idle_mode()
        self.set_heartbeat_period(value_bc=heartbeat_period_bc)
        self.set_heartbeat_wrap_around(wrap_value=heartbeat_wrap_value)
        self.set_heartbeat_keep(keep_value=heartbeat_keep, drop_value=heartbeat_drop)
        self.set_periodic_trigger_period(periodic_trigger_period_bc)
        self.set_reset_value(value=0)

    def set_reset_value(self, value):
        """Sets the value of the TTC reset,
        value in [0,1]"""
        assert value in range(2)
        self.reset_emulator(value)

    def set_mux_downstream(self, value):
        """Sets the downstream multiplexer to the selected value.
        Value should be one of the MuxDownstreamData allowed values"""
        value = MuxDownstreamData(value)
        self.select_downstream_data(self._mux_downstream_data_key[value])

    def set_heartbeat_period(self, value_bc):
        """Sets the HeartBeat (HB) period value in BC"""
        value = value_bc-1 # wrap around value
        assert value in range(self.max_bcid+1), f"HB period out of range {value} not in [0,{self.max_bcid+1}]"
        self.set_emulator_bcmax(value)

    def get_heartbeat_period(self):
        """Just guessing, no documentation on that...
        value returned as-is"""
        return self.roc_read(cru_table.CRUADD['add_ctp_emu_bc_max']) & 0xFFF

    def set_heartbeat_wrap_around(self, wrap_value):
        """Sets the wrap around value of the HeartBeat (HB).
        Every time the HB counter wraps around, a new Time Frame (TF) is sent"""
        assert wrap_value >= 0
        self.set_emulator_hbmax(wrap_value)

    def set_heartbeat_keep(self, keep_value, drop_value):
        """Sets the number of HeartBeat (HB) accept and reject in a Time Frame (TF)"""
        self.set_emulator_prescaler(hbkeep=keep_value, hbdrop=drop_value)

    def set_periodic_trigger_period(self, value_bc):
        """Sets the periodic trigger period in BCs
        1 BC ~ 25ns
        """
        value = value_bc-1 # wrap around value
        if value < 7:
            value = 7
            self.logger.warning("Periodic trigger period set to minimum (200 ns)")
        self.set_emulator_physdiv(value)

    # TTC FSM control

    def send_soc(self):
        """Sends a Start Of Continuous trigger.
        """
        self.set_emulator_trig_mode(mode="continuous")

    def send_eoc(self):
        """Sends a End Of Continuous trigger.
        """
        self.set_emulator_idle_mode()

    def send_sot(self, periodic_triggers=False):
        """Sends a Start Of Triggered trigger and optionally starts periodic triggers.
        """
        if periodic_triggers:
            self.set_emulator_trig_mode(mode="periodic")
        else:
            self.set_emulator_trig_mode(mode="manual")

    def send_eot(self):
        """Sends a End Of Triggered trigger.
        """
        self.set_emulator_idle_mode()

    def send_physics_trigger(self):
        """Sends one physics trigger.
        """
        self.do_manual_phys_trig()

    def log_onu_status(self):
        """ Checks onu status by reading the onu user register and Si5345 clock input"""

        # Note: register adresses and decoding taken from TTC.py

        clk_in_sel = self.pll2.get_clock_select()

        onu_addr = self.roc_read(cru_table.CRUADD["add_onu_user_logic"]) >> 1

        cal_status = self.roc_read(cru_table.CRUADD["add_onu_user_logic"] + 0xc)

        self.logger.info(f"{Si5345ClockSelect(clk_in_sel).name} clock is selected")
        self.logger.info("PON status:")
        self.logger.info(f"  ONU address:\t{onu_addr}")
        self.logger.info("  ONU RX40 locked:\t" + ["NOT OK", "OK"][cal_status & 0x1])
        self.logger.info("  ONU phase good:\t" + ["NOT OK", "OK"][(cal_status >> 1) & 0x1])
        self.logger.info("  ONU RX locked: \t" + ["NOT OK", "OK"][(cal_status >> 2) & 0x1])
        self.logger.info("  ONU operational:\t" + ["NOT OK", "OK"][(cal_status >> 3) & 0x1])
        self.logger.info("  ONU MGT TX ready:\t" + ["NOT OK", "OK"][(cal_status >> 4) & 0x1])
        self.logger.info("  ONU MGT RX ready:\t" + ["NOT OK", "OK"][(cal_status >> 5) & 0x1])
        self.logger.info("  ONU MGT TX pll lock:\t" + ["NOT OK", "OK"][(cal_status >> 6) & 0x1])
        self.logger.info("  ONU MGT RX pll lock:\t" + ["NOT OK", "OK"][(cal_status >> 7) & 0x1])
        self.logger.info(f"  TTC Clock Frequency:\t{self.roc_read(cru_table.CRUADD['add_ttc_clkgen_ttc240freq']) / 1e6 : .2f} MHz")
        self.logger.info(f"  Glb Clock Frequency:\t{self.roc_read(cru_table.CRUADD['add_ttc_clkgen_glb240freq']) / 1e6 : .2f} MHz")
