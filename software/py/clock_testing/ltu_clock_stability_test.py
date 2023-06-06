#!/usr/bin/env python3.6

import subprocess
import json
import logging
from typing_extensions import OrderedDict
import requests
import re
from itertools import zip_longest
import time
import sys
import numpy as np
import signal
import sys

ENABLE_MATTERMOST = True
IN_301 = False
NUM_TESTS = 1000 # 41 is roughly one hour (orbitin and transition)
NUM_ORBITIN_RESET = 1000
NUM_TRANSITION = 100
LTU_TIMEOUT = 300

class MatterMost():

    WEBHOOK_URL = 'https://mattermost.web.cern.ch/hooks/axe1oqyo3igc5f8h77rpqdb1ao'

    payload = {
        "attachments": [
            {
                "text": "",
            }
        ]
    }
    
    @staticmethod
    def send_message(msg):
        if ENABLE_MATTERMOST:
            MatterMost.payload['text'] = f":warning: {msg}"
            requests.post(MatterMost.WEBHOOK_URL, json=MatterMost.payload)

class Crate():

    def __init__(self, hostname, tb):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.hostname = hostname
        self.tb = tb
        self.lol_status = self.get_lol_status()
        self.vtrx_status = self.get_vtrx_status()
        self.reset_status_counters()

    def reset_status_counters(self):
        self.num_lols = 0
        self.num_gbtx0_fec = 0
        self.num_gbtx2_fec = 0

    def update_status(self):
        self.update_lol_status()
        self.update_vtrx_status()
        self.reset_status_counters()

    def _get_tb_cmd(self, cmd):
      return f"cd ogrottvi/CRU_ITS/software/py; {self.tb} {cmd}"

    def get_tb_status(self, cmd, stderr=False):
        self.logger.debug(f"Host: {self.hostname} - TB: {self.tb}")
        ssh = subprocess.Popen(["ssh", "%s" % self.hostname, self._get_tb_cmd(cmd)],
                       shell=False,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
        if stderr:
            output = ssh.stderr.read()
        else:
            output = ssh.stdout.read()
        return str(output.decode('ascii'))

    def get_lol_status(self):
        output = self.get_tb_status(cmd='log_all_lol_counters', stderr=True)
        output = output.split('\n')[:-1]
        output = [line[40:] for line in output]
        output = [re.split('\s+', line) for line in output]
        
        LOL = [{'ch': line[2], 'lol': line[4], 'c2b': line[8]} for line in output]
        return LOL

    def update_lol_status(self):
        self.lol_status = self.get_lol_status()

    def has_lol_changed(self, update=True):
        new_status = self.get_lol_status()
        check = True
        for new, old in zip(new_status, self.lol_status):
            self.num_lols += int(new['lol']) - int(old['lol'])
            if new['lol'] != old['lol'] and new['c2b'] != old['c2b']:
                self.logger.warning(f"{self.format_crate()} - RU {old['ch']} - LOL changed from {old['lol']} to {new['lol']}!")
                self.logger.warning(f"{self.format_crate()} - RU {old['ch']} - C2B changed from {old['c2b']} to {new['c2b']}!")
                check = False
            elif new['lol'] != old['lol']:
                self.logger.warning(f"{self.format_crate()} - RU {old['ch']} - LOL changed from {old['lol']} to {new['lol']}!")
                self.logger.debug(f"{self.format_crate()} - RU {old['ch']} - C2B remained unchanged {old['c2b']}")
                check = False
            elif new['c2b'] != old['c2b']:
                self.logger.debug(f"{self.format_crate()} - RU {old['ch']} - LOL remained unchanged {old['lol']}")
                self.logger.warning(f"{self.format_crate()} - RU {old['ch']} - C2B changed from {old['c2b']} to {new['c2b']}!")
                check = False
            else:
                self.logger.debug(f"{self.format_crate()} - RU {old['ch']} - LOL/C2B remained unchanged {old['lol']}/{old['c2b']}")

        if update:
            self.lol_status = new_status
        return check

    def get_vtrx_status(self):
        output = self.get_tb_status(cmd='log_all_gbtx_status --verbose', stderr=True)
        output = output.split('\n')[:-1]
        output = [line[40:] for line in output]
        rus = self._split_vtrx_status_into_ru_chunks(output)
        vtrx_status = []
        for ru in rus:
            ru = [re.split('\s+', line) for line in ru]
            ru_dict = {'ch': ru[0][1]}
            ru_dict['gbtx0_ref_pll_lol'] = ru[3][8]
            ru_dict['gbtx1_ref_pll_lol'] = ru[3][10]
            ru_dict['gbtx2_ref_pll_lol'] = ru[3][12]
            ru_dict['gbtx0_epll_lol']    = ru[4][8]
            ru_dict['gbtx1_epll_lol']    = ru[4][10]
            ru_dict['gbtx2_epll_lol']    = ru[4][12]
            ru_dict['gbtx0_fec']         = ru[5][7]
            ru_dict['gbtx1_fec']         = ru[5][9]
            ru_dict['gbtx2_fec']         = ru[5][11]
            vtrx_status.append(ru_dict)
        return vtrx_status

    def _split_vtrx_status_into_ru_chunks(self, output):
        iter_ = iter(output)
        return list(zip_longest(iter_, iter_, iter_, iter_, iter_, iter_))

    def update_vtrx_status(self):
        self.vtrx_status = self.get_vtrx_status()

    def has_vtrx_status_changed(self, update=True):
        new_status = self.get_vtrx_status()
        check = True
        for new, old in zip(new_status, self.vtrx_status):
            self.num_gbtx0_fec += int(new['gbtx0_fec']) - int(old['gbtx0_fec'])
            self.num_gbtx2_fec += int(new['gbtx2_fec']) - int(old['gbtx2_fec'])
            check_ru = True
            if new['gbtx0_ref_pll_lol'] != old['gbtx0_ref_pll_lol']:
                self.logger.warning(f"{self.format_crate()} - RU {old['ch']} - gbtx0_ref_pll_lol changed from {old['gbtx0_ref_pll_lol']} to {new['gbtx0_ref_pll_lol']}!")
                check_ru = False
            if new['gbtx1_ref_pll_lol'] != old['gbtx1_ref_pll_lol']:
                self.logger.warning(f"{self.format_crate()} - RU {old['ch']} - gbtx1_ref_pll_lol changed from {old['gbtx1_ref_pll_lol']} to {new['gbtx1_ref_pll_lol']}!")
                check_ru = False
            if new['gbtx2_ref_pll_lol'] != old['gbtx2_ref_pll_lol']:
                self.logger.warning(f"{self.format_crate()} - RU {old['ch']} - gbtx2_ref_pll_lol changed from {old['gbtx2_ref_pll_lol']} to {new['gbtx2_ref_pll_lol']}!")
                check_ru = False
            if new['gbtx0_epll_lol'] != old['gbtx0_epll_lol']:
                self.logger.warning(f"{self.format_crate()} - RU {old['ch']} - gbtx0_epll_lol changed from {old['gbtx0_epll_lol']} to {new['gbtx0_epll_lol']}!")
                check_ru = False
            if new['gbtx1_epll_lol'] != old['gbtx1_epll_lol']:
                self.logger.warning(f"{self.format_crate()} - RU {old['ch']} - gbtx1_epll_lol changed from {old['gbtx1_epll_lol']} to {new['gbtx1_epll_lol']}!")
                check_ru = False
            if new['gbtx2_epll_lol'] != old['gbtx2_epll_lol']:
                self.logger.warning(f"{self.format_crate()} - RU {old['ch']} - gbtx2_epll_lol changed from {old['gbtx2_epll_lol']} to {new['gbtx2_epll_lol']}!")
                check_ru = False
            if new['gbtx0_fec'] != old['gbtx0_fec']:
                self.logger.warning(f"{self.format_crate()} - RU {old['ch']} - gbtx0_fec changed from {old['gbtx0_fec']} to {new['gbtx0_fec']}!")
                check_ru = False
                
            if new['gbtx1_fec'] != old['gbtx1_fec']:
                self.logger.warning(f"{self.format_crate()} - RU {old['ch']} - gbtx1_fec changed from {old['gbtx1_fec']} to {new['gbtx1_fec']}!")
                check_ru = False
            if new['gbtx2_fec'] != old['gbtx2_fec']:
                self.logger.warning(f"{self.format_crate()} - RU {old['ch']} - gbtx2_fec changed from {old['gbtx2_fec']} to {new['gbtx2_fec']}!")
                check_ru = False
                
            if check_ru:
                self.logger.debug(f"{self.format_crate()} - RU {old['ch']} - VTRx status remained unchanged, e.g. Ref PLL LOL GBTx0/GBTx2 {old['gbtx0_ref_pll_lol']}/{old['gbtx2_ref_pll_lol']}")
            else:
                check = False

        if update:
            self.vtrx_status = new_status
        return check

    def format_crate(self):
        return f"{self.hostname} - {self.tb}"


class Hosts():
    base_name = "alio2-cr1-flp"
    
    @staticmethod
    def get_hosts():
        if IN_301:
            return ['flpits11']
        else:
            return [f"{Hosts.base_name}{hostnum}" for hostnum in range(187,188)]

    @staticmethod
    def get_crates():
        if IN_301:
            #return ['./testbench_ibs.py', './testbench_ols.py']
            return ['./testbench_ibs.py']
        else:
            return ['./testbench_l0t_pp1i3.py', './testbench_l0b_pp1o4.py']


class FLP():

    def __init__(self, hostname):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.hostname = hostname
        self.endpoints = []
        self.endpoints.append(Endpoint(hostname, 0))
        self.endpoints.append(Endpoint(hostname, 3))

    def update_status(self):
        for ep in self.endpoints:
            ep.update_status()

    def __str__(self):
        string = ""
        for endpoint in self.endpoints:
            string += str(endpoint) + '\n'
        return string

class Endpoint():

    def __init__(self, hostname, sequence_number):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.hostname = hostname
        self.sequence_number = sequence_number
        self.update_status()
        
    def get_status(self):
        self.logger.debug(f"Host: {self.hostname} - Seq #: {self.sequence_number}")
        ssh = subprocess.Popen(["ssh", "%s" % self.hostname, self._get_roc_status_cmd()],
                       shell=False,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
        return json.loads(str(ssh.stdout.read().decode('ascii')))

    def update_status(self):
        self.status = self.get_status()
        self.check_pon_quality()
        self.onuerror_sticky = self.get_onuerror_sticky()

    def _get_roc_status_cmd(self):
      return f"o2-roc-status --id=#{self.sequence_number} --onu-status --json-out "

    def get_onuerror_sticky(self):
        ssh = subprocess.Popen(["ssh", "%s" % self.hostname, "roc-reg-read --i=#0 --ch=2 --add=0x00200014"],
                       shell=False,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
        output = ssh.stdout.read().decode('ascii').split('\n')[0]
        self.toggle_onuerror_sticky_reset()
        return int(output, 16)

    def toggle_onuerror_sticky_reset(self):
        self._reset_onuerror_sticky()
        time.sleep(0.2)
        self._dereset_onuerror_sticky()
        time.sleep(0.2)

    def _reset_onuerror_sticky(self):
        ssh = subprocess.Popen(["ssh", "%s" % self.hostname, "roc-reg-write --i=#0 --ch=2 --add=0x00200000 --value=0x10000000"],
                        shell=False,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    def _dereset_onuerror_sticky(self):
        ssh = subprocess.Popen(["ssh", "%s" % self.hostname, "roc-reg-write --i=#0 --ch=2 --add=0x00200000 --value=0x0"],
                        shell=False,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)

    def has_onuerror_sticky_changed(self):
        new = self.get_onuerror_sticky()
        if new != self.onuerror_sticky:
            self.logger.warning(f"onuerror_sticky changed from {self.onuerror_sticky} to {new}!")
            self.onuerror_sticky = new
            return True
        else:
            self.logger.debug(f"onuerror_sticky remained unchanged: {new}")
            return False

    def check_pon_quality(self):
        if self.status['PON quality Status'] == 'bad':
            self.logger.warning(f"{self.format_endpoint()} - PON quality is BAD!")

    def has_pon_quality_changed(self, update=True):
        new_status = self.get_status()
        test_status = True
        if new_status['PON quality'] != self.status['PON quality']:
            self.logger.warning(f"{self.format_endpoint()} - PON quality changed from {self.status['PON quality']} to {new_status['PON quality']}!")
            test_status = False
        else:
            self.logger.debug(f"{self.format_endpoint()} - PON quality remained unchanged")
            test_status = True

        if update:
            self.status = new_status
            self.check_pon_quality()
        return test_status

    def format_endpoint(self):
        return f"{self.hostname} - {self.status['serial']}"

class LTU():
  
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        if IN_301:
            self.hostname = 'flpits11'
            self.atb = 30
        else:
            self.hostname = 'alio2-cr1-ctpctr'
            self.atb = 40
        self.seen_missing_burst = 0
        self.mgt_tx_nready = 0
        self.mgt_rx_nready = 0
        self.mgt_pll_nlock = 0
        self.rx_nlock = 0

    def send_cmd(self, cmd):
        ssh = subprocess.Popen(["ssh", "-tt", self.hostname],
                       shell=False,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE,
                       stdin=subprocess.PIPE)

        ssh.stdin.write(cmd)
        try:
            stdout, stderr = ssh.communicate(timeout=LTU_TIMEOUT)
        except:
            self.logger.warning("Timeout when sending command!")

        self.logger.debug("Command sent!")
        return stdout, stderr

    def send_orbitin_reset(self):
        cmds = []
        for i in range(NUM_ORBITIN_RESET):
            cmds.append('fpga orbitin reset')
            cmds.append('sleep 0.1')
        self.send_cmd(self._get_atb_cmd(cmds))
        self.get_sticky_bit()

    def send_reset_outcnts(self):
        cmds = []
        cmds.append('fpga reset outcnts')
        self.send_cmd(self._get_atb_cmd(cmds))
        self.get_sticky_bit()

    def send_global_stdalone(self):
        cmds = []
        cmds.append('fpga global')
        cmds.append('fpga stdalone')
        self.send_cmd(self._get_atb_cmd(cmds))
        self.get_sticky_bit()

    def send_stdalone_global(self):
        cmds = []
        cmds.append('fpga stdalone')
        cmds.append('fpga global')
        self.send_cmd(self._get_atb_cmd(cmds))
        self.get_sticky_bit()

    def send_stdalone_global_stdalone(self):
        cmds = []
        for i in range(NUM_TRANSITION):
            cmds.append('fpga stdalone')
            cmds.append('sleep 0.1')
            cmds.append('fpga global')
            cmds.append('sleep 0.1')
        cmds.append('fpga stdalone')
        self.send_cmd(self._get_atb_cmd(cmds))
        self.get_sticky_bit()

    def _get_atb_cmd(self, cmds):
        c = f'atb {self.atb} << EOF\n'
        for cmd in cmds:
            c += cmd + '\n'
        c += 'q\n'
        c += 'EOF\n'
        c += 'exit\n'
        
        return bytearray(c.encode())

    def _get_ttcpon_cmd(self, cmds):
        c = f'ttcpon its_{self.atb}.net << EOF\n'
        for cmd in cmds:
            c += cmd + '\n'
        c += 'q\n'
        c += 'EOF\n'
        c += 'exit\n'

        return bytearray(c.encode())

    def get_sticky_bit(self):
        self.logger.info("Get/check/clear sticky bits")
        cmds = []
        cmds.append('mondph')
        cmds.append('mondph clear')
        stdout, stderr = self.send_cmd(self._get_ttcpon_cmd(cmds))
        output = stdout.decode('ascii')
        output = output.split('\n')[-6]
        output = re.split('\s+', output)
        self.seen_missing_burst = int(output[1][1])
        self.mgt_tx_nready = int(output[2][0])
        self.mgt_rx_nready = int(output[3][0])
        self.mgt_pll_nlock = int(output[4][0])
        self.rx_nlock = int(output[5][0])
        if self.seen_missing_burst > 0:
            self.logger.warning(f"seen_missing_burst is set")
        else:
            self.logger.debug(f"seen_missing_burst is not set")
        if self.mgt_tx_nready > 0:
            self.logger.warning(f"mgt_tx_nready is set")
        else:
            self.logger.debug(f"mgt_tx_nready is not set")
        if self.mgt_rx_nready > 0:
            self.logger.warning(f"mgt_rx_nready is set")
        else:
            self.logger.debug(f"mgt_rx_nready is not set")
        if self.mgt_pll_nlock > 0:
            self.logger.warning(f"mgt_pll_nlock is set")
        else:
            self.logger.debug(f"mgt_pll_nlock is not set")
        if self.rx_nlock > 0:
            self.logger.warning(f"rx_nlock is set")
        else:
            self.logger.debug(f"rx_nlock is not set")

    def clear_sticky_bit(self):
        cmds = []
        cmds.append('mondph clear')
        self.send_cmd(self._get_ttcpon_cmd(cmds))
        self.seen_missing_burst = 0
        self.mgt_tx_nready = 0
        self.mgt_rx_nready = 0
        self.mgt_pll_nlock = 0
        self.rx_nlock = 0

    def send_ttcpon_init(self):
        c = f'ttcpon its_{self.atb}.net init\n'
        c += 'exit\n'
        self.send_cmd(bytearray(c.encode()))

def test_ttcpon_init(flps, crates, ltu, num_tests):
    logger.info("Starting PON init tests.....")
    test_status = True

    for i in range(num_tests):
        logger.info("Update FLPs status")
        for flp in flps:
            flp.update_status()

        logger.info("Update crate")
        for crate in crates:
            crate.update_status()

        # Provoke LTU
        logger.info("Provoke LTU ttcpon init")
        ltu.send_ttcpon_init()

        logger.info("Check FLPs")
        for flp in flps:
            for endpoint in flp.endpoints:
                endpoint.has_pon_quality_changed()

        logger.info("Check crates")
        for crate in crates:
            crate.has_lol_changed()
            crate.has_vtrx_status_changed()

    logger.info("Test ttcpon_init completed...")
            
def test_orbitin_reset(flps, crates, ltu):
    logger.info("Starting orbitin reset tests.....")
    num_resets = NUM_ORBITIN_RESET * NUM_TESTS
    num_lols = []
    num_gbtx0_fec = []
    num_gbtx2_fec = []
    seen_missing_burst = []
    mgt_tx_nready = []
    mgt_rx_nready = []
    mgt_pll_nlock = []
    rx_nlock = []
    onuerror_sticky = []

    logger.info("LTU: clear sticky bit")
    ltu.clear_sticky_bit()

    logger.info("Update FLPs status")
    for flp in flps:
        flp.update_status()

    logger.info("Update crate")
    for crate in crates:
        crate.update_status()

    for i in range(NUM_TESTS):
        logger.info(f"orbitin reset test {i+1} of {NUM_TESTS}")

        # Provoke LTU
        logger.info(f"Provoke LTU orbitin reset x {NUM_ORBITIN_RESET}")
        ltu.send_orbitin_reset()
        seen_missing_burst.append(ltu.seen_missing_burst)
        mgt_tx_nready.append(ltu.mgt_tx_nready)
        mgt_rx_nready.append(ltu.mgt_rx_nready)
        mgt_pll_nlock.append(ltu.mgt_pll_nlock)
        rx_nlock.append(ltu.rx_nlock)

        logger.info("Check FLPs")
        for flp in flps:
            for endpoint in flp.endpoints:
                if endpoint.has_onuerror_sticky_changed():
                    onuerror_sticky.append(1)
                else:
                    onuerror_sticky.append(0)
                endpoint.has_pon_quality_changed()

        logger.info("Check crates")
        for crate in crates:
            crate.has_lol_changed()
            crate.has_vtrx_status_changed()
            num_lols.append(crate.num_lols)
            num_gbtx0_fec.append(crate.num_gbtx0_fec)
            num_gbtx2_fec.append(crate.num_gbtx2_fec)
            crate.reset_status_counters()

    num_lols = np.array(num_lols)
    num_gbtx0_fec = np.array(num_gbtx0_fec)
    num_gbtx2_fec = np.array(num_gbtx2_fec)
    seen_missing_burst = np.array(seen_missing_burst)
    mgt_tx_nready = np.array(mgt_tx_nready)
    mgt_rx_nready = np.array(mgt_rx_nready)
    mgt_pll_nlock = np.array(mgt_pll_nlock)
    rx_nlock = np.array(rx_nlock)
    onuerror_sticky = np.array(onuerror_sticky)

    logger.info(f"Num LOLs: {num_lols.mean()}+-{num_lols.std()} - per reset {num_lols.mean()/num_resets}+-{num_lols.std()/num_resets}")
    logger.info(f"Num seen_missing_burst: {seen_missing_burst.mean()}+-{seen_missing_burst.std()}")
    logger.info(f"Num mgt_tx_nready: {mgt_tx_nready.mean()}+-{mgt_tx_nready.std()}")
    logger.info(f"Num mgt_rx_nready: {mgt_rx_nready.mean()}+-{mgt_rx_nready.std()}")
    logger.info(f"Num mgt_pll_nlock: {mgt_pll_nlock.mean()}+-{mgt_pll_nlock.std()}")
    logger.info(f"Num rx_nlock: {rx_nlock.mean()}+-{rx_nlock.std()}")
    logger.info(f"Num onuerror_sticky: {onuerror_sticky.mean()}+-{onuerror_sticky.std()}")

    # logger.info(f"Num GBTx0 FEC: {num_gbtx0_fec.mean()}+-{num_gbtx0_fec.std()} - per reset {num_gbtx0_fec.mean()/num_resets}+-{num_gbtx0_fec.std()/num_resets}")
    # logger.info(f"Num GBTx2 FEC: {num_gbtx2_fec.mean()}+-{num_gbtx2_fec.std()} - per reset {num_gbtx2_fec.mean()/num_resets}+-{num_gbtx2_fec.std()/num_resets}")

    logger.info("Test orbitin reset completed")



def test_mode_transition(flps, crates, ltu):
    logger.info("Starting mode transition tests.....")
    num_trans = NUM_TRANSITION * NUM_TESTS
    num_lols = []
    num_gbtx0_fec = []
    num_gbtx2_fec = []
    seen_missing_burst = []
    mgt_tx_nready = []
    mgt_rx_nready = []
    mgt_pll_nlock = []
    rx_nlock = []
    onuerror_sticky = []

    logger.info("LTU: clear sticky bit")
    ltu.clear_sticky_bit()

    logger.info("Update FLPs status")
    for flp in flps:
        flp.update_status()

    logger.info("Update crate")
    for crate in crates:
        crate.update_status()


    for i in range(NUM_TESTS):
        signal.signal(signal.SIGINT, signal.default_int_handler)
        try:
            logger.info(f"mode transition test {i+1} of {NUM_TESTS}")

            # Provoke LTU
            logger.info(f"Provoke LTU stdalone=>global=>stdalone x {NUM_TRANSITION}")
            ltu.send_stdalone_global_stdalone()
            seen_missing_burst.append(ltu.seen_missing_burst)
            mgt_tx_nready.append(ltu.mgt_tx_nready)
            mgt_rx_nready.append(ltu.mgt_rx_nready)
            mgt_pll_nlock.append(ltu.mgt_pll_nlock)
            rx_nlock.append(ltu.rx_nlock)

            logger.info("Check FLPs")
            for flp in flps:
                for endpoint in flp.endpoints:
                    if endpoint.has_onuerror_sticky_changed():
                        onuerror_sticky.append(1)
                    else:
                        onuerror_sticky.append(0)
                    endpoint.has_pon_quality_changed()

            logger.info("Check crates")
            for crate in crates:
                crate.has_lol_changed()
                crate.has_vtrx_status_changed()
                num_lols.append(crate.num_lols)
                num_gbtx0_fec.append(crate.num_gbtx0_fec)
                num_gbtx2_fec.append(crate.num_gbtx2_fec)
                crate.reset_status_counters()
        except KeyboardInterrupt:
            logger.info("Got CTRL-C, trying to exit gracefully...")
            break
        except:
            logger.info("Oh no! Trying to exit gracefully...")
            break


    num_lols = np.array(num_lols)
    num_gbtx0_fec = np.array(num_gbtx0_fec)
    num_gbtx2_fec = np.array(num_gbtx2_fec)
    seen_missing_burst = np.array(seen_missing_burst)
    mgt_tx_nready = np.array(mgt_tx_nready)
    mgt_rx_nready = np.array(mgt_rx_nready)
    mgt_pll_nlock = np.array(mgt_pll_nlock)
    rx_nlock = np.array(rx_nlock)
    onuerror_sticky = np.array(onuerror_sticky)

    logger.info(f"Num LOLs: {num_lols.mean()}+-{num_lols.std()} - per reset {num_lols.mean()/num_trans}+-{num_lols.std()/num_trans}")
    logger.info(f"Num seen_missing_burst: {seen_missing_burst.mean()}+-{seen_missing_burst.std()}")
    logger.info(f"Num mgt_tx_nready: {mgt_tx_nready.mean()}+-{mgt_tx_nready.std()}")
    logger.info(f"Num mgt_rx_nready: {mgt_rx_nready.mean()}+-{mgt_rx_nready.std()}")
    logger.info(f"Num mgt_pll_nlock: {mgt_pll_nlock.mean()}+-{mgt_pll_nlock.std()}")
    logger.info(f"Num rx_nlock: {rx_nlock.mean()}+-{rx_nlock.std()}")
    logger.info(f"Num onuerror_sticky: {onuerror_sticky.mean()}+-{onuerror_sticky.std()}")
    # logger.info(f"Num GBTx0 FEC: {num_gbtx0_fec.mean()}+-{num_gbtx0_fec.std()} - per reset {num_gbtx0_fec.mean()/num_trans}+-{num_gbtx0_fec.std()/num_trans}")
    # logger.info(f"Num GBTx2 FEC: {num_gbtx2_fec.mean()}+-{num_gbtx2_fec.std()} - per reset {num_gbtx2_fec.mean()/num_trans}+-{num_gbtx2_fec.std()/num_trans}")

    logger.info("Test completed!")

def test_stable(flps, crates):
    logger.info("Starting stable tests.....")
    test_status = True
    num_checks = 0
    num_fails = 0

    logger.info("Update FLPs status")
    for flp in flps:
        flp.update_status()

    logger.info("Update crate")
    for crate in crates:
        crate.update_lol_status()
        crate.update_vtrx_status()

    for i in range(NUM_TESTS):
        logger.info(f"Stable test {i+1} of {NUM_TESTS}")
        

        # Provoke LTU
        logger.info("Wait 1 min")
        time.sleep(60)

        logger.info("Check FLPs")
        for flp in flps:
            for endpoint in flp.endpoints:
                num_checks += 1
                if endpoint.has_pon_quality_changed() is False:
                    test_status = False
                    num_fails += 1

        logger.info("Check crates")
        for crate in crates:
            num_checks += 2
            if crate.has_lol_changed() is False:
                test_status = False
                num_fails += 1
            if crate.has_vtrx_status_changed() is False:
                test_status = False
                num_fails += 1

    if test_status:
        logger.info("Test completed sucessfully!")
    else:
        logger.info(f"Test failed {num_fails} of {num_checks}!")

if __name__ == '__main__':
    FORMAT = '%(asctime)-15s %(levelname)s %(name)s:%(funcName)s - %(message)s'
    file_handler = logging.FileHandler('debug.log')
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    logging.basicConfig(
        level=logging.DEBUG,
        format=FORMAT,
        handlers=[
            file_handler,
            console_handler
        ]
    )
    
    logger = logging.getLogger("main")

    crates = []
    for hostname in Hosts.get_hosts():
        for crate in Hosts.get_crates():
            crates.append(Crate(hostname, crate))

    ltu = LTU()
    
    
    flps = []
    for flp in Hosts.get_hosts():
        flps.append(FLP(flp))

    # test_stable(flps, crates)
    # test_orbitin_reset(flps, crates, ltu)
    test_mode_transition(flps, crates, ltu)
    # test_ttcpon_init(flps, crates, ltu, NUM_TESTS)
    
