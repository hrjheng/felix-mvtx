#!/usr/bin/env python3.9

from .ibtest import *

class ReadoutTest(IBTest):
    def __init__(self, name="ReadoutTest", cru=None, ru_list=None):
        IBTest.__init__(self, name, cru, ru_list)
        
        self._stop_on_ru_counter_errors = False
        self._logging_period = 10
        self.duration = 0 # s
        self.readout_test_chip_mask = 'CLUSTERS_128'
        self.set_trigger_period(3564*25/9) # ns
        self.trigger_mode = TriggerMode.CONTINUOUS
        self.trigger_source = trigger_handler.TriggerSource.SEQUENCER
        self.send_pulses = True

    def setup_json(self, config_string):
        conf = json.loads(config_string)
        assert type(conf) is dict, self.name+' JSON config string must be a dict!'
        if 'readout_test_chip_mask' in conf:
            self.readout_test_chip_mask = conf['readout_test_chip_mask']
        if 'trigger_period' in conf:
            self.set_trigger_period(conf['trigger_period'])
        if 'trigger_frequency' in conf:
            available_freq = {44.9: 4, 101: 9, 202:18}
            assert conf['trigger_frequency'] in available_freq, \
                "Only following frequency values allowed: "+str(available_freq.keys())
            self.set_trigger_period(3564*25/available_freq[conf['trigger_frequency']])
        if 'duration' in conf:
            self.duration = conf['duration']
        if 'stop_on_ru_counter_errors' in conf:
            self._stop_on_ru_counter_errors = conf['stop_on_ru_counter_errors']
        if 'dvdd' in conf:
            assert 1.62 < conf['dvdd'] < 1.98
            self.dvdd = conf['dvdd']
        self.log.info('Specific setup applied by parsing '+str(conf))
        
    def _configure_stave(self, ru):
        ch = Alpide(ru, chipid=0xF) # broadcast
        configure_chip(ch, linkspeed=self.link_speed,
                       strobe_duration_ns=self.trigger_period-200,
                       pulse_duration_ns=self.trigger_period*0.5-100,
                       analogue_pulsing=0,
                       pulse2strobe=1,
                       chargepump=15)
        configure_dacs(ch, self.vbb)
        ch.setreg_VPULSEL(170-100)
        configure_chip_mask(ch, self.readout_test_chip_mask)



class ReadoutTestDynamicPreparation(ReadoutTest):
    def __init__(self, name="ReadoutTestDynPre", cru=None, ru_list=None):
        ReadoutTest.__init__(self, name, cru, ru_list)
        self._stop_on_ru_counter_errors = False
        self.duration = 10
        self._iru = 0

    def run_step(self):
        ret = IBTest.run_step(self)
        if ret[0]>=ret[1]:
            if self._iru < len(self.ru_list):
                ru = self.ru_list[self._iru]
                self.log.info(f"Compensating dynamic voltage drop on stave {ru.name}")
                self.log_during_run("BeforeVoltageDropComp"+ru.name, True)
                self.compensate_voltage(ru)
                self.log_during_run("AfterVoltageDropComp"+ru.name, True)
                self._iru += 1
            ret = (self._iru, len(self.ru_list)) 
        return ret



class ReadoutTestDynamicRunning(ReadoutTest):
    def __init__(self, name="ReadoutTestDynRun", cru=None, ru_list=None):
        ReadoutTest.__init__(self, name, cru, ru_list)

    def configure_stave(self, istave):
        assert istave in range(len(self.ru_list))
        ru = self.ru_list[istave]
        self.log.info('Configuring stave '+ru.name)
        ch = Alpide(ru, chipid=0xF) # broadcast
        ch.write_opcode(Opcode.RORST)
        ch.write_opcode(Opcode.BCRST)
