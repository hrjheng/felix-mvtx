#!/usr/bin/env python3.9

from .ibtest import *

class ReadWrite(IBTest):
    def __init__(self, name="ReadWrite", cru=None, ru_list=None):
        IBTest.__init__(self, name, cru, ru_list)
        self._steps = []
        self._step = 0

    def _check_write(self,ru):
        pu,module = self._ru_to_pu[ru]
        time.sleep(0.5)
        last_curr = round(pu._code_to_i(pu.get_power_adc_values(module)['avdd_current']),1)
        self.log.info(f"Testing write on {ru.name}, initial current {last_curr} mA")
        for i in range(9):
            Alpide(ru, chipid=i).setreg_IBIAS(1)
            time.sleep(0.5)
            curr = round(pu._code_to_i(pu.get_power_adc_values(module)['avdd_current']),1)
            delta = round(last_curr-curr,1)
            last_curr = curr
            self.log.info(f" ... chip {i} IBIAS=1, new current = {curr} mA, delta = {delta} mA")
            if abs(delta)<5:
                self.log.warning(f" ... delta lower than expected!")
                self.set_return_code(5, f"Write failed for {ru.name}_c{i}")

    def _check_read(self,ru):
        self.log.info(f"Testing read on {ru.name}")
        for i in range(9):
            ch = Alpide(ru, chipid=i)
            setval = 64+i
            ch.setreg_IBIAS(setval)
            ch.board.wait(int(160e6*0.01))
            getval = ch.getreg_IBIAS()[0]
            self.log.info(f" ... chip {i} IBIAS set to {setval}, read back {getval}")
            if getval != setval:
                self.log.warning(f" ... set and get value mismatch!")
                self.set_return_code(6, f"Read failed for {ru.name}_c{i}")
                

    def configure_stave(self, istave):
        assert istave in range(len(self.ru_list))
        ru = self.ru_list[istave]
        self.log.info('Configuring stave '+ru.name)

        ch = Alpide(ru, chipid=0xF) # broadcast
        ch.write_opcode(Opcode.GRST)
        ch.write_opcode(Opcode.PRST)
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
        self._steps = []
        for ru in self.ru_list:
            self._steps.append((ru, self._check_write))
            self._steps.append((ru, self._check_read))
        self._step = 0
        self.log.info(f"{self.name} test starting")
        self._running = True

    def start_of_trigger(self):
        pass

    def end_of_trigger(self):
        pass

    def end_of_run(self):
        self._running = False
        self.log.info("Run finished")
        if self.get_return_code()==0:
            self.set_return_code(0, 'Done')
    
    def run_step(self):
        if self._step >= len(self._steps):
            self.log.warning('All steps completed, nothing to do!')
            return (self._step, len(self._steps))
        else:
            self.log.info('Running step {}/{}'.format(self._step, len(self._steps)))
            ru,cmd = self._steps[self._step]
            cmd(ru)
            self._step += 1
            return (self._step, len(self._steps))
