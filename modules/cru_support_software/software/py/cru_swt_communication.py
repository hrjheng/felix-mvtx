"""Communication implementation for the CRU using SWTs

Copy paste from communication.py, needs to be restructured and inserted in proper folder.
"""

import time
import traceback
import sys
import inspect

from enum import IntEnum, unique

import communication
import cru_table


@unique
class CruSwtAddress(IntEnum):
    """Class to handle the addressing of the swt controller in the CRU"""
    SWT_CONTROL = cru_table.CRUADD['add_gbt_swt_cmd']
    SWT_MONITOR = cru_table.CRUADD['add_gbt_swt_mon']
    TX_HI       = cru_table.CRUADD['add_gbt_swt_wr_h']
    TX_MID      = cru_table.CRUADD['add_gbt_swt_wr_m']
    TX_LOW      = cru_table.CRUADD['add_gbt_swt_wr_l']
    RX_HI       = cru_table.CRUADD['add_gbt_swt_rd_h']
    RX_MID      = cru_table.CRUADD['add_gbt_swt_rd_m']
    RX_LOW      = cru_table.CRUADD['add_gbt_swt_rd_l']

class CruSwtCommunication(communication.Communication):
    """ Implementation of Communication class

    This implements the commmunication class by establishing a
    Connection through the CRU via SWT packets.

    """
    def __init__(self, cru, gbt_channel):
        super(CruSwtCommunication, self).__init__()
        if gbt_channel is None:
            raise UndefinedGBTChannel
        self._cru = cru
        self._roc = cru._roc
        self.max_poll_per_swt = 200
        self.max_poll_per_fifo_read = 200
        self._gbt_channel = None
        self._assign_gbt_channel(gbt_channel=gbt_channel)

    def _lock_comm(self):
        if not self._cru._lock_comm():
            #self.logger.info(f"{inspect.stack()[1][3]} \t {self._cru._lla_lock_count}")
            return False
        return True

    def _unlock_comm(self, force=False):
        if not self._cru._unlock_comm(force):
            #self.logger.info(f"{inspect.stack()[1][3]} \t {self._cru._lla_lock_count}")
            return False
        return True
        
    def _is_lla_locked(self):
        return self._cru._is_lla_locked()

    def roc_write(self, reg, data):
        self._cru.roc_write(reg, data, self.get_gbt_channel())

    def roc_read(self, reg):
        return self._cru.roc_read(reg, self.get_gbt_channel())

    def _assign_gbt_channel(self, gbt_channel=None):
        """Assigns a cru_ch to the communication class"""
        if gbt_channel is not None:
            assert gbt_channel in range(24), gbt_channel
            self._gbt_channel = gbt_channel

    def get_gbt_channel(self):
        """
        Returns the gbt_channel in use by the comm object
        """
        return self._gbt_channel

    def _read_swt_status(self):
        """
        read the SWT Status register

        [7:0]   = number of SWT Writes since last reset
        [15:8]  = current GBT channel used (0 - 23)
        [25:16] = number of read packets in SWT FIFO
        """
        value = self.roc_read(CruSwtAddress.SWT_MONITOR)
        ret_dict = {'swt_writes'         : (value >>  0) & 0xFF,
                    'gbt_ch'             : (self.get_gbt_channel()),
                    'swt_words_available': (value >> 16) & 0x3FF}
        return value, ret_dict

    def _get_swt_words_available(self):
        """Returns number of SWT words in the FIFO"""
        return self._read_swt_status()[1]['swt_words_available']

    def log_swt_status(self):
        _, value = self._read_swt_status()
        self.logger.info(f"SWT written\t{value['swt_writes']}")
        self.logger.info(f"GBT channel\t{value['gbt_ch']}")
        self.logger.info(f"SWT in FIFO\t{value['swt_words_available']}")

    # WRITE

    def _do_write_dp0(self, data):
        """Implementation of the Communication method"""

        if not self._is_lla_locked():
            traceback.print_stack()
            sys.exit(f"_do_write_dp0({hex(data)}) not locked!")
        sendArray = communication._as_int_array(data)
        for sendVal in sendArray:
            self._send_swt(msg=sendVal)

    def _send_swt(self, msg):
        """
        send a 32-bit message into a SWT
        """
        assert msg | 0xFFFFFFFF == 0xFFFFFFFF
        self.roc_write(CruSwtAddress.TX_LOW, msg)

    def _send_swt_opt(self, msg):
        # The latest CRU fw is already optimized for writing, so use the same
        # function _send_swt here
        raise DeprecationWarning("Deprecated function, please use _send_swt instead")
        self._send_swt(msg)

    def _send_swt_full(self, hi, mid, low):
        """
        send a 76-bit message into a SWT

        hi  : SWT[75:64]
        mid : SWT[63:32]
        low : SWT[31:0]
        """
        assert hi | 0xFFF == 0xFFF
        assert mid | 0xFFFFFFFF == 0xFFFFFFFF
        assert low | 0xFFFFFFFF == 0xFFFFFFFF

        # fill SWT FIFO
        self.roc_write(CruSwtAddress.TX_HI, hi)
        self.roc_write(CruSwtAddress.TX_MID, mid)
        self.roc_write(CruSwtAddress.TX_LOW, low)

    # READ

    def _do_read_dp1(self, size):
        """Implementation of the Communication method"""
        assert size%4 == 0
        remaining = size
        msg = bytearray()

        if not self._is_lla_locked():
            self.logger.warning(f"_do_write_dp0() not locked!")

        while remaining > 0:
            if not self._is_swt_available():
                retries = 1
                is_available = self._is_swt_available()
                while not is_available and retries < self.max_poll_per_swt:
                    # no message received yet, wait a little
                    time.sleep(0.01)
                    is_available = self._is_swt_available()
                    retries += 1
                if not is_available:
                    traceback.print_stack()
                    raise RuntimeError(f"No SWT available after max_poll_per_swt retries on channel {self.get_gbt_channel()}.")
            value = self._read_swt()
            msg.extend((value).to_bytes(4, 'little'))
            remaining -= 4
        return msg

    def _is_swt_available(self):
        """Returns True if SWT are available in the read fifo"""
        words_available = self._get_swt_words_available()
        return words_available != 0

    def _get_high(self):
        hi = self.roc_read(CruSwtAddress.RX_HI)
        ctr = (hi & 0x0000f000) >> 12
        hi_nibble = hi & 0x00000fff
        return ctr, hi_nibble

    def _read_swt(self):
        """
        receives the 32 lowermost bits of a SWT
        """
        # reading the lower part of the SWT also does the FIFO rden
        return self.roc_read(CruSwtAddress.RX_LOW)

    def _read_swt_full(self):
        """
        receive a 80-bit GBT message via the GBT SWT registers and returns it
        """
        # reading the lower part of the SWT also does the FIFO rden
        # so read this first!
        low = self.roc_read(CruSwtAddress.RX_LOW)
        mid = self.roc_read(CruSwtAddress.RX_MID)
        hi = self.roc_read(CruSwtAddress.RX_HI)
        return hi << 64 | mid << 32 | low

    def _dump_swt_fifo(self):
        """Dumps content of SWT fifo"""
        words_available = self._get_swt_words_available()
        words = []
        while words_available != 0:
            words.append(self._read_swt_full())
            words_available -= 1
        return words

    def _dump_swt_fifo_decode(self):
        """Dumps content of SWT fifo, then decodes and logs the words"""
        words = self._dump_swt_fifo()
        for word in words:
            if ((word >> 76) & 0xF) != 0x3:
                self.logger.info(f"Word: {word:#024X}  SWT: NO")
            else:
                self.logger.info(f"Word: {word:#024X}  SWT: YES  Unused 95:80: {(word >> 80) & 0xFFFF:#04X}  Unused 75:32: {(word >> 32) & 0xFFFFFFFFFFF:#011X}  Read error: {(word >> 31) & 0x1}  Module: {(word >> 24) & 0x7F:#02X}  Address: {(word >> 16) & 0xFF:#02X}  Data: {word & 0xFFFF:#04X}")

    def _fifo_read_enable(self):
        """Writes a 1 to the read enable bit of the SWT FIFO control register"""
        self._roc.register_write(CruSwtAddress.SWT_CONTROL, 2)


class UndefinedGBTChannel(Exception):
    pass