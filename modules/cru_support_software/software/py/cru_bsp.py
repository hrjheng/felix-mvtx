"""WP10 implementation of the BSP.
The file is meant to provide user usable functions for the CRU defined class
"""
import time
import logging
import re

from roc import Roc
from cru_table import CRUADD
import cru_i2c


class CruBsp(Roc):
    """
    WP10-defined wrapper for BSP
    several functions imported from equivalent class in cru-sw subtree
    """

    def __init__(self, pcie_opened_roc, pcie_id, verbose=False):
        """Init method for BSP"""

        Roc.__init__(self)
        self.set_roc(pcie_opened_roc)
        self._pcie_id = pcie_id
        self.name = "BSP"
        self.logger = logging.getLogger(f"{self.name}")

    def initialize(self):
        """Initializes the module for the ITS operation"""
        pass

    # ----  JS Methods imported from cru-sw ----

    def enable_run(self):
        """ Enable datataking """
        DeprecationWarning("Not needed any longer")
        self.roc_rmw(CRUADD['add_bsp_info_userctrl'], 0, 1, 0x1)

    def disable_run(self):
        """ Disable datataking """
        DeprecationWarning("Not needed any longer")
        self.roc_rmw(CRUADD['add_bsp_info_userctrl'], 0, 1, 0x0)

    def reset_clock_tree(self):
        """ activate the reset for TTC pon, GBT and dwrapper"""
        self.roc_rmw(CRUADD['add_bsp_info_userctrl'], 0, 1, 0x0)  # deactivate RUN enable

        # Reset ONU first..
        self.roc_rmw(CRUADD['add_onu_user_logic'], 0, 1, 0x1)  # activate onu reset
        time.sleep(1.0)
        self.roc_rmw(CRUADD['add_onu_user_logic'], 0, 1, 0x0)  # deactivate onu reset

        # ..then reset core
        self.roc_rmw(CRUADD['add_bsp_info_userctrl'], 1, 1, 0x1)  # activate core reset
        time.sleep(1.0)
        self.roc_rmw(CRUADD['add_bsp_info_userctrl'], 1, 1, 0x0)  # deactivate core reset

    def get_short_hash(self):
        """ get firmware short hash numer (32 bit) """
        val = self.roc_read(CRUADD['add_bsp_info_shorthash'])
        return val

    def get_dirty_status(self):
        """ get firmware git dirty status at build time """
        if self.roc_read(CRUADD['add_bsp_info_dirtystatus']) != 0:
            val = True
        else:
            val = False
        return val

    def get_build_date(self,verbose=False):
        """ get firmware build date """
        val = self.roc_read(CRUADD['add_bsp_info_builddate'])
        return val

    def get_build_time(self,verbose=False):
        """ get firmware build time """
        val = self.roc_read(CRUADD['add_bsp_info_buildtime'])
        return val

    def get_chip_id(self,verbose=False):
        """ get Altera chip ID """
        idlow = self.roc_read(CRUADD['add_bsp_hkeeping_chipid_low'])
        idhigh = self.roc_read(CRUADD['add_bsp_hkeeping_chipid_high'])
        return idhigh,idlow

    def log_fw_info(self):
        """ Gets firmware information (hash number, build date and time and altera Chip Id """
        idhigh,idlow=self.get_chip_id()
        self.logger.info('=========================================================================================')
        self.logger.info('>>> Firmware short hash=0x{:08x}'.format(self.get_short_hash()))
        self.logger.info('>>> Firmware is dirty status= {}'.format(self.get_dirty_status()))
        self.logger.info('>>> Firmware build date and time={:08X}  {:06X}'.format(self.get_build_date(),self.get_build_time()))
        self.logger.info('>>> Altera chip ID=0x{:08x}-0x{:08x}'.format(idhigh,idlow))
        self.logger.info('=========================================================================================')

    def is_clk240_alive(self):
        """ Checks if clk240 is active or stopped """
        val1 = self.roc_read(CRUADD['add_bsp_hkeeping_spare_in'])
        val2 = self.roc_read(CRUADD['add_bsp_hkeeping_spare_in'])
        if val1 == val2:
            return False
        else:
            return True

    def set_cru_id(self,val):
        """ Set the CRU ID to be added in the RDH (12 bit value) """
        if (val < 0) or (val > (1 << 12) - 1):
            raise ValueError("BSP: bad CRUid setting")
        self.roc_rmw(CRUADD['add_bsp_info_userctrl'], 16, 12, val)

    def led_blink_loop(self, mask=0xF):
        """ blink front panel LED """
        if mask<0 or mask>0xF:
            raise ValueError("BSP: bad LED blinking mask (4 bit max)")
        try:
            while True:
                self.roc_rmw(CRUADD['add_bsp_info_userctrl'], 3, 4, mask)  # toggle LED value
                time.sleep(0.2)
                self.roc_rmw(CRUADD['add_bsp_info_userctrl'], 3, 4, 0)  # back to normal
                time.sleep(0.2)
        except KeyboardInterrupt:
            self.roc_rmw(CRUADD['add_bsp_info_userctrl'], 3, 4, 0)  # back to normal
            return

    def hw_compatible_fw(self, pcie_id):
        """ Returns True if firmware was targeted for current hardware, False otherwise """

        # UTF-8 encoded byte -> character:
        #  76 -> 'v'
        #  32 -> '2'
        #  30 -> '0'
        v20 = 0x763230
        v22 = 0x763232
        MAX_CHAR_EEPROM = 1000 // 8  # EEPROM size is 1KB

        target_hw = self.roc_read(CRUADD['add_bsp_info_boardtype'])

        eeprom = cru_i2c.CruI2c(pcie_opened_roc=self._roc,
                                pcie_id=pcie_id,
                                base_add=CRUADD['add_bsp_i2c_eeprom'],
                                chip_add=0x50)

        eeprom.reset_i2c()
        hw_info = ""
        for i in range(MAX_CHAR_EEPROM):
            res = eeprom.read_i2c(i)
            hw_info = hw_info + chr(res)
            if res == ord("}"):
                break

        # Protection against \xff\xff..
        if len(hw_info) > 0 and hw_info[0] == "\xff":
            hw_info = "?" * len(hw_info)

        # re.search() returns Match object if there's a match, None otherwise
        hw_is_v22 = re.search("p40_.v22",hw_info)

        isCompatible = (target_hw == v22 and hw_is_v22) or (target_hw == v20 and not hw_is_v22)

        if not isCompatible:
            msg = "Firmware-hardware mismatch, "
            if target_hw == v22:
                msg = msg + "hardware type: v2.0 (pre-production), firmware is targeted for v2.2"
                self.logger.warning(msg)
                self.logger.warning("PON upstream will not work (downstream still works)")
            elif target_hw == v20:
                msg = msg + "hardware type: v2.2 (production), firmware is targeted for v2.0:"
                self.logger.warning(msg)
                self.logger.warning("PON upstream will not work (downstream still works)")
            else:
                self.logger.warning(f"Unknown Hardware {target_hw}")

        return isCompatible

    # -------------------- JS end import -----------------------------------
