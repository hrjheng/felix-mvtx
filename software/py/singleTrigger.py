#!/usr/bin/env python

from daq_test import DaqTest

import argparse
import jsonpickle
import configparser
import time
import os
import sys
import logging

script_path = os.path.dirname(os.path.realpath(__file__))
modules_path = os.path.join(
    script_path, '../../modules/board_support_software/software/py/')
sys.path.append(modules_path)

from pALPIDE import Alpide
#from trigger_handler import TrigSourceMask


class single(DaqTest):

    # stave wide settings
    def set_chip_registers_threshold(self):
        """Values from new-alpide-software threshold scan"""
        gbt_channel = self.testbench.rdo_list[0].comm.get_gbt_channel()
        stave_ob = self.testbench.stave_ob(gbt_channel)
        for chipid_ext, ch in stave_ob.items():
            ch.setreg_VCASN(self.config.VCASN, commitTransaction=False)
            ch.setreg_VCASN2(self.config.VCASN2, commitTransaction=False)
            ch.setreg_ITHR(self.config.ITHR, commitTransaction=False)
            ch.setreg_VPULSEH(self.config.VPULSEH, commitTransaction=False)
            ch.setreg_VRESETD(self.config.VRESETD, commitTransaction=False)
            ch.setreg_IDB(self.config.IDB, commitTransaction=False)
            # set frame and pulsing to allow for charge to propagate
            #ch.setreg_fromu_cfg_2(self.config.FRAME_DURATION, commitTransaction=False)
            #ch.setreg_fromu_cfg_3(self.config.FRAME_GAP, commitTransaction=False)
            #ch.setreg_fromu_pulsing1(self.config.PULSE_DELAY, commitTransaction=False)
            #ch.setreg_fromu_pulsing_2(self.config.PULSE_DURATION, commitTransaction=False)

    def dump_chip_config(self, filename):
        gbt_channel = self.testbench.rdo_list[0].comm.get_gbt_channel()
        file = open(os.path.join(self.logdir, filename), 'w+')
        stave_ob = self.testbench.stave_ob(gbt_channel)
        for chipid_ext, ch in stave_ob.items():
            if chipid_ext not in self.config.EXCLUDED_SLAVE_CHIPIDEXT_LIST:
                file.write(f"---{chipid_ext}---")
                file.write(ch.dump_config())
        file.close()

    def append_config(self, config_file):

        con = configparser.ConfigParser()
        con.read(config_file)

        self.config.START_CHARGE = int(con['THRESHOLD']['START_CHARGE'])
        self.config.END_CHARGE = int(con['THRESHOLD']['END_CHARGE'])
        self.config.NINJ = int(con['THRESHOLD']['NINJ'])
        self.config.VCASN = int(con['THRESHOLD']['VCASN'])
        self.config.VCASN2 = int(con['THRESHOLD']['VCASN2'])
        self.config.VPULSEH = int(con['THRESHOLD']['VPULSEH'])
        self.config.VRESETD = int(con['THRESHOLD']['VRESETD'])
        self.config.IDB = int(con['THRESHOLD']['IDB'])
        self.config.FRAME_DURATION = int(con['THRESHOLD']['FRAME_DURATION'])
        self.config.FRAME_GAP = int(con['THRESHOLD']['FRAME_GAP'])
        self.config.PULSE_DELAY = int(con['THRESHOLD']['PULSE_DELAY'])
        self.config.PULSE_DURATION = int(con['THRESHOLD']['PULSE_DURATION'])
        self.config.ITHR = int(con['THRESHOLD']['ITHR'])
        self.config.PRE_DAC = int(con['ALPIDE']['PRE_DAC'])
        self.config.PLL_DAC = int(con['ALPIDE']['PLL_DAC'])
        self.config.DRIVER_DAC = int(con['ALPIDE']['DRIVER_DAC'])
        self.config.DISABLE_MANCHESTER = con.getboolean('ALPIDE', 'DISABLE_MANCHESTER')
        #self.config.EXCLUDED_CHIPIDEXT_LIST = list(con['ALPIDE']['EXCLUDED_CHIPIDEXT_LIST']) # depreciated in favour of yml
        self.rows = [row for row in range(0,512,11)] #should be 11 step size

    def test_routine(self):
        """Main routine for the test:
        - check FPGA design version
        - configures the readout chain
        - resets the counters
        - start of run
        - periodic readout of counters and status in the RU and CRU (with warnings on conditions)
        - error handling in case of issues (tear down process to identify failure)
        - end of run
        """
        #disable logging info (more severe logs still enabled)
        # logging.disable(logging.INFO)
        print("Starting initialization...")
        self.testbench.cru.check_git_hash_and_date(expected_githash=self.config.GITHASH_CRU)
        for rdo in self.testbench.rdo_list:
            rdo.check_git_hash_and_date(expected_git_hash=self.config.GITHASH_RDO)
        for gbt_ch in self.config.CTRL_AND_DATA_LINK_LIST:
            self.testbench.cru.set_gbt_channel(gbt_channel=gbt_ch)
            self.testbench.cru.sca.initialize()
            self.testbench.cru.pa3.check_git_hash(expected_git_hash=self.config.GITHASH_PA3)
        self.testbench.dna()
        #self.setup_chip_config

        if self.config.READOUT_PROC_ACTIVE:
            print("Starting o2-readout-exe...")
            t0 = time.time()
            self.start_datataking()
            print("Readout started!")

        print("Initializing readout chain...")
        self.initialize_readout_chain() #where sensors are set up
        print("Readout chain initialization done!")

        self.readback_sensors('sensors_start_of_run')

        print("Resetting counters...")
        self.reset_counters()
        print("Counters reset!")
        print('--------------------After Reset counters--------------------')
        last_read = time.time()
        dp = self.read_values(recordPrefetch=False)
        self.print_values(last_read, dp, force_complete_print=True)
        for rdo in self.testbench.rdo_list:
            print(rdo.powerunit_1.log_temperatures())
            print(rdo.powerunit_2.log_temperatures())


        #self.test_dctrl_write()
        #self.test_dctrl_read()

        #print("Dumping chip config...(before run)")
        #self.dump_chip_config(filename="chip_config_before.log")
        print('--------------------After dump config--------------------')
        last_read = time.time()
        dp = self.read_values(recordPrefetch=False)
        self.print_values(last_read, dp, force_complete_print=True)
        for rdo in self.testbench.rdo_list:
            print(rdo.powerunit_1.log_temperatures())
            print(rdo.powerunit_2.log_temperatures())



        self.start_run()
        print('--------------------After start run--------------------')
        last_read = time.time()
        dp = self.read_values(recordPrefetch=False)
        self.print_values(last_read, dp, force_complete_print=True)
        for rdo in self.testbench.rdo_list:
            print(rdo.powerunit_1.log_temperatures())
            print(rdo.powerunit_2.log_temperatures())



        run_error = None

        try:
            self.last_irow = 0
            self.threshold_scan()
        except KeyboardInterrupt as ki:
            self.logger.info("Run ended by user (Keyboard interrupt).")
            self.logger.info(ki,exc_info=True)
            run_error = ki
        except Exception as e:
            self.logger.info("Run finished Due to readout errors.")
            self.logger.info(e,exc_info=True)
            run_error = e

        try:
            self.on_test_stop()
        except Exception as e:
            self.logger.error("Exception while running on_test_stop()")
            self.logger.info(e,exc_info=True)

        # Tear down routine for test
        try:
            #print("Dumping chip config...(after run)")
            #self.dump_chip_config(filename="chip_config_after.log")
            logging.disable(logging.NOTSET)
            self.stop_run()
            #self.test_dctrl_read()
            logging.disable(logging.INFO)
        except Exception as e:
            self.logger.info("Final read_values might be partial (This is ok)")
            self.logger.info(e)

        es = self.handle_failure(run_error)

        with open(self.testrun_exit_status_info,'w') as df:
            df.write(jsonpickle.encode(es))
            df.flush()

    def threshold_scan(self):
        print('--------------------Before scan start--------------------')
        last_read = time.time()
        dp = self.read_values(recordPrefetch=False)
        self.print_values(last_read, dp, force_complete_print=True)
        for rdo in self.testbench.rdo_list:
            print(rdo.powerunit_1.log_temperatures())
            print(rdo.powerunit_2.log_temperatures())

        self.scan_start()
        print('--------------------After scan start--------------------')
        self.rows = [1]
        for irow,row in enumerate(self.rows):
            if len(self.rows)<=10 or irow%1==0:
                print('Row {:d}'.format(row))
                last_read = time.time()
                dp = self.read_values(recordPrefetch=False)
                self.print_values(last_read, dp, force_complete_print=True)
                for rdo in self.testbench.rdo_list:
                    print(rdo.powerunit_1.log_temperatures())
                    print(rdo.powerunit_2.log_temperatures())
            self.scan_row(irow)

        self.scan_end()

    def scan_start(self):
        self.scan_start_time = time.time()
        self.triggers_sent = 0
        self.last_irow = 0

        for rdo in self.testbench.rdo_list:
            ch = Alpide(rdo, chipid=0xF)
            self.set_chip_registers_threshold()
            for i in range(512):
                ch.mask_row(i)
                ch.pulse_row_disable(i)
            time.sleep(0.05)


    def scan_end(self):
        dur = time.time()-self.scan_start_time

    def scan_row(self, irow):
        for rdo in self.testbench.rdo_list:
            ch = Alpide(rdo, chipid=0xF)

            # TODO: Fix
            raise NotImplementedError("Update to new readout!")
            #if self.config.TRIGGER_SOURCE == TrigSourceMask.INJECTOR:
            #    for rdo in self.testbench.rdo_list:
            #        rdo.gbt_word_inject.send_trigger()

            #        if self.config.ONLY_MASTERS:
            #            time.sleep(4e-3)
            #        else:
            #            time.sleep(10e-3)

            #else:
            #    for i in range(self.config.NINJ):
            #        self.testbench.cru.send_physics_trigger()
            #        time.sleep(10000e3*1e-9)
            self.triggers_sent+=self.config.NINJ
        time.sleep(1000*1e-9)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config_file", required=False, help="Configuration file relative path", default=None)
    args = parser.parse_args()

    threshold_scan = single()

    threshold_scan.setup_logging()
    threshold_scan.configure_run(args.config_file)
    threshold_scan.append_config(args.config_file)
    threshold_scan.initialize_testbench()
    threshold_scan.testbench.setup_cru()
    threshold_scan.setup_comms()

    try:
        threshold_scan.testbench.cru.initialize()
        time.sleep(2)
        try:
            threshold_scan.testbench.setup_rdos(connector_nr=threshold_scan.config.MAIN_CONNECTOR)
            threshold_scan.logger.debug(f"Started rdos {threshold_scan.testbench.rdo_list}")
            for rdo in threshold_scan.testbench.rdo_list:
                rdo.initialize()
                gbt_channel = rdo.comm.get_gbt_channel()
                if threshold_scan.config.PA3_READ_VALUES or threshold_scan.config.PA3_SCRUBBING_ENABLE:
                    threshold_scan.testbench.cru.pa3.initialize()
                    threshold_scan.testbench.cru.pa3.config_controller.clear_scrubbing_counter()
                if threshold_scan.config.PA3_SCRUBBING_ENABLE:
                    threshold_scan.testbench.cru.pa3.config_controller.start_blind_scrubbing()
                    threshold_scan.logger.info(f"Running blind scrubbing on RDO {gbt_channel}")
            threshold_scan.test_routine()

        except Exception as e:
            raise e
        finally:
            threshold_scan.logger.info("Tearing down")
            threshold_scan.tearDown()
    except Exception as e:
        threshold_scan.logger.info("Exception in Run")
        threshold_scan.logger.info(e,exc_info=True)
    finally:
        threshold_scan.testbench.stop()
        threshold_scan.stop()
