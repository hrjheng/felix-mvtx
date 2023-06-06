#!/usr/bin/env python3.9

from .ibtest import *

class FelixFakeHitRate(IBTest):
    def __init__(self, name="FelixFakeHitRate", cru=FLX, ru_list=None):
        IBTest.__init__(self, name, cru, ru_list)

        self.duration = 300 # s
        # set to ~10us
        self.set_trigger_period(3564*25/9) # ns 3564*25 ns -> 11 kHz
        self.trigger_mode = TriggerMode.CONTINUOUS
        self.trigger_source = trigger_handler.TriggerSource.GBTx2
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
