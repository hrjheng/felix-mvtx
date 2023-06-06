import time
import libO2ReadoutCard


class Roc:
    """WP10 provided wrapper class for libO2ReadoutCard"""
    def __init__(self):
        self._roc = None

    def set_roc(self, roc):
        self._roc = roc

    def open_roc(self, pcie_id, bar_ch):
        self._roc = libO2ReadoutCard.BarChannel(pcie_id, bar_ch)

    def roc_write(self, reg, data):
        self._roc.register_write(reg, data)

    def roc_read(self, reg):
        return self._roc.register_read(reg)

    def reset_cru(self):
        self._roc.register_write(0x400, 0x3)

    def mid(self, data, pos, width):
        mask = pow(2, width) - 1
        result = (data >> pos) & mask
        return result

    def roc_rmw(self, addr, pos, width, value):
        """ Read-Modify-Write width number of bit """
        mask = (pow(2, width) - 1) << pos
        data0 = self.roc_read(addr)
        data1 = (data0 & ~mask) | ((value << pos) & mask)
        self.roc_write(addr, data1)

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
                break

        return bit
