"""Class to implement the trigger handler wishbone slave abstraction layer"""

from enum import IntEnum, unique
import time

from wishbone_module import WishboneModule

import trigger_handler_monitor

@unique
class WsTriggerHandlerAddress(IntEnum):
    """memory mapping for trigger handler module"""
    ENABLE                   = 0x00
    TRIGGER_PERIOD           = 0x01
    PULSE_nTRIGGER           = 0x02
    TRIGGER_MIN_DISTANCE     = 0x03
    OPERATING_MODE           = 0x04
    OPCODE_GATING            = 0x05
    TRIGGER_DELAY            = 0x06
    ENABLE_PACKER_0          = 0x07
    ENABLE_PACKER_1          = 0x08
    ENABLE_PACKER_2          = 0x09
    TRIG_SOURCE              = 0x0A
    SOX_ORBIT_LSB            = 0x0B
    SOX_ORBIT_MSB            = 0x0C
    SEQ_NUM_HB_PER_TF        = 0x0D
    ENABLE_TIMEBASE_SYNC     = 0x0E
    TIMEBASE_SYNCED          = 0x0F
    SEQ_ENABLE               = 0x10
    SEQ_CONTINUOUS_N_TRG     = 0x11
    SEQ_NUM_TF               = 0x12
    SEQ_NUM_HBA_PER_TF       = 0x13
    SEQ_PT_MODE              = 0x14
    SEQ_PT_PERIOD            = 0x15
    RM_RO_RESET              = 0x16
    FLUSH_FIFO               = 0x17
    IGNORE_TRG_IN_CONT_MODE  = 0x18
    INTERNAL_TRG_GRANT_LSB   = 0x19
    INTERNAL_TRG_GRANT_CSB   = 0x1A
    INTERNAL_TRG_GRANT_MSB   = 0x1B
    FIFO_EMPTY               = 0x1C
    EOX_ORBIT_LSB            = 0x1D
    EOX_ORBIT_MSB            = 0x1E
    DEBUG_FIFO               = 0x1F
    EOX_ORBIT_CSB            = 0x20
    SOX_ORBIT_CSB            = 0x21


@unique
class Pulse_nTrigger(IntEnum):
    """Pulse or trigger selection"""
    Trigger = 0x00
    Pulse   = 0x01


@unique
class TriggerSource(IntEnum):
    """Values for the TRIG_SOURCE register"""
    GBTx2     = 0
    SEQUENCER = 1


@unique
class SeqTriggerMode(IntEnum):
    """Values for the SEQ_PT_MODE register"""
    Periodic  = 0
    Random    = 1


@unique
class SeqMode(IntEnum):
    """Values for the SEQ_CONTINUOUS_N_TRG register"""
    Trigger    = 0
    Continous  = 1

@unique
class DebugFifoBit(IntEnum):
    """Enum for discriminating the bits of the DEBUG_FIFO_LANE_* register"""
    DATA       = 0
    RESERVED   = 11
    EMPTY      = 15

@unique
class OrbitBC(IntEnum):
    """Enum for discriminating the bits of the DEBUG_FIFO_LANE_* register"""
    BC       = 12
    ORBIT    = 32
    ORBITBC  = 44


# from https://www.overleaf.com/read/sybgrjhpghdz
ALLOWED_CONTINUOUS_MODE_PERIOD_BC = [3564,1782,1188,891,594,396,324,297,198]


class TriggerHandler(WishboneModule):
    """trigger handler wishbone slave"""

    def __init__(self, moduleid, board_obj, monitor_module):
        super(TriggerHandler, self).__init__(moduleid=moduleid, name="TRIGGER HANDLER", board_obj=board_obj)

        assert isinstance(monitor_module, trigger_handler_monitor.TriggerHandlerMonitor)
        self._monitor = monitor_module
        self.allowed_continuous_period_bc = ALLOWED_CONTINUOUS_MODE_PERIOD_BC

    def enable(self, commitTransaction=True):
        self.write(WsTriggerHandlerAddress.ENABLE, 1, commitTransaction=commitTransaction)

    def disable(self, commitTransaction=True):
        self.write(WsTriggerHandlerAddress.ENABLE, 0, commitTransaction=commitTransaction)

    def is_enable(self):
        return self.read(WsTriggerHandlerAddress.ENABLE) == 1

    def is_disabled(self):
        return self.read(WsTriggerHandlerAddress.ENABLE) == 0

    def disable_packer(self, packer, commitTransaction=True):
        assert packer in range(3)
        address = WsTriggerHandlerAddress.ENABLE_PACKER_0 + packer
        self.write(address, 0, commitTransaction=commitTransaction)

    def enable_packer(self, packer, commitTransaction=True):
        assert packer in range(3)
        address = WsTriggerHandlerAddress.ENABLE_PACKER_0 + packer
        self.write(address, 1, commitTransaction=commitTransaction)

    def is_packer_enabled(self, packer):
        assert packer in range(3)
        address = WsTriggerHandlerAddress.ENABLE_PACKER_0 + packer
        return self.read(address)

    def set_trigger_frequency(self, frequency_khz, commitTransaction=True):
        """Sets the trigger frequency in kHz"""
        assert frequency_khz > 0
        clock_cycles = round(1/(frequency_khz*1e3*25e-9))
        if clock_cycles >= 3564:
            self.logger.warning("Minimum trigger frequency selected {0:.3f} kHz".format(1/(3564*25e-9*1e3)))
            clock_cycles = 3564
        elif clock_cycles <= 0:
            self.logger.warning("Maximum (theoretical) trigger frequency selected {0} kHz".format(1/(10*25e-9*1e3)))
            clock_cycles = 10
        self.set_trigger_period(value=clock_cycles, commitTransaction=commitTransaction)

    def get_trigger_frequency(self):
        """Gets the continuous mode trigger frequency in kHz"""
        clock_cycles = self.get_trigger_period()
        return 1/(clock_cycles*25e-9*1e3)

    def set_trigger_period(self, value, commitTransaction=True):
        """Sets the continuous mode trigger period in units of 25ns"""
        assert value | 0x0FFF == 0x0FFF
        assert value > 0, "A trigger period of 0 is not possible"
        self.write(WsTriggerHandlerAddress.TRIGGER_PERIOD, value, commitTransaction=commitTransaction)

    def get_trigger_period(self):
        """Gets the continuous mode trigger period in units of 25ns"""
        return self.read(WsTriggerHandlerAddress.TRIGGER_PERIOD)

    def _set_pulse_ntrigger(self, value, commitTransaction=True):
        assert value in range(2)
        self.write(WsTriggerHandlerAddress.PULSE_nTRIGGER, value, commitTransaction=commitTransaction)

    def get_pulse_ntrigger(self):
        return self.read(WsTriggerHandlerAddress.PULSE_nTRIGGER)

    def configure_to_send_pulses(self, commitTransaction=True):
        self._set_pulse_ntrigger(Pulse_nTrigger.Pulse, commitTransaction=commitTransaction)

    def configure_to_send_triggers(self, commitTransaction=True):
        self._set_pulse_ntrigger(Pulse_nTrigger.Trigger, commitTransaction=commitTransaction)

    def set_trigger_minimum_distance(self, value, commitTransaction=True):
        """Sets the trigger minimum temporal distance in units of 6.25ns"""
        assert value | 0xFFFF == 0xFFFF
        self.write(WsTriggerHandlerAddress.TRIGGER_MIN_DISTANCE, value, commitTransaction=commitTransaction)

    def get_trigger_minimum_distance(self):
        """Gets the trigger minimum temporal distance in units of 6.25ns"""
        return self.read(WsTriggerHandlerAddress.TRIGGER_MIN_DISTANCE)

    def set_trigger_delay(self, value, commitTransaction=True):
        """Sets the trigger delay in units of 25ns"""
        assert value | 0x01FF == 0x01FF
        self.write(WsTriggerHandlerAddress.TRIGGER_DELAY, value, commitTransaction=commitTransaction)

    def get_trigger_delay(self):
        """Gets the trigger delay in units of 25ns"""
        return self.read(WsTriggerHandlerAddress.TRIGGER_DELAY)

    def get_operating_mode(self):
        """Returns the operating mode of the trigger_handler"""
        mode = self.read(WsTriggerHandlerAddress.OPERATING_MODE)
        # Mode:
        # Bit 3: 0=RO_WITH_DET, 1=RO_NO_DET
        # bits 2:0: 0: IDLE
        #           1: ARMED
        #           2: TRIGGERED
        #           3: CONTINUOUS
        #           4: CONTINUOUS_REJECT
        #           5: TRIGGERED_REJECT
        #           6: ILLEGAL
        #           7: ILLEGAL
        retdict = {'is_triggered':0, 'is_continuous':0}
        if (mode & 0x7) in (2, 5):
            retdict['is_triggered'] = 1
        if (mode & 0x7) in (3, 4):
            retdict['is_continuous'] = 1
        return mode, retdict

    def is_triggered_mode(self):
        mode = self.get_operating_mode()
        return (mode[1]['is_triggered'] == 0x1)

    def is_continuous_mode(self):
        mode = self.get_operating_mode()
        return (mode[1]['is_continuous'] == 0x1)

    def is_ro_no_det(self):
        """If true, no triggers are sent to the detector"""
        mode = self.read(WsTriggerHandlerAddress.OPERATING_MODE)
        return (mode>>3) & 0x1 == 1

    def is_ro_with_det(self):
        """If true, triggers are sent to the detector"""
        mode = self.read(WsTriggerHandlerAddress.OPERATING_MODE)
        return (mode>>3) & 0x1 == 0

    def set_number_of_bc_per_hb(self, value, commitTransaction=True):
        """Set the number of bunch crossings per heartbeat frame"""
        raise NotImplementedError("Value is fixed at 3564")

    def get_number_of_bc_per_hb(self):
        """Get the number of bunch crossings in a heartbeat frame"""
        return 3564

    def set_opcode_gating(self, value, commitTransaction=True):
        """Allows gating the trigger/pulse signal to the alpide control generating an empty gbt packet
        """
        assert value in range(2)
        self.write(WsTriggerHandlerAddress.OPCODE_GATING, value, commitTransaction=commitTransaction)

    def get_opcode_gating(self):
        """returns the current setting of the opcode gating register
        """
        return self.read(WsTriggerHandlerAddress.OPCODE_GATING)

    def mask_all_triggers(self, commitTransaction=True):
        self.set_opcode_gating(value=1, commitTransaction=False)
        for i in range(3):
            self.disable_packer(packer=i, commitTransaction=False)
        if commitTransaction:
            self.flush()

    def set_trigger_source(self, value=0, commitTransaction=True):
        """Set source of triggers"""
        assert value | 0x1 == 0x1
        self.write(WsTriggerHandlerAddress.TRIG_SOURCE, value, commitTransaction=commitTransaction)

    def get_trigger_source(self):
        """Returns the current setting of the trigger_source register"""
        val = self.read(WsTriggerHandlerAddress.TRIG_SOURCE)
        ret = {'GBTx2':0, 'SEQUENCER':0}
        if val == 0:
            ret['GBTx2'] = 1
        else:
            ret['SEQUENCER'] = 1
        return val, ret

    def set_reset_readout_master(self, value, commitTransaction=True):
        """Set the reset register of the Readout Master. System must be in RO_NO_DET mode or the trigger handler FSM in idle mode for the command to take effect."""
        assert value | 0x1 == 0x1
        self.write(WsTriggerHandlerAddress.RM_RO_RESET, value, commitTransaction)

    def reset_readout_master(self, commitTransaction=True):
        """Toggle reset of the Readout Master, system must be in RO_NO_DET mode or the trigger handler FSM in idle mode  for the command to take """
        assert self.is_ro_no_det(), f"This command must be run when the RO_NO_DET mode is active!"
        for value in [1, 0]:
            self.write(WsTriggerHandlerAddress.RM_RO_RESET, value, commitTransaction)

    def flush_fifo(self, commitTransaction=True):
        """Toggle flush of Trigger Handler input FIFO

        Trigger Handler must be disabled and Timebase Sync must be disabled
        """
        assert self.is_disabled(), f"This command is only valid when Trigger Handler is disabled!"
        assert self.is_timebase_sync_disabled(), f"This command is only valid when Timebase Sync is disabled!"
        for value in [1, 0]:
            self.write(WsTriggerHandlerAddress.FLUSH_FIFO, value, commitTransaction)

    def is_fifo_empty(self, fifo_id=0):
        """Return True if the specified trigger fifo is empty"""
        assert fifo_id in range(3), f"FIFO identifier must be within range 0-2"
        val = (self.read(WsTriggerHandlerAddress.FIFO_EMPTY) >> fifo_id) & 0x1
        return val == 0x1

    def are_fifos_empty(self):
        """Return True if all trigger fifos are empty"""
        val = self.read(WsTriggerHandlerAddress.FIFO_EMPTY) & 0x7
        return val == 0x7

    def reset_packer_fifos(self, commitTransaction=True):
        """Resets the packer fifos"""
        raise DeprecationWarning("Functionality moved to gbt_packer.reset()")
        self.board.gbt_packer.reset(commitTransaction=True)

    def setup_for_continuous_mode(self, trigger_period_bc, send_pulses=False):
        """Sets up the trigger handler for continuous mode"""
        assert trigger_period_bc in self.allowed_continuous_period_bc, "Invalid trigger period: see Table 4 of https://www.overleaf.com/read/sybgrjhpghdz"
        assert send_pulses in range(2)
        self.set_trigger_period(value=trigger_period_bc, commitTransaction=False)
        trigger_period = trigger_period_bc<<2 # in 6.25 ns units
        # distance between triggers = trigger period - 25ns (4 * 6.25ns) to avoid extended strobes,
        # but at least 625ns (100 * 6.25ns) to avoid loss by alpide control
        distance = trigger_period - 4
        if distance < 100:
            self.logger.warning("Trigger distance too low, setting it to 100")
            distance = 100
        self.set_trigger_minimum_distance(value=distance, commitTransaction=False)
        if send_pulses:
            self.configure_to_send_pulses()
        else:
            self.configure_to_send_triggers()

    def setup_for_triggered_mode(self, trigger_minimum_distance=100, send_pulses=False):
        """Sets up the trigger handler for triggered mode"""
        assert send_pulses in range(2)
        # Sets the trigger period to the max, avoid internal triggers in triggered mode
        self.set_trigger_period(value=3564, commitTransaction=False)
        if trigger_minimum_distance < 100:
            self.logger.warning("Trigger distance too low, setting it to 100")
            trigger_minimum_distance = 100
        self.set_trigger_minimum_distance(value=trigger_minimum_distance, commitTransaction=False)
        if send_pulses:
            self.configure_to_send_pulses()
        else:
            self.configure_to_send_triggers()

    def dump_config(self):
        """Dump the modules state and configuration as a string"""
        config_str = f"--- {self.name} module ---\n"
        self.board.comm.disable_rderr_exception()
        for address in WsTriggerHandlerAddress:
            name = address.name
            try:
                value = self.read(address.value)
                config_str += "    - {0} : {1:#06X}\n".format(name, value)
            except:
                config_str += "    - {0} : FAILED\n".format(name)
        self.board.comm.enable_rderr_exception()
        return config_str

    # Monitor

    def reset_counters(self, commitTransaction=True):
        """resets all the counters"""
        self._monitor.reset_all_counters(commitTransaction=commitTransaction)

    def read_counters(self, counters=None, latch_first=True, reset_after=False, commitTransaction=True):
        """latches and reads all the counters"""
        return self._monitor.read_counters(counters=counters, latch_first=latch_first, reset_after=reset_after, commitTransaction=commitTransaction)

    def get_rate_cnts(self):
        cnt_pre = self.read_counters()
        time.sleep(2)
        cnt_post = self.read_counters()
        return cnt_pre,cnt_post

    def get_nums(self, cnt_pre, cnt_post):
        nums = dict()
        nums['TF'] = cnt_post['TF'] - cnt_pre['TF']
        nums['HB'] = cnt_post['HB'] - cnt_pre['HB']
        nums['HBR'] = cnt_post['HBR'] - cnt_pre['HBR']
        nums['HBA'] = nums['HB'] - nums['HBR']
        nums['PT'] = cnt_post['PHYSICS'] - cnt_pre['PHYSICS']
        nums['SENT'] = cnt_post['TRIGGER_SENT'] - cnt_pre['TRIGGER_SENT']
        nums['PROC'] = cnt_post['PROCESSED_TRIGGERS'] - cnt_pre['PROCESSED_TRIGGERS']
        return nums

    def get_rates(self, nums):
        if nums['TF'] == 0:
            self.logger.error("Found no timeframes")
            exit()
        elif nums['HBA'] == 0:
            self.logger.error("Found no HBA")
            exit()
        rates = dict()
        rates['HB'] = round(nums['HB'] / nums['TF'], 1)
        rates['HBA'] = round(nums['HBA'] / nums['TF'], 1)
        rates['HBR'] = round(nums['HBR'] / nums['TF'], 1)
        rates['PT'] = round(nums['PT'] / nums['HBA'], 1)
        rates['SENT'] = round(nums['SENT'] / nums['HBA'], 1)
        rates['PROC'] = round(nums['PROC'] / nums['TF'], 1)
        return rates

    def format_rates(self, rates):
        log = \
            f"HB/TF: {rates['HB']} - " + \
            f"HBA/TF: {rates['HBA']} - " + \
            f"HBR/TF: {rates['HBR']} - " + \
            f"PT/HBA: {rates['PT']} - " + \
            f"SENT/HBA: {rates['SENT']} - " + \
            f"PROC/TF: {rates['PROC']}"
        return log

    def log_rates(self):
        cnt_pre, cnt_post = self.get_rate_cnts()
        nums = self.get_nums(cnt_pre, cnt_post)
        rates = self.get_rates(nums)
        self.logger.info(self.format_rates(rates))

    # def get_rate_hba(self, cnt_pre, cnt_post, tf):
    #     return (cnt_post['HB'] - cnt_pre['HB']) - (cnt_post['HBR'] - cnt_pre['HBR']) / tf

    # def get_rate_hbr(self, cnt_pre, cnt_post, tf):
    #     return (cnt_post['HBR'] - cnt_pre['HBR']) / tf

    def get_sox_orbit(self):
        """Get SoX Orbit"""
        msb = self.read(WsTriggerHandlerAddress.SOX_ORBIT_MSB)
        csb = self.read(WsTriggerHandlerAddress.SOX_ORBIT_CSB)
        return (self.read(WsTriggerHandlerAddress.SOX_ORBIT_LSB) | (csb << 16) | (msb << 32))

    def get_eox_orbit(self):
        """Get SoX Orbit"""
        msb = self.read(WsTriggerHandlerAddress.EOX_ORBIT_MSB)
        csb = self.read(WsTriggerHandlerAddress.EOX_ORBIT_CSB)
        return (self.read(WsTriggerHandlerAddress.EOX_ORBIT_LSB) | (csb << 16) | (msb << 32))

    # Timebase

    def enable_timebase_sync(self, enable_timebase_correction=False, commitTransaction=True):
        """Enable syncing of the timebase generator to the incoming trigger message time information"""
        if enable_timebase_correction:
            val = 0x3
        else:
            val = 0x1
        self.write(data=val, addr=WsTriggerHandlerAddress.ENABLE_TIMEBASE_SYNC, commitTransaction=commitTransaction)

    def disable_timebase_sync(self, commitTransaction=True):
        """Disable syncing of the timebase generator to the incoming trigger message time information"""
        self.write(data=0, addr=WsTriggerHandlerAddress.ENABLE_TIMEBASE_SYNC, commitTransaction=commitTransaction)

    def is_timebase_sync_enable(self):
        return self.read(WsTriggerHandlerAddress.ENABLE_TIMEBASE_SYNC) == 1

    def is_timebase_sync_disabled(self):
        return self.read(WsTriggerHandlerAddress.ENABLE_TIMEBASE_SYNC) == 0

    def get_timebase_sync_enable(self):
        """Get the synchronization enable status of the timebase module"""
        return self.read(WsTriggerHandlerAddress.ENABLE_TIMEBASE_SYNC)

    def is_timebase_synced(self):
        """Returns if the timebase module and the trigger message timing information agree"""
        return self.read(WsTriggerHandlerAddress.TIMEBASE_SYNCED) == 1

    # Sequencer

    def sequencer_start(self, commitTransaction=True):
        """Starts the sequencer transactions"""
        self.sequencer_enable(commitTransaction=commitTransaction)

    def sequencer_stop(self, commitTransaction=True):
        """Stops the sequencer transactions"""
        self.sequencer_disable(commitTransaction=commitTransaction)

    def sequencer_enable(self, commitTransaction=True):
        """Starts the sequencer"""
        self.write(data=1, addr=WsTriggerHandlerAddress.SEQ_ENABLE, commitTransaction=commitTransaction)

    def sequencer_disable(self, commitTransaction=True):
        """Stops the sequencer"""
        self.write(data=0, addr=WsTriggerHandlerAddress.SEQ_ENABLE, commitTransaction=commitTransaction)

    def is_sequencer_started(self):
        """Returns if the sequencer has started"""
        return self.read(addr=WsTriggerHandlerAddress.SEQ_ENABLE) == 1

    def sequencer_set_mode_continuous(self, commitTransaction=True):
        """Sets sequencer operating mode to CONTINUOUS"""
        self.write(data=1, addr=WsTriggerHandlerAddress.SEQ_CONTINUOUS_N_TRG, commitTransaction=commitTransaction)

    def sequencer_set_mode_triggered(self, commitTransaction=True):
        """Sets sequencer operating mode to CONTINUOUS"""
        self.write(data=0, addr=WsTriggerHandlerAddress.SEQ_CONTINUOUS_N_TRG, commitTransaction=commitTransaction)

    def sequencer_get_mode(self):
        """Get Sequencer operating mode; 1=CONTINUOUS, 0=TRIGGERED"""
        return SeqTriggerMode(self.read(WsTriggerHandlerAddress.SEQ_CONTINUOUS_N_TRG))

    def sequencer_set_number_of_timeframes(self, value, commitTransaction=True):
        """Set the number of timeframes the sequencer should generate"""
        assert value | 0x1FF == 0x1FF, "Number of timeframes should be < 512"
        self.write(WsTriggerHandlerAddress.SEQ_NUM_TF, value, commitTransaction=commitTransaction)

    def sequencer_set_number_of_timeframes_infinite(self, enable, commitTransaction=True):
        """Set the number of timeframes to infinite if enable"""
        assert enable | 0x1 == 0x1
        enable = enable << 9
        self.write(WsTriggerHandlerAddress.SEQ_NUM_TF, enable, commitTransaction=commitTransaction)

    def sequencer_get_number_of_timeframes(self):
        """Get the number of timeframes the sequencer should generate"""
        return (self.read(WsTriggerHandlerAddress.SEQ_NUM_TF)) & 0x200

    def sequencer_is_done_timeframes(self):
        """Gets the information if the sequencer is done"""
        return self.sequencer_get_number_of_timeframes()==0

    def sequencer_get_number_of_timeframes_infinite(self):
        """check if the number of timeframes the sequencer should generate is at infinite"""
        return ((self.read(WsTriggerHandlerAddress.SEQ_NUM_TF)) >> 9) & 0x1

    def sequencer_set_number_of_hba_per_timeframe(self, value, commitTransaction=True):
        """Set the number of HB accept per timeframe the sequencer should generate"""
        assert value | 0x1FF == 0x1FF, "Number of HBa should be < 512"
        self.write(WsTriggerHandlerAddress.SEQ_NUM_HBA_PER_TF, value, commitTransaction=commitTransaction)

    def sequencer_get_number_of_hba_per_timeframe(self):
        """Set the number of HB accept per timeframe the sequencer should generate"""
        return (self.read(WsTriggerHandlerAddress.SEQ_NUM_HBA_PER_TF))

    def sequencer_set_trigger_period(self, value, commitTransaction=True):
        """Set the period of PhT triggers in BC (25ns) units (average number of BCs per PhT)
        In random trigger mode, this is the average period."""
        assert value | 0xFFF == 0xFFF, "PhT period should be < 4096"
        assert value > 0, "PhT period of 0 is invalid"
        self.write(WsTriggerHandlerAddress.SEQ_PT_PERIOD, value, commitTransaction=commitTransaction)

    def sequencer_get_trigger_period(self):
        """Get the period of PhT triggers in BC (25ns) units (average number of BCs per PhT)
        In random trigger mode, this is the average period."""
        return (self.read(WsTriggerHandlerAddress.SEQ_PT_PERIOD))

    def sequencer_set_trigger_mode_periodic(self, commitTransaction=True):
        """Sets sequencer trigger operating mode to periodic"""
        self.write(data=0, addr=WsTriggerHandlerAddress.SEQ_PT_MODE, commitTransaction=commitTransaction)

    def sequencer_set_trigger_mode_random(self, commitTransaction=True):
        """Sets sequencer trigger operating mode to radnom"""
        self.write(data=1, addr=WsTriggerHandlerAddress.SEQ_PT_MODE, commitTransaction=commitTransaction)

    def sequencer_get_trigger_mode(self):
        """Get Sequencer operating mode; 1=random, 0=periodic"""
        return SeqMode(self.read(WsTriggerHandlerAddress.SEQ_PT_MODE))

    def sequencer_set_number_of_hb_per_timeframe(self, value, commitTransaction=True):
        """Set the number of heartbeat frames per time frame"""
        assert value | 0x1FF == 0x1FF, "Number of HBF per timeframe should be < 512"
        assert value > 0, "0 HB per TF is not possible"
        self.write(WsTriggerHandlerAddress.SEQ_NUM_HB_PER_TF, value, commitTransaction=commitTransaction)

    def sequencer_get_number_of_hb_per_timeframe(self):
        """Get the number of heartbeat frames in a time frame"""
        return self.read(WsTriggerHandlerAddress.SEQ_NUM_HB_PER_TF)

    def set_ignore_trg_in_cont_mode(self, value, commitTransaction=True):
        """Set configuration of Non-HB/EoC trigger handling in continuous mode."""
        assert value | 0x1 == 0x1
        self.write(WsTriggerHandlerAddress.IGNORE_TRG_IN_CONT_MODE, value, commitTransaction)

    def get_ignore_trg_in_cont_mode(self):
        """Get configuration of Non-HB/EoC trigger handling in continuous mode."""
        return self.read(WsTriggerHandlerAddress.IGNORE_TRG_IN_CONT_MODE)

    # Internal Trigger Mask
    def set_internal_trigger_grant(self, value, commitTransaction=True):
        """Set Internal Trigger Mask (1 bit for each Internal Trigger per HB frame)"""
        assert value | 0xFFFFFFFFFFFF == 0xFFFFFFFFFFFF, "value can have at most 48 bits"
        self.write(WsTriggerHandlerAddress.INTERNAL_TRG_GRANT_LSB, (value & 0xFFFF), commitTransaction=False)
        self.write(WsTriggerHandlerAddress.INTERNAL_TRG_GRANT_CSB, ((value >> 16) & 0xFFFF), commitTransaction=False)
        self.write(WsTriggerHandlerAddress.INTERNAL_TRG_GRANT_MSB, (value >> 32), commitTransaction=commitTransaction)

    def get_internal_trigger_grant(self):
        """Get Internal Trigger Mask"""
        msb = self.read(WsTriggerHandlerAddress.INTERNAL_TRG_GRANT_MSB)
        csb = self.read(WsTriggerHandlerAddress.INTERNAL_TRG_GRANT_CSB)
        return (self.read(WsTriggerHandlerAddress.INTERNAL_TRG_GRANT_LSB) | (csb << 16) | (msb << 32))

    def get_debug_fifo(self, commitTransaction=True):
        """Returns the list of data from the debug fifo for the selected fifo"""
        done = False
        ret = []
        while not done:
            self._request_debug_fifo()
            if commitTransaction:
                results = self.board.flush_and_read_results(expected_length=12)
                r = self._format_debug_fifo(results)
                if r['empty']:
                    done=True
                else:
                    del r['empty']
                    ret.append(r)
            else:
                done = True
        return ret

    def _request_debug_fifo(self):
        """WB read request"""
        for i in range(12):
            self.read(WsTriggerHandlerAddress.DEBUG_FIFO, commitTransaction=False)

    def _format_debug_fifo(self, results):
        assert len(results) == 12
        ret = {}

        raw = 0
        for i, data in enumerate(results):
            raw += ((data[1] & 0x7FF) << i*DebugFifoBit.RESERVED)

        next = (raw >> 2*OrbitBC.ORBITBC) & 2**OrbitBC.ORBITBC-1
        error = (raw >> 1*OrbitBC.ORBITBC) & 2**OrbitBC.ORBITBC-1
        prev = (raw >> 0*OrbitBC.ORBITBC) & 2**OrbitBC.ORBITBC-1

        ret['prev_orbit'] = self._get_orbit(prev)
        ret['prev_bc'] = self._get_bc(prev)

        ret['error_orbit'] = self._get_orbit(error)
        ret['error_bc'] = self._get_bc(error)

        ret['next_orbit'] = self._get_orbit(next)
        ret['next_bc'] = self._get_bc(next)

        ret['empty'] = (results[0][1] >> DebugFifoBit.EMPTY) & 1

        return ret

    def _get_orbit(self, orbitbc):
        return (orbitbc >> OrbitBC.BC) & (2**OrbitBC.ORBIT)-1

    def _get_bc(self, orbitbc):
        return orbitbc & (2**OrbitBC.BC)-1
