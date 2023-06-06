#!/usr/bin/env python3.9

import os, sys, time
import logging
import configparser, argparse
import datetime
from typing import List, Dict, Tuple

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(SCRIPT_PATH, '../../../modules/board_support_software/software/py/'))
from module_includes import *

from pALPIDE import Alpide, Opcode
from ru_board import Xcku as RU
from power_unit import PowerUnit as PU
from pu_controller import Tripped

import ibtests.utils as ibutils

if __name__ == "__main__":
    conf = configparser.ConfigParser()
    conf.read(os.path.join(SCRIPT_PATH, 'config/setup.cfg'))

    argparser = argparse.ArgumentParser(description="Wrapper for basic IB operations.")
    argparser.add_argument('setup', choices=conf.sections()+['1','2'], type=lambda s: s.upper(), help='IB setup to be used')
    argparser.add_argument('command', metavar='CMD', help='Command to be executed. Attention, the optional parameters not applied for all commands.')
    argparser.add_argument('--dvdd', default=-1, type=float, help='Digital voltage to be set')
    argparser.add_argument('--avdd', default=-1, type=float, help='Analogue voltage to be set')
    argparser.add_argument('--vbb', default=0.1, type=float, help='Reverse bias voltage to be set')
    argparser.add_argument('--rus', '--only', nargs='+', metavar='RUs', dest='rus',
                           required=False, default=None, type=int,
                           help='RUs to use in the test. Equivalent to setting ctrl_and_data_link_list')
    argparser.add_argument('--handle_clk', '--no_clock_handling', action='store_false', default=True,
                           help='Switch OFF and ON clock during power on')
    argparser.add_argument('--debug', '--dbg', action='store_true', default=False, help='More verbose output')

    args = argparser.parse_args()
    mode = args.command
    hostname = os.uname()[1]
    if args.setup in ['1','2']:
        setups = {'alio2-cr1-flp187.cern.ch': {'1': 'L0T', '2': 'L0B'},
                  'alio2-cr1-flp188.cern.ch': {'1': 'L1T', '2': 'L1B'},
                  'alio2-cr1-flp189.cern.ch': {'1': 'L2TI', '2': 'L2TO'},
                  'alio2-cr1-flp190.cern.ch': {'1': 'L2BO', '2': 'L2BI'}}
        assert hostname in setups, "This functionality not supported on flp "+hostname
        args.setup = setups[hostname][args.setup]
    if args.dvdd < 0: args.dvdd = conf.getfloat(args.setup, 'dvdd')
    if args.avdd < 0: args.avdd = conf.getfloat(args.setup, 'avdd')
    if args.vbb  > 0: args.vbb  = conf.getfloat(args.setup, 'vbb')
    assert  1.6 <= args.dvdd and args.dvdd <= 2.3
    assert  1.6 <= args.avdd and args.avdd <= 2.3
    assert -4.0 <= args.vbb  and args.vbb  <= 0.0
    if args.rus is None: args.rus = ibutils.parse_cfg_list(conf.get(args.setup, 'ctrl_and_data_link_list'))

    logging.getLogger().setLevel(logging.DEBUG if args.debug else logging.INFO)
    log_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG if args.debug else logging.INFO)
    sh.setFormatter(log_format)
    logging.getLogger().addHandler(sh)

    log_file = logging.FileHandler(os.path.join(
        SCRIPT_PATH,'logs/ibcmd_'+datetime.datetime.today().strftime('%Y-%m-%d')+'.log'), mode='a')
    log_file.setLevel(logging.DEBUG)
    log_file.setFormatter(log_format)
    logging.getLogger().addHandler(log_file)

    log = logging.getLogger('ibcmd')
    log.setLevel(logging.DEBUG)

    log.debug(f"Running command {args.command} on setup {args.setup} with args {args}")

    tb = ibutils.setup_testbench(setup=args.setup, ctrl_and_data_link_list=args.rus)
    if mode.lower() in ['cru_init', 'ci']:
        tb.cru.initialize()
        tb.version()
        tb.stop()
        sys.exit()
    elif mode.lower() in ['init_all', 'ai']:
        tb.initialize_boards(initialize_gbtx12=False)
        time.sleep(1)
        tb.initialize_all_gbtx12()
        tb.version()
        tb.stop()
        sys.exit()

    ru_list: List[RU]
    pu_list: List[PU]
    ru_to_pu: Dict[RU, Tuple[PU, int]]
    pu_modules: Dict[PU, List[int]]
    ru_pu_m_list: List[Tuple[RU, PU, int]]
    ru_list,pu_list,ru_to_pu,pu_modules,ru_pu_m_list = ibutils.get_ru_pu_mapping(
        tb.rdo_list, os.path.join(SCRIPT_PATH,conf.get(args.setup, 'pu_calibration_file_path')), return_extended=True)

    if mode.lower() in ['print', 'info']:
        print('Setup information:')
        for ru,pu,m in ru_pu_m_list:
            print(ru.name, pu.name, m)

    elif mode.lower() in ['puinit', 'pi']:
        for pu in pu_list:
            pu.initialize()
        log.info('Powerunits initialized')

    elif mode.lower() in ['reset-temp-interlock', 'ti']:
        for ru in ru_list:
            assert ru.powerunit_1.controller.get_power_enable_status()==0, \
                f'Will not reset interlock for {ru.name} while it is powered on!'
            tb.reset_temp_interlock(rdo=ru)

    elif mode.lower() in ['reset-tripped-latch', 'rtl']:
        msg=('------+' + ''.join('{:^10}+'.format('-'*10) for k in Tripped) + '\n')
        for i in range(5):
            msg+=('      |' + ''.join('{:^10}|'.format(
                (k.name.split('_')+['']*4)[i]) for k in Tripped) + '\n')
        msg+=('------+' + ''.join('{:^10}+'.format('-'*10) for k in Tripped) + '\n')

        for pu in pu_list:
            status = pu.controller.get_tripped_latch()[0]
            msg+=(pu.name[3:]+' |' + ''.join('{:^10}|'.format(
                ('LATCHED' if status[k.name] else '')) for k in Tripped) + '\n')
            pu.controller.reset_tripped_latch()

        msg+=('------+' + ''.join('{:^10}+'.format('-'*10) for k in Tripped))
        log.info('Latch status before reset:\n'+msg)

    elif mode.lower() in ['power-status', 'power_status', 'ps']:
        for pu,modules in pu_modules.items():
            log.info(pu.name)
            pu.log_values_modules(module_list=modules)
        toti = ibutils.measure_total_current(pu_modules)
        log.info('Total current = ' + str(toti))

    elif mode.lower() in ['power-monitoring', 'pm']:
        prev_toti = ibutils.measure_total_current(pu_modules)
        panic_mode = False
        while True:
            log.info('-'*50)
            try:
                for pu,modules in pu_modules.items():
                    log.info(pu.name)
                    pu.log_values_modules(module_list=modules)
                toti = ibutils.measure_total_current(pu_modules)
                log.info('Total current = ' + str(toti))
                # check change
                d = {k:abs(toti[k]-prev_toti[k]) for k in toti.keys()}
                if d['i_d'] > 150. or d['i_a'] > 50.:
                    log.warning('TOTAL CURRENT EXCEEDED THRESHOLD VALUE! Setting DVDD/AVDD to 1.85V')
                    for pu,modules in pu_modules.items():
                        values = pu.get_values_modules(module_list=modules)
                        if values["bias_enable_status"]:
                            vbb = pu._code_to_vbias(values["bb_voltage"])
                        else:
                            vbb = 0
                        pu.setup_power_modules(module_list=modules,
                                               dvdd=args.dvdd, dvdd_current=1.5,
                                               avdd=args.avdd, avdd_current=0.3,
                                               bb=vbb)
                        pu.log_values_modules(module_list=modules)
                    panic_mode = True
                prev_toti=toti
            except KeyboardInterrupt:
                break
            if panic_mode:
                for i in range(10):
                    log.error('Current change detected, contact expert immediately!'.upper())
                    time.sleep(1)
            else:
                time.sleep(10)

    elif mode.lower() in ['power-on', 'power_on', 'pon']:
        ibutils.power_on(ru_list, pu_modules,
                         avdd=args.avdd, dvdd=args.dvdd, vbb=args.vbb,
                         handle_clock=args.handle_clk)

    elif mode.lower() in ['power-off', 'power_off', 'poff']:
        ibutils.power_off(ru_list, pu_modules)

    elif mode.lower() in ['drop']:
        cable_resistances = ibutils.read_cable_resistance_file(conf.get(args.setup, 'cable_resistance_file_path'), ru_list)
        for ru in ru_list:
            pu,m = ru_to_pu[ru]
            pu.configure_current_limits_modules(module_list=[m], dvdd_current=1.3, avdd_current=0.4)
            ibutils.compensate_voltage_drop(ru, pu, m, r=cable_resistances[ru.name], dvset=args.dvdd, avset=args.avdd)
            time.sleep(0.33)
            ibutils.compensate_voltage_drop(ru, pu, m, r=cable_resistances[ru.name], dvset=args.dvdd, avset=args.avdd)

    elif mode.lower() in ['set-power']:
        for ru in ru_list:
            pu,m = ru_to_pu[ru]
            pu.adjust_output_voltage(module=m, dvdd=args.dvdd, avdd=args.avdd)

    elif mode.lower() in ['log_optical_power', 'op']:
        for ru in ru_list:
            try:
                gbt_channel = ru.get_gbt_channel()
                ru.sca.initialize()
                log.info(f"RU {ru.name}\tCRU {ru.sca.read_adc_converted(ru.sca.adc_channels.I_VTRx1):.2f} uA Trigger {ru.sca.read_adc_converted(ru.sca.adc_channels.I_VTRx2):.2f} uA")
            except Exception:
                log.exception(f"FAILED on RU {gbt_channel}")
            except:
                raise

    elif mode.lower() in ['find_pu_connected_modules', 'find_pu_modules', 'find_modules']:
        for pu in pu_list:
            print(ibutils.find_pu_connected_modules(pu))

    elif mode.lower() in ['check_stave']:
        for ru in ru_list:
            print(ibutils.check_communication_with_stave(ru))

    elif mode.lower() in ['ru_pu_con']:
        ibutils.determine_ru_pu_connections(ru_list, pu_list)

    elif mode.lower() in ['adc']:
        for ru in ru_list:
            ibutils.measure_adc_all_chips(ru)

    elif mode.lower() == 'grst':
        for ru in ru_list:
            Alpide(ru, chipid=0xF).write_opcode(Opcode.GRST)

    elif mode.lower() == 'ru_temp':
        for ru in ru_list:
            print(ru.name)
            print({t:v for t,v in ru.sca.read_adcs_conv().items() if 'T_' in t})

    elif mode.lower() in ['reset_all_xcku', 'reset_rus']:
        tb.reset_all_xcku()

    elif mode.lower() in ['program_all_xcku', 'program_rus']:
        tb.program_all_xcku()

    elif mode.lower() == 'conf_chips':
        for ru in ru_list:
            ibutils.configure_chip(Alpide(ru, chipid=0xF), pulse2strobe=False,
                                   strobe_duration_ns=10000,
                                   pulse_duration_ns=5000)
    elif mode.lower() == 'ibias':
        for ru in ru_list:
            Alpide(ru, chipid=0xF).setreg_IBIAS(20)

    elif mode.lower() == 'dump_chips':
        for ru in ru_list:
            for i in range(8, -1, -1):
                print(Alpide(ru, chipid=i).dump_config())

    elif mode.lower() in ['get_daq_counters', 'get_counters', 'cnts']:
        counters = {}

        counters['RUs'] = []
        for ru in ru_list:
            counters['RUs'].append(ibutils.read_counters_ru(ru))

        for c in counters['RUs']:
            log.info(ibutils.print_counters_ru(c))

        log.info(ibutils.print_counters_ru_trigger_handler_monitor_summary(counters['RUs']))

        print_msg,bad_counters,warn_counters = ibutils.print_counters_ru_datapathmon_summary(counters['RUs'])
        if bad_counters:
            log.error(print_msg)
        elif warn_counters:
            log.warning(print_msg)
        else:
            log.info(print_msg)

        print_msg,bad_counters = ibutils.print_status_ru_readout_master_summary(counters['RUs'])
        if bad_counters:
            log.error(print_msg)
        else:
            log.info(print_msg)

    else:
        log.error('Unkown command '+mode)

    log.info('Command '+mode+' executed.')
    tb.stop()
