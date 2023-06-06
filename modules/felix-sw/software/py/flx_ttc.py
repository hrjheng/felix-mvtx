"""WP10 implementation of the TTC.
The file is meant to provide user usable functions for the CRU defined class
"""

import logging
from enum import IntEnum

from flx_roc import Roc
from flx_table import FLXADD


class FlxTtc(Roc):
    """
    MVTX-defined wrapper for TTC
    """

    def __init__(self, flx_opened_roc):
        """Init method for TTC"""

        Roc.__init__(self)
        self.set_roc(flx_opened_roc)
        self.max_bcid = 3564 - 1

        self.name = "TTC"
        self.logger = logging.getLogger(f"{self.name}")

    def initialize(self):
        """Initializes the module for the MVTX operation"""
        pass

    def reset_emulator(self, do_reset):
        """ Reset/disable CTP emulator """
        if do_reset:
            self.roc_write(FLXADD['add_ttc_emu_runmode'], 0x3)  # go idle
            self.roc_write(FLXADD['add_ttc_emu_reset'], 1)
        else:
            self.roc_write(FLXADD['add_ttc_emu_reset'], 0)

    def set_emulator_trig_mode(self, mode, use_gtm=False):
        """ Put emulator in triggered mode """

        if use_gtm:
            use_gtm_bit = 0x4
        else:
            use_gtm_bit = 0

        # always go through idle
        self.roc_write(FLXADD['add_ttc_emu_runmode'], 0x3)

        if mode == "periodic":
            self.roc_write(FLXADD['add_ttc_emu_runmode'], (0x1 | use_gtm_bit))
        elif mode == "manual":
            self.roc_write(FLXADD['add_ttc_emu_runmode'], (0x0 | use_gtm_bit))
        elif mode == "continuous":
            self.roc_write(FLXADD['add_ttc_emu_runmode'], (0x2 | use_gtm_bit))
        else:
            raise ValueError("invalid trigger mode, allowed are only periodic/manual/continuous")

    def do_manual_phys_trig(self):
        """ Request one physical trigger, works only in manual triggered mode """
        self.roc_write(FLXADD['add_ttc_emu_physreq'], 0x01)  # should pulse this register

    def set_emulator_cont_mode(self, use_gtm=False):
        """ Put emulator in continuous mode """

        if use_gtm:
            value = 0x6
        else:
            value = 0x2
        self.roc_write(FLXADD['add_ttc_emu_runmode'], 0x3)  # always go through idle
        self.roc_write(FLXADD['add_ttc_emu_runmode'], value)

    def set_emulator_idle_mode(self):
        """ Put emulator in idle mode (generate SOX if running) """
        self.roc_write(FLXADD['add_ttc_emu_runmode'], 0x3)

    def set_emulator_bcmax(self, bcmax):
        """ Set Bunch Crossing ID max value (12 bit), will count from 0 to max BCID value  """
        assert bcmax <= self.max_bcid
        self.roc_write(FLXADD['add_ttc_emu_bcmax'], bcmax)

    def set_emulator_hbmax(self, hbmax):
        """ Set Heart Beat ID max value (16 bit)  """
        assert hbmax < (1<<16)
        self.roc_write(FLXADD['add_ttc_emu_hbmax'], hbmax)

    def get_emulator_hbmax(self):
        """Get Heart Beat ID max value"""
        return self.roc_read(FLXADD['add_ttc_emu_hbmax'])

    def set_emulator_prescaler(self, hbkeep, hbdrop):
        """ Set Heart Bit frames to keep (16 bit) and to drop.

        Cycle always start with keep, then it alternates with HB to keep and to drop
        until the end of TimeFrame.
        Use a HBDROP larger than HBMAX to keep HBF only at the beginning of HBF
        """
        assert 2 <= hbkeep < (1<<16)
        assert 2 <= hbdrop < (1<<16)
        self.roc_write(FLXADD['add_ttc_emu_hbkeep'], hbkeep)
        self.roc_write(FLXADD['add_ttc_emu_hbdrop'], hbdrop)

    def get_hbkeep(self):
        """Get value of HPKEEP register"""
        return self.roc_read(FLXADD['add_ttc_emu_hbkeep'])

    def get_hbdrop(self):
        """Get value of HPDROP register"""
        return self.roc_read(FLXADD['add_ttc_emu_hbdrop'])

    def set_emulator_physdiv(self, physdiv):
        """ Generate physics trigger every PHYSDIV ticks (28 bit max), larger than 7 to activate  """
        assert physdiv < (1<<28)
        self.roc_write(FLXADD['add_ttc_emu_physdiv'], physdiv)

    def get_emulator_physdiv(self):
        """ Returns physics trigger every PHYSDIV ticks (28 bit max), larger than 7 to activate  """
        return self.roc_read(FLXADD['add_ttc_emu_physdiv'])

    def configure_emulator(self,
                           heartbeat_period_bc,
                           heartbeat_wrap_value=8,
                           heartbeat_keep=3,
                           heartbeat_drop=2,
                           periodic_trigger_period_bc=8):
        """Configures the TTC emulator,
        refer to the individual functions for the input paramenters documentation"""
        self.set_reset_value(value=1)
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

    def set_heartbeat_period(self, value_bc):
        """Sets the HeartBeat (HB) period value in BC"""
        value = value_bc-1 # wrap around value
        assert value in range(self.max_bcid+1), f"HB period out of range {value} not in [0,{self.max_bcid+1}]"
        self.set_emulator_bcmax(value)

    def get_heartbeat_period(self):
        """Just guessing, no documentation on that...
        value returned as-is"""
        return self.roc_read(FLXADD['add_ttc_emu_bcmax']) & 0xFFF

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
        """Sends a Start Of Continuous (SOC) trigger.
        """
        self.set_emulator_trig_mode(mode="continuous")

    def send_eoc(self):
        """Sends an End Of Continuous (EOC) trigger.
        """
        self.set_emulator_idle_mode()

    def send_sot(self, periodic_triggers=False):
        """Sends a Start Of Triggered (SOT) trigger and optionally starts periodic triggers.
        """
        if periodic_triggers:
            self.set_emulator_trig_mode(mode="periodic")
        else:
            self.set_emulator_trig_mode(mode="manual")

    def send_eot(self):
        """Sends an End Of Triggered (EOT) trigger.
        """
        self.set_emulator_idle_mode()

    def send_physics_trigger(self):
        """Sends one physics trigger.
        """
        self.do_manual_phys_trig()

    def use_gtm_orbit(self):
        """Use the received BCO as Orbit value"""
        self.roc_write(FLXADD['add_ttc_emu_use_bco'], 1)

    def use_seq_orbit(self):
        """Use sequencer orbit counter as Orbit value"""
        self.roc_write(FLXADD['add_ttc_emu_use_bco'], 0)

    def get_use_gtm_orbit(self):
        """Return value of emu_use_bco register"""
        return self.roc_read(FLXADD['add_ttc_emu_use_bco'])
