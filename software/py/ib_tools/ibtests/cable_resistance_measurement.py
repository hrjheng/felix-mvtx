#!/usr/bin/env python3.9

from .ibtest import *


class CableResistanceMeasurement(IBTest):
    def __init__(self, name="CableResistanceMeasurement", cru=None, ru_list=None):
        IBTest.__init__(self, name, cru, ru_list)
        self.pu_values = {}
        self.chip_values = {}
        self._steps = []
        self._step = 0
        self.avdd = 1.65
        self.dvdd = 1.65

    def set_supply_voltage(self, dvdd, avdd):
        self.log.warning('Setting supplied voltage not allowed in '+self.name)

    def configure_stave(self, istave):
        assert istave in range(len(self.ru_list))
        ru = self.ru_list[istave]
        self.log.info('Configuring stave '+ru.name)

        if self.handle_power:
            pu,m = self._ru_to_pu[ru]
            pu.adjust_output_voltage(module=m, dvdd=self.dvdd, avdd=self.avdd)
            self.log.info('Supply voltages set to AVDD: {} V, DVDD: {} V'.format(self.avdd, self.dvdd))
        else:
            self.log.warning('Make sure AVDD and DVDD are set to 1.65 V otherwise this test might not work properly!')

        ch = Alpide(ru, chipid=0xF) # broadcast
        ch.write_opcode(Opcode.GRST)
        ch.write_opcode(Opcode.PRST)
        ch.setreg_mode_ctrl(1,1,1,2,1,1,0,0) # disable clock gating
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
        assert self.handle_power, \
            f"{self.name} requires control of PU to run! Execute with '--handle_power' (or equivalent)"
        self.pu_values = {}
        self.chip_values = {}
        self._steps = []
        for ru in self.ru_list:
            self.pu_values[ru.name] = {'dv':[0.,0.], 'av':[0.,0.], 'di':[0.,0.], 'ai':[0.,0.]}
            self.chip_values[ru.name] = {i:{'dv':[0.,0.], 'av':[0.,0.]} for i in list(range(9))+['avg']}
            self._steps.append([ru,0])
            self._steps.append([ru,1])
        self._step = 0
        for ru in self.ru_list:
            pu,module = self._ru_to_pu[ru]
            self.log.info(f"Setting PU_{ru.name} current thresholds to I_d = 1.7 A, I_a = 0.5 A")
            pu.configure_analog_current_threshold(module=module, current_code=pu._ith_to_code(ith=0.5))
            pu.configure_digital_current_threshold(module=module, current_code=pu._ith_to_code(ith=1.7))
        self._running = True

    def start_of_trigger(self):
        pass

    def end_of_trigger(self):
        pass

    def end_of_run(self):
        self._running = False
        for ru in self.ru_list:
            pu,module = self._ru_to_pu[ru]
            self.log.info(f"Sending GRST to {ru.name}")
            Alpide(ru, chipid=0xF).write_opcode(Opcode.GRST)
            ru.wait(int(160e6*0.01))
            self.log.info(f"Setting PU_{ru.name} current thresholds to I_d = 1.3 A, I_a = 0.3 A")
            pu.configure_analog_current_threshold(module=module, current_code=pu._ith_to_code(ith=0.3))
            pu.configure_digital_current_threshold(module=module, current_code=pu._ith_to_code(ith=1.3))
        res = {}
        for ru in self.ru_list:
            r = {i:{} for i in ['avg'] + [c for c in range(9)]}
            for i in r.keys():
                for s in ['d', 'a']:
                    r[i][s+'vdd'] = round(1000.*(self.chip_values[ru.name][i][s+'v'][0]-self.chip_values[ru.name][i][s+'v'][1])
                                          /(self.pu_values[ru.name][s+'i'][1]-self.pu_values[ru.name][s+'i'][0]), 3)

            self.log.debug( 'Rel:    DVDD = {:.3f} R   AVDD = {:.3f} R'.format( r['avg']['dvdd'], r['avg']['avdd'] ) )
            for i in range(9):
                self.log.debug( 'Chip {:d}: DVDD = {:.3f} R   AVDD = {:.3f} R'.format(i, r[i]['dvdd'], r[i]['avdd']) )
            res[ru.name] = r['avg']
            self.log.info('Stave {} cable resistance: {}'.format(ru.name,r['avg']))
        self.log.info('Cable resistance measurement results\n' + json.dumps(res, indent=4))
        if self._fpath_out_prefix is not None:
            with open(self._fpath_out_prefix+'cable_resistances.json', 'w') as jsonfile:
                json.dump(res, jsonfile, indent=4)
        self.set_return_code(0, 'Done')

    def run_step(self):
        if self._step >= len(self._steps):
            self.log.warning('All steps completed, nothing to do!')
            return (self._step, len(self._steps))
        else:
            self.log.info('Running step {}/{}'.format(self._step, len(self._steps)))
            ru,istep = self._steps[self._step]
            self._measure_cable_resistance_ru_step(ru, istep)
            self._step += 1
            return (self._step, len(self._steps))

    def _measure_cable_resistance_ru_step(self, ru, istep):
        assert istep in [0,1]
        ch_bc = Alpide(ru, chipid=0xF)
        pu,module = self._ru_to_pu[ru]
        if istep==0:
            ch_bc.setreg_IBIAS(0) # get as little analogue current as possible
        elif istep==1:
            ch_bc.setreg_dtu_cfg(1,1,0,8,0,0) # turn on PLL
            ch_bc.setreg_dtu_dacs(8,15,15) # get as much digital current as possible
            ch_bc.setreg_IBIAS(100)
        ru.flush()
        time.sleep(2) # allow the system to settle
        meas = pu.get_power_adc_values(module)
        for s in ['d', 'a']:
            self.pu_values[ru.name][s+'v'][istep] = pu._code_to_vpower(meas['%svdd_voltage'%s])
            self.pu_values[ru.name][s+'i'][istep] = pu._code_to_i(meas['%svdd_current'%s])
        self.log.debug(ru.name + ' ' + str(self.pu_values[ru.name]))
        chid_list = [i for i in range(9) if ru.name not in self.exclude_gth_dict or i not in self.exclude_gth_dict[ru.name]]
        vadc_all = measure_voltage_temp_stave(ru, chipids=chid_list, only_inputs=['AVSS', 'DVSS', 'AVDD', 'DVDD'])
        chid_list.reverse()
        for chid in chid_list:
            vadc = vadc_all['CHIP_{:02d}'.format(chid)]
            vadc = {k:1.*sum(v)/len(v) for k,v in vadc.items() if len(v)}
            for s in ['dv', 'av']:
                self.chip_values[ru.name][chid][s][istep] = 2.*0.823e-3*(vadc[s.upper()+'DD']-vadc[s.upper()+'SS'])
                self.chip_values[ru.name]['avg'][s][istep] += self.chip_values[ru.name][chid][s][istep]
        for s in ['dv', 'av']:
            self.chip_values[ru.name]['avg'][s][istep] /= float(len(chid_list))
        self.log.debug(ru.name + ' ' + str(self.chip_values[ru.name]['avg']))
