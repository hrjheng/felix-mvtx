"""file implementing the control for the ws_identity wishbone slave"""

from enum import IntEnum, unique
from wishbone_module import WishboneModule
import warnings


class WsClockHealthStatusAddress(IntEnum):
    """memory mapping for the ws_identity got from ws_identity_pkg.vhd"""
    RESET_CLOCK_HEALTH_FLAGS            = 0x00
    CONFIG_RESET                        = 0x01
    CLOCK_HEALTH_FLAGS                  = 0x02
    TIMEBASE_EVENT_TIMESTAMP_UPTIME_LSB = 0x03
    TIMEBASE_EVENT_TIMESTAMP_UPTIME_CSB = 0x04
    TIMEBASE_EVENT_TIMESTAMP_UPTIME_MSB = 0x05
    CLK_EVENT_TIMESTAMP_UPTIME_LSB      = 0x06
    CLK_EVENT_TIMESTAMP_UPTIME_CSB      = 0x07
    CLK_EVENT_TIMESTAMP_UPTIME_MSB      = 0x08
    TIMEBASE_EVENT_TIMESTAMP_ORBIT_LSB  = 0x09
    TIMEBASE_EVENT_TIMESTAMP_ORBIT_MSB  = 0x0A
    CLK_EVENT_TIMESTAMP_ORBIT_LSB       = 0x0B
    CLK_EVENT_TIMESTAMP_ORBIT_MSB       = 0x0C
    CLK_EVENT_TIMESTAMP_ORBIT_CSB       = 0x0D
    TIMEBASE_EVENT_TIMESTAMP_ORBIT_CSB  = 0x0E


@unique
class CONFIG_RESET(IntEnum):
    ENABLE_TH  = 0x0
    SOX        = 0x1


MAX_CONFIG_RESET_VAL = 2**len(CONFIG_RESET)-1


@unique
class ClockHealthFlags(IntEnum):
    JITTER_CLEANER_LOS  = 0x0
    JITTER_CLEANER_LOL  = 0x1
    LOL_TIMEBASE        = 0x2
    XCKU_CLOCK_LOL      = 0x3


MAX_CLOCK_HEALTH_FLAGS_VAL = 2**len(ClockHealthFlags)-1


class WsClockHealthStatus(WishboneModule):
    """wishbone slave used to identify the firmware and the FPGA"""

    def __init__(self, moduleid, board_obj):
        """init"""
        super(WsClockHealthStatus, self).__init__(moduleid=moduleid, board_obj=board_obj,
                                       name="Clock Health")

    def reset_clock_health_flags(self):
        """Reset clock health flags"""
        self.write(WsClockHealthStatusAddress.RESET_CLOCK_HEALTH_FLAGS, 0x1, commitTransaction=True)

    def _read_config_reset(self):
        val = self.read(WsClockHealthStatusAddress.CONFIG_RESET, commitTransaction=True)
        assert val | MAX_CONFIG_RESET_VAL == MAX_CONFIG_RESET_VAL, f"Config reset register value was outside expected range: {val}"
        return val

    def _get_config_reset_enable_th(self, config_reset):
        return (config_reset >> CONFIG_RESET.ENABLE_TH & 0x1)

    def _get_config_reset_sox(self, config_reset):
        return (config_reset >> CONFIG_RESET.SOX & 0x1)

    def _format_config_reset(self, config_reset):
        """Format reset configuration into dictionary"""
        return {
                'enable_th': self._get_config_reset_enable_th(config_reset),
                'sox': self._get_config_reset_sox(config_reset)}

    def get_config_reset(self):
        """Read and format the config_reset register"""
        return self._format_config_reset(self._read_config_reset())

    def write_config_reset(self, val, commitTransaction=True):
        assert val | MAX_CONFIG_RESET_VAL == MAX_CONFIG_RESET_VAL, f"Config reset register value is outside expected range: {val}"
        self.write(WsClockHealthStatusAddress.CONFIG_RESET, val, commitTransaction=commitTransaction)

    def set_config_reset_enable_th(self, commitTransaction=True):
        val = self._read_config_reset()
        val = val | (1<<CONFIG_RESET.ENABLE_TH)
        self.write_config_reset(val, commitTransaction)

    def clear_config_reset_enable_th(self, commitTransaction=True):
        val = self._read_config_reset()
        val = val & ~(1<<CONFIG_RESET.ENABLE_TH)
        self.write_config_reset(val, commitTransaction)

    def set_config_reset_sox(self, commitTransaction=True):
        val = self._read_config_reset()
        val = val | (1<<CONFIG_RESET.SOX)
        self.write_config_reset(val, commitTransaction)

    def clear_config_reset_sox(self, commitTransaction=True):
        val = self._read_config_reset()
        val = val & ~(1<<CONFIG_RESET.SOX)
        self.write_config_reset(val, commitTransaction)

    def _read_clock_health_flags(self):
        """Read the clock health flags register and assert that value is not higher than max"""
        val = self.read(WsClockHealthStatusAddress.CLOCK_HEALTH_FLAGS, commitTransaction=True)
        assert val | MAX_CLOCK_HEALTH_FLAGS_VAL == MAX_CLOCK_HEALTH_FLAGS_VAL, f"Clock health flags register value was outside expected range: {val}"
        return val

    def _get_jitter_cleaner_los(self, clock_health_flags):
        return (clock_health_flags >> ClockHealthFlags.JITTER_CLEANER_LOS & 0x1)

    def _get_jitter_cleaner_lol(self, clock_health_flags):
        return (clock_health_flags >> ClockHealthFlags.JITTER_CLEANER_LOL & 0x1)

    def _get_lol_timebase(self, clock_health_flags):
        return (clock_health_flags >> ClockHealthFlags.LOL_TIMEBASE & 0x1)

    def _get_xcku_clock_lol(self, clock_health_flags):
        return (clock_health_flags >> ClockHealthFlags.XCKU_CLOCK_LOL & 0x1)

    def _format_clock_health_flags(self, clock_health_flags):
        """Format clock health flags into dictionary"""
        return {
                'jitter_cleaner_los': self._get_jitter_cleaner_los(clock_health_flags),
                'jitter_cleaner_lol': self._get_jitter_cleaner_lol(clock_health_flags),
                'lol_timebase': self._get_lol_timebase(clock_health_flags),
                'xcku_clock_lol': self._get_xcku_clock_lol(clock_health_flags)}

    def get_clock_health_flags(self):
        """Read and return dictionary of clock health flags"""
        return self._format_clock_health_flags(self._read_clock_health_flags())

    def _request_timestamp(self, reg_list):
        for address in reg_list:
            self.read(address, commitTransaction=False)

    def _format_timestamp(self, reg_list, results):
        assert len(results) == len(reg_list)
        ret = 0
        for i, address in enumerate(reg_list):
            assert ((results[i][0] >> 8) & 0x7f) == self.moduleid, \
                    "Requested to read module {0}, but got result for module {1}, iteration {2}".format(self.moduleid, ((results[i][0] >> 8) & 0x7f), i)
            assert (results[i][0] & 0xff) == address.value, \
                    "Requested to read address {0}, but got result for address {1}, iteration {2}".format(address.value, (results[i][0] & 0xff), i)
            ret = ret | results[i][1]<<(16*i)
        return ret

    def get_timebase_event_timestamp_uptime(self):
        reg_list = [WsClockHealthStatusAddress.TIMEBASE_EVENT_TIMESTAMP_UPTIME_LSB, WsClockHealthStatusAddress.TIMEBASE_EVENT_TIMESTAMP_UPTIME_CSB, WsClockHealthStatusAddress.TIMEBASE_EVENT_TIMESTAMP_UPTIME_MSB]
        self._request_timestamp(reg_list)
        results = self.board.flush_and_read_results(expected_length=len(reg_list))
        return self._format_timestamp(reg_list, results)

    def get_clk_event_timestamp_uptime(self):
        reg_list = [WsClockHealthStatusAddress.CLK_EVENT_TIMESTAMP_UPTIME_LSB, WsClockHealthStatusAddress.CLK_EVENT_TIMESTAMP_UPTIME_CSB, WsClockHealthStatusAddress.CLK_EVENT_TIMESTAMP_UPTIME_MSB]
        self._request_timestamp(reg_list)
        results = self.board.flush_and_read_results(expected_length=len(reg_list))
        return self._format_timestamp(reg_list, results)

    def get_timebase_event_timestamp_orbit(self):
        reg_list = [WsClockHealthStatusAddress.TIMEBASE_EVENT_TIMESTAMP_ORBIT_LSB,
                    WsClockHealthStatusAddress.TIMEBASE_EVENT_TIMESTAMP_ORBIT_CSB,
                    WsClockHealthStatusAddress.TIMEBASE_EVENT_TIMESTAMP_ORBIT_MSB]
        self._request_timestamp(reg_list)
        results = self.board.flush_and_read_results(expected_length=len(reg_list))
        return self._format_timestamp(reg_list, results)

    def get_clk_event_timestamp_orbit(self):
        reg_list = [WsClockHealthStatusAddress.CLK_EVENT_TIMESTAMP_ORBIT_LSB,
                    WsClockHealthStatusAddress.CLK_EVENT_TIMESTAMP_ORBIT_CSB,
                    WsClockHealthStatusAddress.CLK_EVENT_TIMESTAMP_ORBIT_MSB]
        self._request_timestamp(reg_list)
        results = self.board.flush_and_read_results(expected_length=len(reg_list))
        return self._format_timestamp(reg_list, results)

    def is_jitter_cleaner_los_set(self):
        """Returns True if jitter_cleaner_los is set"""
        return self.get_clock_health_flags()['jitter_cleaner_los'] == 0x1

    def is_jitter_cleaner_lol_set(self):
        """Returns True if jitter_cleaner_lol is set"""
        return self.get_clock_health_flags()['jitter_cleaner_lol'] == 0x1

    def is_lol_timebase_set(self):
        """Returns True if lol_timebase is set"""
        return self.get_clock_health_flags()['lol_timebase'] == 0x1

    def is_xcku_clock_lol_set(self):
        """Returns True if xcku_clock_lol is set"""
        return self.get_clock_health_flags()['xcku_clock_lol'] == 0x1

    def is_any_clock_health_flags_set(self):
        """Returns True if any clock health flags are set"""
        return 0x1 in self.get_clock_health_flags().values()

    def is_any_clk_event_flags_set(self):
        return (self.is_jitter_cleaner_los_set() or
                self.is_jitter_cleaner_lol_set() or
                self.is_xcku_clock_lol_set())

    def dump_config(self):
        """Dump the modules state and configuration as a string"""
        config_str = f"--- {self.name} module ---\n"
        self.board.comm.disable_rderr_exception()
        for address in WsClockHealthStatusAddress:
            name = address.name
            try:
                value = self.read(address.value)
                config_str += "    - {0} : {1:#06X}\n".format(name, value)
            except:
                config_str += "    - {0} : FAILED\n".format(name)
        self.board.comm.enable_rderr_exception()
        return config_str
