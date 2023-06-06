#!/usr/bin/env python3.9

#####################################################################
# This is a script to run a test in expert mode on a setup.
# Besides running on a pre-defined setup, one can use a CUSTOM setup.
# Search for the keyword "custom" in the following code to find the
# parts to be edited to run the tests on your CUSTOM setup.
#####################################################################

import os, sys
import logging
import argparse
import configparser
import json
import datetime
import time
from typing import Type

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(SCRIPT_PATH, '../'))
sys.path.append(os.path.join(SCRIPT_PATH, '../../../modules/board_support_software/software/py/'))
sys.path.append(os.path.join(SCRIPT_PATH, '../../../modules/felix-sw/software/py/'))

from ibtests import *
import ibtests.utils as ibutils

import testbench

###################################################################
if __name__ == "__main__":
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    conf = configparser.ConfigParser()
    conf.read(os.path.join(SCRIPT_PATH, 'config/setup.cfg'))

    test_list = [
        ReadoutTest, FakeHitRate, FelixFakeHitRate, FakeHitRateWithPulsing,
        ThresholdScan, ThresholdTuning, AnalogueScan, DigitalScan,
        FIFOTest, DACScan, CableResistanceMeasurement, ReadWrite,
        ReadoutTestDynamicPreparation, ReadoutTestDynamicRunning]

    # parse args
    argparser = argparse.ArgumentParser(description="Wrapper for running IB tests. " +
                                        "E.g. to run threshold scan on custom setup and record the data: " +
                                        "./run_test.py CUSTOM ThresholdScan --fpath_out /path/to/some/dir --rec")
    argparser.add_argument('setup', metavar='SETUP', choices=conf.sections(), type=lambda s: s.upper(),
                           help='Setup to run the test on.')
    argparser.add_argument('test', metavar='TEST', choices=test_list,
                           type=lambda n: next( (t for t in test_list if len(n) >= 3 and n.lower() in t.__name__.lower()), n),
                           help='Test to be run i.e. at least first three letters of the test name. '+
                           'Available tests: '+str([t.__name__ for t in test_list]))
    argparser.add_argument('--rus', '--only', nargs='+', metavar='RUs', dest='rus', type=int,
                           help='RUs to use in the test.', required=False, default=None)
    argparser.add_argument('--recording', '--rec', action='store_true',
                           help='Use readout.exe to record data to [ram]disk.')
    argparser.add_argument('--fpath_out', default=None, metavar='PATH',
                           help='Path (+prefix) for output files')
    argparser.add_argument('--config_dacs', default=None, metavar='FILE',
                           help='Config file path with chip DACs configuration.')
    argparser.add_argument('--handle_power', '--hp', '--cv', action='store_true',
                           help='Handle power supply e.g compensate voltage before executing the test.' +
                           ' Works only after power on and with all RUs enabled.')
    argparser.add_argument('--dvdd', default=None, type=float, help='Digital voltage to be set')
    argparser.add_argument('--avdd', default=None, type=float, help='Analogue voltage to be set')
    argparser.add_argument('--vbb', default=None, type=float, help='Bacbias voltage supplied to chips')
    argparser.add_argument('--duration', default=-1, type=float,
                           help='Test duration (if applicable).')
    argparser.add_argument('--runs', '--n_runs', default=-1, type=int,
                           help='Number of runs i.e. times to launch the test.')
    argparser.add_argument('--debug', action='store_true', help='Set logging level to DEBUG.')
    argparser.add_argument('--dry_run', action='store_true', help='Enable DRY RUN mode.')
    argparser.add_argument('--conf_only', default=False, action='store_true', help='Only configure but do not run the test.')
    args = argparser.parse_args()

    if args.fpath_out is None:
        args.fpath_out = os.path.join(conf.get(args.setup, 'path_runs'),now+'_'+args.test.__name__)+'/'
        if not os.path.exists(args.fpath_out): os.makedirs(args.fpath_out)
    if args.rus is None:
        if args.setup == 'CUSTOM':
            args.rus = list(range(1)) # custom: modify this if needed
        else:
            args.rus = ibutils.parse_cfg_list(conf.get(args.setup, 'ctrl_and_data_link_list'))

    if args.dvdd is not None or args.avdd is not None:
        args.handle_power = True
    if args.handle_power:
        if args.dvdd is None: args.dvdd=conf.getfloat(args.setup, 'dvdd')
        if args.avdd is None: args.avdd=conf.getfloat(args.setup, 'avdd')
    if args.vbb is None: args.vbb=conf.getfloat(args.setup, 'vbb')

    print('\nTest configuration:')
    for a in vars(args): print('\t{:<10s} {}'.format(a, getattr(args,a)))

    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG if args.debug else logging.INFO)
    sh.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logging.getLogger().addHandler(sh)

    log = logging.getLogger('run_test')

    # SETUP TESTBENCH
    if conf.getboolean(args.setup, 'use_external_testbench'):
        assert args.handle_power is False, \
            'Power handling when testbench is configured from yml file is not supported'
        tbc = testbench.configure_testbench(
            config_file_path = conf.get(args.setup, 'external_testbench_config'),
            run_standalone=False)
        tb = testbench.Testbench(**{k.lower():v for k,v in tbc.items()}, run_standalone=False)
        tb.setup_cru()
        tb.setup_comms(gbt_channel=tb.ctrl_link_list[0])
        tb.setup_rdo()
        tb.setup_stave()
        tb.setup_rdos()
        log.info('Using external testbench config.')
    else:
        tb = ibutils.setup_testbench(setup=args.setup, ctrl_and_data_link_list=args.rus)

    try:
        test: Type[IBTest]
        test = args.test(cru=tb.cru, ru_list=tb.rdo_list)
        test.set_output_to_file(args.fpath_out)
        test.setup(exclude_gth_dict = json.loads(conf.get(args.setup, 'exclude_gth_dict')),
                   data_link_list = tb.data_link_list,
                   dry_run = args.dry_run)
        if conf.getboolean(args.setup, 'use_ltu'):
            test.set_ltu(
                hostname=conf.get(args.setup, 'ltu_hostname'),
                port=conf.getint(args.setup, 'ltu_port'))
            if not test.ltu.is_ltu_on():
                log.warning('LTU appears to be OFF, waiting 3 seconds and retrying...')
                time.sleep(3)
                assert test.ltu.is_ltu_on(), 'LTU appears to be OFF!'

        if conf.get(args.setup, 'trigger_source', fallback='default') != 'default':
            test.set_trigger_source(conf.get(args.setup, 'trigger_source'))
        active_dma_list = conf.get(args.setup, 'ACTIVE_DMA', fallback=None)
        test.set_handle_readout(args.recording, active_dma_list)
        test.set_link_speed(conf.getint(args.setup, 'link_speed'))
        test.check_clock_source = conf.getboolean(args.setup, 'check_clock_source', fallback=True)

        pixel_mask_dict = json.loads(conf.get(args.setup, 'pixel_mask_dict', fallback='{}'))
        if len(pixel_mask_dict): test.set_pixel_mask_dictionary(pixel_mask_dict)
        region_mask_dict = json.loads(conf.get(args.setup, 'region_mask_dict', fallback='{}'))
        if len(region_mask_dict): test.set_region_mask_dictionary(region_mask_dict)

        if args.handle_power:
            test.set_cable_resistance_file_path(
                os.path.join(SCRIPT_PATH, conf.get(args.setup, 'cable_resistance_file_path')))
            test.set_pu_calibration_file_path(
                os.path.join(SCRIPT_PATH, conf.get(args.setup, 'pu_calibration_file_path')))
            test.set_handle_power(True)
            test.set_supply_voltage(args.dvdd, args.avdd)
        test.set_bias_voltage(args.vbb)
        active_dma_list = conf.get(args.setup, 'ACTIVE_DMA', fallback=None)

        if test.name+'_specific' in conf[args.setup]:
            test.setup_json(conf[args.setup][test.name+'_specific'])

        rus_okay,rus_nok_list  = tb.are_all_rdos_initialized()
        assert f'ERROR RUs {rus_nok_list} not initialised! '

        test.initialize()
        test.configure()
        #test.configure_vcasn_ithr_all_chips(vcasn=65, ithr=50)
        if args.config_dacs:   test.configure_dacs_from_file(args.config_dacs)
        if args.duration >= 0: test.set_duration(args.duration)

        if args.conf_only:
            pass
        elif args.runs > -1:
            for irun in range(args.runs):
                test.launch(irun)
        else:
            test.launch()

    except:
        log.exception('Unhandled exception occured!')
        test.set_return_code(9, 'Unhandled exception')
        log.fatal('CRASHED')
    finally:
        test.finalize()
        test.set_quality_flag()

    tb.stop()
