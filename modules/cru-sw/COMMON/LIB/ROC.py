import sys
import time
from time import sleep

import libO2ReadoutCard


class Roc:
    def openROC(self, pcie_id, bar_ch, debug=None):
        if debug is None:
            self._roc = libO2ReadoutCard.BarChannel(pcie_id, bar_ch)
        else:
            print('Open ROC')

    def rocWr(self, reg, data, debug=None):
        if debug is None:
            self._roc.register_write(reg, data)
        else:
            print('SCA WR ', hex(data))

    def rocRd(self, reg, debug=None):
        if debug is None:
            return self._roc.register_read(reg)
        else:
            return 0

    def resetCRU(self, debug=None):
        if debug is None:
            self._roc.register_write(0x400, 0x3)
        else:
            print('RESET CRU')
