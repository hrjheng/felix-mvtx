#!/usr/bin/env python3.9

"""Threshold scan

Inherits from daq_test
"""

import os
import sys
import time
import yaml
import argparse

script_path = os.path.dirname(os.path.realpath(__file__))
modules_path = os.path.join(
    script_path, '../../modules/board_support_software/software/py/')
sys.path.append(modules_path)

import trigger_handler

from daq_test import DaqTest, RuTriggeringMode
from pALPIDE import Alpide
# TODO: replace
#from trigger_handler import TrigSourceMask
from testbench import LayerList

from daq_test_configurator import DaqTestConfig

class ThresholdConfig(DaqTestConfig):
    def __init__(self, only_warn=False):
        super().__init__(only_warn=only_warn)
        self.ITHR                         = None
        self.VCASN                        = None
        self.VCASN2                       = None
        self.VPULSEH                      = None
        self.VRESETD                      = None
        self.IDB                          = None
        self.NINJ                         = None
        self.START_CHARGE                 = None
        self.END_CHARGE                   = None
        self.FRAME_DURATION               = None
        self.FRAME_GAP                    = None
        self.PULSE_DELAY                  = None
        self.PULSE_DURATION               = None
        self.STEP_ROWS                    = None
        self.rows = []

    def _load_config(self):
        super()._load_config()
        self._configure_threshold()

    def _configure_threshold(self):
        """Configures a specific section of the test"""
        self._section = 'THRESHOLD'
        self.START_CHARGE   = self._get_config_int('START_CHARGE')
        self.END_CHARGE     = self._get_config_int('END_CHARGE')
        self.NINJ           = self._get_config_int('NINJ')
        self.VCASN          = self._get_config_int('VCASN')
        self.VCASN2         = self._get_config_int('VCASN2')
        self.VPULSEH        = self._get_config_int('VPULSEH')
        self.VRESETD        = self._get_config_int('VRESETD')
        self.IDB            = self._get_config_int('IDB')
        self.FRAME_DURATION = self._get_config_int('FRAME_DURATION')
        self.FRAME_GAP      = self._get_config_int('FRAME_GAP')
        self.PULSE_DELAY    = self._get_config_int('PULSE_DELAY')
        self.PULSE_DURATION = self._get_config_int('PULSE_DURATION')
        self.ITHR           = self._get_config_int('ITHR')
        self.STEP_ROWS      = self._get_config_int('STEP_ROWS')

        assert self.STEP_ROWS in range(512)
        self.rows = [row for row in range(0, 512, self.STEP_ROWS)]


        # overrides configuration: this test can only run with the sequencer
        # and it shall be set to
        self.TRIGGER_SOURCE  = trigger_handler.TriggerSource.SEQUENCER
        self.TRIGGERING_MODE = RuTriggeringMode.TRIGGERED_SEQ
        # reduce the HB frequency by a factor of 10 to stay below 2.5 kHz for the OB
        self.TRIGGER_PERIOD_BC  = 3564 # 11 kHz
        self.TRIGGER_HBF_PER_TF = 128
        self.TRIGGER_HBA_PER_TF = 1
        self.TRIGGER_TF         = self.NINJ
        self.DRY                = False # Does not work in dry run mode

    def _configure_alpide(self):
        super()._configure_alpide()
        # Hardcoded overwrite of what is loaded from config file
        self.ANALOGUE_PULSING         = True
        self.PULSE_TO_STROBE          = True
        self.SEND_PULSES              = True
        self.ENABLE_STROBE_GENERATION = False

    def store_scan_specific_config(self, cfg):
        cfg['ITHR']                     = self.ITHR
        cfg['VCASN']                    = self.VCASN
        cfg['VCASN2']                   = self.VCASN2
        cfg['VPULSEH']                  = self.VPULSEH
        cfg['VRESETD']                  = self.VRESETD
        cfg['IDB']                      = self.IDB
        cfg['NINJ']                     = self.NINJ
        cfg['START_CHARGE']             = self.START_CHARGE
        cfg['END_CHARGE']               = self.END_CHARGE
        cfg['FRAME_DURATION']           = self.FRAME_DURATION
        cfg['FRAME_GAP']                = self.FRAME_GAP
        cfg['PULSE_DELAY']              = self.PULSE_DELAY
        cfg['PULSE_DURATION']           = self.PULSE_DURATION
        cfg['STEP_ROWS']                = self.STEP_ROWS
        return cfg


class ThresholdScan(DaqTest):
    def __init__(self, testbench=None, name="Threshold Scan"):
        super().__init__(testbench=testbench, name=name)

        self.logger.warning(f"{name} uses hard-coded trigger configuration")

        # Data member to track the number of detector events readout
        self.gbt_packer_packet_done_counter = None

    def load_config(self):
        self.config = ThresholdConfig()

    def set_scan_specific_registers(self):
        if not self.config.DRY:
            for rdo in self.testbench.rdo_list:
                gbt_channel = rdo.comm.get_gbt_channel()
                ch = self.testbench.chip_broadcast_dict[gbt_channel]
                ch.setreg_VPULSEH(self.config.VPULSEH, commitTransaction=False)
                self.set_ithr(rdo)
                ch.setreg_VRESETD(self.config.VRESETD, commitTransaction=False)
                ch.setreg_IDB(self.config.IDB, commitTransaction=True)
                self.set_vcasn(rdo)
                ch.send_PRST(commitTransaction=True)

    def set_scan_specific_trigger_registers(self):
        if not self.config.DRY:
            for rdo in self.testbench.rdo_list:
                gbt_channel = rdo.comm.get_gbt_channel()
                ch = self.testbench.chip_broadcast_dict[gbt_channel]
                ch.setreg_fromu_cfg_2(self.config.FRAME_DURATION, commitTransaction=False)
                ch.setreg_fromu_cfg_3(self.config.FRAME_GAP, commitTransaction=False)
                ch.setreg_fromu_pulsing1(self.config.PULSE_DELAY, commitTransaction=False)
                ch.setreg_fromu_pulsing_2(self.config.PULSE_DURATION, commitTransaction=True)

    def calculate_detector_timeout_bc(self):
        """Calculates the detector timeout value based on the daq_test.
        The method is designed to be overrides it for the THS"""
        detector_timeout_bc = self.config.FRAME_DURATION + self.config.PULSE_DELAY + self.config.PULSE_DURATION + 200
        return detector_timeout_bc

    def setup_scan_specific_trigger_handler(self):
        """Overrides the configuration of the trigger handler
        Avoids having periodic triggers in the first row injection"""
        for rdo in self.testbench.rdo_list:
            rdo.trigger_handler.sequencer_set_number_of_timeframes(0)
            rdo.trigger_handler.dump_config()
            timebase_sync = rdo.trigger_handler.is_timebase_synced()
            msg = f"{rdo.identity.get_stave_name()} not in sync!"
            self.timebase_sync_at_start = True
            if (self.config.TRIGGER_SOURCE == trigger_handler.TriggerSource.GBTx2) & self.config.USE_GTM:
                pass  # all good here
            elif self.config.TRIGGER_SOURCE == trigger_handler.TriggerSource.GBTx2:
                assert timebase_sync, msg
            elif self.config.TRIGGER_SOURCE == trigger_handler.TriggerSource.SEQUENCER:
                if timebase_sync:
                    pass # all good here
                else:
                    self.timebase_sync_at_start = False
                    self.logger.warning(msg)
            else:
                raise NotImplementedError

    def setup_scan_specific_gbt_packer(self):
        """Method designed to be overriden in daugher classes to tweak the
        configuration of the gbt_packer"""
        if self.config.LAYER in [LayerList.INNER, LayerList.NO_PT100]:
            pass
        elif self.config.LAYER in [LayerList.MIDDLE,LayerList.OUTER]:
            for rdo in self.testbench.rdo_list:
                # value to be tuned
                rdo.gbt_packer.set_timeout_start_stop(0xFFFF)
        else:
            raise NotImplementedError

    def scan(self):
        self.threshold_scan()

    def threshold_scan(self):
        self.scan_start()

        print_row = 1
        for irow,row in enumerate(self.config.rows):
            self.logger.info(f'=============> Row {row:3} <=============')
            self.scan_row(irow)
            if len(self.config.rows)<=print_row or irow%print_row==0:
                last_read = time.time()
                dp = self.read_values(recordPrefetch=False)
                self.print_values(last_read, dp, force_complete_print=True)

        self.scan_end()

    def scan_start(self):
        # initialises the counters for the gbt packer packet_done to 0 for the three gbt packers
        # in OB scenario, only two of them will be used, but the same data member is used for IB and OB
        self.gbt_packer_packet_done_counter = {rdo.get_gbt_channel():3*[0] for rdo in self.testbench.rdo_list}

        self.logger.info(f'Running threshold scan with STEP_ROWS {self.config.STEP_ROWS}, Charge={self.config.START_CHARGE}..{self.config.END_CHARGE}, Ninj={self.config.NINJ}')
        time.sleep(1)
        self.triggers_sent = 0
        self.last_irow = 0
        self.scan_start_time = time.time()

        if not self.config.DRY:
            self.set_chips_in_configuration_mode(silent=True)

            for rdo in self.testbench.rdo_list:
                ch = Alpide(rdo, chipid=0xF)
                for i in range(512):
                    ch.mask_row(i)
                    ch.pulse_row_disable(i)
                ch.region_control_register_unmask_all_double_columns(broadcast=False)

    def scan_end(self):
        if not self.config.DRY:
            self.set_chips_in_configuration_mode(silent=True)

        # Prevents the calibration data word to appear in following runs
        for rdo in self.testbench.rdo_list:
            rdo.calibration_lane.reset()

        dur = time.time()-self.scan_start_time
        print('Threshold scan completed in {:.2f}s. Total triggers sent: {:d}'.format(dur, self.triggers_sent))

    def scan_row(self, irow):
        if self.config.TRIGGER_SOURCE != trigger_handler.TriggerSource.SEQUENCER:
            raise NotImplementedError("Not supported any longer")

        if not self.config.DRY:
            self.set_chips_in_configuration_mode(silent=True)
            for rdo in self.testbench.rdo_list:
                ch = Alpide(rdo, chipid=0xF)
                if irow > 0:
                    ch.mask_row(self.config.rows[irow-1], commitTransaction=False)
                    ch.pulse_row_disable(self.config.rows[irow-1], commitTransaction=False)
                ch.unmask_row(self.config.rows[irow], commitTransaction=False)
                ch.pulse_row_enable(self.config.rows[irow], commitTransaction=False)

        for dv in range(self.config.START_CHARGE, self.config.END_CHARGE):
            for rdo in self.testbench.rdo_list:
                if not self.config.DRY:
                    # Sets the ALPIDE parameters relative to the charge to be injected
                    self.set_chips_in_configuration_mode(rdo=rdo,silent=True)
                    ch = Alpide(rdo, chipid=0xF)
                    ch.setreg_VPULSEL(170-dv, commitTransaction=False)
                    rdo.wait(0xFFFF, commitTransaction=True)

                    self.set_chips_in_triggered_mode(rdo=rdo,silent=True)

                # Sets the data into the calibration lane (Calibration Data Word = CDW)
                # From private discussion between @freidt and @mlupi
                # Maskstage (row) in the 15:0 and setting in 31:16, 47:32 reserved for future use.
                reserved  = (0    & 0xFFFF)<<32
                settings  = (dv   & 0xFFFF)<<16
                maskstage = (irow & 0xFFFF)<<0
                cdw_user_field = reserved | settings | maskstage
                rdo.calibration_lane.set_user_field(cdw_user_field)
                rdo.calibration_lane.read(0) # waits for all commands to be executed before advancing

                # Starts a certain number of TF (injections)
                time.sleep(0.01)
                rdo.trigger_handler.sequencer_set_number_of_timeframes(self.config.NINJ)

            wait25ns = int(self.config.NINJ*self.config.TRIGGER_HBF_PER_TF*3564/self.config.TRIGGER_PERIOD_BC)
            self.testbench.rdo_list[0].wait(wait25ns*4)
            time.sleep(wait25ns*25.e-9)

            self.triggers_sent+=self.config.NINJ

            # Polling to check that the injection is finished
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
                    self.logger.warning(f"Ending wait for sequencer_is_done_timerames at {max_retries} retries...")
                    self.logger.warning(f"This is a demonstrator code, so it is okay, in a real thresholdscan it is not okay.")
                    self.test_pass = False
                    break

            # After all the triggers were sent we need to check that all the data were received.
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
                            self.logger.warning(f"Test not passing because packet_done > NINJ: {value-self.gbt_packer_packet_done_counter[rdo.get_gbt_channel()][packer]}>{self.config.NINJ}")
                            self.test_pass = False # RU_mainFPGA#339
                        done &= done_packer
                        self.logger.debug(f"Done {done}\t{rdo.identity.get_stave_name()} packer {packer}: done {done_packer},\tvalue {value:3}/{self.gbt_packer_packet_done_counter[rdo.get_gbt_channel()][packer]+self.config.NINJ:3}, retries {retries:3}")
                retries += 1
                if retries >= max_retries:
                    self.logger.warning(f"Ending waiting for correct packet_done_counter at {max_retries} retries...")
                    self.logger.warning(f"This is a demonstrator code, so it is okay, in a real thresholdscan it is not okay.")
                    self.test_pass = False # RU_mainFPGA#339
                    break

            # Done reading, now update the counter
            self.gbt_packer_packet_done_counter = {rdo.get_gbt_channel():rdo.gbt_packer.read_counter("PACKET_DONE") for rdo in self.testbench.rdo_list}

            if not self.config.DRY:
                self.set_chips_in_configuration_mode(silent=True)


if __name__ == '__main__':

    assert sys.version_info > (3, 0), "Only Python 3 supported, did you remember to first run \'module load ReadoutCard/vX.YY.Z-1\'"
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config_file", required=False, help="Configuration file relative path", default=None)
    args = parser.parse_args()

    ts = ThresholdScan()
    ts.setup_logging()
    ts.configure_run(args.config_file)
    ts.initialize_testbench()

    ts.logger.info("Start new Run")

    ts.testbench.setup_cru()

    if ts.config.USE_LTU:
        ts.testbench.setup_ltu()

    ts.setup_comms()

    ts.logger.debug(f"Initialised comms {ts.testbench.comm_rdo_list}")
    try:
        ts.testbench.cru.initialize()
        if ts.config.USE_LTU:
            assert ts.testbench.ltu.is_ltu_on(), "LTU communication failed"
        try:
            ts.testbench.setup_rdos(connector_nr=ts.config.MAIN_CONNECTOR)
            ts.logger.debug(f"Started rdos {ts.testbench.rdo_list}")
            ts.testbench.initialize_all_rdos()
            ts.testbench.cru.initialize()
            for rdo in ts.testbench.rdo_list:
                gbt_channel = rdo.get_gbt_channel()
                if ts.config.PA3_READ_VALUES or ts.config.PA3_SCRUBBING_ENABLE:
                    ts.testbench.cru.pa3.initialize()
                    ts.testbench.cru.pa3.config_controller.clear_scrubbing_counter()
                if ts.config.PA3_SCRUBBING_ENABLE:
                    ts.testbench.cru.pa3.config_controller.start_blind_scrubbing()
                    ts.logger.info(f"Running blind scrubbing on RDO {gbt_channel}")
            ts.test_routine()

        except Exception as e:
            raise e
        finally:
            ts.logger.info("Tearing down")
            ts.tearDown()
    except Exception as e:
        ts.logger.info("Exception in Run")
        ts.logger.info(e,exc_info=True)
        ts.test_pass = False
    finally:
        ts.testbench.stop()
        ts.stop()

    if ts.test_pass:
        ts.logger.info("Test passed!")
    else:
        ts.logger.warning("Test failed! Check logs to find out why.")
