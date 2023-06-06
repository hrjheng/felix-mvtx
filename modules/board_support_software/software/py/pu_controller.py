"""Class to implement the Power Unit Controller interface"""

from enum import IntEnum, unique
from collections import OrderedDict

from wishbone_module import WishboneModule


@unique
class WsPuControllerAddress(IntEnum):
    """memory mapping for powerunit controller module"""
    LIMIT_TEMP0           = 0x00
    LIMIT_TEMP1           = 0x01
    LIMIT_TEMP2           = 0x02
    TEMP_PT0              = 0x03
    TEMP_PT1              = 0x04
    TEMP_PT2              = 0x05
    FIFO_RST              = 0x06
    TRIPPED               = 0x07
    ENABLE_PWR            = 0x08
    ENABLE_BIAS           = 0x09
    ENABLE_MASK           = 0x0a
    TEMP_INTERLOCK_ENABLE = 0x0b
    PWR_INTERLOCK_ENABLE  = 0x0c
    LO_LIMIT_TEMP0        = 0x0d
    LO_LIMIT_TEMP1        = 0x0e
    LO_LIMIT_TEMP2        = 0x0f
    ADC_00                = 0x10
    ADC_01                = 0x11
    ADC_02                = 0x12
    ADC_03                = 0x13
    ADC_04                = 0x14
    ADC_05                = 0x15
    ADC_06                = 0x16
    ADC_07                = 0x17
    ADC_08                = 0x18
    ADC_09                = 0x19
    ADC_10                = 0x1a
    ADC_11                = 0x1b
    ADC_12                = 0x1c
    ADC_13                = 0x1d
    ADC_14                = 0x1e
    ADC_15                = 0x1f
    ADC_16                = 0x20
    ADC_17                = 0x21
    ADC_18                = 0x22
    ADC_19                = 0x23
    ADC_20                = 0x24
    ADC_21                = 0x25
    ADC_22                = 0x26
    ADC_23                = 0x27
    ADC_24                = 0x28
    ADC_25                = 0x29
    ADC_26                = 0x2a
    ADC_27                = 0x2b
    ADC_28                = 0x2c
    ADC_29                = 0x2d
    ADC_30                = 0x2e
    ADC_31                = 0x2f
    ADC_32                = 0x30
    ADC_33                = 0x31
    ADC_34                = 0x32
    TRIPPED_PWR           = 0x33
    TRIPPED_BIAS          = 0x34
    TRIPPED_LTCH          = 0x35
    MAX_ADC               = 0x36


@unique
class Tripped(IntEnum):
    """memory mapping for the TRIPPED register"""
    TURN_OFF_MODULES_0_3         = 0x0
    TURN_OFF_MODULES_4_7         = 0x1
    INTERNAL_TEMP_OUTSIDE_LIMITS = 0x2
    EXT_1_TEMP_OUTSIDE_LIMITS    = 0x3
    EXT_2_TEMP_OUTSIDE_LIMITS    = 0x4
    MASK_DIFFERS                 = 0x5
    CLOCK01_TRIP                 = 0x6
    CLOCK23_TRIP                 = 0x7


@unique
class TempInterlockEnable(IntEnum):
    """"Memory mappign of the TEMP_INTERLOCK_ENABLE register"""
    INTERNAL_PT100        = 0x0
    EXTERNAL1_PT100       = 0x1
    EXTERNAL2_PT100       = 0x2


@unique
class PowerUnitRTDSensor(IntEnum):
    """Available RTD Sensor number"""
    PU   = 0
    EXT1 = 1
    EXT2 = 2


@unique
class Adc(IntEnum):
    """ADC index"""
    MODULE_0_V_AVDD = 0
    MODULE_0_I_AVDD = 1
    MODULE_0_V_DVDD = 2
    MODULE_0_I_DVDD = 3
    MODULE_1_V_AVDD = 4
    MODULE_1_I_AVDD = 5
    MODULE_1_V_DVDD = 6
    MODULE_1_I_DVDD = 7
    MODULE_2_V_AVDD = 8
    MODULE_2_I_AVDD = 9
    MODULE_2_V_DVDD = 10
    MODULE_2_I_DVDD = 11
    MODULE_3_V_AVDD = 12
    MODULE_3_I_AVDD = 13
    MODULE_3_V_DVDD = 14
    MODULE_3_I_DVDD = 15
    MODULE_4_V_AVDD = 16
    MODULE_4_I_AVDD = 17
    MODULE_4_V_DVDD = 18
    MODULE_4_I_DVDD = 19
    MODULE_5_V_AVDD = 20
    MODULE_5_I_AVDD = 21
    MODULE_5_V_DVDD = 22
    MODULE_5_I_DVDD = 23
    MODULE_6_V_AVDD = 24
    MODULE_6_I_AVDD = 25
    MODULE_6_V_DVDD = 26
    MODULE_6_I_DVDD = 27
    MODULE_7_V_AVDD = 28
    MODULE_7_I_AVDD = 29
    MODULE_7_V_DVDD = 30
    MODULE_7_I_DVDD = 31
    I_BB            = 32
    V_BB            = 34


class PuController(WishboneModule):
    """Power Unit controller wishbone slave"""
    def __init__(self, moduleid, board_obj):
        super(PuController, self).__init__(moduleid=moduleid, name="PuController", board_obj=board_obj)
        self.power_unit = None
        self.power_unit_index = None

    def _init(self, power_unit_index):
        """Initialised the power unit controller"""
        assert power_unit_index in [1,2], f"{power_unit_index} is not a valid powerunit I2C connector number"
        self.power_unit_index = power_unit_index
        self._set_power_unit()

    def _set_power_unit(self):
        if self.power_unit_index == 1:
            self.power_unit = self.board.powerunit_1
        else:
            self.power_unit = self.board.powerunit_2

    def enable_temperature_interlock(self,
                                     internal_temperature_limit=None,
                                     ext1_temperature_limit=None,
                                     ext2_temperature_limit=None,
                                     internal_temperature_low_limit=None,
                                     ext1_temperature_low_limit=None,
                                     ext2_temperature_low_limit=None,
                                     suppress_warnings=False):
        """Set Temperature limit for all the sensors if not None and
        enables the corresponding interlocks. It is optional to set the low limit. """
        if not self.is_temperature_interlock_enabled():
            interlocks = []
            if internal_temperature_limit is not None:
                if TempInterlockEnable.INTERNAL_PT100 in self.power_unit._get_interlock_vector():
                    self._set_temperature_limit(PowerUnitRTDSensor.PU, internal_temperature_limit)
                    interlocks.append(TempInterlockEnable.INTERNAL_PT100)
                    if internal_temperature_low_limit is not None:
                        self._set_low_temperature_limit(PowerUnitRTDSensor.PU, internal_temperature_low_limit)
                else:
                    self.logger.warning("Setting a limit for the internal temperature, which is not monitored")
            if ext1_temperature_limit is not None:
                if TempInterlockEnable.EXTERNAL1_PT100 in self.power_unit._get_interlock_vector():
                    self._set_temperature_limit(PowerUnitRTDSensor.EXT1, ext1_temperature_limit)
                    interlocks.append(TempInterlockEnable.EXTERNAL1_PT100)
                    if ext1_temperature_low_limit is not None:
                        self._set_low_temperature_limit(PowerUnitRTDSensor.EXT1, ext1_temperature_low_limit)
                else:
                    self.logger.warning("Setting a limit for the external temperature 1, which is not monitored")
            if ext2_temperature_limit is not None:
                if TempInterlockEnable.EXTERNAL2_PT100 in self.power_unit._get_interlock_vector():
                    self._set_temperature_limit(PowerUnitRTDSensor.EXT2, ext2_temperature_limit)
                    interlocks.append(TempInterlockEnable.EXTERNAL2_PT100)
                    if ext2_temperature_low_limit is not None:
                        self._set_low_temperature_limit(PowerUnitRTDSensor.EXT2, ext2_temperature_low_limit)
                else:
                    self.logger.warning("Setting a limit for the external temperature 2, which is not monitored")
            assert interlocks.sort() == self.power_unit._get_interlock_vector().sort(),f"invalid interlock configuration: {interlocks}"
            self.enable_temperature_monitor(interlocks)
        elif not suppress_warnings:
            self.logger.warning("Temperature interlock was already enabled!")

    def enable_power_bias_interlock(self,
                                    power_enable_mask,
                                    bias_enable_mask):
        """Set the mask for bias and back bias and
        enables the corresponding interlocks"""
        self.logger.debug(f"Enabling power bias interlock with power_mask 0x{power_enable_mask:02x}, bias_mask 0x{bias_enable_mask:02x}")
        self.set_expected_power_bias_enable_mask(power_mask=power_enable_mask,
                                                 bias_mask=bias_enable_mask)
        self._enable_power_interlock()

    def _set_temperature_limit(self, sensor_index, temperature):
        """Set upper temperature limit register in PU controller for sensor_index to temperature converted to code"""
        sensor_index = PowerUnitRTDSensor(sensor_index)
        if sensor_index in [PowerUnitRTDSensor.EXT1, PowerUnitRTDSensor.EXT2]:
            code = self.power_unit._temperature_EXT_to_code(temperature)
        elif sensor_index == PowerUnitRTDSensor.PU:
            code = self.power_unit._temperature_to_code(temperature)
        self.write(WsPuControllerAddress.LIMIT_TEMP0 + sensor_index, code)

    def _set_low_temperature_limit(self, sensor_index, temperature):
        """Set lower temperature limit register in PU controller for sensor_index to temperature converted to code"""
        sensor_index = PowerUnitRTDSensor(sensor_index)
        if sensor_index in [PowerUnitRTDSensor.EXT1, PowerUnitRTDSensor.EXT2]:
            code = self.power_unit._temperature_EXT_to_code(temperature)
        elif sensor_index == PowerUnitRTDSensor.PU:
            code = self.power_unit._temperature_to_code(temperature)
        self.write(WsPuControllerAddress.LO_LIMIT_TEMP0 + sensor_index, code)

    def _reset_temperature_limit(self, sensor_index):
        """Set Temperature limit register in PU controller for sensor_index to temperature converted to code"""
        sensor_index = PowerUnitRTDSensor(sensor_index)
        self.write(WsPuControllerAddress.LIMIT_TEMP0 + sensor_index, 0)

    def get_temperature_limit(self, sensor_index):
        """Read temperature limit register for sensor_index"""
        sensor_index = PowerUnitRTDSensor(sensor_index)
        code = self.read(WsPuControllerAddress.LIMIT_TEMP0 + sensor_index)
        ResistanceValue = code >> 1
        if sensor_index in [PowerUnitRTDSensor.EXT1, PowerUnitRTDSensor.EXT2]:
            TemperatureValue = self.power_unit._code_to_temperature_EXT(code=ResistanceValue)
        elif sensor_index == PowerUnitRTDSensor.PU:
            TemperatureValue = self.power_unit._code_to_temperature(code=ResistanceValue)

        return TemperatureValue

    def get_low_temperature_limit(self, sensor_index):
        """Read temperature limit register for sensor_index"""
        sensor_index = PowerUnitRTDSensor(sensor_index)
        code = self.read(WsPuControllerAddress.LO_LIMIT_TEMP0 + sensor_index)
        ResistanceValue = code >> 1
        if sensor_index in [PowerUnitRTDSensor.EXT1, PowerUnitRTDSensor.EXT2]:
            TemperatureValue = self.power_unit._code_to_temperature_EXT(code=ResistanceValue)
        elif sensor_index == PowerUnitRTDSensor.PU:
            TemperatureValue = self.power_unit._code_to_temperature(code=ResistanceValue)

        return TemperatureValue

    def get_temperature(self, sensor_index):
        """Read latest temperature read loop result for sensor_index"""
        sensor_index = PowerUnitRTDSensor(sensor_index)
        code = self.read(WsPuControllerAddress.TEMP_PT0 + sensor_index)
        ResistanceValue = code >> 1
        if sensor_index in [PowerUnitRTDSensor.EXT1, PowerUnitRTDSensor.EXT2]:
            TemperatureValue = self.power_unit._code_to_temperature_EXT(code=ResistanceValue)
        elif sensor_index == PowerUnitRTDSensor.PU:
            TemperatureValue = self.power_unit._code_to_temperature(code=ResistanceValue)
        return TemperatureValue

    def read_all_temperatures(self):
        """Reads all the RTDs sequentially and returns the information"""
        temps = {}
        for rtd in PowerUnitRTDSensor:
            temps[rtd.name] = self.get_temperature(rtd)
        return temps

    def log_temperatures(self):
        log = "Temperature"
        for sensor in PowerUnitRTDSensor:
            t = self.get_temperature(sensor_index=sensor)
            log += f" {sensor.name}: {t:.2f} C"
        self.logger.info(log)

    def reset_fifo(self, fifo_index):
        """Reset Controller Wishbone FIFO indicated in fifo_index"""
        assert fifo_index in range(4) # TODO: add enum here
        data = 0x1 << fifo_index
        self.write(WsPuControllerAddress.FIFO_RST, data)

    def reset_all_fifos(self):
        """Reset all Controller Wishbone FIFOs"""
        self.write(WsPuControllerAddress.FIFO_RST, 0xf)

    def get_tripped(self):
        """Read tripped booleans"""
        tripped_val = self.read(WsPuControllerAddress.TRIPPED)
        ret = {}
        for bit in Tripped:
            ret[bit.name] = (tripped_val>>bit.value & 1 == 1)
        return (ret, tripped_val)

    def get_tripped_latch(self):
        """Read latched tripped booleans"""
        tripped_val = self.read(WsPuControllerAddress.TRIPPED_LTCH)
        ret = {}
        for bit in Tripped:
            ret[bit.name] = (tripped_val>>bit.value & 1 == 1)
        return (ret, tripped_val)

    def reset_tripped_latch(self):
        """Reset the tripped_latch register to 0"""
        # a write to any bit will reset this register
        self.write(WsPuControllerAddress.TRIPPED_LTCH, 1)

    def did_interlock_fire(self):
        """did any interlock fire"""
        ret, _ = self.get_tripped_latch()
        fired = False
        for bit in Tripped:
            if ret[bit.name]:
                if bit in self.power_unit._get_interlock_vector():
                    self.logger.warning(f"{bit.name} bit is 1! Interlock fired!")
                    fired = True
                else:
                    self.logger.error(f"{bit.name} bit is 1! Interlock wrongly configured!")
        return fired

    def get_power_enable_status(self):
        """read the power enable interlock register"""
        return self.read(WsPuControllerAddress.ENABLE_PWR)

    def get_bias_enable_status(self):
        """read the bias enable monitoring register"""
        value = self.read(WsPuControllerAddress.ENABLE_BIAS)
        return self.power_unit._format_get_bias_enable_status(value)

    def set_expected_power_bias_enable_mask(self, power_mask, bias_mask, commitTransaction=True):
        """Write the expected power and bias enable bits
        The power_mask bits are for the modules that should have AVDD and DVDD turned on
        (1 bit per module), 1 = AVDD and DVDD turned on, 0 = AVDD and DVDD turned off)
        The bias_mask bits are for the modules that should have BIAS turned on
        (1 bit per module, 1 = BIAS turned on, 0 BIAS turned off)
        """
        assert power_mask | 0xff == 0xff, "mask should be 8 bits"
        assert bias_mask | 0xff == 0xff, "mask should be 8 bits"
        bias_mask = self.power_unit._format_get_bias_enable_status(bias_mask)
        mask = power_mask | bias_mask << 8
        self.write(WsPuControllerAddress.ENABLE_MASK, mask, commitTransaction=commitTransaction)

    def get_expected_power_bias_enable_mask(self):
        """Read the expected power and bias enable mask"""
        mask = self.read(WsPuControllerAddress.ENABLE_MASK)
        power_mask = mask & 0xFF
        bias_mask = (mask>>8) & 0xFF
        bias_mask = self.power_unit._format_get_bias_enable_status(bias_mask)
        return power_mask, bias_mask

    def log_expected_power_bias_enable_mask(self):
        power_mask, bias_mask = self.get_expected_power_bias_enable_mask()
        self.logger.info(f"Power mask 0x{power_mask:02x}, bias mask {bias_mask:02x}")

    def _set_expected_enable_mask(self, mask):
        """Write the expected power and bias enable bits without formatting
        The lowest 8 bits are for the modules that should have AVDD and DVDD turned on
        (1 bit per module), 1 = AVDD and DVDD turned on, 0 = AVDD and DVDD turned off)
        The upper 8 bits are for the modules that should have BIAS turned on
        (1 bit per module, 1 = BIAS turned off, 0 BIAS turned on)
        """
        assert (mask | 0xffff) == 0xffff, "mask should be 16 bit"
        self.write(WsPuControllerAddress.ENABLE_MASK, mask)

    def _get_expected_enable_mask(self):
        """Read the expected power and bias enable mask without formatting"""
        return self.read(WsPuControllerAddress.ENABLE_MASK)

    def set_temperature_interlock_enable_mask(self, mask):
        """Set the interlock enable bits:"""
        assert mask | ((1<<len(TempInterlockEnable)) - 1) == (1<<len(TempInterlockEnable)) - 1
        self.write(WsPuControllerAddress.TEMP_INTERLOCK_ENABLE, mask)

    def enable_temperature_monitor(self, interlock):
        """Enables the selected interlocks.
        Input can be a value or a list of values"""
        if isinstance(interlock, int):
            interlock = [interlock]
        mask = 0
        for en in interlock:
            en = TempInterlockEnable(en)
            mask |= 1<<en.value
        self.set_temperature_interlock_enable_mask(mask=mask)

    def disable_all_temperature_interlock(self):
        self.set_temperature_interlock_enable_mask(mask=0)
        for sensor in PowerUnitRTDSensor:
            self._reset_temperature_limit(sensor)

    def get_temperature_interlock_enable_mask(self):
        """Gets the monitoring enable
        """
        value = self.read(WsPuControllerAddress.TEMP_INTERLOCK_ENABLE)
        ret = {}
        for bit in TempInterlockEnable:
            ret[bit.name] = ((value >> bit.value)&1 == 0x1)
        return (ret, value)

    def is_temperature_interlock_enabled(self, interlock=None):
        """Input can be a value or a list of values"""
        if interlock is None:
            interlock = self.power_unit._get_interlock_vector()
        elif isinstance(interlock, int):
            interlock = [interlock]
        status, _ = self.get_temperature_interlock_enable_mask()
        result = True
        for en in interlock:
            en = TempInterlockEnable(en)
            if not status[en.name]:
                result = False
        return result

    def _enable_power_interlock(self):
        """Enable Power enable bits Interlock"""
        self.write(WsPuControllerAddress.PWR_INTERLOCK_ENABLE, 1)

    def disable_power_interlock(self, commitTransaction=True):
        self.write(WsPuControllerAddress.PWR_INTERLOCK_ENABLE, 0, commitTransaction=commitTransaction)
        self.set_expected_power_bias_enable_mask(power_mask=0,bias_mask=0, commitTransaction=commitTransaction)

    def get_power_interlock_enable(self):
        return self.read(WsPuControllerAddress.PWR_INTERLOCK_ENABLE)

    def is_power_interlock_enabled(self):
        return self.get_power_interlock_enable() == 1

    def disable_all_interlocks(self):
        """Set all monitoring enable bits to 0"""
        self.disable_all_temperature_interlock()
        self.disable_power_interlock()

    def read_adc_channel(self, channel):
        """Read the ADC value monitored by the PowerUnit Contoller"""
        channel = Adc(channel)
        ADCValue = self.read(WsPuControllerAddress.ADC_00 + channel)
        ADCData = ADCValue >> 4  # 4LSB are not in use, see table 36 manual v1.5
        return ADCData

    def read_power_adc_channel(self, channel):
        """Reads the power adc channels"""
        channel = Adc(channel)
        assert channel not in [Adc.V_BB, Adc.I_BB]
        return self.read_adc_channel(channel)

    def read_bias_adc_channel(self, channel):
        channel = Adc(channel)
        assert channel in [Adc.V_BB, Adc.I_BB]
        return self.read_adc_channel(channel)

    def get_power_adc_values(self, module):
        assert module in range(8), "module {0} not in range(8)".format(module)
        avdd_voltage = self.read_power_adc_channel(0 + 4 * module)
        avdd_current = self.read_power_adc_channel(1 + 4 * module)
        dvdd_voltage = self.read_power_adc_channel(2 + 4 * module)
        dvdd_current = self.read_power_adc_channel(3 + 4 * module)
        ret = OrderedDict([
            ("avdd_voltage", avdd_voltage),
            ("avdd_current", avdd_current),
            ("dvdd_voltage", dvdd_voltage),
            ("dvdd_current", dvdd_current)
        ])
        return ret

    def get_tripped_power_enables(self):
        """Reads the power enable bits before a power interlock trip"""
        return self.read(WsPuControllerAddress.TRIPPED_PWR)

    def get_tripped_bias_enables(self):
        """Reads the bias enable bits before a power interlock trip"""
        tripped_bias = self.read(WsPuControllerAddress.TRIPPED_BIAS)
        return self.power_unit._format_get_bias_enable_status(tripped_bias)

    def set_clock_interlock_threshold(self, voltage):
        """Sets the maximum ADC value for the clock interlock"""
        code = self.power_unit._vpower_to_code(voltage)
        code = code << 4  # lower 4 bits need to be added to ADC code
        self.write(WsPuControllerAddress.MAX_ADC, code)

    def get_clock_interlock_threshold(self):
        """Read the maximum voltage set for clock interlock"""
        return (self.power_unit._code_to_vpower(self.read(WsPuControllerAddress.MAX_ADC) >> 4))

    def dump_config(self):
        """Dump the modules state and configuration as a string"""
        config_str = f"--- {self.name} module ---\n"
        self.board.comm.disable_rderr_exception()
        for address in WsPuControllerAddress:
            name = address.name
            try:
                value = self.read(address.value)
                config_str += "    - {0} : {1:#06X}\n".format(name, value)
            except:
                config_str += "    - {0} : FAILED\n".format(name)
        self.board.comm.enable_rderr_exception()
        return config_str
