#!/usr/bin/env python3.9

from .ibtest import *

DACS = [
    'VRESETP',
    'VRESETD',
    'VCASP',
    'VCASN',
    'VPULSEH',
    'VPULSEL',
    'VCASN2',
    'VCLIP',
    'VTEMP',
    'IAUX2',
    'IRESET',
    'IDB',
    'IBIAS',
    'ITHR',
]

VDACSel = {
    'VCASN':0,
    'VCASP':1,
    'VPULSEH':2,
    'VPULSEL':3,
    'VRESETP':4,
    'VRESETD':5,
    'VCASN2':6,
    'VCLIP':7,
    'VTEMP':8,
    'ADCDAC':9
    }

CDACSel = {
    'IRESET':0,
    'IAUX2':1,
    'IBIAS':2,
    'IDB':3,
    'IREF':4,
    'ITHR':5,
    'IREFBuffer':6
    }

class DACScan(IBTest):
    def __init__(self, name="DACScan", cru=None, ru_list=None):
        IBTest.__init__(self, name, cru, ru_list)

        self.dac_steps = list(range(256))
        self._data = {}
        self._steps = []
        self._step = 0
        
    def _configure_stave(self, ru):
        ch = Alpide(ru, chipid=0xF) # broadcast
        ch.write_opcode(Opcode.GRST)
        ch.write_opcode(Opcode.PRST)
    
        ch.setreg_mode_ctrl(ChipModeSelector=0x0,
                            EnClustering=0x1,
                            MatrixROSpeed=0x1,
                            IBSerialLinkSpeed=0x2,
                            EnSkewGlobalSignals=0x1,
                            EnSkewStartReadout=0x1,
                            EnReadoutClockGating=0x0,
                            EnReadoutFromCMU=0x0)

        ch.setreg_adc_ctrl(Mode=2,
                           SelInput=0,
                           SetIComp=2,
                           DiscriSign=0,
                           RampSpd=1,
                           HalfLSBTrim=0,
                           CompOut=0)

        ch.setreg_cmu_and_dmu_cfg(PreviousChipID=0x0,
                                  InitialToken=0x1,
                                  DisableManchester=0x1,
                                  EnableDDR=0x1)
        
    def configure_ru(self, ru):
        self.log.info('No need to configure RU when running '+self.name)

    def configure_cru(self):
        self.log.info('No need to configure CRU when running '+self.name)

    def start_readout(self):
        self.log.info('Omitting starting readout when running '+self.name)

    def stop_readout(self):
        pass

    def start_of_run(self):
        assert self._fpath_out_prefix is not None, 'Output files path needed'

        self.log.debug(self.dump_parameters())        
        if self._fpath_out_prefix is not None:
            self.dump_volt_temp(self._fpath_out_prefix+'chip_adcs_SOR.json')
            self.dump_chips_config('SOR')
        
        self.log.info('Starting run ' + self.name)
        
        # data{staveID}{chipID}{dac}{avdd/dac}[step]
        self._data = {ru.name:{chipid:{dac:{'AVDD':[], 'Value':[]} for dac in DACS} for chipid in range(9)} for ru in self.ru_list}
        self._data['STEPS'] = self.dac_steps
        self._steps = []
        for ru in self.ru_list:
            ch_bc = Alpide(ru, chipid=0xF)
            chips = [Alpide(ru, chipid=chid) for chid in range(9)]
            for idac in range(len(DACS)):
                self._steps.append([idac, [], ch_bc, []]) # conf dacs signal
                for steps in [self.dac_steps[i:i+64] for i in range(0, len(self.dac_steps), 64)]:
                    self._steps.append([idac, steps, ch_bc, chips])
        self._step = 0
        
        self._run_start_time = time.time()
        self._running = True

    def start_of_trigger(self):
        pass

    def end_of_trigger(self):
        pass

    def end_of_run(self):
        self._running = False
        self._run_end_time = time.time()
        self.log.info(self.name+' finished in {:.2f}s'.format(self._run_end_time-self._run_start_time) )
        with open(self._fpath_out_prefix + 'dac_scan_results.json', 'w') as of:
            json.dump(self._data, of, indent=4)
        self.set_return_code(0, 'Done')

        if self._fpath_out_prefix is not None:
            self.dump_volt_temp(self._fpath_out_prefix+'chip_adcs_EOR.json')
            self.dump_chips_config('EOR')

    def run_step(self):
        if self._step < len(self._steps):
            idac,steps,ch_bc,chips=self._steps[self._step]
            if len(steps)==0:
                self.log.info('Stave {}, reseting DACs to nominal values'.format(ch_bc.board.name))
                self._configure_dacs(ch_bc) # the same power consumption during the measuremnt of each dac
                time.sleep(1) # settle currents
            else:
                self.log.info('Stave {}, DAC {}, steps {}..{}'
                              .format(ch_bc.board.name, DACS[idac], steps[0], steps[-1]))
                for step in steps:
                    self._measure_dac_step(ch_bc, chips, idac, step)
            self._step += 1
        return (self._step, len(self._steps))
        
    def _configure_dacs(self, ch):
        # set dacs to a default value (taken from new-alpide-software)
        ch.write_reg(address=0x601, data=0x0a)
        ch.write_reg(address=0x602, data=0x93)
        ch.write_reg(address=0x603, data=0x56)
        ch.write_reg(address=0x604, data=0x32)
        ch.write_reg(address=0x605, data=0xaa)
        ch.write_reg(address=0x606, data=0x6a)
        ch.write_reg(address=0x607, data=0x39)
        ch.write_reg(address=0x608, data=0x00)
        ch.write_reg(address=0x609, data=0xc8)
        ch.write_reg(address=0x60a, data=0x65)
        ch.write_reg(address=0x60b, data=0x65)
        ch.write_reg(address=0x60c, data=0x1d)
        ch.write_reg(address=0x60d, data=0x40)
        ch.write_reg(address=0x60e, data=0x32)


    def _measure_dac_step(self, ch_bc, chips, idac, step):
        dac = DACS[idac]
        dac_addr = 0x601+idac
        adc_input = 5 if dac_addr<0x60A else 6 # DACMONV or DACMONI
        ch_bc.write_reg(dac_addr, step)
        ch_bc.setreg_analog_monitor_and_override(
            VoltageDACSel=VDACSel[dac] if dac in VDACSel.keys() else 0,
            CurrentDACSel=CDACSel[dac] if dac in CDACSel.keys() else 0,
            SWCNTL_DACMONI=0,SWCNTL_DACMONV=0,IRefBufferCurrent=1)
        for k,sel_input in [['Value',adc_input], ['AVDD',2]]: # measure AVDD and DAC
            ch_bc.setreg_adc_ctrl(Mode=0,SelInput=sel_input,SetIComp=2,RampSpd=1,
                                  DiscriSign=0,HalfLSBTrim=0,CompOut=0)
            ch_bc.setreg_cmd(0xFF20) # ADCMEASURE
            ch_bc.board.wait(int(160e6*0.01)) # wait >=5ms, according to ALPIDE manual
            for ch in chips: self._data[ch.board.name][ch.chipid][dac][k].append(ch.read_reg(0x613))
        
