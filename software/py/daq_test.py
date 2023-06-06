#!/usr/bin/env python3.9
# coding: utf-8
"""Script for running the DAQ test for the commissioning.
This script is meant to work with a single RU"""

#################################
# Diagnostic
############################################
#import importlib
#ht_exist = importlib.util.find_spec("hanging_threads")
#if ht_exist:
#from hanging_threads import start_monitoring
#monitoring_thread = start_monitoring()
############################################
###########################################

from collections import OrderedDict
from datetime import datetime
from enum import IntEnum, unique
from math import floor

import argparse
import jsonpickle
import logging
import os
import select
import subprocess
import signal
import sys
import time
import yaml


script_path = os.path.dirname(os.path.realpath(__file__))
modules_path = os.path.join(
    script_path, '../../modules/board_support_software/software/py/')
sys.path.append(modules_path)
from module_includes import *

from chip import ModeControlChipModeSelector
from pALPIDE import Alpide

import trigger_handler
import testbench
import daq_test_configurator
import crate_mapping
import ru_transition_board

@unique
class RuTriggeringMode(IntEnum):
    """Triggering modes for the test.
    Assumes trigger over CRU"""
    CONTINUOUS        = 0   # Triggering is handled in the RU at the specified
                            # frequency (Synchronised to HB)
    TRIGGERED_SEQ      = 1  # Sequencer is providing periodic triggers.
                            # Used also for thresholdscan
    TRIGGERED_SEQ_RAND = 2  # Sequencer is provided the triggers.
                            # Random distribution.
                            # Not implemented yet
    PERIODIC           = 3  # Periodic triggers from CRU/LTU CTP emulator
                            # in triggered mode
                            # (requires triggering on GBTx2 to work!)
    DUMMY_CONTINUOUS   = 4  # Periodic triggers from CRU/LTU CTP emulator with strobe
                            # length configured as for continuous mode
                            # (requires triggering on GBTx2 to work!)
    PERIODIC_LIMITED   = 5  # Periodic triggers from LTU CTP emulator
                            # limited to NUM_TRIGGERS
                            # (requires triggering on GBTx2 to work!)
    MANUAL             = 6  # Manual triggers either from GTM or via
                            # command
                            # requires triggering on GBTx2 to work)


@unique
class SensorPoweringScheme(IntEnum):
    """Power control for the test."""
    POWERUNIT      = 0   # Uses the powerunit to control the ALPIDE power
    NONE           = 1   # Does not handle the power. The user should take
                         # care of it
    DUAL_POWERUNIT = 2   # Uses two powerunits to control the ALPIDE power
    MONITOR        = 3   # Only monitors one powerunit per stave


class RuDataPoint(object):
    """Datapoint for collecting continuous readout data from RUs"""
    def __init__(self):
        self.timestamp = None
        self.gbt_channel = None
        self.pa3_values = None
        self.powerunit1_values = None
        self.powerunit2_values = None
        self.powerunit1_pt100 = None
        self.powerunit2_pt100 = None
        self.chipdata = None
        self.alpide_control_counters = None
        self.trigger_handler_mon = None
        self.trigger_handler_timebase_sync = None
        self.trigger_handler_triggered_mode = None
        self.gth_aligned = None
        self.gth_status = None
        self.lane_counters = OrderedDict()
        self.wsmstr_rderr = None
        self.wsmstr_wrerr = None
        self.sysmon_vccint = None
        self.sysmon_vccaux = None
        self.sysmon_vccbram = None
        self.sysmon_vcc_alpide = None
        self.sysmon_vcc_sca = None
        self.sysmon_temp = None
        self.sysmon_tmr_status = None
        self.gbtx_flow_monitor_counters = None
        self.lane_counters_gpio = OrderedDict()
        self.gbt_packer_0_monitor = None
        self.gbt_packer_1_monitor = None
        self.gbt_packer_2_monitor = None
        self.gth_config = None
        self.gpio_config = None
        self.readout_master_status = None
        self.readout_master_nok_lanes = None
        self.readout_master_faulty_lanes = None
        self.mmcm_gbtx_rxrdy_monitor = None


class DataPoint(object):
    """Datapoint for collecting continuous readout data"""
    def __init__(self):
        self.timestamp = None
        self.cru_counters = None
        self.cru_adcs = None
        self.cru_gpio = None
        self.cru_dropped_packets = None
        self.cru_total_packets = None
        self.cru_last_hb_dwrapper = None
        self.cru_datapath_counters = None
        self.rdo_values = OrderedDict()


class ExitStatus(object):
    """Class defining the exit status of the test"""
    def __init__(self):
        self.timestamp =None
        self.exit_id = None
        self.msg = None
        self.sca_gpio = []
        self.powerenable_status = []
        self.chip0_pll_status = []
        self.run_error = None
        self.fuse_triggered = None
        self.discardall_dp1_success = None


def heardKeypress():
    i,o,e = select.select([sys.stdin],[],[],0.0001)
    for s in i:
        if s == sys.stdin:
            in_val = sys.stdin.readline()
            return in_val.strip()
    return None


def format_for_roc_config(ls):
    """Formats the link list for roc_config"""
    if len(ls):
        links_list = str(ls)
        links_list = links_list.replace("[", "")
        links_list = links_list.replace("]", "")
        links_list = links_list.replace(" ", "")
    else:
        links_list = ""
    return links_list


class DaqTest(object):
    """Class implementing the test"""
    def __init__(self, testbench=None, name="DAQ Test"):
        self.testbench = testbench

        self.logger = logging.getLogger(name)

        self.load_config()

        self.logdir = None

        self.dump_process = None
        self.readout_process = None
        self.testrun_exit_status_info = None
        self.fdaq_process = [None]*8

        # Data files
        self.datafile = None
        self.datafilepath = None

        # PrefetchComm
        self.sequence_cru = None
        self.sequence_rdo = None

        # live monitor
        self.tot_read_counter = 0

        # trigger source
        self.trigger_on_gbtx2 = None

        self.trigger_cnt = 0

        self.read_str = ''

        self.readout_config_path_modified = False

        self.test_pass = True

        # Used to decide if to warn during run if sync get lost
        self.timebase_sync_at_start = None

    def load_config(self):
        self.config = daq_test_configurator.DaqTestConfig()

    def initialize_testbench(self):
        """Assigns a testbench to the test"""
        if self.testbench is None:
            self.testbench = testbench.Testbench(cru_sn=self.config.CRU_SN,
                                                 check_cru_hash=self.config.CHECK_HASH,
                                                 expected_cru_githash=self.config.GITHASH_CRU,
                                                 ctrl_and_data_link_list=self.config.CTRL_AND_DATA_LINK_LIST,
                                                 only_data_link_list=self.config.ONLY_DATA_LINK_LIST,
                                                 trigger_link_list=self.config.TRIGGER_LINK_LIST,
                                                 ru_transition_board_version=self.config.RU_TRANSITION_BOARD_VERSION,
                                                 ru_main_revision=self.config.RU_MAIN_REVISION,
                                                 ru_minor_revision=self.config.RU_MINOR_REVISION,
                                                 power_board_version=self.config.POWER_BOARD_VERSION,
                                                 power_board_filter_50hz_ac_power_mains_frequency=self.config.POWER_BOARD_FILTER_50HZ_AC_POWER_MAINS_FREQUENCY,
                                                 powerunit_resistance_offset_pt100=self.config.POWERUNIT_RESISTANCE_OFFSET_PT100,
                                                 layer=self.config.LAYER,
                                                 ltu_hostname=self.config.LTU_HOSTNAME,
                                                 subrack=self.config.SUBRACK,
                                                 cru_type=self.config.CRU_TYPE,
                                                 use_rdo_usb=self.config.USE_RDO_USB,
                                                 run_standalone=False,
                                                 use_usb_comm=False)

    def setup_powerunit(self):
        """Sets up the power to the HIC"""
        if not self.config.DRY:
            self.logger.info("Setting up powerunit")
            if self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.POWERUNIT:
                for rdo in self.testbench.rdo_list:
                    rdo.powerunit_1.initialize()
                    rdo.powerunit_1.setup_power_modules(module_list=self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST,
                                                    avdd=self.config.SENSOR_AVDD,
                                                    dvdd=self.config.SENSOR_DVDD,
                                                    avdd_current=self.config.SENSOR_AVDD_MAX_CURRENT,
                                                    dvdd_current=self.config.SENSOR_DVDD_MAX_CURRENT,
                                                    bb=self.config.SENSOR_VBB)
                    rdo.powerunit_1.controller.enable_temperature_interlock(internal_temperature_limit=self.config.POWERUNIT_LIMIT_TEMPERATURE_HARDWARE,
                                                                            ext1_temperature_limit=self.config.POWERUNIT_LIMIT_TEMPERATURE_HARDWARE)
            elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.DUAL_POWERUNIT:
                for rdo in self.testbench.rdo_list:
                    rdo.powerunit_1.initialize()
                    rdo.powerunit_2.initialize()
                    if self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST != []:
                        rdo.powerunit_1.setup_power_modules(module_list=self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST,
                                                        avdd=self.config.SENSOR_AVDD,
                                                        dvdd=self.config.SENSOR_DVDD,
                                                        avdd_current=self.config.SENSOR_AVDD_MAX_CURRENT,
                                                        dvdd_current=self.config.SENSOR_DVDD_MAX_CURRENT,
                                                        bb=self.config.SENSOR_VBB)
                        rdo.powerunit_1.controller.enable_temperature_interlock(internal_temperature_limit=self.config.POWERUNIT_LIMIT_TEMPERATURE_HARDWARE,
                                                                                ext1_temperature_limit=self.config.POWERUNIT_LIMIT_TEMPERATURE_HARDWARE)
                    if self.config.POWER_UNIT_2_OUTPUT_CHANNEL_LIST != []:
                        rdo.powerunit_2.setup_power_modules(module_list=self.config.POWER_UNIT_2_OUTPUT_CHANNEL_LIST,
                                                        avdd=self.config.SENSOR_AVDD,
                                                        dvdd=self.config.SENSOR_DVDD,
                                                        avdd_current=self.config.SENSOR_AVDD_MAX_CURRENT,
                                                        dvdd_current=self.config.SENSOR_DVDD_MAX_CURRENT,
                                                        bb=self.config.SENSOR_VBB)
                        rdo.powerunit_2.controller.enable_temperature_interlock(internal_temperature_limit=self.config.POWERUNIT_LIMIT_TEMPERATURE_HARDWARE,
                                                                                ext1_temperature_limit=self.config.POWERUNIT_LIMIT_TEMPERATURE_HARDWARE)

            elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.NONE:
                # Power not handled
                pass
            elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.MONITOR:
                pass
            else:
                raise NotImplementedError

    def program_Xcku(self):
        pass

    def configure_run(self, config_file):
        """Analyses the configuration and stores is as configuration for the test"""
        self.config.configure_run(config_file=config_file, logdir=self.logdir)

    def on_test_start(self):
        pass

    def set_scan_specific_registers(self):
        pass

    def set_test_duration(self):
        pass

    def set_scan_specific_trigger_registers(self):
        pass

    def get_bad_double_columns(self, rdo):
        if rdo is None:
            rdo = self.testbench.rdo
        yml_filename = f"{rdo.identity.get_stave_name()}.yml"
        path = os.path.join(script_path, "../config/mask_double_cols/")
        if yml_filename not in os.listdir(path):
            self.logger.info(f"yml file {path} not found. No double columns masked!")
            bad_dcols = None
        else:
            with open(path+yml_filename, 'r') as f:
                bad_dcols = yaml.load(f, Loader=yaml.FullLoader)
                self.logger.debug(f"yml file {path} found")

        return bad_dcols

    def get_bad_pixels(self, rdo):
        if rdo is None:
            rdo = self.testbench.rdo
        yml_filename = f"{rdo.identity.get_stave_name()}.yml"
        path = os.path.join(script_path, "../config/noise_masks/")
        if yml_filename not in os.listdir(path):
            self.logger.info(f"yml file {path} not found. No bad pixels masked!")
            bad_pixels = None
        else:
            with open(path+yml_filename, 'r') as f:
                bad_pixels = yaml.load(f, Loader=yaml.FullLoader)
                self.logger.debug(f"yml file {path} found")
        return bad_pixels

    def on_test_stop(self):
        pass

    def check_powerstate_Ru(self):
        raise NotImplementedError

    def powercycle_Ru(self):
        raise NotImplementedError

    def check_powerstate_powerunit(self):
        raise NotImplementedError

    def powercycle_powerunit(self):
        raise NotImplementedError

    def poweroff_powerunit(self):
        raise NotImplementedError

    def force_cut_sensor_power(self):
        if self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.POWERUNIT:
            try:
                for rdo in self.testbench.rdo_list:
                    rdo.powerunit_1.power_off_all()
                    rdo.alpide_control.disable_dclk()
            except:
                self.poweroff_powerunit()
                raise
        elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.DUAL_POWERUNIT:
            try:
                for rdo in self.testbench.rdo_list:
                    rdo.powerunit_1.power_off_all()
                    rdo.powerunit_2.power_off_all()
                    rdo.alpide_control.disable_dclk()
            except:
                self.poweroff_powerunit()
                raise
        elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.NONE:
            # Power Not Handled
            pass
        elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.MONITOR and self.config.LAYER in [testbench.LayerList.INNER, testbench.LayerList.NO_PT100]:
            try:
                for rdo in self.testbench.rdo_list:
                    rdo.powerunit_1.power_off_all()
                    rdo.alpide_control.disable_dclk()
            except:
                self.poweroff_powerunit()
                raise
        elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.MONITOR and self.config.LAYER == testbench.LayerList.MIDDLE:
            try:
                for rdo in self.testbench.rdo_list:
                    rdo.powerunit_1.power_off_all()
                    rdo.alpide_control.disable_dclk()
            except:
                self.poweroff_powerunit()
                raise
        elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.MONITOR and self.config.LAYER == testbench.LayerList.OUTER:
            try:
                for rdo in self.testbench.rdo_list:
                    rdo.powerunit_1.power_off_all()
                    rdo.powerunit_2.power_off_all()
                    rdo.alpide_control.disable_dclk()
            except:
                self.poweroff_powerunit()
                raise
        else:
            raise NotImplementedError

    def powercycle_stave(self):
        if self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.POWERUNIT:
            for rdo in self.testbench.rdo_list:
                rdo.powerunit_1.power_off_all()
                rdo.powerunit_1.setup_power_modules(module_list=self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST,
                                                avdd=self.config.SENSOR_AVDD,
                                                dvdd=self.config.SENSOR_DVDD,
                                                avdd_current=self.config.SENSOR_AVDD_MAX_CURRENT,
                                                dvdd_current=self.config.SENSOR_DVDD_MAX_CURRENT,
                                                bb=self.config.SENSOR_VBB)
        elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.DUAL_POWERUNIT:
            for rdo in self.testbench.rdo_list:
                rdo.powerunit_1.power_off_all()
                rdo.powerunit_2.power_off_all()
                rdo.powerunit_1.setup_power_modules(module_list=self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST,
                                                avdd=self.config.SENSOR_AVDD,
                                                dvdd=self.config.SENSOR_DVDD,
                                                avdd_current=self.config.SENSOR_AVDD_MAX_CURRENT,
                                                dvdd_current=self.config.SENSOR_DVDD_MAX_CURRENT,
                                                bb=self.config.SENSOR_VBB)
                rdo.powerunit_2.setup_power_modules(module_list=self.config.POWER_UNIT_2_OUTPUT_CHANNEL_LIST,
                                                avdd=self.config.SENSOR_AVDD,
                                                dvdd=self.config.SENSOR_DVDD,
                                                avdd_current=self.config.SENSOR_AVDD_MAX_CURRENT,
                                                dvdd_current=self.config.SENSOR_DVDD_MAX_CURRENT,
                                                bb=self.config.SENSOR_VBB)
        elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.NONE:
            # Power Not Handled
            pass
        elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.MONITOR:
            pass
        else:
            raise NotImplementedError

    def check_power(self):
        raise NotImplementedError

    def setup_comms(self):
        self.testbench.setup_comms(cru_ctlOnly=True,
                                   gbt_channel=self.config.CTRL_AND_DATA_LINK_LIST[0])

    def which(self, exe):
        """Check if executable exists in environment"""
        for directory in os.getenv("PATH").split(':'):
            if (os.path.exists(os.path.join(directory, exe))):
                return os.path.join(directory, exe)
        return None

    def load_environment(self, module):
        mc_out = subprocess.check_output(['modulecmd', 'python', 'load', module], stderr=subprocess.PIPE)
        exec(mc_out)

    def get_env_with_infologger_to_stdout(self):
        """ Set O2_INFOLOGGER_MODE environmental variable to stdout for O2 commands

        Many functions of daq_test rely on the output of O2 commands. To parse the output of O2 commands
        the output must be sent to stdout. This is configured by setting the O2_INFOLOGGER_MODE env variable to stdout.
        """
        os.environ['O2_INFOLOGGER_MODE'] = 'stdout'
        return os.environ.copy()

    def get_readout_config_path(self):
        if 'CI' in os.environ and not self.readout_config_path_modified:
            index = self.config.READOUT_PROC_CFG.find("readout")
            self.config.READOUT_PROC_CFG = self.config.READOUT_PROC_CFG[:index] + "ci_" + self.config.READOUT_PROC_CFG[index:]
            readout_config_path = os.path.abspath(os.path.join(script_path, self.config.READOUT_PROC_CFG))
            self.readout_config_path_modified = True
        else:
            readout_config_path = os.path.abspath(os.path.join(script_path, self.config.READOUT_PROC_CFG))
        assert os.path.isfile(readout_config_path), readout_config_path
        self.logger.info(f'readout_config_path: {readout_config_path}')
        return readout_config_path

    def start_datataking(self):
        if self.config.CRU_TYPE is testbench.CruType.O2:
            readout_config = f'file:{self.get_readout_config_path()}'
            alienv = self.get_env_with_infologger_to_stdout()
            self.logger.info(f'Starting o2-readout-exe with config: {readout_config}')
            self.readout_process = subprocess.Popen(['o2-readout-exe', readout_config], env=alienv, encoding='utf-8',
                                                    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            readout_started = False
            readout_stdout = '\n'
            for line in self.readout_process.stdout:
                readout_stdout += '\t' + line
                if 'Entering main loop' in line:
                    readout_started = True
                    break
            if readout_started:
                self.logger.info('o2-readout-exe output:' + readout_stdout)
                self.logger.info('Readout started correctly')
            else:
                self.logger.error('Could not start o2-readout-exe! Output: ' + readout_stdout)
                self.logger.error('Error messages (if any):\n' +
                                  ''.join('\t'+line for line in self.readout_process.stderr))
                raise RuntimeError("Could not start o2-readout-exe due to an error.")
        else:
            command = "nc 127.0.0.1 30001"

            output_data_filename = os.path.join(self.logdir, 'dataout_dp2.Z')
            event_filter_prog = os.path.join(script_path, '../../modules/board_support_software/software/cpp/build/event_filter')
            event_filter_log = os.path.join(script_path, 'logs/event_filter_out.txt')
            #cmd = "{0} | {1} >> {2}".format(nc_command,event_filter_prog,event_filter_log)

            if self.config.EVENT_ANALYSYS_ONLINE:
                cmd = "{0} | {1} {2} {3} {4} {5}".format(command,
                                                         os.path.join(script_path, '../sh/store_check_events.sh'),
                                                         output_data_filename,
                                                         self.logdir,
                                                         event_filter_prog,
                                                         event_filter_log)
            else:
                cmd = "{0} | compress | split -b 10485760 -d - {1}".format(command,
                                                                           output_data_filename)

            self.readout_process = subprocess.Popen(cmd, shell=True,preexec_fn=os.setsid,stdin=subprocess.PIPE)

    def start_fdaq(self):
        """Start ATLAS fdaq process"""
        if self.config.CRU_TYPE is testbench.CruType.FLX:
            timeout = f'{int(self.config.TEST_DURATION) + int(self.config.FDAQ_STARTUP_TIME)}'
            self.logger.info('Starting ATLAS fdaq_process')
            print(self.config.FDAQ_ACTIVE_DMA)
            for dma_count, active in enumerate(self.config.FDAQ_ACTIVE_DMA):
                dma = dma_count % 4
                ep = int(dma_count/4)
                if active:
                    self.fdaq_process[dma_count] = subprocess.Popen(["fdaq", "-d", f"{ep}", "-i", f"{dma}", "-t", timeout, self.config.FDAQ_DATAFILE+f"_ep{ep}_{dma}"],
                                                             encoding='utf-8', stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                    readout_started = False
                    readout_stdout = '\n'
                    for line in self.fdaq_process[dma_count].stdout:
                        readout_stdout += '\t' + line
                        if '**START**' in line:
                            readout_started = True
                            break
                    if readout_started:
                        self.logger.info('fdaq output:%s', readout_stdout)
                        self.logger.info(f"\'fdaq -d {ep}\' started correctly")
                    else:
                        self.logger.error(f"Could not start fdaq -d {ep}! Output: %s", readout_stdout)
                        self.logger.error('Error messages (if any):\n%s',
                                        ''.join('\t'+line for line in self.fdaq_process[dma_count].stderr))
                        raise RuntimeError(f"Could not start \'fdaq -d {ep}\' due to an error.")
        else:
            raise NotImplementedError

    def tearDown(self):
        if self.config.PA3_SCRUBBING_ENABLE:
            for rdo in self.testbench.rdo_list:
                rdo.pa3.config_controller.stop_blind_scrubbing()
        if not self.config.DRY:
            if self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.POWERUNIT:
                for rdo in self.testbench.rdo_list:
                    rdo.powerunit_1.log_values_modules(module_list=self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST)
                    rdo.powerunit_1.power_off_all()
                    time.sleep(1)
                    rdo.powerunit_1.log_values_modules(module_list=self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST)
                    rdo.alpide_control.disable_dclk()
            elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.DUAL_POWERUNIT:
                for rdo in self.testbench.rdo_list:
                    rdo.powerunit_1.log_values_modules(module_list=self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST)
                    rdo.powerunit_2.log_values_modules(module_list=self.config.POWER_UNIT_2_OUTPUT_CHANNEL_LIST)
                    rdo.powerunit_1.power_off_all()
                    rdo.powerunit_2.power_off_all()
                    time.sleep(1)
                    rdo.powerunit_1.log_values_modules(module_list=self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST)
                    rdo.powerunit_2.log_values_modules(module_list=self.config.POWER_UNIT_2_OUTPUT_CHANNEL_LIST)
                    rdo.alpide_control.disable_dclk()
                    rdo.powerunit_1.controller.disable_all_temperature_limits()
                    rdo.powerunit_2.controller.disable_all_temperature_limits()
            elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.NONE:
                # Power Not Handled
                pass
            elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.MONITOR and self.config.LAYER in [testbench.LayerList.INNER, testbench.LayerList.NO_PT100]:
                for rdo in self.testbench.rdo_list:
                    self.testbench.log_values_ib_stave(rdo=rdo)
            elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.MONITOR and self.config.LAYER == testbench.LayerList.MIDDLE:
                for rdo in self.testbench.rdo_list:
                    self.testbench.log_values_ml_stave(rdo=rdo)
            elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.MONITOR and self.config.LAYER == testbench.LayerList.OUTER:
                for rdo in self.testbench.rdo_list:
                    self.testbench.log_values_ob_stave(rdo=rdo)
            else:
                raise NotImplementedError

    # Data to be read from the boards
    def sensor_reads(self, dp, rdo=None):
        if rdo == None:
            rdo = self.testbench.rdo
        gbt_channel = rdo.get_gbt_channel()
        if gbt_channel not in dp.rdo_values.keys():
            dp.rdo_values[gbt_channel] = RuDataPoint()
            dp.rdo_values[gbt_channel].timestamp = dp.timestamp
            dp.rdo_values[gbt_channel].gbt_channel = gbt_channel
        chipdata =  OrderedDict()
        for ch in self.testbench.stave(gbt_channel):
            if ch.chipid not in self.config.EXCLUDE_GTH_LIST:
                try:
                    lock = ch.getreg_dtu_pll_lock_1()[1]
                    lock_counter = lock['LockCounter']
                    lock_status = lock['LockStatus']
                    lock_flag = lock['LockFlag']
                    trigger_count = ch.getreg_fromu_status_1()[0]
                    strobes_count = ch.getreg_fromu_status_2()[0]
                    eventro_count = ch.getreg_fromu_status_3()[0]
                    frame_count = ch.getreg_fromu_status_4()[0]
                    fs5 = ch.getreg_fromu_status_5()[1]
                    last_bc = fs5['BunchCounter']
                    fs5_event_count = fs5['EventCounter']
                    enable_strobe_generation = fs5['EnStrobeGeneration']

                    seu_error_counter = ch.getreg_seu_counter()[0]
                    cmu_dmu_status = ch.getreg_cmu_and_dmu_status()

                    chipid = ch.chipid
                    chipdata[chipid] = {}
                    chipdata[chipid]['is_ib'] = ch.is_inner_barrel()
                    chipdata[chipid]['is_ob_master'] = ch.is_outer_barrel_master()
                    chipdata[chipid]['is_ob_slave'] = ch.is_outer_barrel_slave()
                    if not ch.is_outer_barrel_slave():
                        chipdata[chipid]['lock_counter'] = lock_counter
                        chipdata[chipid]['lock_status'] = lock_status
                        chipdata[chipid]['lock_flag'] = lock_flag
                    chipdata[chipid]['trigger_count'] = trigger_count
                    chipdata[chipid]['strobes_count'] = strobes_count
                    chipdata[chipid]['eventro_count'] = eventro_count
                    chipdata[chipid]['frame_count'] = frame_count
                    chipdata[chipid]['last_bc'] = last_bc
                    chipdata[chipid]['fromu_status_5_event_count'] = fs5_event_count
                    chipdata[chipid]['enable_strobe_generation'] = enable_strobe_generation
                    chipdata[chipid]['seu_count'] = seu_error_counter
                    chipdata[chipid]['cmu_dmu_status'] = cmu_dmu_status
                except Exception as e:
                    self.logger.info(f"Chip {ch.chipid} read failed from RU {gbt_channel}")
                    self.logger.info(e, exc_info=True)
        dp.rdo_values[gbt_channel].chipdata = chipdata

    def sensor_reads_ob_stave(self, dp, rdo=None):
        if rdo == None:
            rdo = self.testbench.rdo
        gbt_channel = rdo.get_gbt_channel()
        stave_number = self.testbench.get_stave_number(gbt_channel=gbt_channel)
        if stave_number in self.config.staves:
            if 'excluded-chips' in self.config.staves[stave_number]:
                excluded_chipid_ext = self.config.staves[stave_number]['excluded-chips']
            else:
                excluded_chipid_ext = []
        else:
            excluded_chipid_ext = []
        if gbt_channel not in dp.rdo_values.keys():
            dp.rdo_values[gbt_channel] = RuDataPoint()
            dp.rdo_values[gbt_channel].timestamp = dp.timestamp
            dp.rdo_values[gbt_channel].gbt_channel = gbt_channel
        chipdata =  OrderedDict()
        stave_ob = self.testbench.stave_ob(gbt_channel)
        excluded_chipid_ext = self.get_excluded_chip_list_from_config(rdo=rdo)
        for chipid_ext, ch in stave_ob.items():
            if chipid_ext in excluded_chipid_ext:
                continue
            try:
                chipdata[chipid_ext] = OrderedDict()
                if not ch.is_outer_barrel_slave():
                    lock = ch.getreg_dtu_pll_lock_1()[1]
                    lock_counter = lock['LockCounter']
                    lock_status = lock['LockStatus']
                    lock_flag = lock['LockFlag']
                trigger_count = ch.getreg_fromu_status_1()[0]
                strobes_count = ch.getreg_fromu_status_2()[0]
                eventro_count = ch.getreg_fromu_status_3()[0]
                frame_count = ch.getreg_fromu_status_4()[0]
                fs5 = ch.getreg_fromu_status_5()[1]
                last_bc = fs5['BunchCounter']
                fs5_event_count = fs5['EventCounter']
                enable_strobe_generation = fs5['FrameExtended']
                vcasn = ch.getreg_VCASN()[0]
                vcasn2 = ch.getreg_VCASN2()[0]
                vpulse_h = ch.getreg_VPULSEH()[0]
                vpulse_l = ch.getreg_VPULSEL()[0]
                i_threshold = ch.getreg_ITHR()[0]

                seu_error_counter = ch.getreg_seu_counter()[0]
                cmu_dmu_status = ch.getreg_cmu_and_dmu_status()

                chipdata[chipid_ext]['is_ib'] = ch.is_inner_barrel()
                chipdata[chipid_ext]['is_ob_master'] = ch.is_outer_barrel_master()
                chipdata[chipid_ext]['is_ob_slave'] = ch.is_outer_barrel_slave()
                if not ch.is_outer_barrel_slave():
                    chipdata[chipid_ext]['lock_counter'] = lock_counter
                    chipdata[chipid_ext]['lock_status'] = lock_status
                    chipdata[chipid_ext]['lock_flag'] = lock_flag
                chipdata[chipid_ext]['trigger_count'] = trigger_count
                chipdata[chipid_ext]['strobes_count'] = strobes_count
                chipdata[chipid_ext]['eventro_count'] = eventro_count
                chipdata[chipid_ext]['frame_count'] = frame_count
                chipdata[chipid_ext]['last_bc'] = last_bc
                chipdata[chipid_ext]['fromu_status_5_event_count'] = fs5_event_count
                chipdata[chipid_ext]['enable_strobe_generation'] = enable_strobe_generation
                chipdata[chipid_ext]['seu_count'] = seu_error_counter
                chipdata[chipid_ext]['cmu_dmu_status'] = cmu_dmu_status
                chipdata[chipid_ext]['vcasn'] = vcasn
                chipdata[chipid_ext]['vcasn2'] = vcasn2
                chipdata[chipid_ext]['vpulse_h'] = vpulse_h
                chipdata[chipid_ext]['vpulse_l'] = vpulse_l
                chipdata[chipid_ext]['ithr'] = i_threshold
            except Exception as e:
                self.logger.info(f"Chip {chipid_ext} read failed on RU {gbt_channel}")
                self.logger.info(e, exc_info=True)
        dp.rdo_values[gbt_channel].chipdata = chipdata

    def cru_reads(self,dp):
        #dp.cru_dropped_packets = self.testbench.cru.dwrapper.get_dropped_packets()
        #dp.cru_total_packets = self.testbench.cru.dwrapper.get_total_packets()
        #dp.cru_last_hb_dwrapper = self.testbench.cru.dwrapper.get_last_hb_id()
        #dp.cru_datapath_counters = self.testbench.cru.dwrapper.get_datapath_counters()

        dp.cru_adcs = self.testbench.rdo_list[0].sca.read_adcs()
        dp.cru_gpio = self.testbench.rdo_list[0].sca.read_gpio()
        dp.pa3_values = {}
        if self.config.PA3_READ_VALUES:
            for rdo in self.testbench.rdo_list:
                gbt_ch = rdo.get_gbt_channel()
                if rdo.get_gbt_channel() not in dp.rdo_values.keys():
                    dp.rdo_values[gbt_ch] = RuDataPoint()
                    dp.rdo_values[gbt_ch].timestamp = dp.timestamp
                    dp.rdo_values[gbt_ch].gbt_channel = gbt_ch
                dp.rdo_values[gbt_ch].pa3_values = rdo.pa3.dump_config()
                dp.rdo_values[gbt_ch].pa3_values['CC_SCRUB_CNT'] = rdo.pa3.config_controller.get_scrubbing_counter()
                dp.rdo_values[gbt_ch].pa3_values['CC_SCRUB_CRC'] = rdo.pa3.config_controller.get_crc()

    def rdo_reads(self,dp, rdo=None):
        if rdo is None:
            rdo = self.testbench.rdo
        gbt_channel = rdo.get_gbt_channel()
        self.logger.debug(f"reading RDO {gbt_channel}")
        if gbt_channel not in dp.rdo_values.keys():
            dp.rdo_values[gbt_channel] = RuDataPoint()
            dp.rdo_values[gbt_channel].timestamp = dp.timestamp
            dp.rdo_values[gbt_channel].gbt_channel = gbt_channel

        ## Wishbone master errors
        wsmstr_counters = rdo.master_monitor.read_counters()
        dp.rdo_values[gbt_channel].wsmstr_rderr = wsmstr_counters['RD_ERRORS']
        dp.rdo_values[gbt_channel].wsmstr_wrerr = wsmstr_counters['WR_ERRORS']

        # Trigger Handler
        dp.rdo_values[gbt_channel].trigger_handler_mon = rdo.trigger_handler.read_counters()

        if not self.config.USE_GTM:
            dp.rdo_values[gbt_channel].trigger_handler_timebase_sync = rdo.trigger_handler.is_timebase_synced()
        dp.rdo_values[gbt_channel].trigger_handler_triggered_mode  = rdo.trigger_handler.is_triggered_mode()
        dp.rdo_values[gbt_channel].trigger_handler_continuous_mode = rdo.trigger_handler.is_continuous_mode()

        ## alpide_control
        dp.rdo_values[gbt_channel].alpide_control_counters = rdo.alpide_control.read_counters()

        ## readout_master
        _, dp.rdo_values[gbt_channel].readout_master_status = rdo.readout_master.get_status()
        if self.config.GTH_ACTIVE:
            dp.rdo_values[gbt_channel].readout_master_nok_lanes = rdo.readout_master.get_ib_nok_lanes()
            dp.rdo_values[gbt_channel].readout_master_faulty_lanes = rdo.readout_master.get_ib_faulty_lanes()
        if self.config.GPIO_ACTIVE:
            dp.rdo_values[gbt_channel].readout_master_nok_lanes = rdo.readout_master.get_ob_nok_lanes()
            dp.rdo_values[gbt_channel].readout_master_faulty_lanes = rdo.readout_master.get_ob_faulty_lanes()
        if self.config.DRY:
            dp.rdo_values[gbt_channel].readout_master_nok_lanes = 0
            dp.rdo_values[gbt_channel].readout_master_faulty_lanes = 0

        ## gbt packer
        gpm = rdo.gbt_packer.read_all_counters()
        dp.rdo_values[gbt_channel].gbt_packer_0_monitor = gpm[0]
        dp.rdo_values[gbt_channel].gbt_packer_1_monitor = gpm[1]
        dp.rdo_values[gbt_channel].gbt_packer_2_monitor = gpm[2]

        ## Data Monitor
        if self.config.GTH_ACTIVE:
            for i in rdo.gth.transceivers:
                dp.rdo_values[gbt_channel].lane_counters[i] = rdo.datapath_monitor_ib.read_counters(i)
            dp.rdo_values[gbt_channel].gth_config = rdo.gth.read_config()
            ## GTH status
            dp.rdo_values[gbt_channel].gth_aligned = rdo.gth.is_aligned()
            dp.rdo_values[gbt_channel].gth_status = rdo.gth.get_gth_status()

        if self.config.GPIO_ACTIVE:
            for i in rdo.gpio.transceivers:
                dp.rdo_values[gbt_channel].lane_counters_gpio[i] = rdo.datapath_monitor_ob.read_counters(i)
            dp.rdo_values[gbt_channel].gpio_config = rdo.gpio.read_config()

        ## Sysmon status
        dp.rdo_values[gbt_channel].sysmon_vccint     = rdo.sysmon.get_vcc_int()
        dp.rdo_values[gbt_channel].sysmon_vccaux     = rdo.sysmon.get_vcc_aux()
        dp.rdo_values[gbt_channel].sysmon_vccbram    = rdo.sysmon.get_vcc_bram()
        dp.rdo_values[gbt_channel].sysmon_vcc_alpide = rdo.sysmon.get_vcc_alpide_3v3()
        dp.rdo_values[gbt_channel].sysmon_vcc_sca    = rdo.sysmon.get_vcc_sca_1v5()
        dp.rdo_values[gbt_channel].sysmon_temp       = rdo.sysmon.get_temperature()
        if dp.rdo_values[gbt_channel].sysmon_temp > 80:
            self.logger.warning("XCKU060: High temperature (%d C)",
                                dp.rdo_values[gbt_channel].sysmon_temp)

        ## GBTX flow monitor
        dp.rdo_values[gbt_channel].gbtx_flow_monitor_counters = rdo.gbtx_flow_monitor.read_counters()

        # MMCM and GBTx RXRDY monitor
        dp.rdo_values[gbt_channel].mmcm_gbtx_rxrdy_monitor = rdo.mmcm_gbtx_rxrdy_monitor.read_counters()

        # Powerunit
        if not self.config.DRY:
            ps = self.config.SENSOR_POWERING_SCHEME

            # helper functions
            def dp_update_pu1(modulelist):
                dp.rdo_values[gbt_channel].powerunit1_values = rdo.powerunit_1.get_values_modules(module_list=modulelist)
                dp.rdo_values[gbt_channel].powerunit1_pt100 = rdo.powerunit_1.read_all_temperatures()
                return dp

            def get_temp_pu1(sensor):
                return dp.rdo_values[gbt_channel].powerunit1_pt100[sensor]

            def dp_update_pu2(modulelist):
                dp.rdo_values[gbt_channel].powerunit2_values = rdo.powerunit_2.get_values_modules(module_list=modulelist)
                dp.rdo_values[gbt_channel].powerunit2_pt100 = rdo.powerunit_2.read_all_temperatures()
                return dp

            def get_temp_pu2(sensor):
                return dp.rdo_values[gbt_channel].powerunit2_pt100[sensor]

            def check_pu(powerunit, temp):
                if powerunit.minimum_temperature_pt100_disconnected > temp > self.config.POWERUNIT_LIMIT_TEMPERATURE_SOFTWARE:
                    self.force_cut_sensor_power()
                    raise RuntimeError(f"Overtemperature detected, sensor power has been shut down! {temp} C")

            if ps == SensorPoweringScheme.POWERUNIT:
                dp = dp_update_pu1(modulelist=self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST)
                t1 = get_temp_pu1('EXT1')
                check_pu(powerunit=rdo.powerunit_1, temp=t1)
            elif ps == SensorPoweringScheme.DUAL_POWERUNIT:
                dp = dp_update_pu1(modulelist=self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST)
                dp = dp_update_pu2(modulelist=self.config.POWER_UNIT_2_OUTPUT_CHANNEL_LIST)
                t1 = get_temp_pu1('EXT1')
                t2 = get_temp_pu2('EXT1')
                check_pu(powerunit=rdo.powerunit_1, temp=t1)
                check_pu(powerunit=rdo.powerunit_2, temp=t2)
            elif ps == SensorPoweringScheme.NONE:
                # Power Not Handled
                pass
            elif ps == SensorPoweringScheme.MONITOR and self.config.LAYER in [testbench.LayerList.INNER, testbench.LayerList.NO_PT100]:
                dp = dp_update_pu1(modulelist=self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST)
                t1 = get_temp_pu1('EXT1')
                check_pu(powerunit=rdo.powerunit_1, temp=t1)
            elif ps == SensorPoweringScheme.MONITOR and self.config.LAYER == testbench.LayerList.MIDDLE:
                dp = dp_update_pu1(modulelist=[0,1,2,3,4,5,6,7]) # Workaround, only half of modules is assigned to PU1 Channel List for ML
                t1 = get_temp_pu1('EXT1')
                t2 = get_temp_pu1('EXT2')
                check_pu(powerunit=rdo.powerunit_1, temp=t1)
                check_pu(powerunit=rdo.powerunit_1, temp=t2)
            elif ps == SensorPoweringScheme.MONITOR and self.config.LAYER == testbench.LayerList.OUTER:
                dp = dp_update_pu1(modulelist=self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST)
                dp = dp_update_pu2(modulelist=self.config.POWER_UNIT_2_OUTPUT_CHANNEL_LIST)
                t1 = get_temp_pu1('EXT1')
                t2 = get_temp_pu2('EXT1')
                check_pu(powerunit=rdo.powerunit_1, temp=t1)
                check_pu(powerunit=rdo.powerunit_2, temp=t2)
            else:
                raise NotImplementedError

        if not self.config.DRY:
            if self.config.READ_SENSORS_DURING_DATATAKING:
                # Deactivate triggering during sensor readout
                rdo.trigger_handler.set_opcode_gating(1)
                # Sensors
                if self.config.GTH_ACTIVE:
                    self.sensor_reads(dp=dp, rdo=rdo)
                elif self.config.GPIO_ACTIVE:
                    self.sensor_reads_ob_stave(dp=dp, rdo=rdo)
                else:
                    raise NotImplementedError
                # Reactivates it after the readings
                rdo.trigger_handler.set_opcode_gating(0)

    def print_values_ru_trigger(self, dp, gbt_channel, final_read):
        """Checks the trigger flow in the rdo in the given gbt_channel"""
        try:
            if self.timebase_sync_at_start:
                if dp.rdo_values[gbt_channel].trigger_handler_timebase_sync:
                    pass # Was sync, is sync, all good
                else:
                    # Lost sync, behaviour depends on the configuration
                    if not self.config.USE_GTM:
                        if self.config.TRIGGER_SOURCE == trigger_handler.TriggerSource.GBTx2:
                            self.test_pass = False
                            self.read_str += '\n\tERROR\t\tTimebase lost sync during the run'
                        elif self.config.TRIGGER_SOURCE == trigger_handler.TriggerSource.SEQUENCER:
                            self.read_str += '\n\tINFO\t\tTimebase not in sync during the run'
                        else:
                            raise NotImplementedError

            trigger_sent = dp.rdo_values[gbt_channel].trigger_handler_mon['TRIGGER_SENT']
            trigger_gated = dp.rdo_values[gbt_channel].trigger_handler_mon['TRIGGER_GATED']
            trigger_echoed = dp.rdo_values[gbt_channel].trigger_handler_mon['TRIGGER_ECHOED']
            trigger_illegal = dp.rdo_values[gbt_channel].trigger_handler_mon['TRIGGER_ILLEGAL_MODE_SWITCH']
            alpide_control_trigger_sent = dp.rdo_values[gbt_channel].alpide_control_counters['TRIGGER_SENT'] + dp.rdo_values[gbt_channel].alpide_control_counters['PULSE_SENT']
            alpide_control_trigger_not_sent = dp.rdo_values[gbt_channel].alpide_control_counters['OPCODE_REJECTED']

            triggers_to_alpide_control_mismatch = trigger_sent != alpide_control_trigger_sent

            if self.config.READ_SENSORS_DURING_DATATAKING:
                sensor_trigger_received_all = [dp.rdo_values[gbt_channel].chipdata[i]['trigger_count'] for i in dp.rdo_values[gbt_channel].chipdata]
                sensor_trigger_received = max(sensor_trigger_received_all)
                sensor_trigger_received_disagree = len(set(sensor_trigger_received_all)) > 1
            else:
                sensor_trigger_received = -1
                sensor_trigger_received_disagree = False

            self.read_str += '\n\tTriggers Sent:\t{0} (Echoed: {1}, Gated: {2}), AlpideControl: {3} (Not: {4})'.format(trigger_sent,
                                                                                                                       trigger_echoed,
                                                                                                                       trigger_gated,
                                                                                                                       alpide_control_trigger_sent,
                                                                                                                       alpide_control_trigger_not_sent)
            if self.config.READ_SENSORS_DURING_DATATAKING:
                self.read_str += ', Sensor: {}'.format(sensor_trigger_received)
                triggers_to_sensors_mismatch = alpide_control_trigger_sent%65536 != sensor_trigger_received
                if triggers_to_sensors_mismatch:
                    self.read_str += '\n\tWARNING (Triggers to sensor do not match the value in Alpide Control)'
                    if final_read:
                        self.test_pass = False

            if triggers_to_alpide_control_mismatch:
                self.read_str += ' (Triggers to alpide control do not match the value in trigger handler)'
                if final_read:
                    self.test_pass = False

            if sensor_trigger_received_disagree:
                self.read_str += ' (SENSORS DISAGREE): {0}'.format(sensor_trigger_received_all)
                if final_read:
                    self.test_pass = False

            if trigger_illegal:
                self.read_str += '\n\tERROR: {} illegal trigger received from CTP!'.format(trigger_illegal)
                if final_read:
                    self.test_pass = False

            if trigger_echoed>1 and not ((self.config.TRIGGERING_MODE == RuTriggeringMode.CONTINUOUS) and self.config.USE_GTM):
                self.read_str += f'\n\tERROR: echoed triggers {trigger_echoed}>1'
                if final_read:
                    self.test_pass = False

            if alpide_control_trigger_not_sent:
                self.read_str += f'\n\tERROR: ALPIDE CONTROL trigger collisions: {alpide_control_trigger_not_sent}'
                if final_read:
                    self.test_pass = False

        except Exception as e:
            self.logger.error(f"Could not perform all print values from {gbt_channel}")
            self.logger.info(e, exc_info=True)
            self.test_pass = False

    def print_values_ru_lanes(self, dp, gbt_channel, final_read):
        """Checks the data flow in the rdo"""
        try:
            sop_cntr = 0
            eop_cntr = 0
            sop_cntr += dp.rdo_values[gbt_channel].gbtx_flow_monitor_counters['UPLINK0_SOP']
            eop_cntr += dp.rdo_values[gbt_channel].gbtx_flow_monitor_counters['UPLINK0_EOP']
            sop_cntr += dp.rdo_values[gbt_channel].gbtx_flow_monitor_counters['UPLINK1_SOP']
            eop_cntr += dp.rdo_values[gbt_channel].gbtx_flow_monitor_counters['UPLINK1_EOP']
            if self.config.LAYER in [testbench.LayerList.INNER, testbench.LayerList.NO_PT100]:
                sop_cntr += dp.rdo_values[gbt_channel].gbtx_flow_monitor_counters['UPLINK2_SOP']
                eop_cntr += dp.rdo_values[gbt_channel].gbtx_flow_monitor_counters['UPLINK2_EOP']

            sop_cntr_packers = 0
            eop_cntr_packers = 0

            # grabs this value from the trigger part to check it againts the number of packets done
            trigger_sent = dp.rdo_values[gbt_channel].trigger_handler_mon['TRIGGER_SENT']

            if self.config.GTH_ACTIVE or (self.config.DRY and self.config.LAYER in [testbench.LayerList.INNER, testbench.LayerList.NO_PT100]):
                PACKERS = 3
            elif self.config.GPIO_ACTIVE or (self.config.DRY and self.config.LAYER in [testbench.LayerList.MIDDLE,testbench.LayerList.OUTER]):
                PACKERS = 2
            else:
                print (self.config.GTH_ACTIVE)
                raise NotImplementedError
            packet_done = [0]*PACKERS
            packers_timeout = [0]*PACKERS
            packers_timeout_trigger_to_start = [0]*PACKERS
            packers_timeout_idle = [0]*PACKERS
            packers_timeout_start_to_stop = [0]*PACKERS
            packers_violation = [0]*PACKERS
            packers_fifo_full = [0]*PACKERS
            packers_fifo_overflow = [0]*PACKERS
            th_fifo_full = [0]*PACKERS
            th_fifo_overflow = [0]*PACKERS

            lanes_timeout = []
            lanes_timeout_gpio = []

            sop_cntr_packers += dp.rdo_values[gbt_channel].gbt_packer_0_monitor["SOP_SENT"]
            eop_cntr_packers += dp.rdo_values[gbt_channel].gbt_packer_0_monitor["EOP_SENT"]
            packet_done[0] += dp.rdo_values[gbt_channel].gbt_packer_0_monitor["PACKET_DONE"]
            packers_timeout[0] += dp.rdo_values[gbt_channel].gbt_packer_0_monitor["PACKET_TIMEOUT"]
            packers_timeout_trigger_to_start[0] += dp.rdo_values[gbt_channel].gbt_packer_0_monitor["START_TIMEOUT"]
            packers_timeout_idle[0] += dp.rdo_values[gbt_channel].gbt_packer_0_monitor["IDLE_TIMEOUT"]
            packers_timeout_start_to_stop[0] += dp.rdo_values[gbt_channel].gbt_packer_0_monitor["STOP_TIMEOUT"]
            for count in ["VIOLATION_START","VIOLATION_ACK","VIOLATION_STOP","VIOLATION_NO_VALID_STOP","VIOLATION_NO_VALID_START","VIOLATION_EMPTY"]:
                packers_violation[0] += dp.rdo_values[gbt_channel].gbt_packer_0_monitor[count]
            packers_fifo_full[0] += dp.rdo_values[gbt_channel].gbt_packer_0_monitor["FIFO_FULL"]
            packers_fifo_overflow[0] += dp.rdo_values[gbt_channel].gbt_packer_0_monitor["FIFO_OVERFLOW"]
            th_fifo_full[0] += dp.rdo_values[gbt_channel].trigger_handler_mon['TRIGGER_FIFO_0_FULL']
            th_fifo_overflow[0] += dp.rdo_values[gbt_channel].trigger_handler_mon['TRIGGER_FIFO_0_OVERFLOW']

            sop_cntr_packers += dp.rdo_values[gbt_channel].gbt_packer_1_monitor["SOP_SENT"]
            eop_cntr_packers += dp.rdo_values[gbt_channel].gbt_packer_1_monitor["EOP_SENT"]
            packet_done[1] += dp.rdo_values[gbt_channel].gbt_packer_1_monitor["PACKET_DONE"]
            packers_timeout[1] += dp.rdo_values[gbt_channel].gbt_packer_1_monitor["PACKET_TIMEOUT"]
            packers_timeout_trigger_to_start[1] += dp.rdo_values[gbt_channel].gbt_packer_1_monitor["START_TIMEOUT"]
            packers_timeout_idle[1] += dp.rdo_values[gbt_channel].gbt_packer_1_monitor["IDLE_TIMEOUT"]
            packers_timeout_start_to_stop[1] += dp.rdo_values[gbt_channel].gbt_packer_1_monitor["STOP_TIMEOUT"]
            for count in ["VIOLATION_START","VIOLATION_ACK","VIOLATION_STOP","VIOLATION_NO_VALID_STOP","VIOLATION_NO_VALID_START","VIOLATION_EMPTY"]:
                packers_violation[1] += dp.rdo_values[gbt_channel].gbt_packer_1_monitor[count]
            packers_fifo_full[1] += dp.rdo_values[gbt_channel].gbt_packer_1_monitor["FIFO_FULL"]
            packers_fifo_overflow[1] += dp.rdo_values[gbt_channel].gbt_packer_1_monitor["FIFO_OVERFLOW"]
            th_fifo_full[1] += dp.rdo_values[gbt_channel].trigger_handler_mon['TRIGGER_FIFO_1_FULL']
            th_fifo_overflow[1] += dp.rdo_values[gbt_channel].trigger_handler_mon['TRIGGER_FIFO_1_OVERFLOW']

            rm_fero_okay = dp.rdo_values[gbt_channel].readout_master_status["FERO_OKAY"]
            rm_no_pdp = dp.rdo_values[gbt_channel].readout_master_status["NO_PENDING_DETECTOR_DATA"]
            rm_no_plp = dp.rdo_values[gbt_channel].readout_master_status["NO_PENDING_LANE_DATA"]
            rm_nok_lanes = dp.rdo_values[gbt_channel].readout_master_nok_lanes
            rm_faulty_lanes = dp.rdo_values[gbt_channel].readout_master_faulty_lanes

            if  self.config.LAYER in [testbench.LayerList.INNER, testbench.LayerList.NO_PT100]:
                sop_cntr_packers += dp.rdo_values[gbt_channel].gbt_packer_2_monitor["SOP_SENT"]
                eop_cntr_packers += dp.rdo_values[gbt_channel].gbt_packer_2_monitor["EOP_SENT"]
                packet_done[2] += dp.rdo_values[gbt_channel].gbt_packer_2_monitor["PACKET_DONE"]
                packers_timeout[2] += dp.rdo_values[gbt_channel].gbt_packer_2_monitor["PACKET_TIMEOUT"]
                packers_timeout_trigger_to_start[2] += dp.rdo_values[gbt_channel].gbt_packer_2_monitor["START_TIMEOUT"]
                packers_timeout_idle[2] += dp.rdo_values[gbt_channel].gbt_packer_2_monitor["IDLE_TIMEOUT"]
                packers_timeout_start_to_stop[2] += dp.rdo_values[gbt_channel].gbt_packer_2_monitor["STOP_TIMEOUT"]
                for count in ["VIOLATION_START","VIOLATION_ACK","VIOLATION_STOP","VIOLATION_NO_VALID_STOP","VIOLATION_NO_VALID_START","VIOLATION_EMPTY"]:
                    packers_violation[2] += dp.rdo_values[gbt_channel].gbt_packer_2_monitor[count]
                packers_fifo_full[2] += dp.rdo_values[gbt_channel].gbt_packer_2_monitor["FIFO_FULL"]
                packers_fifo_overflow[2] += dp.rdo_values[gbt_channel].gbt_packer_2_monitor["FIFO_OVERFLOW"]
                th_fifo_full[2] += dp.rdo_values[gbt_channel].trigger_handler_mon['TRIGGER_FIFO_2_FULL']
                th_fifo_overflow[2] += dp.rdo_values[gbt_channel].trigger_handler_mon['TRIGGER_FIFO_2_OVERFLOW']

            if self.config.GTH_ACTIVE:
                cpll_lol = sum([counter[0]['CPLL_LOCK_LOSS'] for _, counter in dp.rdo_values[gbt_channel].lane_counters.items()])
                comma_not_aligned = sum([counter[0]['ALIGNED_LOSS'] for _, counter in dp.rdo_values[gbt_channel].lane_counters.items()])
                chip_8b10b_oot_errors = sum([counter[0]['8b10b_OOT_ERROR'] for _, counter in dp.rdo_values[gbt_channel].lane_counters.items()])
                lane_protocol_errors = sum([counter[0]['PROTOCOL_ERROR'] for _, counter in dp.rdo_values[gbt_channel].lane_counters.items()])
                detector_timeout_errors = sum([counter[0]['DETECTOR_TIMEOUT'] for _, counter in dp.rdo_values[gbt_channel].lane_counters.items()])
                lane_8b10b_oot_fatal = sum([counter[0]['u8B10B_OOT_FATAL'] for _, counter in dp.rdo_values[gbt_channel].lane_counters.items()])
                busy_count = sum([counter[0]['BUSY_EVENT'] for _, counter in dp.rdo_values[gbt_channel].lane_counters.items()])
                busy_violation = sum([counter[0]['BUSY_VIOLATION'] for _, counter in dp.rdo_values[gbt_channel].lane_counters.items()])
                chip_events = sum([counter[0]['LANE_FIFO_STOP'] for _, counter in dp.rdo_values[gbt_channel].lane_counters.items()])
                chip_events_avg = chip_events/len(self.config.READOUT_GTH_LIST)

                lane_fifo_overflow = [counter[0]['LANE_FIFO_OVERFLOW'] for _, counter in dp.rdo_values[gbt_channel].lane_counters.items()]
                lanes_timeout = [counter[0]['LANE_TIMEOUT'] for _, counter in dp.rdo_values[gbt_channel].lane_counters.items()]

            if self.config.GPIO_ACTIVE:
                chip_8b10b_oot_errors_gpio = sum([counter[0]['8b10b_OOT_ERROR'] for _, counter in dp.rdo_values[gbt_channel].lane_counters_gpio.items()])
                lane_protocol_errors_gpio = sum([counter[0]['PROTOCOL_ERROR'] for _, counter in dp.rdo_values[gbt_channel].lane_counters_gpio.items()])
                detector_timeout_errors_gpio = sum([counter[0]['DETECTOR_TIMEOUT'] for _, counter in dp.rdo_values[gbt_channel].lane_counters_gpio.items()])
                lane_8b10b_oot_fatal_gpio = sum([counter[0]['u8B10B_OOT_FATAL'] for _, counter in dp.rdo_values[gbt_channel].lane_counters_gpio.items()])
                busy_count_gpio = sum([counter[0]['BUSY_EVENT'] for lane, counter in dp.rdo_values[gbt_channel].lane_counters_gpio.items() if lane not in self.config.EXCLUDE_GPIO_LIST])
                busy_violation_gpio = sum([counter[0]['BUSY_VIOLATION'] for lane, counter in dp.rdo_values[gbt_channel].lane_counters_gpio.items() if lane not in self.config.EXCLUDE_GPIO_LIST])
                chip_events_gpio = sum([counter[0]['LANE_FIFO_STOP'] for _, counter in dp.rdo_values[gbt_channel].lane_counters_gpio.items()])
                chip_events_avg_gpio = chip_events_gpio/len(self.config.READOUT_GPIO_LIST)

                lane_fifo_overflow_gpio = [counter[0]['LANE_FIFO_OVERFLOW'] for _, counter in dp.rdo_values[gbt_channel].lane_counters_gpio.items()]
                lanes_timeout_gpio = [counter[0]['LANE_TIMEOUT'] for _, counter in dp.rdo_values[gbt_channel].lane_counters_gpio.items()]

            if any(th_fifo_overflow):
                self.read_str += '\n\tWARNING Trigger FIFO overflow:\t{0}!'.format(th_fifo_overflow)
                if final_read:
                    self.test_pass = False

            # Checks that no pending detector/lane packets are present at the END OF THE RUN
            if final_read:
                if (rm_no_pdp == 0) or (rm_no_plp == 0):
                    self.read_str += f'\n\tWARNING Readout Master not all data readout:\t(NO PDP,NO_PLP)=(1\'b{rm_no_pdp},1\'b{rm_no_plp})'
                    self.test_pass = False
            if rm_fero_okay==0:
                self.read_str += f'\n\tWARNING Readout Master FERO OKAY:\t{rm_fero_okay}'
                if final_read:
                    self.test_pass = False
            if rm_nok_lanes>0 or rm_faulty_lanes>0:
                self.read_str += f'\n\tWARNING Readout Master faulty\t{rm_faulty_lanes} or in error\t{rm_nok_lanes} lanes'
                if final_read:
                    self.test_pass = False

            if self.config.GTH_ACTIVE:
                self.read_str += f'\n\tEvents GTH:\t{chip_events}, average per chip:\t{chip_events_avg:.2f} (DetectorTimeout: {detector_timeout_errors}, ProtocolError: {lane_protocol_errors}, OotErrors: {chip_8b10b_oot_errors}, OotFatal {lane_8b10b_oot_fatal})'
                if cpll_lol:
                    err = [counter[0]['CPLL_LOCK_LOSS'] for _, counter in dp.rdo_values[gbt_channel].lane_counters.items()]
                    self.read_str += '\n\tWARNING Channel PLL lost lock per lane:\t{0}!'.format(err)
                    if final_read:
                        self.test_pass = False
                if comma_not_aligned:
                    err = [counter[0]['ALIGNED_LOSS'] for _, counter in dp.rdo_values[gbt_channel].lane_counters.items()]
                    self.read_str += '\n\tWARNING comma alignment lost lock per lane:\t{0}!'.format(err)
                    if final_read:
                        self.test_pass = False
                if chip_8b10b_oot_errors:
                    err = [counter[0]['8b10b_OOT_ERROR'] for _, counter in dp.rdo_values[gbt_channel].lane_counters.items()]
                    self.read_str += '\n\tWARNING 8b10b Out of Table per lane:\t{0}!'.format(err)
                    if final_read:
                        self.test_pass = False
                if lane_8b10b_oot_fatal:
                    err = [counter[0]['u8B10B_OOT_FATAL'] for _, counter in dp.rdo_values[gbt_channel].lane_counters.items()]
                    self.read_str += '\n\tWARNING 8b10b Out of Table FATAL per lane:\t{0}!'.format(err)
                    if final_read:
                        self.test_pass = False
                if detector_timeout_errors:
                    err = [counter[0]['DETECTOR_TIMEOUT'] for _, counter in dp.rdo_values[gbt_channel].lane_counters.items()]
                    self.read_str += '\n\tWARNING detector timeout per lane:\t{0}!'.format(err)
                    if final_read:
                        self.test_pass = False
                if busy_count:
                    err = [counter[0]['BUSY_EVENT'] for _, counter in dp.rdo_values[gbt_channel].lane_counters.items()]
                    self.read_str += '\n\tWARNING Busy chips per lane:\t\t{0}!'.format(err)
                    if final_read:
                        self.test_pass = False
                if busy_violation:
                    err = [counter[0]['BUSY_VIOLATION'] for _, counter in dp.rdo_values[gbt_channel].lane_counters.items()]
                    self.read_str += '\n\tWARNING Busy violations per lane:\t{0}!'.format(err)
                    if final_read:
                        self.test_pass = False
                if lane_fifo_overflow != len(self.config.READOUT_GTH_LIST)*[0]:
                    self.read_str += f'\n\tWARNING Lane FIFO GTH overflow:\t{lane_fifo_overflow}'
                    if final_read:
                        self.test_pass = False
                if lanes_timeout != len(self.config.READOUT_GTH_LIST)*[0]:
                    self.read_str += '\n\tWARNING Lane GTH timeout:\t{0}'.format(lanes_timeout)
                    if final_read:
                        self.test_pass = False
            if self.config.GPIO_ACTIVE:
                self.read_str += f'\n\tEvents GPIO:\t{chip_events_gpio}, average per chip:\t{chip_events_avg_gpio:.2f} (DetectorTimeout: {detector_timeout_errors_gpio}, ProtocolError: {lane_protocol_errors_gpio}, OotErrors: {chip_8b10b_oot_errors_gpio}, OotFatal {lane_8b10b_oot_fatal_gpio})'
                if chip_8b10b_oot_errors_gpio:
                    err = [counter[0]['8b10b_OOT_ERROR'] for _, counter in dp.rdo_values[gbt_channel].lane_counters_gpio.items()]
                    self.read_str += '\n\tWARNING 8b10b Out of Table per lane:\t{0}!'.format(err)
                    if final_read:
                        self.test_pass = False
                if lane_8b10b_oot_fatal_gpio:
                    err = [counter[0]['u8B10B_OOT_FATAL'] for _, counter in dp.rdo_values[gbt_channel].lane_counters_gpio.items()]
                    self.read_str += '\n\tWARNING 8b10b Out of Table FATAL per lane:\t{0}!'.format(err)
                    if final_read:
                        self.test_pass = False
                if detector_timeout_errors_gpio:
                    err = [counter[0]['DETECTOR_TIMEOUT'] for _, counter in dp.rdo_values[gbt_channel].lane_counters_gpio.items()]
                    self.read_str += '\n\tWARNING dector timeout per lane:\t{0}!'.format(err)
                    if final_read:
                        self.test_pass = False
                if busy_count_gpio:
                    err = [counter[0]['BUSY_EVENT'] for _, counter in dp.rdo_values[gbt_channel].lane_counters_gpio.items()]
                    self.read_str += '\n\tWARNING Busy chips per lane:\t\t{0}!'.format(err)
                    if final_read:
                        self.test_pass = False
                if busy_violation_gpio:
                    err = [counter[0]['BUSY_VIOLATION'] for _, counter in dp.rdo_values[gbt_channel].lane_counters_gpio.items()]
                    self.read_str += '\n\tWARNING Busy violation per lane:\t{0}!'.format(err)
                    if final_read:
                        self.test_pass = False
                if lane_fifo_overflow_gpio != len(self.config.READOUT_GPIO_LIST)*[0]:
                    self.read_str += f'\n\tWARNING Lane FIFO GPIO issue\n\toverflow:\t{lane_fifo_overflow_gpio}'
                    if final_read:
                        self.test_pass = False
                if lanes_timeout_gpio != len(self.config.READOUT_GPIO_LIST)*[0]:
                    self.read_str += '\n\tWARNING Lane GPIO timeout:\t{0}'.format(lanes_timeout_gpio)
                    if final_read:
                        self.test_pass = False

            self.read_str += f'\n\tAverage packet done:\t\t\t{sum(packet_done)/PACKERS:.2f}'
            for i in range(PACKERS):
                if packet_done[i]!=trigger_sent:
                    self.read_str += f'\n\tWARNING: GBT packer {i} PACKET_DONE:\t\t{packet_done[i]}!={trigger_sent}'
                    if final_read:
                        self.test_pass = False

            self.read_str += f'\n\tSOP:\t\t{sop_cntr},\t\tEOP:\t\t{eop_cntr}'

            if sop_cntr_packers != sop_cntr:
                self.read_str += '\n\tWARNING: SOP mismatch. Flow monitor {0} vs packer {1}'.format(sop_cntr, sop_cntr_packers)
                if final_read:
                    self.test_pass = False
            if eop_cntr_packers != eop_cntr:
                self.read_str += '\n\tWARNING: EOP mismatch. Flow monitor {0} vs packer {1}'.format(eop_cntr, eop_cntr_packers)
                if final_read:
                    self.test_pass = False
            if any(packers_timeout):
                self.read_str += f'\n\tWARNING: GBT packers timeout:\t\t{packers_timeout}'
                if final_read:
                    self.test_pass = False
                # Now verify that the indivdual timeout counters are smaller then the total timeout counter
                for i,to in enumerate(packers_timeout):
                    if packers_timeout_trigger_to_start[i] > to:
                        self.read_str += f'\n\tERROR: GBT packer {i} timeout count must be bigger or equal then the trigger_to_start one: {packers_timeout}<={packers_timeout_trigger_to_start[i]}'
                        self.test_pass = False
                    if packers_timeout_idle[i] > to:
                        self.read_str += f'\n\tERROR: GBT packer {i} timeout count must be bigger or equal then the idle one: {packers_timeout}<={packers_timeout_idle[i]}'
                        self.test_pass = False
                    if packers_timeout_start_to_stop[i] > to:
                        self.read_str += f'\n\tERROR: GBT packer {i} timeout count must be bigger or equal then the start_to_stop one: {packers_timeout}<={packers_timeout_start_to_stop[i]}'
                        self.test_pass = False
            if any(packers_violation):
                self.read_str += f'\n\tWARNING: violations in lane-gbt_packer protocol:\t\t{packers_violation}'
                if final_read:
                    self.test_pass = False
            if any(packers_fifo_full):
                self.read_str += '\n\tWARNING: GBT packers FIFO FULL:\t\t{0}'.format(packers_fifo_full)
                if final_read:
                    self.test_pass = False
            if self.config.GTH_ACTIVE:
                if sum(lanes_timeout) > 0:
                    self.read_str += '\n\tWARNING: Lane timeout:\t\t{0}'.format(lanes_timeout)
                    if final_read:
                        self.test_pass = False
            if self.config.GPIO_ACTIVE:
                if sum(lanes_timeout_gpio) > 0:
                    self.read_str += '\n\tWARNING: Lane timeout:\t\t{0}'.format(lanes_timeout_gpio)
                    if final_read:
                        self.test_pass = False
            if any(packers_fifo_overflow):
                self.read_str += '\n\tWARNING: GBT packers FIFO OVERFLOW:\t\t{0}'.format(packers_fifo_overflow)
                if final_read:
                    self.test_pass = False

            return sop_cntr, eop_cntr
        except Exception as e:
            self.logger.error(f"Could not perform all print values from {gbt_channel}")
            self.logger.info(e, exc_info=True)
            self.test_pass = False

    def print_values_cru(self, dp, sop_cntr, eop_cntr, final_read):
        """Print the values relative to the CRU"""
        try:
            assert len(sop_cntr.keys())==len(eop_cntr.keys())
            sop_cntr_tot = 0
            eop_cntr_tot = 0
            for gbt_channel in sop_cntr.keys():
                sop_cntr_tot += sop_cntr[gbt_channel]
                eop_cntr_tot += eop_cntr[gbt_channel]

            cru_dropped_packets = dp.cru_dropped_packets
            cru_total_packets = dp.cru_total_packets
            cru_last_hb_dwrapper = dp.cru_last_hb_dwrapper

            cru_rejected_packets_link = [dp.cru_datapath_counters[i]['rejected_packets'] for i in self.testbench.cru.get_data_link_list()]
            cru_accepted_packets_link = [dp.cru_datapath_counters[i]['accepted_packets'] for i in self.testbench.cru.get_data_link_list()]
            cru_forced_packets_link = [dp.cru_datapath_counters[i]['forced_packets'] for i in self.testbench.cru.get_data_link_list()]

            self.read_str += '\n\tCRU packets:\t{0},\t\tLast HB:\t\t{1}'.format(cru_total_packets, cru_last_hb_dwrapper)
            if cru_dropped_packets>0:
                self.read_str += '\n\tWARNING Dropped CRU packets:\t\t{0}'.format(cru_dropped_packets)
                if final_read:
                    self.test_pass = False
            if sum(cru_rejected_packets_link)>0:
                self.read_str += '\n\tWARNING Rejected CRU packets in link(s):\t\t{0}'.format(cru_rejected_packets_link)
                if final_read:
                    self.test_pass = False
            if sum(cru_forced_packets_link)>0:
                self.read_str += '\n\tWARNING Forced CRU packets in link(s):\t\t{0}'.format(cru_forced_packets_link)
                if final_read:
                    self.test_pass = False
            if sum(cru_accepted_packets_link)!= cru_total_packets:
                self.read_str += '\n\tWARNING Accepted CRU packets in link(s) not match :\t{0}\t\t\t{1}'.format(cru_accepted_packets_link, cru_total_packets)
                if final_read:
                    self.test_pass = False
            if cru_total_packets != sop_cntr_tot:
                self.read_str += '\n\tWARNING Accepted CRU total packets and SOP do not match :\t{0}\t{1}'.format(cru_total_packets, sop_cntr_tot)
                self.read_str += '\n\tWARNING Accepted CRU total packets and EOP do not match :\t{0}\t{1}'.format(cru_total_packets, eop_cntr_tot)
                if final_read:
                    self.test_pass = False
        except Exception as e:
            self.logger.error(f"Could not perform all print values from cru")
            self.logger.info(e, exc_info=True)
            self.test_pass = False

    def print_values_pu(self, dp, gbt_channel):
        """Print the values relative to the PU"""
        if not self.config.DRY:
            try:
                if self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.POWERUNIT:
                    for rdo in self.testbench.rdo_list:
                        for module in self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST:
                            powerunit_av = rdo.powerunit_1._code_to_vpower(dp.rdo_values[gbt_channel].powerunit1_values['module_{0}_avdd_voltage'.format(module)])
                            powerunit_ai = rdo.powerunit_1._code_to_i(dp.rdo_values[gbt_channel].powerunit1_values['module_{0}_avdd_current'.format(module)])
                            powerunit_dv = rdo.powerunit_1._code_to_vpower(dp.rdo_values[gbt_channel].powerunit1_values['module_{0}_dvdd_voltage'.format(module)])
                            powerunit_di = rdo.powerunit_1._code_to_i(dp.rdo_values[gbt_channel].powerunit1_values['module_{0}_dvdd_current'.format(module)])
                            self.read_str += '\n\tPowerunit on ch {4}: avdd {0:.2f} V, {1:.2f} mA, dvdd {2:.2f} V, {3:.2f} mA'.format(powerunit_av,powerunit_ai,powerunit_dv,powerunit_di, rdo.get_gbt_channel())
                elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.DUAL_POWERUNIT:
                    for rdo in self.testbench.rdo_list:
                        for module in self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST:
                            powerunit_av = rdo.powerunit_1._code_to_vpower(dp.rdo_values[gbt_channel].powerunit1_values['module_{0}_avdd_voltage'.format(module)])
                            powerunit_ai = rdo.powerunit_1._code_to_i(dp.rdo_values[gbt_channel].powerunit1_values['module_{0}_avdd_current'.format(module)])
                            powerunit_dv = rdo.powerunit_1._code_to_vpower(dp.rdo_values[gbt_channel].powerunit1_values['module_{0}_dvdd_voltage'.format(module)])
                            powerunit_di = rdo.powerunit_1._code_to_i(dp.rdo_values[gbt_channel].powerunit1_values['module_{0}_dvdd_current'.format(module)])
                            self.read_str += '\n\tPowerunit 1 on ch {4}: avdd {0:.2f} V, {1:.2f} mA, dvdd {2:.2f} V, {3:.2f} mA'.format(powerunit_av,powerunit_ai,powerunit_dv,powerunit_di, rdo.get_gbt_channel())
                        t_int = dp.rdo_values[gbt_channel].powerunit1_pt100["PU"]
                        t_ext = dp.rdo_values[gbt_channel].powerunit1_pt100["EXT1"]
                        t_ext2 = dp.rdo_values[gbt_channel].powerunit1_pt100["EXT2"]
                        self.read_str += '\n\tPowerunit 1 on ch {3}: {0:.2f} C, {1:.2f} C, {2:.2f} C'.format(t_int, t_ext, t_ext2, rdo.get_gbt_channel())
                        for module in self.config.POWER_UNIT_2_OUTPUT_CHANNEL_LIST:
                            powerunit_av = rdo.powerunit_2._code_to_vpower(dp.rdo_values[gbt_channel].powerunit2_values['module_{0}_avdd_voltage'.format(module)])
                            powerunit_ai = rdo.powerunit_2._code_to_i(dp.rdo_values[gbt_channel].powerunit2_values['module_{0}_avdd_current'.format(module)])
                            powerunit_dv = rdo.powerunit_2._code_to_vpower(dp.rdo_values[gbt_channel].powerunit2_values['module_{0}_dvdd_voltage'.format(module)])
                            powerunit_di = rdo.powerunit_2._code_to_i(dp.rdo_values[gbt_channel].powerunit2_values['module_{0}_dvdd_current'.format(module)])
                            self.read_str += '\n\tPowerunit 2 on ch {4}: avdd {0:.2f} V, {1:.2f} mA, dvdd {2:.2f} V, {3:.2f} mA'.format(powerunit_av,powerunit_ai,powerunit_dv,powerunit_di, rdo.get_gbt_channel())
                        t_int = dp.rdo_values[gbt_channel].powerunit2_pt100["PU"]
                        t_ext = dp.rdo_values[gbt_channel].powerunit2_pt100["EXT1"]
                        t_ext2 = dp.rdo_values[gbt_channel].powerunit2_pt100["EXT2"]
                        self.read_str += '\n\tPowerunit 2 on ch {3}: {0:.2f} C, {1:.2f} C, {2:.2f} C'.format(t_int, t_ext, t_ext2, rdo.get_gbt_channel())
                elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.MONITOR and self.config.LAYER in [testbench.LayerList.INNER, testbench.LayerList.NO_PT100]:
                    for rdo in self.testbench.rdo_list:
                        for module in [0]:
                            powerunit_av = rdo.powerunit_1._code_to_vpower(dp.rdo_values[gbt_channel].powerunit1_values['module_{0}_avdd_voltage'.format(module)])
                            powerunit_ai = rdo.powerunit_1._code_to_i(dp.rdo_values[gbt_channel].powerunit1_values['module_{0}_avdd_current'.format(module)])
                            powerunit_dv = rdo.powerunit_1._code_to_vpower(dp.rdo_values[gbt_channel].powerunit1_values['module_{0}_dvdd_voltage'.format(module)])
                            powerunit_di = rdo.powerunit_1._code_to_i(dp.rdo_values[gbt_channel].powerunit1_values['module_{0}_dvdd_current'.format(module)])
                            self.read_str += '\n\tRU {4:2} Powerunit 1: avdd {0:.2f} V, {1:.2f} mA, dvdd {2:.2f} V, {3:.2f} mA'.format(powerunit_av,powerunit_ai,powerunit_dv,powerunit_di, rdo.get_gbt_channel())
                        t_int = dp.rdo_values[gbt_channel].powerunit1_pt100["PU"]
                        t_ext = dp.rdo_values[gbt_channel].powerunit1_pt100["EXT1"]
                        self.read_str += '\n\tRU {2:2} Powerunit 1: {0:.2f} C, {1:.2f} C'.format(t_int, t_ext, rdo.get_gbt_channel())
                elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.MONITOR and self.config.LAYER == testbench.LayerList.MIDDLE:
                    for rdo in self.testbench.rdo_list:
                        for module in [0,1,2,3,4,5,6,7]:
                            powerunit_av = rdo.powerunit_1._code_to_vpower(dp.rdo_values[gbt_channel].powerunit1_values['module_{0}_avdd_voltage'.format(module)])
                            powerunit_ai = rdo.powerunit_1._code_to_i(dp.rdo_values[gbt_channel].powerunit1_values['module_{0}_avdd_current'.format(module)])
                            powerunit_dv = rdo.powerunit_1._code_to_vpower(dp.rdo_values[gbt_channel].powerunit1_values['module_{0}_dvdd_voltage'.format(module)])
                            powerunit_di = rdo.powerunit_1._code_to_i(dp.rdo_values[gbt_channel].powerunit1_values['module_{0}_dvdd_current'.format(module)])
                            self.read_str += '\n\tPowerunit 1 on ch {4}: avdd {0:.2f} V, {1:.2f} mA, dvdd {2:.2f} V, {3:.2f} mA'.format(powerunit_av,powerunit_ai,powerunit_dv,powerunit_di, rdo.get_gbt_channel())
                        t_int = dp.rdo_values[gbt_channel].powerunit1_pt100["PU"]
                        t_ext1 = dp.rdo_values[gbt_channel].powerunit1_pt100["EXT1"]
                        t_ext2 = dp.rdo_values[gbt_channel].powerunit1_pt100["EXT2"]
                        self.read_str += '\n\tRU {3:2} Powerunit 1: {0:.2f} C, {1:.2f} C, {2:.2f} C'.format(t_int, t_ext1, t_ext2, rdo.get_gbt_channel())
                elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.MONITOR and self.config.LAYER == testbench.LayerList.OUTER:
                    for rdo in self.testbench.rdo_list:
                        for module in self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST:
                            powerunit_av = rdo.powerunit_1._code_to_vpower(dp.rdo_values[gbt_channel].powerunit1_values['module_{0}_avdd_voltage'.format(module)])
                            powerunit_ai = rdo.powerunit_1._code_to_i(dp.rdo_values[gbt_channel].powerunit1_values['module_{0}_avdd_current'.format(module)])
                            powerunit_dv = rdo.powerunit_1._code_to_vpower(dp.rdo_values[gbt_channel].powerunit1_values['module_{0}_dvdd_voltage'.format(module)])
                            powerunit_di = rdo.powerunit_1._code_to_i(dp.rdo_values[gbt_channel].powerunit1_values
                                                                      ['module_{0}_dvdd_current'.format(module)])
                            self.read_str += '\n\tRU {4:2} Powerunit 1: avdd {0:.2f} V, {1:.2f} mA, dvdd {2:.2f} V, {3:.2f} mA'.format(powerunit_av,powerunit_ai,powerunit_dv,powerunit_di, rdo.get_gbt_channel())
                        t_int = dp.rdo_values[gbt_channel].powerunit1_pt100["PU"]
                        t_ext = dp.rdo_values[gbt_channel].powerunit1_pt100["EXT1"]
                        self.read_str += '\n\tRU {2:2} Powerunit 1: {0:.2f} C, {1:.2f} C'.format(t_int, t_ext, rdo.get_gbt_channel())
                        for module in self.config.POWER_UNIT_2_OUTPUT_CHANNEL_LIST:
                            powerunit_av = rdo.powerunit_2._code_to_vpower(dp.rdo_values[gbt_channel].powerunit2_values['module_{0}_avdd_voltage'.format(module)])
                            powerunit_ai = rdo.powerunit_2._code_to_i(dp.rdo_values[gbt_channel].powerunit2_values['module_{0}_avdd_current'.format(module)])
                            powerunit_dv = rdo.powerunit_2._code_to_vpower(dp.rdo_values[gbt_channel].powerunit2_values['module_{0}_dvdd_voltage'.format(module)])
                            powerunit_di = rdo.powerunit_2._code_to_i(dp.rdo_values[gbt_channel].powerunit2_values['module_{0}_dvdd_current'.format(module)])
                            self.read_str += '\n\tRU {4:2} Powerunit 2: avdd {0:.2f} V, {1:.2f} mA, dvdd {2:.2f} V, {3:.2f} mA'.format(powerunit_av,powerunit_ai,powerunit_dv,powerunit_di, rdo.get_gbt_channel())
                        t_int = dp.rdo_values[gbt_channel].powerunit2_pt100["PU"]
                        t_ext = dp.rdo_values[gbt_channel].powerunit2_pt100["EXT1"]
                        self.read_str += '\n\tRU {2:2} Powerunit 2: {0:.2f} C, {1:.2f} C'.format(t_int, t_ext, rdo.get_gbt_channel())
                elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.NONE:
                    # Power Not Handled
                    pass
                else:
                    raise NotImplementedError
            except Exception as e:
                self.logger.error(f"Could not perform all print values from pu on {gbt_channel}")
                self.logger.info(e, exc_info=True)
                self.test_pass = False

    def print_values_pa3(self, dp, gbt_channel):
        """Print the values relative to the PA3"""
        try:
            if self.config.PA3_READ_VALUES:
                scrub_cycles = dp.rdo_values[gbt_channel].pa3_values['CC_SCRUB_CNT']
                scrub_crc = dp.rdo_values[gbt_channel].pa3_values['CC_SCRUB_CRC']
                self.read_str += '\n\tPA3 on {2}: Scrub cycles: {0}, CRC: 0x{1:08X}'.format(scrub_cycles, scrub_crc, gbt_channel)
            else:
                scrub_cycles = 0
        except Exception as e:
            self.logger.error(f"Could not perform all print values from pa3 on {gbt_channel}")
            self.logger.info(e, exc_info=True)

    def print_values(self, last_read, dp, force_complete_print=False, final_read=False):
        try:
            self.read_str = "Read Values"

            sop_cntr = {}
            eop_cntr = {}
            for gbt_channel in dp.rdo_values.keys():
                self.read_str +='\n\tRU {0}'.format(gbt_channel)
                self.print_values_ru_trigger(dp=dp,
                                             gbt_channel=gbt_channel,
                                             final_read=final_read)
                sop_cntr[gbt_channel], eop_cntr[gbt_channel] = self.print_values_ru_lanes(dp=dp,
                                                                                          gbt_channel=gbt_channel,
                                                                                          final_read=final_read)

            #self.print_values_cru(dp=dp,
            #                      sop_cntr=sop_cntr,
            #                      eop_cntr=eop_cntr,
            #                      final_read=final_read)
            self.print_values_pu(dp=dp,
                                 gbt_channel=gbt_channel)
            for gbt_channel in dp.rdo_values.keys():
                self.print_values_pa3(dp=dp,
                                      gbt_channel=gbt_channel)

            if self.tot_read_counter == 0 or force_complete_print:
                self.logger.info(self.read_str + "\n\tDone (in %.2f ms)", (time.time() - last_read)*1000)

            self.tot_read_counter += 1
            if self.tot_read_counter == 5:
                self.tot_read_counter = 0

        except Exception as e:
            self.logger.error("Could not perform all print values")
            self.logger.info(e, exc_info=True)
            self.test_pass = False

    def read_values(self, recordPrefetch=False, final_read=False):
        """Collect Values to read"""
        dp = DataPoint()
        try:
            dp.timestamp = time.time()
            # if recordPrefetch:
            #     self.testbench.comm_cru.start_recording()
            # else:
            #     self.testbench.comm_cru.load_sequence(self.sequence_cru)
            #     self.testbench.comm_cru.prefetch()

            self.logger.debug(f"Reading from RDOs {self.testbench.rdo_list}")
            for rdo in self.testbench.rdo_list:
                self.rdo_reads(dp=dp, rdo=rdo)
            self.cru_reads(dp)

            # if recordPrefetch:
            #     self.sequence_cru = self.testbench.comm_cru.stop_recording()
            # if recordPrefetch:
            #     self.sequence_rdo = self.testbench.comm_rdo.stop_recording()
        except:
            #self.testbench.comm_cru.stop_prefetch_mode(checkEmpty=False)
            raise
        finally:
            self.save_datapoint(dp)
            #self.testbench.comm_cru.stop_prefetch_mode(checkEmpty=True)

        if final_read:
            final_counters = self.get_final_counters(dp)
            self.final_counter_file.write(jsonpickle.encode(final_counters))
            self.final_counter_file.close()

        return dp

    def get_final_counters(self, datapoint):
        final_counters = {}
        #deployment test runs separate instance of daq test for each rdo
        gbt_channel = self.testbench.rdo_list[0].get_gbt_channel()
        #as this test will fail if trigger handler triggers sent doesnt match alpide control, no sense in using both
        final_counters['TRIGGERS_SENT'] = datapoint.rdo_values[gbt_channel].trigger_handler_mon['TRIGGER_SENT']
        final_counters['TRIGGERS_ECHOED'] = datapoint.rdo_values[gbt_channel].trigger_handler_mon['TRIGGER_ECHOED']

        #again the test will fail if this isn't = GBT packer sop/eop
        sop_cntr = 0
        eop_cntr = 0
        sop_cntr += datapoint.rdo_values[gbt_channel].gbtx_flow_monitor_counters['UPLINK0_SOP']
        eop_cntr += datapoint.rdo_values[gbt_channel].gbtx_flow_monitor_counters['UPLINK0_EOP']
        sop_cntr += datapoint.rdo_values[gbt_channel].gbtx_flow_monitor_counters['UPLINK1_SOP']
        eop_cntr += datapoint.rdo_values[gbt_channel].gbtx_flow_monitor_counters['UPLINK1_EOP']
        sop_cntr += datapoint.rdo_values[gbt_channel].gbtx_flow_monitor_counters['UPLINK2_SOP']
        eop_cntr += datapoint.rdo_values[gbt_channel].gbtx_flow_monitor_counters['UPLINK2_EOP']

        final_counters['EOP'] = sop_cntr
        final_counters['SOP'] = eop_cntr

        final_counters['CRU_PACKETS'] = datapoint.cru_total_packets
        final_counters['LAST_HB'] = datapoint.cru_last_hb_dwrapper

        return final_counters

    def create_datafile(self):
        self.logger.debug("creating datafile at {0}".format(self.datafilepath))
        self.datafile = open(self.datafilepath,'w')
        assert self.datafile, "{0} could not be created".format(self.datafilepath)
        self.datafile.write('[')

    def create_final_counter_file(self):
        self.logger.debug(f"creating final counter file at {self.final_counter_filepath}")
        self.final_counter_file = open(self.final_counter_filepath, 'w')
        assert self.final_counter_file, "{0} could not be created".format(self.final_counter_filepath)

    def save_datapoint(self, dp):
        if not os.path.isfile(self.datafilepath):
            self.create_datafile()
        else:
            self.datafile.write(',')
        self.datafile.write(jsonpickle.encode(dp))
        self.datafile.flush()

    def readback_sensors(self, filename):
        """Tries to readout the data at the end of the DAQ run"""
        if self.config.READOUT_SOURCE == 'NONE':
            return
        dp = DataPoint()
        dp.timestamp = time.time()
        for rdo in self.testbench.rdo_list:
            rdo_filename = filename + f"_{rdo.get_gbt_channel()}.json"
            try:
                start = time.time()
                if self.config.GTH_ACTIVE:
                    self.sensor_reads(dp=dp, rdo=rdo)
                elif self.config.GPIO_ACTIVE:
                    self.logger.setLevel(logging.FATAL) # prevents logging of readout errors for inactive chips
                    self.sensor_reads_ob_stave(dp=dp, rdo=rdo)
                    self.logger.setLevel(logging.INFO)
                with open(os.path.join(self.logdir, rdo_filename), 'w') as df:
                    df.write(jsonpickle.encode(dp))
                    df.flush()
                end = time.time()
                self.logger.info("ALPIDE readback stored to %s, duration: %.2f s", rdo_filename, end-start)
            except Exception as e:
                self.logger.error("Could not perform ALPIDE readback. File %s may be not written", rdo_filename)
                self.logger.info(e,exc_info=True)
                self.test_pass = False

    def readback_drp(self, filename):
        for rdo in self.testbench.rdo_list:
            try:
                start = time.time()
                rdo_filename = filename + "_" + rdo.get_gbt_channel() + '.json'
                #rb = rdo.gth.readback_common_drp()
                #with open(os.path.join(self.logdir, rdo_filename),'w') as df:
                #    df.write(jsonpickle.encode(rb))
                #    df.flush()
                rb = rdo.gth.readback_all_channel_drp()
                with open(os.path.join(self.logdir, rdo_filename),'a') as df:
                    df.write(jsonpickle.encode(rb))
                    df.flush()
                end = time.time()
                self.logger.info("DRP readback stored to %s, duration: %.2f s", rdo_filename, end-start)
            except Exception as e:
                self.logger.error("Could not perform DRP readback. File %s may be not written", rdo_filename)
                self.logger.info(e,exc_info=True)
                self.test_pass = False

    def stop(self):
        if self.datafile:
            self.datafile.write(']')
            self.datafile.flush()
            os.fsync(self.datafile.fileno())
            self.datafile.close()

        self.testbench.stop()
        if self.readout_process:
            self.readout_process.send_signal(signal.SIGINT)
            readout_stdout = ''
            self.logger.info('o2-readout-exe output: (and error if any)\n')
            for line in self.readout_process.stdout:
                readout_stdout += '\t'+line
            self.logger.info(readout_stdout)
            readout_stderr = ''
            for line in self.readout_process.stderr:
                readout_stderr += '\t'+line
            if readout_stderr != '':
                self.logger.error(readout_stderr)
                self.test_pass = False
            if self.readout_process.stdin:
                self.readout_process.stdin.close()
            time.sleep(2)

        for dma_count,fdaq_dma_proc in enumerate(self.fdaq_process):
            if fdaq_dma_proc is not None:
                readout_stdout = '\n'
                for line in fdaq_dma_proc.stdout:
                    readout_stdout += '\t'+line
                self.logger.info(f"\'fdaq {dma_count}\' output: (and error if any)\n%s", readout_stdout)
                readout_stderr = ''
                for line in fdaq_dma_proc.stderr:
                    readout_stderr += '\t'+line
                if readout_stderr != '':
                    self.logger.error(readout_stderr)
                    self.test_pass = False
                if fdaq_dma_proc.stdin:
                    fdaq_dma_proc.stdin.close()
            time.sleep(2)

    def send_stimuli(self):
        """In main loop, send stimuli to board (run each time main loop)"""
        stop = False
        if self.config.TRIGGERING_MODE in [RuTriggeringMode.CONTINUOUS,
                                           RuTriggeringMode.PERIODIC,
                                           RuTriggeringMode.DUMMY_CONTINUOUS,
                                           RuTriggeringMode.PERIODIC_LIMITED,
                                           RuTriggeringMode.TRIGGERED_SEQ,
                                           RuTriggeringMode.MANUAL]:
            pass
        else:
            raise NotImplementedError
        return stop

    def check_status(self):
        """Check status of run. Decide if the run should stop"""
        key = heardKeypress()
        if key == 'q':
            raise KeyboardInterrupt()
        elif key == 'r':
            self.logger.info("Reset datamon counters")
            for rdo in self.testbench.rdo_list:
                rdo.datapath_monitor_ib.reset_all_counters()
        elif key == 'p':
            input("Script pause: press any key [and press enter] to continue")
        elif key == 's':
            for rdo in self.testbench.rdo_list:
                rdo.pa3.config_controller.stop_blind_scrubbing()
            input("Script (and pa3 scrubbing) pause: press any key [and press enter] to continue")
            for rdo in self.testbench.rdo_list:
                rdo.pa3.config_controller.start_blind_scrubbing()
        return True

    def setup_logging(self, main=True, prefix=""):
        # Logging folder
        self.logdir = os.path.join(
            os.getcwd(),
            'logs/' + prefix + datetime.now().strftime('%Y_%m_%d_%H_%M_%S_%f'))
        os.makedirs(self.logdir)

        self.datafilepath = os.path.join(self.logdir,'read_values.json')
        self.final_counter_filepath = os.path.join(os.getcwd(), 'logs', 'final_counters.json')
        self.testrun_exit_status_info = os.path.join(self.logdir,'exit_status.json')

        runlog = os.path.join(os.getcwd(),'logs/runlog.txt')

        # setup logging
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        log_file = os.path.join(self.logdir, "daq_test.log")
        log_file_errors = os.path.join(self.logdir,
                                       "daq_test_errors.log")

        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)

        fh2 = logging.FileHandler(log_file_errors)
        fh2.setLevel(logging.ERROR)

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        formatter = logging.Formatter("[%(asctime)s]    %(levelname)-10s %(name)-28s %(message)s")

        def fmt_filter(record):
            record.levelname = f"[{record.levelname}]"
            record.name = f"[{record.name}]"
            return True

        fh.setFormatter(formatter)
        fh2.setFormatter(formatter)
        ch.setFormatter(formatter)
        fh.addFilter(fmt_filter) # Adds filter on all handlers

        if main:
            logger.addHandler(fh)
            logger.addHandler(fh2)
            logger.addHandler(ch)

        self.logger = logging.getLogger("run_info")
        rfh = logging.FileHandler(runlog)
        rfh.setLevel(logging.INFO)
        rfh.setFormatter(formatter)
        self.logger.addHandler(rfh)

        self.create_final_counter_file()

    def trigger_start(self):
        """Function executed to start the triggering mechanism"""
        if self.config.TRIGGER_SOURCE == trigger_handler.TriggerSource.GBTx2:
            if self.config.TRIGGERING_MODE == RuTriggeringMode.CONTINUOUS:
                if self.config.USE_LTU:
                    self.testbench.ltu.enable_ferst()
                    self.testbench.ltu.send_soc()
                else:
                    self.testbench.cru.send_soc()
            elif self.config.TRIGGERING_MODE in [RuTriggeringMode.PERIODIC,
                                                 RuTriggeringMode.DUMMY_CONTINUOUS,
                                                 RuTriggeringMode.PERIODIC_LIMITED]:
                if self.config.USE_LTU:
                    self.testbench.ltu.enable_ferst()
                    self.testbench.ltu.send_sot(periodic_triggers=True)
                else:
                    self.testbench.cru.send_sot(periodic_triggers=True)
            elif self.config.TRIGGERING_MODE == RuTriggeringMode.MANUAL:
                if self.config.USE_LTU:
                    self.testbench.ltu.send_sot(periodic_triggers=False)
                else:
                    self.testbench.cru.send_sot(periodic_triggers=False)
            else:
                raise NotImplementedError
        elif self.config.TRIGGER_SOURCE == trigger_handler.TriggerSource.SEQUENCER:
            for rdo in self.testbench.rdo_list:
                rdo.trigger_handler.sequencer_start()
        else:
            raise NotImplementedError

    def trigger_stop(self):
        """Function executed to terminate the triggering mechanism"""
        if self.config.TRIGGER_SOURCE == trigger_handler.TriggerSource.GBTx2:
            if self.config.TRIGGERING_MODE == RuTriggeringMode.CONTINUOUS:
                if self.config.USE_LTU:
                    self.testbench.ltu.send_eoc()
                else:
                    self.testbench.cru.send_eoc()
            elif self.config.TRIGGERING_MODE in [RuTriggeringMode.PERIODIC,
                                                 RuTriggeringMode.DUMMY_CONTINUOUS,
                                                 RuTriggeringMode.PERIODIC_LIMITED,
                                                 RuTriggeringMode.MANUAL]:
                if self.config.USE_LTU:
                    self.testbench.ltu.send_eot()
                else:
                    self.testbench.cru.send_eot()
            else:
                raise NotImplementedError
        elif self.config.TRIGGER_SOURCE == trigger_handler.TriggerSource.SEQUENCER:
            for rdo in self.testbench.rdo_list:
                rdo.trigger_handler.sequencer_stop()
        else:
            raise NotImplementedError

    def start_run(self, rcs=False, ltu_master=False):
        """Starts the DAQ and sends the SOx"""
        if not rcs:
            self.trigger_start()
        else:
            if ltu_master:
                self.trigger_start()

    def stop_run(self, rcs=False, ltu_master=False):
        """Sends the EOx, disable the data forward and interrupts the DAQ in the CRU"""
        if not rcs:
            self.trigger_stop()
        else:
            if ltu_master:
                self.trigger_stop()

        time.sleep(5) # waits for the data to be received
        for rdo in self.testbench.rdo_list:
            rdo.gth.enable_data(enable=False)
            rdo.gpio.enable_data(enable=False)
        self.logger.info("Reading one last time")
        last_read = time.time()
        dp = self.read_values(recordPrefetch=False, final_read=True)
        self.print_values(last_read, dp, force_complete_print=True, final_read=True)
        self.readback_sensors('sensors_end_of_run')
        time.sleep(1)

    def setup_power(self):
        """Setups the power accordingly to the powering method selected"""
        if not self.config.DRY:
            if self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.POWERUNIT:
                self.setup_powerunit()
                self.logger.info("Stopping clock propagation")
                for rdo in self.testbench.rdo_list:
                    rdo.alpide_control.disable_dclk()
                for rdo in self.testbench.rdo_list:
                    rdo.powerunit_1.power_on_modules(module_list=self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST,
                                                 backbias_en=self.config.BB_ENABLE)
                time.sleep(0.1)
                for rdo in self.testbench.rdo_list:
                    rdo.powerunit_1.log_values_modules(module_list=self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST)
                self.logger.info("Propagating clock")
                for rdo in self.testbench.rdo_list:
                    rdo.alpide_control.enable_dclk()
                time.sleep(0.1)
                for rdo in self.testbench.rdo_list:
                    rdo.powerunit_1.log_values_modules(module_list=self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST)
            elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.DUAL_POWERUNIT:
                self.setup_powerunit()
                self.logger.info("Stopping clock propagation")
                for rdo in self.testbench.rdo_list:
                    rdo.alpide_control.disable_dclk()
                for rdo in self.testbench.rdo_list:
                    rdo.powerunit_1.power_on_modules(module_list=self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST,
                                                 backbias_en=self.config.BB_ENABLE)
                    rdo.powerunit_2.power_on_modules(module_list=self.config.POWER_UNIT_2_OUTPUT_CHANNEL_LIST,
                                                 backbias_en=self.config.BB_ENABLE)
                    rdo.powerunit_1.log_values_modules(module_list=self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST)
                    rdo.powerunit_2.log_values_modules(module_list=self.config.POWER_UNIT_2_OUTPUT_CHANNEL_LIST)
                self.logger.info("Propagating clock")
                for rdo in self.testbench.rdo_list:
                    dclk_phase = 0
                    rdo.alpide_control.enable_dclk(phase=dclk_phase)
                for rdo in self.testbench.rdo_list:
                    rdo.powerunit_1.log_values_modules(module_list=self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST)
                    rdo.powerunit_2.log_values_modules(module_list=self.config.POWER_UNIT_2_OUTPUT_CHANNEL_LIST)
            elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.MONITOR and self.config.LAYER in [testbench.LayerList.INNER, testbench.LayerList.NO_PT100]:
                for rdo in self.testbench.rdo_list:
                    rdo.powerunit_1.log_values_modules(module_list=[0])
            elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.MONITOR and self.config.LAYER == testbench.LayerList.MIDDLE:
                for rdo in self.testbench.rdo_list:
                    rdo.powerunit_1.log_values_modules(module_list=[0,1,2,3,4,5,6,7])
            elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.MONITOR and self.config.LAYER == testbench.LayerList.OUTER:
                for rdo in self.testbench.rdo_list:
                    rdo.powerunit_1.log_values_modules(module_list=self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST)
                    rdo.powerunit_2.log_values_modules(module_list=self.config.POWER_UNIT_2_OUTPUT_CHANNEL_LIST)
            elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.NONE:
                # Power Not Handled
                pass
            else:
                raise NotImplementedError

    def get_excluded_chip_list_from_config(self, rdo, silent=False):
        gbt_channel = rdo.get_gbt_channel()
        stave_number = self.testbench.get_stave_number(gbt_channel=gbt_channel)
        excluded_chipid_ext = []
        if stave_number in self.config.staves:
            if 'excluded-chips' in self.config.staves[stave_number]:
                excluded_chipid_ext = self.config.staves[stave_number]['excluded-chips']
            else:
                if not silent:
                    self.logger.warning(f"stave {stave_number} has no excluded-chips")
        else:
            if not silent:
                self.logger.warning(f"Stave {stave_number} not in {self.config.staves}")
        if not silent: self.logger.info(f"Stave {stave_number}, excluded chipid from config: {excluded_chipid_ext}")
        return excluded_chipid_ext

    def configure_chips_from_config(self, rdo):
        gbt_channel = rdo.get_gbt_channel()
        stave_number = self.testbench.get_stave_number(gbt_channel=gbt_channel)
        if stave_number in self.config.staves:
            if 'chip' in self.config.staves[stave_number]:
                for chip in self.config.staves[stave_number]['chip']:
                    if 'registers' in self.config.staves[stave_number]['chip'][chip]:
                        driver_dac=self.config.SENSOR_DRIVER_DAC
                        pre_dac=self.config.SENSOR_PRE_DAC
                        pll_dac=self.config.SENSOR_PLL_DAC
                        if 'DriverDAC' in self.config.staves[stave_number]['chip'][chip]['registers']:
                            driver_dac = self.config.staves[stave_number]['chip'][chip]['registers']['DriverDAC']
                        if 'PreDAC' in self.config.staves[stave_number]['chip'][chip]['registers']:
                            pre_dac = self.config.staves[stave_number]['chip'][chip]['registers']['PreDAC']
                            self.testbench.setup_dtu_dacs_single_sensor(driver_dac=driver_dac, chipid=chip, rdo=rdo)
                        if 'PllDAC' in self.config.staves[stave_number]['chip'][chip]['registers']:
                            pll_dac = self.config.staves[stave_number]['chip'][chip]['registers']['PllDAC']
                        self.testbench.setup_dtu_dacs_single_sensor(driver_dac=driver_dac, pre_dac=pre_dac, pll_dac=pll_dac, chipid=chip, rdo=rdo)

    def setup_sensors(self):
        """All the chip configuration, but the setting in TRIGGERED MODE shall be done HERE."""
        # From setup_datapath_gth
        if self.config.DRY:
            pass
        else:
            for rdo in self.testbench.rdo_list:
                if self.config.GTH_ACTIVE:
                    self.testbench.setup_sensors(mode=ModeControlChipModeSelector.CONFIGURATION,
                                                 LinkSpeed=self.config.LINK_SPEED,
                                                 enable_strobe_generation=0,
                                                 pattern=self.config.SENSOR_PATTERN,
                                                 driver_dac=self.config.SENSOR_DRIVER_DAC,
                                                 pre_dac=self.config.SENSOR_PRE_DAC,
                                                 pll_dac=self.config.SENSOR_PLL_DAC,
                                                 enable_clock_gating=self.config.SENSOR_CLOCK_GATING,
                                                 enable_skew_start_of_readout=self.config.SENSOR_SKEW_START_OF_READOUT,
                                                 enable_clustering=self.config.SENSOR_CLUSTERING,
                                                 disable_manchester=self.config.DISABLE_MANCHESTER,
                                                 analogue_pulsing=self.config.ANALOGUE_PULSING,
                                                 pulse2strobe=self.config.PULSE_TO_STROBE,
                                                 rdo=rdo)
                    # Now do v-drop compensation twice:
                    if self.config.COMPENSATE_VOLTAGE_DROP:
                        self.testbench.compensate_voltage_drop_ib_stave(dvdd_set=self.config.SENSOR_DVDD,
                                                                        avdd_set=self.config.SENSOR_AVDD, rdo=rdo)
                        time.sleep(0.5)
                        self.testbench.compensate_voltage_drop_ib_stave(dvdd_set=self.config.SENSOR_DVDD,
                                                                        avdd_set=self.config.SENSOR_AVDD, rdo=rdo)
                        time.sleep(0.5)

                # From setup_datapath_gpio
                if self.config.GPIO_ACTIVE:
                    bad_dcols = self.get_bad_double_columns(rdo)
                    bad_pixels = self.get_bad_pixels(rdo)
                    excluded_chipid_ext = self.get_excluded_chip_list_from_config(rdo=rdo)
                    self.testbench.setup_sensors_ob_stave(mode=ModeControlChipModeSelector.CONFIGURATION,
                                                          module_list_lower=self.config.OB_LOWER_MODULES,
                                                          module_list_upper=self.config.OB_UPPER_MODULES,
                                                          excluded_chipid_ext=excluded_chipid_ext,
                                                          pattern=self.config.SENSOR_PATTERN,
                                                          driver_dac=self.config.SENSOR_DRIVER_DAC,
                                                          pre_dac=self.config.SENSOR_PRE_DAC,
                                                          pll_dac=self.config.SENSOR_PLL_DAC,
                                                          enable_clock_gating=self.config.SENSOR_CLOCK_GATING,
                                                          enable_skew_start_of_readout=self.config.SENSOR_SKEW_START_OF_READOUT,
                                                          enable_clustering=self.config.SENSOR_CLUSTERING,
                                                          only_master_chips=self.config.ONLY_MASTERS,
                                                          disable_manchester=self.config.DISABLE_MANCHESTER,
                                                          analogue_pulsing=self.config.ANALOGUE_PULSING,
                                                          enable_strobe_generation=False,
                                                          pulse2strobe=self.config.PULSE_TO_STROBE,
                                                          bad_double_columns=bad_dcols,
                                                          bad_pixels=bad_pixels,
                                                          avdd=self.config.SENSOR_AVDD,
                                                          dvdd=self.config.SENSOR_DVDD,
                                                          grst=self.config.GRST,
                                                          rdo=rdo)

                    self.set_scan_specific_registers()
                    self.configure_chips_from_config(rdo=rdo)

                    self.testbench.configure_dtu(rdo, is_on_lower_hs=True)
                    self.testbench.configure_dtu(rdo, is_on_lower_hs=False)

                    time.sleep(5)

            # From setup trigger and strobe
            for rdo in self.testbench.rdo_list:
                if self.config.TRIGGERING_MODE in [RuTriggeringMode.CONTINUOUS,
                                                   RuTriggeringMode.DUMMY_CONTINUOUS]:
                    self.testbench.setup_pulse_and_strobe_duration(pulse_duration_ns=100,
                                                                   strobe_duration_ns=25*self.config.TRIGGER_PERIOD_BC-100,
                                                                   pulse_to_strobe_duration_ns=25,
                                                                   strobe_gap_duration_ns=25,
                                                                   rdo=rdo)
                elif self.config.TRIGGERING_MODE in [RuTriggeringMode.PERIODIC,
                                                     RuTriggeringMode.PERIODIC_LIMITED,
                                                     RuTriggeringMode.TRIGGERED_SEQ,
                                                     RuTriggeringMode.MANUAL]:
                    self.testbench.setup_pulse_and_strobe_duration(pulse_duration_ns=100,
                                                                   strobe_duration_ns=self.config.TRIGGERED_STROBE_DURATION,
                                                                   pulse_to_strobe_duration_ns=25,
                                                                   strobe_gap_duration_ns=25,
                                                                   rdo=rdo)
                else:
                    raise NotImplementedError

            # callback function for scan specific alpide settings
            self.set_scan_specific_trigger_registers()

    def setup_datapath_gpio(self, detector_timeout):
        """Sets up the GPIO datapath with a IB stave connected to a GPIO readout"""
        if self.config.GPIO_ACTIVE:
            for rdo in self.testbench.rdo_list:
                rdo.gpio_subset(transceivers=self.config.READOUT_GPIO_LIST)
                rdo.lanes_ob.set_detector_timeout(detector_timeout)

                aligned = False
                retries = 0
                max_retries = 1

                while not aligned and retries <= max_retries:
                    self.logger.info(f"Scanning idelays for ob stave {rdo.get_gbt_channel()}")
                    self.testbench.scan_idelay_ob_stave(stepsize=10,
                                                        waittime=0.1,
                                                        set_optimum=True,
                                                        rdo=rdo)
                    aligned = self.testbench.setup_readout_gpio(rdo=rdo)
                    retries += 1
                if not aligned:
                    raise RuntimeError("Could not align all transceivers")
                rdo.gpio.enable_data(enable=True)

    def setup_datapath_gth(self, detector_timeout):
        """Sets up the GTH datapath"""
        if self.config.GTH_ACTIVE:
            for rdo in self.testbench.rdo_list:
                rdo.gth_subset(transceivers=self.config.READOUT_GTH_LIST)

                rdo.lanes_ib.set_detector_timeout(detector_timeout)

                aligned = self.testbench.setup_readout(rdo=rdo)
                if not aligned:

                    raise RuntimeError("Could not align all transceivers")

    def setup_gbt_packers(self):
        """Sets up the gbt packers"""
        # Default values for daq_test
        if self.config.TRIGGERING_MODE in [RuTriggeringMode.CONTINUOUS,
                                           RuTriggeringMode.DUMMY_CONTINUOUS]:
            # in 6.25 ns
            # Strobe length + some margin (to be tuned)
            timeout_to_start = 4*self.config.TRIGGER_PERIOD_BC + 1000
            #timeout_to_start = 0xFFFF # used in 167, likely needed due to broken DCTRL flushing
        elif self.config.TRIGGERING_MODE in [RuTriggeringMode.PERIODIC,
                                             RuTriggeringMode.PERIODIC_LIMITED,
                                             RuTriggeringMode.TRIGGERED_SEQ,
                                             RuTriggeringMode.MANUAL]:
            timeout_to_start = 0x0FFF # Default for daq_test
        else:
            raise NotImplementedError

        for rdo in self.testbench.rdo_list:
            rdo.gbt_packer.set_timeout_to_start(timeout_to_start)
            rdo.gbt_packer.set_timeout_start_stop(0xFFFF)
            rdo.gbt_packer.set_timeout_in_idle(0xFFFF)
        # Callback method for scan specific configurations
        self.setup_scan_specific_gbt_packer()

    def setup_scan_specific_gbt_packer(self):
        """Method designed to be overriden in daugher classes to tweak the
        configuration of the gbt_packer"""

    def setup_trigger_handler(self):
        """Sets up the trigger handler"""
        # Enable trigger handler
        for rdo in self.testbench.rdo_list:
            rdo.trigger_handler.enable()

            # Enable timebase sync independently of the
            # trigger source selected.
            rdo.trigger_handler.enable_timebase_sync()

            rdo.trigger_handler.set_trigger_delay(1) # 25 ns of delay here: restores value in case was changed by previous runs
            if self.config.LAYER in [testbench.LayerList.INNER, testbench.LayerList.NO_PT100]:
                for i in range(3):
                    rdo.trigger_handler.enable_packer(i)
            elif self.config.LAYER in [testbench.LayerList.MIDDLE, testbench.LayerList.OUTER]:
                for i in range(2):
                    rdo.trigger_handler.enable_packer(i)
                rdo.trigger_handler.disable_packer(2)
            else:
                raise NotImplementedError
            if self.config.TRIGGERING_MODE == RuTriggeringMode.CONTINUOUS:
                rdo.trigger_handler.setup_for_continuous_mode(trigger_period_bc=self.config.TRIGGER_PERIOD_BC,
                                                              send_pulses=self.config.SEND_PULSES)
            elif self.config.TRIGGERING_MODE in [RuTriggeringMode.PERIODIC,
                                                 RuTriggeringMode.PERIODIC_LIMITED,
                                                 RuTriggeringMode.DUMMY_CONTINUOUS,
                                                 RuTriggeringMode.TRIGGERED_SEQ,
                                                 RuTriggeringMode.MANUAL]:
                # minimum trigger distance 625ns = 100*6.25ns to avoid loss by alpide_control
                trigger_minimum_distance = 100
                assert trigger_minimum_distance < self.config.TRIGGER_PERIOD_BC<<2, \
                    "Trigger period {self.config.TRIGGER_PERIOD_BC*25e-9} lower than minimum distance between triggers {trigger_minimum_distance*6.25e-9}"
                rdo.trigger_handler.setup_for_triggered_mode(trigger_minimum_distance=trigger_minimum_distance,
                                                             send_pulses=self.config.SEND_PULSES)
            else:
                raise NotImplementedError

            # sets the opcode gating to test in DRY mode
            if self.config.DRY:
                rdo.trigger_handler.set_opcode_gating(True)
            else:
                rdo.trigger_handler.set_opcode_gating(False)

            # sets registers for different trigger sources, if necessary.
            # eventually sets the correct trigger source
            if self.config.TRIGGER_SOURCE == trigger_handler.TriggerSource.GBTx2:
                pass
            elif self.config.TRIGGER_SOURCE == trigger_handler.TriggerSource.SEQUENCER:
                rdo.trigger_handler.sequencer_set_number_of_hb_per_timeframe(self.config.TRIGGER_HBF_PER_TF)
                rdo.trigger_handler.sequencer_set_number_of_hba_per_timeframe(self.config.TRIGGER_HBA_PER_TF)
                rdo.trigger_handler.sequencer_set_trigger_period(self.config.TRIGGER_PERIOD_BC)
                rdo.trigger_handler.sequencer_set_trigger_mode_periodic()
                rdo.trigger_handler.disable_timebase_sync()

                # Specific configuration for sequencer modes
                if self.config.TRIGGERING_MODE == RuTriggeringMode.CONTINUOUS:
                    rdo.trigger_handler.sequencer_set_mode_continuous()
                    rdo.trigger_handler.sequencer_set_number_of_timeframes_infinite(True)
                elif self.config.TRIGGERING_MODE in [RuTriggeringMode.PERIODIC,
                                                     RuTriggeringMode.DUMMY_CONTINUOUS]:
                    rdo.trigger_handler.sequencer_set_mode_triggered()
                    rdo.trigger_handler.sequencer_set_number_of_timeframes_infinite(True)
                elif self.config.TRIGGERING_MODE in [RuTriggeringMode.TRIGGERED_SEQ]:
                    rdo.trigger_handler.sequencer_set_mode_triggered()
                    rdo.trigger_handler.sequencer_set_number_of_timeframes(self.config.TRIGGER_TF)
                else:
                    raise NotImplementedError
            rdo.trigger_handler.set_trigger_source(value=self.config.TRIGGER_SOURCE)

            # Checks if the timebase is in sync at the beginning of the run
            # In case of GBTx2 set as trigger source it MUST be in sync
            # In case of SEQUENCER as trigger source it CAN but it is not necessary
            # See point 2.2.9 of https://www.overleaf.com/read/kkzhvscdwwyg
            timebase_sync = rdo.trigger_handler.is_timebase_synced()
            msg = f"{rdo.identity.get_stave_name()} not in sync!"
            self.timebase_sync_at_start = True
            if (self.config.TRIGGER_SOURCE == trigger_handler.TriggerSource.GBTx2) & self.config.USE_GTM:
                pass  # all good here
            elif self.config.TRIGGER_SOURCE == trigger_handler.TriggerSource.GBTx2:
                assert timebase_sync, msg
            elif self.config.TRIGGER_SOURCE == trigger_handler.TriggerSource.SEQUENCER:
                if not timebase_sync:
                    self.logger.warning(msg)
            else:
                raise NotImplementedError

        # Callback method for scan specific configurations
        self.setup_scan_specific_trigger_handler()

    def setup_scan_specific_trigger_handler(self):
        """Method designed to be overriden in daugher classes to tweak the
        configuration of the trigger handler"""
        pass

    def setup_readout_master(self):
        # In DRY run mode the lanes should be active.
        # No triggers are received and the no_data flag
        #  is asserted in the TDH
        if not self.config.DRY:
            if self.config.GTH_ACTIVE:
                for rdo in self.testbench.rdo_list:
                    ib_enabled_lanes = 0
                    for lane in range(rdo.LANES_IB):
                        if lane in self.config.READOUT_GTH_LIST:
                            ib_enabled_lanes |= 1<<lane
                    rdo.readout_master.set_ib_enabled_lanes(ib_enabled_lanes)
                    rdo.readout_master.set_max_nok_lanes_number(len(self.config.READOUT_GTH_LIST))
                    en_lanes = rdo.readout_master.get_ib_enabled_lanes()
                    assert en_lanes == ib_enabled_lanes, f"enabled lanes {en_lanes} != {ib_enabled_lanes} "
            if self.config.GPIO_ACTIVE:
                for rdo in self.testbench.rdo_list:
                    ob_enabled_lanes = 0
                    for lane in range(rdo.LANES_OB):
                        if lane in self.config.READOUT_GPIO_LIST:
                            ob_enabled_lanes |= 1<<lane
                    rdo.readout_master.set_ob_enabled_lanes(ob_enabled_lanes)
                    rdo.readout_master.set_max_nok_lanes_number(len(self.config.READOUT_GPIO_LIST))
                    en_lanes = rdo.readout_master.get_ob_enabled_lanes()
                    assert en_lanes == ob_enabled_lanes, f"enabled lanes {en_lanes} != {ob_enabled_lanes} "

    def setup_datapath(self):
        """Sets up the datapath of the RU"""
        self.setup_trigger_handler()
        self.setup_gbt_packers()
        self.setup_readout_master()

        detector_timeout_bc = self.calculate_detector_timeout_bc()
        DETECTOR_TIMEOUT = detector_timeout_bc<<2
        #DETECTOR_TIMEOUT = 0xFFFF_FFFF # just run with the maximum value, used in 167 like needed due to the broken DCTRL flushing

        self.setup_datapath_gpio(DETECTOR_TIMEOUT)
        self.setup_datapath_gth(DETECTOR_TIMEOUT)

    def calculate_detector_timeout_bc(self):
        """Calculates the detector timeout value based on the daq_test.
        The method is designed to be overridden if needed"""
        if self.config.TRIGGERING_MODE in [RuTriggeringMode.CONTINUOUS,
                                           RuTriggeringMode.DUMMY_CONTINUOUS]:
            detector_timeout_bc = self.config.TRIGGER_PERIOD_BC + 500
        elif self.config.TRIGGERING_MODE in [RuTriggeringMode.PERIODIC,
                                             RuTriggeringMode.PERIODIC_LIMITED,
                                             RuTriggeringMode.TRIGGERED_SEQ,
                                             RuTriggeringMode.MANUAL]:
            detector_timeout_bc = self.config.TRIGGERED_STROBE_DURATION + 50
        else:
            raise NotImplementedError
        return detector_timeout_bc

    def setup_trigger_source(self):
        """Setups the LTU (or the CRU as trigger source on GBTx2)"""
        if self.config.TRIGGER_SOURCE == trigger_handler.TriggerSource.GBTx2:
            hbdrop = self.config.TRIGGER_HBF_PER_TF-self.config.TRIGGER_HBA_PER_TF
            if hbdrop < 2:
                hbdrop = 0xff
            if self.config.TRIGGERING_MODE == RuTriggeringMode.CONTINUOUS:
                if not self.config.USE_LTU:
                    hb_period_bc=3564
                    hb_period_us = hb_period_bc*25e-3
                    self.logger.info(f"hb period {hb_period_us:.2f} us")
                    self.testbench.cru.ttc.configure_emulator(heartbeat_period_bc=hb_period_bc,
                                                              heartbeat_wrap_value=self.config.TRIGGER_HBF_PER_TF-1,
                                                              heartbeat_keep=self.config.TRIGGER_HBA_PER_TF,
                                                              heartbeat_drop=hbdrop,
                                                              periodic_trigger_period_bc=8)
                else:
                    self.testbench.ltu.set_heartbeat_reject_rate(self.config.TRIGGER_HBA_PER_TF)
            elif self.config.TRIGGERING_MODE in [RuTriggeringMode.PERIODIC,
                                                 RuTriggeringMode.PERIODIC_LIMITED,
                                                 RuTriggeringMode.DUMMY_CONTINUOUS,
                                                 RuTriggeringMode.TRIGGERED_SEQ,
                                                 RuTriggeringMode.MANUAL]:
                if self.config.USE_LTU:
                    self.testbench.ltu.set_trigger_rate(self.config.TRIGGER_PERIOD_BC)
                    if self.config.NUM_TRIGGERS is None:
                        self.testbench.ltu.set_num_triggers(self.testbench.ltu.INFINITE_TRIGGERS)
                    else:
                        self.testbench.ltu.set_num_triggers(self.config.NUM_TRIGGERS)
                else:
                    trigger_period_bc=self.config.TRIGGER_PERIOD_BC
                    trigger_period_ns = trigger_period_bc*25
                    self.logger.info(f"trigger period {trigger_period_ns:.2f} ns")
                    hb_period_bc=3564
                    hb_period_us = hb_period_bc*25e-3
                    self.logger.info(f"hb period {hb_period_us:.2f} us")
                    self.testbench.cru.ttc.configure_emulator(heartbeat_period_bc=hb_period_bc,
                                                              heartbeat_wrap_value=self.config.TRIGGER_HBF_PER_TF-1,
                                                              heartbeat_keep=self.config.TRIGGER_HBA_PER_TF,
                                                              heartbeat_drop=hbdrop,
                                                              periodic_trigger_period_bc=trigger_period_bc)
            else:
                raise NotImplementedError

            if self.config.USE_GTM:
                self.testbench.cru.ttc.use_gtm_orbit()
            else:
                self.testbench.cru.ttc.use_seq_orbit()

        elif self.config.TRIGGER_SOURCE == trigger_handler.TriggerSource.SEQUENCER:
            # The following code is a patch for an issue in the code.
            # The trigger handler timebase is not free running if nothing is
            #  connected to the trigger link.
            # Number for HBA/HBR are arbitrary, since the source of the
            # triggers is the sequencer
            # RU_mainFPGA#330.
            if self.config.TRIGGERING_MODE == RuTriggeringMode.TRIGGERED_SEQ:
            #     if self.config.USE_LTU:
            #         self.testbench.ltu.set_trigger_rate(self.config.TRIGGER_PERIOD_BC)
            #         self.testbench.ltu.set_num_triggers(self.testbench.ltu.INFINITE_TRIGGERS)
            #     else:
            #
            #         trigger_period_bc=self.config.TRIGGER_PERIOD_BC
            #         hb_period_bc=3564
            #         self.testbench.cru.ttc.configure_emulator(heartbeat_period_bc=hb_period_bc,
            #                                                   heartbeat_wrap_value=self.config.TRIGGER_HBF_PER_TF-1,
            #                                                   heartbeat_keep=2,
            #                                                   heartbeat_drop=2,
            #                                                   periodic_trigger_period_bc=trigger_period_bc)
                pass # Testing #330 being solved.
            else:
                pass
        else:
            raise NotImplementedError

    def initialize_readout_chain(self):
        """Initializes the readout chain (CRU (not anymore), RU, ALPIDE)"""
        # CRU
        # CRU must be initialized prior to using the DAQ script
        # LTU (or LTU in CRU)
        self.setup_trigger_source()
        # RU
        self.setup_datapath()

    def reset_counters(self):
        """Resets countes for all rdos"""
        self.logger.info("Resetting counters")
        for rdo in self.testbench.rdo_list:
            rdo.reset_daq_counters()

    def dump_rdo_config(self, suffix):
        """Dumps the configuration of all RDOs to file"""
        self.logger.info(f"Dumping rdo config {suffix}")
        for rdo in self.testbench.rdo_list:
            gbt_channel = rdo.get_gbt_channel()
            filename = f"rdo_{gbt_channel}_dump_{suffix}"
            with open(os.path.join(self.logdir, filename), 'w+') as f:
                f.write(rdo.dump_config())

    def dump_chip_config(self,suffix):
        self.logger.info(f"Dumping chip config...{suffix}")
        if self.config.GTH_ACTIVE:
            self.dump_chip_config_ib(suffix=suffix)
        elif self.config.GPIO_ACTIVE:
            self.dump_chip_config_ob(suffix=suffix)

    def dump_chip_config_ib(self, suffix):
        for rdo in self.testbench.rdo_list:
            gbt_channel = rdo.get_gbt_channel()
            filename = f"rdo_{gbt_channel}_alpide_config_{suffix}"
            with open(os.path.join(self.logdir, filename), 'w+') as f:
                stave_ib = self.testbench.stave(gbt_channel)
                for ch in stave_ib:
                    if (ch.chipid not in self.config.EXCLUDE_GTH_LIST) or self.testbench.ru_transition_board_version != ru_transition_board.TransitionBoardVersion.V2_5: # TODO adopt to non v2_5 transition board
                        f.write(ch.dump_config())

    def dump_chip_config_ob(self, suffix):
        for rdo in self.testbench.rdo_list:
            gbt_channel = rdo.get_gbt_channel()
            filename = f"rdo_{gbt_channel}_alpide_config_{suffix}"
            with open(os.path.join(self.logdir, filename), 'w+') as f:
                stave_ob = self.testbench.stave_ob(gbt_channel)
                excluded_chipid_ext = self.get_excluded_chip_list_from_config(rdo=rdo)
                for chipid_ext, ch in stave_ob.items():
                    if (chipid_ext & 0x80) == 0:
                        f.write(f"---Lower HS---{chipid_ext}---\n")
                    else:
                        f.write(f"---Upper HS---{chipid_ext}---\n")
                    if chipid_ext not in excluded_chipid_ext:
                        f.write(ch.dump_config())

    def dump_single_chip_config_ob(self, suffix, chipid_ext):
        for rdo in self.testbench.rdo_list:
            gbt_channel = rdo.get_gbt_channel()
            filename = f"rdo_{gbt_channel}_alpide_config_{suffix}"
            with open(os.path.join(self.logdir, filename), 'w+') as f:
                stave_ob = self.testbench.stave_ob(gbt_channel)
                excluded_chipid_ext = self.get_excluded_chip_list_from_config(rdo=rdo)
                for chid_ext, ch in stave_ob.items():
                    if chipid_ext == chid_ext:
                        if (chipid_ext & 0x80) == 0:
                            f.write(f"---Lower HS---{chipid_ext}---\n")
                        else:
                            f.write(f"---Upper HS---{chipid_ext}---\n")
                        if chipid_ext not in excluded_chipid_ext:
                            f.write(ch.dump_config())

    def before_start_run(self):
        """List of actions to be executed right before the test_start"""
        self.readback_sensors('start_of_run')
        self.dump_chip_config(suffix="start_of_run")
        self.set_chips_in_triggered_mode()
        self.reset_counters()
        self.dump_rdo_config(suffix='start_of_run')
        self.testbench.rdo_list[0].sca.initialize()
        self.testbench.log_all_lol_counters()

    def after_stop_run(self):
        """List of actions to be executed right after the test_stop"""
        self.set_chips_in_configuration_mode()
        for rdo in self.testbench.rdo_list:
            rdo.trigger_handler.disable()
        self.dump_chip_config(suffix="end_of_run")
        self.dump_rdo_config(suffix='end_of_run')
        self.testbench.rdo_list[0].sca.initialize()
        self.testbench.log_all_lol_counters()

    def set_chips_in_triggered_mode(self, rdo=None, silent=False):
        if rdo is not None:
            rdos = [rdo]
        else:
            rdos = self.testbench.rdo_list

        if self.config.GTH_ACTIVE:
            for rdo in rdos:
                self.testbench.set_chips_in_mode(mode=ModeControlChipModeSelector.TRIGGERED,
                                                 LinkSpeed=self.config.LINK_SPEED,
                                                 enable_clock_gating=self.config.SENSOR_CLOCK_GATING,
                                                 enable_skew_start_of_readout=self.config.SENSOR_SKEW_START_OF_READOUT,
                                                 enable_clustering=self.config.SENSOR_CLUSTERING,
                                                 rdo=rdo,
                                                 silent=silent)
        if self.config.GPIO_ACTIVE:
            for rdo in rdos:
                excluded_chipid_ext = self.get_excluded_chip_list_from_config(rdo=rdo, silent=silent)
                self.testbench.set_chips_in_mode(mode=ModeControlChipModeSelector.TRIGGERED,
                                                 LinkSpeed=self.config.LINK_SPEED,
                                                 enable_clock_gating=self.config.SENSOR_CLOCK_GATING,
                                                 enable_skew_start_of_readout=self.config.SENSOR_SKEW_START_OF_READOUT,
                                                 enable_clustering=self.config.SENSOR_CLUSTERING,
                                                 rdo=rdo,
                                                 silent=silent,
                                                 excluded_chipid_ext=excluded_chipid_ext,
                                                 only_masters=self.config.ONLY_MASTERS)

    def set_chips_in_configuration_mode(self, rdo=None, silent=False):
        if rdo is not None:
            rdos = [rdo]
        else:
            rdos = self.testbench.rdo_list

        if self.config.GTH_ACTIVE:
            for rdo in rdos:
                self.testbench.set_chips_in_mode(mode=ModeControlChipModeSelector.CONFIGURATION,
                                                 LinkSpeed=self.config.LINK_SPEED,
                                                 enable_clock_gating=self.config.SENSOR_CLOCK_GATING,
                                                 enable_skew_start_of_readout=self.config.SENSOR_SKEW_START_OF_READOUT,
                                                 enable_clustering=self.config.SENSOR_CLUSTERING,
                                                 rdo=rdo,
                                                 silent=silent)
        if self.config.GPIO_ACTIVE:
            for rdo in rdos:
                excluded_chipid_ext = self.get_excluded_chip_list_from_config(rdo=rdo, silent=silent)
                self.testbench.set_chips_in_mode(mode=ModeControlChipModeSelector.CONFIGURATION,
                                                 LinkSpeed=self.config.LINK_SPEED,
                                                 excluded_chipid_ext=excluded_chipid_ext,
                                                 only_masters=self.config.ONLY_MASTERS,
                                                 enable_clock_gating=self.config.SENSOR_CLOCK_GATING,
                                                 enable_skew_start_of_readout=self.config.SENSOR_SKEW_START_OF_READOUT,
                                                 enable_clustering=self.config.SENSOR_CLUSTERING,
                                                 rdo=rdo,
                                                 silent=silent)

    def setup_chip_config(self, rdo):
        if self.config.LAYER in [testbench.LayerList.MIDDLE, testbench.LayerList.OUTER]:
            DeprecationWarning("This configuration is done before the power handling and should be moved after the power setup")
            ob_staves_yml_path = os.path.join(script_path, "../config/ob_staves.yml")
            with open(ob_staves_yml_path, 'r') as f:
                config = yaml.load(f, Loader=yaml.FullLoader)
                for entry in crate_mapping.subrack_lut[self.config.SUBRACK]:
                    layer = entry[crate_mapping.Fields.layer]
                self.config.staves = config['layer'][layer]['stave']
        elif self.config.LAYER in [testbench.LayerList.NO_PT100, testbench.LayerList.INNER]:
            pass
        else:
            raise NotImplementedError

    def set_vcasn(self, rdo):
        self._set_chip_parameter(rdo=rdo, parameter='VCASN')

    def set_ithr(self, rdo):
        self._set_chip_parameter(rdo=rdo, parameter='ITHR')

    def _set_chip_parameter(self, rdo, parameter='VCASN'):
        try:
            if self.config.LAYER in [testbench.LayerList.OUTER, testbench.LayerList.MIDDLE]:
                excluded_chipid_list = self.get_excluded_chip_list_from_config(rdo)
                gbt_channel = rdo.get_gbt_channel()
                stave_ob = self.testbench.stave_ob(gbt_channel)
                yml_filename = f"{rdo.identity.get_stave_name()}.yml"
                path = os.path.join(script_path, f"../config/{parameter.lower()}/")
                if yml_filename not in os.listdir(path):
                    self.logger.warning(f"yml file {yml_filename} not found, leaving default value!")
                    ch = self.testbench.chip_broadcast_dict[gbt_channel]
                    ch.set_param[parameter](getattr(self.config,parameter), commitTransaction=True)
                else:
                    with open(path+yml_filename, 'r') as f:
                        value_list = yaml.load(f, Loader=yaml.FullLoader)
                        for chipid_ext, ch in stave_ob.items():
                            if chipid_ext not in excluded_chipid_list:
                                ch.set_param[parameter](value_list[chipid_ext], commitTransaction=True)

                    self.logger.info(f"{parameter} configured according to ../config/{parameter.lower()}/{yml_filename}")
                rdo.flush()
            else:
                ch = self.testbench.chip_broadcast_dict[gbt_channel]
                ch.set_param[parameter](getattr(self.config,parameter), commitTransaction=True)
        except:
            self.logger.error(f"Loading {parameter} failed with Exception, raising!")
            raise

    def prepare_for_triggers(self):
        """Main routine for the test:
        - check FPGA design version
        - configures the readout chain
        - resets the counters"""
        self.logger.info("Start initialisation")
        if self.config.CHECK_HASH:
            for rdo in self.testbench.rdo_list:
                rdo.check_git_hash_and_date(expected_git_hash=self.config.GITHASH_RDO)
                rdo.pa3.initialize()
                rdo.pa3.check_git_hash(expected_git_hash=self.config.GITHASH_PA3)
        self.testbench.dna()

        for rdo in self.testbench.rdo_list:
            self.setup_chip_config(rdo)

        if (sum(self.config.FDAQ_ACTIVE_DMA) > 0):
            self.logger.info("Starting fdaq_process")
            t0 = time.time()
            self.start_fdaq()
            self.logger.info(f"Started fdaq in {time.time()-t0:.2f} s")

        self.testbench.clean_all_datapaths()

        self.logger.info("Setting up power")
        self.setup_power()

        self.logger.info("Setting up sensors")
        self.setup_sensors()

        self.logger.info("Initialising readout chain")
        self.initialize_readout_chain()
        self.logger.info("Readout chain initialisation done")

        self.before_start_run()

    def run(self, rcs=False, ltu_master=False):
        """
        - start of run
        - periodic readout of counters and status in the RU and CRU (with warnings on conditions)
        - error handling in case of issues (tear down process to identify failure)
        - end of run
        """
        self.start_run(rcs=rcs, ltu_master=ltu_master)
        if rcs:
            time.sleep(5) # ensure triggers are started before any rack starts main loop
        self.logger.info(f"trigger period {self.config.TRIGGER_PERIOD_BC}. trigger freq {1./(self.config.TRIGGER_PERIOD_BC*25e-9)}")
        self.logger.info("start main loop")
        run_error = None

        try:
            self.scan()
        except KeyboardInterrupt as ki:
            self.logger.info("Run ended by user (Keyboard interrupt).")
            run_error = ki
        except Exception as e:
            self.logger.error("Run finished Due to readout errors.")
            self.logger.error(e,exc_info=True)
            self.test_pass = False
            run_error = e

        self.logger.info("Before call on_test_stop")
        try:
            self.on_test_stop()
        except Exception as e:
            self.logger.error("Exception while running on_test_stop()")
            self.logger.error(e,exc_info=True)
            self.test_pass = False

        self.logger.info("Before call stop_run")
        # Tear down routine for test
        try:
            self.stop_run(rcs=rcs, ltu_master=ltu_master)
            self.after_stop_run()
        except Exception as e:
            self.logger.info("Final read_values might be partial (This is ok)")
            self.logger.info(e)

        self.logger.info("Before call handle_failure")
        es = self.handle_failure(run_error)

        with open(self.testrun_exit_status_info,'w') as df:
            df.write(jsonpickle.encode(es))
            df.flush()

    def test_routine(self):
        """Main routine for the test.
        """
        self.prepare_for_triggers()
        self.run(rcs=self.config.USE_RUN_SERVER)

    def scan(self):
        READ_INTERVAL = 0.5
        running = True
        self.start_time = time.time()
        self.read_values(recordPrefetch=False)

        self.on_test_start()

        last_read = self.start_time
        while running:
            if (time.time()-last_read) > READ_INTERVAL:
                last_read = time.time()
                dp = self.read_values()
                self.print_values(last_read, dp)

            stop = self.send_stimuli()
            running = self.check_status()

            if self.config.TEST_DURATION and (time.time() - self.start_time) > self.config.TEST_DURATION:
                self.logger.info("stop run after %.2f",(time.time() - self.start_time))
                self.logger.info("Finished after end_time reached")
                running=False
            if stop:
                self.logger.info("stop run after %.2f",(time.time() - self.start_time))
                self.logger.info("Finished after sending one trigger")
                running=False

    def exit_status_over_tg(self, exitstatus):
        pass
        #self.testbench.tg_notification(exitstatus.msg)

    def handle_failure(self,run_error):

        es = ExitStatus()
        es.timestamp = time.time()
        es.run_error = run_error

        exit_ids = {
            0: "Run stopped normally",
            1: "Run stopped by Keyboard Interrupt",
            4: "Can't communicate with CRU",
            5: "Can't communicate with SCA",
            6: "Can't communicate with RDO",
            7: "Can't communicate with Powerunit",
            8: "Can't communicate with Chips",
            9: "Unknown Error"
        }

        if run_error is None:
            es.exit_id = 0
            es.msg = exit_ids[es.exit_id]
            return es

        if isinstance(run_error,KeyboardInterrupt):
            es.exit_id = 1
            es.msg = exit_ids[es.exit_id]
            return es

        # cleanup CRU
        try:
            self.logger.info("handle_failure, check CRU")
            self.testbench.cru.check_git_hash_and_date(expected_githash=self.config.GITHASH_CRU)
            self.logger.info("handle_failure, check CRU OK")
        except Exception as e:
            self.logger.info(e,exc_info=True)
            self.logger.info("Communication with CRU broken")
            es.exit_id = 4
            es.msg = exit_ids[4]
            #self.poweroff_RUv0()
            self.exit_status_over_tg(es)
            return es

        try:
            self.logger.info("handle_failure, check SCA")
            for rdo in self.testbench.rdo_list:
                rdo.sca.initialize()
                gpio = rdo.sca.read_gpio()
                es.sca_gpio.append(gpio)
            self.testbench.cru.initialize()
            self.logger.info("handle_failure, check SCA OK")
        except Exception as e:
            self.logger.info(e,exc_info=True)
            self.logger.info("CRU SCA read fail")
            es.exit_id = 5
            es.msg = exit_ids[5]
            self.exit_status_over_tg(es)
            return es

        try:
            self.logger.info("handle_failure, check RDOs")
            for rdo in self.testbench.rdo_list:
                rdo.check_git_hash_and_date(expected_git_hash=self.config.GITHASH_RDO)
            self.logger.info("handle_failure, check RDOs OK")
        except Exception as e:
            self.logger.info(e,exc_info=True)
            self.logger.info("Cannot access RDO")
            self.force_cut_sensor_power()
            es.exit_id = 6
            es.msg = exit_ids[6]
            self.exit_status_over_tg(es)
            return es

        try:
            if self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.POWERUNIT:
                for rdo in self.testbench.rdo_list:
                    pes = rdo.powerunit_1.get_power_enable_status()
                    es.powerenable_status.append(pes)
                    if pes != 0x03:
                        self.logger.info(f"Chip power Latch triggered on rdo {rdo.get_gbt_channel()}")
                return es
            elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.DUAL_POWERUNIT:
                for rdo in self.testbench.rdo_list:
                    pes = rdo.powerunit_1.get_power_enable_status()
                    es.powerenable_status.append(pes)
                    expected_pes = 0
                    for module in self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST:
                        expected_pes |= 0x3<<module
                    if pes != expected_pes:
                        self.logger.info(f"Chip power Latch triggered on rdo {rdo.get_gbt_channel()}: 0x{pes:04X}!=0x{expected_pes:04X}")
                    pes = rdo.powerunit_2.get_power_enable_status()
                    es.powerenable_status.append(pes)
                    expected_pes = 0
                    for module in self.config.POWER_UNIT_2_OUTPUT_CHANNEL_LIST:
                        expected_pes |= 0x3<<module
                    if pes != expected_pes:
                        self.logger.info(f"Chip power Latch triggered on rdo {rdo.get_gbt_channel()}: 0x{pes:04X}!=0x{expected_pes:04X}")
                return es
            elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.MONITOR and self.config.LAYER in [testbench.LayerList.INNER, testbench.LayerList.NO_PT100]:
                for rdo in self.testbench.rdo_list:
                    pes = rdo.powerunit_1.get_power_enable_status()
                    es.powerenable_status.append(pes)
                    expected_pes = 0
                    for module in [0]:
                        expected_pes |= 0x3<<module
                    if pes != expected_pes:
                        self.logger.info(f"Chip power Latch triggered on rdo {rdo.get_gbt_channel()}: 0x{pes:04X}!=0x{expected_pes:04X}")
                return es
            elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.MONITOR and self.config.LAYER == testbench.LayerList.MIDDLE:
                for rdo in self.testbench.rdo_list:
                    pes = rdo.powerunit_1.get_power_enable_status()
                    es.powerenable_status.append(pes)
                    expected_pes = 0
                    for module in [0,1,2,3,4,5,6,7]:
                        expected_pes |= 0x3<<module
                    if pes != expected_pes:
                        self.logger.info(f"Chip power Latch triggered on rdo {rdo.get_gbt_channel()}: 0x{pes:04X}!=0x{expected_pes:04X}")
                return es
            elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.MONITOR and self.config.LAYER == testbench.LayerList.OUTER:
                for rdo in self.testbench.rdo_list:
                    pes = rdo.powerunit_1.get_power_enable_status()
                    es.powerenable_status.append(pes)
                    expected_pes = 0
                    for module in self.config.POWER_UNIT_1_OUTPUT_CHANNEL_LIST:
                        expected_pes |= 0x3<<module
                    if pes != expected_pes:
                        self.logger.info(f"Chip power Latch triggered on rdo {rdo.get_gbt_channel()}: 0x{pes:04X}!=0x{expected_pes:04X}")
                    pes = rdo.powerunit_2.get_power_enable_status()
                    es.powerenable_status.append(pes)
                    expected_pes = 0
                    for module in self.config.POWER_UNIT_2_OUTPUT_CHANNEL_LIST:
                        expected_pes |= 0x3<<module
                    if pes != expected_pes:
                        self.logger.info(f"Chip power Latch triggered on rdo {rdo.get_gbt_channel()}: 0x{pes:04X}!=0x{expected_pes:04X}")
                return es
            elif self.config.SENSOR_POWERING_SCHEME == SensorPoweringScheme.NONE:
                # Power is not handled
                pass
            else:
                raise NotImplementedError

        except Exception as e:
            self.logger.info(e,exc_info=True)
            self.logger.info("Cannot access Powerunit")
            self.force_cut_sensor_power()
            es.exit_id = 7
            es.msg = exit_ids[7]
            self.exit_status_over_tg(es)
            return es

        try:
            self.logger.info("handle_failure, check Chips")
            for rdo in self.testbench.rdo_list:
                if self.config.LAYER in [testbench.LayerList.MIDDLE, testbench.LayerList.OUTER]:
                    ch = Alpide(chipid=16, board=rdo)
                else:
                    ch = Alpide(chipid=0, board=rdo)
                pll_status = ch.getreg_dtu_pll_lock_1()[1]
                es.chip0_pll_status.append(pll_status)
                if not pll_status['LockStatus']:
                    self.logger.info(f"Chip0: Pll not locked on rdo {rdo.get_gbt_channel()}")
                    self.exit_status_over_tg(es)
                    return es
            self.logger.info("handle_failure, check Chips OK")
        except Exception as e:
            self.logger.info(e,exc_info=True)
            self.logger.info("Cannot communicate with chip")
            es.exit_id = 8
            es.msg = exit_ids[8]
            self.exit_status_over_tg(es)
            return es

        if es.run_error is not None:
            self.logger.info("Unknown problem")
            es.exit_id = 9
            es.msg = exit_ids[9]
            self.exit_status_over_tg(es)
            return es

    def log_powersupply_values(self):
        raise NotImplementedError

    def test_dctrl_read(self):
        for is_lower_hs in [True,False]:
            self._test_dctrl_read(is_lower_hs)
        self.logger.info("Test register readback complete")

    def _test_dctrl_read(self,is_lower_hs):
        for rdo in self.testbench.rdo_list:
            gbt_channel = rdo.get_gbt_channel()
            test_reg = 0x0019
            if is_lower_hs:
                stave_ob = self.testbench.stave_ob_lower(gbt_channel)
            elif not is_lower_hs:
                stave_ob = self.testbench.stave_ob_upper(gbt_channel)
            for chip_id, ch in stave_ob.items():
                errors = 0
                try:
                    rdback = ch.read_reg(test_reg)
                    if rdback != chip_id:
                        errors += 1
                        print(f"Mismatch failure for Chip 0x{chip_id:01x}, read: {rdback}. expected{chip_id}")
                except:
                    errors += 1
                    print(f"Readback failure for Chip 0x{chip_id:01x}")

    def test_dctrl_write(self):
        for is_lower_hs in [True,False]:
            self._test_dctrl_write(is_lower_hs)

    def _test_dctrl_write(self,is_lower_hs):
        for rdo in self.testbench.rdo_list:
            gbt_channel = rdo.get_gbt_channel()
            test_reg = 0x0019
            if is_lower_hs:
                stave_ob = self.testbench.stave_ob_lower(gbt_channel)
            elif not is_lower_hs:
                stave_ob = self.testbench.stave_ob_upper(gbt_channel)
            for chip_id, ch in stave_ob.items():
                pattern = chip_id
                ch.write_reg(test_reg, pattern, readback=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config_file", required=False, help="Configuration file relative path", default=None)
    args = parser.parse_args()

    daq_test = DaqTest()

    daq_test.setup_logging()

    daq_test.configure_run(args.config_file)

    daq_test.initialize_testbench()

    daq_test.logger.info("Start new Run")

    daq_test.testbench.setup_cru()

    if daq_test.config.USE_LTU:
        daq_test.testbench.setup_ltu()

    daq_test.setup_comms()

    daq_test.logger.debug(f"Initialised comms {daq_test.testbench.comm_rdo_list}")
    try:
        daq_test.testbench.cru.initialize()
        if daq_test.config.USE_LTU:
            assert daq_test.testbench.ltu.is_ltu_on(), "LTU communication failed"
        try:
            daq_test.testbench.setup_rdos(connector_nr=daq_test.config.MAIN_CONNECTOR)
            daq_test.testbench.cru.initialize(gbt_ch=daq_test.config.CTRL_AND_DATA_LINK_LIST[0])
            daq_test.testbench.initialize_all_rdos()
            daq_test.testbench.initialize_all_gbtx12()
            for rdo in daq_test.testbench.rdo_list:
                if daq_test.config.PA3_READ_VALUES or daq_test.config.PA3_SCRUBBING_ENABLE:
                    rdo.pa3.config_controller.clear_scrubbing_counter()
                if daq_test.config.PA3_SCRUBBING_ENABLE:
                    rdo.pa3.config_controller.start_blind_scrubbing()
                    daq_test.logger.info(f"Running blind scrubbing on RDO {rdo.get_gbt_channel()}")
            daq_test.test_routine()

        except Exception as e:
            raise e
        finally:
            daq_test.logger.info("Tearing down")
            daq_test.tearDown()
            daq_test.logger.info("Tearing down DONE")
    except Exception as e:
        daq_test.logger.error("Exception in Run")
        daq_test.logger.error(e,exc_info=True)
        daq_test.test_pass = False
    finally:
        daq_test.logger.info("Stop ")
        daq_test.testbench.stop()
        daq_test.stop()
        daq_test.logger.info("Stop DONE")

    if daq_test.test_pass:
        daq_test.logger.info("Test passed!")
    else:
        daq_test.logger.warning("Test failed! Check logs")
