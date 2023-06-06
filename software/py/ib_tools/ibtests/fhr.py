#!/usr/bin/env python3.9

from .ibtest import *

class FakeHitRate(IBTest):
    def __init__(self, name="FakeHitRate", cru=None, ru_list=None):
        IBTest.__init__(self, name, cru, ru_list)

        self.duration = 300 # s
        self.set_trigger_period(3564*25/2) # ns 3564*25 ns -> 11 kHz
        self.trigger_mode = TriggerMode.CONTINUOUS
        self.trigger_source = trigger_handler.TriggerSource.SEQUENCER
        self.send_pulses = False
        
    def _configure_stave(self, ru):
        ch = Alpide(ru, chipid=0xF) # broadcast
        configure_chip(ch, linkspeed=self.link_speed,
                       strobe_duration_ns=self.trigger_period-200,
                       pulse_duration_ns=self.trigger_period*0.5, # not relevant
                       pulse2strobe=self.send_pulses,
                       analogue_pulsing=1)
        configure_dacs(ch, self.vbb)
        ch.unmask_all_pixels()

class FakeHitRateWithPulsing(FakeHitRate):
    def __init__(self, name="FakeHitRateWithPulsing", cru=None, ru_list=None):
        FakeHitRate.__init__(self, name, cru, ru_list)

        self.duration = 30 # s
        self.set_trigger_period(3564*25/2) # ns
        self.send_pulses = True
        
    def _configure_stave(self, ru):
        IBTest._configure_stave(self, ru)

        ch = Alpide(ru, chipid=0xF)
        ch.setreg_VPULSEL(160)
        configure_chip_mask(ch, 'QUARTER_ROW', pulsing=True, masking=False)
