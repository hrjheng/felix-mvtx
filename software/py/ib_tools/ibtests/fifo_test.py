#!/usr/bin/env python3.9

from .ibtest import *
import userdefinedexceptions

PATTERNS=[
  ('ramp'         ,range(128*32)                          ),
  ('zeros'        ,[0]*(128*32)                           ),
  ('ones'         ,[0xFFFFFF]*(128*32)                    ),
  ('marching'     ,[1<<i for i in range(24)]*171          ),
  ('checker board',[0xAAAAAA,0x555555]*(64*32)            ),
  ('prime'        ,[(i*17)&0xFFFFFF for i in range(128*32)])
]
            
class FIFOTest(IBTest):
    def __init__(self, name="FIFOTest", cru=None, ru_list=None):
        IBTest.__init__(self, name, cru, ru_list)

        self._write_fifo_results_to_file = True
        self._steps = []
        self._ofs = []
        self._step = 0

        self._max_read_tries = 2
        self.n_read_retries = {}
        self.n_fifo_errors = {}
        
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

        ch.setreg_cmu_and_dmu_cfg(PreviousChipID=0x0,
                                  InitialToken=0x1,
                                  DisableManchester=0x1,
                                  EnableDDR=0x1)


    def configure_ru(self, ru):
        self.log.info('No need to configure RU when running '+self.name)
        ru.alpide_control.logger.setLevel(logging.WARNING)

    def configure_cru(self):
        self.log.info('No need to configure CRU when running '+self.name)

    def start_readout(self):
        self.log.info('Omitting starting readout when running '+self.name)

    def stop_readout(self):
        pass

    def start_of_run(self):
        self.log.debug(self.dump_parameters())        
        if self._fpath_out_prefix is not None:
            self.dump_volt_temp(self._fpath_out_prefix+'chip_adcs_SOR.json')
            self.dump_chips_config('SOR')
        
        self.log.info('Starting run ' + self.name)
        
        self._steps = []
        self._ofs = []
        for ru in self.ru_list:
            ch_bc = Alpide(ru, chipid=0xF)
            chips = [Alpide(ru, chipid=chid) for chid in range(8, -1, -1)]
            if self._fpath_out_prefix is None or self._write_fifo_results_to_file is False:
                self.log.info('Output file path not provided or disabled, redirecting test results to /dev/null')
                of = open(os.devnull, 'w')
            else:
                of = open(self._fpath_out_prefix + 'fifo_test_results_{}.txt'.format(ru.name), 'w')
            self._ofs.append(of)
            for pattern in range(len(PATTERNS)):
                self._steps.append([of, pattern, ch_bc])
                for ch in chips:
                    self._steps.append([of, pattern, ch])
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
        for of in self._ofs:
            of.close()
        counter_status = self.print_counters()
        if len(counter_status): self.log.warning(counter_status)
        self.set_return_code(0, 'Done')

        if self._fpath_out_prefix is not None:
            self.dump_volt_temp(self._fpath_out_prefix+'chip_adcs_EOR.json')
            self.dump_chips_config('EOR')

    def run_step(self):
        if self._step < len(self._steps):
            of,ipattern,ch = self._steps[self._step]
            name,pattern=PATTERNS[ipattern]
            if ch.chipid == 0xF:
                self._write_pattern(of,ch,name,pattern)
            else:
                self._read_pattern(of,ch,name,pattern)
            self._step += 1
        return (self._step, len(self._steps))

    def print_counters(self):
        msg = ''
        for counter_name,counter in {'Number of read retries per chip':self.n_read_retries,
                                     'Number of FIFO errors per chip': self.n_fifo_errors}.items():
            if len(counter)==0: continue
            msg += counter_name+' (only if >0):\n'
            msg += ''.join('\t{}: {}\n'.format(k,v) for k,v in counter.items())
        return msg
    
    def _write_pattern(self, of, ch, name, pattern):
        self.log.info('Writing pattern "{}" on stave {} chipID {}'.format(name, ch.board.name, ch.chipid))
        of.write('    writing pattern "{}" on stave {} chipID {}\n'.format(name, ch.board.name, ch.chipid))
        for region in range(32):
            for addr in range(128):
                data=pattern[region*128+addr]
                ch.write_region_reg(region,1,addr,data>> 0&0xFFFF, commitTransaction=False)
                ch.write_region_reg(region,2,addr,data>>16&0x00FF, commitTransaction=False)
        ch.board.flush()

    def _read_region_reg_chip(self, chip, rgn_add, base_add, sub_add):
        ret = -1
        itry = 0
        while ret < 0 and itry < self._max_read_tries:
            itry += 1
            try:
                ret = chip.read_region_reg(rgn_add,base_add,sub_add,commitTransaction=True)
            except userdefinedexceptions.ChipidMismatchError:
                ret = -1
                ch_name = chip.board.name+'_'+str(chip.chipid)
                self.log.warning('Failed to read from chip {} rgn {} base {} sub {} (attempt {}/{})!'
                                 .format(ch_name, rgn_add, base_add, sub_add, itry, self._max_read_tries))
                if ch_name in self.n_read_retries:
                    self.n_read_retries[ch_name] += 1
                else:
                    self.n_read_retries[ch_name] = 1
        return ret

                
    def _read_pattern(self, of, ch, name, pattern):
        self.log.debug('  reading pattern "{}" from stave {} chipID {}'.format(name, ch.board.name, ch.chipid))
        of.write('    reading pattern "{}" from stave {} chipID {}\n'.format(name, ch.board.name, ch.chipid))
        nerr=0
        for region in range(32):
            for addr in range(128):
                data_lo=self._read_region_reg_chip(ch,region,1,addr)
                data_hi=self._read_region_reg_chip(ch,region,2,addr)
                data=(data_hi&0xFF)<<16|data_lo
                if data!=pattern[region*128+addr]:
                    nerr+=1
                    of.write('Error in chip %d, region %d, address 0x%02X: read 0x%06X instead of 0x%06X\n'
                             %(ch.chipid,region,addr,data,pattern[region*128+addr]))
        if nerr==0:
            self.log.info('    -> Chip ID {} OK'.format(ch.chipid))
            of.write('OK: no read back errors\n')
        else:
            self.log.warning('    -> {} errors in chip ID {}'.format(nerr, ch.chipid))
            self.set_return_code(3, 'FIFO errors found')
            ch_name = ch.board.name+'_'+str(ch.chipid)
            if ch_name in self.n_fifo_errors:
                self.n_fifo_errors[ch_name] += nerr
            else:
                self.n_fifo_errors[ch_name] = nerr
