#!/usr/bin/env python3.9

"""Test for verifying the functionality of the RUs/PBs in a crate"""

import argparse
import logging
import os
import yaml
import sys
import time
import traceback
import unittest

script_path = os.path.dirname(os.path.realpath(__file__))
modules_path = os.path.join(
    script_path, '../../../modules/board_support_software/software/py/')
sys.path.append(modules_path)
from module_includes import *

sys.path.append(os.path.join(
    script_path, '../.'))
import testbench
import crate_mapping

import daq_test
import threshold_scan
from pu_controller import TempInterlockEnable

def setup_subrack(subrack):
    assert subrack in crate_mapping.subrack_lut.keys(), f"{subrack} not in {list(crate_mapping.subrack_lut.keys())}"
    return crate_mapping.subrack_lut[subrack]

def check_subrack(subrack, parameter_list, tb_dict):
    for flp, cru_id, layer, gbt_ch, ru_sn, ru_index, rdo_githash, pa3_githash in parameter_list:
        assert os.uname().nodename in flp, f"wrong flp {os.uname().nodename} selected for running the test: expect {flp}"
        assert tb_dict[subrack].cru_sn == cru_id, f"wrong cru_id {cru_id} selected for running the test {tb_dict[subrack].cru_sn}"
        assert layer in range(7)
        assert gbt_ch in range(24)
        assert ru_index in range(48)
        assert rdo_githash in range(0xFFFFFFFF+1)
        assert pa3_githash in range(0xFFFFFFFF+1)
    return {gbt_ch: (layer, ru_sn, ru_index, rdo_githash, pa3_githash) for _,_,layer,gbt_ch,ru_sn,ru_index,rdo_githash, pa3_githash in parameter_list}


class TestConfig():

    def __init__(self, config_file, bitfile=None) -> None:
        self.logger = logging.getLogger()

        with open(os.path.realpath(config_file)) as cfg:
            cfg_data = yaml.load(cfg, Loader=yaml.SafeLoader)

        if bitfile is None:
            self.bitfile = cfg_data['BITFILE']
        else:
            self.bitfile = bitfile

        if self.bitfile[-11:-4] == "_bs_ecc":
            self.bitfile_version = int(self.bitfile[-19:-11], base=16)
        elif self.bitfile[-8:-4] == "_ecc":
            self.bitfile_version = int(self.bitfile[-16:-8], base=16)
        elif self.bitfile[-7:-4] == "_bs":
            self.bitfile_version = int(self.bitfile[-15:-7], base=16)
        else:
            self.bitfile_version = int(self.bitfile[-12:-4], base=16)

        self.flash_via_fifo = cfg_data['FLASH_VIA_FIFO']
        self.subrack_list = cfg_data['SUBRACK_LIST']
        assert set(self.subrack_list) <= {'IB-test', 'UT', 'OL-test', 'ML-test','IB-table', 'ORNL', 'LANL'}, "Setup list can only contain IB-test, UT, OL-test, ML-test, IB-table, ORNL, LANL"

        self.ignore_checks = cfg_data['IGNORE_CHECKS']
        self.skip_wet = cfg_data['SKIP_WET']

        self.ib_tb_config_file = os.path.join(script_path, cfg_data['IB_TB_CONFIG_FILE'])
        self.ols_tb_config_file = os.path.join(script_path, cfg_data['OLS_TB_CONFIG_FILE'])
        self.mls_tb_config_file = os.path.join(script_path, cfg_data['MLS_TB_CONFIG_FILE'])

        self.mvtx_daqtest_config_file = os.path.join(script_path, cfg_data['MVTX_DAQTEST_CONFIG_FILE'])
        self.ibs_daqtest_config_file = os.path.join(script_path, cfg_data['IBS_DAQTEST_CONFIG_FILE'])
        self.ols_daqtest_config_file = os.path.join(script_path, cfg_data['OLS_DAQTEST_CONFIG_FILE'])
        self.mls_daqtest_config_file = os.path.join(script_path, cfg_data['MLS_DAQTEST_CONFIG_FILE'])
        self.ibs_daqtest_excl0_config_file = os.path.join(script_path, cfg_data['IBS_DAQTEST_EXCL0_CONFIG_FILE'])
        self.ibs_daqtest_excl2_config_file = os.path.join(script_path, cfg_data['IBS_DAQTEST_EXCL2_CONFIG_FILE'])

        self.threshold_ibs_config_file = os.path.join(script_path, cfg_data['THRESHOLD_IBS_CONFIG_FILE'])
        self.threshold_ols_config_file = os.path.join(script_path, cfg_data['THRESHOLD_OLS_CONFIG_FILE'])
        self.threshold_mls_config_file = os.path.join(script_path, cfg_data['THRESHOLD_MLS_CONFIG_FILE'])

        self.dctrl_tests_ib = cfg_data['DCTRL_TESTS_IB']
        self.dctrl_tests_mls = cfg_data['DCTRL_TESTS_MLS']
        self.dctrl_tests_ols = cfg_data['DCTRL_TESTS_OLS']

        self.swt_test = cfg_data['SWT_TEST']
        self.ib_broken_chips = cfg_data['IB_BROKEN_CHIPS']
        self.ml_broken_chips = cfg_data['ML_BROKEN_CHIPS']
        self.ol_broken_chips = cfg_data['OL_BROKEN_CHIPS']

        self.powerunit                = cfg_data['POWERUNIT']
        assert self.powerunit > 0 and self.powerunit < 3, f"Powerunit not valid: {self.powerunit}"
        self.powerunit_max_bb_voltage = cfg_data['MAX_BB_VOLTAGE']
        self.powerunit_max_bb_current = cfg_data['MAX_BB_CURRENT']
        self.powerunit_max_voltage    = cfg_data['MAX_VOLTAGE']
        self.powerunit_max_current    = cfg_data['MAX_CURRENT']
        self.powerunit_max_tmp        = cfg_data['MAX_TMP']
        self.powerunit_min_tmp        = cfg_data['MIN_TMP']
        self.powerunit_ext1           = cfg_data['EXT1']
        self.powerunit_ext2           = cfg_data['EXT2']
        self.powerunit_monitor_cycles = cfg_data['MONITOR_CYCLES']
        self.powerunit_wr_cycles      = cfg_data['WRITE_READ_CYCLES']

        # These should NOT change
        if "CI" in os.environ:
            self.ibs_readout_output = "/tmp/ramdisk/ci_data.lz4"
            self.ols_readout_output = "/tmp/ramdisk_obs/ci_ols_data.lz4"
            self.mls_readout_output = "/tmp/ramdisk_obs/ci_mls_data.lz4"
        else:
            self.ibs_readout_output = "/tmp/ramdisk/data.lz4"
            self.ols_readout_output = "/tmp/ramdisk_obs/data_ols.lz4"
            self.mls_readout_output = "/tmp/ramdisk_obs/data_mls.lz4"

        self.tb_dict = {}
        self.ru_parameter_dict = {}
        for subrack in self.subrack_list:

            self.logger.info(f"Logging parsed values, subrack: {subrack}, config_file: {config_file}")
            parameter_list = setup_subrack(subrack)

            if subrack in ['UT', 'IB-test', 'IB-table', 'ORNL', 'LANL']:
                self.tb_dict[subrack] = testbench.configure_testbench(config_file_path=self.ib_tb_config_file,
                                                                      run_standalone=True)
            if subrack == 'OL-test':
                self.tb_dict[subrack] = testbench.configure_testbench(config_file_path=self.ols_tb_config_file,
                                                                      run_standalone=True)
            if subrack == 'ML-test':
                self.tb_dict[subrack] = testbench.configure_testbench(config_file_path=self.mls_tb_config_file,
                                                                      run_standalone=True)

            self.ru_parameter_dict[subrack] = check_subrack(subrack, parameter_list, self.tb_dict)


class TestcaseBase(unittest.TestCase):
    bitfile_loaded = False
    pb_connected = False
    stave_powered_on = True

    def __init__(self, methodName: str) -> None:
        super().__init__(methodName=methodName)
        self.subrack = None

    def setUp(self):
        self.subrack = self.get_subrack()
        gbt_channel = TestcaseBase.test_config.tb_dict[self.subrack].ctrl_link_list[0]
        self.configure_test(gbt_channel=gbt_channel)
        self.tb = TestcaseBase.test_config.tb_dict[self.subrack]

        self.set_parameters()
        self.set_objects()
        self.tb.initialize_boards()

    @staticmethod
    def do_ignore_checks():
        return TestcaseBase.test_config.ignore_checks

    @staticmethod
    def do_skip_wet():
        return TestcaseBase.test_config.skip_wet

    @staticmethod
    def is_bitfile_loaded():
        return TestcaseBase.bitfile_loaded

    @staticmethod
    def set_bitfile_loaded(bool):
        TestcaseBase.bitfile_loaded = bool

    @staticmethod
    def is_pb_connected():
        return TestcaseBase.pb_connected

    @staticmethod
    def set_pb_connected(bool):
        TestcaseBase.pb_connected = bool

    @staticmethod
    def is_stave_powered_on():
        return TestcaseBase.stave_powered_on

    @staticmethod
    def set_stave_power_status(status):
        TestcaseBase.stave_powered_on = status

    def configure_test(self, gbt_channel):
        self.gbt_channel = gbt_channel

    def get_subrack(self):
        if 'IB-test' in TestcaseBase.test_config.subrack_list:
            subrack = 'IB-test'
        elif 'IB-table' in TestcaseBase.test_config.subrack_list:
            subrack = 'IB-table'
        elif 'OL-test' in TestcaseBase.test_config.subrack_list:
            subrack = 'OL-test'
        elif 'ML-test' in TestcaseBase.test_config.subrack_list:
            subrack = 'ML-test'
        elif 'ORNL' in TestcaseBase.test_config.subrack_list:
            subrack = 'ORNL'
        elif 'LANL' in TestcaseBase.test_config.subrack_list:
            subrack = 'LANL'
        else:
            self.skipTest(f"Invalid subrack: {TestcaseBase.test_config.subrack_list}")
        return subrack

    def get_subrack_shorthand(self):
        if self.subrack in ['IB-test','IB-table', 'UT', 'ORNL', 'LANL']:
            return 'ibs'
        if self.subrack == 'ML-test':
            return 'mls'
        if self.subrack == 'OL-test':
            return 'ols'
        raise NotImplementedError

    def set_objects(self):
        self.logger = logging.getLogger(__name__)

        self.cru = self.tb.cru
        for i, rdo in enumerate(self.tb.rdo_list):
            if rdo.get_gbt_channel() == self.gbt_channel:
                self.rdo = self.tb.rdo_list[i]
                break

    def set_parameters(self):
        self.layer, self.ru_sn, self.ru_index, self.rdo_githash, self.pa3_githash = TestcaseBase.test_config.ru_parameter_dict[self.subrack][self.gbt_channel]
        self.is_ib = self.layer in [0,1,2]
        self.is_ml = self.layer in [3,4]
        self.is_ol = self.layer in [5,6]

    def _assert_equal_hex(self, expected, read):
        self.assertEqual(expected, read, f"Got 0x{read:08X} expected 0x{expected:08X}")

    def _assert_equal_dict_excluded_keys(self, expected, read, excluded_keys):
        for key in read.keys():
            if key not in excluded_keys:
                self.assertEqual(expected[key], read[key], f"Readback errors for chipid 0x{key:02x}")


class TestcaseDry(TestcaseBase):
    def setUp(self):
        if not TestcaseBase.is_bitfile_loaded() and not TestcaseBase.do_ignore_checks():
            self.skipTest("Bitfiles not loaded!")
        super().setUp()


class TestcaseWet(TestcaseBase):

    def setUp(self):
        if not TestcaseBase.is_bitfile_loaded() and not TestcaseBase.do_ignore_checks():
            self.skipTest("Bitfile not loaded!")
        if not TestcaseBase.is_stave_powered_on() and not TestcaseBase.do_ignore_checks():
            self.skipTest("Stave is off!")
        if TestcaseBase.do_skip_wet():
            self.skipTest("Skipping wet tests")
        super().setUp()


# Ensure that staves are off before loading new
class AAAAAAAA_TestcaseStavePowerOff(TestcaseBase):

    def setUp(self):
        super().setUp()

    def test_power_off(self):
        # Set global stave power status to False before test
        # in the case of fail
        TestcaseBase.set_stave_power_status(False)
        if self.subrack in ['IB-test', 'UT','IB-table','ORNL', 'LANL']:
            self.tb.power_off_all_ib_staves(True)
            self.tb.log_values_ib_stave()
        elif self.subrack == 'ML-test':
            self.tb.power_off_ml_stave(True)
            self.tb.log_values_ml_stave()
        elif self.subrack == 'OL-test':
            self.tb.power_off_ob_stave(True)
            self.tb.log_values_ob_stave()
        else:
            raise NotImplementedError


# Ensure that staves are power off at the end of the tests
class ZZZZZZZZZ_TestcaseStavePowerOff(TestcaseBase):

    def setUp(self):
        super().setUp()

    def test_power_off(self):
        # Set global stave power status to False before test
        # in the case of fail
        TestcaseBase.set_stave_power_status(False)
        if self.subrack in ['IB-test', 'UT', 'IB-table', 'ORNL', 'LANL']:
            self.tb.power_off_all_ib_staves(True)
            self.tb.log_values_ib_stave()
        elif self.subrack == 'ML-test':
            self.tb.power_off_ml_stave(True)
            self.tb.log_values_ml_stave()
        elif self.subrack == 'OL-test':
            self.tb.power_off_ob_stave(True)
            self.tb.log_values_ob_stave()
        else:
            raise NotImplementedError


class A_TestcaseLoadBitfile(TestcaseBase):

    def setUp(self):
        if TestcaseBase.is_stave_powered_on():
                self.skipTest("Stave is on! Too dangerous to load new bitfile!")
        super().setUp()

    def test_check_pa3_communication(self):
        for i,rdo in enumerate(self.tb.rdo_list):
            pa3_fee_id = int(rdo.pa3.dump_config()['DIPSWITCH1'],16) >> 2
            expected = rdo.identity.get_fee_id()
            self.assertEqual(expected, pa3_fee_id, f"Wrong fee_id {pa3_fee_id} value from pa3, {expected} expected")

    def test_flash_bitfiles_ultrascale_fifo(self):
        if not TestcaseBase.test_config.flash_via_fifo:
            self.skipTest("Flashing via PA3 I2C")
        for rdo in self.tb.rdo_list:
            rdo.program_xcku()
        self.tb.initialize_boards()

        for rdo in self.tb.rdo_list:
            if rdo.git_hash() == TestcaseBase.test_config.bitfile_version:
                self.logger.info(f"Skipping flashing on RDO {rdo.get_gbt_channel()}, requested version already loaded!")
            else:
                rdo.flash_bitfiles_to_block(filename=TestcaseBase.test_config.bitfile, golden=False, use_ultrascale_fifo=True)

    def test_flash_bitfiles_PA3_i2c(self):
        if TestcaseBase.test_config.flash_via_fifo:
            self.skipTest("Flashing via Ultrascale fifo")

        for rdo in self.tb.rdo_list:
            rdo.program_xcku()
        self.tb.initialize_boards()

        for rdo in self.tb.rdo_list:
            if rdo.git_hash() == TestcaseBase.test_config.bitfile_version:
                self.logger.info(f"Skipping flashing on RDO {rdo.get_gbt_channel()}, requested version already loaded!")
            else:
                rdo.flash_bitfiles_to_block(filename=TestcaseBase.test_config.bitfile, golden=False, use_ultrascale_fifo=False)

    def test_load_bitfiles(self):
        bitfiles_loaded = True
        for rdo in self.tb.rdo_list:
            bitfile_loaded = rdo.program_xcku()
            if not bitfile_loaded:
                bitfiles_loaded = False
        self.assertTrue(bitfiles_loaded, "NOT ALL BITFILES LOADED, check logs!")
        self.tb.initialize_boards()
        for rdo in self.tb.rdo_list:
            read_version = rdo.git_hash()
            self.assertEqual(TestcaseBase.test_config.bitfile_version, read_version, f"INCORRECT VERSION READ ON RDO {rdo.get_gbt_channel()}, EXPECTED:\t 0x{TestcaseBase.test_config.bitfile_version:07X}, READ:\t 0x{read_version:07X}")

        TestcaseBase.set_bitfile_loaded(True)


class B_TestcaseRDO(TestcaseDry):

    def setUp(self):
        super().setUp()

    def test_1_initialize_rdo(self):
        self.rdo.initialize()

    def test_2_initialize_gbtx12(self):
        self.assertTrue(self.rdo.initialize_gbtx12(pre_check_fsm=False), "Could not initialize GBTx 1&2")

    def test_rdo_githash(self):
        """
        Checks that the XCKU have the correct githash
        """
        self._assert_equal_hex(expected=self.rdo_githash, read=self.rdo.git_hash())

    def test_feeid(self):
        """
        Checks the fee id of the board
        """
        self.rdo.identity.is_fee_id_correct(layer=self.layer, stave=self.ru_index)

    def test_sn(self):
        """
        Checks the serial number of the board
        """
        self.assertIsNot(self.ru_sn, None)
        dna_rdo = self.rdo.identity.get_dna()
        found_in_db = False
        sn = self.rdo.identity.decode_sn(dna_rdo)
        if sn is not None:
            found_in_db = True
        self.assertTrue(found_in_db,f"DNA {dna_rdo} for SN{self.ru_sn} not found in database")
        self.assertEqual(sn, self.ru_sn, f"SN{sn} not matching expected value {self.ru_sn}")

    def test_swt(self):
        errors = self.rdo.test_swt(nrtests=TestcaseBase.test_config.swt_test, use_ru=True)
        self.assertEqual(errors, 0, "Errors observed!")

    def test_gbtx_access(self):
        """
        Test for issue CRU_ITS#154

        https://gitlab.cern.ch/alice-its-wp10-firmware/CRU_ITS/-/issues/154
        """
        sca = self.rdo.gbtx0_swt.get_phase_detector_charge_pump()
        rdo = self.rdo.gbtx0_swt.get_phase_detector_charge_pump()
        self.assertEqual(sca,rdo,"Mismatch between SCA and RDO read of same GBTx register")

    def test_read_temperature(self, limit=50):
        """Checks the RU temperature to be lower than the limit"""
        temperature = self.rdo.sysmon.get_temperature()
        self.logger.info(f"Sysmon temperature\t{temperature:.3f} C")
        self.assertLess(temperature, limit, f"Temperature over limit {temperature}/{limit}")

    def test_sysmon_access(self):
        """Checks the XCKU sysmon values and logs them to compare to the SCA values"""
        self.rdo.sysmon.log_voltages()

    def test_dipswitch(self):
        """Checks that the dipswitch is set correctly"""
        dipswitch = 1 + (self.layer << 6) + (self.ru_index << 2)
        self.assertEqual(dipswitch, self.rdo.identity.get_dipswitch(), "Dipswitches not set correctly")


class TestcasePUController(TestcaseDry):

    def setUp(self):
        super().setUp()

        if TestcaseBase.test_config.powerunit == 1:
            self.pu = self.rdo.powerunit_1
        else:
            self.pu = self.rdo.powerunit_2
        self.pu_ctrl = self.pu.controller
        self.pu_aux_mon = self.pu.aux_monitor
        self.pu_main_mon = self.pu.main_monitor

        self.MAX_BB_VOLTAGE = TestcaseBase.test_config.powerunit_max_bb_voltage
        self.MAX_BB_CURRENT = TestcaseBase.test_config.powerunit_max_bb_current
        self.MAX_VOLTAGE    = TestcaseBase.test_config.powerunit_max_voltage
        self.MAX_CURRENT    = TestcaseBase.test_config.powerunit_max_current
        self.MAX_TMP        = TestcaseBase.test_config.powerunit_max_tmp
        self.MIN_TMP        = TestcaseBase.test_config.powerunit_min_tmp

    def tearDown(self):
        self.logger.debug("Power off and revert to nominal values")

        self.pu.power_off_all()
        self.pu_ctrl.reset_tripped_latch()
        self.pu_ctrl.set_clock_interlock_threshold(2.05)
        self.pu_ctrl.reset_all_fifos()
        self.pu_ctrl.enable_temperature_interlock(internal_temperature_limit=35, suppress_warnings=True)
        time.sleep(1)

    def _test_pu_values(self, use_i2c=True, cycles=1):
        """Reads all values for the powerunit and verifies them when the staves are OFF but power is set up"""

        for i in range(cycles):
            #voltages and currents
            values = self.pu.get_values_modules(use_i2c=use_i2c, suppress_warnings=True)
            assert values['power_enable_status'] == 0, f"{__name__}: ({i}) power_enable_status should be 0 (code), was {values['power_enable_status']}"
            assert values['bias_enable_status'] == 0,f"{__name__}: ({i}) bias_enable_status should be 0 (code), was {values['bias_enable_status']}"
            assert values['bb_voltage'] < self.MAX_BB_VOLTAGE, f"{__name__}: ({i}) bb_voltage should be less than {self.pu._code_to_vbias(self.MAX_BB_VOLTAGE)}, was {self.pu._code_to_vbias(values['bb_voltage'])}"
            assert values['bb_current'] < self.MAX_BB_CURRENT, f"{__name__}: ({i}) bb_current should be less than {self.pu._code_to_ibias(self.MAX_BB_CURRENT)}, was {self.pu._code_to_ibias(values['bb_current'])}"
            for val in [value for key, value in values.items() if 'vdd_voltage' in key.lower()]:
                assert val < self.MAX_VOLTAGE, f"{__name__}: ({i}) vdd_voltage should be less than {self.pu._code_to_vpower(self.MAX_VOLTAGE)}, was {self.pu._code_to_vpower(val)}"
            for val in [value for key, value in values.items() if 'vdd_current' in key.lower()]:
                assert val < self.MAX_CURRENT, f"{__name__}: ({i}) vdd_current should be less than {self.pu._code_to_ipower(self.MAX_CURRENT)}, was {self.pu._code_to_ipower(val)}"

            #temperatures
            values = self.pu.read_all_temperatures()
            assert values['PU'] > self.MIN_TMP and values['PU'] < self.MAX_TMP, f"""{__name__}: ({i}) PU tmp should be between {self.MIN_TMP} and {self.MAX_TMP}, was {values['PU']}"""
            for val in [values for key, value in values.items() if 'EXT' in key.lower()]:
                assert val > self.MIN_TMP and val < self.MAX_TMP, f"""{__name__}: ({i}) EXT tmp should be between {self.MIN_TMP} and {self.MAX_TMP}, was {val}"""

    def _test_pu_counters(self):
        """Verifies that the i2c transaction counters are OK"""

        counters = self.pu_aux_mon.read_counters(reset_after=True)
        for key, value in counters.items():
            if "completed_byte_count" in key:
                assert value > 0, f"{__name__}: {key} should be a large number"
            else:
                assert value == 0, f"{__name__}: {key} should be zero"
        counters = self.pu_main_mon.read_counters(reset_after=True)
        for key, value in counters.items():
            if "completed_byte_count" in key:
                assert value > 0, f"{__name__}: {key} should be a large number"
            else:
                assert value == 0, f"{__name__}: {key} should be zero"

    def _test_tripped_latch(self, expected_tripped_latch):
        tripped_latch = self.pu_ctrl.get_tripped_latch()
        for i, (key, value) in enumerate(tripped_latch[0].items()):
            assert value == expected_tripped_latch[i], f"{__name__}: {key} should be " + str(expected_tripped_latch[i]) + ". Value read " + str(value)

    def _test_tripped(self, expected_tripped):
        tripped = self.pu_ctrl.get_tripped()
        for i, (key, value) in enumerate(tripped[0].items()):
            assert value == expected_tripped[i], f"{__name__}: {key} should be " + str(expected_tripped[i]) + ". Value read " + str(value)


class C1_TestCasePUConnection(TestcasePUController):

    def test_is_pb_connected(self):
        self.pu.reset_all_counters()
        self.pu.get_power_enable_status()
        self.pu.get_bias_enable_status()
        try:
            self._test_pu_counters()
            TestcaseBase.set_pb_connected(True)
        except:
            raise Exception("Error in powerunit transaction counters. Is the powerunit connected?")


class TestcasePUControllerConnected(TestcasePUController):

    def setUp(self):
        if not TestcaseBase.is_pb_connected() and not TestcaseBase.do_ignore_checks():
            self.skipTest("PB is not connected, no reason to continue tests...")
        super().setUp()

        self.logger.debug("Setup of powerunit test. Set correct voltage/current. Turn off all interlocks and set in default state")
        self.rdo.alpide_control.disable_dclk()
        self.pu.initialize()
        self.pu_ctrl.set_clock_interlock_threshold(2.0)
        self.pu.setup_power_modules(dvdd=1.82, dvdd_current=1.5,
                           avdd=1.82, avdd_current=1.5,
                           bb=0,
                           module_list=[0,1,2,3,4,5,6,7],
                           check_interlock=False,
                           no_offset=False,
                           verbose=False)
        for i in range(3): #sets up temperature sensors to read sensible values
            self.pu.initialize_temperature_sensor(i)
        self.pu_ctrl.disable_all_interlocks()
        self.pu.reset_all_counters()
        self.pu_ctrl.reset_tripped_latch()
        time.sleep(1)


class C2_TestCasePUComms(TestcasePUControllerConnected):

    def test_pu_writeread(self):
        """
        Test of Write and Read to PowerUnit. The only RW regs on the Powerboard are BIAS enable and POWER enable.
        """
        if not self.rdo.identity.is_ib():
            self.skipTest("Only run for IB")
        for i in range (TestcaseBase.test_config.powerunit_wr_cycles):
            mask = i % 255
            i_pwr = mask << 8
            self.pu.enable_bias_with_mask(mask)
            self.pu.enable_power_with_mask(i_pwr)
            time.sleep(0.1)
            assert self.pu.get_bias_enable_status() == mask, "test_power_unitIB: bias_enable should be " + str(mask)
            assert self.pu.get_power_enable_status() == i_pwr, "test_power_unitIB: power_enable should be " + str(i_pwr)

    def test_pu_monitor_i2c(self):
        self._test_pu_monitoring(use_i2c=True, cycles=TestcaseBase.test_config.powerunit_monitor_cycles, test_conflicts=False)

    def test_pu_monitor_ctrl(self):
        self._test_pu_monitoring(use_i2c=False, cycles=TestcaseBase.test_config.powerunit_monitor_cycles, test_conflicts=False)

    def test_pu_monitor_i2c_ctrl_conflicts(self):
        self._test_pu_monitoring(use_i2c=False, cycles=TestcaseBase.test_config.powerunit_monitor_cycles, test_conflicts=True)

    def _test_pu_monitoring(self, use_i2c=True, cycles=1, test_conflicts=False):
        """Test of monitoring of values from PowerUnit when all channels are OFF. Verify that all transactions are OK and values are as expected"""

        assert not (use_i2c == True and test_conflicts == True), "If test_conflicts is True then use_i2c must be False"
        # set up high/low thresholds to avoid interlocks

        if self.subrack in ['ORNL', 'LANL']:
            self.pu_ctrl.enable_temperature_interlock(internal_temperature_limit=50,
                                                      internal_temperature_low_limit=0,
                                                      suppress_warnings=True)
        else:
            self.pu_ctrl.enable_temperature_interlock(internal_temperature_limit=50,
                                                      ext1_temperature_limit=50,
                                                      internal_temperature_low_limit=0,
                                                      suppress_warnings=True)
        time.sleep(2)  # ADC and RTD values take some time to initialize and read properly
        if use_i2c:
            self.pu_ctrl.set_temperature_interlock_enable_mask(0x0) #disable all interlocks
        else:
            self.pu_ctrl.set_temperature_interlock_enable_mask(0x7)
            self.pu_ctrl.enable_power_bias_interlock(0xFF, 0xFF)

        self._test_pu_values(use_i2c=use_i2c, cycles=cycles)
        self._test_pu_counters()
        if test_conflicts:
            # When this is true it means that manually reads are done at the same time as
            # monitoring is active
            self._test_pu_values(use_i2c=True, cycles=cycles)
            self._test_pu_counters()


class C3_TestCasePUInterlocks(TestcasePUControllerConnected):

    def _enable_power_all_modules(self):
        mask = 0
        for j in range(16): # power on all
            mask = mask | (0x1 << j)
            self.pu.enable_power_with_mask(mask=mask)
            time.sleep(0.2)

    def _turn_off_one_ch_all_else_on(self, ch):
        mask = 0xFFFF ^ (1 << ch)
        self.pu.enable_power_with_mask(mask=mask)
        time.sleep(0.5)

    def _turn_off_one_bias_ch_all_else_on(self, module):
        mask = 0xFF & ~2**module
        self.pu.enable_bias_with_mask(mask=mask)
        time.sleep(0.5)

    def _get_expected_power_enable_after_nobias_trip(self, ch):
        stave = ch//2
        expected_power_enable_status = 0xFFFF ^ (1 << (stave*2) | 1 << (stave*2+1))
        return expected_power_enable_status

    def _get_ch_indicator(self, ch):
        return f"{'A' if ch%2==0 else 'D'}VDD{(ch+2)//2}"

    def test_pu_temp_interlocks(self):
        """
        Verifies that all temperature interlocks fires when the shall and do not fire when they should not
        """

        temps = self.pu.read_all_temperatures()
        int_limit = temps["PU"] - 5
        ext1_limit = temps["EXT1"] - 5
        ext2_limit = temps["EXT2"] - 5

        #Testing internal temperature interlock - other interlocks are disabled
        self.pu_ctrl.enable_temperature_interlock(internal_temperature_limit=50,
                                              internal_temperature_low_limit=0,
                                              suppress_warnings=True)
        # lowering ext1/ext2 temp limit to fire interlock IF enabled - should not be
        self.pu_ctrl._set_temperature_limit(1, ext1_limit)
        self.pu_ctrl._set_temperature_limit(2, ext2_limit)
        expected_tripped_latch = [False, False, False, False, False, False, False, False]
        time.sleep(0.5)
        self._test_tripped_latch(expected_tripped_latch)
        # Lowering internal temperature threshold - should fire interlock
        # When interlock is fired - also TURN_OFF_MODULES are set
        self.pu_ctrl._set_temperature_limit(0, int_limit)
        time.sleep(0.2)
        # this is expected for ALL layers
        expected_tripped_latch = [True, True, True, False, False, False, False, False]
        self._test_tripped_latch(expected_tripped_latch)
        # clears all interlocks
        self.pu_ctrl.disable_all_interlocks()
        self.pu_ctrl.reset_tripped_latch()
        time.sleep(0.2)
        # testing low temperature threshold - setting VERY high value
        # this should also fire interlock
        self.pu_ctrl.enable_temperature_interlock(internal_temperature_limit=50,
                                          internal_temperature_low_limit=0,
                                          suppress_warnings=True)
        time.sleep(0.2)
        self.pu_ctrl.reset_tripped_latch()
        expected_tripped_latch = [False, False, False, False, False, False, False, False]
        self._test_tripped_latch(expected_tripped_latch)
        self.pu_ctrl._set_low_temperature_limit(0, 49)
        # this is expected for ALL layers
        expected_tripped_latch = [True, True, True, False, False, False, False, False]
        time.sleep(0.2)
        self._test_tripped_latch(expected_tripped_latch)

        # clears all interlocks
        self.pu_ctrl.disable_all_interlocks()
        self.pu_ctrl.reset_tripped_latch()

        if TestcaseBase.test_config.powerunit_ext1:
            # Testing ext1 temperature interlock - other interlocks are disabled
            self.pu._set_interlock_vector(interlock=[TempInterlockEnable.INTERNAL_PT100,TempInterlockEnable.EXTERNAL1_PT100])
            self.pu_ctrl.enable_temperature_interlock(ext1_temperature_limit=50,
                                              ext1_temperature_low_limit=0,
                                              suppress_warnings=True)
            self.pu_ctrl._set_temperature_limit(0, int_limit)
            expected_tripped_latch = [False, False, False, False, False, False, False, False]
            time.sleep(0.2)
            self._test_tripped_latch(expected_tripped_latch)
            self.pu_ctrl._set_temperature_limit(1, ext1_limit)
            expected_tripped_latch = [True, True, False, True, False, False, False, False]
            if self.rdo.identity.is_ml():
                expected_tripped_latch = [True, False, False, True, False, False, False, False]
            time.sleep(0.2)
            self._test_tripped_latch(expected_tripped_latch)
            # clears all interlocks
            self.pu._set_interlock_vector(interlock=[TempInterlockEnable.INTERNAL_PT100])
            self.pu_ctrl.disable_all_interlocks()
            self.pu_ctrl.reset_tripped_latch()
        if TestcaseBase.test_config.powerunit_ext2:
            # Testing ext2 temperature interlock - other interlocks are disabled
            self.pu._set_interlock_vector(interlock=[TempInterlockEnable.INTERNAL_PT100,TempInterlockEnable.EXTERNAL2_PT100])
            self.pu_ctrl.enable_temperature_interlock(ext2_temperature_limit=50,
                                              ext2_temperature_low_limit=0,
                                              suppress_warnings=True)
            self.pu_ctrl._set_temperature_limit(0, int_limit)
            expected_tripped_latch = [False, False, False, False, False, False, False, False]
            time.sleep(0.2)
            self._test_tripped_latch(expected_tripped_latch)
            self.pu_ctrl._set_temperature_limit(2, ext2_limit)
            expected_tripped_latch = [False, True, False, False, True, False, False, False]
            time.sleep(0.2)
            self._test_tripped_latch(expected_tripped_latch)
            # clears all interlocks
            self.pu._set_interlock_vector(interlock=[TempInterlockEnable.INTERNAL_PT100])
            self.pu_ctrl.disable_all_interlocks()
            self.pu_ctrl.reset_tripped_latch()


    def test_pu_mask_interlock(self):
        expected_tripped_latch = [False, False, False, False, False, False, False, False]
        self._test_tripped_latch(expected_tripped_latch)
        self.pu_ctrl.enable_power_bias_interlock(0xFF, 0xFF)
        time.sleep(0.1)
        expected_tripped_latch = [True, True, False, False, False, True, False, False]
        self._test_tripped_latch(expected_tripped_latch)

    def test_pu_power_grouping_interlock_noBIAS(self):
        """
        Test trip conditions without mask

        Expected behaviour:
        Power_enable[1:0]   /= power_enable_mask[0] --> report tripped 1:4, disable power[1:0]
        Power_enable[3:2]   /= power_enable_mask[1] --> report tripped 1:4, disable power[3:2]
        Power_enable[5:4]   /= power_enable_mask[3] --> report tripped 1:4, disable power[5:4]
        Power_enable[7:6]   /= power_enable_mask[4] --> report tripped 1:4, disable power[7:6]
        Power_enable[9:8]   /= power_enable_mask[5] --> report tripped 5:8, disable power[9:8]
        Power_enable[11:10] /= power_enable_mask[6] --> report tripped 5:8, disable power[11:10]
        Power_enable[13:12] /= power_enable_mask[7] --> report tripped 5:8, disable power[13:12]
        Power_enable[15:14] /= power_enable_mask[8] --> report tripped 5:8, disable power[15:14]"""

        self._enable_power_all_modules()

        for ch in range(16): #Select which to trip
            self.pu.enable_power_with_mask(mask=0xFFFF)
            self.logger.info(f"Testing {self._get_ch_indicator(ch)}")
            time.sleep(0.5)

            #power mask all on - bias mask OFF
            self.pu_ctrl.enable_power_bias_interlock(0xFF, 0x00)
            time.sleep(0.5)
            assert self.pu_ctrl.did_interlock_fire() == False, "Interlock fired! This should not fire now!"

            self._turn_off_one_ch_all_else_on(ch)
            if ch < 8:
                expected_tripped_latch = [True, False, False, False, False, True, False, False]
            else:
                expected_tripped_latch = [False, True, False, False, False, True, False, False]
            self._test_tripped_latch(expected_tripped_latch)
            power_enable_status_pu = self.pu.get_power_enable_status()
            expected_power_enable_status = self._get_expected_power_enable_after_nobias_trip(ch)

            assert power_enable_status_pu == expected_power_enable_status, f"{self._get_ch_indicator(ch)} should be powered down. Actual power_enable_status is: {hex(power_enable_status_pu)}"
            self.pu_ctrl.disable_all_interlocks()
            self.pu_ctrl.reset_tripped_latch()

    def test_pu_power_grouping_interlock_BIAS(self):
        """
        Test trip conditions without mask

        Expected behaviour:
        IB/ML/OL: Power_enable[3:0]   /= power_enable_mask[1:0] | bias_enable[0] /= bias_mask[0]
                  --> report tripped 1:4, disable power [3:0], disable bias[0]
        ML:       Power_enable[7:4]   /= power_enable_mask[3:2] | bias_enable[1] /= bias_mask[1]
                  --> report tripped 1:4, disable power [7:4], disable bias[1]
        ML:       Power_enable[11:8]  /= power_enable_mask[5:4] | bias_enable[2] /= bias_mask[2]
                  --> report tripped 5:8, disable power [11:8], disable bias[2]
        ML:       Power_enable[15:12] /= power_enable_mask[7:6] | bias_enable[3] /= bias_mask[3]
                  --> report tripped 5:8, disable power [15:12], disable bias[3]
        IB/OL:    Power_enable[9:4]   /= power_enable_mask[4:2] | bias_enable[1] /= bias_mask[1]
                  --> report tripped 1:4/5:8, disable power [9:4], disable bias[1]
        IB/OL:    Power_enable[13:10] /= power_enable_mask[6:5] | bias_enable[2] /= bias_mask[2]
                  --> report tripped 5:8, disable power [13:10], disable bias[2]
        """

        self._enable_power_all_modules()

        for ch in range(20): #Select which to trip 0:15 - POWER, 16 - 19 BIAS
            self.pu.enable_power_with_mask(mask=0xFFFF)
            self.pu.enable_bias_all()
            time.sleep(0.5)

            if ch < 16:
                self.logger.info(f"Testing {self._get_ch_indicator(ch)}")
            else:
                self.logger.info(f"Testing BIAS module: {ch-15}")

            # power mask all on - bias mask OFF
            self.pu_ctrl.enable_power_bias_interlock(0xFF, 0xFF)
            time.sleep(0.5)
            if self.pu_ctrl.did_interlock_fire():
                self.logger.error(f"Interlock fired:")
                self.logger.error(f"tripped_power_enables {self.pu_ctrl.get_tripped_power_enables}")
                self.logger.error(f"tripped_bias_enables {self.pu_ctrl.get_tripped_bias_enables}")
            assert self.pu_ctrl.did_interlock_fire() is False, "Interlock fired! This should not fire now!"
            if ch < 16:
                self._turn_off_one_ch_all_else_on(ch)
            else:
                self._turn_off_one_bias_ch_all_else_on(ch-16)

            power_enable_status = self.pu.get_power_enable_status()
            bias_enable_status = self.pu.get_bias_enable_status()
            # test for ML
            if self.rdo.identity.is_ml():
                if ch < 4:
                    expected_tripped_latch = [True, False, False, False, False, True, False, False]
                    expected_power_enable_status = 0xFFF0
                    expected_bias_enable_status  = 0xFE
                elif ch < 8:
                    expected_tripped_latch = [True, False, False, False, False, True, False, False]
                    expected_power_enable_status = 0xFF0F
                    expected_bias_enable_status  = 0xFD
                elif ch < 12:
                    expected_tripped_latch = [False, True, False, False, False, True, False, False]
                    expected_power_enable_status = 0xF0FF
                    expected_bias_enable_status  = 0xFB
                elif ch < 16:
                    expected_tripped_latch = [False, True, False, False, False, True, False, False]
                    expected_power_enable_status = 0x0FFF
                    expected_bias_enable_status  = 0xF7
                elif ch == 16:
                    expected_tripped_latch = [True, False, False, False, False, True, False, False]
                    expected_power_enable_status = 0xFFF0
                    expected_bias_enable_status  = 0xFE
                elif ch == 17:
                    expected_tripped_latch = [True, False, False, False, False, True, False, False]
                    expected_power_enable_status = 0xFF0F
                    expected_bias_enable_status  = 0xFD
                elif ch == 18:
                    expected_tripped_latch = [False, True, False, False, False, True, False, False]
                    expected_power_enable_status = 0xF0FF
                    expected_bias_enable_status  = 0xFB
                elif ch == 19:
                    expected_tripped_latch = [False, True, False, False, False, True, False, False]
                    expected_power_enable_status = 0x0FFF
                    expected_bias_enable_status  = 0xF7
                self._test_tripped_latch(expected_tripped_latch)
                assert power_enable_status == expected_power_enable_status, f"ML: {self._get_ch_indicator(ch)} should be powered down. Actual power_enable_status is: hex(power_enable_status)"
                assert bias_enable_status == expected_bias_enable_status, f"ML: {self._get_ch_indicator(ch)} should be powered down. Actual bias_enable_status is: hex(bias_enable_status)"
            else: #IB and OL have the same behaviour
                if ch < 4:
                    expected_tripped_latch = [True, False, False, False, False, True, False, False]
                    expected_power_enable_status = 0xFFF0
                    expected_bias_enable_status  = 0xFE
                elif ch < 10:
                    expected_tripped_latch = [True, True, False, False, False, True, False, False]
                    expected_power_enable_status = 0xFC0F
                    expected_bias_enable_status  = 0xFD
                elif ch < 14:
                    expected_tripped_latch = [False, True, False, False, False, True, False, False]
                    expected_power_enable_status = 0xC3FF
                    expected_bias_enable_status  = 0xFB
                elif ch == 14:
                    expected_tripped_latch = [False, False, False, False, False, False, False, False]
                    expected_power_enable_status = 0xBFFF
                    expected_bias_enable_status  = 0xFF
                elif ch == 15:
                    expected_tripped_latch = [False, False, False, False, False, False, False, False]
                    expected_power_enable_status = 0x7FFF
                    expected_bias_enable_status  = 0xFF
                elif ch == 16: #bias bit 0
                    expected_tripped_latch = [True, False, False, False, False, True, False, False]
                    expected_power_enable_status = 0xFFF0
                    expected_bias_enable_status  = 0xFE
                elif ch == 17: #bias bit 1
                    expected_tripped_latch = [True, True, False, False, False, True, False, False]
                    expected_power_enable_status = 0xFC0F
                    expected_bias_enable_status  = 0xFD
                elif ch == 18: #bias bit 2
                    expected_tripped_latch = [False, True, False, False, False, True, False, False]
                    expected_power_enable_status = 0xC3FF
                    expected_bias_enable_status  = 0xFB
                else:
                    expected_tripped_latch = [False, False, False, False, False, False, False, False]
                    expected_power_enable_status = 0xFFFF
                    expected_bias_enable_status  = 0xF7

                self._test_tripped_latch(expected_tripped_latch)
                assert power_enable_status == expected_power_enable_status, f"IB/OL: {self._get_ch_indicator(ch)} should be powered down. Actual power_enable_status is: hex(power_enable_status)"
                assert bias_enable_status == expected_bias_enable_status, f"IB/OL: {self._get_ch_indicator(ch)} should be powered down. Actual bias_enable_status is: hex(bias_enable_status)"

            self.pu_ctrl.disable_all_interlocks()
            self.pu_ctrl.reset_tripped_latch()

    def test_pu_power_interlock_threshold(self):
        """
        Verifies that lowering current threshold below active current will fire interlock.
        """
        self._enable_power_all_modules()

        self.pu_ctrl.enable_power_bias_interlock(0xFF, 0x00)
        time.sleep(0.2)
        assert self.pu_ctrl.did_interlock_fire() == False, "Interlock fired! This should not fire now!"
        if self.rdo.identity.is_ib():
             expected_tripped_latch = [True, False, False, False, False, True, False, False]
             expected_tripped       = [True, True, False, False, False, True, False, False]
        elif self.rdo.identity.is_ml():
             expected_tripped_latch = [True, False, False, False, False, True, False, False]
             expected_tripped       = [True, True, False, False, False, True, False, False]
        elif self.rdo.identity.is_ol():
             expected_tripped_latch = [True, False, False, False, False, True, False, False]
             expected_tripped       = [True, True, False, False, False, True, False, False]

        # time.sleep(0.2)
        self.pu.lower_current_thresholds_to_min()
        time.sleep(0.2)
        self._test_tripped_latch(expected_tripped_latch)
        self._test_tripped(expected_tripped)
        tripped_power_enables = self.pu_ctrl.get_tripped_power_enables()
        power_enable_status = self.pu_ctrl.get_power_enable_status()
        power_enable_status_pu = self.pu.get_power_enable_status()
        assert tripped_power_enables != 0, "Tripped POWER enable WAS " + str(hex(tripped_power_enables)) + ". It should have a positive value after the trip."
        assert power_enable_status == 0, "Power enable (controller) WAS " + str(hex(power_enable_status)) + ". It should be 0x0000 after the trip"
        assert power_enable_status_pu == 0, "Power enable (busctlaux) WAS " + str(hex(power_enable_status_pu)) + ". It should be 0x0000 after the trip"

    def test_pu_clock_interlock(self):
        """
        Verifies that disabling the clock will provoke clock interlock if voltage is above max_adc
        """
        # power on stave with interlocks enabled and high temperature settings to avoid temp interlocks
        # this enables dclk and everything
        self._enable_power_all_modules()

        self.pu_ctrl.enable_power_bias_interlock(0xFF, 0x00)
        #self.power_on_ib_stave(avdd=2.0, dvdd=2.0, internal_temperature_limit=50, compensate_v_drop=False, external_temperature_limit=50, external_temperature_low_limit=None)
        time.sleep(0.5)
        expected_tripped_latch = [False, False, False, False, False, False, False, False]
        self._test_tripped_latch(expected_tripped_latch)
        # With the MAX ADC value set to 2.0V it should not cause an interlock
        self.rdo.alpide_control.disable_dclk()
        time.sleep(0.5)
        expected_tripped_latch = [False, False, False, False, False, False, False, False]
        self._test_tripped_latch(expected_tripped_latch)
        #Enables clock again and verifies if a trip happens with a lower MAX_ADC value
        self.rdo.alpide_control.enable_dclk()
        #read voltage value... - set max_adc to this value -
        self.pu.controller.set_clock_interlock_threshold(1.0)
        self.rdo.alpide_control.disable_dclk([4,3,2,1,0])
        time.sleep(0.5)
        if not self.rdo.identity.is_ml():
            expected_tripped_latch = [True, True, False, False, False, False, True, True]
        else: # MLS will trip the modules of the first clock that was turned off, but all will be powered off
            expected_tripped_latch = [False, True, False, False, False, False, False, True]
        self._test_tripped_latch(expected_tripped_latch)
        assert  self.pu.controller.get_power_enable_status() == 0

    def test_pu_clock_interlock_mls_mod5_8(self):
        """
        Verifies that disabling the clock for mod5_8 will provoke clock interlock only for mod5_8
        """
        if not self.rdo.identity.is_ml():
            self.skipTest("RU is not ML...")
        # power on stave with interlocks enabled and high temperature settings to avoid temp interlocks
        # this enables dclk and everything
        self._enable_power_all_modules()

        self.pu_ctrl.enable_power_bias_interlock(0xFF, 0x00)
        #self.power_on_ib_stave(avdd=2.0, dvdd=2.0, internal_temperature_limit=50, compensate_v_drop=False, external_temperature_limit=50, external_temperature_low_limit=None)
        time.sleep(0.5)
        expected_tripped_latch = [False, False, False, False, False, False, False, False]
        self._test_tripped_latch(expected_tripped_latch)
        # With the MAX ADC value set to 2.0V it should not cause an interlock
        self.rdo.alpide_control.disable_dclk()
        time.sleep(0.5)
        expected_tripped_latch = [False, False, False, False, False, False, False, False]
        self._test_tripped_latch(expected_tripped_latch)
        #Enables clock again and verifies if a trip happens with a lower MAX_ADC value
        self.rdo.alpide_control.enable_dclk()
        #read voltage value... - set max_adc to this value -
        self.pu.controller.set_clock_interlock_threshold(1.0)
        self.rdo.alpide_control.disable_dclk([2,3])
        time.sleep(0.5)
        expected_tripped_latch = [False, True, False, False, False, False, False, True]
        self._test_tripped_latch(expected_tripped_latch)
        assert  self.pu.controller.get_power_enable_status() == 0x00FF

    def test_pu_clock_interlock_mls_mod1_4(self):
        """
        Verifies that disabling the clock for mod1_4 will provoke clock interlock only for mod1_4
        """
        if not self.rdo.identity.is_ml():
            self.skipTest("RU is not ML...")
        # power on stave with interlocks enabled and high temperature settings to avoid temp interlocks
        # this enables dclk and everything
        self._enable_power_all_modules()

        self.pu_ctrl.enable_power_bias_interlock(0xFF, 0x00)
        #self.power_on_ib_stave(avdd=2.0, dvdd=2.0, internal_temperature_limit=50, compensate_v_drop=False, external_temperature_limit=50, external_temperature_low_limit=None)
        time.sleep(0.5)
        expected_tripped_latch = [False, False, False, False, False, False, False, False]
        self._test_tripped_latch(expected_tripped_latch)
        # With the MAX ADC value set to 2.0V it should not cause an interlock
        self.rdo.alpide_control.disable_dclk()
        time.sleep(0.5)
        expected_tripped_latch = [False, False, False, False, False, False, False, False]
        self._test_tripped_latch(expected_tripped_latch)
        #Enables clock again and verifies if a trip happens with a lower MAX_ADC value
        self.rdo.alpide_control.enable_dclk()
        #read voltage value... - set max_adc to this value -
        self.pu.controller.set_clock_interlock_threshold(1.0)
        self.rdo.alpide_control.disable_dclk([0,1])
        time.sleep(0.5)
        expected_tripped_latch = [True, False, False, False, False, False, True, False]
        self._test_tripped_latch(expected_tripped_latch)
        assert  self.pu.controller.get_power_enable_status() == 0xFF00

    def test_pu_clock_interlock_ols_ctrl1(self):
        """
        Verifies that disabling the clock for pu_ctrl1 will provoke clock interlock for pu_ctrl1
        """
        if not self.rdo.identity.is_ol():
            self.skipTest("RU is not OL...")
        # power on stave with interlocks enabled and high temperature settings to avoid temp interlocks
        # this enables dclk and everything
        self._enable_power_all_modules()

        self.pu_ctrl.enable_power_bias_interlock(0xFF, 0x00)
        #self.power_on_ib_stave(avdd=2.0, dvdd=2.0, internal_temperature_limit=50, compensate_v_drop=False, external_temperature_limit=50, external_temperature_low_limit=None)
        time.sleep(0.5)
        expected_tripped_latch = [False, False, False, False, False, False, False, False]
        self._test_tripped_latch(expected_tripped_latch)
        # With the MAX ADC value set to 2.0V it should not cause an interlock
        self.rdo.alpide_control.disable_dclk()
        time.sleep(0.5)
        expected_tripped_latch = [False, False, False, False, False, False, False, False]
        self._test_tripped_latch(expected_tripped_latch)
        #Enables clock again and verifies if a trip happens with a lower MAX_ADC value
        self.rdo.alpide_control.enable_dclk()
        #read voltage value... - set max_adc to this value -
        self.pu.controller.set_clock_interlock_threshold(1.0)
        #Disable clock for modules of second ctrl, should not provoke any interlock
        self.rdo.alpide_control.disable_dclk([0,1])
        time.sleep(0.5)
        expected_tripped_latch = [True, True, False, False, False, False, True, True]
        self._test_tripped_latch(expected_tripped_latch)
        assert  self.pu.controller.get_power_enable_status() == 0x0

    def test_pu_clock_interlock_ols_ctrl2(self):
        """
        Verifies that disabling the clock for pu_ctrl2 will NOT provoke clock interlock for pu_ctrl1
        """
        if not self.rdo.identity.is_ol():
            self.skipTest("RU is not OL...")
        # power on stave with interlocks enabled and high temperature settings to avoid temp interlocks
        # this enables dclk and everything
        self._enable_power_all_modules()

        self.pu_ctrl.enable_power_bias_interlock(0xFF, 0x00)
        #self.power_on_ib_stave(avdd=2.0, dvdd=2.0, internal_temperature_limit=50, compensate_v_drop=False, external_temperature_limit=50, external_temperature_low_limit=None)
        time.sleep(0.5)
        expected_tripped_latch = [False, False, False, False, False, False, False, False]
        self._test_tripped_latch(expected_tripped_latch)
        # With the MAX ADC value set to 2.0V it should not cause an interlock
        self.rdo.alpide_control.disable_dclk()
        time.sleep(0.5)
        expected_tripped_latch = [False, False, False, False, False, False, False, False]
        self._test_tripped_latch(expected_tripped_latch)
        #Enables clock again and verifies if a trip happens with a lower MAX_ADC value
        self.rdo.alpide_control.enable_dclk()
        #read voltage value... - set max_adc to this value -
        self.pu.controller.set_clock_interlock_threshold(1.0)
        #Disable clock for modules of second ctrl, should not provoke any interlock
        self.rdo.alpide_control.disable_dclk([2,3])
        time.sleep(0.5)
        expected_tripped_latch = [False, False, False, False, False, False, False, False]
        self._test_tripped_latch(expected_tripped_latch)
        assert  self.pu.controller.get_power_enable_status() == 0xFFFF


class D_TestcaseStavePowerOn(TestcaseDry):

    def setUp(self):
        if not TestcaseBase.is_pb_connected() and not TestcaseBase.do_ignore_checks():
            self.skipTest("PB is not connected, no reason to continue tests...")
        super().setUp()

    def test_power_on(self):
        if self.subrack in ['IB-test','IB-table']:
            self.tb.power_on_ib_stave(internal_temperature_limit=40, external_temperature_limit=40)
            self.tb.log_values_ib_stave()
        elif self.subrack == 'ML-test':
            self.tb.power_on_ml_stave(internal_temperature_limit=40, external_temperature_limit=40)
            self.tb.log_values_ml_stave()
        elif self.subrack == 'OL-test':
            self.tb.power_on_ol_stave(internal_temperature_limit=40, external_temperature_limit=40)
            self.tb.log_values_ob_stave()
        elif self.subrack == "ORNL":
            self.tb.power_on_ib_stave_ORNL()
            self.tb.log_values_ib_stave()
        elif self.subrack == "LANL":
            self.tb.power_on_all_ib_staves_LANL()
            self.tb.log_values_ib_staves()
        else:
            raise NotImplementedError
        TestcaseWet.set_stave_power_status(True)


class E_TestCaseChips(TestcaseWet):

    def setUp(self):
        super().setUp()

    def test_chips_no_manchester(self):
        if self.subrack in ['IB-test','IB-table', 'ORNL', 'LANL']:
            self._test_chips_ib(disable_manchester=True, nrtests=TestcaseBase.test_config.dctrl_tests_ib)
        elif self.subrack == 'ML-test':
            self._test_chips_ml(disable_manchester=True, nrtests=TestcaseBase.test_config.dctrl_tests_mls)
        elif self.subrack == 'OL-test':
            self._test_chips_ol(disable_manchester=True, nrtests=TestcaseBase.test_config.dctrl_tests_ols)
        else:
            raise NotImplementedError

    def test_chips_manchester(self):
        if self.subrack in ['IB-test','IB-table', 'ORNL', 'LANL']:
            self._test_chips_ib(disable_manchester=False, nrtests=TestcaseBase.test_config.dctrl_tests_ib)
        elif self.subrack == 'ML-test':
            self._test_chips_ml(disable_manchester=False, nrtests=TestcaseBase.test_config.dctrl_tests_mls)
        elif self.subrack == 'OL-test':
            self._test_chips_ol(disable_manchester=False, nrtests=TestcaseBase.test_config.dctrl_tests_ols)
        else:
            raise NotImplementedError

    def test_issue_203_no_manchester(self):
        if self.subrack in ['IB-test','IB-table', 'ORNL', 'LANL']:
            self._test_issue_203_ib(disable_manchester=True)
        elif self.subrack == 'ML-test':
            self._test_issue_203_ml(disable_manchester=True)
        elif self.subrack == 'OL-test':
            self._test_issue_203_ol(disable_manchester=True)
        else:
            raise NotImplementedError

    def test_issue_203_manchester(self):
        if self.subrack in ['IB-test','IB-table', 'ORNL', 'LANL']:
            self._test_issue_203_ib(disable_manchester=False)
        elif self.subrack == 'ML-test':
            self._test_issue_203_ml(disable_manchester=False)
        elif self.subrack == 'OL-test':
            self._test_issue_203_ol(disable_manchester=False)
        else:
            raise NotImplementedError

    def _test_chips_ib(self, disable_manchester, nrtests):
        """Tests chips with/without manchester encoding.
        It assumes that the chips are properly powered before starting the test"""
        self.tb.setup_sensors(disable_manchester=disable_manchester, rdo=self.rdo)
        # now do v-drop compensation twice with a small pause in between
        self.tb.compensate_voltage_drop_ib_stave(dvdd_set=1.8, avdd_set=1.8, rdo=self.rdo)
        time.sleep(0.5)
        self.tb.compensate_voltage_drop_ib_stave(dvdd_set=1.8, avdd_set=1.8, rdo=self.rdo)
        time.sleep(0.5)
        expected = {chip.chipid:0 for chip in self.tb.chips}
        # avoid wasting time (fails early)
        errors_dict, _ = self.tb.test_chips(nrtests=1, is_on_ob=False, rdo=self.rdo)
        self._assert_equal_dict_excluded_keys(expected, errors_dict, TestcaseBase.test_config.ib_broken_chips)
        errors_dict, _ = self.tb.test_chips(nrtests=nrtests, is_on_ob=False, rdo=self.rdo)
        self._assert_equal_dict_excluded_keys(expected, errors_dict, TestcaseBase.test_config.ib_broken_chips)

    def _test_chips_ml(self, disable_manchester, nrtests):
        """Tests chips with/without manchester encoding.
        It assumes that the chips are properly powered before starting the test"""
        self.tb.setup_sensors(disable_manchester=disable_manchester, rdo=self.rdo)
        expected = {chipid:0 for chipid in self.tb.chips_ml.keys()}
        # avoid wasting time (fails early)
        errors_dict = self.tb.test_chips_ml_stave(nrtests=1, rdo=self.rdo)
        self._assert_equal_dict_excluded_keys(expected, errors_dict, TestcaseBase.test_config.ml_broken_chips)
        errors_dict = self.tb.test_chips_ml_stave(nrtests=nrtests, rdo=self.rdo)
        self._assert_equal_dict_excluded_keys(expected, errors_dict, TestcaseBase.test_config.ml_broken_chips)

    def _test_chips_ol(self, disable_manchester, nrtests):
        """Tests chips with/without manchester encoding.
        It assumes that the chips are properly powered before starting the test"""
        self.tb.setup_sensors(disable_manchester=disable_manchester, rdo=self.rdo)
        expected = {chipid:0 for chipid in self.tb.chips_ob.keys()}
        # avoid wasting time (fails early)
        errors_dict = self.tb.test_chips_ob_stave(nrtests=1, rdo=self.rdo)
        self._assert_equal_dict_excluded_keys(expected, errors_dict, TestcaseBase.test_config.ol_broken_chips)
        errors_dict = self.tb.test_chips_ob_stave(nrtests=nrtests, rdo=self.rdo)
        self._assert_equal_dict_excluded_keys(expected, errors_dict, TestcaseBase.test_config.ol_broken_chips)

    def _test_issue_203_ib(self, disable_manchester, nrtests=10):
        """Tests against the Issue 203
        It assumes that the chips are properly powered before starting the test"""
        self.tb.setup_sensors(disable_manchester=disable_manchester, rdo=self.rdo)
        # now do v-drop compensation twice with a small pause in between
        self.tb.compensate_voltage_drop_ib_stave(dvdd_set=1.8, avdd_set=1.8, rdo=self.rdo)
        time.sleep(0.5)
        self.tb.compensate_voltage_drop_ib_stave(dvdd_set=1.8, avdd_set=1.8, rdo=self.rdo)
        time.sleep(0.5)
        ch_broadcast = self.tb.stave_chip_broadcast(gbt_ch=self.gbt_channel)
        ch_broadcast.clear_cmuerrors(commitTransaction=True)
        expected = {chip.chipid:0 for chip in self.tb.chips}
        # Reads some registers to have counter for CMU and DMU errors
        errors_dict, _ = self.tb.test_chips(nrtests=nrtests, is_on_ob=False, rdo=self.rdo)
        self._assert_equal_dict_excluded_keys(expected, errors_dict, TestcaseBase.test_config.ib_broken_chips)
        # Runs the real test
        errors_dict = self.tb.test_cmu_dmu_errors(is_on_ob=False, rdo=self.rdo)
        self._assert_equal_dict_excluded_keys(expected, errors_dict, TestcaseBase.test_config.ib_broken_chips)

    def _test_issue_203_ml(self, disable_manchester, nrtests=2):
        """Tests against the Issue 203
        It assumes that the chips are properly powered before starting the test"""
        self.tb.setup_sensors(disable_manchester=disable_manchester, rdo=self.rdo)
        ch_broadcast = self.tb.stave_chip_broadcast(gbt_ch=self.gbt_channel)
        ch_broadcast.clear_cmuerrors(commitTransaction=True)
        expected = {chipid:0 for chipid in self.tb.chips_ml.keys()}
        # avoid wasting time (fails early)
        errors_dict = self.tb.test_chips_ml_stave(nrtests=nrtests, rdo=self.rdo)
        self._assert_equal_dict_excluded_keys(expected, errors_dict, TestcaseBase.test_config.ml_broken_chips)
        errors_dict = self.tb.test_cmu_dmu_errors_ml_stave(rdo=self.rdo)
        self._assert_equal_dict_excluded_keys(expected, errors_dict, TestcaseBase.test_config.ml_broken_chips)

    def _test_issue_203_ol(self, disable_manchester, nrtests=2):
        """Tests against the Issue 203
        It assumes that the chips are properly powered before starting the test"""
        self.tb.setup_sensors(disable_manchester=disable_manchester, rdo=self.rdo)
        ch_broadcast = self.tb.stave_chip_broadcast(gbt_ch=self.gbt_channel)
        ch_broadcast.clear_cmuerrors(commitTransaction=True)
        expected = {chipid:0 for chipid in self.tb.chips_ob.keys()}
        # avoid wasting time (fails early)
        errors_dict = self.tb.test_chips_ob_stave(nrtests=nrtests, rdo=self.rdo)
        self._assert_equal_dict_excluded_keys(expected, errors_dict, TestcaseBase.test_config.ol_broken_chips)
        errors_dict = self.tb.test_cmu_dmu_errors_ob_stave(rdo=self.rdo)
        self._assert_equal_dict_excluded_keys(expected, errors_dict, TestcaseBase.test_config.ol_broken_chips)

class EA_TestswithPowerOn(TestcaseWet):

    def setUp(self):
        super().setUp()

    def test_radmon_issue_515(self):
        self.assertTrue(self.tb.test_radmon_issue_515(), "RADMON issue is not solved")

class E_XTestPowerOffBeforeDaq(TestcaseWet):

    def setUp(self):
        super().setUp()

    def test_power_off(self):
        if self.subrack in ['IB-test', 'IB-table', 'ORNL', 'LANL']:
            self.tb.power_off_all_ib_staves(True)
            self.tb.log_values_ib_staves()
        elif self.subrack == 'ML-test':
            self.tb.power_off_ml_stave(True)
            self.tb.log_values_ml_stave()
        elif self.subrack == 'OL-test':
            self.tb.power_off_ob_stave(True)
            self.tb.log_values_ob_stave()
        else:
            raise NotImplementedError

class F_DaqTest(TestcaseWet):

    def setUp(self):
        super().setUp()
        if self.subrack in ['IB-test','IB-table', 'ORNL', 'LANL']:
            self.readout_output = TestcaseBase.test_config.ibs_readout_output

            if self._testMethodName == 'test_daqtest_0_regular':
                self.config_file = TestcaseBase.test_config.ibs_daqtest_config_file
                self.check_config_file(self.config_file)

            elif self._testMethodName == 'test_daqtest_1_excl0':
                self.config_file = TestcaseBase.test_config.ibs_daqtest_excl0_config_file
                self.check_config_file(self.config_file)

            elif self._testMethodName == 'test_daqtest_2_excl2':
                self.config_file = TestcaseBase.test_config.ibs_daqtest_excl2_config_file
                self.check_config_file(self.config_file)
            elif self._testMethodName == 'test_daqtest_mvtx':
                self.config_file = TestcaseBase.test_config.mvtx_daqtest_config_file
                self.check_config_file(self.config_file)

            else:
                raise NotImplementedError
        elif self.subrack == 'ML-test':
            self.readout_output = TestcaseBase.test_config.mls_readout_output
            self.config_file = TestcaseBase.test_config.mls_daqtest_config_file
            self.check_config_file(self.config_file)

        elif self.subrack == 'OL-test':
            self.readout_output = TestcaseBase.test_config.ols_readout_output
            self.config_file = TestcaseBase.test_config.ols_daqtest_config_file
            self.check_config_file(self.config_file)

        else:
            self.skipTest(f"Skipping: subrack {self.subrack} not implemented")

        if self.subrack in ['IB-test','IB-table']:
            self.tb.power_on_ib_stave(internal_temperature_limit=40, external_temperature_limit=40)
            self.tb.log_values_ib_stave()
        elif self.subrack == 'ML-test':
            self.tb.power_on_ml_stave(internal_temperature_limit=40, external_temperature_limit=40)
            self.tb.log_values_ml_stave()
        elif self.subrack == 'OL-test':
            self.tb.power_on_ol_stave(internal_temperature_limit=40, external_temperature_limit=40)
            self.tb.log_values_ob_stave()
        elif self.subrack == "ORNL":
            self.tb.power_on_ib_stave_ORNL()
            self.tb.log_values_ib_stave()
        elif self.subrack == "LANL":
            self.tb.power_on_all_ib_staves_LANL()
            self.tb.log_values_ib_staves()
        else:
            raise NotImplementedError

    def tearDown(self):
        if self.subrack in ['IB-test', 'IB-table', 'ORNL', 'LANL']:
            self.tb.power_off_all_ib_staves(True)
            self.tb.log_values_ib_staves()
        elif self.subrack == 'ML-test':
            self.tb.power_off_ml_stave(True)
            self.tb.log_values_ml_stave()
        elif self.subrack == 'OL-test':
            self.tb.power_off_ob_stave(True)
            self.tb.log_values_ob_stave()
        else:
            raise NotImplementedError

    def check_config_file(self, config_file):
        if self.config_file.endswith('None'):
            self.skipTest('No config file given, skipping')
        else:
            if not os.path.isfile(self.config_file):
                self.fail(f"Config file {self.config_file} not existing")

    def test_daqtest_0_regular(self):
        self._test_data()

        self.assertTrue(os.path.isfile(self.readout_output), "READOUT OUTPUT NOT FOUND")
        self.assertFalse(os.system('cp ' + self.readout_output + f' ~/tmp_data/daqtest_{self.get_subrack_shorthand()}.lz4'), "Failed to copy readout output!")
        final_counter_path = os.path.join(os.getcwd(), 'logs', 'final_counters.json')
        self.assertFalse(os.system('cp ' + final_counter_path + f' ~/tmp_data/daqtest_{self.get_subrack_shorthand()}_final_counters.json'), "Failed to copy final counters!")

    def test_daqtest_mvtx(self):
        self._test_data()

        # TODO: no datafile outputs for MVTX, yet
        tmp_dir = os.path.expanduser("~/tmp_data")
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)
        final_counter_path = os.path.join(os.getcwd(), 'logs', 'final_counters.json')
        self.assertFalse(os.system('cp ' + final_counter_path + f' ~/tmp_data/daqtest_{self.get_subrack_shorthand()}_final_counters.json'), "Failed to copy final counters!")

    def test_daqtest_1_excl0(self):
        if self.subrack not in ['IB-test','IB-table']:
            self.skipTest('Not implemented for MLS and OLS or MVTX')

        self._test_data()

        self.assertTrue(os.path.isfile(self.readout_output), "READOUT OUTPUT NOT FOUND")
        self.assertFalse(os.system('cp ' + self.readout_output + ' ~/tmp_data/daqtest_ibs_excl_0.lz4'), "Failed to copy readout output!")
        final_counter_path = os.path.join(os.getcwd(), 'logs', 'final_counters.json')
        self.assertFalse(os.system('cp ' + final_counter_path + f' ~/tmp_data/daqtest_ibs_excl0_final_counters.json'), "Failed to copy final counters!")

    def test_daqtest_2_excl2(self):
        if self.subrack not in ['IB-test','IB-table']:
            self.skipTest('Not implemented for MLS and OLS or MVTX')

        self._test_data()

        self.assertTrue(os.path.isfile(self.readout_output), "READOUT OUTPUT NOT FOUND")
        self.assertFalse(os.system('cp ' + self.readout_output + ' ~/tmp_data/daqtest_ibs_excl_2.lz4'), "Failed to copy readout output!")
        final_counter_path = os.path.join(os.getcwd(), 'logs', 'final_counters.json')
        self.assertFalse(os.system('cp ' + final_counter_path + f' ~/tmp_data/daqtest_ibs_excl2_final_counters.json'), "Failed to copy final counters!")

    def _test_data(self):
        self.tb.initialize_all_gbtx12()
        d_test = daq_test.DaqTest()
        d_test.setup_logging(main=False)
        d_test.configure_run(self.config_file)
        d_test.initialize_testbench()

        d_test.logger.info("Start new Run")

        d_test.testbench.setup_cru()

        if d_test.config.USE_LTU:
            d_test.testbench.setup_ltu()

        d_test.setup_comms()

        d_test.logger.debug(f"Initialised comms {d_test.testbench.comm_rdo_list}")
        try:
            d_test.testbench.initialize_boards()
            if d_test.config.USE_LTU:
                assert d_test.testbench.ltu.is_ltu_on(), "LTU communication failed"
            try:
                d_test.testbench.setup_rdos(connector_nr=d_test.config.MAIN_CONNECTOR)
                d_test.logger.debug(f"Started rdos {d_test.testbench.rdo_list}")
                d_test.testbench.initialize_all_rdos()
                for rdo in d_test.testbench.rdo_list:
                    if d_test.config.PA3_READ_VALUES or d_test.config.PA3_SCRUBBING_ENABLE:
                        rdo.pa3.initialize()
                        rdo.pa3.config_controller.clear_scrubbing_counter()
                    if d_test.config.PA3_SCRUBBING_ENABLE:
                        rdo.pa3.config_controller.start_blind_scrubbing()
                        d_test.logger.info(f"Running blind scrubbing on RDO {rdo.get_gbt_channel()}")
                d_test.test_routine()

            except Exception as e:
                raise e
            finally:
                d_test.logger.info("Tearing down")
                d_test.tearDown()
        except Exception as e:
            d_test.test_pass = False
            d_test.logger.info("Exception in Run")
            d_test.logger.info(e,exc_info=True)
        finally:
            d_test.testbench.stop()
            d_test.stop()

        d_test.logger.info("Run finished.")
        self.assertTrue(d_test.test_pass, "DAQ test did not pass, check logs!!")


class G_ThresholdTest(TestcaseWet):

    def setUp(self):
        super().setUp()
        self.tb.initialize_all_gbtx12()

        if self.subrack in ['IB-test','IB-table', 'ORNL', 'LANL']:
            self.config_file = TestcaseBase.test_config.threshold_ibs_config_file
            self.check_config_file(self.config_file)
            self.readout_output = TestcaseBase.test_config.ibs_readout_output
        elif self.subrack == 'ML-test':
            self.config_file = TestcaseBase.test_config.threshold_mls_config_file
            self.check_config_file(self.config_file)
            self.readout_output = TestcaseBase.test_config.mls_readout_output
        elif self.subrack == 'OL-test':
            self.config_file = TestcaseBase.test_config.threshold_ols_config_file
            self.check_config_file(self.config_file)
            self.readout_output = TestcaseBase.test_config.ols_readout_output
        else:
            raise NotImplementedError
        if self.subrack in ['IB-test','IB-table']:
            self.tb.power_on_ib_stave(internal_temperature_limit=40, external_temperature_limit=40)
            self.tb.log_values_ib_stave()
        elif self.subrack == 'ML-test':
            self.tb.power_on_ml_stave(internal_temperature_limit=40, external_temperature_limit=40)
            self.tb.log_values_ml_stave()
        elif self.subrack == 'OL-test':
            self.tb.power_on_ol_stave(internal_temperature_limit=40, external_temperature_limit=40)
            self.tb.log_values_ob_stave()
        elif self.subrack == "ORNL":
            self.tb.power_on_ib_stave_ORNL()
            self.tb.log_values_ib_stave()
        elif self.subrack == "LANL":
            self.tb.power_on_all_ib_staves_LANL()
            self.tb.log_values_ib_staves()
        else:
            raise NotImplementedError

    def check_config_file(self, config_file):
        if self.config_file.endswith('None'):
            self.skipTest('No config file given, skipping')
        else:
            if not os.path.isfile(self.config_file):
                self.fail(f"Config file {self.config_file} not existing")

    def test_threshold(self):

        self._test_data()

        # TODO: no datafile output for MVTX tests, yet
        if self.subrack not in ['ORNL', 'LANL']:
            self.assertTrue(os.path.isfile(self.readout_output), "READOUT OUTPUT NOT FOUND")
            self.assertFalse(os.system('cp ' + self.readout_output + f' ~/tmp_data/threshold_{self.get_subrack_shorthand()}.lz4'), "Failed to copy readout output!")
        final_counter_path = os.path.join(os.getcwd(), 'logs', 'final_counters.json')
        self.assertFalse(os.system('cp ' + final_counter_path + f' ~/tmp_data/threshold_{self.get_subrack_shorthand()}_final_counters.json'), "Failed to copy final counters!")

    def _test_data(self):
        ts = threshold_scan.ThresholdScan()
        ts.setup_logging(main=False)
        ts.configure_run(self.config_file)
        ts.initialize_testbench()

        ts.logger.info("Start new Run")

        ts.testbench.setup_cru()

        if ts.config.USE_LTU:
            ts.testbench.setup_ltu()

        ts.setup_comms()

        ts.logger.debug(f"Initialised comms {ts.testbench.comm_rdo_list}")
        try:
            ts.testbench.initialize_boards()
            if ts.config.USE_LTU:
                assert ts.testbench.ltu.is_ltu_on(), "LTU communication failed"
            try:
                ts.testbench.setup_rdos(connector_nr=ts.config.MAIN_CONNECTOR)
                ts.logger.debug(f"Started rdos {ts.testbench.rdo_list}")
                ts.testbench.initialize_all_rdos()
                for rdo in ts.testbench.rdo_list:
                    if ts.config.PA3_READ_VALUES or ts.config.PA3_SCRUBBING_ENABLE:
                        rdo.pa3.initialize()
                        rdo.pa3.config_controller.clear_scrubbing_counter()
                    if ts.config.PA3_SCRUBBING_ENABLE:
                        rdo.pa3.config_controller.start_blind_scrubbing()
                        ts.logger.info(f"Running blind scrubbing on RDO {rdo.get_gbt_channel()}")
                ts.test_routine()

            except Exception as e:
                raise e
            finally:
                ts.logger.info("Tearing down")
                ts.tearDown()
        except Exception as e:
            ts.test_pass = False
            ts.logger.error("Exception in Run")
            ts.logger.error(e,exc_info=True)
        finally:
            ts.testbench.stop()
            ts.stop()

        ts.logger.info("Run finished.")
        self.assertTrue(ts.test_pass, "Threshold scan did not pass, check logs!!")


class H_TestCase_Post_DAQ(TestcaseWet):

    def test_radmon(self):
        self.assertTrue(self.rdo.radmon.is_xcku_without_seus())


def setup_logger():
    """Sets up the logger"""
    logger_int = logging.getLogger()
    logger_int.setLevel(logging.INFO)

    log_folder = os.path.join(os.getcwd(), "logs")
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)

    log_file = log_folder+"/deployment.log"
    log_file_errors = log_folder+"/deployment_error.log"

    fh = logging.FileHandler(log_file)
    fh2 = logging.FileHandler(log_file_errors)
    ch = logging.StreamHandler()

    fh.setLevel(logging.DEBUG)
    fh2.setLevel(logging.ERROR)
    ch.setLevel(logging.WARNING)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    formatter_ch = logging.Formatter(
        "%(name)s - %(levelname)s - %(message)s")

    fh.setFormatter(formatter)
    fh2.setFormatter(formatter)
    ch.setFormatter(formatter_ch)

    logger_int.addHandler(fh)
    logger_int.addHandler(fh2)
    logger_int.addHandler(ch)

    return logger_int


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config_file", required=True, help="Configuration file relative path")
    parser.add_argument("-b", "--bitfile", required=False, help="Bitfile relative path")
    args, unittest_args = parser.parse_known_args()
    unit_argv = [sys.argv[0]] + unittest_args

    config_file = args.config_file
    bitfile = args.bitfile
    logger = setup_logger()
    # logger = logging.getLogger()

    TestcaseBase.test_config = TestConfig(config_file, bitfile)
    try:
        for setup in TestcaseBase.test_config.tb_dict:
            logger.info(f"CRU Initialize({setup})")
            TestcaseBase.test_config.tb_dict[setup].initialize_boards()
    except Exception as e:
        logger.error("Test crashed before starting, logging")
        logger.error(e, exc_info=True)
        os._exit(1)
    except:
        logger.error("Test crashed, traceback not logged")
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        os._exit(1)


    exit_code = 0
    try:
        logger.info("Start Test")
        unittest.main(verbosity=2, exit=True, warnings='ignore', argv=unit_argv)
    except KeyboardInterrupt as ki:
        logger.error("Test interrupted with KeyboardInterrupt")
        logger.info(ki, exc_info=True)
        os._exit(1)
    except SystemExit as sys_exit:
        exit_code = sys_exit.code
    except Exception as e:
        logger.error("Test crashed, logging")
        logger.error(e, exc_info=True)
        os._exit(1)
    except:
        logger.error("Test crashed, traceback not logged")
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        os._exit(1)

    logger.info("Done")
    if exit_code:
        os._exit(1)
