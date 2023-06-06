"""Class to implement the latest capabilities of the GBTxController"""

from wishbone_module import WishboneModule
from enum import IntEnum, unique

@unique
class WsGbtxControllerAddress(IntEnum):
    """memory mapping for gbtx controller module"""
    DEAD_01                = 0x00
    DEAD_02                = 0x01
    SET_IDELAY_VALUE0      = 0x02
    SET_IDELAY_VALUE1      = 0x03
    SET_IDELAY_VALUE2      = 0x04
    SET_IDELAY_VALUE3      = 0x05
    SET_IDELAY_VALUE4      = 0x06
    SET_IDELAY_VALUE5      = 0x07
    SET_IDELAY_VALUE6      = 0x08
    SET_IDELAY_VALUE7      = 0x09
    SET_IDELAY_VALUE8      = 0x0A
    SET_IDELAY_VALUE9      = 0x0B
    GET_IDELAY_VALUE0      = 0x0C
    GET_IDELAY_VALUE1      = 0x0D
    GET_IDELAY_VALUE2      = 0x0E
    GET_IDELAY_VALUE3      = 0x0F
    GET_IDELAY_VALUE4      = 0x10
    GET_IDELAY_VALUE5      = 0x11
    GET_IDELAY_VALUE6      = 0x12
    GET_IDELAY_VALUE7      = 0x13
    GET_IDELAY_VALUE8      = 0x14
    GET_IDELAY_VALUE9      = 0x15
    IDELAY_LOAD            = 0x16
    BITSLIP_RX_VALUE       = 0x17
    BITSLIP_TX_VALUE       = 0x18
    BITSLIP_LOAD           = 0x19
    TX_PATTERN_SELECTION   = 0x1A
    TX1_PATTERN_SELECTION  = 0x1B
    DEAD_00                = 0x1C
    NUM_REGS               = 0x1D


@unique
class TxPattern(IntEnum):
    """Tx pattern from the GBTx controller"""
    FIFO    = 0
    COUNTER = 1
    STATIC  = 2
    MIRROR  = 3


class GBTxController(WishboneModule):
    """GBTx controller wishbone slave"""

    def __init__(self, moduleid, board_obj):
        super(GBTxController, self).__init__(moduleid=moduleid, name="GBTxController", board_obj=board_obj)
        self.verbose = False

    def _load_idelay(self, commitTransaction=True):
        """commits the idelay value into the IDELAY"""
        self.write(WsGbtxControllerAddress.IDELAY_LOAD, 1, commitTransaction=commitTransaction)

    def _set_idelay_value_i(self, i, idelayi=None, commitTransaction=True):
        """sets the input delay for ports of the i_th group"""
        assert idelayi | 0x1FF == 0x1FF
        assert i in range(10)
        self.write(WsGbtxControllerAddress.SET_IDELAY_VALUE0+i, idelayi, commitTransaction=commitTransaction)

    def set_idelay(self, idelays=10*[None], idelay_all=None, commitTransaction=True):
        """sets the input delay of all the elinks groups ports, if they are not None"""
        if idelay_all is not None:
            idelays = 10*[idelay_all]
        for i in range(10):
            if idelays[i] is not None:
                self._set_idelay_value_i(i=i, idelayi=idelays[i], commitTransaction=commitTransaction)
        self._load_idelay(commitTransaction=commitTransaction)

    def get_idelay(self):
        """gets the idelay values and check if values are consistent,
        returns a tuple with the idelays 0 to 9"""
        idelay = 10*[None]
        idelay_read = 10*[None]
        for i in range(10):
            idelay[i] = self.read(WsGbtxControllerAddress.SET_IDELAY_VALUE0 + i)
            idelay_read[i] = self.read(WsGbtxControllerAddress.GET_IDELAY_VALUE0 + i)
            
        for i in range(10):
            assert idelay[i] == idelay_read[i], "idelay{0} value set is not consistent with read value: SET {1} GET {2}".format(i, idelay[i], idelay_read[i])
        return idelay_read

    def _load_bitslip(self, commitTransaction=True):
        """Loads the bitslip values for RX and TX in the GBTx controller"""
        self.write(WsGbtxControllerAddress.BITSLIP_LOAD, 1, commitTransaction=False)
        self.write(WsGbtxControllerAddress.BITSLIP_LOAD, 0, commitTransaction=commitTransaction)

    def set_bitslip_rx(self, value, commitTransaction=True):
        """sets the bitslip value in rx to be used on the GBTx module"""
        assert value | 0x7 == 0x7
        self.write(WsGbtxControllerAddress.BITSLIP_RX_VALUE, value, commitTransaction=False)
        self._load_bitslip(commitTransaction=commitTransaction)

    def get_bitslip_rx(self):
        """gets the bitslip value in rx to be used on the GBTx module"""
        return self.read(WsGbtxControllerAddress.BITSLIP_RX_VALUE)

    def set_bitslip_tx(self, value, commitTransaction=True):
        """sets the bitslip value in tx to be used on the GBTx module"""
        assert value | 0x7 == 0x7
        self.write(WsGbtxControllerAddress.BITSLIP_TX_VALUE, value, commitTransaction=False)
        self._load_bitslip(commitTransaction=commitTransaction)

    def get_bitslip_tx(self):
        """gets the bitslip value in tx to be used on the GBTx module"""
        return self.read(WsGbtxControllerAddress.BITSLIP_TX_VALUE)

    def set_tx_pattern(self, value, commitTransaction=True):
        """sets the transmission pattern to be used on the GBTx module"""
        value = TxPattern(value)
        self.write(WsGbtxControllerAddress.TX_PATTERN_SELECTION, value, commitTransaction=commitTransaction)

    def get_tx_pattern(self):
        """gets the transmission pattern to be used on the GBTx module"""
        return self.read(WsGbtxControllerAddress.TX_PATTERN_SELECTION)

    def set_loopback_gbtx0(self):
        """ Set GBTx0 to loopback packets received on GBTx0 downlink """
        self.set_tx_pattern(TxPattern.MIRROR)

    def set_loopback_gbtx1(self):
        """ Set GBTx1 to loopback packets received on GBTx0 downlink """
        self.set_tx1_pattern(TxPattern.MIRROR)

    def set_loopback(self):
        """Loops back the GBT packets"""
        # GBTx1 must be configured before GBTx0, otherwise SWT is lost
        self.set_loopback_gbtx1()
        self.set_loopback_gbtx0()

    def set_tx1_pattern(self, value, commitTransaction=True):
        """sets the transmission pattern to be used on the GBTx module"""
        assert value | 0x3 == 0x3
        self.write(WsGbtxControllerAddress.TX1_PATTERN_SELECTION, value, commitTransaction=commitTransaction)

    def get_tx1_pattern(self):
        """gets the transmission pattern to be used on the GBTx module"""
        return self.read(WsGbtxControllerAddress.TX1_PATTERN_SELECTION)

    def verify_configuration(self, reload_configuration=False):
        """verifies the configuration of the GBTx controller to investigate
        https://gitlab.cern.ch/alice-its-wp10-firmware/CRU_ITS/-/issues/158

        NOTE: to be used only for gbtx2_controller, via SWT. It can be used on the other gbtx_controller, if accessed via CANbus.
        On GBTx0, if the module is disabled or some IDELAYs are not correct, no SWT cannot be received. It can hence be accessed only via CANbus.
        """
        self.logger.warning("You are calling verify_configuration() - is issue #158 still open? If not, stop calling this function.")
        okay = True

        idelay_read = self.get_idelay()
        idelay_expected = 10*[450] # FROM gbtx_controller_pkg.vhd in RU_mainFPGA
        if idelay_read != idelay_expected:
            msg = f"Invalid IDELAY_VALUES found {idelay_read} != {idelay_expected}"
            self.logger.error(msg)
            if reload_configuration:
                self.logger.warning("You are reloading hardcoded GBTx Controller IDELAY values - are you sure you want this?")
                self.set_idelay(idelays=idelay_expected)
                self.logger.info("Reloaded!")
            else:
                raise Exception(msg)
            okay = False

        bitslip_tx_read = self.get_bitslip_tx()
        bitslip_tx_expected = 2
        if bitslip_tx_read != bitslip_tx_expected:
            msg = f"Invalid bitslip tx found {bitslip_tx_read} != {bitslip_tx_expected}"
            self.logger.error(msg)
            if reload_configuration:
                self.logger.warning("You are reloading hardcoded GBTx Controller Bitslip TX values - are you sure you want this?")
                self.set_bitslip_tx(bitslip_tx_expected)
                self.logger.info("Reloaded!")
            else:
                raise Exception(msg)
            okay = False

        bitslip_rx_read = self.get_bitslip_rx()
        bitslip_rx_expected = 0
        if bitslip_rx_read != bitslip_rx_expected:
            msg = f"Invalid bitslip rx found {bitslip_rx_read} != {bitslip_rx_expected}"
            self.logger.error(msg)
            if reload_configuration:
                self.logger.warning("You are reloading hardcoded GBTx Controller Bitslip RX values - are you sure you want this?")
                self.set_bitslip_rx(bitslip_rx_expected)
                self.logger.info("Reloaded!")
            else:
                raise Exception(msg)
            okay = False

        return okay

    def dump_config(self):
        """Dump the modules state and configuration as a string"""
        config_str = f"--- {self.name} module ---\n"
        self.board.comm.disable_rderr_exception()
        for address in WsGbtxControllerAddress:
            name = address.name
            try:
                value = self.read(address.value)
                config_str += "    - {0} : {1:#06X}\n".format(name, value)
            except:
                config_str += "    - {0} : FAILED\n".format(name)
        self.board.comm.enable_rderr_exception()
        return config_str
