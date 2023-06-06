"""File implementing the configuration of the daq_test.py"""

from collections import OrderedDict

import configparser
import errno
import json
import os
import sys
import warnings

script_path = os.path.dirname(os.path.realpath(__file__))
modules_path = os.path.join(
    script_path, '../')
sys.path.append(modules_path)
modules_path = os.path.join(
    script_path, '../../modules/board_support_software/software/py/')
sys.path.append(modules_path)
from module_includes import *


import daq_test
import power_unit
import ru_transition_board
import testbench
import trigger_handler
from pALPIDE import ModeControlIbSerialLinkSpeed


class DaqTestConfig(object):
    """Configuration for the daq_test"""
    def __init__(self, only_warn=False):
        self.only_warn = only_warn
        self._config = None
        self._section = None
        self._config_file = None

        # TESTBENCH_SECTION
        self.yml                                              = None
        # GITHASH section
        self.GITHASH_CRU                                      = None
        self.GITHASH_RDO                                      = None
        self.GITHASH_PA3                                      = None
        self.CHECK_HASH                                       = None
        # CRU section
        self.CRU_SN                                           = None
        self.CTRL_AND_DATA_LINK_LIST                          = None
        self.ONLY_DATA_LINK_LIST                              = None
        self.TRIGGER_LINK_LIST                                = None
        self.CRU_TYPE                                         = None
        # RU section
        self.RU_MAIN_REVISION                                 = None
        self.RU_MINOR_REVISION                                = None
        self.RU_TRANSITION_BOARD_VERSION                      = None
        self.USE_RDO_USB                                      = None
        # PB section
        self.POWER_BOARD_VERSION                              = None
        self.POWER_BOARD_FILTER_50HZ_AC_POWER_MAINS_FREQUENCY = None
        self.POWER_UNIT_1_OUTPUT_CHANNEL_LIST                 = None
        self.POWER_UNIT_2_OUTPUT_CHANNEL_LIST                 = None
        self.POWERUNIT_RESISTANCE_OFFSET_PT100                = None
        self.POWERUNIT_LIMIT_TEMPERATURE_SOFTWARE             = None
        self.POWERUNIT_LIMIT_TEMPERATURE_HARDWARE             = None
        self.COMPENSATE_VOLTAGE_DROP                          = None
        # TRIGGER section
        self.TRIGGER_PERIOD_BC                                = None
        self.NUM_TRIGGERS                                     = None
        self.TRIGGERING_MODE                                  = None
        self.USE_LTU                                          = None
        self.USE_GTM                                          = None
        self.USE_RUN_SERVER                                   = None
        self.TRIGGERED_STROBE_DURATION                        = None
        self.TRIGGER_SOURCE                                   = None
        self.TRIGGER_TF                                       = None
        self.TRIGGER_HBF_PER_TF                               = None
        self.TRIGGER_HBA_PER_TF                               = None
        # Stave section
        self.LAYER                                            = None
        self.LTU_HOSTNAME                                     = None
        # ALPIDE section
        self.SENSOR_POWERING_SCHEME                           = None
        self.SENSOR_AVDD                                      = None
        self.SENSOR_DVDD                                      = None
        self.SENSOR_VBB                                       = None
        self.SENSOR_AVDD_MAX_CURRENT                          = None
        self.SENSOR_DVDD_MAX_CURRENT                          = None
        self.SENSOR_PATTERN                                   = None
        self.SENSOR_DRIVER_DAC                                = None
        self.SENSOR_PRE_DAC                                   = None
        self.SENSOR_PLL_DAC                                   = None
        self.LINK_SPEED                                       = None
        self.SENSOR_CLOCK_GATING                              = None
        self.SENSOR_SKEW_START_OF_READOUT                     = None
        self.SENSOR_CLUSTERING                                = None
        self.BB_ENABLE                                        = None
        self.EXCLUDED_SLAVE_CHIPIDEXT_LIST                    = None
        self.EXCLUDED_MASTER_CHIPIDEXT_LIST                   = None
        self.EXCLUDED_CHIPIDEXT_LIST                          = None
        self.OB_LOWER_MODULES                                 = None
        self.OB_UPPER_MODULES                                 = None
        self.GPIO_PU1_MODULES                                 = None
        self.GPIO_PU2_MODULES                                 = None
        self.ONLY_MASTERS                                     = None
        self.ANALOGUE_PULSING                                 = None
        self.PULSE_TO_STROBE                                  = None
        self.SEND_PULSES                                      = None
        self.ENABLE_STROBE_GENERATION                         = None
        self.GRST                                             = None
        # READOUT section
        self.DRY                                              = None
        self.GTH_ACTIVE                                       = None
        self.GPIO_ACTIVE                                      = None
        self.READOUT_SOURCE                                   = None
        self.EXCLUDE_GTH_LIST                                 = None
        self.EXCLUDE_GPIO_LIST                                = None
        self.DISABLE_MANCHESTER                               = None
        self.GTH_CONNECTOR                                    = None
        self.GPIO_CONNECTORS                                  = None
        self.MAIN_CONNECTOR                                   = None
        self.READOUT_GPIO_LIST                                = None
        self.READOUT_GTH_LIST                                 = None
        # PA3 section
        self.PA3_READ_VALUES                                  = None
        self.PA3_SCRUBBING_ENABLE                             = None
        # READOUT PROCESS
        self.READOUT_PROC_ACTIVE                              = None
        self.READOUT_PROC_CFG                                 = None
        # FDAQ PROCESS
        self.FDAQ_ACTIVE_DMA                                  = None
        self.FDAQ_STARTUP_TIME                                = None
        self.FDAQ_DATAFILE                                    = None
        # TEST section
        self.TEST_DURATION                                    = None
        self.READ_SENSORS_DURING_DATATAKING                   = None
        self.EVENT_ANALYSYS_ONLINE                            = None
        self.SUBRACK                                          = None

    def scan_specific_parameter(self):
        """Pass for daq_test, super used for obtest_configurator"""
        pass

    def _parse_configuration_file(self, config_file):
        """Retrieves the configuration from the config or from the specified local configuration file"""
        self._config_file = config_file
        if config_file is not None:
            config_file = os.path.realpath(os.path.join(script_path, config_file))
        else:
            config_file = os.path.realpath(os.path.join(script_path, '../config/daq_test.cfg'))
        if not os.path.isfile(config_file):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), config_file)

        self._config = configparser.ConfigParser()
        self._config.read(config_file)
        return self._config

    def configure_run(self, config_file, logdir):
        """Defines the whole configuration from the config file"""
        self._parse_configuration_file(config_file)
        self._load_config()
        self._store_configuration(logdir)

    def _load_config(self):
        self._configure_yml()
        self._configure_githash()
        self._configure_ru()
        self._configure_alpide()
        self._configure_pb()
        self._configure_trigger()
        self._configure_stave()
        self._configure_readout()
        self._configure_pa3()
        self._configure_readout_proc()
        self._configure_fdaq_proc()
        self._configure_test()

    def _get_config_int(self, option):
        """Gets the section from the config and converts to int"""

        try:
            val = self._config.get(self._section, option)
            return int(val, 0)
        except configparser.NoSectionError:
            msg = f"Section {self._section} not present in config file {self._config_file}"
        except configparser.NoOptionError:
            msg = f"Option {option} not present in section {self._section} of config file {self._config_file}"
        except ValueError:
            msg = f"Error on converting option {option} in section {self._section} in {self._config_file} with data {self._config.get(self._section, option)} to int"
        if self.only_warn:
            warnings.warn(msg)
            return 0
        else:
            raise ValueError(msg)

    def _get_config_boolean(self, option, fallback=None):
        """Gets the section from the config and converts to boolean"""
        try:
            if fallback is None:
                return self._config.getboolean(section=self._section, option=option)
            return self._config.getboolean(section=self._section, option=option, fallback=fallback)
        except configparser.NoSectionError:
            msg = f"Section {self._section} not present in config file {self._config_file}"
        except configparser.NoOptionError:
            msg = f"Option {option} not present in section {self._section} of config file {self._config_file}"
        except ValueError:
            msg = f"Error on converting option {option} in section {self._section} in {self._config_file} with data {self._config.get(self._section, option)} to boolean"
        if self.only_warn:
            warnings.warn(msg)
            return False
        else:
            raise ValueError(msg)

    def _get_config_float(self, option):
        """Gets the section from the config and converts to float"""
        try:
            val = self._config.get(self._section, option)
            return float(val)
        except configparser.NoSectionError:
            msg = f"Section {self._section} not present in config file {self._config_file}"
        except configparser.NoOptionError:
            msg = f"Option {option} not present in section {self._section} of config file {self._config_file}"
        except ValueError:
            msg = f"Error on converting option {option} in section {self._section} in {self._config_file} with data {self._config.get(self._section, option)} to float"
        if self.only_warn:
            warnings.warn(msg)
            return 0.0
        else:
            raise ValueError(msg)

    def _get_config_str(self, option):
        """Gets the section from the config and converts to string"""
        try:
            return self._config.get(self._section, option)
        except configparser.NoSectionError:
            msg = f"Section {self._section} not present in config file {self._config_file}"
        except configparser.NoOptionError:
            msg = f"Option {option} not present in section {self._section} of config file {self._config_file}"
        if self.only_warn:
            warnings.warn(msg)
            return ''
        else:
            raise ValueError(msg)

    def _get_config_list(self, option, conv_type, allow_empty=False):
        """Gets the section from the config and converts to list of type conv_type"""
        try:
            input_list = self._config.get(self._section, option)
            if (not input_list.strip() or str(input_list).upper() == "NONE") and allow_empty:
                return []
            else:
                if conv_type == int:
                    return list(map(int, input_list.split(','), [0]*len(input_list.split(','))))
                elif conv_type == bool:
                    return [x in ["True",1,"yes"] for x in input_list.split(',')]
                else:
                    return list(map(conv_type, input_list.split(',')))
        except configparser.NoSectionError:
            msg = f"Section {self._section} not present in config file {self._config_file}"
        except configparser.NoOptionError:
            msg = f"Option {option} not present in section {self._section} of config file {self._config_file}"
        except ValueError:
            msg = f"Error on converting option {option} in section {self._section} in {self._config_file} with data {input_list} to {conv_type} list"
        if self.only_warn:
            warnings.warn(msg)
            return []
        else:
            raise ValueError(msg)

    def _get_config_enum(self, option, enum):
        """Gets the section from the config and converts to enum"""
        try:
            data = self._config.get(self._section, option)
            return enum[data]
        except configparser.NoSectionError:
            msg = f"Section {self._section} not present in config file {self._config_file}"
        except configparser.NoOptionError:
            msg = f"Option {option} not present in section {self._section} of config file {self._config_file}"
        except ValueError:
            msg = f"Invalid value for option {option} in section {self._section} in {self._config_file} with data {data}, not in {list(enum)}"
        if self.only_warn:
            warnings.warn(msg)
            return enum(0)
        else:
            raise ValueError(msg)

    def _configure_yml(self):
        """Configures some paramters from the testbench_yml_file"""
        self._section = 'TESTBENCH'
        self.yml = os.path.join(script_path, self._get_config_str('YML'))
        d = testbench.configure_testbench(self.yml,
                                          run_standalone=False,
                                          check_yml=self.only_warn)
        self.CRU_SN = d['CRU_SN']
        self.CTRL_AND_DATA_LINK_LIST = d['CTRL_AND_DATA_LINK_LIST']
        self.ONLY_DATA_LINK_LIST = d['ONLY_DATA_LINK_LIST']
        self.TRIGGER_LINK_LIST = d['TRIGGER_LINK_LIST']
        self.RU_MAIN_REVISION = d['RU_MAIN_REVISION']
        self.RU_MINOR_REVISION = d['RU_MINOR_REVISION']
        self.RU_TRANSITION_BOARD_VERSION = d['RU_TRANSITION_BOARD_VERSION']
        self.POWER_BOARD_VERSION = d['POWER_BOARD_VERSION']
        self.POWER_BOARD_FILTER_50HZ_AC_POWER_MAINS_FREQUENCY = d['POWER_BOARD_FILTER_50HZ_AC_POWER_MAINS_FREQUENCY']
        self.POWERUNIT_RESISTANCE_OFFSET_PT100 = d['POWERUNIT_RESISTANCE_OFFSET_PT100']
        self.LTU_HOSTNAME = d['LTU_HOSTNAME']
        self.LAYER = d['LAYER']
        self.SUBRACK = d['SUBRACK']
        self.CRU_TYPE = d['CRU_TYPE']
        if self.CRU_TYPE == testbench.CruType.NONE:
            msg = "USB access to RDO not currently supported by DAQ test"
            if self.only_warn:
                warnings.warn(msg)
            else:
                raise NotImplementedError(msg)
        self.USE_RDO_USB = d['USE_RDO_USB']
        if self.USE_RDO_USB:
            msg = "USB access to RDO not currently supported by DAQ test"
            if self.only_warn:
                warnings.warn(msg)
            else:
                raise NotImplementedError(msg)

    def _configure_githash(self):
        """Configures a specific section of the test"""
        self._section = 'GITHASH'
        self.GITHASH_CRU = self._get_config_int('CRU')
        self.GITHASH_RDO = self._get_config_int('RDO')
        self.GITHASH_PA3 = self._get_config_int('PA3')
        self.CHECK_HASH  = self._get_config_boolean('CHECK_HASH')

    def _configure_ru(self):
        """Configures a specific section of the test"""
        self._section = 'RU'

    def _configure_pb(self):
        """Configures a specific section of the test"""
        self._section = 'PB'
        self.POWERUNIT_LIMIT_TEMPERATURE_SOFTWARE             = self._get_config_float('LIMIT_TEMPERATURE_SOFTWARE')
        self.POWERUNIT_LIMIT_TEMPERATURE_HARDWARE             = self._get_config_float('LIMIT_TEMPERATURE_HARDWARE')
        self.COMPENSATE_VOLTAGE_DROP                          = self._get_config_boolean('COMPENSATE_VOLTAGE_DROP')

    def _configure_trigger(self):
        """Configures a specific section of the test"""
        self._section = 'TRIGGER'
        self.TRIGGERING_MODE           = self._get_config_enum('MODE', daq_test.RuTriggeringMode)
        self.TRIGGER_PERIOD_BC         = self._get_config_int('PERIOD_BC')
        self.NUM_TRIGGERS              = self._get_config_int('NUM_TRIGGERS')
        self.USE_LTU                   = self._get_config_boolean('USE_LTU')
        self.USE_GTM                   = self._get_config_boolean('USE_GTM', False)
        self.USE_RUN_SERVER            = self._get_config_boolean('USE_RUN_SERVER')
        self.TRIGGERED_STROBE_DURATION = self._get_config_int('TRIGGERED_STROBE_DURATION')
        self.TRIGGER_SOURCE            = self._get_config_enum('SOURCE', trigger_handler.TriggerSource)
        self.TRIGGER_TF                = self._get_config_int('TF')
        self.TRIGGER_HBF_PER_TF        = self._get_config_int('HBF_PER_TF')
        self.TRIGGER_HBA_PER_TF        = self._get_config_int('HBA_PER_TF')

        if self.USE_LTU and self.TRIGGER_SOURCE != trigger_handler.TriggerSource.GBTx2:
            warnings.warn("Trigger source must be GBTx2 when LTU is enabled.")
            self.TRIGGER_SOURCE = trigger_handler.TriggerSource.GBTx2

        if self.USE_RUN_SERVER and (not self.USE_LTU  or self.TRIGGER_SOURCE != trigger_handler.TriggerSource.GBTx2):
            warnings.warn("USE_LTU must be True when run server is enabled.")
            warnings.warn("Trigger source must be GBTx2 when run server is enabled.")
            self.USE_LTU = True
            self.TRIGGER_SOURCE = trigger_handler.TriggerSource.GBTx2

        if self.USE_LTU:
            self.TRIGGER_LINK_LIST = []
        if self.TRIGGERING_MODE in [daq_test.RuTriggeringMode.CONTINUOUS,
                                    daq_test.RuTriggeringMode.DUMMY_CONTINUOUS]:
            if not self.TRIGGER_PERIOD_BC in trigger_handler.ALLOWED_CONTINUOUS_MODE_PERIOD_BC:
                msg = f"{self.TRIGGER_PERIOD_BC} not in {trigger_handler.ALLOWED_CONTINUOUS_MODE_PERIOD_BC}"
                if self.only_warn:
                    warnings.warn(msg)
                else:
                    raise ValueError(msg)

    def _configure_stave(self):
        """Configures a specific section of the test"""
        self._section = 'STAVE'

    def _configure_alpide(self):
        """Configures a specific section of the test"""
        self._section = 'ALPIDE'
        self.SENSOR_POWERING_SCHEME        = self._get_config_enum('POWERING_SCHEME', daq_test.SensorPoweringScheme)
        self.SENSOR_AVDD                   = self._get_config_float('AVDD')
        self.SENSOR_DVDD                   = self._get_config_float('DVDD')
        self.SENSOR_VBB                    = self._get_config_float('VBB')
        self.SENSOR_AVDD_MAX_CURRENT       = self._get_config_float('AVDD_MAX_CURRENT')
        self.SENSOR_DVDD_MAX_CURRENT       = self._get_config_float('DVDD_MAX_CURRENT')
        self.SENSOR_PATTERN                = self._get_config_enum('PATTERN', testbench.SensorMatrixPattern)
        self.SENSOR_DRIVER_DAC             = self._get_config_int('DRIVER_DAC')
        self.SENSOR_PRE_DAC                = self._get_config_int('PRE_DAC')
        self.SENSOR_PLL_DAC                = self._get_config_int('PLL_DAC')
        self.LINK_SPEED                    = self._get_config_int('LINK_SPEED')
        self.SENSOR_CLOCK_GATING           = self._get_config_boolean('CLOCK_GATING')
        self.SENSOR_SKEW_START_OF_READOUT  = self._get_config_boolean('SKEW_START_OF_READOUT')
        self.SENSOR_CLUSTERING             = self._get_config_boolean('CLUSTERING')
        self.BB_ENABLE                     = self.SENSOR_VBB != 0.0
        self.EXCLUDED_SLAVE_CHIPIDEXT_LIST = self._get_config_list('EXCLUDED_SLAVE_CHIPIDEXT_LIST', int, allow_empty=True)
        self.OB_LOWER_MODULES              = self._get_config_list('OB_LOWER_MODULES', int, allow_empty=True)
        self.OB_UPPER_MODULES              = self._get_config_list('OB_UPPER_MODULES', int, allow_empty=True)
        self.GPIO_PU1_MODULES = [module-1 for module in self.OB_LOWER_MODULES]
        self.GPIO_PU2_MODULES = [module-1 for module in self.OB_UPPER_MODULES]
        self.DISABLE_MANCHESTER            = self._get_config_boolean('DISABLE_MANCHESTER')
        self.SEND_PULSES                   = self._get_config_boolean('SEND_PULSES')
        self.ANALOGUE_PULSING              = self._get_config_boolean('ANALOGUE_PULSING')
        self.PULSE_TO_STROBE               = self._get_config_boolean('PULSE_TO_STROBE')
        self.ENABLE_STROBE_GENERATION      = self._get_config_boolean('ENABLE_STROBE_GENERATION')
        self.GRST                          = self._get_config_boolean('GRST')

        assert self.LINK_SPEED in [600,1200], "Link Speed must be 600 or 1200"
        if self.LINK_SPEED == 600:
            self.LINK_SPEED = ModeControlIbSerialLinkSpeed.MBPS600
        else:
            self.LINK_SPEED = ModeControlIbSerialLinkSpeed.MBPS1200

    def _configure_readout(self):
        """Configures a specific section of the test"""
        self._section = 'READOUT'
        self.GPIO_CONNECTORS     = self._get_config_list('GPIO_CONNECTORS', int, allow_empty=True)
        self.EXCLUDE_GTH_LIST       = self._get_config_list('EXCLUDE_GTH_LIST', int, allow_empty=True)
        self.EXCLUDE_GPIO_LIST      = self._get_config_list('EXCLUDE_GPIO_LIST', int, allow_empty=True)
        self.ONLY_MASTERS           = self._get_config_boolean('ONLY_MASTERS')
        self.DRY                    = self._get_config_boolean('DRY')

        # Don't touch if not needed (generated from main config above)
        self.GTH_CONNECTOR = 2 #(MVTX CTRL connector = 2)
        GTH_PU_MODULE = 0
        self.READOUT_GTH_LIST = [gth for gth in range(9) if gth not in self.EXCLUDE_GTH_LIST]
        self.EXCLUDED_CHIPIDEXT_LIST = self.EXCLUDED_SLAVE_CHIPIDEXT_LIST

        self.GTH_ACTIVE = False
        self.GPIO_ACTIVE = False

        try:
            if self.DRY:
                self.READOUT_SOURCE = "NONE"
                self.MAIN_CONNECTOR = None
                self.READOUT_GTH_LIST = []
                self.READOUT_GPIO_LIST = []
            else:
                if self.LAYER in [testbench.LayerList.INNER, testbench.LayerList.NO_PT100]:
                    self.READOUT_SOURCE = "GTH"
                    self.GTH_ACTIVE = True
                    self.MAIN_CONNECTOR = self.GTH_CONNECTOR
                elif self.LAYER in [testbench.LayerList.MIDDLE,testbench.LayerList.OUTER]:
                    self.READOUT_SOURCE = "GPIO"
                    self.GPIO_ACTIVE = True
                    self.MAIN_CONNECTOR = self.GPIO_CONNECTORS[0]
                    self.READOUT_GPIO_LIST = [lane
                                              for connector in self.GPIO_CONNECTORS
                                              for lane in ru_transition_board.select_transition_board(ru_main_revision=self.RU_MAIN_REVISION,
                                                                                                      transition_board_version=self.RU_TRANSITION_BOARD_VERSION).gpio_subset_map[connector]
                                              if lane not in self.EXCLUDE_GPIO_LIST]
                    self.EXCLUDED_MASTER_CHIPIDEXT_LIST = [ru_transition_board.select_transition_board(ru_main_revision=self.RU_MAIN_REVISION,
                                                                                                      transition_board_version=self.RU_TRANSITION_BOARD_VERSION).gpio_lane2chipidext_lut[lane]
                                                          for lane in self.READOUT_GPIO_LIST
                                                          if lane in self.EXCLUDE_GPIO_LIST]
                    self.EXCLUDED_CHIPIDEXT_LIST += self.EXCLUDED_MASTER_CHIPIDEXT_LIST
                else:
                    raise NotImplementedError(f"Invalid LAYER {self.LAYER.name}")
        except AssertionError as ae:
            msg = f"Invalid {self.LAYER} in {self._config_file}, {ae}"
            if self.only_warn:
                warnings.warn(msg)
            else:
                raise ValueError(msg)
        except NotImplementedError as nie:
            if self.only_warn:
                warnings.warn(str(nie))
            else:
                raise

        self.POWER_UNIT_1_OUTPUT_CHANNEL_LIST = []
        self.POWER_UNIT_2_OUTPUT_CHANNEL_LIST = []
        try:
            if not self.DRY:
                if self.SENSOR_POWERING_SCHEME in [daq_test.SensorPoweringScheme.POWERUNIT,
                                                   daq_test.SensorPoweringScheme.DUAL_POWERUNIT,
                                                   daq_test.SensorPoweringScheme.MONITOR]:
                    if self.GTH_ACTIVE:
                        self.POWER_UNIT_1_OUTPUT_CHANNEL_LIST.append(GTH_PU_MODULE)
                    if self.GPIO_ACTIVE:
                        self.POWER_UNIT_1_OUTPUT_CHANNEL_LIST += self.GPIO_PU1_MODULES
                        self.POWER_UNIT_2_OUTPUT_CHANNEL_LIST += self.GPIO_PU2_MODULES
                elif self.SENSOR_POWERING_SCHEME == daq_test.SensorPoweringScheme.NONE:
                    pass
                else:
                    raise NotImplementedError(f"Invalid SENSOR_POWERING_SCHEME {self.SENSOR_POWERING_SCHEME.name}")
        except NotImplementedError as nie:
            if self.only_warn:
                warnings.warn(str(nie))
            else:
                raise

    def _configure_pa3(self):
        """Configures a specific section of the test"""
        self._section = 'PA3'
        self.PA3_READ_VALUES      = self._get_config_boolean('READ_VALUES')
        self.PA3_SCRUBBING_ENABLE = self._get_config_boolean('SCRUBBING')

    def _configure_readout_proc(self):
        """Configures a specific section of the test"""
        self._section = 'READOUT_PROC'
        self.READOUT_PROC_ACTIVE  = self._get_config_boolean('ACTIVE')
        self.READOUT_PROC_CFG     = self._get_config_str('CFG')

    def _configure_fdaq_proc(self):
        """Configures a specific section of the test"""
        self._section = 'FDAQ_PROC'
        self.FDAQ_STARTUP_TIME     = self._get_config_float('STARTUP_TIME')
        self.FDAQ_DATAFILE         = self._get_config_str('DATAFILE')
        self.FDAQ_ACTIVE_DMA       = self._get_config_list('ACTIVE_DMA', bool, allow_empty=False)

    def _configure_test(self):
        """Configures a specific section of the test"""
        self._section = 'TEST'
        self.TEST_DURATION                  = self._get_config_float('DURATION')
        self.READ_SENSORS_DURING_DATATAKING = self._get_config_boolean('READ_SENSORS_DURING_DATATAKING')
        self.EVENT_ANALYSYS_ONLINE          = self._get_config_boolean('EVENT_ANALYSYS_ONLINE')

    @staticmethod
    def _get_item_name(item):
        if item is None:
            return None
        else:
            return item.name

    def _store_configuration(self, logdir):
        """Stores the test configuration to file"""
        cfg = OrderedDict()
        cfg['yml'] = self.yml

        cfg['GITHASH_CRU'] = hex(self.GITHASH_CRU)
        cfg['GITHASH_RDO'] = hex(self.GITHASH_RDO)
        cfg['GITHASH_PA3'] = hex(self.GITHASH_PA3)

        cfg['CRU_SN']                  = self.CRU_SN
        cfg['CTRL_AND_DATA_LINK_LIST'] = self.CTRL_AND_DATA_LINK_LIST
        cfg['ONLY_DATA_LINK_LIST']     = self.ONLY_DATA_LINK_LIST
        cfg['TRIGGER_LINK_LIST']       = self.TRIGGER_LINK_LIST
        cfg['CRU_TYPE']                = self._get_item_name(self.CRU_TYPE)

        cfg['RU_MAIN_REVISION'] = self.RU_MAIN_REVISION
        cfg['RU_MINOR_REVISION'] = self.RU_MINOR_REVISION
        cfg['RU_TRANSITION_BOARD_VERSION'] = self._get_item_name(self.RU_TRANSITION_BOARD_VERSION)
        cfg['USE_RDO_USB'] = self.USE_RDO_USB

        cfg['POWER_BOARD_VERSION'] = self._get_item_name(self.POWER_BOARD_VERSION)
        cfg['POWER_BOARD_FILTER_50HZ_AC_POWER_MAINS_FREQUENCY'] = self.POWER_BOARD_FILTER_50HZ_AC_POWER_MAINS_FREQUENCY
        cfg['GPIO_PU1_MODULES'] = self.GPIO_PU1_MODULES
        cfg['GPIO_PU2_MODULES'] = self.GPIO_PU2_MODULES
        cfg['POWER_UNIT_1_OUTPUT_CHANNEL_LIST'] = self.POWER_UNIT_1_OUTPUT_CHANNEL_LIST
        cfg['POWER_UNIT_2_OUTPUT_CHANNEL_LIST'] = self.POWER_UNIT_2_OUTPUT_CHANNEL_LIST
        cfg['POWERUNIT_RESISTANCE_OFFSET_PT100'] = self.POWERUNIT_RESISTANCE_OFFSET_PT100
        cfg['POWERUNIT_LIMIT_TEMPERATURE_SOFTWARE'] = self.POWERUNIT_LIMIT_TEMPERATURE_SOFTWARE
        cfg['POWERUNIT_LIMIT_TEMPERATURE_HARDWARE'] = self.POWERUNIT_LIMIT_TEMPERATURE_HARDWARE
        cfg['COMPENSATE_VOLTAGE_DROP'] = self.COMPENSATE_VOLTAGE_DROP

        cfg['TRIGGER_PERIOD_BC'] = self.TRIGGER_PERIOD_BC
        cfg['NUM_TRIGGERS'] = self.NUM_TRIGGERS
        cfg['TRIGGERING_MODE'] = self._get_item_name(self.TRIGGERING_MODE)
        cfg['USE_LTU'] = self.USE_LTU
        cfg['USE_RUN_SERVER'] = self.USE_RUN_SERVER
        cfg['TRIGGERED_STROBE_DURATION'] = self.TRIGGERED_STROBE_DURATION
        cfg['TRIGGER_SOURCE'] = self.TRIGGER_SOURCE
        cfg['TRIGGER_TF'] = self.TRIGGER_TF
        cfg['TRIGGER_HBF_PER_TF'] = self.TRIGGER_HBF_PER_TF
        cfg['TRIGGER_HBA_PER_TF'] = self.TRIGGER_HBA_PER_TF

        cfg['LTU_HOSTNAME'] = self.LTU_HOSTNAME
        cfg['LAYER'] = self._get_item_name(self.LAYER)
        cfg['SENSOR_POWERING_SCHEME'] = self._get_item_name(self.SENSOR_POWERING_SCHEME)
        cfg['SENSOR_AVDD'] = self.SENSOR_AVDD
        cfg['SENSOR_DVDD'] = self.SENSOR_DVDD
        cfg['SENSOR_VBB'] = self.SENSOR_VBB
        cfg['SENSOR_AVDD_MAX_CURRENT'] = self.SENSOR_AVDD_MAX_CURRENT
        cfg['SENSOR_DVDD_MAX_CURRENT'] = self.SENSOR_DVDD_MAX_CURRENT
        cfg['SENSOR_PATTERN'] = self.SENSOR_PATTERN
        cfg['SENSOR_DRIVER_DAC'] = self.SENSOR_DRIVER_DAC
        cfg['SENSOR_PRE_DAC'] = self.SENSOR_PRE_DAC
        cfg['SENSOR_PLL_DAC'] = self.SENSOR_PLL_DAC
        cfg['SENSOR_CLOCK_GATING'] = self.SENSOR_CLOCK_GATING
        cfg['SENSOR_SKEW_START_OF_READOUT'] = self.SENSOR_SKEW_START_OF_READOUT
        cfg['SENSOR_CLUSTERING'] = self.SENSOR_CLUSTERING
        cfg['BB_ENABLE'] = self.BB_ENABLE
        cfg['OB_LOWER_MODULES'] = self.OB_LOWER_MODULES
        cfg['OB_UPPER_MODULES'] = self.OB_UPPER_MODULES
        cfg['EXCLUDED_SLAVE_CHIPIDEXT_LIST'] = self.EXCLUDED_SLAVE_CHIPIDEXT_LIST
        cfg['EXCLUDED_MASTER_CHIPIDEXT_LIST'] = self.EXCLUDED_MASTER_CHIPIDEXT_LIST
        cfg['EXCLUDED_CHIPIDEXT_LIST'] = self.EXCLUDED_CHIPIDEXT_LIST
        cfg['DISABLE_MANCHESTER'] = self.DISABLE_MANCHESTER
        cfg['ANALOGUE_PULSING'] = self.ANALOGUE_PULSING
        cfg['SEND_PULSES'] = self.SEND_PULSES
        cfg['PULSE_TO_STROBE'] = self.PULSE_TO_STROBE
        cfg['ENABLE_STROBE_GENERATION'] = self.ENABLE_STROBE_GENERATION

        cfg['DRY'] = self.DRY
        cfg['GTH_ACTIVE'] = self.GTH_ACTIVE
        cfg['GPIO_ACTIVE'] = self.GPIO_ACTIVE
        cfg['READOUT_SOURCE'] = self.READOUT_SOURCE
        cfg['EXCLUDE_GTH_LIST'] = self.EXCLUDE_GTH_LIST
        cfg['EXCLUDE_GPIO_LIST'] = self.EXCLUDE_GPIO_LIST
        cfg['GTH_CONNECTOR'] = self.GTH_CONNECTOR
        cfg['GPIO_CONNECTORS'] = self.GPIO_CONNECTORS
        cfg['MAIN_CONNECTOR'] = self.MAIN_CONNECTOR
        cfg['READOUT_GPIO_LIST'] = self.READOUT_GPIO_LIST
        cfg['READOUT_GTH_LIST'] = self.READOUT_GTH_LIST
        cfg['ONLY_MASTERS'] = self.ONLY_MASTERS

        cfg['TEST_DURATION'] = self.TEST_DURATION

        cfg['PA3_READ_VALUES'] = self.PA3_READ_VALUES
        cfg['PA3_SCRUBBING_ENABLE'] = self.PA3_SCRUBBING_ENABLE

        cfg['READ_SENSORS_DURING_DATATAKING'] = self.READ_SENSORS_DURING_DATATAKING
        cfg['EVENT_ANALYSYS_ONLINE'] = self.EVENT_ANALYSYS_ONLINE
        cfg['SUBRACK'] = self.SUBRACK

        cfg = self.store_scan_specific_config(cfg)

        with open(logdir + '/test_config.json','w') as cfg_file:
            cfg_file.write(json.dumps(cfg, sort_keys=True, indent=4))

    def store_scan_specific_config(self, cfg):
        """not used by daq test but used by ob tests"""
        return cfg
