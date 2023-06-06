"""Control of LTU emu"""
from enum import IntEnum, unique
import logging
import re
import xmlrpc.client
import unicodedata
import warnings

from ws_gbt_prbs_chk import PrbsMode

@unique
class LtuCounters(IntEnum):
    """List of counters returned by LTU `outcnts r`,
       enum value not used"""
    CAL      = 0
    EOC      = 1
    EOT      = 2
    HB       = 3
    HBr      = 4
    HC       = 5
    ORB      = 6
    PH       = 7
    PP       = 8
    SOC      = 9
    SOT      = 10
    TF       = 11
    TOF      = 12
    TPC_rst  = 13
    TPC_sync = 14
    GAP1     = 15
    GAP2     = 16
    clk240   = 17 # Can be ignored
    bc40     = 18 # Can be ignored
    FERST    = 19
    RS       = 20
    RT       = 21

@unique
class LtuEmuConfigs(IntEnum):
    """Ordering of emulator settings returned by LTU `emu status`
       order as left column->right column,
       enum value not used"""
    EOC_tf         = 0
    CAL_bc         = 1
    TOF_bc         = 2
    TF_orbit       = 3
    HBr_orbit      = 4
    HC             = 5
    TPC_RST_bc     = 6
    SOC_tf         = 7
    PH_rnd         = 8
    SOT_tf         = 9
    PH_bc          = 10
    EOT_tf         = 11
    PP_bc          = 12
    TPC_SYNC_orbit = 13

@unique
class LtuEmuMode(IntEnum):
    """Operating mode of LTU emu"""
    NOSOX  = 0
    SOTEOT = 1
    SOCEOC = 2

class Ltu:
    """LTU implementation"""
    ORBIT_RATE_BC = 3564
    TIMEFRAME_RATE_BC = ORBIT_RATE_BC*256
    INFINITE_TRIGGERS = 0xffffffff

    def __init__(self, hostname = "pcitsnuc", port = "8000"):
        self.comm = xmlrpc.client.ServerProxy(f"http://{hostname}:{port}")
        self.logger = logging.getLogger("LTU")
        self.trigger_rate = 0
        self.num_triggers = self.INFINITE_TRIGGERS

    def set_trigger_rate(self, rate):
        """Set default value for trigger rate.
        Value indicates the TRIGGER PERIOD in BC
        """
        assert rate | 0xFFFFFFFF == 0xFFFFFFFF, "Value too big"
        self.trigger_rate = rate

    def set_num_triggers(self, num):
        """Set default value for number of triggers to send"""
        assert num | 0xFFFFFFFF == 0xFFFFFFFF, "Value too big"
        self.num_triggers = num

    def send_soc(self):
        """Sends a Start Of Continuous trigger"""
        self.comm.send_soc()

    def send_eoc(self):
        """Sends a End Of Continuous trigger"""
        self.comm.send_eoc()

    def send_sot(self, periodic_triggers=False):
        """Sends a Start Of Triggered trigger"""
        assert periodic_triggers | 0x1 == 0x1, "Value too big"
        self.comm.send_sot()
        if periodic_triggers:
            self.send_physics_trigger(rate=self.trigger_rate, num=self.num_triggers, start_stop=False)

    def send_eot(self):
        """Sends a End Of Triggered trigger"""
        self.comm.send_eot()

    def run_continous(self, time_ms):
        """Sends a SOC, runs for time_ms and then sends an EOC"""
        assert time_ms | 0xFFFF == 0xFFFF, "Value too big"
        self.comm.run_continous(time_ms)

    def run_triggered(self, rate, time_ms):
        """Sends a SOT, runs for time_ms with rate of triggers and then sends an EOT"""
        assert rate | 0xFFFFFFFF == 0xFFFFFFFF, "Value too big"
        assert time_ms | 0xFFFF == 0xFFFF, "Value too big"
        rate_high = rate >> 16
        rate_low = rate & 0xFFFF
        self.comm.run_triggered(rate_high, rate_low, time_ms)

    def send_physics_trigger(self, rate=0, num=1, start_stop=False):
        """Sends num physics triggers at BC rate, if start_stop enabled, also send SOT/EOT"""
        assert num | 0xFFFFFFFF == 0xFFFFFFFF, "Value too big"
        assert rate | 0xFFFFFFFF == 0xFFFFFFFF, "Value too big"
        num_high = num >> 16
        num_low = num & 0xFFFF
        rate_high = rate >> 16
        rate_low = rate & 0xFFFF
        self.comm.send_physics_trigger(rate_high, rate_low, num_high, num_low, start_stop)

    def send_physics_trigger_random(self, rate=0, num=1, start_stop=False):
        """Sends num physics triggers at random interval BC rate, if start_stop enabled, also send SOT/EOT"""
        assert num | 0xFFFFFFFF == 0xFFFFFFFF, "Value too big"
        assert rate | 0xFFFFFFFF == 0xFFFFFFFF, "Value too big"
        num_high = num >> 16
        num_low = num & 0xFFFF
        rate_high = rate >> 16
        rate_low = rate & 0xFFFF
        self.comm.send_physics_trigger_random(rate_high, rate_low, num_high, num_low, start_stop)

    def set_heartbeat_reject_rate(self, rate=0, num=INFINITE_TRIGGERS):
        """Set realtionship between HBa and HBr.
        HBa is sent every orbit, rate sets the spacing in orbits for when also HBr is sent.
        num is the number of HBr sent between a SOX and EOX"""
        assert num | 0xFFFFFFFF == 0xFFFFFFFF, "Value too big"
        assert rate | 0xFFFFFFFF == 0xFFFFFFFF, "Value too big"
        num_high = num >> 16
        num_low = num & 0xFFFF
        rate_high = rate >> 16
        rate_low = rate & 0xFFFF
        self.comm.set_heartbeat_reject_rate(rate_high, rate_low, num_high, num_low)

    def get_heartbeat_reject_rate(self):
        """Returns the realtionship between HBa and HBr"""
        return self.get_emu_status_decode()['HBr_orbit'][0]

    def set_timeframe_rate(self, rate=TIMEFRAME_RATE_BC/ORBIT_RATE_BC):
        """Sets the rate at which timeframes are sent, measured in orbits."""
        assert rate | 0xFFFFFFFF == 0xFFFFFFFF, "Value too big"
        rate_high = rate >> 16
        rate_low = rate & 0xFFFF
        self.comm.set_timeframe_rate(rate_high, rate_low)

    def get_timeframe_rate(self):
        """Gets the rate at which timeframes are sent, measured in orbits."""
        return self.get_emu_status_decode()['TF_orbit'][0]

    def get_heartbeat_period(self):
        """Returns the period of heartbeats in BCings (25ns)"""
        return self.ORBIT_RATE_BC

    def reset_emu(self):
        """Resets emu and counters"""
        self.comm.reset_emu()

    def calibrate_pon(self):
        """Run a PON calibration"""
        self.comm.ttcpon_fullcal()

    def init_pon(self):
        """Run a reset and init of PON and SFPs"""
        self.comm.ttcpon_init()

    def enable_prbs(self, mode=PrbsMode.PRBS7):
        """Enable PRBS testing"""
        mode = PrbsMode(mode)
        self.comm.enable_prbs(mode.value)

    def disable_prbs(self):
        """Disable PRBS testing"""
        self.comm.disable_prbs()

    def enable_ferst(self, num=1):
        """When run started, FEreset is generated 'num' time frames before SOX (default: 1)
            0: behaves like 1"""
        assert num | 0xFFFF == 0xFFFF, "Value too big" # In principle it supports 32b, but would require an extra parameter and who needs that many FErst
        self.comm.enable_ferst(num)

    def disable_ferst(self):
        """Disable signaling FErst before SOX"""
        self.comm.disable_ferst()

    def get_emu_status(self):
        """Returns the table of configured signal rates"""
        return self.comm.log_emu_status()

    def get_emu_status_decode(self):
        """Returns the table of configured signal rates, decoded into an dictionary"""
        string = self.get_emu_status()
        string_split = str(string).split('\n')
        assert len(string_split) == 23 or len(string_split) == 18, "Too many elements returned from get_emu"
        if len(string_split) == 23:
            string = ('\n').join(str(string).split('\n')[3:-6])
        else:
            string = ('\n').join(str(string).split('\n')[3:-1])
        string = "".join(ch for ch in string if unicodedata.category(ch)[0]!="C") # Strip ASCII color encoding
        nums = re.findall(r' [0-9\-]+', string)
        ret = {}
        i = 0
        assert len(nums) == len(LtuEmuConfigs)*2, f"Too many numbers extracted {len(nums)} expected {len(LtuEmuConfigs)*2}"
        for num in nums:
            if i % 2 == 0:
                ret[LtuEmuConfigs(int(i/2)).name] = list()
            ret[LtuEmuConfigs(int(i/2)).name] += [num.strip()]
            i += 1
        return ret

    def get_trigger_mode(self):
        """Returns the current trigger mode of the device"""
        string = self.get_emu_status()
        string = str(string).split('\n')[2]
        return LtuEmuMode[string[string.rfind(':')+1:-1]]

    def get_ltu_status(self):
        """Returns the log generated by starting the LTU software"""
        return self.comm.log_ltu_status()

    def get_counters(self):
        """Returns the number of output signals generated since last reading"""
        return self.comm.log_counters()

    def get_counters_decode(self):
        """Returns the number of output signals generated since last reading, decoded into an dictionary"""
        string = str(self.get_counters())
        string = string[string.index('outcnts'):string.index("oldTTC counters")]
        
        nums = re.findall(r'[a-zA-Z_0-9]+: *[0-9]+', string)
        ret = {}
        for num in nums:
            counter = num.split(':')
            name = counter[0]
            counts = counter[1].lstrip()
            if not name in LtuCounters.__members__:
                warnings.warn(f"Unrecognized counter {name}")
            ret[name] = counts
        return ret

    def log_emu_status(self):
        """Returns the table of configured signal rates"""
        self.logger.info(self.get_emu_status())

    def log_ltu_status(self):
        """Returns the log generated by starting the LTU software"""
        self.logger.info(self.get_ltu_status())

    def log_counters(self):
        """Returns the number of output signals generated since last reading"""
        self.logger.info(self.get_counters())

    def reboot_ltu(self):
        """Warm reboots the LTU"""
        self.logger.info(self.comm.reboot_ltu())

    def is_ltu_on(self):
        """Check if the LTU is powered on and responds to pings"""
        try:
            if self.comm.is_ltu_on():
                return True
            else:
                self.logger.error("The LTU is not on")
                return False
        except: # pylint: disable=bare-except
            self.logger.error("The LTU server is not responding")
            return False

    def is_ltu_ok(self):
        """Checks if LTU booted up in the correct state"""
        return self.comm.is_ltu_ok()

    # Aliases
    def send_start_of_triggered(self):
        """Sends a Start Of Triggered trigger"""
        self.send_sot()
    def send_end_of_triggered(self):
        """Sends a End Of Triggered trigger"""
        self.send_eot()
    def send_start_of_continous(self):
        """Sends a Start Of Continous trigger"""
        self.send_soc()
    def send_end_of_continous(self):
        """Sends a End Of Continous trigger"""
        self.send_eoc()
    def send_trigger(self):
        """Sends single physics trigger"""
        self.send_physics_trigger(0, 1)
