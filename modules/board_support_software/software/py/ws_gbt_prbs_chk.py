"""Implements the control for the gbt_prbs_chk wishbone slave"""

from enum import IntEnum, unique
from wishbone_module import WishboneModule

@unique
class WsGbtPrbsChkAddress(IntEnum):
    """Memory mapping for the gbt_prbs_chk module taken from gbt_prbs_chk_pkg.vhd"""
    RST_LATCH         = 0x00
    CONTROL           = 0x01
    ERRORS            = 0x02

@unique
class Control(IntEnum):
    ENABLE   = 0x0
    MODE     = 0x1
    LOCKED   = 0x2

@unique
class PrbsMode(IntEnum):
    PRBS7  = 0
    PRBS23 = 1

@unique
class ResetLatch(IntEnum):
    RESET  = 0
    LATCH  = 1

class WsGbtPrbsChk(WishboneModule):
    """Wishbone slave for GBT PRSB checker"""

    def __init__(self, moduleid, board_obj):
        super(WsGbtPrbsChk, self).__init__(moduleid=moduleid, name="GBT PRBS checker", board_obj=board_obj)

    def is_locked(self):
        """Check if PRBS has locked to steream"""
        data = self.read(WsGbtPrbsChkAddress.CONTROL)
        return (data >> Control.LOCKED & 0x1) == 0x1

    def set_mode(self, mode):
        """Set PRBS mode, 0=PRBS7, 1=PRBS23"""
        assert mode in set(item.value for item in PrbsMode)
        data = self.read(WsGbtPrbsChkAddress.CONTROL)
        data = (data & ~(1 << Control.MODE)) | (mode << Control.MODE)
        self.write(WsGbtPrbsChkAddress.CONTROL, data)

    def enable_prbs_test(self):
        """Enable PRBS testing"""
        data = self.read(WsGbtPrbsChkAddress.CONTROL)
        data = data | 0x1
        self.write(WsGbtPrbsChkAddress.CONTROL, data)

    def disable_prbs_test(self):
        """Disable PRBS testing"""
        data = self.read(WsGbtPrbsChkAddress.CONTROL)
        data = data & ~0x1
        self.write(WsGbtPrbsChkAddress.CONTROL, data)

    def get_errors(self):
        """Get accumulated PRBS errors"""
        self.latch_errors()
        return self.read(WsGbtPrbsChkAddress.ERRORS)

    def reset_errors(self):
        """Reset the error counter"""
        data = 1 << ResetLatch.RESET
        self.write(WsGbtPrbsChkAddress.RST_LATCH, data)

    def latch_errors(self):
        """Latch the error counter"""
        data = 1 << ResetLatch.LATCH
        self.write(WsGbtPrbsChkAddress.RST_LATCH, data)

    def dump_config(self):
        """Dump the modules state and configuration as a string"""
        config_str = "--- GBT PRBS CHK module ---\n"
        for address in WsGbtPrbsChkAddress:
            name = address.name
            value = self.read(address.value)
            config_str += "    - {0} : {1:#06X}\n".format(name, value)
        return config_str
