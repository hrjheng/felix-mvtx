"""VCASN tuning scan (to be called from obtest.py)

Inherits from ThresholdScan
"""

import configparser
import jsonpickle
import os
import sys
import time
import logging

script_path = os.path.dirname(os.path.realpath(__file__))
modules_path = os.path.join(
    script_path, '../../modules/board_support_software/software/py/')
sys.path.append(modules_path)

from testbench import LayerList
from daq_test import DaqTest, RuTriggeringMode
from pALPIDE import Alpide
import trigger_handler

import crate_mapping
from daq_test_configurator import DaqTestConfig
from threshold_scan import ThresholdScan, ThresholdConfig

class ThresholdTune(ThresholdScan):
    """VCASN or ITHR tuning scans using a fixed charge. Data must be decoded to extract the optimum parameter.
    """
    def __init__(self, testbench=None, name="Threshold Tuning"):
        super().__init__(testbench=testbench, name=name);
        self._is_vcasn_not_ithr = True
        self._value_list = list(range(30, 70, 1))
        self._last = 0

    def load_config(self):
        self.config = ThresholdConfig()

    def set_scan_specific_registers(self):
        target_threshold = 10
        for rdo in self.testbench.rdo_list:
            gbt_channel = rdo.comm.get_gbt_channel()
            stave_ob = self.testbench.stave_ob(gbt_channel)
            for chipid_ext, ch in stave_ob.items():
                if self._is_vcasn_not_ithr:
                    ch.setreg_ITHR(self.config.ITHR, commitTransaction=False)
                ch.setreg_VPULSEH(self.config.VPULSEH, commitTransaction=False)
                ch.setreg_VRESETD(self.config.VRESETD, commitTransaction=False)
                ch.setreg_IDB(self.config.IDB, commitTransaction=False)
                ch.setreg_VPULSEL(self.config.VPULSEH-target_threshold, commitTransaction=True) # 170 is the reset value of VPULSEH
            if not self._is_vcasn_not_ithr:
                self.set_vcasn(rdo)

    def configure_vcasn_all_chips(self, vcasn):
        self.logger.debug(f"Setting VCASN to {vcasn}")
        for rdo in self.testbench.rdo_list:
            ch = Alpide(rdo, chipid=0xF)
            ch.set_all_vcasn_values(vcasn, commitTransaction=False)
            rdo.wait(0xFFFF, commitTransaction=True)

    def configure_ithr_all_chips(self, ithr):
        self.logger.debug(f"Setting ITHR to {ithr}")
        for rdo in self.testbench.rdo_list:
            ch = Alpide(rdo, chipid=0xF)
            ch.setreg_ITHR(ithr, commitTransaction=False)
            rdo.wait(0xFFFF, commitTransaction=True)

    def set_vcasn_ithr_list(self, value_list=None, is_vcasn_not_ithr=True):
        self._value_list = value_list
        self._is_vcasn_not_ithr = is_vcasn_not_ithr

    def scan(self):
        self.threshold_tuning()

    def threshold_tuning(self):
        self._rows = [1,2,254,255,509,510]
        self.scan_start()

        for irow,row in enumerate(self._rows):
            if len(self._rows)<=10 or irow%10==0:
                self.logger.info(f'=============> Row {row:3} <=============')
                last_read = time.time()
                dp = self.read_values(recordPrefetch=False)
                self.print_values(last_read, dp, force_complete_print=True)
            self.scan_row(irow)

        self.scan_end()

    def scan_start(self):
        self.gbt_packer_packet_done_counter = {rdo.get_gbt_channel():3*[0] for rdo in self.testbench.rdo_list}

        self.logger.info(f'Running tuning scan with STEP_ROWS {self.config.STEP_ROWS},  Ninj={self.config.NINJ}')
        self.triggers_sent = 0
        self.last_irow = 0
        self.scan_start_time = time.time()

        self.set_chips_in_configuration_mode(silent=True)

        for rdo in self.testbench.rdo_list:
            ch = Alpide(rdo, chipid=0xF)
            for i in range(512):
                ch.mask_row(i)
                ch.pulse_row_disable(i)
            ch.region_control_register_unmask_all_double_columns(broadcast=False)

    def scan_row(self, irow):
        if self.config.TRIGGER_SOURCE != trigger_handler.TriggerSource.SEQUENCER:
            raise NotImplementedError("Not supported any longer")

        if not self.config.DRY:
            self.set_chips_in_configuration_mode(silent=True)
            for rdo in self.testbench.rdo_list:
                ch = Alpide(rdo, chipid=0xF)
                if irow > 0:
                    ch.mask_row(self._rows[irow-1], commitTransaction=False)
                    ch.pulse_row_disable(self._rows[irow-1], commitTransaction=False)
                ch.unmask_row(self._rows[irow], commitTransaction=False)
                ch.pulse_row_enable(self._rows[irow], commitTransaction=False)

        for value in self._value_list:
            for rdo in self.testbench.rdo_list:
                if not self.config.DRY:
                    # Sets the ALPIDE parameters relative to the charge to be injected
                    self.set_chips_in_configuration_mode(rdo=rdo, silent=True)
                    ch = Alpide(rdo, chipid=0xF)
                    if self._is_vcasn_not_ithr:
                        self.configure_vcasn_all_chips(value)
                    else:
                        self.configure_ithr_all_chips(value)
                    self.set_chips_in_triggered_mode(rdo=rdo, silent=True)

                # Sets the data into the calibration lane (Calibration Data Word = CDW)
                # From private discussion between @freidt and @mlupi
                # Maskstage (row) in the 15:0 and setting in 31:16, 47:32 reserved for future use.
                reserved  = (0     & 0xFFFF)<<32
                settings  = (value & 0xFFFF)<<16
                maskstage = (irow  & 0xFFFF)<<0
                cdw_user_field = reserved | settings | maskstage
                rdo.calibration_lane.set_user_field(cdw_user_field)
                rdo.calibration_lane.read(0) # waits for all commands to be executed before advancing

                # Starts a certain number of TF (injections)
                rdo.trigger_handler.sequencer_set_number_of_timeframes(self.config.NINJ)

            wait25ns = int(self.config.NINJ*self.config.TRIGGER_HBF_PER_TF*3564/self.config.TRIGGER_PERIOD_BC)
            self.testbench.rdo_list[0].wait(wait25ns*4)
            time.sleep(wait25ns*25.e-9)


            self.triggers_sent+=self.config.NINJ

            # Polling whether the injections have been sent out
            done = False
            retries = 0
            max_retries = 500
            while not done:
                done = True
                time.sleep(0.01)
                for rdo in self.testbench.rdo_list:
                    done &= rdo.trigger_handler.sequencer_is_done_timeframes()
                    self.logger.debug(f"Done {done}, single {rdo.trigger_handler.sequencer_is_done_timeframes()}, TF left {rdo.trigger_handler.sequencer_get_number_of_timeframes()}, retries {retries}")
                retries += 1
                if retries >= max_retries:
                    self.logger.warning(f"Ending at {max_retries} retries...")
                    self.logger.warning(f"This is a demonstrator code, so it is okay, in a real thresholdscan it is not okay.")
                    self.test_pass = False
                    break

            # After all the triggers were sentm we need to check that all the data were received.
            done = False
            retries = 0
            max_retries = 500
            while not done:
                done = True
                time.sleep(0.01)
                for rdo in self.testbench.rdo_list:
                    c = rdo.gbt_packer.read_counter("PACKET_DONE")
                    for packer, value in enumerate(c):
                        if self.config.LAYER in [LayerList.MIDDLE,LayerList.OUTER] and packer==2:
                            continue # skip when not using this packer
                        # Note the >= in the next line.
                        # This allows continuing taking data for issues such as
                        # RU_mainFPGA#339 (solved)
                        # The >= line allows running, but the test will fail!
                        done_packer = value-self.gbt_packer_packet_done_counter[rdo.get_gbt_channel()][packer]>=self.config.NINJ
                        if value-self.gbt_packer_packet_done_counter[rdo.get_gbt_channel()][packer]>self.config.NINJ:
                            self.test_pass = False # RU_mainFPGA#339
                        done &= done_packer
                        self.logger.debug(f"Done {done}\t{rdo.identity.get_stave_name()} packer {packer}: done {done_packer},\tvalue {value:3}/{self.gbt_packer_packet_done_counter[rdo.get_gbt_channel()][packer]+self.config.NINJ:3}, retries {retries:3}")
                retries += 1
                if retries >= max_retries:
                    self.logger.warning(f"Ending at {max_retries} retries...")
                    self.logger.warning(f"This is a demonstrator code, so it is okay, in a real thresholdscan it is not okay.")
                    self.test_pass = False # RU_mainFPGA#339
                    break

            # Done reading, now update the counter
            self.gbt_packer_packet_done_counter = {rdo.get_gbt_channel():rdo.gbt_packer.read_counter("PACKET_DONE") for rdo in self.testbench.rdo_list}

            if not self.config.DRY:
                self.set_chips_in_configuration_mode(silent=True)
