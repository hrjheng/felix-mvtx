#!/usr/bin/env python3.9

"""Test for verifying the functionality of the RUs/PBs in a FELIX"""

import argparse
import logging
import os
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
from pALPIDE import ModeControlIbSerialLinkSpeed


# Safety
ALLOW_STAVE_TESTING=False # if False, prevents checking of staves
STAVE_ATTACHED=True # if True, prevents check of power unit channels

# Globals
global tb_global
global ru_parameter_dict_global
tb_global = None
ru_parameter_dict_global = {}


class TestcaseBase(unittest.TestCase):
    gbt_channel = None
    rdo_githash = None
    pa3_githash = None

    def setUp(self, ctrl=True):
        self.tb = tb_global
        # objects
        assert tb_global is not None, "Testbench must be present"
        if ctrl: # RU tests
            if self.gbt_channel not in self.tb.ctrl_link_list:
                self.skipTest(f"gbt_channel {self.gbt_channel} not in {self.tb.ctrl_link_list}")
        else: # GBT uplinks
            if self.gbt_channel not in self.tb.data_link_list:
                self.skipTest(f"gbt_channel {self.gbt_channel} not in {self.tb.data_link_list}")

        # values assignment
        self.set_parameters()
        self.set_objects()

    def set_parameters(self):
        pass

    def set_objects(self):
        self.cru = self.tb.cru

    def _assert_equal_hex(self, expected, read, info_string=""):
        self.assertEqual(expected, read, f"{info_string} Got 0x{read:08X} expected 0x{expected:08X}")


class RdoBaseTest:
    class TestRuOnChannel(TestcaseBase):

        def configure_test(self, gbt_channel):
            self.gbt_channel = gbt_channel

        @classmethod
        def setUpClass(cls):
            pass

        @classmethod
        def tearDownClass(cls):
            pass

        def setUp(self):
            super().setUp()
            assert self.gbt_channel is not None
            self.cru.initialize()

        def tearDown(self):
            super().tearDown()
            self.rdo.trigger_handler.set_opcode_gating(0)
            self.cru.send_eot()

        def set_parameters(self):
            self.layer, self.ru_sn, self.stave, self.rdo_githash, self.pa3_githash= ru_parameter_dict_global[self.gbt_channel]

        def set_objects(self):
            super().set_objects()
            self.logger = logging.getLogger(f'L{self.layer}_{self.stave}')
            self.test_pu1 = test_pu1
            if self.layer in range(5):
                self.test_pu2 = False
            else:
                self.test_pu2 = test_pu2
            self.test_trg = test_trg
            self.test_stv = test_stv
            self.rdo = self.tb.rdos(self.gbt_channel)
            self.pa3 = self.tb.pa3s(self.gbt_channel)
            self.sca = self.tb.scas(self.gbt_channel)
            # TODO load this from a config file
            self.nr_pu_rw = 256
            self.ib_broken_chips = {}
            self.dctrl_tests_ib = 1000

        def test_AA_initialize_rdo(self):
            """Initialises the RDO"""
            cp_set = self.rdo.GBTx0_CHARGEPUMP_DEFAULT
            cp = self.rdo.gbtx0_swt.get_phase_detector_charge_pump()
            if cp != cp_set:
                self.logger.warning(f"Initial value of GBTx0 chargepump current is {cp}!={cp_set}")
            self.rdo.initialize()
            time.sleep(0.2)
            self.cru.initialize()
            self.assertEqual(self.rdo.gbtx0_swt.get_phase_detector_charge_pump(), cp_set,
                             f"GBTx0 chargepump current expected {cp_set} got {self.rdo.gbtx0_swt.get_phase_detector_charge_pump()}")

        def test_rdo_githash(self):
            """Checks that the XCKU have the correct githash"""
            self._assert_equal_hex(expected=self.rdo_githash, read=self.rdo.git_hash(), info_string="XCKU githash")

        def test_feeid(self):
            """Checks the fee id of the board"""
            self.rdo.identity.is_fee_id_correct(layer=self.layer, stave=self.stave)

        def test_sn(self):
            """Checks the serial number of the board"""
            self.assertIsNot(self.ru_sn, None)
            dna_rdo = self.rdo.identity.get_dna()
            sn = self.rdo.identity.decode_sn(dna_rdo)
            print(f"Board SN: {sn}, config: {self.ru_sn}")
            self.assertIsNot(sn, None)
            self.assertEqual(sn, self.ru_sn, "SN not matching expected value")

        def test_pa3_githash(self):
            """Checks that the PA3 has the correct githash"""
            self.sca.initialize()
            self.pa3.initialize(verbose=False)
            self._assert_equal_hex(expected=self.pa3_githash, read=self.pa3.githash(), info_string="PA3 githash")

        def test_send_triggers(self, triggers=50):
            """Check if the RU are receiving the correct number of triggers"""
            if not self.test_trg:
                self.skipTest('Skipping trigger tests')
            raise NotImplementedError

        def test_initialize_gbtx12(self):
            """Check if the RUs GBTx 1 and 2 can be initialized"""
            initialised = self.rdo.initialize_gbtx12(verbose=False, check=True, readback=True)
            if not initialised:
                self.logger.info('GBTx configuration FAILED via XCKU')
                initialised = self.rdo.initialize_gbtx12(verbose=False, check=True, readback=True)
            self.assertTrue(initialised, "gbtx12 not initialised correctly")

        def test_read_rdo_temperature(self, limit=40):
            """Checks the RU temperature to be lower than the limit"""
            temperature = self.rdo.sysmon.get_temperature()
            self.assertLess(temperature, limit, f"Temperature over limit {temperature}/{limit}")

        def _select_powerunit(self, index):
            if index == 1:
                pu = self.rdo.powerunit_1
                if not self.test_pu1:
                    self.skipTest('Skipping PU1 tests')
            elif index == 2:
                pu = self.rdo.powerunit_2
                if not self.test_pu2:
                    self.skipTest('Skipping PU2 tests')
            else:
                raise ValueError(f"Powerunit index {index} not in [1,2]")
            return pu

        def _test_powerunit_writeread(self, index):
            """Tests the powerunit read and access"""
            pu = self._select_powerunit(index)
            pu.initialize()
            pu.controller.set_clock_interlock_threshold(2.0)
            pu.setup_power_modules(dvdd=1.72, dvdd_current=1.5,
                                   avdd=1.72, avdd_current=1.5,
                                   bb=-1.0,
                                   module_list=[0,1,2,3,4,5,6,7],
                                   check_interlock=False,
                                   no_offset=False,
                                   verbose=False)
            for i in range(3): #sets up temperature sensors to read sensible values
                pu.initialize_temperature_sensor(i)
            pu.controller.disable_all_interlocks()
            pu.reset_all_counters()
            pu.controller.reset_tripped_latch()
            time.sleep(1)
            for i in range(self.nr_pu_rw):
                mask = i % 255
                i_pwr = mask << 8
                pu.enable_bias_with_mask(mask)
                pu.enable_power_with_mask(i_pwr)
                time.sleep(0.05)
                assert pu.get_bias_enable_status() == mask, "test_power_unit: bias_enable should be " + str(mask)
                assert pu.get_power_enable_status() == i_pwr, "test_power_unit: power_enable should be " + str(i_pwr)
            pu.controller.set_temperature_interlock_enable_mask(1)

        def test_powerunit_1_writeread(self):
            self._test_powerunit_writeread(index=1)

        def test_powerunit_2_writeread(self):
            self._test_powerunit_writeread(index=2)

        def _test_powerunit_temperatures(self, index, temperature_limit=35):
            """Tests the powerunit read and access"""
            pu = self._select_powerunit(index)
            pu.initialize()
            pu.power_off_all()
            pu.reset_all_counters()
            cntrs = pu.main_monitor.read_counters()
            for name in ['arbitration_lost_error_count','noack_error_count']:
                self.assertEqual(cntrs[name], 0, f"Errors in {name}")
            # check for temperatures
            temperatures = pu.controller.read_all_temperatures()
            for name, t in temperatures.items():
                if t < pu.minimum_temperature_pt100_disconnected:
                    self.assertLess(t, temperature_limit, f"Temperature {name} over threshold {t}/{temperature_limit}")

        def test_powerunit_1_temperatures(self):
            self._test_powerunit_temperatures(index=1)

        def test_powerunit_2_temperatures(self):
            self._test_powerunit_temperatures(index=2)

        def _test_powerunit_channels(self, index, vbb=0.0):
            """Tests the powerunit read and access"""
            if (not self.test_pu1 and (index == 1)) or (not self.test_pu2 and (index == 2)):
                self.skipTest(f'Powerunit {index} was not selected for testing')
            if STAVE_ATTACHED:
                self.skipTest('Too dangerous to run with stave attached!')
            assert -5.0 <= vbb <= 0.0
            backbias_en = vbb != 0.0
            pu = self._select_powerunit(index)
            pu.initialize()
            pu.power_off_all(disable_power_interlock=True)

            for module in range(8):
                pu.setup_power_module(module=module, dvdd=1.8, avdd=1.8, bb=vbb, check_interlock=False)
                pu.power_on_module(module=module, backbias_en=backbias_en, check_interlock=False)
                time.sleep(0.1)
                power_enable_status = pu.get_power_enable_status()
                mask = 0x3 << (2*module)
                self.assertEqual(power_enable_status, mask, f"power_enable_status 0x{power_enable_status:04X} not matching expected value 0x{mask:04X} for module {module}")
                bias_enable_status = pu.get_bias_enable_status()
                if backbias_en:
                    mask = (0x1 << module)
                else:
                    mask = 0
                self.assertEqual(bias_enable_status, mask, f"bias_enable_status 0x{bias_enable_status:02X} not matching expected value 0x{mask:02X}")
                pu.power_off_all()

        def test_powerunit_1_channels(self):
            self._test_powerunit_channels(index=1, vbb=0)

        def test_powerunit_1_channels_bb(self):
            self._test_powerunit_channels(index=1, vbb=-3)

        @unittest.skip("Powerunit 2 not used in MVTX")
        def test_powerunit_2_channels(self):
            self._test_powerunit_channels(index=2, vbb=0)

        @unittest.skip("Powerunit 2 not used in MVTX")
        def test_powerunit_2_channels_bb(self):
            self._test_powerunit_channels(index=2, vbb=-3)

        def _test_rx_optical_power(self, channel, low_limit, low_warning_limit, high_limit):
            i = self.sca.read_adc_converted(channel)
            self.logger.info(f"{channel.name}: Optical Current: {i} uA")
            self.assertGreater(i, low_limit, f"Current way too low {i} [uA]")
            self.assertLess(i, high_limit, f"Current way too high {i} [uA]")
            # test last to indicate a WARNING in the report at the end
            self.assertGreater(i, low_warning_limit, f"WARNING: Current too low: {i} [uA], contact WP10 expert for fiber cleaning")

        def test_rx_optical_from_flx_vtrx1(self):
            self._test_rx_optical_power(self.sca.adc_channels.I_VTRx1, 100.0, 200.0, 700.0)

        def test_rx_optical_from_flx_vtrx2(self):
            self._test_rx_optical_power(self.sca.adc_channels.I_VTRx2, 100.0, 200.0, 700.0)

        def _assert_equal_dict_excluded_keys(self, expected, read, excluded_keys):
            for key in read.keys():
                if key not in excluded_keys:
                    self.assertEqual(expected[key], read[key], f"Readback errors for chipid 0x{key:02x}")

        def _test_chips_ib(self, disable_manchester, nrtests):
            """Tests chips with/without manchester encoding.
            It assumes that the chips are properly powered before starting the test"""
            tb_global.setup_sensors(disable_manchester=disable_manchester, LinkSpeed=ModeControlIbSerialLinkSpeed.MBPS600, rdo=self.rdo)
            # now do v-drop compensation twice with a small pause in between
            tb_global.compensate_voltage_drop_ib_stave(dvdd_set=1.8, avdd_set=1.8, rdo=self.rdo)
            time.sleep(0.5)
            tb_global.compensate_voltage_drop_ib_stave(dvdd_set=1.8, avdd_set=1.8, rdo=self.rdo)
            time.sleep(0.5)
            expected = {chip.chipid:0 for chip in tb_global.chips}
            # avoid wasting time (fails early)
            errors_dict, _ = tb_global.test_chips(nrtests=1, is_on_ob=False, rdo=self.rdo)
            self._assert_equal_dict_excluded_keys(expected, errors_dict, self.ib_broken_chips)
            errors_dict, _ = tb_global.test_chips(nrtests=nrtests, is_on_ob=False, rdo=self.rdo)
            self._assert_equal_dict_excluded_keys(expected, errors_dict, self.ib_broken_chips)

        def test_zz0_poweron_stave(self):
            """Power On stave"""
            if not self.test_stv or not self.test_pu1:
                self.skipTest('Skipping Stave tests')
            tb_global.power_on_ib_stave(internal_temperature_limit=40,
                                        link_speed=600,
                                        check_interlock=True,
                                        rdo=self.rdo)
            tb_global.log_values_ib_stave(rdo=self.rdo)

        def test_zz1_chips_no_manchester(self):
            if not self.test_stv or not self.test_pu1:
                self.skipTest('Skipping Stave tests')
            self._test_chips_ib(disable_manchester=True, nrtests=self.dctrl_tests_ib)

        def test_zz2_chips_manchester(self):
            if not self.test_stv or not self.test_pu1:
                self.skipTest('Skipping Stave tests')
            self._test_chips_ib(disable_manchester=False, nrtests=self.dctrl_tests_ib)

        def test_zz9_poweroff_stave(self):
            if not self.test_stv or not self.test_pu1:
                self.skipTest('Skipping Stave tests')
            tb_global.power_off_ib_stave(disable_power_interlock=True, rdo=self.rdo)


class TestRuOnChannel00(RdoBaseTest.TestRuOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=0)
        super().setUp()

class TestRuOnChannel03(RdoBaseTest.TestRuOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=3)
        super().setUp()

class TestRuOnChannel06(RdoBaseTest.TestRuOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=6)
        super().setUp()

class TestRuOnChannel09(RdoBaseTest.TestRuOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=9)
        super().setUp()

class TestRuOnChannel12(RdoBaseTest.TestRuOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=12)
        super().setUp()

class TestRuOnChannel15(RdoBaseTest.TestRuOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=15)
        super().setUp()

class TestRuOnChannel18(RdoBaseTest.TestRuOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=18)
        super().setUp()

class TestRuOnChannel21(RdoBaseTest.TestRuOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=21)
        super().setUp()


class GbtChannelBaseTest:
    class TestGbtOnChannel(TestcaseBase):

        def configure_test(self, gbt_channel):
            self.gbt_channel = gbt_channel

        def setUp(self):
            super().setUp(ctrl=False)
            assert self.gbt_channel is not None

        def set_objects(self):
            super().set_objects()
            self.logger = logging.getLogger(f'CRU_gbt_channel{self.gbt_channel}')


class TestGbtOnChannel0(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=0)
        super().setUp()
class TestGbtOnChannel1(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=1)
        super().setUp()
class TestGbtOnChannel2(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=2)
        super().setUp()
class TestGbtOnChannel3(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=3)
        super().setUp()
class TestGbtOnChannel4(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=4)
        super().setUp()
class TestGbtOnChannel5(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=5)
        super().setUp()
class TestGbtOnChannel6(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=6)
        super().setUp()
class TestGbtOnChannel7(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=7)
        super().setUp()
class TestGbtOnChannel8(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=8)
        super().setUp()
class TestGbtOnChannel9(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=9)
        super().setUp()
class TestGbtOnChannel10(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=10)
        super().setUp()
class TestGbtOnChannel11(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=11)
        super().setUp()
class TestGbtOnChannel12(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=12)
        super().setUp()
class TestGbtOnChannel13(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=13)
        super().setUp()
class TestGbtOnChannel14(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=14)
        super().setUp()
class TestGbtOnChannel15(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=15)
        super().setUp()
class TestGbtOnChannel16(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=16)
        super().setUp()
class TestGbtOnChannel17(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=17)
        super().setUp()
class TestGbtOnChannel18(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=18)
        super().setUp()
class TestGbtOnChannel19(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=19)
        super().setUp()
class TestGbtOnChannel20(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=20)
        super().setUp()
class TestGbtOnChannel21(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=21)
        super().setUp()
class TestGbtOnChannel22(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=22)
        super().setUp()
class TestGbtOnChannel23(GbtChannelBaseTest.TestGbtOnChannel):
    def setUp(self):
        self.configure_test(gbt_channel=23)
        super().setUp()


@unittest.skip("Dummytest for exit code verification")
class TestExitHandling(TestcaseBase):
    def setUp(self):
        super().setUp()

    def test_0_access(self):
        _, githash_ref = self.tb.rdo.read(1,1)

    def test_1_pass(self):
        self.assertEqual(0,0,"Failure not expected here")

    @unittest.skip("Failure disabled")
    def test_2_fail(self):
        self.assertEqual(0,1,"Failure provoked")


def setup_logger(subrack):
    """Sets up the logger"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    log_folder = "logs"
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)

    log_file = log_folder+f"/subrack_verify_{subrack.replace('/','-')}.log"
    log_file_errors = log_folder+f"/subrack_verify_{subrack.replace('/','-')}_error.log"

    fh = logging.FileHandler(log_file)
    fh2 = logging.FileHandler(log_file_errors)
    ch = logging.StreamHandler()

    fh.setLevel(logging.DEBUG)
    fh2.setLevel(logging.ERROR)
    ch.setLevel(logging.WARNING)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    fh.setFormatter(formatter)
    fh2.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(fh2)
    logger.addHandler(ch)
    return logger


def setup_subrack(subrack):
    assert subrack in crate_mapping.subrack_lut.keys(), f"{subrack} not in {list(crate_mapping.subrack_lut.keys())}"
    return crate_mapping.subrack_lut[subrack]


def check_subrack(parameter_list):
    for flp, cru_id, layer, gbt_ch, ru_sn, stave, rdo_githash, pa3_githash in parameter_list:
        assert os.uname().nodename == flp, f"wrong flp selected for running the test; nodename {os.uname().nodename} flp {flp}"
        assert tb_global.cru_sn == cru_id, "wrong cru_id selected for running the test"
        assert layer in range(7)
        assert gbt_ch in range(24)
        assert stave in range(48)
        assert rdo_githash in range(0xFFFFFFFF+1)
        assert pa3_githash in range(0xFFFFFFFF+1)
    return {gbt_ch: (layer, ru_sn, stave, rdo_githash, pa3_githash) for _,_,layer,gbt_ch,ru_sn,stave,rdo_githash, pa3_githash in parameter_list}


def main(config_file,
         unit_argv):
    """Main method parsing the input parameters"""
    global tb_global
    tb_global = testbench.configure_testbench(config_file_path=config_file,
                                              run_standalone=True)
    subrack = tb_global.subrack
    parameter_list = setup_subrack(subrack)
    print(parameter_list)
    logger = setup_logger(subrack=subrack)
    logger.info(f"Logging parsed valued\nsubrack {subrack}\nconfig_file {config_file}")
    global ru_parameter_dict_global
    ru_parameter_dict_global = check_subrack(parameter_list)
    print(ru_parameter_dict_global)

    try:
        tb_global.cru.initialize()
    except Exception as e:
        logger.error("Test crashed before starting, logging")
        logger.error(e, exc_info=True)
        os._exit(1)
    except:
        logger.error("Test crashed, traceback not logged")
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        os._exit(1)

    try:
        logger.info("Start Test")
        unittest.main(verbosity=2, exit=True, argv=unit_argv)
    except KeyboardInterrupt as ki:
        logger.error("Test interrupted with KeyboardInterrupt")
        logger.info(ki, exc_info=True)
        os._exit(1)
    except SystemExit:
        pass
    except Exception as e:
        logger.error("Test crashed, logging")
        logger.error(e, exc_info=True)
        os._exit(1)
    except:
        logger.error("Test crashed, traceback not logged")
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        os._exit(1)

    logger.info(f"Done testing on {subrack}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config_file", required=True, help="Configuration file relative path")
    parser.add_argument("-pu1", "--test_powerunit_1", required=False, help="Flag to enable the run with powerunit_1", action='store_true')
    parser.add_argument("-pu2", "--test_powerunit_2", required=False, help="Flag to enable the run with powerunit_2", action='store_true')
    parser.add_argument("-trg", "--test_trigger", required=False, help="Flag to mark if to run with trigger", action='store_true')
    parser.add_argument("-stv", "--test_stave", required=False, help="Flag to mark if to run with stave", action='store_true')
    options, unittest_args = parser.parse_known_args()
    unit_argv = [sys.argv[0]] + unittest_args;

    config_file = options.config_file
    test_pu1 = options.test_powerunit_1
    test_pu2 = options.test_powerunit_2
    test_trg = options.test_trigger
    test_stv = options.test_stave

    main(config_file=config_file,
         unit_argv=unit_argv)
