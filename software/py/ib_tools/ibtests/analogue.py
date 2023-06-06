#!/usr/bin/env python3.9

from .ibtest import *

class AnalogueScan(IBTest):
    def __init__(self, cru=None, ru_list=None):
        IBTest.__init__(self, "AnalogueScan", cru, ru_list)

        self.ninj = 9
        self.charge = 70
        self.rows = list(range(512))
        self._last_irow = 0
        
        self._min_trigger_distance_ns = 3564*25 # ns
        self.trigger_mode = TriggerMode.TRIGGERED
        self.set_trigger_period(self._min_trigger_distance_ns) # Hz
        self.trigger_source = trigger_handler.TriggerSource.SEQUENCER
        self._trg_seq_hb_per_tf = self.ninj
        self._trg_seq_hba_per_tf = self.ninj
        self.send_pulses = True
        
    def _configure_stave(self, ru):
        ch = Alpide(ru, chipid=0xF) # broadcast
        configure_chip(ch, linkspeed=self.link_speed,
                       strobe_duration_ns=10e3,
                       pulse_duration_ns=5e3,
                       analogue_pulsing=1)
        configure_dacs(ch, self.vbb)
        ch.setreg_VPULSEL(170-self.charge)
        ch.unmask_all_pixels()
        
    def run_step(self, nrows=512):
        irow_start = self._last_irow
        irow_end   = irow_start + nrows
        if irow_end > len(self.rows): irow_end = len(self.rows)
        self._last_irow = irow_end
        self.log.info('Rows {:d}..{:d}'.format(irow_start, irow_end))
        bc_chips = [Alpide(ru, chipid=0xF) for ru in self.ru_list]
        for irow in range(irow_start, irow_end):
            for ch in bc_chips:
                ch.pulse_row_enable(self.rows[irow])
                    
            for ru in self.ru_list:
                ru.trigger_handler.sequencer_set_number_of_timeframes(1)
                done = False
                while not done:
                    done = True
                    time.sleep(self.ninj*self._min_trigger_distance_ns*1e-9)
                    for ru in self.ru_list:
                        done &= ru.trigger_handler.sequencer_is_done_timeframes()
                time.sleep(self.ninj*self._min_trigger_distance_ns*1e-9)
                self.triggers_sent+=self.ninj

            for ch in bc_chips:
                ch.pulse_row_disable(self.rows[irow])

        return (self._last_irow, len(self.rows))

