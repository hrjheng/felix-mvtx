""" GBT-SCA controller implementation for the FELIX board
"""

import time
from enum import IntEnum, unique

import flx_table
from gbt_sca import Sca
from gbt_sca import ScaBadErrorFlagError


@unique
class FlxScaAddress(IntEnum):
    """Address for the SCA module in the CRU"""
    WR_CMD_DATA  = flx_table.FLXADD['add_gbt_sca_tx_cmd_data']
    WR_CTRL      = flx_table.FLXADD['add_gbt_sca_wr_ctr']
    RD_CMD_DATA  = flx_table.FLXADD['add_gbt_sca_rx_cmd_data']
    RD_CTR_MON   = flx_table.FLXADD['add_gbt_sca_rd_ctr_mon']


class Sca_flx(Sca):
    """Class to implement GBT-SCA transactions"""

    # keep track of the gbt_channel within the SCA class
    _selected_gbt_channel = -1

    def __init__(self, comm,
                 use_adc=True,
                 use_gpio=True,
                 use_jtag=True,
                 use_gbtx_i2c=True,
                 use_pa3_i2c=True,
                 use_pa3_i2c_2=True,
                 use_us_i2c=False,
                 is_on_ruv1=False,
                 is_on_ruv2_0=True):
        """Class constructor. Init register addresses"""
        super(Sca_flx, self).__init__(use_adc=use_adc,
                                      use_gpio=use_gpio,
                                      use_gbtx_i2c=use_gbtx_i2c,
                                      use_pa3_i2c=use_pa3_i2c,
                                      use_pa3_i2c_2=use_pa3_i2c_2,
                                      use_us_i2c=use_us_i2c,
                                      is_on_ruv1=is_on_ruv1,
                                      is_on_ruv2_0=is_on_ruv2_0)

        self.comm  = comm
        self._trID = 0

    def _lock_comm(self):
        self.comm._lock_comm()

    def _unlock_comm(self):
        self.comm._unlock_comm()

    def _check_gbt_channel(self):
        if self.comm._gbt_channel != Sca_flx._selected_gbt_channel:
            self.comm._flx.set_gbt_channel(gbt_channel=self.comm._gbt_channel)
            Sca_flx._selected_gbt_channel = self.comm._gbt_channel

    def _wr(self, cmd, data, trID = None):
        """
        Write 64 bit packet (data + cmd) to the SCA interface and execute the command
        If trID is not defined, it increments it for every _wr
        """
        self._check_gbt_channel()

        if trID is None:
            self._trID = self._trID + 1
            if self._trID == 0xff:
                self._trID =  0x1
            _trID = self._trID
        else:
            _trID = trID

        _cmd = (cmd & 0xff00ffff) + (_trID<<16)
        _tx_data = (data<<32) + _cmd

        tx_busy_cnt = 0
        self._lock_comm()
        try:
            tx_busy = (self.comm.roc_read(FlxScaAddress.RD_CTR_MON))>>30
            while (tx_busy == 0x1):
                tx_busy_cnt += 1
                if tx_busy_cnt == 1e5:
                    self.logger.error(f"SCA transaction is stuck ch {self.comm.get_gbt_channel()} ... exiting")
                    raise Exception("SCA is stuck ...")
                tx_busy = (self.comm.roc_read(FlxScaAddress.RD_CTR_MON))>>30

            self.comm.roc_write(FlxScaAddress.WR_CMD_DATA, _tx_data)

            self.comm.roc_write(FlxScaAddress.WR_CTRL, 0x4)
            self.comm.roc_write(FlxScaAddress.WR_CTRL, 0x0)
            self.waitBusy()

            _time = self.comm.roc_read(FlxScaAddress.RD_CTR_MON)
            _time = (_time>>8) & 0xff
        finally:
            self._unlock_comm()

        self.logger.debug(
            "WR - DATA 0x{0:010X} CH {1:04X} TR {2:04X} CMD {3:04X} TIME {4:04X}".format(
                data,
                (_cmd>>24),
                ((_cmd>>16)&0xff),
                (_cmd&0xff),
                _time))

    def waitBusy(self):
        """
        Wait for the SCA component to be available
        """
        busy_cnt = 0
        busy = 0x1
        self._lock_comm()
        try:
            while (busy == 0x1):
                busy = (self.comm.roc_read(FlxScaAddress.RD_CTR_MON))>>31
                busy_cnt = busy_cnt + 1
                if busy_cnt == 1e5:
                    self.logger.error(f"SCA is stuck ch {self.comm.get_gbt_channel()} ... exiting")
                    raise Exception("SCA is stuck ...")
        finally:
            self._unlock_comm()

    def _rd(self):
        """
        Read the feedback from the SCA component
        """
        data = 0xFFFFFFFF
        err_code = 0x40
        self._lock_comm()
        try:
            while err_code != 0:
                _rx_data = self.comm.roc_read(FlxScaAddress.RD_CMD_DATA)
                data = (_rx_data >> 32) & 0xFFFFFFFF
                cmd  = _rx_data & 0xFFFFFFFF
                ctrl = self.comm.roc_read(FlxScaAddress.RD_CTR_MON) & 0xff

                err_code = cmd & 0xff
                if err_code == 0x40:
                    time.sleep(0.001)
                elif err_code != 0:
                    raise ScaBadErrorFlagError(err_code)
                else:
                    self.logger.debug(
                        "RD - DATA 0x{0:010X} CH {1:04X} TR {2:04X} ERR {3:04X} CTRL {4:04X}".format(
                            data,
                            (cmd>>24),
                            ((cmd>>16)&0xff),
                            (cmd&0xff),
                            ctrl))
        finally:
            self._unlock_comm()
        return data

    def _sca_write(self, channel, length, command, scadata, trid=0x12, commitTransaction=True, wait=400):
        assert (channel & 0xffffff00) == 0, "channel must be 8bit"
        assert (length & 0xffffff00) == 0, "length must be 8bit"
        assert (command & 0xffffff00) == 0, "command must be 8bit"
        assert (trid & 0xffffff00) == 0, "trid must be 8bit"

        cmd = ((channel&0xff)<<24) + (command&0xff)
        self._wr(cmd, scadata, trid)

    def _sca_read(self):
        return (self._rd())

    def init_communication(self):
        """
        Init SCA communication
        """
        self.HDLC_reset()
        self.HDLC_connect()

    def HDLC_reset(self):
        self._check_gbt_channel()
        self.logger.debug("SCA Reset")
        self._lock_comm()
        try:
            self.comm.roc_write(FlxScaAddress.WR_CTRL, 0x1)
            self.waitBusy()
            self._rd()
            self.comm.roc_write(FlxScaAddress.WR_CTRL, 0x0)
        finally:
            self._unlock_comm()

    def HDLC_connect(self):
        self._check_gbt_channel()
        self.logger.debug("SCA Init")
        self._lock_comm()
        try:
            self.comm.roc_write(FlxScaAddress.WR_CTRL, 0x2)
            self.waitBusy()
            self._rd()
            self.comm.roc_write(FlxScaAddress.WR_CTRL, 0x0)
        finally:
            self._unlock_comm()
