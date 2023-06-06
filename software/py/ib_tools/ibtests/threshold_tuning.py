#!/usr/bin/env python3.9

from .ibtest import *
from .threshold import ThresholdScan

class ThresholdTuning(ThresholdScan):
    def __init__(self, name="ThresholdTuning", cru=None, ru_list=None):
        ThresholdScan.__init__(self, name, cru, ru_list)

        self._ithr_list  = list(range(40, 60, 5))
        self._vcasn_list = list(range(50, 70, 5))
        self._vcasn_ithr_list = None
        self.set_vcasn_ithr_list()
        self._rows = [1,2, 254,255, 509,510]
        self._last = 0


    def set_vcasn_ithr_list(self, ithr_list=None, vcasn_list=None):
        if type(ithr_list) in [tuple, list]:
            self._ithr_list = ithr_list
            self.log.info('ITHR tuning list set to {}'.format(self._ithr_list))
        if type(vcasn_list) in [tuple, list]:
            self._vcasn_list = vcasn_list
            self.log.info('VCASN tuning list set to {}'.format(self._vcasn_list))
        self._vcasn_ithr_list = [[v,i] for v in self._vcasn_list for i in self._ithr_list]

        
    def set_bias_voltage(self, vbb):
        ThresholdScan.set_bias_voltage(self, vbb)
        if self.vbb == -3:
            self.set_vcasn_ithr_list(vcasn_list=list(range(100, 120, 5)) )
        elif self.vbb == -1:
            self.set_vcasn_ithr_list(vcasn_list=list(range(65, 85, 5)) )
        elif self.vbb == 0:
            self.set_vcasn_ithr_list(vcasn_list=list(range(50, 70, 5)) )
        else:
            raise ValueError('VCASN tuning list must be set manually for the selected VBB ({})!'.format(vbb))

            
    def run_step(self):
        if self._last < len(self._vcasn_ithr_list):
            if self._last_irow == 0:
                vcasn,ithr = self._vcasn_ithr_list[self._last]
                self.log.info('Threshold tuning step {} of {}: VCASN {}, ITHR {}'
                              .format(self._last, len(self._vcasn_ithr_list), vcasn, ithr))
                self.configure_vcasn_ithr_all_chips(vcasn, ithr)
            ThresholdScan.run_step(self)
        if self._last_irow >= len(self._rows):
            self._last_irow = 0
            self._last += 1
        return (self._last, len(self._vcasn_ithr_list))


    def run(self):
        self.log.info('Starting threshold tuning of {:d} VCASN/ITHR steps with Nrows={:d}, Q={:d}..{:d}, Ninj={:d}'
                      .format(len(self._vcasn_ithr_list), len(self._rows), self.start_charge, self.stop_charge, self.ninj) )
        start_time = time.time()
        while True:
            step,total_steps = self.run_step()
            if step >= total_steps:
                break
        dur = time.time()-start_time
        self.log.info('Threshold tuning completed in {:.2f}s. Total triggers sent: {:d}'
                      .format(dur, self.triggers_sent))