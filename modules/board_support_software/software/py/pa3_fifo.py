"""Implements the control for the pa3_fifo_wb_slave wishbone slave"""
from enum import IntEnum, unique
import logging
import warnings

from communication import WishboneReadError
import pa3_fifo_monitor
from wishbone_module import WishboneModule


@unique
class Pa3FifoAddress(IntEnum):
    """Memory mapping for the pa3_fifo_wb_slave taken from pa3_fifo_wb_slave_pkg.vhd"""
    WR_FIFO_DATA = 0
    DEAD_00 = 1
    DEAD_01 = 2
    DEAD_02 = 3
    DEAD_03 = 4
    DEAD_04 = 5
    DEAD_05 = 6
    DEAD_06 = 7
    DEAD_07 = 8
    FIFO_RESET = 9


class Pa3Fifo(WishboneModule):
    """Send data to PA3 FIFO slave"""
    def __init__(self, moduleid, board_obj, monitor_module):
        super(Pa3Fifo, self).__init__(moduleid=moduleid, board_obj=board_obj, name="PA3 FIFO")
        assert isinstance(monitor_module, pa3_fifo_monitor.Pa3FifoMonitor)
        self._monitor = monitor_module
        if type(self.comm).__name__ == 'CruSwtCommunication':
            # To be used only in the CRU_ITS, where the import is available
            # Hacky version of ```import cru_swt_communication.CruSwtAddress as _cru_add``` to fool pylint
            _temp = __import__('cru_swt_communication', globals(), locals(), ['CruSwtAddress'], 0)
            _cru_add = _temp.CruSwtAddress
            self._BASE_SWT_WRITE_MESSAGE = ((0x80 | self.moduleid) << 24) | (Pa3FifoAddress.WR_FIFO_DATA << 16)
            self._CRU_ADD_TX_LOW = _cru_add.TX_LOW
            self._CRU_ADD_SWT_CONTROL = _cru_add.SWT_CONTROL
        elif type(self.comm).__name__ == 'FlxSwtCommunication':
            # To be used only with FELIX, where the import is available
            # Hacky version of ```import flx_swt_communication.FlxSwtAddress as _cru_add``` to fool pylint
            _temp = __import__('flx_swt_communication', globals(), locals(), ['FlxSwtAddress'], 0)
            _flx_add = _temp.FlxSwtAddress
            self._BASE_SWT_WRITE_MESSAGE = ((0x80 | self.moduleid) << 24) | (Pa3FifoAddress.WR_FIFO_DATA << 16)
            self._CRU_ADD_TX_LOW = _flx_add.TX_LOW
            self._CRU_ADD_SWT_CONTROL = _flx_add.SWT_CONTROL
        else:
            # In RU_mainFPGA this method should not be used
            self._BASE_SWT_WRITE_MESSAGE = None
            self._CRU_ADD_TX_LOW = None
            self._CRU_ADD_SWT_CONTROL = None

    def write_data_to_fifo(self, data):
        """Writes data 16-bit word to the FIFO"""
        assert data in range(0xFFFF+1)
        self.write(Pa3FifoAddress.WR_FIFO_DATA, data)

    def write_data_to_fifo_opt(self, data):
        """
        does the same as write_data_to_fifo, but with significantly more speed.
        should be about 4x improvement by calling C code directly from here.
        This bypasses the software queing mechanism, so it should be used with some caution.
        """
        self.comm.roc_write(self._CRU_ADD_TX_LOW, (self._BASE_SWT_WRITE_MESSAGE | (data & 0xffff)))
        self.comm.roc_write(self._CRU_ADD_SWT_CONTROL, 1)

    def write_data_to_fifo_opt_flx(self, data):
        """
        does the same as write_data_to_fifo, but with significantly more speed.
        should be about 4x improvement by calling C code directly from here.
        This bypasses the software queing mechanism, so it should be used with some caution.
        """
        self.comm._roc.register_write(self._CRU_ADD_TX_LOW, (self._BASE_SWT_WRITE_MESSAGE | (data & 0xffff)))
        self.comm._roc.register_write(self._CRU_ADD_SWT_CONTROL, 1)
        self.comm._roc.register_write(self._CRU_ADD_SWT_CONTROL, 0)

    def is_old_wb2fifo(self):
        """Does the FW have the old wb2fifo slave?"""
        exc_en = self.comm._enable_rderr_exception
        self.comm.enable_rderr_exception()
        logger = logging.getLogger("Communication")
        level = logger.level
        logger.setLevel(logging.FATAL)
        try:
            self.read(0, True)
        except WishboneReadError:
            return False
        finally:
            logger.setLevel(level)
            if not exc_en:
                self.comm.disable_rderr_exception()
        return True

    def reset_fifo(self):
        """Resets the PA3 FIFO"""
        if self.is_old_wb2fifo():
            warnings.warn("Old FW detected, can't reset fifo. Reset XCKU if problems.")
        else:
            self.write(Pa3FifoAddress.FIFO_RESET, 1)

    # Monitor

    def reset_counters(self, commitTransaction=True):
        """resets all the counters"""
        self._monitor.reset_all_counters(commitTransaction=commitTransaction)

    def read_counters(self, reset_after=False, commitTransaction=True):
        """latches and reads all the counters"""
        return self._monitor.read_counters(reset_after=reset_after, commitTransaction=commitTransaction)

   # Old methods for accessing old slave, kept for ability to seamlessly do flash upgrades on old FW

    def _read_write_counter(self, deprecation_warning_en=True):
        if deprecation_warning_en:
            warnings.warn("Use pa3_fifo.read_counter('FIFO_WRITE') instead.", DeprecationWarning)
        if self.is_old_wb2fifo():
            self.read(0,False)
            self.read(1,False)
            results = self.read_all()
            return results[0] | (results[1] << 16)
        else:
            return self._monitor.read_counter('FIFO_WRITE', reset_after=False, commitTransaction=True)

    def _read_read_counter(self, deprecation_warning_en=True):
        if deprecation_warning_en:
            warnings.warn("Use pa3_fifo.read_counter('FIFO_READ') instead.", DeprecationWarning)
        if self.is_old_wb2fifo():
            self.read(2,False)
            self.read(3,False)
            results = self.read_all()
            return results[0] | (results[1] << 16)
        else:
            return self._monitor.read_counter('FIFO_READ', reset_after=False, commitTransaction=True)

    def _read_overflow_counter(self, deprecation_warning_en=True):
        if deprecation_warning_en:
            warnings.warn("Use pa3_fifo.read_counter('FIFO_OVERFLOW') instead.", DeprecationWarning)
        if self.is_old_wb2fifo():
            self.read(4,False)
            self.read(5,False)
            results = self.read_all()
            return results[0] | (results[1] << 16)
        else:
            return self._monitor.read_counter('FIFO_OVERFLOW', reset_after=False, commitTransaction=True)

    def _read_underflow_counter(self, deprecation_warning_en=True):
        if deprecation_warning_en:
            warnings.warn("Use pa3_fifo.read_counter('FIFO_UNDERFLOW') instead.", DeprecationWarning)
        if self.is_old_wb2fifo():
            warnings.warn("Old FW detected, underflow counter not present, skipping check")
            return 0
        else:
            return self._monitor.read_counter('FIFO_UNDERFLOW', reset_after=False, commitTransaction=True)
