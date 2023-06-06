#!/usr/bin/env python3.9

import os, sys, time, re
import logging
import subprocess
import json
import configparser
from enum import IntEnum, unique
from typing import List, Dict, Tuple

from .utils import *

from pALPIDE import Alpide
import trigger_handler, communication
from ltu import Ltu
from cru_board import O2Cru as CRU
from ru_board import Xcku as RU
from power_unit import PowerUnit as PU
from flx_card import FlxCard as FLX

try:
    GIT_HASH_SW = subprocess.run(['git', 'describe', '--always', '--dirty', '--tags'],
                                 check=True, stdout=subprocess.PIPE) \
                         .stdout.decode('utf-8').strip()
except Exception as e:
    GIT_HASH_SW = 'Exception in retriving git hash: '+str(e)
    print(e)
    sys.exit()


@unique
class TriggerMode(IntEnum):
    NOT_SET    = 0
    CONTINUOUS = 1
    TRIGGERED  = 2
    PERIODIC   = 3
    RANDOM     = 4


#######################################################################
class IBTest:
    '''
    This class was written with goal of separating different configuration steps by equipment
    and different running steps by purpose. Here is the general scheme how to run it:
    * SETUP phase: class initialization and set methods
    * INIT phase: initialize(), a limited number of commands needs to be set before any other
    * CONFIGURE phase: configure(), see method for further segmentation by STAVE, RU, CRU
    * RUN fase: launch(), see methods launch() and _run_procedure() for further segmentation
    '''
    cru: CRU
    ru_list: List[RU]
    data_link_list: List[int]
    trigger_mode: TriggerMode
    trigger_source: trigger_handler.TriggerSource
    _ru_to_pu: Dict[RU, Tuple[PU, int]]
    _pu_modules: Dict[PU, List[int]]

    #__________________________________________________________________
    def __init__(self, name: str, cru: CRU, ru_list: List[RU]) -> None:
        self.name = name
        self.cru = cru
        self.ltu = cru
        self.ru_list = ru_list
        self.return_code = (0, 'Not set') # from -9 to -1 for warnings, 0=Not set, 1 to 9 where 9 is most severe
        self._return_code_list = []
        self.git_hashes = {}     # dict to store various GIT hashes
        # RU and chip setup
        self.data_link_list = [] # list of active gbt links, both up and down
        self.exclude_gth_dict = {} # dict for excluding GTH lanes, {"L1_07":[0,4]}
        self.link_speed = 2      # HS data link speed 0=400,1=600,2=1200 Mbps
        self.dry_run = False     # if True, run without staves powered on
        self.ru_scrubbing = None # True/False, enable/disable RU scrubbing
        self.ru_lol_counters = {'SOR':{},'EOR':{}} # Loss of lock counter status
        self._ru_gbtx0_coarse_delay = 4 # gbtx0 coarse delay setting
        self._pixel_mask_dict = {} # pixels to be masked, format {"L1_07": {1:[(256,4),(col,row)]}}
        self._region_mask_dict = {} # regions to be masked, format {"L2_17": {8:[23]}}
        # CRU/RU/LTU triggering setup (set in daughter classes)
        self.trigger_mode = TriggerMode.NOT_SET
        self.trigger_period = None # ns
        self.trigger_source = None # e.g trigger_handler.TriggerSource.GBTx2
        self.detector_timeout = None # ns
        self.send_pulses = None  # if True, on trigger send PULSE opcode, if False, TRIGGER opcode
        self._trg_seq_hb_per_tf = 1
        self._trg_seq_hba_per_tf = 1
        # running and triggering
        self.check_clock_source = True # verify clock source matches trigger source
        self.duration = 0      # duration of the run, 0 = infinite
        self.n_triggers = 0    # number of triggers to be sent (either hardware or software), 0 = infinite
        self.triggers_sent = 0 # number of triggers sent from software (e.g. injections in threshold scan)
        self._logging_period = 5 # frequency of logging run information (e.g. RU counters) during run
        self._stop_on_ru_counter_errors = False # stop if there are errors in the RU counters during run
        # running and triggering, private variables managed by start_of_* and end_of_* methods
        self._triggering = False
        self._trigger_start_time = -1
        self._trigger_end_time = -1
        self._running = False
        self._run_start_time = -1
        self._run_end_time = -1
        self._last_log_time = -1
        # readout
        self.active_dma_list = None
        self.handle_readout = False # True/False to handle starting & stoping of o2-readout-exe
        self.readout_config = None  # either /path/to/readout.cfg or 'auto' for automatic generation (see below)
        self.ignore_readout_errors = None # ignore i.e. don't warn on errors originating from o2-readout-exe
        self._readout_process = None # o2-readout-exe subprocess object
        self._readout_process_logs = None # variable containing file descriptors for managing readout logs
        self._kill_unresponsive_readout_process = True # temporary variable to help with debugging problems with o2-readout-exe
        self._fdaq_process = [None]*8
        # power
        self.handle_power = False # dvdd & avdd are set only if this handle is True
        self.dvdd = 1.80 # V
        self.avdd = 1.80 # V
        self.vbb  = 0 # vbb is never set from the current version of tests, this value is used for setting the DACs
        self.pu_calibration_fpath = None   # path to PUs calibration file
        self.cable_resistance_fpath = None # path to cable resistance file
        self._cable_resistance = {} # dict of cable resistances, {"L0_11":{"dvdd":0.3,"avdd":1.03"}}
        self._ru_to_pu = {}   # dict for RU->PU+module mapping, {ru_object:(pu_object,0)}
        self._pu_modules = {} # dict for PU->connected modules mapping, {pu_object:[0,1,2,3]}
        # output
        self._fpath_out_prefix = None # prefix for output files, if None don't save any output
        # logging
        self.log = logging.getLogger(self.name) # main logger object for all printouts
        self.log.setLevel(logging.DEBUG)
        self._log_file = None # logging file handler, see set_output_to_file method

    #__________________________________________________________________
    def setup(self, cru=None, ru_list=None, data_link_list=None, exclude_gth_dict=None, dry_run=None):
        ''' Set key variables (if) not covered in __init__ '''
        if cru is not None:
            self.cru = cru
            if self.ltu is None: self.ltu = cru
        if ru_list          is not None: self.ru_list = ru_list
        if exclude_gth_dict is not None:
            assert isinstance(exclude_gth_dict, dict)
            for key in exclude_gth_dict:
                assert isinstance(exclude_gth_dict[key], list)
            self.exclude_gth_dict.update(exclude_gth_dict)
            self.log.debug('Excluding following GTH lanes: {}'.format(self.exclude_gth_dict))
        if data_link_list   is not None:
            self.data_link_list = data_link_list
            #self.cru.dwrapper.set_data_link_list(self.data_link_list)
        if dry_run is not None:
            self.dry_run = bool(dry_run)
            if self.dry_run:
                assert self.name in ['ReadoutTest', 'FakeHitRate', 'ThresholdScan'], \
                    self.name+' not runnable in DRY mode!'

    #__________________________________________________________________
    def setup_json(self, config_string):
        ''' Custom config from a JSON string, mut be implemented in individual classes. '''
        raise NotImplementedError(f"Configuration from JSON string not implemented in {self.name}")

    #__________________________________________________________________
    def set_ltu(self, hostname=None, port=None):
        ''' Use LTU for triggering '''
        if hostname is None or port is None:
            self.ltu = DummyLtu()
            self.log.info("Using LTU for triggering as SLAVE")
        else:
            self.ltu = Ltu(hostname, port)
            self.log.info("Using LTU on {}:{} for triggering as MASTER".format(hostname,port))

    #__________________________________________________________________
    def set_trigger_source(self, source):
        if source == 'GBTx2':
            self.trigger_source = trigger_handler.TriggerSource.GBTx2
        else:
            self.trigger_source = trigger_handler.TriggerSource.SEQUENCER
        self.log.info('Set trigger source to '+self.trigger_source.name)

    #__________________________________________________________________
    def set_trigger_frequency(self, frequency_hz):
        self.trigger_period = 1.e9/frequency_hz
        self.detector_timeout = self.trigger_period + 4e3

    #__________________________________________________________________
    def set_trigger_period(self, period_ns):
        self.trigger_period = period_ns
        self.detector_timeout = self.trigger_period + 4e3

    #__________________________________________________________________
    def set_trigger_mode(self, mode):
        if isinstance(mode, int):
            self.trigger_mode = TriggerMode(mode)
        elif isinstance(mode, str):
            self.trigger_mode = TriggerMode[mode.upper()]
        elif isinstance(mode, TriggerMode):
            self.trigger_mode = mode
        else:
            raise TypeError('Trigger mode must be either int, string or TriggerMode!')

    #__________________________________________________________________
    def set_ru_gbtx0_coarse_delay(self, coarse_delay):
        self._ru_gbtx0_coarse_delay = int(coarse_delay)
        self.log.info('RU GBTx0 coarse delay set to {}'.format(self._ru_gbtx0_coarse_delay))

    #__________________________________________________________________
    def set_link_speed(self, linkspeed):
        ''' Set the HS link speed to be used by chip, call before configure_chip'''
        if linkspeed == 1200:
            self.link_speed = 2
        elif linkspeed == 600:
            self.link_speed = 1
        elif linkspeed == 400:
            self.link_speed = 0
        elif linkspeed in [0,1,2,3]:
            self.link_speed = linkspeed
        else:
            raise ValueError('Link speed must be one of the following: 0,1,2,3,400,600,1200')
        self.log.info('HS data link speed set to {} Mbps'
                      .format([400,600,1200,1200][self.link_speed]))

    #__________________________________________________________________
    def set_duration(self, duration):
        assert duration >= 0
        self.duration = duration

    #__________________________________________________________________
    def set_output_to_file(self, fpath_out_prefix):
        ''' Enable output to file by setting the output files path prefix '''
        self._fpath_out_prefix = fpath_out_prefix

        self._log_file = logging.FileHandler(fpath_out_prefix+self.name+'.log', mode='w')
        self._log_file.setLevel(logging.DEBUG)
        self._log_file.setFormatter(logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s") )
        logging.getLogger().addHandler(self._log_file)

    #__________________________________________________________________
    def set_handle_readout(self, handle_readout, active_dma_list=None, ignore_errors=False):
        '''Configure readout process'''
        self.handle_readout = handle_readout
        self.ignore_readout_errors = bool(ignore_errors)
        if (str(active_dma_list).upper() == "NONE" or not active_dma_list.strip()):
            self.active_dma_list = []
        else:
            self.active_dma_list = [x in ["True",1,"yes"] for x in active_dma_list.split(',')]
            if (sum(self.active_dma_list) > 0):
                self.log.info("Recording via fdaq, active_dma_list = {}".format(self.active_dma_list))

    #__________________________________________________________________
    def set_handle_power(self, handle_power, mapping='standard'):
        self.handle_power = handle_power
        if mapping == 'standard': # standard IB mapping RU+PU1+module0
            self._ru_to_pu = {ru:(ru.powerunit_1, 0) for ru in self.ru_list}
        else:
            assert isinstance(mapping, dict)
            self._ru_to_pu = mapping
        self._pu_modules = {}
        for ru in self.ru_list:
            pu,m = self._ru_to_pu[ru]
            if pu in self._pu_modules.keys():
                self._pu_modules[pu].append(m)
            else:
                self._pu_modules[pu] = [m]

    #__________________________________________________________________
    def set_pu_calibration_file_path(self, fpath):
        ''' PU calibration is loaded from this file in initialize() '''
        assert os.path.isfile(fpath)
        self.pu_calibration_fpath = fpath

    #__________________________________________________________________
    def set_cable_resistance_file_path(self, fpath):
        ''' Cable resistances are loaded from this file in initialize() '''
        assert os.path.isfile(fpath)
        self.cable_resistance_fpath = fpath

    #__________________________________________________________________
    def set_pixel_mask_dictionary(self, pixel_mask):
        assert isinstance(pixel_mask, dict)
        for stave,vals in pixel_mask.items():
            assert isinstance(vals, dict)
            for chip,pixels in vals.items():
                assert isinstance(pixels, list)
        self._pixel_mask_dict = pixel_mask
        self.log.info("Pixel mask set!")
        self.log.debug(" ... "+str(self._pixel_mask_dict))

    #__________________________________________________________________
    def set_region_mask_dictionary(self, region_mask):
        assert isinstance(region_mask, dict)
        for stave,vals in region_mask.items():
            assert isinstance(vals, dict)
            for chip,regs in vals.items():
                assert isinstance(regs, list)
        self._region_mask_dict = region_mask
        self.log.info("Region mask set!")
        self.log.debug(" ... "+str(self._region_mask_dict))

    #__________________________________________________________________
    def set_supply_voltage(self, dvdd, avdd):
        assert 1.62<dvdd and dvdd<1.98
        assert 1.62<avdd and avdd<1.98
        self.dvdd = dvdd
        self.avdd = avdd
        self.log.info('Supply voltage set to {:.2f} DVDD / {:.2f} AVDD'.format(self.dvdd, self.avdd))
        if not self.handle_power:
            self.log.warning('Supply voltage set but not applied unless power handle is set!')

    #__________________________________________________________________
    def set_bias_voltage(self, vbb):
        assert -4 <= vbb and vbb <= 0
        self.vbb = vbb
        self.log.info('Bias voltage set to {:.2f} V.'.format(self.vbb))

    #__________________________________________________________________
    def set_return_code(self, val, msg):
        self._return_code_list.append( (int(val), str(msg)) )
        self.return_code = sorted(self._return_code_list)[-1]

    #__________________________________________________________________
    def get_return_code(self):
        return self.return_code[0]

    #__________________________________________________________________
    def get_return_msg(self, version=None):
        if version == 'short':
            return self.return_code[1]
        elif version == 'list':
            msg_list = 'Run finished with exit codes:\n'
            for code,msg in sorted(self._return_code_list, reverse=True):
                msg_list += ' - code {}: {}\n'.format(code, msg)
            return msg_list
        else:
            return '"{}"'.format(self.return_code[1])

    #__________________________________________________________________
    def set_quality_flag(self):
        ''' Asses the outcome of the run, return GOOD/BAD flag and comment for the logbook '''
        flag = 'BAD' if self.get_return_code() > 0 else 'GOOD'
        self.log.info('*'*60)
        self.log.info('Flagged the run as {}. {}'.format(flag, self.get_return_msg()))
        self.log.info('*'*60)
        try:
            with open(self._fpath_out_prefix+'vcasn_ithr.txt') as f:
                vcasn_ithr_conf = f.readline().strip()
        except:
            vcasn_ithr_conf = 'Unkown'
        comment = self.name + \
            '\nRun type: ' + self.name +\
            '\nQuality flag: ' + flag +\
            '\nVCASN/ITHR configuration: ' + vcasn_ithr_conf +\
            '\n'+self.get_return_msg('list') +\
            '\n\n\n'+self.dump_parameters(skip_private=True, skip_classes=True)
        with open(self._fpath_out_prefix+flag, 'w') as f:
            f.write(comment+'\n')
        return flag, comment # return log entry

    #__________________________________________________________________
    def set_scrubbing(self, enabled):
        self.log.info('Scrubbing control moved outside RCS!')
        #self.ru_scrubbing = bool(enabled)
        #self.log.info('RU scrubbing set to {}'.format(enabled))

    #__________________________________________________________________
    def initialize(self):
        ''' Initialize the test, do all set methods before calling this method '''
        self.log.debug(self.name + ' initialising')
        self.log.info('{} git hash: {}'.format(self.name, GIT_HASH_SW))
        self.git_hashes['SW'] = GIT_HASH_SW

        self.cru.initialize()
        self.log.info('FLX {} version: {}'.format("0000", self.cru.version_formatted(as_git_hash=False)))
        self.git_hashes['FLX'] = self.cru.version_formatted(as_git_hash=True)
        self.git_hashes['FLX_v'] = self.cru.version_formatted(as_git_hash=False)

        if self._fpath_out_prefix is not None:
            self.dump_pa3_config('INIT')

        git_hash_rus = []
        for ru in self.ru_list:
            try:
                ru.name = ru_id_string(ru)
                git_hash_ru = f"{ru.git_hash():08X}"
                ru.gth.enable_data(0) # disable data coming from transcievers
                ru.gpio.enable_data(0) # disable data coming from gpio
                ru.initialize() # setting the GBTx chargepump
                dna = ru.identity.get_dna()
                sn = ru.identity.get_sn()
                if sn is not None:
                    sn = f"SN {sn}"
                else:
                    sn = f"DNA {dna:024X}"
                ut = ru.identity.get_uptime_seconds(0)
                tsr = ru.identity.get_uptime_seconds(1)
                self.log.info('RU {} version: 0x{}, {}, uptime: {:.1f}s, reset time: {:.1f}s'.format(ru.name, git_hash_ru, sn, ut, tsr))
            except RuntimeError:
                ru.name = 'RU_GBT_ch'+str(ru.get_gbt_channel())
                git_hash_ru = 'UNKNOWN'
                self.log.exception('Problem communicating with '+ru.name)
            git_hash_rus.append(git_hash_ru)
        if self.ru_list:
            assert 'UNKNOWN' not in git_hash_rus, 'Problem establishing SWT communication with a RU!'
            assert len(set(git_hash_rus)) == 1, 'Different git hashes detected among the RUs! '+str(set(git_hash_rus))
            self.git_hashes['RU'] = git_hash_rus[0]

        for ru in self.ru_list:
            self.cru.initialize()
            ru.pa3.initialize(reset=False)
            LOCAL_CLK_LOL_CNT,_,LOCAL_CLK_C2B_CNT = ru.pa3.loss_of_lock_counter.get()
            self.ru_lol_counters['SOR'][ru.name+'_LOCAL_CLK_LOL_CNT'] = LOCAL_CLK_LOL_CNT
            self.ru_lol_counters['SOR'][ru.name+'_LOCAL_CLK_C2B_CNT'] = LOCAL_CLK_C2B_CNT
            #if self.ru_scrubbing:
            #    ru.pa3.config_controller.start_blind_scrubbing()
            #else:
            #    ru.pa3.config_controller.stop_blind_scrubbing()
            self.log.debug('RU {} is scrubbing {}, counter {}'.format(
                ru.name, ru.pa3.config_controller.is_scrubbing(),
                ru.pa3.config_controller.get_scrubbing_counter() ))

        for ru in self.ru_list:
            git_hash_ru = ru.git_hash()
            ut = ru.identity.get_uptime_seconds(0)
            tsr = ru.identity.get_uptime_seconds(1)
            self.log.info('RU {} version: 0x{:07X}, uptime: {:.1f}s, reset time: {:.1f}s'.format(ru.name, git_hash_ru, ut, tsr))

        for ru in self.ru_list:
            self.log.info(f'RU {ru.name} GBTx0 phase_detector_charge_pump = {ru.gbtx0_swt.get_phase_detector_charge_pump()}')

        #gbtx_check = [ru.name for ru in self.ru_list if not ru.gbtx2_controller.verify_configuration()]
        #if gbtx_check:
        #    self.log.error(f"GBTx2 configuration verification failed on RUs {gbtx_check}!")
        #    self.set_return_code(-2, f"GBTx2 configuration reloaded on RUs {gbtx_check}!")
        #else:
        #    self.log.info("GBTx2 configuration ok.")

        if self._fpath_out_prefix is not None:
            self.dump_optical_power()

        if self.ru_list and self.handle_power:
            for ru,(pu,_) in self._ru_to_pu.items():
                pu.name = 'PU_'+ru.name
            if self.pu_calibration_fpath is not None:
                self._load_pu_calibration_from_file()
            if self.cable_resistance_fpath is not None:
                self._load_cable_resistance_from_file()

        self.log.info(self.name + ' initialized')

    #__________________________________________________________________
    def _load_pu_calibration_from_file(self):
        with open(self.pu_calibration_fpath) as f:
            pu_calibration = json.load(f)
        for ru,(pu,_) in self._ru_to_pu.items():
            pu.set_voltage_offset(
                offset_avdd=[int(o, 16) for o in pu_calibration[ru.name]['offset_avdd']],
                offset_dvdd=[int(o, 16) for o in pu_calibration[ru.name]['offset_dvdd']])

    #__________________________________________________________________
    def _load_cable_resistance_from_file(self):
        self._cable_resistance = read_cable_resistance_file(
            self.cable_resistance_fpath, self.ru_list)

    #__________________________________________________________________
    def configure_stave(self, istave):
        assert istave in range(len(self.ru_list))
        ru = self.ru_list[istave]
        self.log.info('Configuring stave '+ru.name)
        self._configure_stave(ru)
        self._configure_masked_pixels(ru)
        self._configure_masked_regions(ru)
        if self.handle_power and not self.dry_run:
            pu,m=self._ru_to_pu[ru]
            check_vbb(pu,m,self.vbb)
            self.compensate_voltage(ru)

    #__________________________________________________________________
    def _configure_stave(self, ru):
        ''' Abstract method to be implemented in daughter classes '''
        raise NotImplementedError

    #__________________________________________________________________
    def _configure_masked_pixels(self, ru):
        if ru.name not in self._pixel_mask_dict: return
        self.log.debug("Masking pixels on stave "+ru.name)
        for chid,pixels in self._pixel_mask_dict[ru.name].items():
            if len(pixels):
                Alpide(ru, chipid=int(chid)).mask_pixel(pixels)
                self.log.debug(" ... on chip {} pixels: {}".format(chid, pixels))

    #__________________________________________________________________
    def _configure_masked_regions(self, ru):
        if ru.name not in self._region_mask_dict: return
        self.log.debug("Masking regions on stave "+ru.name)
        for chid,regions in self._region_mask_dict[ru.name].items():
            msbs = 0x0
            lsbs = 0x0
            for region in regions:
                if region >= 16: msbs |= 1<<(region-16)
                else:            lsbs |= 1<<(region)
                ch = Alpide(ru, chipid=int(chid))
                if msbs: ch.setreg_disable_regions_msbs(msbs)
                if lsbs: ch.setreg_disable_regions_lsbs(lsbs)
                self.log.debug(" ... on chip {} regions: {} or 0x{:04x}{:04x}".format(chid, regions, msbs, lsbs))

    #__________________________________________________________________
    def configure_ru(self, ru):
        if isinstance(ru, int):
            assert ru in range(0, len(self.ru_list))
            ru = self.ru_list[ru]
        # list of GTH to be used (9 if none are excluded)
        gth_list = [g for g in range(9) if ru.name not in self.exclude_gth_dict \
                    or g not in self.exclude_gth_dict[ru.name]]

        self.log.info('Configuring RU {}: '.format(ru.name) +
                      'trigger {}/{}/{:.1f}kHz/{}, '.format('pulses' if self.send_pulses else 'triggers',
                                                            self.trigger_mode.name, 1e6/self.trigger_period, self.trigger_source.name) +
                      '{} GTH lanes: {}, {}ns timeout'.format(len(gth_list), gth_list, self.detector_timeout) )

        #    success = False
        #    for _ in range(2): # try two times to initialize gbtx because sometimes it fails on first try
        #        success = ru.initialize_gbtx12(
        #            xml_gbtx1_RUv1_1=path_cru_its+"/modules/gbt/software/GBTx_configs/GBTx1_Config_RUv1_1.xml",
        #            xml_gbtx2_RUv1_1=path_cru_its+"/modules/gbt/software/GBTx_configs/GBTx2_Config_RUv1_1.xml",
        #            xml_gbtx1_RUv2_x=path_cru_its+"/modules/gbt/software/GBTx_configs/GBTx1_Config_RUv2.xml",
        #            xml_gbtx2_RUv2_x=path_cru_its+"/modules/gbt/software/GBTx_configs/GBTx2_Config_RUv2.xml")
        #        if success: break
        #    if not success:
        #        raise Exception('GBTx12 configuration failed on RU {}'.format(ru.name))

        ru.clean_datapath()
        time.sleep(0.33)
        # fix timing issues with LTU
        ru.gbtx0_swt.setreg_coarse_delay(channel=2, delay=self._ru_gbtx0_coarse_delay)
        # check GBTxConfig
        assert ru.gbtx1_swt.is_gbtx_config_completed(), "GBTx1 config is NOT completed on RU "+ru.name
        assert ru.gbtx2_swt.is_gbtx_config_completed(), "GBTx2 config is NOT completed on RU "+ru.name

        # setup lanes
        ru.gth_subset(gth_list)
        if self.dry_run:
            ru.alpide_control.disable_all_dctrl_connectors()

        # setup GBT packer
        ru.gbt_packer.set_timeout_to_start(int(self.detector_timeout/6.25))

        # setup trigger
        ru.trigger_handler.enable()
        if self.trigger_source == trigger_handler.TriggerSource.GBTx2:
            ru.trigger_handler.enable_timebase_sync()
        else:
            ru.trigger_handler.disable_timebase_sync()
        ru.trigger_handler.set_trigger_delay(1) # BUG FIX
        ru.trigger_handler.set_trigger_source(self.trigger_source)
        trigger_period_bc=int(0.04*self.trigger_period)
        if self.trigger_mode in [TriggerMode.CONTINUOUS]:
            ru.trigger_handler.setup_for_continuous_mode(trigger_period_bc=trigger_period_bc, send_pulses=self.send_pulses)
            ru.trigger_handler.set_trigger_minimum_distance(100)
        elif self.trigger_mode in [TriggerMode.TRIGGERED, TriggerMode.PERIODIC, TriggerMode.RANDOM]:
            ru.trigger_handler.setup_for_triggered_mode(trigger_minimum_distance=100, send_pulses=self.send_pulses)
        else:
            raise ValueError(f"Trigger mode {self.trigger_mode.name} not supported")
        if self.trigger_source == trigger_handler.TriggerSource.SEQUENCER:
            ru.trigger_handler.sequencer_set_number_of_hb_per_timeframe(self._trg_seq_hb_per_tf)
            ru.trigger_handler.sequencer_set_number_of_hba_per_timeframe(self._trg_seq_hba_per_tf)
            ru.trigger_handler.sequencer_set_trigger_period(trigger_period_bc)
            ru.trigger_handler.sequencer_set_trigger_mode_periodic() # vs random
            if self.trigger_mode == TriggerMode.CONTINUOUS:
                ru.trigger_handler.sequencer_set_mode_continuous()
                ru.trigger_handler.sequencer_set_number_of_timeframes_infinite(True)
            elif self.trigger_mode == TriggerMode.PERIODIC:
                ru.trigger_handler.sequencer_set_mode_triggered()
                ru.trigger_handler.sequencer_set_number_of_timeframes_infinite(True)
            elif self.trigger_mode == TriggerMode.TRIGGERED:
                ru.trigger_handler.sequencer_set_mode_triggered()
                ru.trigger_handler.sequencer_set_number_of_timeframes(0)
            else:
                raise ValueError(f"Trigger mode {self.trigger_mode.name} not supported with trigger sequencer")
        if self.dry_run:
            ru.trigger_handler.set_opcode_gating(True)
        if self.trigger_source == trigger_handler.TriggerSource.GBTx2:
            assert ru.trigger_handler.is_timebase_synced(), f"RU {ru.name} is not timebase synced!"
        self.log.debug('RU trigger configured, period {} BC'.format(trigger_period_bc))

        # setup transceivers
        ru.gth.set_transceivers(gth_list)
        ru.gth.initialize(commitTransaction=True, check_reset_done=True)
        ru.wait(100000)
        assert ru.gth.is_reset_done(), "RU {} Could not initialize GTH transceivers".format(ru.name)
        ru.wait(100000)
        locked = ru.gth.is_cdr_locked()
        if self.dry_run:
            self.log.info('Omitting GTH verification in DRY RUN.')
        else:
            assert False not in locked, "RU {} Could not lock to all sensor clocks: {}".format(ru.name, str(locked))
            assert ru.gth.align_transceivers(check_aligned=True, max_retries=1), \
                "RU {} Could not align all transceivers to comma: {}".format(ru.name, ru.gth.is_aligned())
            self.log.debug("All Transceivers aligned to comma")
        ru.clean_datapath()
        time.sleep(0.33)
        ru.datapath_monitor_ib.reset_all_counters()

        # setup lanes
        ru.lanes_ib.set_detector_timeout(round(self.detector_timeout/6.25))
        lane_mask = 0
        for lane in gth_list: lane_mask |= 1<<lane
        ru.readout_master.set_ib_enabled_lanes(lane_mask)
        ru.readout_master.set_max_nok_lanes_number(len(gth_list))

        en_lanes = ru.readout_master.get_ib_enabled_lanes()
        self.log.debug(f"RU {ru.name}: Enabled lanes: {en_lanes}")
    #__________________________________________________________________
    def configure_cru(self):
        #self.log.info('Configuring CRU {} with {} data links'.format(self.cru.get_pcie_id(), len(self.data_link_list)))
        #self.cru.dwrapper.configure_for_readout(data_link_list=self.data_link_list, enable_dynamic_offset=True)
        if isinstance(self.ltu, FLX):
            self.cru.ttc.configure_emulator(heartbeat_period_bc=3564,
                                            heartbeat_wrap_value=32, # these value discussed with Pippo on 16/10/20
                                            heartbeat_keep=500,
                                            heartbeat_drop=2,
                                            periodic_trigger_period_bc=3564)
            self.cru.ttc.use_gtm_orbit()
            self.log.info('FLX trigger configured to 11.2 kHz (3564 BC), using GTM BCO as orbit')
        else:
            # only FLX is implemented for MVTX
            raise NotImplementedError

    #__________________________________________________________________
    def configure(self):
        ''' Do the full (but mininmal) configuration '''
        for istave,ru in enumerate(self.ru_list):
            self.configure_stave(istave)
            self.configure_ru(ru)
        self.configure_cru()

    #__________________________________________________________________
    def configure_dacs_from_file(self, fname):
        ''' read dacs config from file <fname> and configure chip <ch> connected to RU <ru> accordingly
        e.g. structure of config inside the file:
        conf = {"L2_05": {"CHIP_0": {"ITHR": 50}, "CHIP_N": {"VCASN": 51}}}
        or    {"L1_XX": {"CHIP_15": {"ITHR": 50, "VCASN": 51}}} for all chips on layer 1
        or    {"LX_XX": {"CHIP_15": {"ITHR": 50, "VCASN": 51}}} for all chips of all layers '''
        with open(fname) as jsonfile:
            conf = json.load(jsonfile)
        nstaves = nchips = 0
        for ru in self.ru_list:
            for rukey in ['LX_XX', ru.name[:2]+'_XX', ru.name]:
                if rukey not in conf.keys():
                    continue
                nstaves += 1
                for chid in sorted(conf[rukey].keys(), reverse=True):
                    ch = Alpide(ru, chipid=int(chid.replace('CHIP_', '')))
                    nchips += 1
                    for dac,val in conf[rukey][chid].items():
                        getattr(ch, 'setreg_'+dac.upper())(val)
                        self.log.debug('Configure DAC from file: {ruid} {chid} {dac} set to {val}'
                                .format(ruid=ru.name, chid=chid, dac=dac, val=val))
        self.log.info('Read DAC configuration for {} chip(s) on {} stave(s) from file {}'.format(nchips, nstaves, fname))

    #__________________________________________________________________
    def configure_vcasn_ithr_all_chips(self, vcasn, ithr):
        assert vcasn in range(255)
        assert ithr in range(255)
        self.log.info('Setting VCASN to {} and ITHR to {} for all chips'.format(vcasn, ithr))
        for ru in self.ru_list:
            ch = Alpide(ru, chipid=0xF)
            ch.setreg_VCASN (vcasn)
            ch.setreg_VCASN2(vcasn+12)
            ch.setreg_ITHR  (ithr)

    #__________________________________________________________________
    def compensate_voltage(self, ru):
        assert not self.dry_run, 'Cannot compensate voltage in DRY RUN mode!'
        assert isinstance(self._cable_resistance, dict), 'Cable resistance not present!'
        assert ru.name in self._cable_resistance.keys(), 'Cable resistance for {} unknown!'.format(ru.name)
        time.sleep(0.33)
        pu,m = self._ru_to_pu[ru]
        # iterative process
        compensate_voltage_drop(ru, pu, m, r=self._cable_resistance[ru.name], dvset=self.dvdd, avset=self.avdd)
        time.sleep(0.33)
        compensate_voltage_drop(ru, pu, m, r=self._cable_resistance[ru.name], dvset=self.dvdd, avset=self.avdd)
        time.sleep(0.33)

    #__________________________________________________________________
    def compensate_voltage_all(self):
        assert not self.dry_run, 'Cannot compensate voltage in DRY RUN mode!'
        assert isinstance(self._cable_resistance, dict), 'Cable resistance not present!'
        for ru in self.ru_list:
            assert ru.name in self._cable_resistance.keys(), 'Cable resistance for {} unknown!'.format(ru.name)
        time.sleep(0.33)
        for ru in self.ru_list:
            pu,m = self._ru_to_pu[ru]
            compensate_voltage_drop(ru, pu, m, r=self._cable_resistance[ru.name], dvset=self.dvdd, avset=self.avdd)
        time.sleep(0.33)
        for ru in self.ru_list:
            pu,m = self._ru_to_pu[ru]
            compensate_voltage_drop(ru, pu, m, r=self._cable_resistance[ru.name], dvset=self.dvdd, avset=self.avdd)
        time.sleep(0.33)

    #__________________________________________________________________
    def launch(self):
        ''' Wrapper for catching errors/exception in run procedure '''
        try:
            self._run_procedure()
        except communication.WishboneReadError:
            self.log.exception('WishboneReadError exception occured!')
            self.log.fatal('RUN CRASHED')
            self.set_return_code(9, 'WishboneReadError exception')
        except:
            self.log.exception('Unexpected exception! Stopping...')
            self.set_return_code(9, 'Unexpected exception. Emergency stop.')
            self.emergency_run_stop()

        if self.get_return_code() != 0:
            self.log.error('Test finished with error status {}'.format(self.get_return_msg('short')))
        else:
            self.log.info('Test finished successfully')

        return self.get_return_code()

    #__________________________________________________________________
    def _run_procedure(self):
        self.start_fdaq()
        self.start_of_run()
        self.start_of_trigger()

        try:
            self.run()
        except KeyboardInterrupt:
            self.log.info('Keyboard Interrupt. Stopping...')
            self.set_return_code(1, 'Keyboard Interrupt')

        self.end_of_trigger()
        self.end_of_run()
        self.stop_fdaq()

        return self.get_return_code()

    #__________________________________________________________________
    def finalize(self):
        ''' Cleanup class variables '''
        self.dump_parameters(self._fpath_out_prefix+'run_parameters.json' if self._fpath_out_prefix else None)
        if self._log_file: logging.getLogger().removeHandler(self._log_file)

    #__________________________________________________________________
    def generate_readout_config(self):
        ''' auto generate readout config based on template
        to trigger this set self.readout_config to "auto"
        "auto-norec" creates a readout config without recording '''
        self.log.debug('Generating o2-readout-exe configuration file...')
        conf = configparser.ConfigParser()
        conf.optionxform = lambda option: option # preserve variable case
        assert len(conf.read(os.path.join(IBTESTS_PATH,'../config/readout-template.cfg'))), \
            'Problem with reading readout-template.cfg!'
        cruid = self.cru.get_pcie_id()
        link_list = sorted(self.cru.get_data_link_list())
        links_ep = [[l    for l in link_list if l< 12], # distribute links over the dwrappers
                    [l-12 for l in link_list if l>=12]]
        for i in range(2):
            ii = str(i+1)
            if len(links_ep[i]) == 0:
                conf.remove_section('bank-a'+ii)
                conf.remove_section('equipment-rorc-'+ii)
            else:
                name = f"{cruid}-{i}"
                conf['bank-a'+ii]['enabled'] = '1'
                conf['bank-'+name] = {k:v for k,v in conf['bank-a'+ii].items()}
                conf.remove_section('bank-a'+ii) # mem banks have to have unique names
                conf['equipment-rorc-'+ii]['enabled'] = '1'
                conf['equipment-rorc-'+ii]['id'] = str(i)
                conf['equipment-rorc-'+ii]['cardId'] = name.replace('-',':')
                conf['equipment-rorc-'+ii]['name'] = self.name+'-'+name
                conf['equipment-rorc-'+ii]['memoryBankName'] = 'bank-'+name
                if 'pagesmax' in self.readout_config: conf['equipment-rorc-'+ii]['rdhCheckEnabled'] = '0'
                conf['equipment-rorc-'+name] = {k:v for k,v in conf['equipment-rorc-'+ii].items()}
                conf.remove_section('equipment-rorc-'+ii)
        for section in ['consumer-rec-lz4', 'consumer-processor-lz4']:
            if 'norec' in self.readout_config or conf[section]['enabled']=='0':
                conf.remove_section(section)
            elif 'pagesmax' in self.readout_config:
                conf[section]['pagesMax'] = re.findall('pagesmax-([0-9]+)', self.readout_config)[0]
        if 'consumer-rec-lz4' in conf.sections():
            conf['consumer-rec-lz4']['fileName'] = self._fpath_out_prefix+f"data_cru{cruid}.lz4"
        with open(self._fpath_out_prefix+'readout.cfg', 'w') as f:
            conf.write(f)
        self.readout_config = self._fpath_out_prefix+'readout.cfg'
        self.log.info('Auto-generated o2-readout-exe configuration file in '+self.readout_config)

    #__________________________________________________________________
    def start_readout(self):
        if not self.handle_readout:
            self.log.info('Not handling readout - omitting starting o2-readout-exe!')
            return
        if 'auto' in self.readout_config:
            self.generate_readout_config()
        # run readout
        self.log.info('Starting o2-readout-exe with config: {}'.format(self.readout_config))
        if 'file://' not in self.readout_config:
            config = 'file://' + self.readout_config
        else:
            config = self.readout_config
        self._readout_process_logs = {
            'stdout_w': open(self._fpath_out_prefix+'readout_stdout.txt', 'w'),
            'stderr_w': open(self._fpath_out_prefix+'readout_stderr.txt', 'w'),
            'stdout_r': open(self._fpath_out_prefix+'readout_stdout.txt', 'r'),
            'stderr_r': open(self._fpath_out_prefix+'readout_stderr.txt', 'r')
        }
        self._readout_process = subprocess.Popen(['o2-readout-exe', config], encoding='utf-8',
                                                 stdout=self._readout_process_logs['stdout_w'],
                                                 stderr=self._readout_process_logs['stderr_w'])
        while self._readout_process.poll() is None:
            line = self._readout_process_logs['stdout_r'].readline()
            if 'Entering main loop' in line:
                self.log.info('Readout started')
                return
            time.sleep(0.1)
        self._readout_process_logs['stdout_r'].seek(0)
        self.log.fatal('Could not start o2-readout-exe! Output:\n'+self._readout_process_logs['stdout_r'].read())
        self.log.error('Error messages (if any):\n'+self._readout_process_logs['stderr_r'].read())
        self.set_return_code(6, 'Readout not started')
        raise Exception(self.get_return_msg())

    # __________________________________________________________________
    def start_fdaq(self):
        """Start ATLAS fdaq process(es)"""
        if not self.handle_readout:
            self.log.info('Not handling readout - omitting starting fdaq!')
            return
        if isinstance(self.cru, FLX):
            timeout = f'{self.duration + 5}'
            self.log.info('Starting ATLAS fdaq_process')
            for dma_count, active in enumerate(self.active_dma_list):
                dma = dma_count % 4
                ep = int(dma_count/4)
                if active:
                    self._fdaq_process[dma_count] = subprocess.Popen(["fdaq", "-d", f"{ep}", "-i", f"{dma}", "-t",
                                                                      timeout, self._fpath_out_prefix+f"ibtest_ep{ep}_{dma}"],
                                                                     encoding='utf-8',
                                                                     stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                    readout_started = False
                    readout_stdout = '\n'
                    for line in self._fdaq_process[dma_count].stdout:
                        readout_stdout += '\t' + line
                        if '**START**' in line:
                            readout_started = True
                            break
                    if readout_started:
                        self.log.info('fdaq output:%s', readout_stdout)
                        self.log.info(f"\'fdaq -d {ep}\' started correctly")
                    else:
                        self.log.error(f"Could not start fdaq -d {ep}! Output: %s", readout_stdout)
                        self.log.error('Error messages (if any):\n%s',
                                       ''.join('\t'+line for line in self._fdaq_process[dma_count].stderr))
                        raise RuntimeError(f"Could not start \'fdaq -d {ep}\' due to an error.")
        else:
            raise NotImplementedError

    #__________________________________________________________________
    def stop_readout(self):
        if not self.handle_readout:
            self.log.info('Not handling readout - omitting stopping o2-readout-exe!')
            return
        self.log.info('Waiting for all data to arrive before terminating readout')
        time.sleep(5)
        self.log.info('Terminating readout')
        if self._readout_process is None:
            self.log.warning('o2-readout-exe not started, nothing to stop.')
            return
        if self._readout_process.poll() is not None:
            self.log.warning('o2-readout-exe already stopped with exit code {}'
                             .format(self._readout_process.poll()))
        else:
            time.sleep(5) # make sure all data is written
            self.log.debug(' ... sending term signal.')
            self._readout_process.terminate()
            self.log.debug(' ... term signal sent.')
            w = 0
            while self._readout_process.poll() is None and w < 20:
                time.sleep(1)
                w += 1
                if w % 5 == 0: self.log.info(' ... waiting for o2-readout-exe to terminate')
            if self._readout_process.poll() is None:
                if self._kill_unresponsive_readout_process:
                    self.log.warning(' ... o2-readout-exe still not teminated, sending kill')
                    self.set_return_code(6, 'o2-readout-exe killed')
                    self._readout_process.terminate()
                    self.log.warning(' ... kill command sent')
                else:
                    self.set_return_code(9, 'o2-readout-exe not terminated.' +
                                         'Inform Miko (166849) immediately and DO NOT START any new runs!')
                    return
        out = self._readout_process_logs['stdout_r'].read()
        if 'Warning -' in out:
            if len(out)>10000:
                out = out[:9999]+RESET+'\n\n\t OUTPUT TOO LONG, TRUNCATED TO 10000 SYMBOLS!'
            if self.ignore_readout_errors:
                self.log.debug('o2-readout-exe output (ignored):\n'+out)
            elif self.trigger_source.name == 'GBTx0' and \
                out.count('Warning - Non-contiguous timeframe IDs') == out.count('Warning'):
                # this kind of warning is expected when using GBTx0 (this is probably obsolete since on surface commissioning)
                self.log.info('o2-readout-exe output (contains "Warning - Non-contiguous timeframe IDs" warnings):\n'+out)
            else:
                self.set_return_code(5, 'Warnings in o2-readout-exe')
                self.log.warning('o2-readout-exe output (contains warnings):\n'+out)
        else:
            self.log.debug('o2-readout-exe output:\n'+out)
        err = self._readout_process_logs['stderr_r'].read()
        if len(err):
            self.log.error('Errors in o2-readout-exe:\n'+err)
            if not self.ignore_readout_errors:
                self.set_return_code(6, 'Errors in o2-readout-exe')
        else:
            self.log.info('Readout stopped')
        for f in self._readout_process_logs.values(): f.close()
        self._readout_process = None

    # __________________________________________________________________
    def stop_fdaq(self):
        """Stop ATLAS fdaq process(es)"""
        if not self.handle_readout:
            self.log.info('Not handling readout - omitting stopping fdaq!')
            return
        self.log.info('Waiting for all data to arrive before terminating fdaq')
        time.sleep(5)
        self.log.info('Terminating fdaq processes')
        for dma_count,fdaq_dma_proc in enumerate(self._fdaq_process):
            if fdaq_dma_proc is not None:
                readout_stdout = '\n'
                for line in fdaq_dma_proc.stdout:
                    readout_stdout += '\t'+line
                self.log.info(f"\'fdaq {dma_count}\' output: (and error if any)\n%s", readout_stdout)
                readout_stderr = ''
                for line in fdaq_dma_proc.stderr:
                    readout_stderr += '\t'+line
                if readout_stderr != '':
                    self.log.error(readout_stderr)
                    self.test_pass = False
                if fdaq_dma_proc.stdin:
                    fdaq_dma_proc.stdin.close()
        time.sleep(2)
        self.log.info('fdaq stopped')

    #__________________________________________________________________
    def start_of_run(self):
        self.log.debug(self.dump_parameters())

        for ru in self.ru_list:
            ru.reset_daq_counters()
            ru.mmcm_gbtx_rxrdy_monitor.reset_all_counters()
        self.log_during_run('SOR')

        if self._fpath_out_prefix is not None:
            if not self.dry_run:
                self.dump_volt_temp(self._fpath_out_prefix+'chip_adcs_SOR.json')
                self.dump_chips_config('SOR')
            self.dump_rus_config('SOR')
            self.dump_pa3_config('SOR')
            self.dump_gbtx_config('SOR')

        self.log.info('Starting run ' + self.name)

        if not self.dry_run:
            for ru in self.ru_list: ru.gth.enable_data(True)
        self._run_start_time = time.time()
        self._running = True

    #__________________________________________________________________
    def start_of_trigger(self):
        self.log.info('Starting trigger via {} in {} mode at {:.1f} kHz on source {}'.format(
            type(self.ltu).__name__.upper(),
            self.trigger_mode.name,
            1e6/self.trigger_period,
            self.trigger_source.name) )

        if self.trigger_source == trigger_handler.TriggerSource.GBTx2:
            if self.check_clock_source:
                if isinstance(self.ltu, CRU):
                    assert self.cru.ttc.pll2.get_clock_select() == 0, 'CRU selected as trigger source but ONU clock is not LOCAL!'
                elif isinstance(self.ltu, FLX):
                    pass
                else:
                    assert self.cru.ttc.pll2.get_clock_select() == 1, 'LTU selected as trigger source but ONU clock is not TTC!'

            if self.trigger_mode == TriggerMode.CONTINUOUS:
                if type(self.ltu) in [CRU, FLX]:
                    hb_period = (self.cru.ttc.get_heartbeat_period()+1)*25.00
                else: # LTU
                    hb_period = 3564*25.00
                for ru in self.ru_list:
                    th_period = ru.trigger_handler.get_trigger_period()*6.25
                    assert hb_period % th_period == 0, \
                        "HB period {} not a multiple of RU {} trigger period {}".format(hb_period,ru.name,th_period)
                self.ltu.send_soc()
            elif self.trigger_mode == TriggerMode.TRIGGERED:
                self.ltu.send_sot()
            elif self.trigger_mode == TriggerMode.PERIODIC:
                self.ltu.send_sot(periodic_triggers=True)
            elif self.trigger_mode == TriggerMode.RANDOM:
                assert type(self.ltu) not in [CRU, FLX], 'Random trigger via CRU not forseen'
                self.ltu.send_sot()
                self.ltu.send_physics_trigger(rate=round(self.trigger_period/25.), num=self.ltu.INFINITE_TRIGGERS, start_stop=False)
            else:
                raise ValueError('Trigger mode {} not supported'.format(self.trigger_mode.name))
        else: #trigger_handler.TriggerSource.SEQUENCER
            for ru in self.ru_list: ru.trigger_handler.sequencer_start()

        self._trigger_start_time = time.time()
        self._triggering = True

    #__________________________________________________________________
    def run(self):
        ''' This method is called when test is run directly as a script '''
        self.log.info('Running (duration: {:.2f}s, n_triggers: {:d})'
                     .format(self.duration, self.n_triggers))
        time.sleep(0.5)
        while True:
            step,total_steps = self.run_step()
            if step >= total_steps:
                break

    #__________________________________________________________________
    def run_step(self):
        ''' This method is called when running via RCS '''
        if self.trigger_mode == TriggerMode.TRIGGERED:
            if self.trigger_source == trigger_handler.TriggerSource.GBTx2:
                self.ltu.send_physics_trigger()
                time.sleep(self.trigger_period*1e-9)
            else:
                for ru in self.ru_list:
                    ru.trigger_handler.sequencer_set_number_of_timeframes(1)
            self.triggers_sent += 1
        elapsed_time = round(time.time()-self._trigger_start_time)
        if time.time()-self._last_log_time > self._logging_period:
            self.log.info('Elapsed time: {} of {} s'.format(elapsed_time, self.duration))
            counters = self.log_during_run('RUN_STEP')

            _,bad_counters,_ = print_counters_ru_datapathmon_summary(counters['RUs'])
            if bad_counters:
                self.log.warning(f'RU datapath counters show errors! {bad_counters}')
            if self._stop_on_ru_counter_errors and len(bad_counters) and not self.dry_run:
                self.log.error('RU datapath counters not OK! Stopping!')
                return (-1, -1)

            _,bad_counters = print_status_ru_readout_master_summary(counters['RUs'])
            if 'FERO_OKAY' in bad_counters:
                self.log.warning(f"RU readout master shows errors! {bad_counters['FERO_OKAY']}")
            if 'FERO_OKAY' in bad_counters and not self.dry_run:
                self.log.error('RU readout master FERO NOT OKAY! Stopping!')
                return (-1, -1)

            self._last_log_time = time.time()
        if self.n_triggers > 0:
            return (self.triggers_sent, self.n_triggers)
        elif self.duration > 0:
            return (elapsed_time, self.duration)
        else:
            return (-1, 0)

    #__________________________________________________________________
    def end_of_trigger(self):
        self.log.info('Stopping trigger')
        if self.trigger_source == trigger_handler.TriggerSource.GBTx2:
            if self.trigger_mode == TriggerMode.CONTINUOUS:
                self.ltu.send_eoc()
            elif self.trigger_mode in [TriggerMode.TRIGGERED, TriggerMode.PERIODIC, TriggerMode.RANDOM]:
                self.ltu.send_eot()
            else:
                self.log.fatal('Trigger mode {} not supported'.format(self.trigger_mode.name))
        else: # trigger_handler.TriggerSource.SEQUENCER
            # Workaround for CRU / o2-readout-exe problem:
            # sending dummy triggers resulting in empty events in order to flush out all 'good' events
            # currently 1000 * 511 TFs
            #for ru in self.ru_list:
            #    ch = Alpide(ru, chipid=0xF)
            #    ch.mask_all_pixels()
            #    ch.pulse_all_pixels_disable(commitTransaction=True)
            #    for i in range(1000):
            #        ru.trigger_handler.sequencer_set_number_of_timeframes(511)
            #        done = False
            #        while not done:
            #            done = True
            #            time.sleep(1e-3)
            #            for ru in self.ru_list:
            #                done &= ru.trigger_handler.sequencer_is_done_timeframes()
            # actually stopping the sequencer
            self.log.info('Stopping internal sequencer')
            for ru in self.ru_list: ru.trigger_handler.sequencer_stop()

        self._trigger_end_time = time.time()
        self._triggering = False
        self.log.info('Trigger stopped. Triggering duration {:.2f}. Software triggers sent: {}'
                      .format(self._trigger_end_time-self._trigger_start_time, self.triggers_sent))

    #__________________________________________________________________
    def end_of_run(self):
        self.log.info('Stopping run')
        time.sleep(0.1) # make sure all triggers are sent
        for ru in self.ru_list:
            ru.gth.enable_data(False) # prevent junk in fifos during reconfiguation / powercycle
        time.sleep(0.5) # waits for the data to be received

        counters = {}

        self._run_end_time = time.time()
        self._running = False

        counters['RUs'] = []
        for ru in self.ru_list:
            counters['RUs'].append(read_counters_ru(ru))

        self.log.info(self.name + ' finished in {:.2f}s'
                      .format(self._run_end_time-self._run_start_time) )

        # print output
        for c in counters['RUs']:
            self.log.debug(print_counters_ru(c))

        if (self.trigger_source == trigger_handler.TriggerSource.GBTx2) and isinstance(self.ltu, FLX):
            flag_echoes = False
        else:
            flag_echoes = True
        print_msg = print_counters_ru_trigger_handler_monitor_summary(counters['RUs'], flag_echoes) \
            if len(self.ru_list) else 'No RUs present!'
        if RED in print_msg:
            self.log.error(print_msg)
            self.set_return_code(8, 'Check RU trigger handler counters')
        else:
            self.log.info(print_msg)

        print_msg,bad_counters,warn_counters = print_counters_ru_datapathmon_summary(counters['RUs']) \
            if len(self.ru_list) else ('No RUs present!',{},{})
        if bad_counters and not self.dry_run:
            self.log.error(print_msg)
            self.set_return_code(8, 'Check RU datapath counters: '+str(bad_counters).replace('ERROR', 'ERR'))
        elif warn_counters and not self.dry_run:
            self.log.warning(print_msg)
            self.set_return_code(-3, 'Check RU datapath counters: '+str(warn_counters))
        else:
            self.log.info(print_msg)

        print_msg,bad_counters = print_status_ru_readout_master_summary(counters['RUs']) \
            if len(self.ru_list) else ('No RUs present!',{})
        if bad_counters:
            self.log.error(print_msg)
            self.set_return_code(8, f'Check RU readout master status: {bad_counters}')
        else:
            self.log.info(print_msg)

        if self.get_return_code()==0:
            self.set_return_code(0, 'Done')

        self.log_during_run('EOR')
        if self._fpath_out_prefix is not None:
            with open(self._fpath_out_prefix+'counters_EOR.json', 'w') as jsonfile:
                json.dump(counters, jsonfile, indent=4)
            self.dump_pa3_config('EOR')
            self.dump_rus_config('EOR')
            self.dump_gbtx_config('EOR')
            if not self.dry_run:
                self.dump_volt_temp(self._fpath_out_prefix+'chip_adcs_EOR.json')
                self.dump_chips_config('EOR')

        self.log.debug('Checking LOL counters')
        for ru in self.ru_list:
            self.cru.initialize()
            ru.sca.initialize()
            LOCAL_CLK_LOL_CNT,_,LOCAL_CLK_C2B_CNT = ru.pa3.loss_of_lock_counter.get()
            self.ru_lol_counters['EOR'][ru.name+'_LOCAL_CLK_LOL_CNT'] = LOCAL_CLK_LOL_CNT
            self.ru_lol_counters['EOR'][ru.name+'_LOCAL_CLK_C2B_CNT'] = LOCAL_CLK_C2B_CNT
        print_msg = 'GBTx LOL counters:\n\t{:<25}{:<10}{:<10}\n'.format('','SOR','EOR')
        bad_counters = []
        for c in self.ru_lol_counters['SOR']:
            c_sor = self.ru_lol_counters['SOR'][c]
            c_eor = self.ru_lol_counters['EOR'][c]
            if c_eor != c_sor:
                print_msg += RED
                bad_counters.append(c)
            else:
                print_msg += RESET
            print_msg += '\t{:<25}{:>10}{:>10}\n'.format(c, c_sor, c_eor)+RESET
        if bad_counters:
            self.set_return_code(9, 'Check GBTx LOL counters: '+str(bad_counters))
            self.log.warning(print_msg)
        else:
            self.log.debug(print_msg)

        for ru in self.ru_list: # Matteo likes it this way
            ru.trigger_handler.set_trigger_source(trigger_handler.TriggerSource.SEQUENCER)

    #__________________________________________________________________
    def emergency_run_stop(self):
        ''' Do the minimal set of commands to exit and leave the hardware in a clean state '''
        self.set_return_code(3, 'Run interrupted.')
        try:
            if self._triggering:
                self.end_of_trigger()
            if self._running:
                self.end_of_run()
            if self._readout_process:
                self.stop_readout()
        except:
            self.log.exception('Exception occured during emergency run stop!')
        self.log.fatal('Run stopped!')

    #__________________________________________________________________
    def log_during_run(self, tag='', verbose=False):
        ''' Read certain PU and RU registers and write them to file or debug output '''
        counters = {}
        counters['tag']  = tag
        counters['time'] = time.time()
        # log CRU and RU counters
        #counters['CRU'] = read_counters_cru(self.cru)
        counters['RUs'] = []
        for ru in self.ru_list:
            counters['RUs'].append(read_counters_ru(ru))
        # log PB voltages and currents
        msg = 'Power logging read ({}): '.format(tag)
        if not self.handle_power: msg += '(not handling power)'
        counters['PUs'] = []
        for pu,modules in self._pu_modules.items():
            values = pu.get_values_modules(module_list=modules)
            values['id'] = pu.name
            msg += '\n\t' + pu.name
            msg += '\n\t' + "Power enable status: 0x{0:04X}".format(values["power_enable_status"])
            msg += '\n\t' + "Bias enable status: 0x{0:02X}".format(values["bias_enable_status"])
            msg += '\n\t' + "Backbias: {0:.4f} V, {1:.2f} mA".format(pu._code_to_vbias(values["bb_voltage"]),
                                                                   pu._code_to_ibias(values["bb_current"]))
            for module in modules:
                for vdd in ["avdd", "dvdd"]:
                    msg += '\n\t' + "Module {0}, {1}: {2:.4f} V, {3:.2f} mA ".format(
                        module, vdd,
                        pu._code_to_vpower(values["module_{0}_{1}_voltage".format(module, vdd)]),
                        pu._code_to_i(values["module_{0}_{1}_current".format(module, vdd)])
                    )
            temperature = pu.controller.read_all_temperatures()
            values.update((k.lower()+'_temperature', t) for k,t in temperature.items())
            msg += '\n\t' + 'Temperature: ' + ', '.join('{:s} = {:.2f} C'.format(k,t) for k,t in temperature.items())
            counters['PUs'].append(values)
        if self._fpath_out_prefix is not None:
            with open(self._fpath_out_prefix+'counters_log.json', 'a') as f:
                f.write(json.dumps(counters)+'\n')
        if tag in ['SOR', 'EOR', 'ALARM'] or verbose:
            self.log.debug(msg)
        return counters

    #__________________________________________________________________
    def dump_chips_config(self, tag=''):
        ''' Dump chip configuration to file '''
        if len(tag):
            tag = '_'+tag
        assert not self.dry_run, 'Cannot dump chip config in DRY RUN mode!'
        if self._fpath_out_prefix is None:
            self.log.warning('Not dumping chip config, output file path not provided!')
            return
        for ru in self.ru_list:
            self.log.info('Dumping chips config stave '+ru.name)
            config=''
            for chid in [i for i in range(9) if ru.name not in self.exclude_gth_dict
                         or i not in self.exclude_gth_dict[ru.name]]:
                ch = Alpide(ru, chipid=chid)
                config += ch.dump_config()
            with open(self._fpath_out_prefix+'chip_config_dump'+tag+'_'+ru.name+'.txt', 'w') as f:
                f.write(config)

    #__________________________________________________________________
    def dump_rus_config(self, tag=''):
        ''' Dump RUs configuration to file '''
        if len(tag):
            tag = '_'+tag
        if self._fpath_out_prefix is None:
            self.log.warning('Not dumping RUs config, output file path not provided!')
            return
        directory = self._fpath_out_prefix+'/ru_config_dump/'
        if not os.path.exists(directory):
            os.makedirs(directory)
        for ru in self.ru_list:
            self.log.info('Dumping RU '+ru.name+' config')
            with open(directory+'ru_config_'+ru.name+tag+'.txt', 'w') as f:
                f.write(ru.dump_config())

    #__________________________________________________________________
    def dump_gbtx_config(self, tag=''):
        ''' Dump RUs GBTX configurations to file '''
        self.log.info('Skipping GBTX config dump') # too long and not necessary
        return
        if len(tag):
            tag = '_'+tag
        if self._fpath_out_prefix is None:
            self.log.warning('Not dumping GBTX config, output file path not provided!')
            return
        directory = self._fpath_out_prefix+'/gbtx_config_dump/'
        if not os.path.exists(directory):
            os.makedirs(directory)
        for ru in self.ru_list:
            self.log.info('Dumping RU '+ru.name+' GBTX config')
            with open(directory+'gbtx_config_'+ru.name+tag+'.txt', 'w') as f:
                f.write('\n'.join(ru.gbtx0_swt.dump_config()))
                f.write('\n'.join(ru.gbtx1_swt.dump_config()))
                f.write('\n'.join(ru.gbtx2_swt.dump_config()))

    #__________________________________________________________________
    def dump_pa3_config(self, tag=''):
        """Dumps a limited selection of the PA3 configuration for monitoring purposes"""
        self.log.info('Dumping PA3 config')
        if len(tag):
            tag = '_'+tag
        directory = self._fpath_out_prefix+'/pa3_dump/'
        if not os.path.exists(directory):
            os.makedirs(directory)
        for ru in self.ru_list:
            gbt_channel = ru.get_gbt_channel()
            self.log.debug(f" ... Dump from PA3 on channel {gbt_channel}")
            self.cru.initialize(gbt_ch=gbt_channel)
            ru.pa3.initialize()
            d = ru.pa3.dump_config()
            fname = os.path.join(directory, f"pa3_reads_ch{gbt_channel}{tag}")
            with open(fname, 'w') as f:
                json.dump(d, f, indent=4)
        self.log.debug(' ... Done dumping PA3')

    #__________________________________________________________________
    def dump_optical_power(self, tag=''):
        '''Dumps optical power of RUs in file'''
        self.log.info('Dumping optical power information')
        if len(tag):
            tag = '_'+tag
        with open(self._fpath_out_prefix+'optical_power'+tag+'.txt', 'w') as f:
            for ru in self.ru_list:
                gbt_channel = ru.get_gbt_channel()
                self.cru.initialize(gbt_ch=gbt_channel)
                ru.sca.initialize()
                f.write(f"RU {ru.name} on {gbt_channel:2}\tCRU {ru.sca.read_adc_converted(ru.sca.adc_channels.I_VTRx1):.2f} uA Trigger {ru.sca.read_adc_converted(ru.sca.adc_channels.I_VTRx2):.2f} uA\n")
        self.log.debug(' ... Done dumping optical power')

    #__________________________________________________________________
    def dump_parameters(self, fname_out=None, skip_private=False, skip_classes=False):
        ''' Dump this class parameters to file '''
        class_vars = vars(self)
        dump = 'Dumping test configuration:\n'
        for k,v in class_vars.items():
            if skip_classes and '<' in str(v):
                continue
            if skip_private and k[0]=='_':
                continue
            dump += '   {:.<20s} {}\n'.format(k,str(v))
        if fname_out is not None:
            with open(fname_out, 'w') as jsonfile:
                json.dump({k:v for k,v in class_vars.items() if '<' not in str(v)}, jsonfile, indent=4)
        return dump

    #__________________________________________________________________
    def dump_volt_temp(self, fname_out):
        ''' Dump chip and PU voltage and temperature reads to file '''
        assert not self.dry_run, 'Cannot dump chip voltage and temperature in DRY RUN mode!'
        self.log.info('Dumping voltages and temperatures...')
        data = {}
        self.log.debug('   Dumping PU reads')
        for pu,modules in self._pu_modules.items():
            data[pu.name] = pu.get_values_modules(module_list=modules)
            data[pu.name]['temperature'] = pu.controller.read_all_temperatures()
        self.log.debug('   Dumping chip ADC reads')
        for ru in self.ru_list:
            self.log.debug('      Dumping chip ADCs '+ru.name)
            #data[ru.name] = measure_voltage_temp_stave(ru, chipids=[g for g in self.gth_list])
            data[ru.name] = measure_voltage_temp_stave(ru, chipids=[0, 8]) # only first and last chips as tmp solution for IBT
        with open(fname_out, 'w') as jsonfile:
            json.dump(data, jsonfile, indent=4)
        self.log.debug('Dump complete.')

    #__________________________________________________________________
    def power_on(self):
        power_on(self.ru_list,self._pu_modules,avdd=self.avdd,dvdd=self.dvdd,vbb=self.vbb)

    #__________________________________________________________________
    def power_off(self):
        power_off(self.ru_list,self._pu_modules)

    #__________________________________________________________________
    def is_triggering(self):
        return self._triggering

    def is_running(self):
        return self._running

    def is_readout_active(self):
        if self._readout_process is None:
            return False
        elif self._readout_process.poll() is None:
            return True
        else:
            return False

    def is_triggered_via_ltu(self):
        return type(self.ltu) not in [CRU, FLX]


class DummyLtu:
    ''' LTU placeholder object which does nothing. Serves when RCS is run as LTU slave. '''
    INFINITE_TRIGGERS = None

    def __init__(self):
        self.log = logging.getLogger("DummyLTU")

    def send_soc(self):
        self.log.debug('This is an LTU slave, SOC sent from master')

    def send_eoc(self):
        self.log.debug('This is an LTU slave, EOC sent from master')

    def send_sot(self, periodic_triggers=False):
        self.log.debug('This is an LTU slave, SOT sent from master')

    def send_eot(self):
        self.log.debug('This is an LTU slave, EOT sent from master')

    def send_physics_trigger(self, rate=0, num=1, start_stop=False):
        pass

    def send_physics_trigger_random(self, rate=0, num=1, start_stop=False):
        pass
