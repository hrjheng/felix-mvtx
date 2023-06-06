#!/usr/bin/env python3.9
"""Test for verifying the functionality of the RUs after assembly"""

from itertools import starmap

import argparse
import logging
import os
import sys
import subprocess
import time
import traceback
import unittest

script_path = os.path.dirname(os.path.realpath(__file__))
modules_path = os.path.join(
    script_path, '../../../modules/board_support_software/software/py/')
sys.path.append(modules_path)
from module_includes import *

sys.path.append(os.path.join(script_path, '../.'))

import gbt_sca
import hameg
import proasic3
import testbench


# Globals
global tb_global
global logger_global
global hameg_global
global serial_number
global channel
tb_global = None
logger_global = None
hameg_global = None
serial_number = None
channel = None

if os.path.exists('/home/mvtx/RU_bitfiles/'):
    pa3_bitfile = '/home/mvtx/RU_bitfiles/RU_auxFPGA/RU_auxFPGA_v020A_211027_0910_c95fa5d.pdb'
    ru_wb2fifo_bitfile = '/home/mvtx/RU_bitfiles/RU_mainFPGA/pre_release/XCKU_top_211129_1447_d4a86112.bit'
    ru_golden_bitfile = '/home/mvtx/RU_bitfiles/RU_mainFPGA/pre_release/XCKU_top_211129_1447_d4a86112.bit'
else:
    pa3_bitfile = '../../../RU_auxFPGA/RU_auxFPGA_v020A_211027_0910_c95fa5d.pdb'
    ru_wb2fifo_bitfile = '../../../XCKU_top_211129_1447_d4a86112.bit'
    ru_golden_bitfile = '../../../XCKU_top_211129_1447_d4a86112.bit'

rdo_golden_githash = 0xD4A86112
rdo_wb2fifo_githash = 0xD4A86112
pa3_githash = 0xC95FA5D


class TestcaseBase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.set_objects()
        cls.tb.initialize_boards()

    @classmethod
    def set_objects(cls):
        cls.logger = logger_global

        cls.tb = tb_global
        cls.cru = cls.tb.cru
        cls.rdo = cls.tb.rdo
        cls.pa3 = cls.tb.rdo.pa3
        cls.sca = cls.tb.rdo.sca

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        assert self.tb is not None
        assert self.cru is not None
        assert self.rdo is not None
        assert self.pa3 is not None
        assert self.sca is not None

    def _assert_equal_hex(self, expected, read):
        self.assertEqual(expected, read, f"Got 0x{read:08X} expected 0x{expected:08X}")


class Test2Xcku(TestcaseBase):  # int is to force order of execution

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rdo.initialize()

    def test_sn(self):
        """Checks the serial number of the board"""
        self.assertIsNot(serial_number, None)
        dna_rdo = self.rdo.identity.get_dna()
        sn = self.rdo.identity.decode_sn(dna_rdo)
        self.assertIsNot(sn, None, f"DNA {dna_rdo} for SN{serial_number} not found in database")
        self.assertEqual(sn, serial_number, f"SN{sn} not matching expected value {serial_number}")

    def test_read_temperature(self, limit=50):
        """Checks the RU temperature to be lower than the limit"""
        temperature = self.rdo.sysmon.get_temperature()
        self.logger.info(f"Sysmon temperature\t{temperature:.3f} C")
        self.assertLess(temperature, limit, f"Temperature over limit {temperature}/{limit}")

    def test_sysmon_access(self):
        """Checks the XCKU sysmon values and logs them to compare to the SCA values"""
        print("")
        self.rdo.sysmon.log_voltages()

    def test_initialize_gbtx12(self):
        """Initialises all gbtx12 using the XCKU"""
        success = self.rdo.initialize_gbtx12(verbose=False, check=True, readback=True)
        self.assertTrue(success,'GBTx configuration FAILED via XCKU after second retry')

    def test_timebase_sync(self):
        """Checks that timebase is synced after GBTx2 initialization"""
        self.assertTrue(self.rdo.trigger_handler.is_timebase_synced(), "Timebase must be synced!")

    def test_timebase_sync_counter(self):
        self.rdo.trigger_handler.reset_counters()
        time.sleep(5)
        self.assertLessEqual(self.rdo.trigger_handler.read_counters()['LOL_TIMEBASE'], 0, "LOL counters should not increment")

    def test_dipswitch(self):
        """Checks that the dipswitch is set correctly"""
        self.assertEqual(1, self.rdo.identity.get_dipswitch(), "Dipswitches not set correctly")


class Test4XckuFlashing(TestcaseBase): # int is to force order of execution
    def test_access_selectMap(self):
        self.cru.pa3.initialize()
        selMapIdCode = self.cru.pa3._SelMap.get_idcode()
        self.assertEqual(0x13919093, selMapIdCode)

    def test_flash(self):
        self.pa3.initialize()
        if not self.pa3.config_controller.is_init_config_done(): # XCKU was not programmed on boot
            self.tb.flash_all_rdo_bitfiles(filename=os.path.join(script_path, ru_golden_bitfile),
                                             bitfile_block=None, # Selects existing positions or 0x100/0x200
                                             scrubfile_block=None,
                                             use_ultrascale_fifo=True)
            success = self.tb.rdo.program_xcku()
            self.assertTrue(success, "Flash failed to program, init config not done or program not done")
            self.tb.initialize_boards()
            success = self.tb.rdo.program_xcku(chip_num=2)
            self.assertTrue(success, "Flash failed to program, init config not done or program not done")
            self.tb.initialize_boards()
        else: # Was programmed on boot, reflash and program again and check
            self.tb.flash_all_rdo_bitfiles(filename=os.path.join(script_path, ru_golden_bitfile),
                                             bitfile_block=None, # Selects existing positions or 0x100/0x200
                                             scrubfile_block=None,
                                             use_ultrascale_fifo=True)
            success = self.tb.rdo.program_xcku()
            self.assertTrue(success, "Flash failed to program, init config not done or program not done")
            self.tb.initialize_boards()
            success = self.tb.rdo.program_xcku(chip_num=2)
            self.assertTrue(success, "Flash failed to program, init config not done or program not done")
            self.tb.initialize_boards()
        self.assertEqual(self.tb.rdo.git_hash(), rdo_golden_githash, "Bitfile loaded is not correct")

    def test_flash_gold(self):
        success = self.tb.rdo.program_xcku(use_gold=True)
        self.tb.initialize_boards()
        if success:
            if self.tb.rdo.git_hash() == rdo_golden_githash:
                self.tb.rdo.program_xcku(use_gold=False)
                return # Goldfile good and same as main
        else:
            self.tb.program_all_xcku()
        self.tb.flash_all_rdo_goldfiles(filename=os.path.join(script_path, ru_golden_bitfile),
                                 goldfile_block=None, # Selects existing positions or 0x300/0x400
                                 use_ultrascale_fifo=True)
        success = self.tb.rdo.program_xcku(use_gold=True)
        self.tb.initialize_boards()
        self.assertTrue(success, "Flash failed to program goldfile, init config not done or program not done")
        self.assertEqual(self.tb.rdo.git_hash(), rdo_golden_githash, "Bitfile loaded is not correct")
        success = self.tb.rdo.program_xcku(use_gold=True, chip_num=2)
        self.tb.initialize_boards()
        self.assertTrue(success, "Flash failed to program goldfile, init config not done or program not done")
        self.assertEqual(self.tb.rdo.git_hash(), rdo_golden_githash, "Bitfile loaded is not correct")


class Test1Sca(TestcaseBase):  # int is to force order of execution


    def test_1_initialize_gbtx12(self): # Force the gbtx initialize to run before the ADC test so the currents are consistent
        """Initialises all gbtx12 using the SCA"""
        success = self.rdo.initialize_gbtx12(verbose=False, check=True, readback=True, use_xcku=False)
        self.assertTrue(success,'GBTx configuration FAILED via XCKU after second retry')

    def _test_adc_threshold(self, adc, threshold_low, threshold_high):
        value = self.sca.read_adc_converted(adc)
        uom = self.sca.get_adc_unit_of_measurement(adc)
        self.logger.info(f"ADC {adc.name:<10}\t{value:.3f} {uom}")
        if value < threshold_low:
            self.logger.error(f"ADC below {threshold_low}")
        self.assertGreater(value, threshold_low, "ADC below limit")
        if value > threshold_high:
            self.logger.error(f"ADC above {threshold_high}")
        self.assertLess(value, threshold_high, "ADC above limit")

    def test_adc_i_int(self):
        self._test_adc_threshold(adc=self.sca.adc_channels.I_INT,threshold_low=0.60,threshold_high=2.3)
    def test_adc_i_mgt(self):
        self._test_adc_threshold(adc=self.sca.adc_channels.I_MGT,threshold_low=0.5,threshold_high=1.0)

    def test_adc_i_1v2(self):
        self._test_adc_threshold(adc=self.sca.adc_channels.I_1V2,threshold_low=0.4,threshold_high=0.56)

    def test_adc_i_1v5(self):
        self._test_adc_threshold(adc=self.sca.adc_channels.I_1V5,threshold_low=1.3,threshold_high=2.3)

    def test_adc_i_1v8(self):
        self._test_adc_threshold(adc=self.sca.adc_channels.I_1V8,threshold_low=0.67,threshold_high=1.00)

    def test_adc_i_2v5(self):
        self._test_adc_threshold(adc=self.sca.adc_channels.I_2V5,threshold_low=0.67,threshold_high=0.76)

    def test_adc_i_3v3(self):
        self._test_adc_threshold(adc=self.sca.adc_channels.I_3V3,threshold_low=0.37,threshold_high=0.55)

    def test_adc_i_in(self):
        self._test_adc_threshold(adc=self.sca.adc_channels.I_IN,threshold_low=1.0,threshold_high=3.2)

    def test_adc_i_vtrx1(self):
        self._test_adc_threshold(adc=self.sca.adc_channels.I_VTRx1,threshold_low=150,threshold_high=370)
    def test_adc_i_vtrx2(self):
        self._test_adc_threshold(adc=self.sca.adc_channels.I_VTRx2,threshold_low=150,threshold_high=370)

    def test_adc_v_int(self):
        self._test_adc_threshold(adc=self.sca.adc_channels.V_INT,threshold_low=0.945,threshold_high=0.96)
    def test_adc_v_mgt(self):
        self._test_adc_threshold(adc=self.sca.adc_channels.V_MGT,threshold_low=0.98,threshold_high=1.02)

    def test_adc_v_1v2(self):
        self._test_adc_threshold(adc=self.sca.adc_channels.V_1V2,threshold_low=1.18,threshold_high=1.22)

    def test_adc_v_1v5(self):
        self._test_adc_threshold(adc=self.sca.adc_channels.V_1V5,threshold_low=1.48,threshold_high=1.54)

    def test_adc_v_1v8(self):
        self._test_adc_threshold(adc=self.sca.adc_channels.V_1V8,threshold_low=1.78,threshold_high=1.82)

    def test_adc_v_2v5(self):
        self._test_adc_threshold(adc=self.sca.adc_channels.V_2V5,threshold_low=2.46,threshold_high=2.54)

    def test_adc_v_3v3(self):
        self._test_adc_threshold(adc=self.sca.adc_channels.V_3V3,threshold_low=3.27,threshold_high=3.33)

    def test_adc_v_in(self):
        self._test_adc_threshold(adc=self.sca.adc_channels.V_IN,threshold_low=6.2,threshold_high=8.0)

    def test_adc_t_1(self):
        self._test_adc_threshold(adc=self.sca.adc_channels.T_1,threshold_low=15.0,threshold_high=60.0)

    def test_adc_t_2(self):
        self._test_adc_threshold(adc=self.sca.adc_channels.T_2,threshold_low=15.0,threshold_high=60.0)


class Test3Pa3(TestcaseBase):  # int is to force order of execution
    def setUp(self):
        super().setUp()
        self.pa3.initialize()
        self.count_lol, self.count_c1b, self.count_c2b = 0,0,0

    def _set_lol_counters(self):
        self.count_lol, self.count_c1b, self.count_c2b = self.pa3.loss_of_lock_counter.get()

    def _check_lol_counters(self):
        lol, c1b, c2b = self.pa3.loss_of_lock_counter.get()
        self.assertEqual(self.count_lol, lol, "LOL counter increased!")
        self.assertEqual(self.count_c1b, c1b, "C1B counter increased!")
        self.assertEqual(self.count_c2b, c2b, "C2B counter increased!")

    def test_loss_of_lock_counter(self):
        """Tests that no loss of locks are present"""
        self._set_lol_counters()
        time.sleep(10)
        self._check_lol_counters()

    def _i2c_dump_config(self, bus, total_time=60):
        """Tests the pa3 communication over the selected I2C bus"""
        self._set_lol_counters()
        PRINT_INTERVAL = 10
        start = time.time()
        total_tests = 0
        failed_tests = 0
        last_read = start
        self.logger.setLevel('CRITICAL')
        cur_reg = 0
        failed_regs = []
        self.pa3.set_i2c_channel(bus)
        while (time.time() - start) < total_time:
            total_tests += 1
            try:
                for register in proasic3.Pa3Register:
                    cur_reg = register
                    self.pa3.read_reg(address=register)

            except Exception as ae:
                self.logger.info(ae)
                failed_tests += 1
                failed_regs.append(cur_reg)

            if(time.time() - last_read) > PRINT_INTERVAL:
                last_read = time.time()
                self.logger.setLevel('INFO')
                self.logger.info("Number of tests failed on i2c: %d/%d", failed_tests, total_tests)
                self.logger.setLevel('CRITICAL')

        self.logger.setLevel('INFO')
        self.logger.info(f"Test stopped after {total_time:.2f} s")
        self.logger.info("{0:0.2f} reads per second".format(total_tests/(time.time()-start)))
        self.logger.info("Average read time {0:e}s".format((time.time()-start)/(total_tests)))
        self.logger.info("Number of tests failed on i2c: %d/%d", failed_tests, total_tests)
        self.logger.info('Failing regs:')
        self.logger.info('\n'.join(starmap('{}: {}'.format, enumerate(failed_regs))))

        self._check_lol_counters()
        self.assertEqual(failed_tests, 0, f"PA3 i2c read failing on bus {bus.name}")

    def test_i2c_dump_config_0(self):
        print("")
        self._i2c_dump_config(bus=gbt_sca.ScaChannel.I2C0)

    def test_i2c_dump_config_5(self):
        print("")
        self._i2c_dump_config(bus=gbt_sca.ScaChannel.I2C5)


@unittest.skip('Dummy test for development')
class TestExitHandling(TestcaseBase):
    def test_0_access(self):
        _, _githash_ref = self.tb.rdo.read(1,1)

    def test_1_pass(self):
        self.assertEqual(0,0,"Failure not expected here")

    @unittest.skip("Failure disabled")
    def test_2_fail(self):
        self.assertEqual(0,1,"Failure provoked")


def setup_logger():
    """Sets up the logger"""
    global logger_global
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    log_folder = "logs"
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)

    log_file = log_folder + f"/RU_{serial_number}.log"
    log_file_errors = log_folder + f"/RU_{serial_number}_error.log"

    fh = logging.FileHandler(log_file)
    fh2 = logging.FileHandler(log_file_errors)
    #ch = logging.StreamHandler()

    fh.setLevel(logging.INFO)
    fh2.setLevel(logging.ERROR)
    #ch.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    #formatter_ch = logging.Formatter(
    #    "%(name)s - %(levelname)s - %(message)s")

    fh.setFormatter(formatter)
    fh2.setFormatter(formatter)
    #ch.setFormatter(formatter_ch)

    logger.addHandler(fh)
    logger.addHandler(fh2)
    #logger.addHandler(ch)
    logger_global = logger


def program_pa3():
    tb_global.logger.setLevel(logging.INFO)
    try:
        logger_global.info('Programming PA3.')
        subprocess.run(args=['make', 'program_PA3_chain', os.path.join(script_path, pa3_bitfile)],
                             cwd=os.path.join(script_path, '../../../modules/board_support_software/software'),
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
    except subprocess.CalledProcessError as e:
        logger_global.error(e.output.decode())
        logger_global.error('PA3 programming failed.')
        print('PA3 programming failed, check J30 and J31 position.\nMake sure Flashpro 5 programmer is connected.\n \
               See log for more details.')
        sys.stdout.flush()
        os._exit(1)
    except Exception as e:
        print('PA3 programming crashed.')
        logger_global.error('PA3 programming crashed, traceback not logged.')
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        os._exit(1)
    logger_global.info('PA3 programmed.')
    print("Power Cycle RU")
    os._exit(0)

def program_xcku():
    tb_global.logger.setLevel(logging.INFO)
    try:
        logger_global.info('Programming XCKU.')
        subprocess.run(args=['make', 'program_RU', os.path.join(script_path, ru_wb2fifo_bitfile)],
                       cwd=os.path.join(script_path, '../../../modules/board_support_software/software'),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
    except subprocess.CalledProcessError as e:
        logger_global.error(e.output.decode())
        logger_global.error('XCKU programming failed.')
        print('XCKU programming failed, check J30 and J31.\nMake sure Xilinx programmer is connected.\n \
               See log for more details.')
        sys.stdout.flush()
        os._exit(1)
    except Exception as e:
        print('XCKU programming crashed.')
        logger_global.error('XCKU programming crashed, traceback not logged.')
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        os._exit(1)
    logger_global.info('XCKU programmed with wb2fifo.')
    input("Disconnect Xilinx programmer, then press ENTER")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-sn', action='store', type=int, help='RU serial number', required=True, dest='serial_number')
    parser.add_argument('-c', action='store', default=os.path.join(script_path, '../../config/testbench_mvtx1.yml'), help='Testbench config file', dest='config_file')
    parser.add_argument('-no_power', action='store_true', default=True, help='Skip check of Hameg', dest='no_power')
    parser.add_argument('-ch', action='store', default=0, type=int, help='Set GBT channel, for use with CRU', dest='channel')
    options, unittest_args = parser.parse_known_args()

    unit_argv = [sys.argv[0]] + unittest_args

    serial_number = options.serial_number
    channel = options.channel
    config_file_path = os.path.realpath(options.config_file)
    setup_logger()

    logger_global.info("==================")
    logger_global.info(f"Test of RU {serial_number}")
    logger_global.info("==================")

    # Power check
    if options.no_power:
        logger_global.info("Power logging disabled")
    else:
        try:
            HAMEG_PORT = "/dev/ttyHAMEG"
            HAMEG_CHANNEL = 2
            hameg_global = hameg.Hameg(HAMEG_PORT)
            voltage = hameg_global.get_voltage(HAMEG_CHANNEL)
            current = hameg_global.get_current(HAMEG_CHANNEL)
            tripped = hameg_global.get_fuse_triggered(HAMEG_CHANNEL)
            logger_global.info(f"Powercheck Voltage: {voltage:.3f} V, Current: {current/1000:.3f} A, Fuse triggered: {tripped}")
        except Exception as e:
            logger_global.error("Hameg initialisation failed, logging")
            logger_global.error(e, exc_info=True)
            try:
                hameg_global = hameg.Hameg(HAMEG_PORT)
                voltage = hameg_global.get_voltage(HAMEG_CHANNEL)
                current = hameg_global.get_current(HAMEG_CHANNEL)
                tripped = hameg_global.get_fuse_triggered(HAMEG_CHANNEL)
                logger_global.info(f"Powercheck Voltage: {voltage:.3f} V, Current: {current/1000:.3f} A, Fuse triggered: {tripped}")
            except:
                logger_global.error("Hameg initialisation failed (2nd try), logging")
                logger_global.error(e, exc_info=True)
                print("Error: Hameg initialisation failed (2nd try), is the Hameg on?")
                os._exit(1)
        except:
            logger_global.error("Hameg initialisation failed, traceback not logged")
            traceback.print_exc(file=sys.stdout)
            print("Error: Hameg initialisation failed, is the Hameg on?")
            os._exit(1)

    tb_global = testbench.configure_testbench(config_file_path=config_file_path,
                                              run_standalone=True)
    # CRU check
    try:
        tb_global.initialize_boards()
    except Exception as e:
        logger_global.error("Test crashed before starting, logging")
        logger_global.error(e, exc_info=True)
        try:
            tb_global.initialize_boards()
        except Exception as e:
            logger_global.error("Test crashed before starting (2nd try), logging")
            logger_global.error(e, exc_info=True)
            print("Error: CRU initialize failed (2nd try)")
            os._exit(1)
    except:
        logger_global.error("Test crashed, traceback not logged")
        traceback.print_exc(file=sys.stdout)
        print("Error: CRU initialize failed")
        os._exit(1)

    # Program XCKU with wb2fifo
    try:
        tb_global.logger.setLevel(logging.FATAL)
        tb_global.cru.initialize()
        if tb_global.rdo.version() != rdo_wb2fifo_githash: # Try if already programmed and hash is correct
            program_xcku()
    except Exception as e: # If un-programmed and reading version, an exception is thrown and it ends here
        try:
            tb_global.program_all_xcku() # Try to program from flash
            tb_global.cru.initialize()
            if tb_global.rdo.version() != rdo_wb2fifo_githash:
                program_xcku()
        except Exception as e: # Programming from flash failed
            program_xcku()
    except:
        logger_global.error("PA3 init crashed, traceback not logged")
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        os._exit(1)

    # Check if PA3 is programmed
    try:
        tb_global.logger.setLevel(logging.FATAL)
        tb_global.initialize_boards()
        if tb_global.rdo.pa3.githash() != pa3_githash:
            program_pa3()
    except Exception as e:
        program_pa3()
    except:
        logger_global.error("PA3 init crashed, traceback not logged")
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        os._exit(1)

    tb_global.logger.setLevel(logging.INFO)

    # Unit test
    try:
        logger_global.info("Start Test")
        tb_global.rdo.comm.discardall_dp1(20)
        tb_global.cru.comm.discardall_dp1(20)
        tb_global.cru.initialize(gbt_ch=channel)
        time.sleep(1)
        unittest.main(verbosity=2, exit=True, argv=unit_argv)
    except KeyboardInterrupt as ki:
        logger_global.error("Test interrupted with KeyboardInterrupt")
        logger_global.info(ki, exc_info=True)
        os._exit(1)
    except SystemExit:
        pass
    except Exception as e:
        logger_global.error("Test crashed, logging")
        logger_global.error(e, exc_info=True)
        os._exit(1)
    except:
        logger_global.error("Test crashed, traceback not logged")
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        os._exit(1)

    logger_global.info("==================")
    logger_global.info("       Done")
    logger_global.info("==================")
