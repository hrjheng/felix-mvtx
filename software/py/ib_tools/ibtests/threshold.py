#!/usr/bin/env python3.9

from .ibtest import *

class ThresholdScan(IBTest):
    def __init__(self, name="ThresholdScan", cru=None, ru_list=None):
        IBTest.__init__(self, name, cru, ru_list)

        self.ninj = 25
        self.start_charge = 0
        self.stop_charge = 50
        self._rows = list(range(512))
        self._last_irow = 0

        self._min_trigger_distance_ns = 3564*25 # ns
        self.trigger_mode = TriggerMode.TRIGGERED
        self.set_trigger_period(self._min_trigger_distance_ns) # Hz
        self.trigger_source = trigger_handler.TriggerSource.SEQUENCER
        self._min_trg_dist = round(self._min_trigger_distance_ns/6.25)
        self._inj_ntrg = self.trigger_source == trigger_handler.TriggerSource.SEQUENCER
        self._trg_seq_hb_per_tf = self.ninj
        self._trg_seq_hba_per_tf = self.ninj
        self.send_pulses = True
        

    def set_min_trigger_distance(self, min_trigger_distance_ns):
        self._min_trigger_distance_ns = min_trigger_distance_ns
        self._min_trg_dist = round(self._min_trigger_distance_ns/6.25) # clock cycles
        self.set_trigger_period(self._min_trigger_distance_ns) # Hz
        

    def _configure_stave(self, ru):
        ch = Alpide(ru, chipid=0xF) # broadcast
        configure_chip(ch, linkspeed=self.link_speed,
                       strobe_duration_ns=10e3,
                       pulse_duration_ns=5e3,
                       analogue_pulsing=1)
        configure_dacs(ch, self.vbb)
        
        
    def _scan_row(self, irow):
        self.log.debug('Row {:d}'.format(self._rows[irow]))
        for ru in self.ru_list: # unmask row
            ch = Alpide(ru, chipid=0xF)
            ch.unmask_row(self._rows[irow])
            ch.pulse_row_enable(self._rows[irow])
            self._configure_masked_pixels(ru)
            time.sleep(self._min_trigger_distance_ns*1e-9)
            
        for dv in range(self.start_charge, self.stop_charge):
            for ru in self.ru_list:
                ch = Alpide(ru, chipid=0xF)
                ch.setreg_VPULSEL(170-dv)
                # Sets the data into the calibration lane (Calibration Data Word = CDW)
                # From private discussion between @freidt and @mlupi
                # Maskstage (row) in the 15:0 and setting in 31:16, 47:32 reserved for future use.
                reserved  = (0    & 0xFFFF)<<32
                settings  = (dv   & 0xFFFF)<<16
                maskstage = (irow & 0xFFFF)<<0
                cdw_user_field = reserved | settings | maskstage
                ru.calibration_lane.set_user_field(cdw_user_field)
                ru.calibration_lane.read(0) # waits for all commands to be executed before advancing
                time.sleep(self._min_trigger_distance_ns*1e-9)

            if self._inj_ntrg:
                for ru in self.ru_list:
                    ru.trigger_handler.sequencer_set_number_of_timeframes(1)
                done = False
                while not done:
                    done = True
                    time.sleep(self.ninj*self._min_trigger_distance_ns*1e-9)
                    for ru in self.ru_list:
                        done &= ru.trigger_handler.sequencer_is_done_timeframes()
                time.sleep(self.ninj*self._min_trigger_distance_ns*1e-9)
            else:
                for _ in range(self.ninj):
                    self.ltu.send_physics_trigger()
                    time.sleep(self._min_trigger_distance_ns*1e-9)
            self.triggers_sent+=self.ninj
            time.sleep(self._min_trigger_distance_ns*1e-9)

        for ru in self.ru_list: # mask row
            ch = Alpide(ru, chipid=0xF)
            ch.mask_row(self._rows[irow])
            ch.pulse_row_disable(self._rows[irow])
            time.sleep(self._min_trigger_distance_ns*1e-9)

        
    def run(self):
        self.log.info('Starting threshold scan with Nrows={:d}, Charge={:d}..{:d}, Ninj={:d}'
                      .format(len(self._rows), self.start_charge, self.stop_charge, self.ninj) )
        start_time = time.time()
        while True:
            step,total_steps = self.run_step(32)
            if step >= total_steps:
                break
        dur = time.time()-start_time
        self.log.info('Threshold scan completed in {:.2f}s. Total triggers sent: {:d}'
                      .format(dur, self.triggers_sent))


    def run_step(self, nrows=8):
        irow_start = self._last_irow
        irow_end   = irow_start + nrows
        if irow_end > len(self._rows): irow_end = len(self._rows)
        self._last_irow = irow_end
        self.log.info('Rows {:d}..{:d}'.format(irow_start, irow_end))
        self.log_during_run('RUN_STEP: Rows {:d}..{:d}'.format(irow_start, irow_end))
        for irow in range(irow_start, irow_end):
            self._scan_row(irow)
        return (self._last_irow, len(self._rows))

    
