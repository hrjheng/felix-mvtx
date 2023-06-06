import os, sys, time
import logging
import colorama
import json
from typing import List, Dict

IBTESTS_PATH = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(IBTESTS_PATH, '../../'))
sys.path.append(os.path.join(IBTESTS_PATH, '../../../../modules/board_support_software/software/py/'))
sys.path.append(os.path.join(IBTESTS_PATH, '../../../../modules/cru_support_software/software/py/'))
sys.path.append(os.path.join(IBTESTS_PATH, '../../../../modules/ltu_support_software/software/py/'))
sys.path.append(os.path.join(IBTESTS_PATH, '../../../../modules/felix-sw/software/py/'))

import testbench
import power_unit, ru_transition_board
import userdefinedexceptions
from pALPIDE import Alpide, Opcode, Addr, CommandRegisterOpcode
from cru_board import O2Cru as CRU
from ru_board import Xcku as RU
from power_unit import PowerUnit as PU
from pu_controller import Adc

colorama.init()
RED=colorama.Back.RED+colorama.Fore.WHITE
RESET=colorama.Style.RESET_ALL

LOG_NAME = "ibutils"
logging.getLogger("ibutils").setLevel(logging.DEBUG)


#__________________________________________________________________
def setup_testbench(setup: str, ctrl_and_data_link_list=None) -> testbench.Testbench:
    log = logging.getLogger(LOG_NAME)

    link_map = None
    trigger_link_list       = []

    if 'L0T' in setup:
        flp = "alio2-cr1-flp187.cern.ch"
        cru_sn = "0183"
        nstaves = 6
        subrack = "L0T-PP1-I-3"

    elif 'L0B' in setup:
        flp = "alio2-cr1-flp198.cern.ch"
        cru_sn = "0172"
        nstaves = 6
        subrack = "L0B-PP1-O-4"

    elif 'L1T' in setup:
        flp = "alio2-cr1-flp188.cern.ch"
        cru_sn = "0181"
        nstaves = 8
        subrack = "L1T-PP1-I-3"

    elif 'L1B' in setup:
        flp = "alio2-cr1-flp203.cern.ch"
        cru_sn = "0196"
        nstaves = 8
        subrack = "L1B-PP1-O-4"

    elif 'L2TI' in setup:
        flp = "alio2-cr1-flp189.cern.ch"
        cru_sn = "0184"
        nstaves = 5
        subrack = "L2TI-PP1-I-4"

    elif 'L2TO' in setup:
        flp = "alio2-cr1-flp189.cern.ch"
        cru_sn = "0191"
        nstaves = 5
        subrack = "L2TO-PP1-I-4"

    elif 'L2BO' in setup:
        flp = "alio2-cr1-flp190.cern.ch"
        cru_sn = "0179"
        nstaves = 5
        subrack = "L2BO-PP1-O-3"

    elif 'L2BI' in setup:
        flp = "alio2-cr1-flp190.cern.ch"
        cru_sn = "0192"
        nstaves = 5
        subrack = "L2BI-PP1-O-3"

    # REF setups
    elif 'IBS' in setup:
        flp = 'flpits11.cern.ch'
        cru_sn = "0171"
        link_map = {11: [9,8]}
        subrack = "IB-test"

    elif 'IBTABLE' in setup:
        flp = 'flpits12.cern.ch'
        cru_sn = "0188"
        link_map = {11: [10,9]}
        trigger_link_list = [10]
        subrack = "IB-table"

    # MVTX setups
    elif 'CRATE1' in setup:
        flp = "ebdc11.sphenix.bnl.gov"
        cru_sn = "0000"
#        nstaves = 8
        link_map = {0: [1,2],3: [4,5],6: [7,8],9: [10,11],12: [13,14],15: [16,17],18: [19,20],21: [22,23]}
#        trigger_link_list = []
        subrack = "CRATE1"

    elif 'LANL' in setup:
        flp = 'mvtx-flx-amd'
        cru_sn = "0000"
        link_map = {0: [1,2],3: [4,5],6: [7,8],9: [10,11],12: [13,14],15: [16,17],18: [19,20],21: [22,23]}
#        trigger_link_list = []
        subrack = "LANL"

    elif 'ORNL' in setup:
        flp = 'pc0127025.ornl.gov'
        cru_sn = "0000"
        link_map = {0: [1,2]}
#        trigger_link_list = []
        subrack = "ORNL"

    elif ('MVTX_FLX' in setup) and (len(setup) == 9) :
        flp = f'mvtx-flx{setup[8]}.sphenix.bnl.gov'
        cru_sn = "0000"
        link_map = {0: [1,2],3: [4,5],6: [7,8],9: [10,11],12: [13,14],15: [16,17],18: [19,20],21: [22,23]}
        subrack = f"MVTX_FLX{setup[8]}"

    elif 'MVTX_8STVTEL' in setup:
        flp = f'test03.sphenix.bnl.gov'
        cru_sn = "0000"
        link_map = {0: [1,2],3: [4,5],6: [7,8],9: [10,11],12: [13,14],15: [16,17],18: [19,20],21: [22,23]}
        subrack = "MVTX_8STVTEL"

    else:
        log.error('Unknown setup ' + setup)
        raise ValueError('Uknown setup ' + setup)

    if link_map is None:
        link_map = {i: [i+nstaves,i+2*nstaves] for i in range(nstaves)}
    if ctrl_and_data_link_list is None:
        ctrl_and_data_link_list = list(link_map.keys())
    only_data_link_list     = [dl for cl in ctrl_and_data_link_list for dl in link_map[cl]]
    hostname = os.uname()[1]
    assert flp in hostname, 'Setup {} is not available on {} but on {}!'.format(setup, hostname, flp)
    tb = testbench.Testbench(
        cru_sn=cru_sn,
        check_cru_hash=False,
        expected_cru_githash=0,
        ru_main_revision=2, ru_minor_revision=1,
        ru_transition_board_version=ru_transition_board.TransitionBoardVersion.V2_5,
        power_board_version=power_unit.PowerUnitVersion.PRODUCTION,
        power_board_filter_50hz_ac_power_mains_frequency=False,
        ctrl_and_data_link_list=ctrl_and_data_link_list,
        only_data_link_list=only_data_link_list,
        trigger_link_list=trigger_link_list,
        powerunit_resistance_offset_pt100=3.4,
        layer=testbench.LayerList.INNER,
        subrack=subrack,
        cru_type=testbench.CruType.FLX,
        ltu_hostname='',
        run_standalone=False)
    tb.setup_cru()
    # tb.setup_comms(gbt_channel=tb.ctrl_link_list[0])
    tb.setup_comms_rdo()
    # tb.setup_rdo()
    tb.setup_stave()
    tb.setup_rdos()
    return tb


#__________________________________________________________________
def get_ru_pu_mapping(ru_list: List[RU], pu_calibration_fpath=None, return_extended=False):
    log = logging.getLogger(LOG_NAME)
    pu_list = []
    ru_pu_m_list = []
    if pu_calibration_fpath:
        with open(pu_calibration_fpath) as f:
            pu_calibration = json.load(f)
    else:
        pu_calibration = None
        log.warning('PU calibration file not provided, PowerUnit outputs not calibrated!')
    for ru in ru_list:
        ru.name = ru_id_string(ru)
        pu = ru.powerunit_1
        pu.name = 'PU_'+ru.name
        if pu_calibration:
            pu.set_voltage_offset(
                offset_avdd=[int(o, 16) for o in pu_calibration[ru.name]['offset_avdd']],
                offset_dvdd=[int(o, 16) for o in pu_calibration[ru.name]['offset_dvdd']])
        pu_list.append(pu)
        ru_pu_m_list.append((ru, pu, 0))

    ru_to_pu     = {ru: (pu, m) for ru,pu,m in ru_pu_m_list}
    pu_modules   = {pu:[] for pu in pu_list}
    for ru,pu,m in ru_pu_m_list:
        pu_modules[pu].append(m)

    if return_extended:
        return (ru_list, pu_list, ru_to_pu, pu_modules, ru_pu_m_list)
    else:
        return ru_to_pu


#__________________________________________________________________
def power_on(ru_list: List[RU], pu_modules: Dict[PU, List[int]],
             avdd=1.8, dvdd=1.8, vbb=0, handle_clock=True, check_interlock=True):

    log = logging.getLogger(LOG_NAME)
    log.info('Powering on {} staves.'.format(len(ru_list)))
    if not check_interlock:
        log.warning('Interlock is not checked!')
    for pu in pu_modules:
        assert pu.controller.get_power_enable_status()==0, f'{pu.name} is already powered on!'
    if handle_clock:
        log.info('Switching stave clock OFF.')
        for ru in ru_list:
            ru.alpide_control.disable_dclk()
    time.sleep(0.5)
    for pu in pu_modules:
        log.info('Powering on modules {} on {}'.format(pu_modules[pu], pu.name))
        pu.controller.set_clock_interlock_threshold(2.0)
        pu.setup_power_modules(module_list=pu_modules[pu],
                               dvdd=dvdd, dvdd_current=1.3,
                               avdd=avdd, avdd_current=0.4,
                               bb=vbb, check_interlock=check_interlock)
        pu.power_on_modules(module_list=pu_modules[pu],
                            backbias_en=vbb<0, check_interlock=check_interlock)
    time.sleep(0.5)
    if handle_clock:
        log.info('Switching stave clock ON.')
        for ru in ru_list:
            ru.alpide_control.enable_dclk()
    time.sleep(0.5)
    for pu,m in pu_modules.items():
        pu.log_values_modules(module_list=m)
    toti = measure_total_current(pu_modules)
    log.info('IB stave(s) ON - total current = ' + str(toti))


#__________________________________________________________________
def power_off(ru_list: List[RU], pu_modules: Dict[PU, List[int]]):
    log = logging.getLogger(LOG_NAME)
    for pu in pu_modules:
        pu.power_off_all(disable_power_interlock=True)
    time.sleep(0.3)
    for ru in ru_list:
        ru.alpide_control.disable_dclk()
    time.sleep(0.3)
    toti = measure_total_current(pu_modules)
    log.info('IB stave(s) OFF - total current = ' + str(toti))


#__________________________________________________________________
def measure_total_current(pu_modules: Dict[PU, List[int]]):
    ret = {'i_d': 0., 'i_a': 0.}
    for pu in pu_modules:
        for m in pu_modules[pu]:
            meas = pu.get_values_module(module=m)
            ret['i_d'] += pu._code_to_i(meas['module_%d_dvdd_current' % m])
            ret['i_a'] += pu._code_to_i(meas['module_%d_avdd_current' % m])
    return {k:round(v,0) for k,v in ret.items()}


#__________________________________________________________________
def parse_cfg_list(list_string, default=None):
    ret = []
    try:
        for item in list_string.strip().split(','):
            if item.lower() == 'default':
                return default
            elif '-' in item:
                start,end = item.split('-')
                ret.extend(list(range(int(start),int(end)+1)))
            else:
                ret.append(int(item))
    except:
        logging.getLogger().exception('Exception in parsing config file list!')
        ret = []
    return ret


#__________________________________________________________________
def read_cable_resistance_file(fpath: str, ru_list: List[RU]) -> dict:
    ''' Naming scheme as in configure_dacs_from_file '''
    log = logging.getLogger(LOG_NAME)
    with open(fpath) as jsonfile:
        conf = json.load(jsonfile)
    r = {}
    for ru in ru_list:
        for rukey in ['LX_XX', ru.name[:2]+'_XX', ru.name]:
            if rukey not in conf.keys():
                continue
            r[ru.name] = conf[rukey]
            log.debug('Read cable resistance {} for {}'.format(r[ru.name], ru.name))
    if len(r.keys()) == len(ru_list):
        log.info('Loaded cable resistance from file {}'.format(fpath))
        return r
    else:
        missing = [ru.name for ru in ru_list if ru.name not in r.keys()]
        log.fatal('Cable resistance file {} does not contain valus for all staves! Missing staves: {}'.format(fpath, missing))
        raise KeyError('{} keys not found in cable resistance file'.format(missing))


#__________________________________________________________________
def configure_chip(ch: Alpide, chargepump=15, driver=5, preemp=15,
                   strobe_duration_ns=10000,
                   pulse_duration_ns=10000,
                   analogue_pulsing=False,
                   pulse2strobe=True,
                   linkspeed=2):

    assert chargepump in range(16)
    assert driver in range(16)
    assert preemp in range(16)
    assert linkspeed in range(4)
    pulse2strobe = int(bool(pulse2strobe))
    analogue_pulsing = int(bool(analogue_pulsing))

    log = logging.getLogger(LOG_NAME)

    log.info('Configuring chip ID {}: '.format(ch.chipid) +
             'CP/DR/PE {}/{}/{}, '.format(chargepump, driver, preemp) +
             'STROBE/PULSE duration {}/{} us, '.format(strobe_duration_ns*0.001, pulse_duration_ns*0.001) +
             '{} pulsing, pulse2strobe {}'.format('analogue' if analogue_pulsing else 'digital', 'ON' if pulse2strobe else 'OFF'))

    ch.write_opcode(Opcode.GRST)
    ch.write_opcode(Opcode.PRST)

    ch.setreg_mode_ctrl(ChipModeSelector=0x1,
                        EnClustering=0x1,
                        MatrixROSpeed=0x1,
                        IBSerialLinkSpeed=linkspeed,
                        EnSkewGlobalSignals=0x1,
                        EnSkewStartReadout=0x1,
                        EnReadoutClockGating=0x0,
                        EnReadoutFromCMU=0x0)

    ch.setreg_fromu_cfg_1(MEBMask=0x0,
                          EnStrobeGeneration=0x0,
                          EnBusyMonitoring=0x0,
                          PulseMode=analogue_pulsing,
                          EnPulse2Strobe=pulse2strobe,
                          EnRotatePulseLines=0x0,
                          TriggerDelay=0x0)

    strobe_duration = round(strobe_duration_ns/25)-1
    assert 0 <= strobe_duration and strobe_duration < 65535
    ch.setreg_fromu_cfg_2(FrameDuration=strobe_duration) # (n+1)*25ns

    ch.setreg_fromu_pulsing1(PulseDelay=0)

    pulse_duration = round(pulse_duration_ns/25)
    assert 0 <= pulse_duration and pulse_duration < 65535
    ch.setreg_fromu_pulsing_2(PulseDuration=pulse_duration) # n*25ns

    ch.setreg_cmu_and_dmu_cfg(PreviousChipID=0x0,
                              InitialToken=0x1,
                              DisableManchester=0x1,
                              EnableDDR=0x1)
    ch.setreg_dtu_dacs(PLLDAC=chargepump,
                       DriverDAC=driver,
                       PreDAC=preemp)
    ch.setreg_dtu_cfg(VcoDelayStages=0x1,
                      PllBandwidthControl=0x1,
                      PllOffSignal=0x0,
                      SerPhase=0x8,
                      PLLReset=0x0,
                      LoadENStatus=0x0)

    ch.write_opcode(Opcode.RORST)

    ch.mask_all_pixels()
    ch.pulse_all_pixels_disable()

    ch.write_opcode(Opcode.BCRST)

    log.debug('Chip(s) configured')


#__________________________________________________________________
def configure_dacs(ch: Alpide, vbb):
    log = logging.getLogger(LOG_NAME)
    log.debug('Configuring chip ID {} DACs to nominal values for Vbb = {} V'.format(ch.chipid,vbb))
    # values from new_alpide_software
    if vbb == -3:
        ch.setreg_VCASN (105)
        ch.setreg_VCASN2(117)
        ch.setreg_VCLIP (60)
    elif vbb == -2: # interpolated values
        ch.setreg_VCASN (90)
        ch.setreg_VCASN2(102)
        ch.setreg_VCLIP (45)
    elif vbb == -1:
        ch.setreg_VCASN (75)
        ch.setreg_VCASN2(87)
        ch.setreg_VCLIP (30)
    elif vbb == 0:
        ch.setreg_VCASN (50)
        ch.setreg_VCASN2(62)
        ch.setreg_VCLIP (0)
    else:
        raise ValueError('Only 0, -1, -2 and -3 Vbb are supported!')
    ch.setreg_ITHR   (51)
    ch.setreg_IDB    (29)
    ch.setreg_VPULSEH(170)
    ch.setreg_VPULSEL(160)
    ch.setreg_VRESETD(147)
    ch.setreg_VRESETP(117)
    ch.setreg_IRESET (50)
    ch.setreg_VCASP  (86)
    ch.setreg_IBIAS  (64)
    ch.setreg_VTEMP  (0)
    ch.setreg_IAUX2  (0)


#__________________________________________________________________
def configure_chip_mask(ch: Alpide, pattern: str, pulsing=True, masking=True):
    log = logging.getLogger(LOG_NAME)
    if pattern=='ROW':
        if masking:
            ch.unmask_row(255)
        if pulsing:
            ch.pulse_row_enable(255)
        return
    elif pattern=='HALF_ROW':
        pixels = [(2*i,255) for i in range(512)]
    elif pattern=='QUARTER_ROW':
        pixels = [(4*i,255) for i in range(256)]
    elif pattern=='ONEPAGE_3GBT': # fill one 8K page ~94% of a row
        pixels = [(2*i,255) for i in range(512)] + [(2*i-1,255) for i in range(1,448)]
    elif pattern=='ONE_PIX_PER_REG':
        pixels = [(32*i,255) for i in range(32)]
    elif pattern=='MAX_1MHZ':
        pixels = [(64*i,255) for i in range(16)]
    elif 'CLUSTERS' in pattern:
        n = int(pattern.replace('CLUSTERS_', ''))
        pixels = []
        for j in range(4):
            pixels += [(int(1024/n)*i,255+j) for i in range(n)]
            pixels += [(int(1024/n)*i+1,255+j) for i in range(n)]
    else:
        raise ValueError('Uknown masking pattern {}'.format(pattern))

    log.debug('Configuring chip ID {} mask to {}'.format(ch.chipid, pattern))
    if masking:
        ch.unmask_pixel(pixels)
        log.debug('    Unmasked {} pixels'.format(len(pixels)))
    if pulsing:
        ch.pulse_pixel_enable(pixels)
        log.debug('    Pulse enabled for {} pixels'.format(len(pixels)))


#__________________________________________________________________
def ru_id_string(ru: RU):
    _,layer,stave = ru.identity.get_decoded_fee_id()
    return 'L{:d}_{:02d}'.format(layer, stave)


#__________________________________________________________________
def check_vbb(pu: PU, module: int, expected_vbb: float):
    log = logging.getLogger(LOG_NAME)
    expected_status = (expected_vbb < 0) << module
    status = pu.controller.get_bias_enable_status() & (1 << module)
    vbb = pu._code_to_vbias(pu.controller.read_bias_adc_channel(channel=Adc.V_BB))
    assert status == expected_status, \
        'Expected bias enable status 0x{:02X} but got 0x{:02X}'.format(expected_status, status)
    if expected_vbb:
        assert expected_vbb-0.3 < vbb < expected_vbb+0.3, \
            'Expected VBB {:.3f}V but read {:.3f}V'.format(expected_vbb, vbb)
        if not expected_vbb-0.1 < vbb < expected_vbb+0.1:
            log.warning('{} expected VBB {:.3f}V but read {:.3f}V (>100 mV difference)'.format(pu.name, expected_vbb, vbb))


#__________________________________________________________________
def readout_from_cmu(ch: Alpide, fname_out=None):
    data = []
    while True:
        lsb,_ = ch.getreg_dmu_data_fifo_lsbs()
        msb,_ = ch.getreg_dmu_data_fifo_msbs()
        if msb == 0xFF and lsb == 0xFFFF: break
        data += [msb, lsb>>8, lsb & 0xFF]
    if fname_out:
        with open(fname_out, 'wb') as f:
            f.write(bytearray(data))
    return data


#__________________________________________________________________
def read_counters_ru(ru: RU, ib=True):
    counters = {'id': ru.name }
    counters['datapathmon']             = ru.datapath_monitor_ib.read_counters() if ib \
                                          else ru.datapath_monitor_ob.read_counters()
    counters['trigger_handler_monitor'] = ru.trigger_handler.read_counters()
    counters['gbtx_flow_monitor']       = ru.gbtx_flow_monitor.read_counters()
    counters['mmcm_gbtx_rxrdy_monitor'] = ru.mmcm_gbtx_rxrdy_monitor.read_counters()
    counters['gbt_packer_0_monitor']    = ru._gbt_packer_0_monitor.read_counters()
    counters['gbt_packer_1_monitor']    = ru._gbt_packer_1_monitor.read_counters()
    counters['gbt_packer_2_monitor']    = ru._gbt_packer_2_monitor.read_counters()
    counters['readout_master']          = ru.readout_master.get_status()[1]

    return counters


#__________________________________________________________________
def print_counters_ru(counters: dict):
    assert type(counters) is dict

    msg = 'RU ID ' + str(counters['id']) + ' counters\n'
    msg+=('  ' + '+'*30 + ' RU ID ' + str(counters['id']) +' '+ '+'*30 + '\n')

    cnts = counters['datapathmon']
    keys = ['LANE_FIFO_START', 'LANE_FIFO_STOP',
            'u8B10B_OOT', 'u8B10B_OOT_FATAL', 'u8B10B_OOT_TOLERATED', 'u8B10B_OOT_IN_IDLE',
            '8b10b_OOT_ERROR', 'DETECTOR_TIMEOUT', 'PROTOCOL_ERROR']
    non_zero_keys = ['LANE_FIFO_START', 'LANE_FIFO_STOP', '8b10b_COMMA']
    keys.extend([key for key in cnts[0].keys() if key not in non_zero_keys
                 and key not in keys and any([lane[key] for lane in cnts])])
    msg+=('  ' + '-'*20 + 'datapathmon' + '-'*20 + '\n')
    msg+=('  ' + '{:1}'.format('') + ''.join('{:^10}|'.format(k[0:10]) for k in keys) + '\n')
    msg+=('  ' + '{:1}'.format('') + ''.join('{:^10}|'.format(k[10:20]) for k in keys) + '\n')
    for i,c in enumerate(cnts):
        msg+=('  ' + RESET+'{:1}'.format(i) + ''.join(
            (RED if (k not in non_zero_keys and c[k] > 0 or k in non_zero_keys and c[k]==0) else RESET) +
            '{:>10}|'.format(c[k]) for k in keys) + RESET + '\n')

    cnts = counters['trigger_handler_monitor']
    msg+=('  ' + '-'*20 + 'trigger_handler_monitor' + '-'*20 + '\n')
    for k in [k for k in cnts.keys() if 'TRIGGER' in k]:
        msg+=('  ' + '{:<27}'.format(k) + '{:>10}'.format(cnts[k])  + '\n')
    msg+=('  ' + 'Type' + ''.join('{:>9}|'.format(k)       for k in cnts.keys() if 'TRIGGER' not in k) + '\n')
    msg+=('  ' + 'Cnts' + ''.join('{:>9}|'.format(cnts[k]) for k in cnts.keys() if 'TRIGGER' not in k) + '\n')

    cnts = counters['gbtx_flow_monitor']
    keys = ['SOP_UPLINK', 'EOP_UPLINK', 'SWT_UPLINK', 'SWT_DOWNLINK', 'TRG_DOWNLINK']
    msg+=('  ' + '-'*20 + 'gbtx_flow_monitor' + '-'*20 + '\n')
    msg+=('  ' + '{:<13}'.format('') + ''.join('{:>10}'.format('uplink'+str(i)) for i in range(3)) + '\n')
    for k in keys:
        msg+=('  ' + '{:<13}'.format(k) + ''.join('{:>10}'.format(cnts[k+str(i)] if k+str(i) in cnts else '') for i in range(3)) + '\n')

    cnts = [counters['gbt_packer_0_monitor'],
            counters['gbt_packer_1_monitor'],
            counters['gbt_packer_2_monitor']]
    msg+=('  ' + '-'*20 + 'gbt_packer_X_monitor' + '-'*20 + '\n')
    msg+=('  ' + '{:<25}'.format('') + ''.join('{:>10}'.format('packer_'+str(i)) for i in range(3)) + '\n')
    for k in cnts[0].keys():
        msg+=('  ' + '{:<25}'.format(k) + ''.join('{:>10}'.format(c[k]) for c in cnts)  + '\n')

    msg+=('  ' + '+'*30 + 'RU ID ' + str(counters['id']) + '+'*30 + '\n')

    return msg


#__________________________________________________________________
def print_counters_ru_datapathmon_summary(ru_counters_list):
    msg = 'RU datapathmon summary\n'
    bad = {}
    bad_keys = ['DETECTOR_TIMEOUT', 'PROTOCOL_ERROR', 'LANE_FIFO_ERROR', 'LANE_FIFO_OVERFLOW', 'LANE_TIMEOUT',
                '8b10b_OOT_ERROR', 'u8B10B_OOT_FATAL', 'u8B10B_OOT', 'u8B10B_OOT_TOLERATED', 'u8B10B_OOT_IN_IDLE']
    warn_keys = ['BUSY_EVENT', 'BUSY_VIOLATION']
    keys = warn_keys+bad_keys
    # keys that are not zero but should be zero
    keys_not_zero = {k: sum(sum(chip_cnt[k] for chip_cnt in ru_cnt['datapathmon']) for ru_cnt in ru_counters_list) for k in keys}
    # keys that are zero but should not be
    keys_zero     = {k: all(all(chip_cnt[k]>0 for chip_cnt in ru_cnt['datapathmon']) for ru_cnt in ru_counters_list) for k in ['LANE_FIFO_START', 'LANE_FIFO_STOP']} # FIXEM 'EVENT'

    msg+=('  ' + '*'*31 + ' RU datapathmon summary ' + '*'*31 + '\n')
    if sum(v for k,v in keys_not_zero.items()) == 0 and all(v for k,v in keys_zero.items()):
        msg+=('  ' + 'No errors in checked datapathmon counters' + '\n')

    for key in [k for k,v in keys_not_zero.items() if v>0]+[k for k,v in keys_zero.items() if not v]:
        msg+=('  ' + RESET+'-'*31 + RED+key+RESET + '-'*31 + '\n')
        msg+=('  ' + '    ' + ''.join('{:>11}'.format('Chip'+str(i)) for i in range(9)) + '\n')
        bad[key] = []
        for counters in ru_counters_list:
            cnts = counters['datapathmon']
            line =('  ' + RESET+counters['id'] + ''.join(
                (RED if (key in keys_not_zero and c[key]>0) or (key in keys_zero and c[key]==0) else RESET) +
                '{:>11}'.format(c[key]) for c in cnts) + '\n')
            msg+=line
            if RED in line:
                bad[key].append(counters['id'])

    msg+=('  ' + RESET+'*'*31 + ' RU datapathmon summary ' + '*'*31 + '\n')

    return (msg,
            {k:v for k,v in bad.items() if k not in warn_keys},
            {k:v for k,v in bad.items() if k in warn_keys})


#__________________________________________________________________
def print_counters_ru_trigger_handler_monitor_summary(ru_counters_list, flag_echoes=True):
    msg = 'RU trigger_handler_monitor summary\n'

    keys = ru_counters_list[0]['trigger_handler_monitor'].keys()
    msg+=('  ' + '*'*31 + ' RU trigger_handler monitor summary ' + '*'*31 + '\n')
    msg+=('  ' + '{:<27}'.format('') + ''.join('{:>10}|'.format(dict(cntrs)['id']) for cntrs in ru_counters_list) + '\n')
    for k in [k for k in keys if 'TRIGGER' in k]:
        msg+=('  ' + '{:<27}'.format(k) + ''.join(
            (RED if ('ECHOED' in k and flag_echoes and cntrs['trigger_handler_monitor'][k]>2) else RESET) +
            '{:>10}|'.format(cntrs['trigger_handler_monitor'][k]) for cntrs in ru_counters_list) + RESET + '\n')
    msg+=('  ' + '{:<27}'.format('-'*27) + ''.join('{:>10}+'.format('-'*10) for cntrs in ru_counters_list) + '\n')
    msg+=('  ' + '{:<5}'.format('') + ''.join('{:>9}|'.format(k)       for k in keys if 'TRIGGER' not in k) + '\n')
    for cntrs in ru_counters_list:
        msg+=('  ' + '{:<5}'.format(cntrs['id']) + ''.join('{:>9}|'.format(
            cntrs['trigger_handler_monitor'][k]) for k in keys if 'TRIGGER' not in k) + '\n')

    msg+=('  ' + RESET + '*'*31 + ' RU trigger_handler_monitor summary ' + '*'*31 + '\n')
    return msg


#__________________________________________________________________
def print_status_ru_readout_master_summary(ru_counters_list):
    msg = 'RU readout master status summary\n'
    bad = {}

    msg+=('  ' + '*'*31 + ' RU readout master status summary ' + '*'*31 + '\n')

    msg += '  '+' '*27 + ' '.join(f'{counters["id"]:>5}' for counters in ru_counters_list)+'\n'
    keys = ['FERO_OKAY', 'NO_PENDING_DETECTOR_DATA', 'NO_PENDING_LANE_DATA']
    for key in keys:
        bad[key] = [counters['id'] for counters in ru_counters_list if not counters['readout_master'][key]]
        msg+=(f'  {RED+key+RESET if bad[key] else key:<25}: '+' '.join(f'{counters["readout_master"][key]:>5}' for counters in ru_counters_list)+'\n')

    msg+=('  ' + '*'*31 + ' RU readout master status summary ' + '*'*31 + '\n')
    return msg,{k:v for k,v in bad.items() if v}


#__________________________________________________________________
def read_counters_cru(cru: CRU):
    counters = {'id': cru.get_pcie_id()}
    counters['dwrapper'] = {}
    counters['dwrapper']['datapath']        = cru.dwrapper.get_datapath_counters()
    counters['dwrapper']['dropped_packets'] = cru.dwrapper.get_dropped_packets()
    counters['dwrapper']['total_packets']   = cru.dwrapper.get_total_packets()
    return counters


#__________________________________________________________________
def print_counters_cru(counters):
    assert type(counters) is dict

    msg = 'CRU ID ' + str(counters['id']) + ' counters\n'
    msg+=('  ' + '='*30 + ' CRU ID ' + str(counters['id']) +' '+ '='*30 + '\n')

    cnts = counters['dwrapper']['datapath']
    msg+=('  ' + '-'*20 + 'dwrapper_datapath_counters' + '-'*20 + '\n')
    msg+=('  ' + '{:<16}'.format('') + ''.join('{:>10}'.format('link_'+str(k)) for k in cnts) + '\n')
    for k in cnts[next(k for k in cnts.keys())].keys():
        msg+=('  ' + '{:<16}'.format(k) + ''.join( ((RED if v[k]==0 else RESET) if 'accept' in k else '') +
                            '{:>10}'.format(v[k]) + (RESET if 'acc' in k else '') for _,v in cnts.items() ) + '\n')
    msg+=('  ' + '{:<16}'.format('dropped_packets') + (RED if counters['dwrapper']['dropped_packets'] else RESET) +
               '{:>20}'.format(counters['dwrapper']['dropped_packets']) + RESET + '\n')
    msg+=('  ' + '{:<16}'.format('total_packets') + '{:>20}'.format(counters['dwrapper']['total_packets']) + '\n')

    sum_packets = sum([v['accepted_packets'] for _,v in cnts.items()])
    if sum_packets != counters['dwrapper']['total_packets']:
        msg += ('  ' + RED + 'WARNING! Accepted/total packets mismatch! {}/{}'
                .format(sum_packets,counters['dwrapper']['total_packets']) + RESET + '\n')

    msg+=('  ' + '='*30 + 'CRU ID ' + str(counters['id']) + '='*30 + '\n')

    return msg


#__________________________________________________________________
def calibrate_adc(ch: Alpide):
    log = logging.getLogger(LOG_NAME)
    # step 1 - DiscriSign, ALPIDE manual v0.3 fig. 3.23
    ch.setreg_adc_ctrl(Mode=1, SelInput=0, SetIComp=2, RampSpd=1,
                       DiscriSign=0, HalfLSBTrim=0)
    ch.board.wait(int(160e6*0.01))
    ch.setreg_cmd(CommandRegisterOpcode.ADCMEASURE)
    ch.board.wait(int(160e6*0.01)) # has to be at least 5 ms
    val1 = ch.getreg_adc_calibration_value()[0]
    ch.setreg_adc_ctrl(Mode=1, SelInput=0, SetIComp=2, RampSpd=1,
                       DiscriSign=1, HalfLSBTrim=0)
    ch.board.wait(int(160e6*0.01))
    ch.setreg_cmd(CommandRegisterOpcode.ADCMEASURE)
    ch.board.wait(int(160e6*0.01)) # has to be at least 5 ms
    val2 = ch.getreg_adc_calibration_value()[0]
    DiscriSign = int(not val1>val2)

    # step 2 - HalfLSBTrim, ALPIDE manual v0.3 fig. 3.24, but using Input 0 instead of 7 as in Fabrice's code
    ch.setreg_adc_ctrl(Mode=1, SelInput=0, SetIComp=2, RampSpd=1,
                       DiscriSign=DiscriSign, HalfLSBTrim=0)
    ch.setreg_cmd(CommandRegisterOpcode.ADCMEASURE)
    ch.board.wait(int(160e6*0.01))
    ch.setreg_cmd(CommandRegisterOpcode.ADCMEASURE)
    ch.board.wait(int(160e6*0.01)) # has to be at least 5 ms
    val1 = ch.getreg_adc_calibration_value()[0]
    ch.setreg_adc_ctrl(Mode=1, SelInput=0, SetIComp=2, RampSpd=1,
                       DiscriSign=DiscriSign, HalfLSBTrim=1)
    ch.board.wait(int(160e6*0.01))
    ch.setreg_cmd(CommandRegisterOpcode.ADCMEASURE)
    ch.board.wait(int(160e6*0.01)) # has to be at least 5 ms
    val2 = ch.getreg_adc_calibration_value()[0]
    HalfLSBTrim = int(not val1>val2)

    # step 3 - ALPIDE manual v0.3 page 84
    Offset = 0.
    n_samples = 10
    for _ in range(n_samples):
        ch.setreg_adc_ctrl(Mode=1, SelInput=0, SetIComp=2, RampSpd=1,
                           DiscriSign=DiscriSign, HalfLSBTrim=HalfLSBTrim)
        ch.board.wait(int(160e6*0.01))
        ch.setreg_cmd(CommandRegisterOpcode.ADCMEASURE)
        ch.board.wait(int(160e6*0.01)) # has to be at least 5 ms
        Offset += ch.getreg_adc_calibration_value()[0]
        # print(ch.getreg_adc_calibration_value()[0])
    Offset /= 1.*n_samples
    Offset = int(round(Offset))
    log.info('ADC Calibration results: DiscriSign = {:d}, HalfLSBTrim = {:d}, Offset = {:d}'.format(DiscriSign, HalfLSBTrim, Offset))
    return(DiscriSign, HalfLSBTrim, Offset)


#__________________________________________________________________
def measure_adc(ch: Alpide, calibration=None):
    if calibration is not None:
        assert type(calibration) in [list,tuple] and len(calibration) == 3
        DiscriSign, HalfLSBTrim, Offset = calibration
    else:
        DiscriSign, HalfLSBTrim, Offset = calibrate_adc(ch)
    inputs = {'AVSS':0, 'DVSS':1, 'AVDD':2, 'DVDD':3, 'TEMP':8}
    results = {}
    # direct measurements
    for i in inputs.keys():
        ch.setreg_adc_ctrl(Mode=0, SelInput=inputs[i], SetIComp=2, RampSpd=1, CompOut=0,
                           DiscriSign=DiscriSign, HalfLSBTrim=HalfLSBTrim, commitTransaction=False)
        ch.setreg_cmd(CommandRegisterOpcode.ADCMEASURE, commitTransaction=False)
        ch.board.wait(800000, commitTransaction=False)
        results[i] = ch.getreg_adc_avss_value(commitTransaction=True)[0]-Offset
    # indirect measurement AVDD
    ch.setreg_VTEMP(200, commitTransaction=False)
    ch.board.wait(800000, commitTransaction=False)
    ch._set_dac_monitor(Addr.VTEMP, commitTransaction=False)
    ch.board.wait(800000, commitTransaction=False)
    ch.setreg_adc_ctrl(Mode=0, SelInput=5, SetIComp=2, RampSpd=1,
                         DiscriSign=DiscriSign, HalfLSBTrim=HalfLSBTrim, commitTransaction=False)
    ch.setreg_cmd(CommandRegisterOpcode.ADCMEASURE, commitTransaction=False)
    ch.board.wait(800000, commitTransaction=False)
    results['AVDD_indirect'] = ch.getreg_adc_avss_value(commitTransaction=True)[0]-Offset
    return results


#__________________________________________________________________
def measure_adc_all_chips(ru: RU):
    names = ['AVSS', 'DVSS', 'AVDD', 'DVDD']
    results = {'Avg':{n:0. for n in names}}
    for chid in range(8, -1, -1):
        ch = Alpide(ru, chipid=chid)
        r = measure_adc(ch, (0,0,0))
        results[chid] = r
        for n in names:
            results['Avg'][n] += r[n]
    for n in names:
        results['Avg'][n] /= len(results.keys())-1.
    print(''.join(['{:s}\t'.format(n) for n in ['ChipID']+names]))
    for chid in results.keys():
        print('{:s}\t'.format(str(chid)), ''.join(['{:.3f}\t'.format(results[chid][n]) for n in names]))


#__________________________________________________________________
def measure_voltage_temp_stave(ru: RU, chipids=range(9), n_samples=1, only_inputs=None):
    chips = [Alpide(ru, chipid=i) for i in sorted(chipids)]
    ch_bc = Alpide(ru, chipid=0xF)
    DiscriSign = HalfLSBTrim = 0
    inputs = {'AVSS':0, 'DVSS':1, 'AVDD':2, 'DVDD':3, 'TEMP':8}
    if type(only_inputs) == list:
        inputs = {k:v for k,v in inputs.items() if k in only_inputs}
    results = {'CHIP_{:02d}'.format(i):{adc:[] for adc in list(inputs.keys())+['AVDD_indirect']} for i in sorted(chipids)}
    # direct measurements
    for adc in inputs.keys():
        ch_bc.setreg_adc_ctrl(Mode=0, SelInput=inputs[adc], SetIComp=2, RampSpd=1, CompOut=0,
                              DiscriSign=DiscriSign, HalfLSBTrim=HalfLSBTrim)
        for s in range(n_samples):
            ch_bc.setreg_cmd(CommandRegisterOpcode.ADCMEASURE)
            ru.wait(int(160e6*0.01)) # 5 ms
            time.sleep(0.01)
            for ch in chips:
                results['CHIP_{:02d}'.format(ch.chipid)][adc].append(ch.getreg_adc_avss_value()[0])
    if type(only_inputs) == list and 'AVDD_indirect' not in only_inputs:
        return results
    # indirect measurement AVDD
    ch_bc.setreg_VTEMP(200)
    ru.wait(int(160e6*0.01))
    time.sleep(0.01)
    ch_bc.setreg_analog_monitor_and_override(VoltageDACSel=8, CurrentDACSel=0,SWCNTL_DACMONI=0,
                                             SWCNTL_DACMONV=0, IRefBufferCurrent=2)
    ch_bc.setreg_adc_ctrl(Mode=0, SelInput=5, SetIComp=2, RampSpd=1, CompOut=0,
                          DiscriSign=DiscriSign, HalfLSBTrim=HalfLSBTrim)
    for s in range(n_samples):
        ch_bc.setreg_cmd(CommandRegisterOpcode.ADCMEASURE)
        ru.wait(int(160e6*0.01)) # 5 ms
        time.sleep(0.01)
        for ch in chips:
            results['CHIP_{:02d}'.format(ch.chipid)]['AVDD_indirect'].append(ch.getreg_adc_avss_value()[0])
    return results


#__________________________________________________________________
def compensate_voltage_drop(ru: RU, pu: PU, module, dvset, avset, r):
    ''' Compensate for cable voltage drop. '''
    log = logging.getLogger(LOG_NAME)
    assert 0 <= module and module <= 7
    assert 1.62<dvset and dvset<1.98 # in V, desired voltage at the middle of HIC
    assert 1.62<avset and avset<1.98 # in V, desired voltage at the middle of HIC
    assert type(r) is dict # format e.g. r={'dvdd': 0.3, 'avdd': 1.0} in Ohm

    meas = pu.get_values_module(module)
    log.debug('Voltage drop compensation reads {}: '.format(ru.name)+json.dumps(meas))

    dv = pu._code_to_vpower(meas[f'module_{module}_dvdd_voltage'])
    av = pu._code_to_vpower(meas[f'module_{module}_avdd_voltage'])
    di = pu._code_to_i(     meas[f'module_{module}_dvdd_current'])
    ai = pu._code_to_i(     meas[f'module_{module}_avdd_current'])
    new_dv = dvset + 0.001*di*(sum([v for k,v in r.items() if 'dvdd' in k or 'dgnd' in k]))
    new_av = avset + 0.001*ai*(sum([v for k,v in r.items() if 'avdd' in k or 'agnd' in k]))

    log.info('Compensating voltage drop to get {:.3f} DVDD, {:.3f} AVDD. '.format(dvset, avset) +
             'DVDD: {:.3f}->{:.3f}V, AVDD: {:.3f}->{:.3f}V.'.format(dv, new_dv, av, new_av))
    if pu.adjust_output_voltage(module=module, dvdd=new_dv, avdd=new_av, max_iterations=50, max_voltage_diff=0.015) is False:
        log.error(pu.name+': setting new voltage failed! The new voltage might be wrong!')

    meas = pu.get_values_module(module)
    log.debug('Power reads after voltage drop compensation {}:\n'.format(ru.name)+json.dumps(meas))


# _______VERY OLD CODE______________

#__________________________________________________________________
def find_pu_connected_modules(pu: PU):
    log = logging.getLogger(LOG_NAME)
    '''Find out which PU channels are connected
    by powering on and checking digital current'''
    pu.initialize()
    modules = list(range(8))
    pu.setup_power_modules(module_list=modules, dvdd=1.8, avdd=1.8, bb=0)
    pu.power_on_modules(module_list=modules, backbias_en=0)
    time.sleep(1)
    meas = pu.get_values_modules(module_list=modules)
    pu.power_off_all()
    if meas['power_enable_status'] != 0xFFFF:
        log.error('Some modules tripped! Please check! '+str(meas['power_enable_status'])+
                  ' instead of '+str(0xFFFF))
        return []
    connected_modules = [m for m in modules if pu._code_to_i(meas['module_%d_dvdd_current' % m]) > 10]
    return connected_modules


#__________________________________________________________________
def check_communication_with_stave(ru: RU):
    log = logging.getLogger(LOG_NAME)
    ru.alpide_control.enable_dclk()
    time.sleep(0.5)
    ch = Alpide(ru, chipid=0x0)
    ch.write_opcode(Opcode.GRST)
    ch.write_opcode(Opcode.PRST)
    print('-'*50, ru.name, '-'*50)
    try:
        ch.getreg_mode_ctrl()
        check = True
    except userdefinedexceptions.ChipidMismatchError:
        check = False
    except:
        check = False
        log.error('Unexpected exception in communication with stave')
        raise
    ru.alpide_control.disable_dclk()
    return check


#__________________________________________________________________
def determine_ru_pu_connections(ru_list: List[RU], pu_list: List[PU]):
    con_rus = []
    skip_mod = {pu:[] for pu in pu_list}
    ret = []
    for pu in pu_list:
        print('*'*50, pu.name, '*'*50)
        #pu.initialize()
        #for m in [mod for mod in range(8) if mod not in skip_mod[pu]]:
        for m in range(1):
            pu.setup_power_module(module=m, dvdd=1.8, avdd=1.8, bb=0)
            time.sleep(0.1)
            pu.power_on_module(module=m, backbias_en=0)
            time.sleep(0.5)
            pu.log_values_module(module=m)
            meas = pu.get_values_module(module=m)
            if pu._code_to_i(meas['module_%d_dvdd_current'%m]) > 10:
                ru = next((ru for ru in [r for r in ru_list if r not in con_rus]
                           if check_communication_with_stave(ru)), None)
                if ru:
                    con_rus.append(ru)
                    skip_mod[pu].append(m)
                    ret.append([ru, pu, m])
            else:
                skip_mod[pu].append(m)
            pu.power_off_all()
            time.sleep(0.2)
            pu.controller.disable_power_interlock()
            if len(con_rus) == len(ru_list): break
        if len(con_rus) == len(ru_list): break
    print('Connected RUs:', [ru.name for ru in con_rus])
    print('Not connected:', [ru.name for ru in ru_list if ru not in con_rus])
    for t in ret:
        print(t[0].name, t[1].name, t[2])
    return ret
