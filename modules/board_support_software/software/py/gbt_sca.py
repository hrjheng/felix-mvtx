""" Generic SCA module
"""

from collections import OrderedDict
from enum import IntEnum, unique
from enum import IntFlag
from aenum import Enum, NoAlias

import logging


@unique
class ScaGpioRU(IntEnum):
    """GPIO mapping of the SCA.
    XCKU indicates connection with main FPGA of the RU
    PA3 indicated connection with the auxliary FPGA of the RU"""
    XCKU_TMR_RESET       = 0
    XCKU_TMR_RESERVED1   = 1
    XCKU_TMR_RESERVED2   = 2
    XCKU_TMR_RESERVED3   = 3
    XCKU_RESERVED4       = 4
    XCKU_RESERVED5       = 5
    XCKU_RESERVED6       = 6
    XCKU_RESERVED7       = 7
    XCKU_RESERVED8       = 8
    XCKU_RESERVED9       = 9
    XCKU_RESERVED10      = 10
    XCKU_RESERVED11      = 11
    PA3_START_PROGRAM    = 12
    PA3_PROGRAM_DONE     = 13
    PA3_RESET            = 14
    PA3_RESERVED0        = 15
    PA3_RESERVED1        = 16
    PA3_RESERVED2        = 17
    PA3_RESERVED3        = 18
    PA3_RESERVED4        = 19
    PROGRAM_B            = 23
    DONE                 = 24
    INIT_B               = 25


@unique
class ScaGpioDir(IntEnum):
    """
    Direction constant for GPIO on SCA
    (https://espace.cern.ch/GBT-Project/GBT-SCA/Manuals/Forms/AllItems.aspx)"""
    INPUT  = 0
    OUTPUT = 1


class ScaGpioDirRU(Enum):
    """
    Direction of GPIO pins on SCA
    Taken from top level XCKU, PA3 and https://twiki.cern.ch/twiki/pub/ALICE/ITS_WP10_RUV2/ITS_RUv2Manual.pdf
    """
    _settings_ = NoAlias
    XCKU_TMR_RESET     = ScaGpioDir.OUTPUT
    XCKU_TMR_RESERVED1 = ScaGpioDir.INPUT
    XCKU_TMR_RESERVED2 = ScaGpioDir.INPUT
    XCKU_TMR_RESERVED3 = ScaGpioDir.INPUT
    XCKU_RESERVED4     = ScaGpioDir.INPUT
    XCKU_RESERVED5     = ScaGpioDir.INPUT
    XCKU_RESERVED6     = ScaGpioDir.INPUT
    XCKU_RESERVED7     = ScaGpioDir.INPUT
    XCKU_RESERVED8     = ScaGpioDir.INPUT
    XCKU_RESERVED9     = ScaGpioDir.INPUT
    XCKU_RESERVED10    = ScaGpioDir.INPUT
    XCKU_RESERVED11    = ScaGpioDir.INPUT
    PA3_START_PROGRAM  = ScaGpioDir.OUTPUT
    PA3_PROGRAM_DONE   = ScaGpioDir.INPUT
    PA3_RESET          = ScaGpioDir.OUTPUT
    PA3_RESERVED0      = ScaGpioDir.OUTPUT
    PA3_RESERVED1      = ScaGpioDir.INPUT
    PA3_RESERVED2      = ScaGpioDir.INPUT
    PA3_RESERVED3      = ScaGpioDir.INPUT
    PA3_RESERVED4      = ScaGpioDir.INPUT
    PROGRAM_B          = ScaGpioDir.INPUT
    DONE               = ScaGpioDir.INPUT
    INIT_B             = ScaGpioDir.INPUT


@unique
class ScaChannel(IntEnum):
    """
    SCA channel mapping in the RU.

    NOTE: Copied from p17 of the GBT-SCA-UserManual.pdf v8.2
    (https://espace.cern.ch/GBT-Project/GBT-SCA/Manuals/Forms/AllItems.aspx)"""
    CTRL = 0x00  # SCA configuration registers
    SPI  = 0x01  # Serial Peripheral master Interface
    GPIO = 0x02  # Parallel I/O interface
    I2C0 = 0x03  # I2C Serial interface - master 0 (PA3)
    I2C1 = 0x04  # I2C Serial interface - master 1 (VTTx ch1)
    I2C2 = 0x05  # I2C Serial interface - master 2 (VTTx ch2)
    I2C3 = 0x06  # I2C Serial interface - master 3
    I2C4 = 0x07  # I2C Serial interface - master 4 (US)
    I2C5 = 0x08  # I2C Serial interface - master 5 (PA3)
    I2C6 = 0x09  # I2C Serial interface - master 6
    I2C7 = 0x0A  # I2C Serial interface - master 7 (GBTX)
    I2C8 = 0x0B  # I2C Serial interface - master 8
    I2C9 = 0x0C  # I2C Serial interface - master 9
    I2CA = 0x0D  # I2C Serial interface - master 10
    I2CB = 0x0E  # I2C Serial interface - master 11
    I2CC = 0x0F  # I2C Serial interface - master 12
    I2CD = 0x10  # I2C Serial interface - master 13
    I2CE = 0x11  # I2C Serial interface - master 14
    I2CF = 0x12  # I2C Serial interface - master 15
    JTAG = 0x13  # JTAG serial master interface
    ADC  = 0x14  # Analog to digital converter
    DAC  = 0x15  # Digital to analog converter


@unique
class ScaI2cChannelRU(IntEnum):
    """
    I2C channels in use on RU
    From: https://twiki.cern.ch/twiki/pub/ALICE/ITS_WP10_RUV2/ITS_RUv2Manual.pdf
    """
    PA3_0  = ScaChannel.I2C0
    VTTX_0 = ScaChannel.I2C1
    VTTX_1 = ScaChannel.I2C2
    VTRX2  = ScaChannel.I2C3 # Not present on RUv2
    US     = ScaChannel.I2C4
    PA3_1  = ScaChannel.I2C5
    GBTX   = ScaChannel.I2C7


@unique
class ScaCRB(IntEnum):
    """ Bitmapping of CRB register
        From: https://espace.cern.ch/GBT-Project/GBT-SCA/Manuals/GBT-SCA-UserManual.pdf section 5.1 """
    RESERVED = 0
    ENSPI    = 1
    ENGPIO   = 2
    ENI2C0   = 3
    ENI2C1   = 4
    ENI2C2   = 5
    ENI2C3   = 6
    ENI2C4   = 7


@unique
class ScaCRC(IntEnum):
    """ Bitmapping of CRC register
        From: https://espace.cern.ch/GBT-Project/GBT-SCA/Manuals/GBT-SCA-UserManual.pdf section 5.1 """
    ENI2C5   = 0
    ENI2C6   = 1
    ENI2C7   = 2
    ENI2C8   = 3
    ENI2C9   = 4
    ENI2CA   = 5
    ENI2CB   = 6
    ENI2CC   = 7

@unique
class ScaCRD(IntEnum):
    """ Bitmapping of CRD register
        From: https://espace.cern.ch/GBT-Project/GBT-SCA/Manuals/GBT-SCA-UserManual.pdf section 5.1 """
    ENI2CD    = 0
    ENI2CE    = 1
    ENI2CF    = 2
    ENJTAG    = 3
    ENADC     = 4
    RESERVED0 = 5
    RESERVED1 = 6
    RESERVED2 = 7


@unique
class ScaErrorFlag(IntFlag):
    """Sca error flag bit mapping"""
    GENERIC_ERROR_FLAG          = 0
    INVALID_CHANNEL_REQUEST     = 1
    INVALID_COMMAND_REQUEST     = 2
    INVALID_TRANSACTION_REQUEST = 3
    INVALID_LENGTH              = 4
    CHANNEL_NOT_ENABLED         = 5
    CHANNEL_CURRENTLY_BUSY      = 6
    COMMAND_IN_TREATMENT        = 7


class ScaBadErrorFlagError(Exception):
    """basic class to define an SCA error flag exception"""

    def __init__(self, status=None):
        self.status=status
        self.error_message = "ScaBadErrorFlagError: "
        self.get_error_message()
        super(ScaBadErrorFlagError, self).__init__(self.error_message)

    def get_error_message(self):
        for i in iter(ScaErrorFlag):
            # isolates individual errors
            if self.status>>i.value & 0x1 == 0x1:
                self.error_message += f"\n\t{ScaErrorFlag(i).name} - SCA Error Return: 0x{self.status:02X}"


@unique
class ScaI2cStatusFlag(IntFlag):
    """SCA I2C status bit mapping"""
    RESERVED0 = 0
    RESERVED1 = 1
    SUCC      = 2
    LEVERR    = 3
    EMPTY4    = 4
    INVCOM    = 5
    NOACK     = 6
    EMPTY7    = 7


@unique
class ScaI2cCmd(IntEnum):
    I2C_W_CTRL  = 0x30 # Write CONTROL register
    I2C_R_CTRL  = 0x31 # Read CONTROL register
    I2C_R_STR   = 0x11 # Read STATUS register
    I2C_W_MSK   = 0x20 # Write MASK register
    I2C_R_MSK   = 0x21 # Read MASK register
    I2C_W_DATA0 = 0x40 # Write data register bytes 0,1,2,3
    I2C_R_DATA0 = 0x41 # Read data register bytes 0,1,2,3
    I2C_W_DATA1 = 0x50 # Write data register bytes 4,5,6,7
    I2C_R_DATA1 = 0x51 # Write data register bytes 4,5,6,7
    I2C_W_DATA2 = 0x60 # Write data register bytes 8,9,10,11
    I2C_R_DATA2 = 0x61 # Write data register bytes 8,9,10,11
    I2C_W_DATA3 = 0x70 # Write data register bytes 12,13,14,15
    I2C_R_DATA3 = 0x71 # Write data register bytes 12,13,14,15
    I2C_S_7B_W  = 0x82 # Start I2C single byte write (7-bit addr)
    I2C_S_7B_R  = 0x86 # Start I2C single byte read (7-bit addr)
    I2C_S_10B_W = 0x8A # Start I2C single byte write (10-bit addr)
    I2C_S_10B_R = 0x8E # Start I2C single byte read (10-bit addr)
    I2C_M_7B_W  = 0xDA # Start I2C multi byte write (7-bit addr)
    I2C_M_7B_R  = 0xDE # Start I2C multi byte read (7-bit addr)
    I2C_M_10B_W = 0xE2 # Start I2C multi byte write (10-bit addr)
    I2C_M_10B_R = 0xE6 # Start I2C multi byte read (10-bit addr)
    #I2C_RMW_AND = # Address not specified in SCA manual??
    I2C_RMW_OR  = 0xC6 # Start I2C read-modify-write transaction with OR mask
    I2C_RMW_XOR = 0xCA # Start I2C read-modify-write transaction with XOR mask


@unique
class ScaI2cSpeed(IntEnum):
    """I2C communication speed"""
    f100kHz = 0
    f200kHz = 1
    f400kHz = 2
    f1MHz   = 3


@unique
class ScaI2cMode(IntEnum):
    """I2C communication speed"""
    OPEN_DRAIN = 0
    CMOS       = 1


@unique
class ScaAdcChannelsRUv1(IntEnum):
    """Naming for the SCA ADC channels as connected on the RUv1
    I_: current
    V_: voltage
    T_: temperature
    """
    I_MGT   = 0x00
    I_INT   = 0x01
    I_1V2   = 0x02
    I_1V5   = 0x03
    I_1V8   = 0x04
    I_2V5   = 0x05
    I_3V3   = 0x06
    I_IN    = 0x07
    V_MGT   = 0x08
    V_INT   = 0x09
    V_1V2   = 0x0A
    V_1V5   = 0x0B
    V_1V8   = 0x0C
    V_2V5   = 0x0D
    V_3V3   = 0x0E
    V_IN    = 0x0F
    I_VTRx1 = 0x10
    I_VTRx2 = 0x11
    T_1     = 0x17
    T_2     = 0x18
    T_INT   = 0x1F


@unique
class ScaAdcChannelsRUv2(IntEnum):
    """Naming for the SCA ADC channels as connected on the RUv2
    I_: current
    V_: voltage
    T_: temperature
    """
    I_INT   = 0x00
    I_MGT   = 0x01
    I_1V2   = 0x02
    I_1V5   = 0x03
    I_1V8   = 0x04
    I_2V5   = 0x05
    I_3V3   = 0x06
    I_IN    = 0x07
    V_INT   = 0x08
    V_MGT   = 0x09
    V_1V2   = 0x0A
    V_1V5   = 0x0B
    V_1V8   = 0x0C
    V_2V5   = 0x0D
    V_3V3   = 0x0E
    V_IN    = 0x0F
    I_VTRx1 = 0x10
    I_VTRx2 = 0x11
    T_1     = 0x17
    T_2     = 0x18
    T_INT   = 0x1F


@unique
class ScaAdcCmd(IntEnum):
    ADC_GO     = 0x02 # Start of conversion
    ADC_W_MUX  = 0x50 # Set input ADC mux
    ADC_R_MUX  = 0x51 # Get input ADC mux
    ADC_W_CURR = 0x60 # Set channels that should have current source enabled
    ADC_R_CURR = 0x61 # Get channels that should have current source enabled
    ADC_W_GAIN = 0x10 # Set gain correction
    ADC_R_GAIN = 0x11 # Read gain correction
    ADC_R_DATA = 0x21 # Read value of latest conversion
    ADC_R_RAW  = 0x31 # Read raw value of conversion
    ADC_R_OFS  = 0x41 # Get offset of latest conversion


@unique
class ScaCtrlCmd(IntEnum):
    CTRL_W_CRB   = 0x02 # write control register B
    CTRL_R_CRB   = 0x03 # read control register B
    CTRL_W_CRC   = 0x04 # write control register C
    CTRL_R_CRC   = 0x05 # read control register C
    CTRL_W_CRD   = 0x06 # write control register D
    CTRL_R_CRD   = 0x07 # read control register D
    CTRL_R_SEU   = 0xF1 # read SEU counter (needs to go to channel 0x13)
    CTRL_R_ID_V1 = 0x91 # Read the chip ID for SCA V1 (needs to go to channel 0x14)
    CTRL_R_ID_V2 = 0xD1 # Read the chip ID for SCA V2 (needs to go to channel 0x14)
    CTRL_C_SEU   = 0xF0 # reset SEU counter (needs to go to channel 0x13)


class ScaI2cBadStatusError(Exception):
    """basic class to define an SCA I2C error exception"""

    def __init__(self, status=None):
        self.status=status
        self.error_message = "ScaI2cBadStatusError: "
        self.get_error_message()
        super(ScaI2cBadStatusError, self).__init__(self.error_message)

    def get_error_message(self):
        self.error_message += f"Status 0x{self.status:02X}"
        for i in iter(ScaI2cStatusFlag):
            # isolates individual errors
            if self.status>>i.value & 0x1 == 0x1:
                self.error_message += f" {ScaI2cStatusFlag(i).name}"

    def is_leverr(self):
        return self.status >> ScaI2cStatusFlag.LEVERR & 0x1 == 0x1

    def is_noack(self):
        return self.status >> ScaI2cStatusFlag.NOACK & 0x1 == 0x1


class Sca(object):
    """Class to handle SCA transactions"""

    def __init__(self,
                 use_adc=True,
                 use_gpio=True,
                 use_jtag=True,
                 use_gbtx_i2c=True,
                 use_pa3_i2c=True,
                 use_pa3_i2c_2=True,
                 use_us_i2c=False,
                 is_on_ruv1=False,
                 is_on_ruv2_0=True):
        self.logger = logging.getLogger("SCA")

        self.use_adc = use_adc
        self.use_gpio = use_gpio
        self.use_jtag = use_jtag
        self.use_gbtx_i2c = use_gbtx_i2c
        self.use_pa3_i2c = use_pa3_i2c
        self.use_pa3_i2c_2 = use_pa3_i2c_2
        self.use_us_i2c = use_us_i2c

        assert not(is_on_ruv1 and is_on_ruv2_0), "RU cannot be RUv1 and RUv2.0! (is_on_ruv1: {0}, is_on_ruv2_0: {1})".format(is_on_ruv1, is_on_ruv2_0)

        self.adc_channels = None
        self._set_adc_channels(is_on_ruv1)

        self.adc_correction_factor = None
        self._set_adc_correction_factor(is_on_ruv2_0)

        self.gbtx_i2c_speed = ScaI2cSpeed.f100kHz

    def initialize(self, gbtx_i2c_speed=None):
        self.init_communication()
        self.enable_channel(ADC=self.use_adc,
                            GPIO=self.use_gpio,
                            JTAG=self.use_jtag,
                            I2C_GBTX=self.use_gbtx_i2c,
                            I2C_PA3_0=self.use_pa3_i2c,
                            I2C_PA3_1=self.use_pa3_i2c_2,
                            I2C_US=self.use_us_i2c)
        if self.use_adc:
            self.initialize_adc_channel()
        if self.use_gpio:
            self.initialize_gpio_channel()

        if gbtx_i2c_speed is None:
            self.initialize_i2c_channel(channel=ScaI2cChannelRU.GBTX, speed=self.gbtx_i2c_speed)
        else:
            self.initialize_i2c_channel(channel=ScaI2cChannelRU.GBTX, speed=gbtx_i2c_speed)

    def _lock_comm(self):
        """Method allowing (but not forcing if not needed) to implement a locking mechanism in derived classes"""
        pass

    def _unlock_comm(self):
        """Method allowing (but not forcing if not needed) to implement a locking mechanism in derived classes"""
        pass

    def initialize_gpio_channel(self):
        gpio_direction = 0
        for pos, direction in zip(list(ScaGpioRU), list(ScaGpioDirRU)):
            gpio_direction |= direction.value << pos.value
        self.set_gpio_direction(gpio_direction)

    def _set_adc_channels(self, is_on_ruv1):
        """Sets the adc_channels attribute for the GBT SCA.
        Since the mapping is different between RUv1 and RUv2,
        """
        if is_on_ruv1:
            self.adc_channels = ScaAdcChannelsRUv1
        else:
            self.adc_channels = ScaAdcChannelsRUv2

    def _set_adc_correction_factor(self,is_on_ruv2_0):
        """Sets the adc correction factor which is specific to RUv2.0
        For the other boards the factor is 1.0, i.e. no correction"""
        if is_on_ruv2_0:
            # I_In has wrong shunt resistor on RUv2, needs corrected by 20%
            self.adc_correction_factor = 0.8
        else:
            self.adc_correction_factor = 1.0

    def _sca_write(self, channel, length, command, scadata, trid=0x12, commitTransaction=True, wait=400):
        """Implementation of writing to SCA"""
        raise NotImplementedError

    def _sca_read(self):
        """Implementation of reading from SCA"""
        raise NotImplementedError

    def init_communication(self):
        """Implementation to initialize communication with SCA"""
        raise NotImplementedError

    def enable_channel(self, SPI=0, GPIO=0, I2C_PA3_0=0, I2C_PA3_1=0,
                       I2C_VTTX_0=0, I2C_VTTX_1=0, I2C_VTRX2=0,
                       I2C_US=0, I2C_GBTX=0, JTAG=0, ADC=0):
        CRB = (SPI<<ScaCRB.ENSPI) | (GPIO<<ScaCRB.ENGPIO) | (I2C_PA3_0<<ScaCRB.ENI2C0) | (I2C_VTTX_0<<ScaCRB.ENI2C1) | \
              (I2C_VTTX_1<<ScaCRB.ENI2C2) | (I2C_VTRX2<<ScaCRB.ENI2C3) | (I2C_US<<ScaCRB.ENI2C4)
        CRC = (I2C_PA3_1<<ScaCRC.ENI2C5) | (I2C_GBTX<<ScaCRC.ENI2C7)
        CRD = (JTAG<<ScaCRD.ENJTAG) | (ADC<<ScaCRD.ENADC)

        CRB = CRB<<24
        CRC = CRC<<24
        CRD = CRD<<24

        self._lock_comm()
        try:
            self._sca_write(channel=ScaChannel.CTRL, length=1, command=ScaCtrlCmd.CTRL_W_CRB, scadata=CRB)
            self._sca_write(channel=ScaChannel.CTRL, length=1, command=ScaCtrlCmd.CTRL_W_CRC, scadata=CRC)
            self._sca_write(channel=ScaChannel.CTRL, length=1, command=ScaCtrlCmd.CTRL_W_CRD, scadata=CRD)
        finally:
            self._unlock_comm()

    def initialize_i2c_channel(self, channel, speed=ScaI2cSpeed.f1MHz):
        """
        Sets the I2C transactions speed to 1MHz,
        with no multi byte operation and
        no scl mode
        """
        self.set_i2c_w_ctrl_reg(channel=channel, speed=speed, nbytes=0, sclmode=0)

    def set_i2c_w_ctrl_reg(self, channel, speed, nbytes, sclmode):
        """GBT sca manual page 23 v8.2"""
        speed =  ScaI2cSpeed(speed) # Assert if not in value
        assert nbytes in range(17)
        assert sclmode in range(2)
        assert channel not in [ScaChannel.CTRL, ScaChannel.SPI, ScaChannel.GPIO, ScaChannel.ADC, ScaChannel.DAC], "Only writing to I2C channels allowed with this function"

        data = sclmode<<7|nbytes<<2|speed.value
        data = data<<24 # uses uppermost bits

        self._sca_write(channel=channel, length=1, command=ScaI2cCmd.I2C_W_CTRL, scadata=data, wait=400)

    def get_i2c_w_ctrl_reg(self, channel):
        """Return I2C Control Reg"""
        assert channel not in [ScaChannel.CTRL, ScaChannel.SPI, ScaChannel.GPIO, ScaChannel.ADC, ScaChannel.DAC], "Only writing to I2C channels allowed with this function"
        self._sca_write(channel=channel, length=1, command=ScaI2cCmd.I2C_R_CTRL, scadata=0x0)
        val = self._sca_read() >> 24
        sclmode = val >> 7 & 0x1
        nbytes = val >> 2 & 0x1F
        speed = val & 0x3
        return speed, nbytes, sclmode

    def read_i2c_w_ctrl_reg(self, channel):
        speed, nbytes, sclmode = self.get_i2c_w_ctrl_reg(channel)
        return ScaI2cSpeed(speed).name, nbytes, ScaI2cMode(sclmode).name

    def initialize_adc_channel(self):
        """Sets the channels where the 100uA current source should be enabled (The temp sensors)"""
        data = 0
        for ch in self.adc_channels:
            if ch.name.startswith("T_") and ch.name != "T_INT":
                data |= 1 << ch
        self._sca_write(channel=ScaChannel.ADC, length=4, command=ScaAdcCmd.ADC_W_CURR, scadata=data)

    def set_adc_channel(self, channel, commitTransaction=True):
        """Sets the adc channel to the correct MUX channel"""
        assert channel in range(32), " Channel must be between 0 and 31"
        self._sca_write(channel=ScaChannel.ADC, length=4, command=ScaAdcCmd.ADC_W_MUX, scadata=channel, commitTransaction=commitTransaction)

    def read_adc_channel(self, channel):
        """Expected wait time for ADC read: 9000 cycles"""
        self._lock_comm()
        try:
            self.set_adc_channel(channel, commitTransaction=True)
            self._sca_write(channel=ScaChannel.ADC, length=4, command=ScaAdcCmd.ADC_GO, scadata=1, commitTransaction=True, wait=20000) # ADC go command
            ret = self._sca_read()
        finally:
            self._unlock_comm()
        return ret

    def read_adc_channel_ext(self, channel):
        """Expected wait time for ADC read: 9000 cycles"""
        self._lock_comm()
        try:
            self.set_adc_channel(channel, commitTransaction=True)
            retval = []
            self._sca_write(channel=ScaChannel.ADC, length=4, command=ScaAdcCmd.ADC_GO, scadata=1, commitTransaction=True, wait=20000) # ADC go command
            retval.append(['Data', self._sca_read()])
            self._sca_write(channel=ScaChannel.ADC, length=4, command=ScaAdcCmd.ADC_R_RAW, scadata=1, commitTransaction=True, wait=400)
            retval.append(['Raw', self._sca_read()])
            self._sca_write(channel=ScaChannel.ADC, length=4, command=ScaAdcCmd.ADC_R_OFS, scadata=1, commitTransaction=True, wait=400)
            retval.append(['Offset', self._sca_read()])
        finally:
            self._unlock_comm()
        return retval

    def get_adc_gain(self):
        """Get the gain setting for the ADCs (default loaded from efuses"""
        self._lock_comm()
        try:
            self._sca_write(channel=ScaChannel.ADC, length=4, command=ScaAdcCmd.ADC_R_GAIN, scadata=1, commitTransaction=True, wait=400)
            ret = self._sca_read()
        finally:
            self._unlock_comm()
        return ret

    def set_adc_gain(self, gain):
        """Set the gain setting for the ADCs (default loaded from efuses"""
        assert gain | 0xFF == 0xFF
        self._sca_write(channel=ScaChannel.ADC, length=4, command=ScaAdcCmd.ADC_W_GAIN, scadata=1, commitTransaction=True, wait=400)

    def read_gpio(self):
        self._lock_comm()
        try:
            self._sca_write(channel=ScaChannel.GPIO, length=1, command=0x01, scadata=0) # GPIO_R_DATAIN
            ret = self._sca_read()
        finally:
            self._unlock_comm()
        return ret

    def write_gpio(self, value):
        """Writes GPIOs set to output"""
        self._sca_write(channel=ScaChannel.GPIO, length=4, command=0x10, scadata=value)

    def set_gpio_direction(self, value):
        """Sets the direction for the GPIO pin of the SCA.
        value is a one-hot bit array with position n indicating GPIO n
        if the bit is set to 1, the pin is an output,
        if the bit is set to 0, the pin is an input"""
        assert value | 0xFFFFF == 0xFFFFF
        self._sca_write(channel=ScaChannel.GPIO, length=4, command=0x20, scadata=value)

    def set_gpio(self, index, value, verbose=False):
        """overwrites the value in the index with the value in the SCA gpio"""
        assert value in range(2)
        assert index in iter(ScaGpioRU)
        actual_value = self.read_gpio()
        if value == 0:
            altered_value = ~(1 << index) & actual_value
        else:
            altered_value = (1 << index) | actual_value
        if verbose:
            self.logger.info("Got SCA GPIO {0:#06X} and set to {1:#06X}".format(actual_value, altered_value))
        self.write_gpio(altered_value)

    def get_gpio(self):
        """Returns GPIO pin status and names"""
        data = self.read_gpio()
        retval = {}
        for flag in ScaGpioRU:
            retval[flag.name] = (data >> flag.value) & 0x1
        return retval

    def reset_xcku(self):
        """Resets the main FPGA"""
        self.logger.debug("Resetting XCKU")
        for i in [1,0]:
            self.set_xcku_reset(i)

    def set_xcku_reset(self, value):
        """XCKU reset via SCA"""
        self.set_gpio(index=ScaGpioRU.XCKU_TMR_RESET, value=value)

    def is_xcku_programmed(self):
        return self.get_gpio()[ScaGpioRU.DONE.name] == 1

    def is_config_sequence_initiated(self):
        return self.get_gpio()[ScaGpioRU.PROGRAM_B.name] == 0

    def is_xcku_in_config_state(self):
        return self.get_gpio()[ScaGpioRU.INIT_B.name] == 0

    def get_xcku_program_state(self):
        done = self.get_gpio()[ScaGpioRU.DONE.name]
        program_b = self.get_gpio()[ScaGpioRU.PROGRAM_B.name]
        init_b = self.get_gpio()[ScaGpioRU.INIT_B.name]
        return done, program_b, init_b

    def log_xcku_program_state(self):
        done, program_b, init_b = self.get_xcku_program_state()
        self.logger.info("\n"
                         f"\t\t\t\t\tPROGRAM_B:\t{program_b}\n"
                         f"\t\t\t\t\tINIT_B:\t\t{init_b}\n"
                         f"\t\t\t\t\tDONE:\t\t{done}"
        )

    def _write_spi(self, slave_select, nbits, data0=0, data1=0, data2=0, data3=0):
        """Perform a SPI write of "nbits" on SCA channel "channel" with slave_select as SPI slave select (8bit)
        Up to 16 bytes can be sent, to be filled into data0 - data3 as follows:
        """

        self._lock_comm()
        try:
            data = 19
            self._sca_write(channel=ScaChannel.SPI, length=6, command=0x50, scadata=data, wait=400)

            assert nbits in range(128+1), "Max 128 bits allowed"

            if nbits > 96:
                self._sca_write(channel=ScaChannel.SPI, length=6, command=0x30, scadata=data3)
            if nbits > 64:
                self._sca_write(channel=ScaChannel.SPI, length=6, command=0x20, scadata=data2, wait=400)
            if nbits > 32:
                self._sca_write(channel=ScaChannel.SPI, length=6, command=0x10, scadata=data1, wait=400)
            if nbits > 0:
                self._sca_write(channel=ScaChannel.SPI, length=6, command=0x00, scadata=data0, wait=400)

            # write control register
            data = (nbits & 0x00ff) | (0x30 << 8)
            self._sca_write(channel=ScaChannel.SPI, length=6, command=0x40, scadata=data, wait=400)

            # enable targeted slave select
            data = ((1 << slave_select) & 0xff)
            self._sca_write(channel=ScaChannel.SPI, length=6, command=0x60, scadata=data, wait=400)

            # start write
            self._sca_write(channel=ScaChannel.SPI, length=2, command=0x72, scadata=data, wait=400)

            status = self._sca_read()
        finally:
            self._unlock_comm()
        return status

    def _read_spi(self, slave_select, nbits):
        """Perform a SPI read of "nbits" on SCA channel "channel" with slave_select as SPI slave select (8bit)
        For all other nbyte values, the return is a tuple of up to five 32bit unsigned integers as follows:
        """
        self._lock_comm()
        try:
            assert nbits in range(128+1), "Max 128 bits allowed"
            results = []
            # write control register
            data = (nbits & 0x00ff) | (0x30 << 8)
            self._sca_write(channel=ScaChannel.SPI, length=6, command=0x40, scadata=data, wait=400)

            # enable targeted slave select
            data = ((1 << slave_select) & 0xff)
            self._sca_write(channel=ScaChannel.SPI, length=6, command=0x60, scadata=data, wait=400)

            # start read
            self._sca_write(channel=ScaChannel.SPI, length=2, command=0x72, scadata=data, wait=400)

            # return read value is status in upper 8 bits
            results.append(self._sca_read())
            if nbits > 0:
                self._sca_write(channel=ScaChannel.SPI, length=2, command=0x01, scadata=0, wait=10000)
                results.append(self._sca_read())
            if nbits > 4:
                self._sca_write(channel=ScaChannel.SPI, length=2, command=0x11, scadata=0, wait=10000)
                results.append(self._sca_read())
            if nbits > 8:
                self._sca_write(channel=ScaChannel.SPI, length=2, command=0x21, scadata=0, wait=10000)
                results.append(self._sca_read())
            if nbits > 12:
                self._sca_write(channel=ScaChannel.SPI, length=2, command=0x31, scadata=0, wait=10000)
                results.append(self._sca_read())
        finally:
            self._unlock_comm()
        return(results)

    def _write_i2c(self, channel, sl_addr, nbytes, data0=0, data1=0, data2=0, data3=0):
        """Perform a I2C write of "nbytes" on SCA channel "channel" to I2C slave address "sl_addr" (7bit)
        Up to 16 bytes can be sent, to be filled into data0 - data3 as follows:
        data0 = byte0<<24  | byte1<<16  | byte2<<8  | byte3
        data1 = byte4<<24  | byte5<<16  | byte6<<8  | byte7
        data2 = byte8<<24  | byte9<<16  | byte10<<8 | byte11
        data3 = byte12<<24 | byte13<<16 | byte14<<8 | byte15
        """
        assert channel not in [ScaChannel.CTRL, ScaChannel.SPI, ScaChannel.GPIO, ScaChannel.ADC, ScaChannel.DAC], "Only writing to I2C channels allowed with this function"
        assert nbytes | 0xFFFF == 0xFFFF, "Max 16 bytes allowed"
        self._lock_comm()
        try:
            if nbytes == 1:
                data = ((sl_addr & 0x7f)<<24) | ((data0 & 0xff000000)>>8)
                # I2C_S_7B_W needs 20 us (3200) wait to be executed @ 1 MHz
                self._sca_write(channel=channel, length=2, command=ScaI2cCmd.I2C_S_7B_W, scadata=data, wait=3500)
                status = self._sca_read()
                if (status & 0xff000000) != 0x04000000:
                    raise ScaI2cBadStatusError(status>>24)
                return

            if nbytes > 12:
                self._sca_write(channel=channel, length=4, command=ScaI2cCmd.I2C_W_DATA3, scadata=data3, wait=800)
            if nbytes > 8:
                self._sca_write(channel=channel, length=4, command=ScaI2cCmd.I2C_W_DATA2, scadata=data2, wait=800)
            if nbytes > 4:
                self._sca_write(channel=channel, length=4, command=ScaI2cCmd.I2C_W_DATA1, scadata=data1, wait=800)
            if nbytes > 0:
                self._sca_write(channel=channel, length=4, command=ScaI2cCmd.I2C_W_DATA0, scadata=data0, wait=800)

            # Update control register for multi byte write
            speed, _, sclmode = self.get_i2c_w_ctrl_reg(channel=channel)
            self.set_i2c_w_ctrl_reg(channel=channel, speed=speed, nbytes=nbytes, sclmode=sclmode)

            # Start multibyte write
            data = ((sl_addr & 0x7f)<<24)
            self._sca_write(channel=channel, length=1, command=ScaI2cCmd.I2C_M_7B_W, scadata=data, wait=40000)

            status = self._sca_read()
        finally:
            self._unlock_comm()
        if (status & 0xff000000) != 0x04000000:
            raise ScaI2cBadStatusError(status>>24)

    def _read_i2c(self, channel, sl_addr, nbytes):
        """Perform a I2C read of "nbytes" on SCA channel "channel" from I2C slave address "sl_addr" (7bit)
        If nbytes==1 the value returned contains (status<<24 | byte0<<16)
        For all other nbyte values, the return is a tuple of up to five 32bit unsigned integers as follows:
        data0 = status<<24
        data1 = byte0<<24  | byte1<<16  | byte2<<8  | byte3
        data2 = byte4<<24  | byte5<<16  | byte6<<8  | byte7
        data3 = byte8<<24  | byte9<<16  | byte10<<8 | byte11
        data4 = byte12<<24 | byte13<<16 | byte14<<8 | byte15
        """
        assert channel not in [ScaChannel.CTRL, ScaChannel.SPI, ScaChannel.GPIO, ScaChannel.ADC, ScaChannel.DAC], "Only writing to I2C channels allowed with this function"
        assert nbytes | 0xFFFF == 0xFFFF, "Max 16 bytes allowed"
        self._lock_comm()
        try:
            results = []
            if nbytes == 1:
                data = ((sl_addr & 0x7f)<<24)
                self._sca_write(channel=channel, length=1, command=ScaI2cCmd.I2C_S_7B_R, scadata=data, wait=20000)
                results.append(self._sca_read())
                status = results[0]
                if (status & 0xff000000) != 0x04000000:
                    raise ScaI2cBadStatusError(status>>24)
                return(results)
            else:
                #print("Reading {0} bytes from I2C".format(nbytes))

                # Update control register for multi byte write
                speed, _, sclmode = self.get_i2c_w_ctrl_reg(channel=channel)
                self.set_i2c_w_ctrl_reg(channel=channel, speed=speed, nbytes=nbytes, sclmode=sclmode)
                # Start multibyte read
                data = (sl_addr & 0x7f)<<24
                self._sca_write(channel=channel, length=4, command=ScaI2cCmd.I2C_M_7B_R, scadata=data, wait=40000)
                # return read value is status in upper 8 bits
                results.append(self._sca_read())
                if nbytes > 0:
                    self._sca_write(channel=channel, length=4, command=ScaI2cCmd.I2C_R_DATA3, scadata=0, wait=800)
                    results.append(self._sca_read())
                if nbytes > 4:
                    self._sca_write(channel=channel, length=4, command=ScaI2cCmd.I2C_R_DATA2, scadata=0, wait=800)
                    results.append(self._sca_read())
                if nbytes > 8:
                    self._sca_write(channel=channel, length=4, command=ScaI2cCmd.I2C_R_DATA1, scadata=0, wait=800)
                    results.append(self._sca_read())
                if nbytes > 12:
                    self._sca_write(channel=channel, length=4, command=ScaI2cCmd.I2C_R_DATA0, scadata=0, wait=800)
                    results.append(self._sca_read())
        finally:
            self._unlock_comm()
        return(results)

    def read_us_i2c(self):
        """Read 1 byte from Ultrascale I2C channel at the test slave address 0101000"""
        result = self._read_i2c(channel=ScaI2cChannelRU.US, sl_addr=0x28, nbytes=1)
        return((result[0] >> 16) & 0xff)

    def write_us_i2c(self, val):
        """Write 1 byte to Ultrascale I2C channel at the test slave address 0101000"""
        data0 = (val & 0xff) << 24
        self._write_i2c(channel=ScaI2cChannelRU.US, sl_addr=0x28, nbytes=1, data0=data0)

    def get_adc_names(self):
        """Returns the ADC names and channel"""
        return [adc.name for adc in self.adc_channels]

    def _adc_code_to_voltage(self, adc, code):
        """From https://twiki.cern.ch/twiki/pub/ALICE/ITS_WP10_RUV2/ITS_RUv2Manual.pdf"""
        if isinstance(adc, str):
            adc = self.adc_channels[adc]
        assert adc.name.startswith('V_')
        if adc is self.adc_channels.V_IN:
            return 21.0 * code / 4095.0
        if adc in [self.adc_channels.V_3V3,
                   self.adc_channels.V_2V5]:
            return 5.0 * code / 4095.0
        else:
            return 2.0 * code / 4095.0

    def _adc_code_to_current(self, adc, code):
        """From https://twiki.cern.ch/twiki/pub/ALICE/ITS_WP10_RUV2/ITS_RUv2Manual.pdf"""
        if isinstance(adc, str):
            adc = self.adc_channels[adc]
        assert adc.name.startswith('I_')
        if adc is self.adc_channels.I_IN:
            return self.adc_correction_factor * 5.0 * code / 4095.0
        if adc in [self.adc_channels.I_VTRx1,
                   self.adc_channels.I_VTRx2]:
            return 1e6*(2.5 - ((code/4095)*69/22))/4700
        else:
            return 5.0 * code / 4095.0

    def _adc_code_to_temperature(self, adc, code):
        """From https://twiki.cern.ch/twiki/pub/ALICE/ITS_WP10_RUV2/ITS_RUv2Manual.pdf
        and https://its.cern.ch/jira/browse/GBTSUPPORT-373"""
        constant_I_uA = 100  # expected: 100uA
        if isinstance(adc, str):
            adc = self.adc_channels[adc]
        assert adc.name.startswith('T_')
        if adc is self.adc_channels.T_INT:
            return (716 - 1000*code / 4095.0) / 1.829
        else:
            return (code * 1000000) / (4095 * 3.85 * constant_I_uA) - 259.74

    def adc_code_to_float(self, adc, code):
        """From https://twiki.cern.ch/twiki/pub/ALICE/ITS_WP10_RUV2/ITS_RUv2Manual.pdf"""
        if isinstance(adc, str):
            adc = self.adc_channels[adc]
        if adc in [self.adc_channels.T_1,
                   self.adc_channels.T_2,
                   self.adc_channels.T_INT]:
            return self._adc_code_to_temperature(adc, code)
        elif adc in [self.adc_channels.V_INT,
                     self.adc_channels.V_MGT,
                     self.adc_channels.V_1V2,
                     self.adc_channels.V_1V5,
                     self.adc_channels.V_1V8,
                     self.adc_channels.V_2V5,
                     self.adc_channels.V_3V3,
                     self.adc_channels.V_IN]:
            return self._adc_code_to_voltage(adc, code)
        elif adc in [self.adc_channels.I_INT,
                     self.adc_channels.I_MGT,
                     self.adc_channels.I_1V2,
                     self.adc_channels.I_1V5,
                     self.adc_channels.I_1V8,
                     self.adc_channels.I_2V5,
                     self.adc_channels.I_3V3,
                     self.adc_channels.I_IN,
                     self.adc_channels.I_VTRx1,
                     self.adc_channels.I_VTRx2]:
            return self._adc_code_to_current(adc, code)
        else:
            raise NotImplementedError

    def read_adc_converted(self, adc):
        """Reads one ADC and converts it into the correct float value"""
        if isinstance(adc, str):
            adc = self.adc_channels[adc]
        return self.adc_code_to_float(adc,
                                      self.read_adc_channel(adc.value))

    def read_adcs(self):
        """Reads all the ADCs in the ADC list"""
        results = OrderedDict()
        for adc in self.adc_channels:
            results[adc.name] = self.read_adc_channel(adc.value)
        return results

    def read_adcs_conv(self):
        """Reads the ADC values and converts them into the correct read value"""
        results = OrderedDict()
        for adc in self.adc_channels:
            results[adc.name] = self.adc_code_to_float(adc,
                                                       self.read_adc_channel(adc.value))
        return results

    def get_adc_unit_of_measurement(self, adc):
        if isinstance(adc, str):
            adc = self.adc_channels[adc]
        if adc.name.startswith("I_VTRx"):
            uom = "uA"
        elif adc.name.startswith("I_"):
            uom = "A"
        elif adc.name.startswith("V_"):
            uom = "V"
        elif adc.name.startswith("T_"):
            uom = "C"
        else:
            raise NotImplementedError(adc.name)
        return uom

    def log_adcs_reads(self, raw_reads):
        """Logs the ADC read values provided"""
        for key, value in raw_reads.items():
            uom = self.get_adc_unit_of_measurement(key)
            msg = "{0}:\t{1:.2f} {2}".format(key, value, uom)
            self.logger.info(msg)

    def log_adcs(self):
        """Logs the ADC values converted"""
        results = self.read_adcs_conv()
        self.log_adcs_reads(results)

    def get_seu_counter(self):
        """Gets SCA SEU counter
        From: https://espace.cern.ch/GBT-Project/GBT-SCA/Manuals/GBT-SCA-UserManual.pdf section 5.2 """
        self._sca_write(channel=ScaChannel.JTAG, length=1, command=ScaCtrlCmd.CTRL_R_SEU, scadata=0)
        return self._sca_read()

    def reset_seu_counter(self):
        """Resets SCA SEU counter
        From: https://espace.cern.ch/GBT-Project/GBT-SCA/Manuals/GBT-SCA-UserManual.pdf section 5.2 """
        self._sca_write(channel=ScaChannel.JTAG, length=1, command=ScaCtrlCmd.CTRL_C_SEU, scadata=0)

    def get_control_register_CRB(self):
        """Read Control register CRB"""
        self._lock_comm()
        try:
            self._sca_write(channel=ScaChannel.CTRL, length=4, command=ScaCtrlCmd.CTRL_R_CRB, scadata=0)
            value = self._sca_read()>>24
        finally:
            self._unlock_comm()
        ret = {}
        for item in ScaCRB:
            ret[item.name] = (value >> item.value) & 0x1
        return ret

    def get_control_register_CRC(self):
        """Read Control register CRC"""
        self._lock_comm()
        try:
            self._sca_write(channel=ScaChannel.CTRL, length=4, command=ScaCtrlCmd.CTRL_R_CRC, scadata=0)
            value = self._sca_read()>>24
        finally:
            self._unlock_comm()
        ret = {}
        for item in ScaCRC:
            ret[item.name] = (value >> item.value) & 0x1
        return ret

    def get_control_register_CRD(self):
        """Read Control register CRD"""
        self._lock_comm()
        try:
            self._sca_write(channel=ScaChannel.CTRL, length=4, command=ScaCtrlCmd.CTRL_R_CRD, scadata=0)
            value = self._sca_read()>>24
        finally:
            self._unlock_comm()
        ret = {}
        for item in ScaCRD:
            ret[item.name] = (value >> item.value) & 0x1
        return ret

    def get_id(self):
        """Gets SCA unique chip id"""
        return self._get_id_v2()

    def _get_id_v1(self):
        """Gets SCA unique chip id for SCA v1
        From: https://espace.cern.ch/GBT-Project/GBT-SCA/Manuals/GBT-SCA-UserManual.pdf section 5.2 """
        self._lock_comm()
        try:
            self._sca_write(channel=ScaChannel.ADC, length=1, command=ScaCtrlCmd.CTRL_R_ID_V1, scadata=0)
            ret = self._sca_read()
        finally:
            self._unlock_comm()
        return ret

    def _get_id_v2(self):
        """Gets SCA unique chip id for SCA v2
        From: https://espace.cern.ch/GBT-Project/GBT-SCA/Manuals/GBT-SCA-UserManual.pdf section 5.2 """
        self._lock_comm()
        try:
            self._sca_write(channel=ScaChannel.ADC, length=1, command=ScaCtrlCmd.CTRL_R_ID_V2, scadata=0)  # CTRL_R_ID
            ret = self._sca_read()
        finally:
            self._unlock_comm()
        return ret

    # GBTx I2C functions

    def read_gbtx_register(self, register, gbtx_index=0, check=True):
        """Read GBTx register "register" from GBTx "gbtx_index" """
        assert gbtx_index in range(3)
        sl_addr = gbtx_index*2+1
        data0 = ((register&0xff)<<24) | ((register&0xff00)<<8)
        self._lock_comm()
        try:
            self._write_i2c(channel=ScaI2cChannelRU.GBTX, sl_addr=sl_addr, nbytes=2, data0=data0)
            result = self._read_i2c(channel=ScaI2cChannelRU.GBTX, sl_addr=sl_addr, nbytes=1)
        finally:
            self._unlock_comm()
        return((result[0]>>16)&0xff)

    def write_gbtx_register(self, register, value, gbtx_index=0, check=True):
        """Write "value" (8bit) to register "register" of GBTx "gbtx_index" """
        assert gbtx_index in range(3)
        sl_addr = gbtx_index*2+1
        data0 = ((register&0xff)<<24) | ((register&0xff00)<<8) | ((value&0xff)<<8)
        self._write_i2c(channel=ScaI2cChannelRU.GBTX, sl_addr=sl_addr, nbytes=3, data0=data0)

    def write_gbtx_register_and_check(self, register, value, gbtx_index=0, retry=True):
        """Write "value" (8bit) to register "register" of GBTx "gbtx_index" """
        retry_transaction = True
        timeout_counter = 0
        while retry_transaction:
            error = False
            try:
                self.write_gbtx_register(register, value, gbtx_index)
            except ScaI2cBadStatusError:
                self.logger.warning(f"ScaI2cBadStatusError GBTx {gbtx_index} reg: {register}")
                timeout_counter += 1
                if retry:
                    if timeout_counter > 100:
                        raise Exception("SCA GBTx I2C Transaction timed out - GBTx {gbtx_index} reg: {register}")
                    else:
                        retry_transaction = True
                        self.logger.info("Retrying transaction data {data}")
                        continue
            readback = self.read_gbtx_register(register, gbtx_index)
            if value != readback:
                self.logger.warning(f"readback got wrong value. exp: {value}, got: {readback}. Index: {gbtx_index}, register: {register}")
                error = True
            if error and retry:
                timeout_counter += 1
                if timeout_counter > 100:
                    raise Exception("SCA GBTx I2C Transaction timed out")
                else:
                    retry_transaction = True
                    self.logger.info("Retrying transaction data {data}")
            elif error:
                raise Exception("SCA GBTx I2C Transaction failed")
            else:
                retry_transaction = False

    def check_gbtx_register(self, register, expected_data, gbtx_index=0):
        data = self.read_gbtx_register(register, gbtx_index)
        if data != expected_data:
            self.logger.warning(f"Register {register} was {data:02x} != expected {expected_data:02x}")
            return False
        return True

    def gbtx_config(self, registers, gbtx_index=0, check=True):
        """Write GBTx configuration data to GBTx"""
        assert gbtx_index in range(3)

        for register, r in enumerate(registers):
            try:
                if check:
                    self.write_gbtx_register_and_check(register=register, value=r, gbtx_index=gbtx_index)
                else:
                    self.write_gbtx_register(register=register, value=r, gbtx_index=gbtx_index)
            except ScaI2cBadStatusError as e:
                self.logger.error("GBTx configuration failed at add: {0} \tvalue: 0x{1:04X} \tgbtx: {2}".format(register, r, gbtx_index))
                break

    def check_gbtx_config(self, registers, gbtx_index=0):
        """Check GBTx xml configuration to GBTx"""
        assert gbtx_index in range(3)
        num_errors = 0
        for register, r in enumerate(registers):
            try:
                if not self.check_gbtx_register(register=register, expected_data=r, gbtx_index=gbtx_index):
                    num_errors += 1
            except Exception as e:
                self.logger.error(f"Reading of register {register} failed with {type(e).__name__} - could not check")
                print(e)
                num_errors += 1
        if num_errors > 0:
            return False
        return True
