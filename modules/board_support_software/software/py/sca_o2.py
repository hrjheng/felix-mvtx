""" GBT-SCA controller implementation for the CRU board
"""

import time
from enum import IntEnum, unique

import os

import cru_table
from gbt_sca import Sca
from gbt_sca import ScaBadErrorFlagError


@unique
class CruScaAddress(IntEnum):
    """Address for the SCA module in the CRU"""
    WR_DATA = cru_table.CRUADD['add_gbt_sca_wr_data']
    WR_CMD  = cru_table.CRUADD['add_gbt_sca_wr_cmd']
    WR_CTR  = cru_table.CRUADD['add_gbt_sca_wr_ctr']
    RD_DATA = cru_table.CRUADD['add_gbt_sca_rd_data']
    RD_CMD  = cru_table.CRUADD['add_gbt_sca_rd_cmd']
    RD_CTR  = cru_table.CRUADD['add_gbt_sca_rd_ctr']
    RD_MON  = cru_table.CRUADD['add_gbt_sca_rd_mon']


class Sca_O2(Sca):
    """Class to implement GBT-SCA transactions"""

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
        super(Sca_O2, self).__init__(use_adc=use_adc,
                                     use_gpio=use_gpio,
                                     use_jtag=use_jtag,
                                     use_gbtx_i2c=use_gbtx_i2c,
                                     use_pa3_i2c=use_pa3_i2c,
                                     use_pa3_i2c_2=use_pa3_i2c_2,
                                     use_us_i2c=use_us_i2c,
                                     is_on_ruv1=is_on_ruv1,
                                     is_on_ruv2_0=is_on_ruv2_0)

        self.comm = comm
        self._trID = 0

    def _lock_comm(self):
        self.comm._lock_comm()

    def _unlock_comm(self):
        self.comm._unlock_comm()

    def _wr(self, cmd, data, trID = None):
        """
        Write 64 bit packet (data + cmd) to the SCA interface and execute the command
        If trID is not defined, it increments it for every _wr
        """
        if trID is None:
            self._trID = self._trID + 1
            if self._trID == 0xff:
                self._trID =  0x1
            _trID = self._trID
        else:
            _trID = trID

        _cmd = (cmd & 0xff00ffff) + (_trID<<16)

        self._lock_comm()
        try:
            self.comm.roc_write(CruScaAddress.WR_DATA, data)
            self.comm.roc_write(CruScaAddress.WR_CMD, _cmd)

            self.comm.roc_write(CruScaAddress.WR_CTR, 0x4)
            self.comm.roc_write(CruScaAddress.WR_CTR, 0x0)
            self.waitBusy()

            _time = self.comm.roc_read(CruScaAddress.RD_MON)
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
                busy = (self.comm.roc_read(CruScaAddress.RD_CTR))>>31
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
                data = self.comm.roc_read(CruScaAddress.RD_DATA)
                cmd = self.comm.roc_read(CruScaAddress.RD_CMD)
                ctrl = self.comm.roc_read(CruScaAddress.RD_CTR)

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
        self.logger.debug("SCA Reset")
        self._lock_comm()
        try:
            self.comm.roc_write(CruScaAddress.WR_CTR, 0x1)
            self.waitBusy()
            self._rd()
            self.comm.roc_write(CruScaAddress.WR_CTR, 0x0)
        finally:
            self._unlock_comm()#release_kept_lock=True)

    def HDLC_connect(self):
        self.logger.debug("SCA Init")
        self._lock_comm()
        try:
            self.comm.roc_write(CruScaAddress.WR_CTR, 0x2)
            self.waitBusy()
            self._rd()
            self.comm.roc_write(CruScaAddress.WR_CTR, 0x0)
        finally:
            self._unlock_comm()#release_kept_lock=True)
