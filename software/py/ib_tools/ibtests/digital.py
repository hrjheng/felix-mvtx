#!/usr/bin/env python3.9

from .ibtest import *

class DigitalScan(IBTest):
    def __init__(self, name="DigitalScan", cru=None, ru_list=None):
        IBTest.__init__(self, name, cru, ru_list)

        self.ninj = 9 # number of pulses per configuration
        self.nregions = 8 # number of regions to be pulsed per iteration, must be divisor of 32
        self.pulse_mode = 0 # 0 for digital 1 for analogue
        self.charge = 100 # in analogue pulsing

        self.trigger_mode = TriggerMode.TRIGGERED
        self.set_trigger_period(3564*25) # Hz
        self.trigger_source = trigger_handler.TriggerSource.SEQUENCER
        self.send_pulses = True

        self._bc_chips = []
        self._steps = []
        self._step = 0
        
    def _configure_stave(self, ru):
        ch = Alpide(ru, chipid=0xF) # broadcast
        configure_chip(ch, linkspeed=self.link_speed,
                       strobe_duration_ns=10e3,
                       pulse_duration_ns=5e3,
                       analogue_pulsing=self.pulse_mode)
        configure_dacs(ch, self.vbb)
        ch.setreg_VPULSEL(170-self.charge)


    def start_of_run(self):
        self._bc_chips = [Alpide(ru, chipid=0xF) for ru in self.ru_list]
        self._steps = []
        for regions in [range(self.nregions*r,self.nregions*(r+1)) for r in range(int(32/self.nregions))]:
            self._steps.append(regions) 
            for meb_mask in [0b001, 0b010, 0b100, 0b111]:
                self._steps.append(meb_mask)
        self._step = 0
        IBTest.start_of_run(self)
        
    def run_step(self):
        if self._step < len(self._steps):
            if type(self._steps[self._step]) is range:
                regions = self._steps[self._step]
                self.log.info('Enabling regions in {}, disabling others'.format(regions))
                for ch in self._bc_chips:
                    for region in range(32):
                        ch._region_control_register_set_double_column(
                            region,0x0000 if region in regions else 0xFFFF)
                self.log_during_run('RUN_STEP')
            else:
                self._process_meb_mask(self._steps[self._step])
            self._step += 1
        return (self._step, len(self._steps))


    def _process_meb_mask(self, meb_mask):
        self.log.info('MEB mask {:03b}'.format(meb_mask))
        for ch in self._bc_chips:
            ch.setreg_fromu_cfg_1(MEBMask=meb_mask, EnStrobeGeneration=0, EnBusyMonitoring=0,
                                  PulseMode=self.pulse_mode, EnPulse2Strobe=1,
                                  EnRotatePulseLines=0, TriggerDelay=0)
        for pulsing in ['pulse_all_pixels_enable()', 'pulse_all_pixels_disable()']:
            for masking in ['unmask_all_pixels()', 'mask_all_pixels()']:
                for ch in self._bc_chips:
                    exec('ch.'+pulsing)
                    exec('ch.'+masking)
                    ch.write_opcode(Opcode.PRST)
                for _ in range(self.ninj):
                    for ru in self.ru_list:
                        ru.trigger_handler.sequencer_set_number_of_timeframes(1)
                    done = False
                    while not done:
                        done = True
                        for ru in self.ru_list:
                            done &= ru.trigger_handler.sequencer_is_done_timeframes()
                    time.sleep(0.01) # make sure all the data gets through
                    self.triggers_sent+=1
