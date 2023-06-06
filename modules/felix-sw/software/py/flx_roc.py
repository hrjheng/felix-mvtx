import libflxcard_py
import time

class Roc:
    def __init__(self):
        self._roc = None

    def set_roc(self, roc):
        self._roc = roc

    def open_card(self, card_nr=0, lock_mask=0):
        self._roc = libflxcard_py.flxcard()
        self._roc.card_open(card_nr, lock_mask)

    def roc_write(self, reg, data):
        self._roc.register_write(reg, data)

    def roc_read(self, reg):
        return self._roc.register_read(reg)

    def roc_rmw(self, addr, pos, width, value):
        """ Read-Modify-Write width number of bit """
        mask = (pow(2, width) - 1) << pos
        data0 = self.roc_read(addr)
        data1 = (data0 & ~mask) | ((value << pos) & mask)
        self.roc_write(addr, data1)

    def mid(self, data, pos, width):
        mask = pow(2, width) - 1
        result = (data >> pos) & mask
        return result

    def wait_for_bit(self, address, position, value):
        """ Waits for a single bit until timeout (500 ms) """
        t0 = time.time()
        timeout = t0 + 0.5  # 500 ms timout

        while True:
            data = self.roc_read(address)
            bit = self.mid(data, position, 1)
            if (bit == value):
                break

            if (time.time() >= timeout):
                return(-1)

        return bit

    def resetDMA(self, debug=None):
        if debug is None:
            pass
        else:
            print('RESET FELIX DMA')

    def resetSOFT(self, debug=None):
        if debug is None:
            pass
        else:
            print('RESET FELIX SOFT')

    def resetREG(self, debug=None):
        if debug is None:
            pass
        else:
            print('RESET FELIX REGISTER')

    def reset_flx(self, debug=None):
        self.resetREG(debug=debug)
        self.resetDMA(debug=debug)
        self.resetSOFT(debug=debug)