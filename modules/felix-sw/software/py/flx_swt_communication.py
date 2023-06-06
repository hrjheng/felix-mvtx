"""Communication implementation for the FLX using SWTs

Copy paste from communication.py, needs to be restructured and inserted in proper folder.
"""

import time

from enum import IntEnum, unique

import communication
import flx_table

@unique
class FlxSwtAddress(IntEnum):
    """Class to handle the addressing of the swt controller in the FELIX card"""
    SWT_CONTROL = flx_table.FLXADD['add_gbt_swt_cmd']
    SWT_MONITOR = flx_table.FLXADD['add_gbt_swt_mon']
    TX_HI       = flx_table.FLXADD['add_gbt_swt_wr_h']
    TX_LOW      = flx_table.FLXADD['add_gbt_swt_wr_l']
    RX_HI       = flx_table.FLXADD['add_gbt_swt_rd_h']
    RX_LOW      = flx_table.FLXADD['add_gbt_swt_rd_l']

class FlxSwtCommunication(communication.Communication):
    """ Implementation of Communication class

    This implements the communication class by establishing a
    Connection through the FELIX via SWT packets.

    """
    def __init__(self, flx, gbt_channel=None, always_set_gbt_channel=False):
        super(FlxSwtCommunication, self).__init__()
        self._flx = flx
        self._roc = flx._roc
        self.max_poll_per_swt = 200
        self.max_poll_per_fifo_read = 200
        self._gbt_channel = None
        self._assign_gbt_channel(gbt_channel=gbt_channel)
        self._always_set_gbt_channel = None
        self._set_always_set_gbt_channel(always_set_gbt_channel)

    def _lock_comm(self):
        self._flx._lock_comm()

    def _unlock_comm(self):
        self._flx._unlock_comm()

    def roc_write(self, reg, data):
        self._flx.roc_write(reg, data)

    def roc_read(self, reg):
        return self._flx.roc_read(reg)

    def _assign_gbt_channel(self, gbt_channel=None):
        """Assigns a flx_ch to the communication class"""
        if gbt_channel is not None:
            assert gbt_channel in range(24), gbt_channel
            self._gbt_channel = gbt_channel

    def get_gbt_channel(self):
        """
        Returns the gbt_channel in use by the comm object
        """
        return self._gbt_channel

    def get_currently_selected_channel(self):
        return self._read_swt_status()[1]['gbt_ch']

    def _set_always_set_gbt_channel(self, always_set_gbt_channel):
        """Sets the internal variable for setting the gbt_channel before each read/write"""
        assert always_set_gbt_channel in [True, False]
        self._always_set_gbt_channel = always_set_gbt_channel

    def _read_swt_status(self):
        """
        read the SWT Status register

        [7:0]   = number of SWT Writes since last reset
        [15:8]  = current GBT channel used (0 - 23)
        [25:16] = number of read packets in SWT FIFO
        """
        value = self._roc.register_read(FlxSwtAddress.SWT_MONITOR)
        ret_dict = {'swt_writes'         : (value >> 32) & 0xFF,
                    'gbt_ch'             : (value >> 44) & 0x1F,
                    'swt_words_available': (value >> 52) & 0x3FF}
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
        if self._gbt_channel is not None: # should prevent testbench to break
            if self._always_set_gbt_channel:
                self._flx.set_gbt_channel(gbt_channel=self._gbt_channel)
            else:
                if self._gbt_channel != self._flx._selected_gbt_channel:
                    self.logger.debug("Switching gbt_channel from {0} to {1}".format(self._flx._selected_gbt_channel, self._gbt_channel))
                    self._flx.set_gbt_channel(gbt_channel=self._gbt_channel)
        sendArray = communication._as_int_array(data)
        for sendVal in sendArray:
            self._send_swt(msg=sendVal)

    def _send_swt(self, msg):
        """
        send a 32-bit message into a SWT
        """
        assert msg | 0xFFFFFFFF == 0xFFFFFFFF
        self._roc.register_write(FlxSwtAddress.TX_LOW, msg)
        self._fifo_write_enable()



    def _send_swt_opt(self, msg):
        # The latest FLX fw is already optimized for writing, so use the same
        # function _send_swt here
        DeprecationWarning("Deprecated function, please use _send_swt instead")
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

        TX_H = hi
        TX_L = (mid << 32) | low
        # fill SWT FIFO
        self._roc.register_write(FlxSwtAddress.TX_HI,  TX_H)
        self._roc.register_write(FlxSwtAddress.TX_LOW, TX_L)
        self._fifo_write_enable()

    # READ

    def _do_read_dp1(self, size):
        """Implementation of the Communication method"""
        assert size%4 == 0
        remaining = size
        msg = bytearray()

        if self._gbt_channel is not None:  # should prevent testbench to break
            if self._always_set_gbt_channel:
                self._flx.set_gbt_channel(gbt_channel=self._gbt_channel)
            else:
                self.logger.debug("Gbt_channel is {0}".format(self._gbt_channel))
                if self._gbt_channel != self._flx._selected_gbt_channel:
                    self.logger.info("Switching gbt_channel from {0} to {1}".format(self._flx._selected_gbt_channel, self._gbt_channel))
                    self._flx.set_gbt_channel(gbt_channel=self._gbt_channel)

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
                    selected_channel = self.get_currently_selected_channel()
                    if self._gbt_channel is not None:
                        if selected_channel != self._gbt_channel:
                            self.logger.error(f"Wrong GBT channel selected! Expected {self._gbt_channel} got {selected_channel}")
                        raise RuntimeError(f"No SWT available after max_poll_per_swt retries on channel {selected_channel}. Tried to read from {self._gbt_channel}")
                    else:
                        raise RuntimeError(f"No SWT available after max_poll_per_swt retries on channel {selected_channel}.")
            value = self._read_swt()
            msg.extend((value).to_bytes(4, 'little'))
            remaining -= 4
        return msg

    def _is_swt_available(self):
        """Returns True if SWT are available in the read fifo"""
        words_available = self._get_swt_words_available()
        return words_available != 0

    def _get_high(self):
        hi = self._roc.register_read(FlxSwtAddress.RX_HI)
        ctr = (hi & 0x0000f000) >> 12
        hi_nibble = hi & 0x00000fff
        return ctr, hi_nibble

    def _read_swt(self):
        """
        receives the 32 lowermost bits of a SWT
        """
        prev_cnt = self._flx.get_prev_swt_cntr()
        if prev_cnt is None:
            prev_cnt, _ = self._get_high()
        self._fifo_read_enable()
        cur_cnt, _ = self._get_high()
        retries = 0
        while(cur_cnt == prev_cnt):
            cur_cnt, _ = self._get_high()
            retries += 1
            if retries > self.max_poll_per_fifo_read:
                self.log_swt_status()
                raise RuntimeError(f"SWT FIFO counter didn't change after {self.max_poll_per_fifo_read} tries: prev {prev_cnt} cur {cur_cnt}")
        self._flx.set_prev_swt_cntr(cur_cnt)
        return self._roc.register_read(FlxSwtAddress.RX_LOW)

    def _read_swt_full(self):
        """
        receive a 80-bit GBT message via the GBT SWT registers and returns it
        """
        prev_cnt = self._flx.get_prev_swt_cntr()
        if prev_cnt is None:
            prev_cnt, _ = self._get_high()
        self._fifo_read_enable()
        cur_cnt, hi = self._get_high()
        retries = 0
        while(cur_cnt == prev_cnt):
            cur_cnt, hi = self._get_high()
            retries += 1
            if retries > self.max_poll_per_fifo_read:
                raise RuntimeError(f"SWT FIFO counter didn't change after {self.max_poll_per_fifo_read} tries prev {prev_cnt} cur {cur_cnt}")
        self._flx.set_prev_swt_cntr(cur_cnt)
        # read other nibbles of SWT FIFO
        low = self._roc.register_read(FlxSwtAddress.RX_LOW)
        return hi << 64 | low

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
        self._roc.register_write(FlxSwtAddress.SWT_CONTROL, 2)
        self._roc.register_write(FlxSwtAddress.SWT_CONTROL, 0)

    def _fifo_write_enable(self):
        """Writes a 1 to the write enable bit of the SWT FIFO control register"""
        self._roc.register_write(FlxSwtAddress.SWT_CONTROL, 1)
        self._roc.register_write(FlxSwtAddress.SWT_CONTROL, 0)
