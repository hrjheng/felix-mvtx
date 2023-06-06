"""Power unit wishbone module

NOTE: use latest documentation

Twiki: https://twiki.cern.ch/twiki/bin/view/ALICE/Documentation

Documentation at: https://twiki.cern.ch/twiki/pub/ALICE/Documentation/2018_09_04_ITS_power_system_V15_32-channel_operation_manual.pdf
and
https://twiki.cern.ch/twiki/pub/ALICE/Documentation/2018_09_04_ITS_power_system_V15_32-channel_operation_manual.docx
"""

from collections import OrderedDict
from enum import IntEnum, unique

import time

from wishbone_module import WishboneModule
from pu_controller import PuController, TempInterlockEnable, PowerUnitRTDSensor, Adc
from pu_monitor import PuMonitor

# Voltage limits at the connector including drop correction
MAX_AVDD = 2.30
MAX_DVDD = 2.40

# Voltage limits before a reset can be carried out (loss of clock and/or configuration)
MAX_DVDD_RESET = 1.82
MAX_AVDD_RESET = 1.82

@unique
class WbI2cPuAddress(IntEnum):
    InternalRegister           = 0x0
    TempThreshConfigAddress    = 0x1
    ThresCurrAddress_0         = 0x2
    ThresCurrAddress_1         = 0x3
    ThresCurrAddress_2         = 0x4
    ThresCurrAddress_3         = 0x5
    PotPowerAddress_0          = 0x6
    PotPowerAddress_1          = 0x7
    PotPowerAddress_2          = 0x8
    PotPowerAddress_3          = 0x9
    PotBiasAddress             = 0xA
    ADCAddressSetup_0          = 0xB
    ADCAddressSetup_1          = 0xC
    ADCAddressSetup_2          = 0xD
    ADCAddressSetup_3          = 0xE
    ADCBiasAddressSetup        = 0xF
    ADCAddress_0               = 0x10
    ADCAddress_1               = 0x11
    ADCAddress_2               = 0x12
    ADCAddress_3               = 0x13
    ADCBiasAddress             = 0x14
    Reserved_0                 = 0x15
    IOExpanderBiasAddress      = 0x16
    TempThreshRdAddress        = 0x17
    ADCAddress_0_Read          = 0x18
    ADCAddress_1_Read          = 0x19
    ADCAddress_2_Read          = 0x1a
    ADCAddress_3_Read          = 0x1b
    ADCBiasAddress_Read        = 0x1c
    Reserved_1                 = 0x1d
    IOExpanderBiasAddress_Read = 0x1e
    TempThreshRdAddress_Read   = 0x1f
    I2CDataEmptyAddress        = 0x20
    I2CDataAddress             = 0x21


@unique
class WbI2cPuAuxAddress(IntEnum):
    Reserved                      = 0x0
    IOExpanderPowerAddress_0      = 0x1
    IOExpanderPowerAddress_1      = 0x2
    IOExpanderPowerAddress_0_Read = 0x3
    IOExpanderPowerAddress_1_Read = 0x4
    I2CDataEmptyAddress           = 0x5
    I2CDataAddress                = 0x6


@unique
class VoltageChannelType(IntEnum):
    """Implements the channels of the PU alternated fashion"""
    ANALOG = 0
    DIGITAL = 1


@unique
class RtdFilterFrequency(IntEnum):
    """Implements the Byte3 of the I2C transaction for the RTD between 50 and 60 Hz filtering"""
    # see power unit manual Chapter 9.1, Table 17 (not in v1.0 production, but confirmed by AC)
    F60Hz = 0xc2
    F50Hz = 0xc3


@unique
class PowerUnitVersion(IntEnum):
    PRODUCTION     = 0 # square, dual-pcb, production
    PRE_PRODUCTION = 1 # square, dual-pcb, pre-production
    PROTOTYPE      = 2 # rectangular, single PCB, prototype


@unique
class BiasAdc(IntEnum):
    """enum for the Bias ADCs numbering"""
    I_BB = 0
    V_BB = 2


@unique
class Layer(IntEnum):
    """enum for layer"""
    INNER    = 0
    MIDDLE   = 1
    OUTER    = 2
    NO_PT100 = 3


class PowerUnitAux(WishboneModule):
    """Class for performing I2C transactions with the Power Unit AUX bus on RU"""

    def __init__(self, board_obj, moduleid):
        super(PowerUnitAux, self).__init__(moduleid=moduleid, name='PowerUnitAux', board_obj=board_obj)

    def do_read_transaction(self, addr, transaction_id=None, commitTransaction=True):
        """Redefining read to send a wishbone write to addr to start the I2C read transaction,
        then wait for FIFO_EMPTY bit to go low,
        and then read I2CDataAddress"""
        if transaction_id is None:
            transaction_id = int(time.time()*1e6) & 0x7FFF
        assert transaction_id in range(0x7FFF+1)

        MAX_NR_RETRIES = 1000
        assert addr in [WbI2cPuAuxAddress.IOExpanderPowerAddress_0_Read, WbI2cPuAuxAddress.IOExpanderPowerAddress_1_Read]
        self.write(addr=addr, data=transaction_id, commitTransaction=True)
        self.board.wait(1000, commitTransaction=False)
        fifo_empty, read_transaction_id = self.get_fifo_status()
        nr_retries = 0
        while (fifo_empty and (nr_retries < MAX_NR_RETRIES)):
            nr_retries += 1
            self.board.wait(1000, commitTransaction=False)
            fifo_empty, read_transaction_id = self.get_fifo_status()
        if nr_retries == MAX_NR_RETRIES:
            msg = "Max number of retries exceeded in do_read_transaction"
            raise RuntimeError(msg)
        else:
            if transaction_id != read_transaction_id:
                self.logger.warning(f"transaction_id mismatch 0x{transaction_id:04x}!=0x{read_transaction_id:04x}")
                self.board.wait(800000, commitTransaction=False)
                if type(self.comm).__name__ in ['CruSwtCommunication', 'FlxSwtCommunication']:
                    # It only runs on the CRU!
                    self.comm.log_swt_status()
                count = 0
                FIFO_DEPTH = 256
                while transaction_id != read_transaction_id and count < FIFO_DEPTH:
                    count += 1
                    self.read(WbI2cPuAuxAddress.I2CDataAddress)
                    fifo_empty, read_transaction_id = self.get_fifo_status()
                if transaction_id != read_transaction_id:
                    raise RuntimeError(f"repeated transaction_id mismatch for 0x{transaction_id:04x}, failed to find missing transaction in the FIFO!")
                else:
                    self.logger.info(f"Recovered transaction_id mismatch for transaction 0x{transaction_id:04x} after reading {count} previous transactions")
            self.logger.debug(f"Succeded after {nr_retries}")
            return self.read(addr=WbI2cPuAuxAddress.I2CDataAddress, commitTransaction=commitTransaction)

    def get_fifo_status(self):
        """Returns the fifo status"""
        status = self.read(WbI2cPuAuxAddress.I2CDataEmptyAddress)
        empty = (status >> 15) & 1
        transaction_id = status & 0x7FFF
        return empty, transaction_id

    def reset_fifo(self):
        count = 0
        while not self.get_fifo_status()[0]:
            count += 1
            self.read(WbI2cPuAuxAddress.I2CDataAddress)
        self.logger.info(f"FIFO reset after {count} reads")


class PowerUnit(WishboneModule):
    """Class for performing I2C transactions with the Power Unit on XCKU"""

    ADC_VREF = 2.56       # ADC128D818 datasheet
    ADC_BITS = 12         # ADC128D818 datasheet
    ADC_BITS_TEMP = 15    # MAX31865 datasheet
    TEMP_REF_RES = 400.   # Reference resistor used in temp measurement (R1400, R1399, R899)
    PT100_ZERO_RES = 100. # Resistance value of PT100 at 0 deg
    PT100_ALPHA = 3.85e-3 # Alpha value used in temp calculation, standard according to DIN 43760 IEC751 DIN EN 60 751

    def __init__(self, board_obj,
                 index,
                 moduleid,
                 main_monitor_module,
                 auxiliary_module,
                 aux_monitor_module,
                 controller_module,
                 resistance_offset,
                 offset_avdd, offset_dvdd,
                 layer,
                 version=PowerUnitVersion.PRE_PRODUCTION,
                 filter_50Hz_ac_power_mains_frequency=True):
        super(PowerUnit, self).__init__(moduleid=moduleid, name='PowerUnit', board_obj=board_obj)
        assert index in [1,2]
        self.index = index

        self.layer = Layer(layer)
        # By default use only PT100 for temp interlock
        self.interlock = [TempInterlockEnable.INTERNAL_PT100]

        self.main_monitor = None
        self.aux = None
        self.aux_monitor = None
        self.controller = None
        self._add_submodules(main_monitor_module,
                             auxiliary_module,
                             aux_monitor_module,
                             controller_module)

        self.version = None
        self.set_version(version)

        self.filter_50Hz_ac_power_mains_frequency = None
        self.set_filter_50Hz_ac_power_mains_frequency(filter_50Hz_ac_power_mains_frequency)


        self.resistance_offset = None # Additional resistance added by the PU, cable, and stave (to the PT100 and back).
        self.set_resistance_offset(resistance_offset)
        self.offset_avdd = [None]*8
        self.offset_dvdd = [None]*8
        self.set_voltage_offset(offset_avdd, offset_dvdd)

        self.minimum_temperature_pt100_disconnected = 720

        # register mapping is different than power unit documentation.
        # refer to vhdl file
        self._get_memory_mapping()

    def _get_interlock_vector(self):
        return self.interlock

    def _set_interlock_vector(self, interlock = [TempInterlockEnable.INTERNAL_PT100]):
        self.interlock = interlock

    def _get_memory_mapping(self):
        """Addds the memory_mapping"""
        self.ThresCurrAddress = (WbI2cPuAddress.ThresCurrAddress_0,
                                 WbI2cPuAddress.ThresCurrAddress_1,
                                 WbI2cPuAddress.ThresCurrAddress_2,
                                 WbI2cPuAddress.ThresCurrAddress_3)
        self.PotPowerAddress = (WbI2cPuAddress.PotPowerAddress_0,
                                WbI2cPuAddress.PotPowerAddress_1,
                                WbI2cPuAddress.PotPowerAddress_2,
                                WbI2cPuAddress.PotPowerAddress_3)
        self.PotBiasAddress = (WbI2cPuAddress.PotBiasAddress)
        self.ADCAddressSetup = (WbI2cPuAddress.ADCAddressSetup_0,
                                WbI2cPuAddress.ADCAddressSetup_1,
                                WbI2cPuAddress.ADCAddressSetup_2,
                                WbI2cPuAddress.ADCAddressSetup_3)
        self.ADCBiasAddressSetup = (WbI2cPuAddress.ADCBiasAddressSetup)
        self.ADCAddress = (WbI2cPuAddress.ADCAddress_0,
                           WbI2cPuAddress.ADCAddress_1,
                           WbI2cPuAddress.ADCAddress_2,
                           WbI2cPuAddress.ADCAddress_3)
        self.ADCReadAddress = (WbI2cPuAddress.ADCAddress_0_Read,
                               WbI2cPuAddress.ADCAddress_1_Read,
                               WbI2cPuAddress.ADCAddress_2_Read,
                               WbI2cPuAddress.ADCAddress_3_Read)
        self.ADCBiasAddress = (WbI2cPuAddress.ADCBiasAddress)
        self.ADCBiasReadAddress = (WbI2cPuAddress.ADCBiasAddress_Read)
        self.IOExpanderBiasAddress = (WbI2cPuAddress.IOExpanderBiasAddress)
        self.IOExpanderBiasReadAddress = (WbI2cPuAddress.IOExpanderBiasAddress_Read)
        self.IOExpanderPowerAddress = (WbI2cPuAuxAddress.IOExpanderPowerAddress_0,
                                       WbI2cPuAuxAddress.IOExpanderPowerAddress_1)
        self.IOExpanderPowerReadAddress = (WbI2cPuAuxAddress.IOExpanderPowerAddress_0_Read,
                                           WbI2cPuAuxAddress.IOExpanderPowerAddress_1_Read)
        self.TempThreshConfigAddress = (WbI2cPuAddress.TempThreshConfigAddress)
        self.TempThreshRdAddress = (WbI2cPuAddress.TempThreshRdAddress)
        self.TempThreshRdReadAddress = (WbI2cPuAddress.TempThreshRdAddress_Read)

    def _add_submodules(self,
                        main_monitor_module,
                        auxiliary_module,
                        aux_monitor_module,
                        controller_module):
        """Adds modules used by powerunit"""
        # wishbone module for MAIN bus monitor
        assert isinstance(main_monitor_module, PuMonitor)
        self.main_monitor = main_monitor_module
        # wishbone module for AUX bus
        assert isinstance(auxiliary_module, PowerUnitAux)
        self.aux = auxiliary_module
        # wishbone module for AUX bus monitor
        assert isinstance(aux_monitor_module, PuMonitor)
        self.aux_monitor = aux_monitor_module
        # wishbone module for controller
        assert isinstance(controller_module, PuController)
        self.controller = controller_module

    def do_read_transaction(self, addr, transaction_id=None, commitTransaction=True):
        """Redefining read to send a wishbone write to addr to start the I2C read transaction,
        then wait for FIFO_EMPTY bit to go low,
        and then read I2CDataAddress"""
        if transaction_id is None:
            transaction_id = int(time.time() * 1e6) & 0x7FFF
        assert transaction_id in range(0x7FFF + 1)

        MAX_NR_RETRIES = 10000
        assert addr in range(WbI2cPuAddress.ADCAddress_0_Read, WbI2cPuAddress.TempThreshRdAddress_Read + 1)
        self.write(addr=addr, data=transaction_id, commitTransaction=True)
        self.board.wait(1000, commitTransaction=False)
        fifo_empty, read_transaction_id = self.get_fifo_status()
        nr_retries = 0
        while (fifo_empty and (nr_retries < MAX_NR_RETRIES)):
            nr_retries += 1
            self.board.wait(1000, commitTransaction=False)
            fifo_empty, read_transaction_id = self.get_fifo_status()
        if nr_retries == MAX_NR_RETRIES:
            msg = "Max number of retries exceeded in do_read_transaction"
            raise RuntimeError(msg)
        else:
            if transaction_id != read_transaction_id:
                self.logger.warning(f"transaction_id mismatch 0x{transaction_id:04x}!=0x{read_transaction_id:04x}")
                self.board.wait(800000, commitTransaction=False)
                if type(self.comm).__name__ in ['CruSwtCommunication', 'FlxSwtCommunication']:
                    # It only runs on the CRU!
                    self.comm.log_swt_status()
                count = 0
                FIFO_DEPTH = 256
                while transaction_id != read_transaction_id and count < FIFO_DEPTH:
                    count += 1
                    self.read(WbI2cPuAddress.I2CDataAddress)
                    fifo_empty, read_transaction_id = self.get_fifo_status()
                if transaction_id != read_transaction_id:
                    raise RuntimeError(f"repeated transaction_id mismatch for 0x{transaction_id:04x}, failed to find missing transaction in the FIFO!")
                else:
                    self.logger.info(f"Recovered transaction_id mismatch for transaction 0x{transaction_id:04x} after reading {count} previous transactions")
            self.logger.debug(f"Succeded after {nr_retries}")
            return self.read(addr=WbI2cPuAddress.I2CDataAddress, commitTransaction=commitTransaction)

    def get_fifo_status(self):
        """Returns the fifo status"""
        status = self.read(WbI2cPuAddress.I2CDataEmptyAddress)
        empty = (status >> 15) & 1
        transaction_id = status & 0x7FFF
        return empty, transaction_id

    def reset_fifo(self):
        count = 0
        while not self.get_fifo_status()[0]:
            self.read(WbI2cPuAddress.I2CDataAddress)
            count += 1
        self.logger.info(f"FIFO reset after {count} reads")

    def reset_all_fifos(self):
        self.reset_fifo()
        self.aux.reset_fifo()

    def initialize(self):
        """Check whether the temperature interlock is already enabled,
        if not initialize and restart the temperature interlock"""

        temp_interlock_enabled = self.controller.is_temperature_interlock_enabled(interlock=self.interlock)
        self._initialise(temp_interlock_enabled)
        if not temp_interlock_enabled: # re-activating the interlock can cause the CANbus interlock to fire
            _, mask = self.controller.get_temperature_interlock_enable_mask()
            self.controller.set_temperature_interlock_enable_mask(mask)

    def _initialise(self, temp_interlock_enabled=False):
        """real initialisation of the powerunit"""
        self.configure_bias_adc()
        self.configure_power_adc()
        if not temp_interlock_enabled:
            for rtd in PowerUnitRTDSensor:
                self.initialize_temperature_sensor(sensor=rtd)

    def set_version(self, version):
        """Sets the version of the power unit.
        The PU in production version has a different ADC conversion factor"""
        self.version = PowerUnitVersion(version)

    def set_filter_50Hz_ac_power_mains_frequency(self, value):
        """Sets the filter for power distribution.
        If value = True:  usage of power unit in 50 Hz AC,
        if value = False: usage of power unit in 60 Hz AC.
        """
        assert value in [True, False]
        self.filter_50Hz_ac_power_mains_frequency = value

    def check_i2c_comm(self, num_checks=100):
        """Reads temperature of sensor 0, and checks if the value is sane to determine if I2C comm works"""
        for _ in range(num_checks):
            pu_tmp = self.read_temperature(PowerUnitRTDSensor.PU)
            assert pu_tmp > 0 and pu_tmp < 80, f"PU {self.index} I2C Comm unstable, PU temperature read: {pu_tmp}."

    # Conversions

    def _vbias_to_code(self,vbias):
        code = int(vbias * (-25.0)) # Sec 9.4 manual v1.5 and Sec 6.4 v1.0 production
        if code > 0xff:
            self.logger.warning("code out of range, set to max (code:{0}/255)".format(code))
            code=0xff
        if code < 0:
            self.logger.warning("code out of range, set to 0 (code: {0})".format(code))
            code=0
        return code

    def _code_to_vbias(self, code):
        """V in V
        """
        # The *2 is due to an onboard 1/2 voltage divider
        return -2 * (PowerUnit.ADC_VREF / (2**PowerUnit.ADC_BITS - 1)) * code

    def _code_to_ibias(self, code):
        """I in mA
        """
        if self.version==PowerUnitVersion.PRODUCTION:
            # The bias voltage regulator (LT3091 U277) has a current monitoring pin that sinks 1/4000 of the output current through a 40k res giving 10mv/mA, this causes the factor 10
            i = 1000* (PowerUnit.ADC_VREF / (2**PowerUnit.ADC_BITS - 1)) / 10 * code   # Sec 6.7.3 v1.0
        else:
            i = 1000* (PowerUnit.ADC_VREF / (2**PowerUnit.ADC_BITS - 1)) * code   # Private email with ALBERTO COLLU (2019.01.30 h17:06 CET)

        if i < 0:
            i = 0
        return i

    def _ibias_to_code(self, ibias):
        """I in mA
        """
        if self.version==PowerUnitVersion.PRODUCTION:
            # The bias voltage regulator (LT3091 U277) has a current monitoring pin that sinks 1/4000 of the output current through a 40k res giving 10mv/mA, this causes the factor 10
            code = 10 * (ibias/1000) * (2**PowerUnit.ADC_BITS - 1) / (PowerUnit.ADC_VREF)
        else:
            code = (ibias/1000) * (2**PowerUnit.ADC_BITS - 1) / (PowerUnit.ADC_VREF)

        return code

    def _vout_to_code(self, vout, offset):
        code = int((vout / 0.00486) - 306) # Sec 9.3 manual v1.5 and Sec 6.2 v1.0 production
        code = code - offset
        if code < 0:
            self.logger.warning("code out of range, set to 0 (code:{0})".format(code))
            code = 0
        elif code > 0xff:
            self.logger.warning("code out of range, set to max (code:{0}/255)".format(code))
            code = 0xff
        return code

    def _code_to_vpower(self, adc_code):
        """
        Converts the ADC value of the VDD (Analog and Digital) to VDD in [V]
        """
        if self.version==PowerUnitVersion.PROTOTYPE:
            # From PB manual (https://twiki.cern.ch/twiki/pub/ALICE/Documentation/2018_10_12_ITS_power_system_V16_32-channel_operation_manual.pdf) P35
            return (PowerUnit.ADC_VREF / 2**PowerUnit.ADC_BITS) * adc_code
        else:
            # From PB manual (https://twiki.cern.ch/twiki/pub/ALICE/DocumentationAndSchematics/2018_11_05_ITS_production_power_board_V10_32-channel_operation_manual.pdf) P32
            # There is a 200+1k voltage divider on the ADC input
            return (200 + 1000) / 1000 * (PowerUnit.ADC_VREF / (2**PowerUnit.ADC_BITS - 1)) * adc_code

    def _vpower_to_code(self, vpower):
        """Converts a Voltage to a Power ADC code"""
        if self.version == PowerUnitVersion.PROTOTYPE:
            code = int(((2**PowerUnit.ADC_BITS - 1) / PowerUnit.ADC_VREF) * vpower)
        else:
            code = int(1000 / (200 + 1000) * ((2**PowerUnit.ADC_BITS - 1) / PowerUnit.ADC_VREF) * vpower)

        if code > 0xfff:
            self.logger.warning("code out of range, set to max (code:{0}/255)".format(code))
            code = 0xfff
        return code

    def _ith_to_code(self,ith):
        if self.version == PowerUnitVersion.PROTOTYPE:
            code = int(410 + (3685.0 / 3.0) * ith) # Sec 9.2 manual v1.5
        else:
            code = int(400 + (3695.0 / 3.0) * ith) # Sec 6.2 manual v1.0 production

        if code < 0:
            self.logger.warning("code out of range, set to 0 (code:{0})".format(code))
            code = 0
        if code > 0xFFF:
            self.logger.warning("code out of range, set to max (code: 0X{0:03X}/0xFFF)".format(code))
            code = 0xFFF
        return code

    def _code_to_i(self, code):
        """I in mA
        """
        # The diff amp that measures the current has a 250mV offfset added to avoid non-linearity at low currents. The diff amp gain is set to 3/4 V/A.
        i = 1000 * ((self.ADC_VREF / (2**self.ADC_BITS - 1)) * code - 0.25) * 4 / 3  # Sec 6.7.3 v1.0 production
        if i < 0:
            i = 0
        return i

    def _temperature_to_code(self, temperature):
        """Convert temperature to a 16-bit RTD code"""
        # See _code_to_temperature for derrivation
        code = (int(((temperature * self.PT100_ZERO_RES * self.PT100_ALPHA) + self.PT100_ZERO_RES) * (2**self.ADC_BITS_TEMP - 1) / self.TEMP_REF_RES)) << 1
        assert code | 0xffff == 0xffff
        return code

    def _temperature_EXT_to_code(self, temperature):
        """Convert temperature to a 16-bit RTD code for an external PT100"""
        # See _code_to_temperature_EXT for derrivation
        code = (int(((temperature * self.PT100_ZERO_RES * self.PT100_ALPHA) + self.PT100_ZERO_RES + self.resistance_offset) * (2**self.ADC_BITS_TEMP - 1) / self.TEMP_REF_RES)) << 1
        assert code | 0xffff == 0xffff
        return code

    def _code_to_temperature(self, code):
        """Translate the 15-bit RTD read resistance (code) to temperature in C"""
        assert code | 0x7FFF == 0x7FFF
        # ADC measures code = (PT100_val / TEMP_REF_RES) * 2**self.ADC_BITS_TEMP
        # Reistance value of PT100 given temp is PT100_val = PT100_ZERO_RES * (1 + PT100_ALPHA * TEMP)
        # Rearranging and solving for TEMP gives the old formula from the manual : Sec 6.8.1 v1.0 production powerboard manual
        # (code - (PT100_ZERO_RES / TEMP_REF_RES * 2**ADC_BITS_TEMP)) / (PT100_ZERO_RES * PT100_ALPHA * 2**ADC_BITS_TEMP / TEMP_REF_RES)
        # Which can be simplified to
        return (code * self.TEMP_REF_RES / (2**self.ADC_BITS_TEMP - 1) - self.PT100_ZERO_RES) / (self.PT100_ZERO_RES * self.PT100_ALPHA)

    def _code_to_temperature_EXT(self, code):
        """Translate the 15-bit RTD read resistance (code) to temperature in C"""
        assert code | 0x7FFF == 0x7FFF
        # For resistance offsets in the cable the PT100_val = PT100_ZERO_RES * (1 + PT100_ALPHA * TEMP) + resistance_offset
        # Re-solving gives
        return ((code * self.TEMP_REF_RES / (2**self.ADC_BITS_TEMP - 1)) - self.PT100_ZERO_RES - self.resistance_offset) / (self.PT100_ZERO_RES * self.PT100_ALPHA)

    # calibration

    def set_voltage_offset(self,
                           offset_avdd,
                           offset_dvdd):
        if offset_avdd is None:
            offset_avdd = [0x12]*8
        if offset_dvdd is None:
            offset_dvdd = [0x12]*8
        assert isinstance(offset_avdd, list)
        assert isinstance(offset_dvdd, list)
        assert len(offset_avdd)==8
        assert len(offset_dvdd)==8
        for off in offset_avdd: assert off in range(256)
        for off in offset_dvdd: assert off in range(256)
        self.offset_avdd = offset_avdd
        self.offset_dvdd = offset_dvdd

    def get_voltage_offset(self):
        return self.offset_avdd, self.offset_dvdd

    def set_resistance_offset(self, resistance_offset):
        """Sets the value for resistance_offset"""
        self.resistance_offset = resistance_offset

    def get_resistance_offset(self):
        return self.resistance_offset

    # Modules powering

    def setup_power_module(self,
                       dvdd=1.9, dvdd_current=1.5,
                       avdd=1.9, avdd_current=1.5,
                       bb=0.0,
                       module=0,
                       check_interlock=True):
        self.setup_power_modules(dvdd=dvdd, dvdd_current=dvdd_current,
                             avdd=avdd, avdd_current=avdd_current,
                             bb=bb,
                             module_list=[module],
                             check_interlock=check_interlock)

    def setup_power_modules(self,
                        dvdd=1.9, dvdd_current=1.5,
                        avdd=1.9, avdd_current=1.5,
                        bb=0,
                        module_list=[0,1],
                        check_interlock=True,
                        no_offset=False,
                        verbose=True):
        for module in module_list:
            assert module in range(8), f"{module} not in range(8), module_list = {module_list}"

        # built-in extra safety
        if dvdd > MAX_DVDD:
            self.logger.warning(f"DVDD of {dvdd} requested for modules {module_list}, limiting to {MAX_DVDD} V")
            dvdd = MAX_DVDD
        if avdd > MAX_AVDD:
            self.logger.warning(f"AVDD of {avdd} requested for modules {module_list}, limiting to {MAX_AVDD} V")
            avdd = MAX_AVDD

        assert 0 <= dvdd <= MAX_DVDD
        assert 0 <= avdd <= MAX_AVDD
        assert 0 <= dvdd_current <= 3.0
        assert 0 <= avdd_current <= 3.0
        assert -4.5 <= bb <= 0, bb

        for module in module_list:
            assert module in range(8), f"{module} not in range(8), module_list = {module_list}"
            if verbose:
                self.logger.info("Setup power on module {0}".format(module))

        if check_interlock:
            assert self.controller.is_temperature_interlock_enabled(interlock=self.interlock)
            assert not self.controller.did_interlock_fire(), f"Interlock is active and fired! Please verify that it is fine, and retry!"

        if module_list != []:
            dvdd_code = [0,0,0,0,0,0,0,0]
            avdd_code = [0,0,0,0,0,0,0,0]
            bb_code = self._vbias_to_code(vbias=bb)
            dvdd_current_code = self._ith_to_code(ith=dvdd_current)
            avdd_current_code = self._ith_to_code(ith=avdd_current)

            for module in module_list:
                self.logger.debug(f"module = {module}")
                self.logger.debug(f"dvdd in setup power ibs: {dvdd}")
                if no_offset:
                    offset_dvdd = 0x0
                    offset_avdd = 0x0
                else:
                    offset_dvdd = self.offset_dvdd[module]
                    offset_avdd = self.offset_avdd[module]
                dvdd_code[module] = (self._vout_to_code(vout=dvdd, offset=offset_dvdd))
                avdd_code[module] = (self._vout_to_code(vout=avdd, offset=offset_avdd))
                self.logger.debug(f"dvdd_code: {dvdd_code}")
                self.configure_analog_power_voltage(module=module, voltage_code=avdd_code[module])
                self.configure_digital_power_voltage(module=module, voltage_code=dvdd_code[module])
            if bb :
                self.configure_bias_voltage(voltage_code=bb_code)
            else:
                # JS always set the bias voltage to something different than 0.0
                # (private conversation with F. Reidt)
                self.configure_bias_voltage(voltage_code=self._vbias_to_code(-3.0))
            self.raise_current_thresholds_to_max()
            for module in module_list:
                self.configure_analog_current_threshold(module=module, current_code=avdd_current_code)
                self.configure_digital_current_threshold(module=module, current_code=dvdd_current_code)

    def configure_current_limits_modules(self,
                                         dvdd_current=1.5,
                                         avdd_current=1.5,
                                         module_list=[0,1]):
        for module in module_list:
            assert module in range(8), f"{module} not in range(8), module_list = {module_list}"

        assert 0 <= dvdd_current <= 3.0
        assert 0 <= avdd_current <= 3.0

        if module_list != []:
            dvdd_current_code = self._ith_to_code(ith=dvdd_current)
            avdd_current_code = self._ith_to_code(ith=avdd_current)

            for module in module_list:
                self.configure_analog_current_threshold(module=module, current_code=avdd_current_code)
                self.configure_digital_current_threshold(module=module, current_code=dvdd_current_code)

    def log_enable_status(self):
        power_enable_status = self.get_power_enable_status()
        bias_enable_status = self.get_bias_enable_status()
        self.logger.info("Power enable status: %04X, Bias enable status: %02X",
                         power_enable_status,
                         bias_enable_status)
        return power_enable_status, bias_enable_status

    def check_module_power(self, module_list=[0,1], use_i2c=False):
        for module in module_list:
            values = self.get_values_modules(module_list=module_list, use_i2c=use_i2c)
            for vdd in ["avdd", "dvdd"]:
                v = self._code_to_vpower(values[f"module_{module}_{vdd}_voltage"])
                i = self._code_to_i(values[f"module_{module}_{vdd}_current"])
                if not v > 0:
                    raise Exception(f"module_{module}_{vdd}_voltage is not above 0, was {v}")
                if not i > 0:
                    raise Exception(f"module_{module}_{vdd}_current is not above 0, was {i}")

    def power_on_module(self, module, backbias_en=0, check_interlock=True):
        self.power_on_modules(module_list=[module], backbias_en=backbias_en, check_interlock=check_interlock)

    def power_on_modules(self, module_list=[0,1], backbias_en=0,
                     check_interlock=True):
        for module in module_list:
            assert module in range(8), f"{module} not in range(8), module_list = {module_list}"
            self.logger.info("Setup power on module {0}".format(module))
        if check_interlock:
            assert self.controller.is_temperature_interlock_enabled(interlock=self.interlock)
            assert not self.controller.did_interlock_fire(), f"Interlock is active and fired! Please verify that it is fine, and retry!"

        if module_list != []:
            try:
                self.logger.info("All off")
                #self.controller.disable_power_interlock()
                self.log_enable_status()
                mask_b = 0
                if backbias_en :
                    self.logger.info("Bias powering ON")
                    for module in module_list:
                        mask_b = mask_b | (0x1 << module)
                    self.enable_bias_with_mask(mask=mask_b)
                    self.logger.info("BB on")
                    power_enable_status, bias_enable_status = self.log_enable_status()
                    assert power_enable_status == 0, f"0x{power_enable_status:04X} != 0"
                    assert bias_enable_status == mask_b, f"0x{bias_enable_status:02X} != 0x{mask_b:02X}"

                mask_ad = 0
                mask_pw = 0  # interlock
                self.logger.info("Analog + Digital powering on")
                for module in module_list:
                    self.logger.info("Powering module {0}".format(module))
                    mask_ad = mask_ad | (0x1 << (module * 2))
                    self.enable_power_with_mask(mask=mask_ad) # analog
                    power_enable_status, bias_enable_status = self.log_enable_status()

                    assert power_enable_status == mask_ad, f"0x{power_enable_status:04X} != 0x{mask_ad:04X}"
                    assert bias_enable_status == mask_b, f"0x{bias_enable_status:02X} != 0x{mask_b:02X}"
                    self.board.wait(0x400000,commitTransaction=False)
                    mask_ad = mask_ad | (0x3 << (module * 2))
                    mask_pw = mask_pw | (0x1 << module)
                    self.enable_power_with_mask(mask=mask_ad) # digital + analog
                    power_enable_status, bias_enable_status = self.log_enable_status()
                    assert power_enable_status == mask_ad, f"0x{power_enable_status:04X} != 0x{mask_ad:04X}"
                    assert bias_enable_status == mask_b, f"0x{bias_enable_status:02X} != 0x{mask_b:02X}"

                power_enable_status, bias_enable_status = self.log_enable_status()
                assert power_enable_status == mask_ad, f"0x{power_enable_status:04X} != 0x{mask_ad:04X}"
                assert bias_enable_status == mask_b, f"0x{bias_enable_status:02X} != 0x{mask_b:02X}"
                time.sleep(0.5)
                self.check_module_power(module_list=module_list)
                self.logger.info("All modules powered on successfully. Checking interlock...")
                time.sleep(0.1)
                self.controller.enable_power_bias_interlock(power_enable_mask=mask_pw,
                                                            bias_enable_mask=mask_b)
                self.logger.info("Power/Bias Interlock enabled.")
                if check_interlock:
                    assert not self.controller.did_interlock_fire()
                power_enable_status, bias_enable_status = self.log_enable_status()
                assert power_enable_status == mask_ad, f"0x{power_enable_status:04X} != 0x{mask_ad:04X}"
                assert bias_enable_status == mask_b, f"0x{bias_enable_status:02X} != 0x{mask_b:02X}"
                time.sleep(0.5)
                self.check_module_power(module_list=module_list)
                self.logger.info("################   Power on succeeded!   ################")
            except Exception as e:
                self.logger.error("Power on failed, powering all off!")
                self.power_off_all()
                time.sleep(0.2)
                self.log_values_modules(module_list=module_list)
                self.logger.info("Raising")
                raise e

    def power_off_all(self, disable_power_interlock=False):
        if disable_power_interlock:
            self.controller.disable_power_interlock(commitTransaction=False)
        self.disable_power_all(commitTransaction=False)
        self.disable_bias_all(commitTransaction=True)
        self._set_power_voltage_all(voltage_code=0)
        self.configure_bias_voltage(voltage_code=0)
        self.lower_current_thresholds_to_min()

    def get_values_module(self, module, use_i2c=False):
        return self.get_values_modules(module_list=[module], use_i2c=use_i2c)

    def get_values_modules(self, module_list=[0,1,2,3,4,5,6,7], use_i2c=False, suppress_warnings=False):
        """Returns the values of the different components of the powerunit
        from the main bus of the controller"""
        vdd_ret = {}
        if not self.controller.is_temperature_interlock_enabled(interlock=TempInterlockEnable.INTERNAL_PT100) and not suppress_warnings:
            self.logger.warning("Temperature interlock not active!")
        if self.controller.is_temperature_interlock_enabled(interlock=TempInterlockEnable.INTERNAL_PT100) and not use_i2c:
            # under this condition all the values are mirrored
            power_enable_status = self.controller.get_power_enable_status()
            bias_enable_status = self.controller.get_bias_enable_status()
            for module in module_list:
                vdd_ret[module] = self.controller.get_power_adc_values(module)
            bb_voltage = self.controller.read_bias_adc_channel(channel=Adc.V_BB)
            bb_current = self.controller.read_bias_adc_channel(channel=Adc.I_BB)
        else:
            self.logger.debug(f"Using I2C to retrieve values!")
            power_enable_status = self.get_power_enable_status()
            bias_enable_status = self.get_bias_enable_status()
            for module in module_list:
                vdd_ret[module] = self.get_power_adc_values(module)
            bb_voltage = self.read_bias_adc_channel(channel=BiasAdc.V_BB)
            bb_current = self.read_bias_adc_channel(channel=BiasAdc.I_BB)

        values = OrderedDict([
            ("power_enable_status", power_enable_status),
            ("bias_enable_status", bias_enable_status),
            ("bb_voltage",         bb_voltage),
            ("bb_current",         bb_current)
        ])
        for module in module_list:
            for key, dict_value in vdd_ret[module].items():
                values["module_{0}_{1}".format(module, key)] = dict_value
        return values

    def log_values_module(self, module, use_i2c=False):
        self.log_values_modules(module_list=[module], use_i2c=use_i2c)

    def log_values_modules(self, module_list=[0,1,2,3,4,5,6,7], zero_volt_read_check=False, use_i2c=False):
        if not self.controller.is_temperature_interlock_enabled(interlock=[TempInterlockEnable.INTERNAL_PT100]):
            self.logger.warning("Temperature Interlock is not active on internal PT100s")
        values = self.get_values_modules(module_list=module_list, use_i2c=use_i2c)
        self.logger.info("Power enable status: 0x{0:04X}".format(values["power_enable_status"]))
        self.logger.info("Bias enable status: 0x{0:02X}".format(values["bias_enable_status"]))
        self.logger.info("Backbias: {0:.3f} V, {1:.1f} mA".format(self._code_to_vbias(values["bb_voltage"]),
                                                                  self._code_to_ibias(values["bb_current"])))
        for module in module_list:
            msg = f"Module {module}, "
            for vdd in ["avdd", "dvdd"]:
                v = self._code_to_vpower(values[f"module_{module}_{vdd}_voltage"])
                i = self._code_to_i(values[f"module_{module}_{vdd}_current"])
                msg += f"{vdd.upper()}: ({v:5.3f} V, {i:5.1f} mA) "
            self.logger.info(msg)
        if self.controller.is_temperature_interlock_enabled(interlock=[TempInterlockEnable.INTERNAL_PT100]) and not use_i2c:
            self.controller.log_temperatures()
        else:
            self.logger.debug(f"Using I2C to retrieve temperatures!")
            self.log_temperatures()
        self.controller.did_interlock_fire()
        if zero_volt_read_check:
            ret = True
            for module in module_list:
                for vdd in ["avdd", "dvdd"]:
                    if self._code_to_vpower(values["module_{0}_{1}_voltage".format(module, vdd)]) == 0:
                        ret = False
            return ret

    # Current Thresholds

    def configure_analog_current_threshold(self, module, current_code):
        """Configures the maximum current for the analog channel"""
        assert module in range(8), "Range out of range"
        assert current_code in range(0xFFF+1), "Analog current code out of range"
        self._set_current_threshold(channel=VoltageChannelType.ANALOG +2*module, value=current_code)

    def configure_digital_current_threshold(self, module, current_code):
        """Configures the maximum current for the digital channel"""
        assert module in range(8), "Range out of range"
        assert current_code in range(0xFFF+1), "Digital current code out of range"
        self._set_current_threshold(channel=VoltageChannelType.DIGITAL +2*module, value=current_code)

    def raise_current_thresholds_to_max(self, commitTransaction=True):
        """Set current thresholds of all channels to 0xffff"""
        byte1 = 0x3f
        byte2 = 0xff
        byte3 = 0xff

        self.write(WbI2cPuAddress.InternalRegister, byte1, commitTransaction=False)

        data = (byte2 << 8) | byte3
        for i in range(4) :
            self.write(self.ThresCurrAddress[i], data, commitTransaction=False)
        if commitTransaction:
            self.flush()

    def lower_current_thresholds_to_min(self, commitTransaction=True):
        """Set current thresholds of all channels to 0x0000"""

        byte1 = 0x3f
        byte2 = 0x00
        byte3 = 0x00

        self.write(WbI2cPuAddress.InternalRegister, byte1, commitTransaction=False)

        data = (byte2 << 8) | byte3
        for i in range(4) :
            self.write(self.ThresCurrAddress[i], data, commitTransaction=False)
        if commitTransaction:
            self.flush()

    def _set_current_threshold(self, channel, value, commitTransaction=True):
        """Set threshold of channel 'channel' to 'value'

        16 channels
        0 + 2*module: analog
        1 + 2*module: digital"""
        assert channel | 0xF == 0xF
        assert value | 0xFFF == 0xFFF

        channel_msb = channel >> 2
        channel_lsb = channel & 0x3

        byte1 = (0x3 << 4) | channel_lsb
        byte2 = (value >> 4) & 0xff
        byte3 = (value & 0xf) << 4

        self.write(WbI2cPuAddress.InternalRegister, byte1, commitTransaction=False)

        data = (byte2 << 8) | byte3
        self.write(self.ThresCurrAddress[channel_msb], data, commitTransaction=False)
        if commitTransaction:
            self.flush()

    def _set_current_threshold_with_mask(self, mask, value, commitTransaction=True):
        """Set threshold of each channel of bitposition in 'mask' to 'value'"""
        assert value | 0xFFF == 0xFFF
        assert mask | 0xFFFF == 0xFFFF
        for i in range(16):
            if ((mask >> i) & 1):
                self._set_current_threshold(i, value, commitTransaction=False)
        if commitTransaction:
            self.flush()

    def _set_current_threshold_all(self, value, commitTransaction=True):
        """Set threshold of all channels to 'value'"""
        assert value | 0xFFF == 0xFFF

        byte1 = 0x3f
        byte2 = (value >> 4) & 0xff
        byte3 = (value & 0xf) << 4

        self.write(WbI2cPuAddress.InternalRegister, byte1, commitTransaction=False)

        data = (byte2 << 8) | byte3
        for i in range(4) :
            self.write(self.ThresCurrAddress[i], data, commitTransaction=False)
        if commitTransaction:
            self.flush()

    # Power Enable/Disable

    def enable_power(self, channel, commitTransaction=True):
        """Enable power channel 'channel'"""
        assert channel in range(16)

        channel_msb = channel >> 3
        channel_lsb = channel & 0x7
        byte3 = 0x01 << channel_lsb
        self.aux.write(self.IOExpanderPowerAddress[channel_msb], byte3, commitTransaction=commitTransaction)

    def enable_power_with_mask(self, mask, commitTransaction=True):
        """Enable each power channel of bitposition in 'mask'"""
        assert mask | 0xFFFF == 0xFFFF

        byte3 = mask & 0xff
        self.aux.write(self.IOExpanderPowerAddress[0], byte3, commitTransaction=True)
        byte3 = (mask >> 8) & 0xff
        self.aux.write(self.IOExpanderPowerAddress[1], byte3, commitTransaction=True)

    def enable_power_all(self, commitTransaction=True):
        """Enable all power channels"""

        byte3 = 0xff
        self.aux.write(self.IOExpanderPowerAddress[0], byte3, commitTransaction=True)
        self.aux.write(self.IOExpanderPowerAddress[1], byte3, commitTransaction=True)
        #if commitTransaction:
        #    self.flush()

    def disable_power_all(self, commitTransaction=True):
        """Disable each power channel"""

        byte3 = 0x00
        self.aux.write(self.IOExpanderPowerAddress[0], byte3, commitTransaction=commitTransaction)
        self.aux.write(self.IOExpanderPowerAddress[1], byte3, commitTransaction=commitTransaction)

    def get_power_enable_status(self, commitTransaction=True):
        """Read enable status of all power channels as a mask"""
        results = []
        results.append(self.aux.do_read_transaction(self.IOExpanderPowerReadAddress[0], commitTransaction=True))
        results.append(self.aux.do_read_transaction(self.IOExpanderPowerReadAddress[1], commitTransaction=True))
        return self._format_get_power_enable_status(results)

    def _format_get_power_enable_status(self, results):
        assert len(results) == 2
        ret = ((results[1] & 0xFF) << 8) | (results[0] & 0xFF)
        return ret

    # Bias Enable/Disable

    def enable_bias_with_mask(self, mask, commitTransaction=True):
        """Enable each bias for channels in bit position of mask"""
        assert mask | 0xFF == 0xFF

        byte3 = 0xff ^ mask
        self.write(self.IOExpanderBiasAddress, byte3, commitTransaction=True)

    def enable_bias_all(self, commitTransaction=True):
        """Enable all bias channels"""

        byte3 = 0x00
        self.write(self.IOExpanderBiasAddress, byte3, commitTransaction=True)

    def disable_bias_all(self, commitTransaction=True):
        """Disable each bias channel"""

        byte3 = 0xff
        self.write(self.IOExpanderBiasAddress, byte3, commitTransaction=commitTransaction)

    def get_bias_enable_status(self, commitTransaction=True):
        """Read enable status of all bias channels as a mask"""
        results = self.do_read_transaction(self.IOExpanderBiasReadAddress, commitTransaction=True)
        return self._format_get_bias_enable_status(results)

    def _format_get_bias_enable_status(self, results):
        ret = (results & 0xFF) ^ 0xFF
        return ret

    # Power DACs

    def configure_analog_power_voltage(self, module, voltage_code):
        """Configures the voltage for the analog channel"""
        assert module in range(8), "Range out of range"
        assert voltage_code in range(0xFF+1), "Analog voltage code out of range"
        self._set_power_voltage(channel=VoltageChannelType.ANALOG +2*module, voltagecode=voltage_code)

    def configure_digital_power_voltage(self, module, voltage_code):
        """Configures the voltage for the digital channel"""
        assert module in range(8), "Range out of range"
        assert voltage_code in range(0xFF+1), "Digital voltage code out of range"
        self._set_power_voltage(channel=VoltageChannelType.DIGITAL +2*module, voltagecode=voltage_code)

    def _set_power_voltage(self, channel, voltagecode, commitTransaction=True):
        """Set output voltage setting of power 'channel' to 'voltage'"""
        assert channel in range(16)
        assert voltagecode | 0xFF == 0xFF

        channel_msb = channel >> 2
        channel_lsb = channel & 0x3

        byte2 = channel_lsb
        byte3 = voltagecode
        data = (byte2 << 8) | byte3
        self.write(self.PotPowerAddress[channel_msb], data, commitTransaction=commitTransaction)

    def _set_power_voltage_all(self, voltage_code, commitTransaction=True):
        """Set output voltage setting of all power channels to 'voltage'"""
        for channel in range(16):
            self._set_power_voltage(channel, voltage_code, commitTransaction=commitTransaction)

    # Bias DAC

    def configure_bias_voltage(self, voltage_code, commitTransaction=True):
        """Set output voltage setting of bias channels to the given voltage code"""
        assert voltage_code | 0xFF == 0xFF
        byte2 = 0x11
        byte3 = voltage_code
        data = (byte2 << 8) | byte3
        self.write(self.PotBiasAddress, data, commitTransaction=commitTransaction)

    # Power ADC

    def configure_power_adc(self, commitTransaction=True):
        """Configure control registers of all Power ADCs"""

        for SlaveAddress in self.ADCAddressSetup:
            #byte2 = 0x00 # Table 33 manual v1.5
            #byte3 = 0x00
            #data = (byte2 << 8) | byte3
            data = 0
            self.write(SlaveAddress, data, commitTransaction=True)
            byte2 = 0x07 # Table 33 manual v1.5
            byte3 = 0x01
            data = (byte2 << 8) | byte3
            self.write(SlaveAddress, data, commitTransaction=True)
            byte2 = 0x0B # Table 33 manual v1.5
            byte3 = 0x02
            data = (byte2 << 8) | byte3
            self.write(SlaveAddress, data, commitTransaction=True)
            byte2 = 0x00 # Table 33 manual v1.5
            byte3 = 0x01
            data = (byte2 << 8) | byte3
            self.write(SlaveAddress, data, commitTransaction=True)

    def read_power_adc(self):
        """Trigger ADC conversion and readout of all Power ADC channels"""

        ADCData = []
        for i in range(len(self.ADCAddress)):
            for channel in range(8):
                byte3 = 0x20 | channel
                self.write(self.ADCAddress[i], byte3, commitTransaction=True)
                ADCValue = self.do_read_transaction(self.ADCReadAddress[i])
                ADCData.append(ADCValue >> 4)  # 4LSB are not in use, see table 36 manual v1.5
        return ADCData

    def get_power_adc_values(self, module):
        assert module in range(8), "module {0} not in range(8)".format(module)
        avdd_voltage = self.read_power_adc_channel(0 + 4*module)
        avdd_current = self.read_power_adc_channel(1 + 4*module)
        dvdd_voltage = self.read_power_adc_channel(2 + 4*module)
        dvdd_current = self.read_power_adc_channel(3 + 4*module)
        ret = OrderedDict([
            ("avdd_voltage", avdd_voltage),
            ("avdd_current", avdd_current),
            ("dvdd_voltage", dvdd_voltage),
            ("dvdd_current", dvdd_current)
        ])
        return ret

    def read_power_adc_channel(self, channel):
        """Trigger ADC conversion and readout a Power ADC channel
        """
        assert channel in range(32), "channel not in range (0 <= channel < 32)"

        channel_msb = channel >> 3
        channel_lsb = channel & 0x7

        byte3 = 0x20 | channel_lsb
        SlaveAddress = self.ADCAddress[channel_msb]
        self.write(SlaveAddress, byte3, commitTransaction=True)
        SlaveAddress = self.ADCReadAddress[channel_msb]
        ADCValue = self.do_read_transaction(SlaveAddress)
        ADCData = ADCValue >> 4  # 4LSB are not in use, see table 36 manual v1.5
        return ADCData

    # Bias ADC

    def configure_bias_adc(self, commitTransaction=True):
        """Configure control registers of all Bias ADCs"""

        SlaveAddress = self.ADCBiasAddressSetup
        #byte2 = 0x00 # Table 33 manual v1.5
        #byte3 = 0x00
        #data = (byte2 << 8) | byte3
        data = 0
        self.write(SlaveAddress, data, commitTransaction=True)
        byte2 = 0x07  # Table 33 manual v1.5
        byte3 = 0x01
        data = (byte2 << 8) | byte3
        self.write(SlaveAddress, data, commitTransaction=True)
        byte2 = 0x0B  # Table 33 manual v1.5
        byte3 = 0x02
        data = (byte2 << 8) | byte3
        self.write(SlaveAddress, data, commitTransaction=True)
        byte2 = 0x00  # Table 33 manual v1.5
        byte3 = 0x01
        data = (byte2 << 8) | byte3
        self.write(SlaveAddress, data, commitTransaction=True)

    def read_bias_adc(self):
        """Trigger ADC conversion and readout of all Bias ADC channels"""

        ADCData = []
        SlaveAddress = self.ADCBiasAddress
        SlaveAddressRead = self.ADCBiasReadAddress
        for channel in BiasAdc:
            byte3 = 0x20 | channel
            self.write(SlaveAddress, byte3, commitTransaction=True)
            ADCValue = self.do_read_transaction(SlaveAddressRead)
            ADCData.append(ADCValue >> 4)  # 4LSB are not in use, see table 36 manual v1.5
        return ADCData

    def read_bias_adc_channel(self, channel):
        """Trigger ADC conversion and readout of a Bias ADC channel"""
        channel = BiasAdc(channel)

        SlaveAddress = self.ADCBiasAddress
        byte3 = 0x20 | channel
        self.write(SlaveAddress, byte3, commitTransaction=True)
        SlaveAddress = self.ADCBiasReadAddress
        ADCValue = self.do_read_transaction(SlaveAddress)
        ADCData = ADCValue >> 4  # 4LSB are not in use, see table 36 manual v1.5
        return ADCData

    # Temperature Sensor

    def initialize_temperature_sensor(self, sensor, commitTransaction=True):
        """Configure temperature sensor"""
        sensor = PowerUnitRTDSensor(sensor)

        # byte values according to chapter 9.1, Table 17
        sensor_id = 0x1 << (sensor)
        self.write(WbI2cPuAddress.InternalRegister, sensor_id, commitTransaction=True)

        byte2 = 0x80
        if self.filter_50Hz_ac_power_mains_frequency:
            byte3 = RtdFilterFrequency.F50Hz
        else:
            byte3 = RtdFilterFrequency.F60Hz
        data = (byte2 << 8) | byte3
        self.write(self.TempThreshConfigAddress, data, commitTransaction=True)

    def read_temperature(self, sensor, commitTransaction=True):
        """Read temperature sensor specified"""
        sensor = PowerUnitRTDSensor(sensor)
        sensor_id = 0x1 << (sensor)

        # See Chapter 6.8.1 Table 45 production board manual V1.0
        byte0 = sensor_id
        byte1 = 0x1
        byte2 = 0xff
        byte3 = 0xff

        data = (byte0 << 8) | byte1
        self.write(WbI2cPuAddress.InternalRegister, data, commitTransaction=True)

        data = (byte2 << 8) | byte3
        # first 4-byte write, followed by 2-byte read
        self.write(self.TempThreshRdAddress, data, commitTransaction=True)

        results = self.do_read_transaction(self.TempThreshRdReadAddress, commitTransaction=True)
        ResistanceValue = (results) >> 1
        if sensor in [PowerUnitRTDSensor.EXT1, PowerUnitRTDSensor.EXT2]:
            TemperatureValue = self._code_to_temperature_EXT(code=ResistanceValue)
        elif sensor == PowerUnitRTDSensor.PU:
            TemperatureValue = self._code_to_temperature(code=ResistanceValue)

        return TemperatureValue

    def read_all_temperatures(self):
        """Reads all the RTDs sequentially and returns the information"""
        temps = {}
        for rtd in PowerUnitRTDSensor:
            temps[rtd.name] = self.read_temperature(rtd)
        return temps

    def log_temperatures(self):
        """Reads all the RTDs sequentially and logs the information"""
        for rtd in PowerUnitRTDSensor:
            temp = self.read_temperature(rtd)
            self.logger.info("RTD {0}: {1:.2f} C".format(rtd.name, temp))

    def ConfigureRTD(self, SensorID, commitTransaction=True):
        DeprecationWarning("Deprecated function, please use initialize_temperature_sensor instead")
        self.initialize_temperature_sensor(sensor=SensorID-1,
                            commitTransaction=commitTransaction)

    def compensate_voltage_drop(self, module, r='nominal', dvdd_set=None, avdd_set=None):
        assert module in range(8)
        self.compensate_voltage_drops(r=r, dvdd_set=dvdd_set, avdd_set=avdd_set, module_list=[module])

    def compensate_voltage_drops(self, r='nominal', dvdd_set=None, avdd_set=None, module_list=[0,1,2,3,4,5,6], check_interlock=False):
        '''
        Compensate for cable voltage drop.
        If dvdd_set/avdd_set != None, use these values as the starting values, else use the measured values as starting values.
        r is either the string "nominal" or a dict containing cable resistances
        For r == "nominal" the hard-coded resistance values are used
        '''

        assert 1.62 < dvdd_set < 1.98  # in V, desired voltage at the middle of HIC
        assert 1.62 < avdd_set < 1.98  # in V, desired voltage at the middle of HIC

        if r=='nominal': # need to update with resistances of all ob module lines -> one big dictionary
            # from: https://twiki.cern.ch/twiki/bin/view/ALICE/Cable-resistance-and-voltage-drop
            r = {'cable_dvdd':0.102, 'cable_dgnd':0.101, 'cable_avdd':0.433, 'cable_agnd':0.433}
            rfpc = {}
            rfpc['f'] = {'fpc_dvdd':0.048, 'fpc_dgnd':0.026, 'fpc_avdd':0.048, 'fpc_agnd': 0.050}  # to the first chip
            rfpc['l'] = {'fpc_dvdd':0.128, 'fpc_dgnd':0.060, 'fpc_avdd':0.207, 'fpc_agnd': 0.182}  # to the last chip
            rfpc['m'] = {k:rfpc['f'][k]+0.5*(rfpc['l'][k]-rfpc['f'][k]) for k in rfpc['f'].keys()} # to the middle chip
            r.update(rfpc['m'])
        else:
            assert type(r) is dict


        for module in module_list:
            self.logger.info(f"Executing voltage compensation")
            meas = self.get_values_module(module)
            dv = self._code_to_vpower(meas[f"module_{module}_dvdd_voltage"])
            av = self._code_to_vpower(meas[f"module_{module}_avdd_voltage"])
            di = self._code_to_i(meas[f"module_{module}_dvdd_current"])
            ai = self._code_to_i(meas[f"module_{module}_avdd_current"])
            bb = self._code_to_vbias(meas['bb_voltage'])
            if dvdd_set is None:
                dvdd_set = dv
            if avdd_set is None:
                avdd_set = av

            d_dv = d_av = 0.

            d_dv = 0.001*di*(sum([v for k,v in r.items() if 'dvdd' in k or 'dgnd' in k]))
            self.logger.info(f"DVDD Delta V {d_dv:.2f}")

            d_av = 0.001*ai*(sum([v for k,v in r.items() if 'avdd' in k or 'agnd' in k]))
            self.logger.info(f"AVDD Delta V {d_av:.2f}")

            if d_dv>0 or d_av>0:
                self.logger.info('Compensating voltage drop: \t' +
                                 f"\t\tDVDD: {dv:.2f} -> {dvdd_set+d_dv:.2f}V, AVDD: {av:.2f} -> {avdd_set+d_av:.2f}V")
                self.setup_power_module(module=module, dvdd=dvdd_set+d_dv, avdd=avdd_set+d_av, bb=bb, check_interlock=check_interlock)
        time.sleep(0.5)
        self.check_module_power(module_list=module_list)
        self.logger.info("################   Voltage drop compensation succeeded!   ################")

    def compensate_voltage_drops_ob(self, l=4.5, dvdd=1.82, avdd=1.82, powered_module_list=None):
        '''ported from new-alpide-software/src/TPowerBoard.cpp '''

        self.logger.info("Compensating voltage drop")
        ana_resistance = l*0.04 # voltage drop is 0.04Ohm/m for analogue
        dig_resistance = l*0.02 # voltage drop is 0.02Ohm/m for digitial

        additional_line_voltage_drop_ana = 0.13 # line resistance not accounted for by powerbus or cables. i.e. fileterboard, powerunit channels. Measured with measure_cable_resistance in testbench on B301 test setup OL stave
        additional_line_voltage_drop_dig = 0.18

        powerbus_resistances = {"ol": {"ana": [0.179, 0.383, 0.458, 0.476, 0.490, 0.512, 0.507],
                                       "dig": [0.074, 0.098, 0.107, 0.113, 0.123, 0.118, 0.121],
                                       "gnd": [0.007, 0.008, 0.010, 0.012, 0.014, 0.016, 0.018]},
                                "ml": {"ana": [0.193, 0.291, 0.356, 0.388, 0.193, 0.291, 0.356, 0.388],
                                       "dig": [0.094, 0.087, 0.092, 0.1, 0.094, 0.087, 0.092, 0.1],
                                       "gnd": [0.007, 0.008, 0.010, 0.012, 0.007, 0.008, 0.010, 0.012]}} # powerbus resistances measured in Torino and taken from new-alpide-software
        if self.layer is Layer.OUTER:
            module_list = [0,1,2,3,4,5,6]
            powerbus_resistances = powerbus_resistances["ol"]
        elif self.layer is Layer.MIDDLE:
            module_list = [0,1,2,3,4,5,6,7]
            powerbus_resistances = powerbus_resistances["ml"]
        else:
            raise NotImplementedError
        if powered_module_list is None:
            powered_module_list = module_list

        idda = [None] * len(module_list)
        iddd = [None] * len(module_list)
        r_gnd = [None] * len(module_list)
        v_drop_part = [None] * len(module_list)
        v_drop_gnd = [0.] * len(module_list)
        v_drop_ana_gnd = [None] * len(module_list)
        v_ana_diff = [None] * len(module_list)
        v_dig_diff = [None] * len(module_list)

        for module in module_list:
            meas = self.get_values_module(module)
            idda[module] = self._code_to_i(meas[f"module_{module}_avdd_current"])
            iddd[module] = self._code_to_i(meas[f"module_{module}_dvdd_current"])
            r_gnd[module] = powerbus_resistances["gnd"][module]
            v_drop_gnd[module] = 0.001 * (idda[module] + iddd[module]) * r_gnd[module]

        i_total = 0.
        for module in reversed(module_list):
            i_total += iddd[module]
            i_total += idda[module]
            resistance  = r_gnd[module] - (r_gnd[module-1] if module > 0 else 0.)
            v_drop_part[module] = 0.001 * resistance * i_total

        for module in powered_module_list:
            v_drop_gnd[module] += sum(v_drop_part[previous_modules] for previous_modules in range(module))
            v_ana_diff[module] = (0.001 * idda[module] * (ana_resistance + powerbus_resistances["ana"][module])) + additional_line_voltage_drop_ana + v_drop_gnd[module]
            v_dig_diff[module] = (0.001 * iddd[module] * (dig_resistance + powerbus_resistances["dig"][module])) + additional_line_voltage_drop_dig + v_drop_gnd[module]
            self.logger.info(f"voltage drop for module {module}: analog: {v_ana_diff[module]:.3f}, digital: {v_dig_diff[module]:.3f}. idda: {idda[module]:.3f}, iddd: {iddd[module]:.3f}")
            # built-in extra safety
            avdd_con = avdd+v_ana_diff[module]
            dvdd_con = dvdd+v_dig_diff[module]
            if dvdd_con > MAX_DVDD:
                self.logger.warning(f"DVDD of {dvdd_con:.3f} requested for modules {module_list}, limiting to {MAX_DVDD} V")
                dvdd_con = MAX_DVDD
            if avdd_con > MAX_AVDD:
                self.logger.warning(f"AVDD of {avdd_con:.3f} requested for modules {module_list}, limiting to {MAX_AVDD} V")
                avdd_con = MAX_AVDD

            self.setup_power_module(module=module, dvdd=dvdd_con, avdd=avdd_con)
            time.sleep(1)
        self.check_module_power(module_list=powered_module_list)
        self.logger.info("################   Voltage drop compensation succeeded!   ################")

    def reset_voltage(self, avdd=1.82, dvdd=1.82):
        """Remove voltage compensation

           This function is used to return the chips to a safe powering stave before a loss of clock."""
        if dvdd > MAX_DVDD_RESET:
            self.logger.warning(f"DVDD of {dvdd} requested, limiting to {MAX_DVDD_RESET} V for resetting")
            dvdd = MAX_DVDD_RESET
        if avdd > MAX_AVDD_RESET:
            self.logger.warning(f"AVDD of {avdd} requested, limiting to {MAX_AVDD_RESET} V for resetting")
            avdd = MAX_AVDD_RESET

        assert 0 <= dvdd <= MAX_DVDD_RESET
        assert 0 <= avdd <= MAX_AVDD_RESET

        if self.layer is Layer.OUTER:
            module_list = [0,1,2,3,4,5,6]
        elif self.layer is Layer.MIDDLE:
            module_list = [0,1,2,3,4,5,6,7]
        elif self.layer is Layer.INNER:
            module_list = [0]
        else:
            raise NotImplementedError

        for module in module_list:
            self.setup_power_module(module=module, avdd=avdd, dvdd=dvdd)

    def is_any_channel_tripped(self, module_list):
        """Verifies that no channel in module_list is tripped for overcurrent.
        It assumes that the channels have been correctly switched on."""
        expected_mask = 0
        for module in module_list:
            expected_mask = 0x3<<(2*module) | expected_mask
        power_enable_status = self.get_power_enable_status()
        if power_enable_status != expected_mask:
            self.logger.error(f"AVDD/DVDD mask 0x{power_enable_status:X} not as expected 0x{expected_mask:X}. Powering off")
            self.power_off_all()
            return True
        else:
            return False

    def is_bias_tripped(self, module_list):
        """Checks if bias is tripped for overcurrent.
        Assumes bias is switched on.
        """
        expected_mask_b = 0
        for module in module_list:
            expected_mask_b = 0x1 << (module//3) | expected_mask_b
        bias_enable_status = self.get_bias_enable_status()
        if bias_enable_status != expected_mask_b:
            self.logger.error(f"bias mask 0x{bias_enable_status:X} not as expected 0x{expected_mask_b:X}. Powering off")
            self.power_off_all()
            return True
        else:
            return False

    def is_overtemperature(self, trip_temperature):
        """Verifies that the temperature is below a certain limit and powers off all the modules in case"""
        overtemp = False
        assert 10.0 <= trip_temperature <= 50.0
        for sensor_idx in [PowerUnitRTDSensor.EXT1, PowerUnitRTDSensor.EXT2]:
            temp = self.read_temperature(sensor_idx.value)
            if temp > self.minimum_temperature_pt100_disconnected:
                self.logger.debug(f"sensor {sensor_idx.name} powerunit PT100 disconnected!")
            elif temp > trip_temperature:
                self.logger.warning(f"Sensor {sensor_idx.name} temperature: {temp:.3f} C")
                overtemp = True
            else:
                self.logger.info(f"Sensor {sensor_idx.name} temperature: {temp:.3f} C")
        return overtemp

    def calculate_voltage_offset(self):
        raise NotImplementedError

    def read_counters(self):
        """Reads the monitor counters"""
        ret = {}
        ret['main'] = self.main_monitor.read_counters()
        ret['aux'] = self.aux_monitor.read_counters()
        return ret

    def reset_all_counters(self):
        """Resets the monitor counters"""
        self.main_monitor.reset_all_counters()
        self.aux_monitor.reset_all_counters()

    def adjust_output_voltages(self, module_list=[0,1,2,3,4,5,6,7],
                               avdd=1.8, dvdd=1.8,
                               max_iterations = 5,
                               max_voltage_diff = 0.005):
        """Adjusts the powerunit output voltage for a module iteratively.
        DVDD, AVDD, max_voltage_diff are given in V"""
        for module in module_list:
            assert module in range(8), f"{module} not in range(8), module_list = {module_list}"
        for module in module_list:
            self.adjust_output_voltage(module=module,
                                       dvdd=dvdd, avdd=avdd,
                                       max_iterations=max_iterations,
                                       max_voltage_diff=max_voltage_diff)

    def adjust_output_voltage(self, module=0,
                           dvdd=1.8, avdd=1.8,
                           max_iterations = 5,
                           max_voltage_diff = 0.005):
        """Adjusts the powerunit output voltage for a module iteratively.
        DVDD, AVDD, max_voltage_diff are given in V"""
        assert 0 <= dvdd <= MAX_DVDD
        assert 0 <= avdd <= MAX_AVDD
        assert module in range(8)

        avdd_adc = self._code_to_vpower(self.controller.read_power_adc_channel(0 + 4*module))
        dvdd_adc = self._code_to_vpower(self.controller.read_power_adc_channel(2 + 4*module))
        if avdd_adc < 0.1 or dvdd_adc < 0.1:
            self.logger.error('Voltages appear to be OFF, cannot use ADC to calibrate voltage output!')
            return False
        avdd_diff = avdd - avdd_adc
        dvdd_diff = dvdd - dvdd_adc
        avdd_set = avdd
        dvdd_set = dvdd
        self.logger.debug('Set power pre-check: requested AVDD is {:.3f}V, read is {:.4f}, diff is {:.1f}mV'.format(avdd, avdd_adc, 1000.*avdd_diff) )
        self.logger.debug('Set power pre-check: requested DVDD is {:.3f}V, read is {:.4f}, diff is {:.1f}mV'.format(dvdd, dvdd_adc, 1000.*dvdd_diff) )
        n_iter = 0
        while (abs(dvdd_diff) > max_voltage_diff or abs(avdd_diff) > max_voltage_diff) and n_iter < max_iterations:
            self.logger.debug('Set power module {} iteration {}/{}:'.format(module,n_iter+1,max_iterations))
            if abs(avdd_diff) > max_voltage_diff:
                self.logger.debug('    Requested AVDD is {:.3f}V, AVDD_diff is {:.1f}mV, setting AVDD to {:.4f}V'
                                 .format(avdd, 1000.*avdd_diff, avdd_set) )
                assert 0 <= avdd_set <= MAX_AVDD, 'Requested AVDD ({:.3f} V) exceeds MAX_AVDD ({:.3f} V)'.format(avdd_set, MAX_AVDD)
                self.configure_analog_power_voltage(module=module, voltage_code=self._vout_to_code(vout=avdd_set, offset=self.offset_avdd[module]))
                self.board.wait(16000000) # give the pu some time to settle
                avdd_adc = self._code_to_vpower(self.controller.read_power_adc_channel(0 + 4*module))
                assert avdd_adc > 1., 'AVDD < 1 V! Did the module trip?'
                avdd_diff = avdd - avdd_adc
                avdd_set = avdd + avdd_diff
                self.logger.debug('    ADC reports AVDD is {:.4f}V, diff is {:.1f}mV'.format(avdd_adc, 1000.*avdd_diff) )
                if avdd_set > MAX_AVDD:
                    avdd_set = MAX_AVDD
            if abs(dvdd_diff) > max_voltage_diff:
                self.logger.debug('    Requested DVDD is {:.3f}V, DVDD_diff is {:.1f}mV, setting DVDD to {:.4f}V'
                                 .format(dvdd, 1000.*dvdd_diff, dvdd_set) )
                assert 0 <= dvdd_set <= MAX_DVDD, 'Requested DVDD ({:.3f} V) exceeds MAX_DVDD ({:.3f} V)'.format(dvdd_set, MAX_DVDD)
                self.configure_digital_power_voltage(module=module, voltage_code=self._vout_to_code(vout=dvdd_set, offset=self.offset_dvdd[module]))
                self.board.wait(16000000) # give the pu some time to settle
                dvdd_adc = self._code_to_vpower(self.controller.read_power_adc_channel(2 + 4*module))
                assert dvdd_adc > 1., 'DVDD < 1 V! Did the module trip?'
                dvdd_diff = dvdd - dvdd_adc
                dvdd_set = dvdd + dvdd_diff
                self.logger.debug('    ADC reports DVDD is {:.4f}V, diff is {:.1f}mV, '.format(dvdd_adc, 1000.*dvdd_diff) )
                if dvdd_set > MAX_DVDD:
                    dvdd_set = MAX_DVDD
            n_iter += 1
        self.logger.debug('Set power post-check: ADC reads AVDD is {:.4f}V, diff is {:.1f}mV'.format(avdd_adc, 1000.*(avdd-avdd_adc)))
        self.logger.debug('Set power post-check: ADC reads DVDD is {:.4f}V, diff is {:.1f}mV'.format(dvdd_adc, 1000.*(dvdd-dvdd_adc)))
        return n_iter < max_iterations

    def get_monitored_values(self, module_list=[0,1,2,3,4,5,6,7]):
        """Return monitor values for enable status and voltages/currrents for specified power unit modules"""
        power_enable_status = self.controller.get_power_enable_status()
        bias_enable_status = self.controller.get_bias_enable_status()
        self.logger.info("Power enable status: 0x{0:04X}".format(power_enable_status))
        self.logger.info("Bias enable status: 0x{0:02X}".format(bias_enable_status))
        bb_voltage = self.controller.read_adc_channel(Adc.V_BB)
        bb_current = self.controller.read_adc_channel(Adc.I_BB)
        self.logger.info("Backbias: {0:.3f} V, {1:.1f} mA".format(self._code_to_vbias(bb_voltage),
                                                                  self._code_to_ibias(bb_current)))
        for module in module_list:
            avdd_voltage = self.controller.read_adc_channel(0 + 4 * module)
            avdd_current = self.controller.read_adc_channel(1 + 4 * module)
            dvdd_voltage = self.controller.read_adc_channel(2 + 4 * module)
            dvdd_current = self.controller.read_adc_channel(3 + 4 * module)
            self.logger.info("Module {0}, AVDD: {1:.3f} V, {2:.1f} mA ".format(module,
                                                                               self._code_to_vpower(avdd_voltage),
                                                                               self._code_to_i(avdd_current)))
            self.logger.info("Module {0}, DVDD: {1:.3f} V, {2:.1f} mA ".format(module,
                                                                               self._code_to_vpower(dvdd_voltage),
                                                                               self._code_to_i(dvdd_current)))

    def get_i2c_values(self, module_list=[0,1,2,3,4,5,6,7]):
        """Return values for enable status and voltages/currrents for specified power unit modules
        read directly from I2C"""
        power_enable_status = self.get_power_enable_status()
        bias_enable_status = self.get_bias_enable_status()
        self.logger.info("Power enable status: 0x{0:04X}".format(power_enable_status))
        self.logger.info("Bias enable status: 0x{0:02X}".format(bias_enable_status))
        bb_voltage = self.read_bias_adc_channel(2)
        bb_current = self.read_bias_adc_channel(0)
        self.logger.info("Backbias: {0:.3f} V, {1:.1f} mA".format(self._code_to_vbias(bb_voltage),
                                                                  self._code_to_ibias(bb_current)))
        for module in module_list:
            avdd_voltage = self.read_power_adc_channel(0 + 4 * module)
            avdd_current = self.read_power_adc_channel(1 + 4 * module)
            dvdd_voltage = self.read_power_adc_channel(2 + 4 * module)
            dvdd_current = self.read_power_adc_channel(3 + 4 * module)
            self.logger.info("Module {0}, AVDD: {1:.3f} V, {2:.1f} mA ".format(module,
                                                                               self._code_to_vpower(avdd_voltage),
                                                                               self._code_to_i(avdd_current)))
            self.logger.info("Module {0}, DVDD: {1:.3f} V, {2:.1f} mA ".format(module,
                                                                               self._code_to_vpower(dvdd_voltage),
                                                                               self._code_to_i(dvdd_current)))

    def powerunit_offset(self, avdd, dvdd, module_list=[0,1,2,3,4,5,6,7]):
        offset_analog = []
        offset_digital = []
        offsets = {'avdd':[], 'dvdd':[]}
        self.set_voltage_offset([0]*8, [0]*8)
        for module in module_list:
            values = self.get_values_module(module)
            pb_adc_dvdd = self._code_to_vpower(values["module_{0}_{1}_voltage".format(module, "dvdd")])
            pb_adc_avdd = self._code_to_vpower(values["module_{0}_{1}_voltage".format(module, "avdd")])
            avg_offset_dvdd = self._vout_to_code(pb_adc_dvdd, offset=0) - self._vout_to_code(dvdd, offset=0)
            avg_offset_avdd = self._vout_to_code(pb_adc_avdd, offset=0) - self._vout_to_code(avdd, offset=0)
            offset_analog.append(hex(int(avg_offset_avdd)))
            offset_digital.append(hex(int(avg_offset_dvdd)))

        offsets['avdd'] = offset_analog
        offsets['dvdd'] = offset_digital
        print_offset_analog = ", ".join(offset_analog)
        print_offset_digital = ", ".join(offset_digital)
        self.logger.info(print_offset_analog)
        self.logger.info(print_offset_digital)

        return offsets
