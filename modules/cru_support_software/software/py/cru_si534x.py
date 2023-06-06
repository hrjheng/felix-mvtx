import logging
from enum import IntEnum, unique

from cru_i2c import CruI2c


@unique
class Si5345ClockSelect(IntEnum):
    LOCAL   = 0
    TTC     = 1
    Unknown = 2

@unique
class Si5345ClockSwitchMode(IntEnum):
    Manual = 0
    Automatic_non_revertive = 1
    Automatic_revertive = 2
    Reserved = 3


@unique
class Si5345ClockSelectMode(IntEnum):
    pin = 0
    register = 1


class CruSi534x(CruI2c):
    def __init__(self, pcie_opened_roc, pcie_id, bar_ch, base_add, chip_add):
        """
        Default constructor
        """
        super(CruSi534x, self).__init__(pcie_opened_roc=pcie_opened_roc,
                                        pcie_id=pcie_id,
                                        base_add=base_add,
                                        chip_add=chip_add)

        self.name = "SI534X"
        self.logger = logging.getLogger("{0}".format(self.name))

    def get_clock_switch_mode(self):
        """return the clock switch mode of the PLL"""
        self.reset_i2c()
        self.write_i2c((0x0001), 5)
        clk_switch_mode = self.read_i2c(0x36) & 0x3
        return clk_switch_mode

    def get_clock_select_mode(self):
        """return the clock select mode of the PLL"""
        self.reset_i2c()
        self.write_i2c((0x0001), 5)
        clk_sel_mode = self.read_i2c(0x2A) & 0x1
        return clk_sel_mode

    def get_clock_select(self):
        """return the clock selection of the PLL"""
        self.reset_i2c()
        self.write_i2c((0x0001), 5)
        clk_sel = self.read_i2c(0x2A) >> 1 & 0x3
        return clk_sel

    def get_input_info(self, show=False):
        """ Reports about enabled and selected inputs """

        self.reset_i2c()
        self.write_i2c((0x0001), 5)
        clk_switch_mode = self.read_i2c(0x36) & 0x3
        clk_sel_mode = self.read_i2c(0x2A) & 0x1
        clk_sel = self.read_i2c(0x2A) >> 1 & 0x3

        if show:
            self.logger.info(f"Clock switch mode is {Si5345ClockSwitchMode(clk_switch_mode).name}")
            self.logger.info(f"Clock selection is {Si5345ClockSelectMode(clk_switch_mode).name} controlled")
            self.logger.info(f"Input clock {Si5345ClockSelect(clk_sel).name} is selected")

        return (clk_switch_mode, clk_sel_mode, clk_sel)
