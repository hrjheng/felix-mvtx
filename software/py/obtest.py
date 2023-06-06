#!/usr/bin/env python3.9

# builtin
import argparse
import os
import time
import sys

# imports
import logging
import yaml

# local from x import
from fakehitrate import FakeHitRate
from pALPIDE import Alpide, AdcIndex, Addr, Opcode
from power_unit import Layer
from threshold_scan import ThresholdScan
from threshold_tune import ThresholdTune
from dcol_tester import DColTester
from daq_test import DaqTest

# local imports
import crate_mapping
import power_cable_mapping
import testbench
import trigger_handler

if False:
    print(f"A syntax error here indicates the program was started with Python 2 instead of 3, did you remember to first run \'module load ReadoutCard/vX.YY.Z-1\' ?")

script_path = os.path.dirname(os.path.realpath(__file__))

# easier way to translate from YML config
alpide_addr = {
"CMD" : (0 << 8) | 0,
"MODE_CTRL" : (0 << 8) | 1,
"DISABLE_REGIONS_LSBS" : (0 << 8) | 2,
"DISABLE_REGIONS_MSBS" : (0 << 8) | 3,
"FROMU_CFG_1" : (0 << 8) | 4,
"FROMU_CFG_2" : (0 << 8) | 5,
"FROMU_CFG_3" : (0 << 8) | 6,
"FROMU_PULSING1" : (0 << 8) | 7,
"FROMU_PULSING_2" : (0 << 8) | 8,
"FROMU_STATUS_1" : (0 << 8) | 9,
"FROMU_STATUS_2" : (0 << 8) | 10,
"FROMU_STATUS_3" : (0 << 8) | 11,
"FROMU_STATUS_4" : (0 << 8) | 12,
"FROMU_STATUS_5" : (0 << 8) | 13,
"DAC_SETTINGS_DCLK_AND_MCLK_IO_BUFFERS" : (0 << 8) | 14,
"DAC_SETTINGS_CMU_IO_BUFFERS" : (0 << 8) | 15,
"CMU_AND_DMU_CFG" : (0 << 8) | 16,
"CMU_AND_DMU_STATUS" : (0 << 8) | 17,
"DMU_DATA_FIFO_LSBS" : (0 << 8) | 18,
"DMU_DATA_FIFO_MSBS" : (0 << 8) | 19,
"DTU_CFG" : (0 << 8) | 20,
"DTU_DACS" : (0 << 8) | 21,
"DTU_PLL_LOCK_1" : (0 << 8) | 22,
"DTU_PLL_LOCK_2" : (0 << 8) | 23,
"DTU_TEST_1" : (0 << 8) | 24,
"DTU_TEST_2" : (0 << 8) | 25,
"DTU_TEST_3" : (0 << 8) | 26,
"BUSY_MIN_WIDTH" : (0 << 8) | 27,
"PIXEL_CFG" : (5 << 8) | 0,
"ANALOG_MONITOR_AND_OVERRIDE" : (6 << 8) | 0,
"VRESETP" : (6 << 8) | 1,
"VRESETD" : (6 << 8) | 2,
"VCASP" : (6 << 8) | 3,
"VCASN" : (6 << 8) | 4,
"VPULSEH" : (6 << 8) | 5,
"VPULSEL" : (6 << 8) | 6,
"VCASN2" : (6 << 8) | 7,
"VCLIP" : (6 << 8) | 8,
"VTEMP" : (6 << 8) | 9,
"IAUX2" : (6 << 8) | 10,
"IRESET" : (6 << 8) | 11,
"IDB" : (6 << 8) | 12,
"IBIAS" : (6 << 8) | 13,
"ITHR" : (6 << 8) | 14,
"BUFFER_BYPASS" : (6 << 8) | 15,
"ADC_CTRL" : (6 << 8) | 16,
"ADC_DAC_INPUT_VALUE" : (6 << 8) | 17,
"ADC_CALIBRATION_VALUE" : (6 << 8) | 18,
"ADC_AVSS_VALUE" : (6 << 8) | 19,
"ADC_DVSS_VALUE" : (6 << 8) | 20,
"ADC_AVDD_VALUE" : (6 << 8) | 21,
"ADC_DVDD_VALUE" : (6 << 8) | 22,
"ADC_VCASN_VALUE" : (6 << 8) | 23,
"ADC_VCASP_VALUE" : (6 << 8) | 24,
"ADC_VPULSEH_VALUE" : (6 << 8) | 25,
"ADC_VPULSEL_VALUE" : (6 << 8) | 26,
"ADC_VRESETP_VALUE" : (6 << 8) | 27,
"ADC_VRESETD_VALUE" : (6 << 8) | 28,
"ADC_VCASN2_VALUE" : (6 << 8) | 20,
"ADC_VCLIP_VALUE" : (6 << 8) | 30,
"ADC_VTEMP_VALUE" : (6 << 8) | 31,
"ADC_ITHR_VALUE" : (6 << 8) | 32,
"ADC_IREF_VALUE" : (6 << 8) | 33,
"ADC_IDB_VALUE" : (6 << 8) | 34,
"ADC_IBIAS_VALUE" : (6 << 8) | 35,
"ADC_IAUX2_VALUE" : (6 << 8) | 36,
"ADC_IRESET_VALUE" : (6 << 8) | 37,
"ADC_BG2V_VALUE" : (6 << 8) | 38,
"ADC_T2V_VALUE" : (6 << 8) | 39,
"SEU_ERROR_COUNTER" : 0x700,
"TEST_CONTROL" : 0x0701
}

class ObTest(DaqTest):
    def __init__(self):
         super().__init__()
         self.verbose = False
         self.switched = True

    def print_currents(self,powerunit, module_list, power_unit_number):
        """prints powerboard currents"""
        values = powerunit.get_values_modules(module_list=module_list)
        self.logger.info(f"POWERUNIT {power_unit_number}:")
        for module in module_list:
            for vdd in ["avdd", "dvdd"]:
                self.logger.info("Module {0}, {1}: {2:.3f} V, {3:.1f} mA ".format(module,
                                                                                  vdd,
                                                                                  powerunit._code_to_vpower(values["module_{0}_{1}_voltage".format(module, vdd)]),
                                                                                  powerunit._code_to_i(values["module_{0}_{1}_current".format(module, vdd)])))

    def log(self):
        layer = self.testbench.layer
        if layer is testbench.LayerList.OUTER:
            pu_index_set = (1,2)
        elif layer is testbench.LayerList.MIDDLE:
            pu_index_set = (1,)
        else:
            raise NotImplementedError
        for rdo in self.testbench.rdo_list:
            pu_list = self.testbench._get_pu_list(pu_index_set, rdo=rdo)
            for pu_index, powerunit in enumerate(pu_list):
                self.print_currents(powerunit=powerunit, module_list=[0,1,2,3,4,5,6,7], power_unit_number=pu_index)

    def power_off(self):
        self.logger.info("Powering off...")
        layer = self.testbench.layer
        for rdo in self.testbench.rdo_list:
            if layer is testbench.LayerList.OUTER:
                self.testbench.power_off_ob_stave(rdo=rdo, disable_power_interlock=True)
            elif layer is testbench.LayerList.MIDDLE:
                self.testbench.power_off_ml_stave(rdo=rdo, disable_power_interlock=True)
            else:
                raise NotImplementedError
            self.logger.info("Powered off!")

    def get_cable_length(self,rdo):
        stave = self.testbench.get_stave_number(rdo.comm.get_gbt_channel())
        layer_number = self.testbench.get_layer(rdo.comm.get_gbt_channel())
        cable_length = [0]*2
        for entry in power_cable_mapping.cable_length_lut[str(layer_number)]:
            if entry[0] == int(stave):
                if entry[1] == 'lower':
                    cable_length[0] = entry[2]+entry[3]
                elif entry[1] == 'upper':
                    cable_length[1] = entry[2]+entry[3]
        return cable_length

    def clear_triggers(self):
        for rdo in self.testbench.rdo_list:
            rdo.trigger_handler.disable()
            rdo.trigger_handler.mask_all_triggers()
            rdo.trigger_handler.reset_packer_fifos()
            rdo.trigger_handler.sequencer_disable()
            rdo.trigger_handler.sequencer_set_number_of_timeframes(0)
            rdo.trigger_handler.reset_counters()

    def reset_swt_fifo(self):
        if self.testbench is None: return
        self.testbench.cru.force_swt_counter_update()
        comm = self.testbench.rdo_list[0].comm
        swt_in_fifo = comm._get_swt_words_available()
        if swt_in_fifo:
            self.logger.warning('{} SWTs in FIFO! Waiting 100ms then reading and resetting'.format(swt_in_fifo))
            time.sleep(0.1)
            words_read = 0
            while comm._is_swt_available() and words_read < swt_in_fifo:
                self.logger.warning('SWT found in FIFO: 0x{:08X}'.format(comm._read_swt()))
                words_read += 1
            self.logger.info('SWT FIFO before reset:')
            comm.log_swt_status()
            self.testbench.cru.reset_sc_cores()
            self.logger.info('SWT FIFO after reset:')
            comm.log_swt_status()

    def power_on(self,
                 excluded_chipid_ext=[],
                 avdd_current=1.5, dvdd_current=1.5,
                 bb=0,
                 internal_temperature_limit=30,
                 stave_temperature_limit=26,
                 configure_chips=True,
                 half_staves=[0, 1]):
        self._power_configure_correct_drop(excluded_chipid_ext=excluded_chipid_ext,
                                           avdd_current=avdd_current, dvdd_current=dvdd_current,
                                           bb=bb,
                                           internal_temperature_limit=internal_temperature_limit,
                                           stave_temperature_limit=stave_temperature_limit,
                                           power_on=True,
                                           configure_chips=configure_chips,
                                           half_staves=half_staves)

    def configure_correct_drop(self,
                               excluded_chipid_ext=[],
                               avdd_current=1.5, dvdd_current=1.5,
                               bb=0,
                               internal_temperature_limit=30,
                               stave_temperature_limit=26,
                               half_staves=[0, 1]):
        self._power_configure_correct_drop(excluded_chipid_ext=excluded_chipid_ext,
                                           avdd_current=avdd_current, dvdd_current=dvdd_current,
                                           bb=bb,
                                           internal_temperature_limit=internal_temperature_limit,
                                           stave_temperature_limit=stave_temperature_limit,
                                           power_on=False,
                                           configure_chips=True,
                                           half_staves=half_staves)


    def _power_configure_correct_drop(self,
                                      excluded_chipid_ext=[],
                                      avdd_current=1.5, dvdd_current=1.5,
                                      bb=0,
                                      internal_temperature_limit=30,
                                      stave_temperature_limit=26,
                                      power_on=True,
                                      configure_chips=True,
                                      half_staves=[0,1]):

        """ Power stave. If test_power=True: power on, read currents, switch on clock, read currents, configure chips, read currents, print out module by module"""
        #disable info logging (will still give error/critical/fatal)
        avdd=self.config.SENSOR_AVDD
        dvdd=self.config.SENSOR_DVDD
        if not self.verbose:
            logging.disable(logging.INFO)
            dclk_phase = 0
        layer = self.testbench.layer
        if layer is testbench.LayerList.OUTER:
            if 0 in half_staves:
                powerunit_1_module_list=[0,1,2,3,4,5,6]
                module_ids_lower=[m+1 for m in powerunit_1_module_list]
            else:
                powerunit_1_module_list=[]
                module_ids_lower=[]
            if 1 in half_staves:
                powerunit_2_module_list=[0,1,2,3,4,5,6]
                module_ids_upper=[m+1 for m in powerunit_2_module_list]
            else:
                powerunit_2_module_list=[]
                module_ids_upper=[]
            pu_index_set = (1,2)
            module_list = self.testbench._get_pu_module_list(powerunit_1_module_list, powerunit_2_module_list)
        elif layer is testbench.LayerList.MIDDLE:
            if 0 in half_staves:
                module_list_lower = [0,1,2,3]
                module_ids_lower = [m+1 for m in module_list_lower]
            else:
                module_list_lower = []
                module_ids_lower = []
            if 1 in half_staves:
                module_list_upper = [0,1,2,3]
                module_ids_upper = [m+1 for m in module_list_upper]
            else:
                module_list_upper = []
                module_ids_upper = []
            module_list = [module_list_lower + [m+4 for m in module_list_upper]]
            pu_index_set = (1,)
        else:
            raise NotImplementedError

        self.logger.info("Beginning power on...")
        for rdo in self.testbench.rdo_list:
            pu_list = self.testbench._get_pu_list(pu_index_set, rdo=rdo)
            self.logger.info(f"Powering on stave {self.testbench.get_stave_number(rdo.comm.get_gbt_channel())}....")
            self.logger.info(f"Powering with dvdd: {dvdd} and avdd: {avdd}")
            try:
                if layer is testbench.LayerList.OUTER:
                    self.testbench.power_on_ol_stave(powerunit_1_module_list, powerunit_2_module_list, avdd=avdd, dvdd=dvdd, rdo=rdo, external_temperature_limit=stave_temperature_limit, internal_temperature_limit=internal_temperature_limit, configure_chips=False, compensate_v_drop=False)
                elif layer is testbench.LayerList.MIDDLE:
                    self.testbench.power_on_ml_stave(module_list_lower=module_list_lower, module_list_upper=module_list_upper, external_temperature_limit=stave_temperature_limit, internal_temperature_limit=internal_temperature_limit, avdd=avdd, dvdd=dvdd, rdo=rdo, configure_chips=False, compensate_v_drop=False)
                elif layer in [testbench.LayerList.INNER, testbench.LayerList.NO_PT100]:
                    raise NotImplementedError
                time.sleep(1)
                if configure_chips:
                    self.logger.info(".................COMPENSATING VOLTAGE DROP.................")
                    cable_length = self.get_cable_length(rdo)
                    for pu_index, powerunit in enumerate(pu_list):
                        powerunit.compensate_voltage_drops_ob(avdd=avdd, dvdd=dvdd, l=cable_length[pu_index], powered_module_list=module_list[pu_index])
                        time.sleep(0.1)
                    if layer is testbench.LayerList.OUTER:
                        self.testbench.log_values_ob_stave(rdo=rdo)
                    elif layer is testbench.LayerList.MIDDLE:
                        self.testbench.log_values_ml_stave(rdo=rdo)
                    self.logger.info(".................CONFIGURING CHIPS.................")
                    self.configure_chips(rdo, module_list_lower=module_ids_lower, module_list_upper=module_ids_upper)
                    time.sleep(1)
                    self.logger.info(".................COMPENSATING VOLTAGE DROP.................")
                    cable_length = self.get_cable_length(rdo)
                    for pu_index, powerunit in enumerate(pu_list):
                        powerunit.compensate_voltage_drops_ob(avdd=avdd, dvdd=dvdd, l=cable_length[pu_index], powered_module_list=module_list[pu_index])
                        time.sleep(0.1)
                    if layer is testbench.LayerList.OUTER:
                        self.testbench.log_values_ob_stave(rdo=rdo)
                    elif layer is testbench.LayerList.MIDDLE:
                        self.testbench.log_values_ml_stave(rdo=rdo)

            except Exception as e:
                self.logger.error("Power-on failed Exception")
                self.logger.error("Power off!")
                self.testbench.power_off_ob_stave(rdo=rdo, disable_power_interlock=True)
                self.logger.error("Printing Traceback and raising")
                raise e
            logging.disable(logging.NOTSET)

    def reset_voltage(self, reset_chips=True):
        self.logger.info("Resetting voltage to 1.82V for DVDD and AVDD on the powerunit (NOT CHIP VOLTAGE!)")
        avdd=1.82
        dvdd=1.82
        layer = self.testbench.layer
        if layer is testbench.LayerList.OUTER:
            pu_index_set = (1,2)
        elif layer is testbench.LayerList.MIDDLE:
            pu_index_set = (1,)
        else:
            raise NotImplementedError

        for rdo in self.testbench.rdo_list:
            pu_list = self.testbench._get_pu_list(pu_index_set, rdo=rdo)
            chip_broadcast = self.testbench.stave_chip_broadcast(gbt_ch=rdo.get_gbt_channel())
            for pu_index, powerunit in enumerate(pu_list):
                powerunit.reset_voltage(avdd=avdd, dvdd=dvdd)
                time.sleep(0.1)

                if reset_chips:
                    chip_broadcast.reset()
                    chip_broadcast.send_PRST()
                    chip_broadcast.setreg_cmd(Command=0xFF00, commitTransaction=True) # CMU CLEAR ERROR
                    chip_broadcast.setreg_cmd(Command=0x0063, commitTransaction=True) # RORST

    def clean_gbt_fifos(self):
        for i in range(1,4):
            self.logger.info(f"{i}/3 cleans ongoing")
            self.testbench.gbt_packer_clean_fifos()
            self.logger.info(f"clean {i} finished")

    def measure_voltage_drop(self):
        layer = self.testbench.layer
        if layer is testbench.LayerList.OUTER:
            powerunit_1_module_list=[0,1,2,3,4,5,6]
            powerunit_2_module_list=[0,1,2,3,4,5,6]
            pu_index_set = (1,2)
        elif layer is testbench.LayerList.MIDDLE:
            powerunit_1_module_list=[0,1,2,3,4,5,6,7]
            powerunit_2_module_list=[]
            pu_index_set = (1,)
        else:
            raise NotImplementedError

        module_list = self.testbench._get_pu_module_list(powerunit_1_module_list, powerunit_2_module_list)
        for rdo in self.testbench.rdo_list:
            pu_list = self.testbench._get_pu_list(pu_index_set, rdo=rdo)
            stave = self.testbench.get_stave_number(rdo.comm.get_gbt_channel())
            layer_number = self.testbench.get_layer(rdo.comm.get_gbt_channel())

            cable_length = self.get_cable_length(rdo)

        for pu_index in range(len(pu_list)):
            self.testbench.measure_cable_resistance(module_list=[0,1,2,3,4,5,6], verbose=True, powerunit_number=pu_index+1, cable_length=cable_length[pu_index], disable_manchester=self.config.DISABLE_MANCHESTER, driver_dac=self.config.SENSOR_DRIVER_DAC, pre_dac=self.config.SENSOR_PRE_DAC, pll_dac=self.config.SENSOR_PLL_DAC, rdo=rdo)

    def configure_chips(self, rdo, module_list_lower=[1,2,3,4,5,6,7], module_list_upper=[1,2,3,4,5,6,7]):
        self.logger.info("Configuring chips...")
        gbt_channel = rdo.comm.get_gbt_channel()
        ch = Alpide(rdo, chipid=0x0F)
        time.sleep(1)
        stave_number = self.testbench.get_stave_number(gbt_channel)
        self.logger.info(f"stave number {stave_number}")
        stave_ob = self.testbench.stave_ob(gbt_channel)
        excluded_chipid_ext = self.testbench.get_excluded_chip_list_from_config(rdo)
        self.testbench.setup_sensors_ob_stave(module_list_lower=module_list_lower,
                                              module_list_upper=module_list_upper,
                                              rdo=rdo,
                                              disable_manchester=self.config.DISABLE_MANCHESTER,
                                              excluded_chipid_ext=excluded_chipid_ext,
                                              driver_dac=self.config.SENSOR_DRIVER_DAC,
                                              pre_dac=self.config.SENSOR_PRE_DAC,
                                              pll_dac=self.config.SENSOR_PLL_DAC,
                                              avdd=self.config.SENSOR_AVDD,
                                              dvdd=self.config.SENSOR_DVDD,
                                              grst=False)
        self.logger.info("Chips configured!")

    def test_read_register(self):
        register_list = [0x19,0x100,0xf900,0x17f]#,0xf97f]
        total_errors = {}
        if not self.verbose:
            logging.disable(logging.ERROR)
            self.logger.info("Beginning control test...")
        for rdo in self.testbench.rdo_list:
            gbt_channel = rdo.comm.get_gbt_channel()
            stave_ob = self.testbench.stave_ob(gbt_channel)
            stave_number = self.testbench.get_stave_number(gbt_channel)
            excluded_chipid_ext = [241,97]# [20, 48, 49, 50, 51, 52, 53, 54, 73, 70] #self.get_excluded_chip_list_from_config(rdo=rdo)
            for test_pattern in [0x5555, 0xAAAA, 0xFFFF, 0x55, 0xAA, 0xFF, 0x1234, 0x4321, 0xDEAD]:
                for test_reg in register_list:
                    self.logger.info(f"################## Register: 0x{test_reg:x}")
                    bcast= Alpide(rdo, chipid=0xF)
                    bcast.write_reg(test_reg, test_pattern, readback=False)
                    for chipid_ext, ch in stave_ob.items():
                        if chipid_ext not in excluded_chipid_ext:
                            try:
                                ch.write_reg(test_reg, test_pattern, readback=False)
                                rdback = ch.read_reg(test_reg)
                                if rdback != test_pattern:
                                    errors += 1
                                    self.logger.info(f"Wrong readback for Chip ID {chipid_ext}: 0x{rdback:x} instead of 0x{test_pattern:x}")
                            except:
                                errors += 1
                                self.logger.info(f"Wrong readback for Chip ID {chipid_ext}, test pattern 0x{test_pattern:x}")

    def test_control(self, nrtests=1000, half_staves=[0, 1]):
        """ Write-readback test to the 3 DTU test registers on each chip """
        layer = self.testbench.layer
        if layer == testbench.LayerList.OUTER:
            if 0 in half_staves:
                module_list_lower=[1,2,3,4,5,6,7]
            else:
                module_list_lower=[]
            if 1 in half_staves:
                module_list_upper=[1,2,3,4,5,6,7]
            else:
                module_list_upper=[]
        elif layer == testbench.LayerList.MIDDLE:
            if 0 in half_staves:
                module_list_lower=[1,2,3,4]
            else:
                module_list_lower=[]
            if 1 in half_staves:
                module_list_upper=[1,2,3,4]
            else:
                module_list_upper=[]
        else:
            raise NotImplementedError
        self.logger.info("Beginning control test...")
        for rdo in self.testbench.rdo_list:
            try:
                total_errors = self.testbench.test_chips_ob_stave(module_list_lower=module_list_lower, module_list_upper=module_list_upper, exclude_chips=True, nrtests=nrtests, rdo=rdo)
                try:
                    for key in total_errors.keys():
                        if total_errors[key] != 0:
                            self.logger.warning(f"total_errors: {total_errors}")
                            raise ValueError('chip failed control test')
                except Exception as e:
                    self.logger.error("Printing Traceback and raising")
                    raise e

            except Exception as e:
                self.logger.error("Control test exception")
                self.logger.error("Printing Traceback and raising")
                raise e

    def test_ibias_write(self):
        self.logger.info("Starting ibias write test...")
        if not self.verbose:
            logging.disable(logging.ERROR)
            register_list = [0x60D]
            pu_index_set = (1, 2)
            module_list = self.testbench._get_pu_module_list([0,1,2,3,4,5,6],[0,1,2,3,4,5,6])
            total_errors = {}
        for rdo in self.testbench.rdo_list:
            pu_list = self.testbench._get_pu_list(pu_index_set, rdo=rdo)
            gbt_channel = rdo.comm.get_gbt_channel()
            stave = self.testbench.get_stave_number(gbt_channel)
            self.logger.info(f"Stave: {stave} powerunit currents before test:")
            for pu_index, powerunit in enumerate(pu_list):
                time.sleep(0.1)
                self.print_currents(powerunit, module_list[pu_index], pu_index + 1)
                stave_ob = self.testbench.stave_ob(gbt_channel)
            for test_reg in register_list:
                for chipid_ext, ch in stave_ob.items():
                    pattern = 0x0
                    ch.write_reg(test_reg, pattern, readback=False)
                    self.logger.info(f"Stave: {stave} powerunit currents after test:")
            for pu_index, powerunit in enumerate(pu_list):
                time.sleep(0.1)
                self.print_currents(powerunit, module_list[pu_index], pu_index + 1)
                self.logger.info("Ibias write test complete!")


    def test_chip_voltage_read(self,lower=1.75, upper = 1.85):
        """ After everything is powered, return AVD/DVD voltages for each chip if outside of range. NOTE: USES INDIRECT METHOD FOR ANALOGUE VOLTAGE"""
        self.logger.info(f"Beginning voltage test... Lower limit: {lower}, upper limit: {upper}")
        if not self.verbose:
            logging.disable(logging.INFO)
        for rdo in self.testbench.rdo_list:
            gbt_channel = rdo.comm.get_gbt_channel()
            stave_ob = self.testbench.stave_ob(gbt_channel)
            for chipid_ext, ch in stave_ob.items():
                ch.logger.disabled = True
                dvdd = ch.measure_adc(adc_list=[AdcIndex.DVDD])['DVDD']
                avdd = ch.measure_adc_avdd_indirect(samples=25)
                if dvdd < lower or dvdd > upper:
                    self.logger.info(f"Chip DVDD out of range, chipID: {chipid_ext}, DVDD: {dvdd}")
                if avdd < lower or avdd > upper:
                    self.logger.info(f"Chip AVDD out of range, chipID: {chipid_ext}, AVDD: {avdd}")
                    ch.logger.disabled = False
                    logging.disable(logging.NOTSET)
                    self.logger.info("Voltage test complete!")

    def stave_to_link(self, stave):
        for entry in crate_mapping.subrack_lut[self.config.SUBRACK]:
            if entry[5] == int(stave):
                return entry[3]
        self.logger.info(f"Stave not found in crate mapping! Given stave: {stave}, staves on {self.config.SUBRACK}:")
        for entry in crate_mapping.subrack_lut[self.config.SUBRACK]:
            self.logger.info(f"Layer: {entry[2]}, stave: {entry[5]}")
            quit()

    def setup_links(self, staves=[0]):
        links = []
        for stave in staves:
            links.append(self.stave_to_link(stave))
        only_data_link_list = self.config.ONLY_DATA_LINK_LIST
        ctrl_and_data_link_list = self.config.CTRL_AND_DATA_LINK_LIST
        trigger_link_list = self.config.TRIGGER_LINK_LIST

        data_links = []
        trigger_links = []
        for link in links:
            if len(only_data_link_list) == len(ctrl_and_data_link_list): # gbtx1 only
                data_links.append(only_data_link_list[ctrl_and_data_link_list.index(link)])
            elif len(only_data_link_list) == 2*len(ctrl_and_data_link_list): # gbtx1 and gbtx2
                data_links.append(only_data_link_list[ctrl_and_data_link_list.index(link*2)])
                data_links.append(only_data_link_list[(ctrl_and_data_link_list.index(link)*2)+1])
            else:
                raise NotImplementedError
            if len(trigger_link_list) > 0:
                trigger_links.append(trigger_link_list[ctrl_and_data_link_list.index(link)])

        self.logger.info(f"CTRL_AND_DATA_LINK_LIST {links}")
        self.logger.info(f"ONLY_DATA_LINK_LIST {data_links}")
        self.logger.info(f"TRIGGER_LINK_LIST {trigger_links}")
        self.config.CTRL_AND_DATA_LINK_LIST = links
        self.config.ONLY_DATA_LINK_LIST = data_links
        self.config.TRIGGER_LINK_LIST = trigger_links


    def send_GRST(self):
        for rdo in self.testbench.rdo_list:
            ch = Alpide(rdo, chipid=0xF)  # broadcast
            ch.write_opcode(Opcode.GRST)

    def dctrl_transactions(self):
        test_reg = 0x0604 # VCASN
        for rdo in self.testbench.rdo_list:
            stave_ob = self.testbench.stave_ob(rdo.comm.get_gbt_channel())
            excluded_chipid_ext = self.testbench.get_excluded_chip_list_from_config(rdo)
            for chipid_ext, ch in stave_ob.items():
                if chipid_ext not in excluded_chipid_ext:
                    try:
                        rdback = ch.read_reg(address=test_reg, commitTransaction=True)
                    except:
                         self.logger.info(f"Test passed for Chip ID {chipid_ext}. Could not read via dctrl.")

class ThresholdScanOb(ObTest, ThresholdScan):
    pass

class ThresholdTuneOb(ObTest, ThresholdTune):
    pass

class DColTesterOb(ObTest, DColTester):
    pass

class FakeHitRateOb(ObTest, FakeHitRate):
    pass

class BusyDebug(ObTest, FakeHitRate):
    pass

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config_file", required=True, help="Configuration file relative path")
    parser.add_argument("-t", "--test_list", nargs='+', required=True, help="List of tests to be run (options are Threshold, PowerOn, PowerOff, Control, Voltage, Ibias separated by space)")
    parser.add_argument("-s", "--stave_list", nargs='+', required=False, help="List of staves being used", default=0)
    parser.add_argument("-v", "--verbose", required=False, default=False)
    parser.add_argument("-switched", "--switched", required=False, default=False)
    parser.add_argument("-p", "--prefix", required=False, default="")
    parser.add_argument("-e", "--excluded_chipid", required=False, default=-1)
    parser.add_argument("-d", "--duration_of_test", required=False, default=-1)

    args = parser.parse_args()

    test_list = args.test_list

    if "Threshold" in test_list:
        scan = ThresholdScanOb()
    elif [x for x in ["FakeHitScan","TunedFakeHitScan","FakeHitScanPulsed","TunedFakeHitScanPulsed"] if(x in test_list)]:
        scan = FakeHitRateOb()
    elif "FakeHitScanSequencer" in test_list or "TunedFakeHitScanSequencer" in test_list:
        scan = FakeHitRateOb()
        scan.force_sequencer()
    elif "BusyDebug" in test_list:
        scan = BusyDebug()
    elif "Tune" in test_list or "TuneVCASN" in test_list or "TuneITHR" in test_list:
        scan = ThresholdTuneOb()
        if "Tune" in test_list or "TuneVCASN" in test_list:
            scan.set_vcasn_ithr_list(value_list=range(30, 70, 1), is_vcasn_not_ithr=True)
        elif "TuneITHR" in test_list:
            scan.set_vcasn_ithr_list(value_list=range(20, 130, 1), is_vcasn_not_ithr=False)
    elif "DColTest" in test_list:
        scan = DColTesterOb()
    else:
        scan = ObTest()

    scan.switched = args.switched
    scan.verbose  = args.verbose
    scan.setup_logging(prefix=args.prefix)
    scan.configure_run(args.config_file)
    scan.setup_links(args.stave_list)
    scan.initialize_testbench()
    scan.testbench.setup_cru()
    if scan.config.USE_LTU:
        scan.testbench.setup_ltu()
    scan.setup_comms()

    scan.logger.info(f"Running {args.test_list}")
    try:
        scan.testbench.cru.initialize()
        time.sleep(1)
        if scan.config.USE_LTU:
            assert scan.testbench.ltu.is_ltu_on(), "LTU communication failed"
        try:
            scan.testbench.setup_rdos(connector_nr=scan.config.MAIN_CONNECTOR)
            for rdo in scan.testbench.rdo_list:
                rdo.initialize()
                gbt_channel = rdo.comm.get_gbt_channel()
                if scan.config.PA3_READ_VALUES or scan.config.PA3_SCRUBBING_ENABLE:
                    scan.testbench.cru.pa3.initialize()
                    scan.testbench.cru.pa3.config_controller.clear_scrubbing_counter()
                if scan.config.PA3_SCRUBBING_ENABLE:
                    scan.testbench.cru.pa3.config_controller.start_blind_scrubbing()
                    scan.logger.info(f"Running blind scrubbing on RDO {gbt_channel}")
            something_run = False
            if "Threshold" in test_list:
                something_run = True
                scan.test_routine()
            if "Tune" in test_list or "TuneVCASN" in test_list or "TuneITHR" in test_list:
                something_run = True
                scan.test_routine()
            if "FakeHitScan" in test_list:
                something_run = True
                scan.test_routine()
            if "TunedFakeHitScan" in test_list:
                something_run = True
                scan.test_routine()
            if "FakeHitScanSequencer" in test_list:
                something_run = True
                scan.test_routine()
            if "TunedFakeHitScanSequencer" in test_list:
                something_run = True
                scan.activate_tuning()
                scan.test_routine()
            if "FakeHitScanPulsed" in test_list:
                something_run = True
                scan.force_pulsing()
                scan.test_routine()
            if "TunedFakeHitScanPulsed" in test_list:
                something_run = True
                scan.activate_tuning()
                scan.force_pulsing()
                scan.test_routine()
            if "DColTest" in test_list:
                something_run=True
                scan.test_routine()
            if "BusyDebug" in test_list:
                something_run=True
                scan.set_excluded_chipid(args.excluded_chipid)
                scan.set_duration(args.duration_of_test)
                scan.test_routine()
            if "PowerOn" in test_list:
                something_run = True
                scan.power_on(configure_chips=True)
            if "Configure" in test_list:
                something_run = True
                scan.configure_correct_drop()
            if "MeasureDrop" in test_list:
                something_run = True
                scan.measure_voltage_drop()
            if "logValues" in test_list:
                something_run = True
                scan.log()
            if "ResetVoltage" in test_list:
                something_run = True
                scan.reset_voltage(reset_chips=False)
            if "ResetVoltageAndChips" in test_list:
                something_run = True
                scan.reset_voltage(reset_chips=True)
            if "PowerOff" in test_list:
                something_run = True
                scan.power_off()
            if "Control" in test_list:
                something_run = True
                scan.test_control(1)
            if "Voltage" in test_list:
                something_run = True
                scan.test_chip_voltage_read()
            if "Ibias" in test_list:
                something_run = True
                scan.test_ibias_write()
            if "Register_read" in test_list:
                something_run = True
                scan.test_read_register()
            if "dump" in test_list:
                something_run = True
                scan.dump_chip_config_ob(suffix=args.prefix)
            if "cleanGBT" in test_list:
                something_run = True
                scan.clean_gbt_fifos()
            if "clearTriggers" in test_list:
                something_run = True
                scan.clear_triggers()
            if "GRST" in test_list:
                something_run=True
                scan.send_GRST()
            if "read_dctrl" in test_list:
                something_run=True
                scan.dctrl_transactions()
            if "reset_swt_fifo" in test_list:
                something_run=True
                scan.reset_swt_fifo()
            if "verify_stave" in test_list:
                something_run=True
                scan.power_on(configure_chips=True,half_staves=[0])
                scan.test_control(10,half_staves=[0])
                scan.testbench.configure_dtu(rdo, is_on_lower_hs=True)
                try:
                    scan.setup_datapath_gpio(1000)
                except:
                    print("")
                scan.power_off()
                scan.power_on(configure_chips=True,half_staves=[1])
                scan.test_control(10,half_staves=[1])
                scan.testbench.configure_dtu(rdo, is_on_lower_hs=False)
                try:
                    scan.setup_datapath_gpio(1000)
                except:
                    print("")
                scan.power_off()
            if "verify_communication" in test_list:
                something_run=True
                scan.test_control(10)
                try:
                    scan.setup_datapath_gpio(1000)
                except:
                    print("")
            if "setup_communication" in test_list:
                something_run=True
                scan.test_control(10)
                scan.testbench.configure_dtu(rdo)
                try:
                    scan.setup_datapath_gpio(1000)
                except:
                    print("")

            if not something_run:
                raise NotImplementedError(f"No valid test in test list {test_list}")

        except Exception as e:
            raise e
    except Exception as e:
        scan.logger.info("Exception in Run")
        scan.logger.info(e,exc_info=True)
        scan.test_pass = False
    finally:
        scan.testbench.stop()
        scan.stop()

    if scan.test_pass:
        scan.logger.info("Test passed!")
    else:
        scan.logger.warning("Test failed! Check logs to find out why.")
        scan.logger.info("Power off!")
        # scan.testbench.power_off_ob_stave(rdo=rdo, disable_power_interlock=True)
        sys.exit(-1)
