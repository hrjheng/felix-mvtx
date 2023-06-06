"""Fake hit rate scan (to be called from obtest.py)

Inherits from daq_test
"""

import os
import sys
import time
import yaml

script_path = os.path.dirname(os.path.realpath(__file__))
modules_path = os.path.join(
    script_path, '../../modules/board_support_software/software/py/')
sys.path.append(modules_path)

import trigger_handler

from daq_test import DaqTest, RuTriggeringMode
from daq_test_configurator import DaqTestConfig
#from trigger_handler import TrigSourceMask


class FHRConfig(DaqTestConfig):
    def __init__(self, only_warn=False):
        super().__init__(only_warn=only_warn)
        self.ITHR                         = None
        self.VCASN                        = None
        self.VCASN2                       = None
        self.VPULSEH                      = None
        self.VRESETD                      = None
        self.IDB                          = None

        self.use_sequencer = False

    def force_sequencer(self):
        self.use_sequencer = True

    def _load_config(self):
        super()._load_config()
        self._configure_fakehit()

    def _configure_fakehit(self):
        """Configures a specific section of the test"""
        self._section = 'FAKEHIT'
        self.VCASN               = self._get_config_int('VCASN')
        self.VCASN2              = self._get_config_int('VCASN2')
        self.VPULSEH             = self._get_config_int('VPULSEH')
        self.VRESETD             = self._get_config_int('VRESETD')
        self.IDB                 = self._get_config_int('IDB')
        self.ITHR                = self._get_config_int('ITHR')
        if self.use_sequencer:
            # overrides configuration: this test can only run with the sequencer
            # and it shall be set to
            self.TRIGGER_SOURCE  = trigger_handler.TriggerSource.SEQUENCER
            self.TRIGGERING_MODE = RuTriggeringMode.TRIGGERED_SEQ
            self.TRIGGER_PERIOD_BC  = 3564 # 11 kHz / 1 trigger per HBF (= ORBIT of 3564 BCs)
            self.TRIGGER_HBF_PER_TF = 255 # FIXME remove to use the value from the config
            self.TRIGGER_HBA_PER_TF = 255 # FIXME remove to use the value from the config
            self.TRIGGER_TF         = 0 # Not relevant, will be set to infinite
        else:
            self.MULTIPLE_OF_ORBIT = self._get_config_boolean('MULTIPLE_OF_ORBIT')
            self.LTU_MASTER        = self._get_config_boolean('LTU_MASTER')
            self.USE_LTU           = self._get_config_boolean('USE_LTU')
            self.TRIGGER_SOURCE    = self._get_config_enum('SOURCE', trigger_handler.TriggerSource)
            self.TRIGGERING_MODE   = self._get_config_enum('MODE', RuTriggeringMode)

            if self.MULTIPLE_OF_ORBIT:
                self.FREQUENCY          = self._get_config_int("FREQUENCY")
                #self.TRIGGER_PERIOD_BC  = trigger_handler.ALLOWED_CONTINUOUS_MODE_PERIOD_BC[self.FREQUENCY]
                self.TRIGGER_PERIOD_BC  = trigger_handler.ALLOWED_CONTINUOUS_MODE_PERIOD_BC[0] ##11kHz
                self.TRIGGER_HBF_PER_TF = 255 # FIXME remove to use the value from the config
                self.TRIGGER_HBA_PER_TF = 255 # FIXME remove to use the value from the config
                self.TRIGGER_TF         = 0 # Not relevant, will be set to infinite
            else:
                self.TRIGGER_PERIOD_BC  = 891 # 11 kHz / 1 trigger per HBF (= ORBIT of 3564 BCs)
                self.TRIGGER_HBF_PER_TF = 255 # FIXME remove to use the value from the config
                self.TRIGGER_HBA_PER_TF = 255 # FIXME remove to use the value from the config
                self.TRIGGER_TF         = 0 # Not relevant, will be set to infinite



        self.DRY                = False # Does not work in dry run mode

    def _configure_alpide(self):
        super()._configure_alpide()
        # Hardcoded overwrite of what is loaded from config
        self.ANALOGUE_PULSING         = False
        self.PULSE_TO_STROBE          = False
        self.SEND_PULSES              = False
        self.ENABLE_STROBE_GENERATION = False

    def store_scan_specific_config(self, cfg):
        cfg['ITHR']    = self.ITHR
        cfg['VCASN']   = self.VCASN
        cfg['VCASN2']  = self.VCASN2
        cfg['VPULSEH'] = self.VPULSEH
        cfg['VRESETD'] = self.VRESETD
        cfg['IDB']     = self.IDB
        cfg['FORCE_SEQUENCER'] = self.use_sequencer
        cfg['TRIGGER_SOURCE'] = self.TRIGGER_SOURCE
        cfg['TRIGGERING_MODE'] = self.TRIGGERING_MODE
        cfg['TRIGGER_PERIOD_BC']  = self.TRIGGER_PERIOD_BC
        cfg['TRIGGER_HBF_PER_TF'] = self.TRIGGER_HBF_PER_TF
        cfg['TRIGGER_HBA_PER_TF'] = self.TRIGGER_HBA_PER_TF
        cfg['TRIGGER_TF']         = self.TRIGGER_TF

        cfg['ANALOGUE_PULSING'] = self.ANALOGUE_PULSING
        cfg['PULSE_TO_STROBE'] = self.PULSE_TO_STROBE
        cfg['SEND_PULSES'] = self.SEND_PULSES
        cfg['ENABLE_STROBE_GENERATION'] = self.ENABLE_STROBE_GENERATION

        if not self.use_sequencer:
            cfg['TRIGGER_SOURCE']    = self._get_item_name(self.TRIGGER_SOURCE)
            cfg['USE_LTU']           = self.USE_LTU
            cfg['LTU_MASTER']        = self.LTU_MASTER
            cfg['TRIGGERING_MODE']   = self.TRIGGERING_MODE

        return cfg


class FakeHitRate(DaqTest):
    def __init__(self, testbench=None, name="Fake Hit Rate"):
        super().__init__(testbench=testbench, name=name)
        self.logger.warning("Fake-hit rate uses hard-coded trigger configuration")
        self.tuned = False
        self.pulsed = False
        self.chipid = -1

    def set_excluded_chipid(self, excluded_chipid):
        self.chipid = excluded_chipid

    def set_duration(self, test_duration):
        self.test_duration = test_duration

    def force_sequencer(self):
        self.config.force_sequencer()

    def load_config(self):
        self.config = FHRConfig()

    def set_scan_specific_registers(self):
        self.set_chip_registers()

    def calculate_detector_timeout_bc(self):
        """Calculates the detector timeout value based on the daq_test.
        The method is designed to be overrides it for the THS"""
        detector_timeout_bc = self.config.TRIGGER_PERIOD_BC
        return detector_timeout_bc

    def setup_scan_specific_trigger_handler(self):
        """Overrides the configuration of the trigger handler
        Avoids having periodic triggers in the first row injection"""
        for rdo in self.testbench.rdo_list:
            rdo.trigger_handler.sequencer_set_number_of_timeframes_infinite(enable=True)
            rdo.trigger_handler.dump_config()
            assert rdo.trigger_handler.is_timebase_synced()

    def activate_tuning(self, tuned=True):
        self.tuned = tuned

    def force_pulsing(self, pulsed=True):
        self.pulsed = pulsed
        self.config.PULSE_TO_STROBE = pulsed
        self.config.SEND_PULSES     = pulsed

    # stave wide settings
    def set_chip_registers(self):
        """Values from new-alpide-software threshold scan

        FIXME: this comment is not relative to the FHR
        FIXME: why not broadcasting the configuration?
        """
        for rdo in self.testbench.rdo_list:
            gbt_channel = rdo.comm.get_gbt_channel()
            ch = self.testbench.chip_broadcast_dict[gbt_channel]
            if self.pulsed:
                ch.setreg_fromu_cfg_1(MEBMask=0x0,
                                      EnStrobeGeneration=0x0,
                                      EnBusyMonitoring=0x0,
                                      PulseMode=0, # digitial
                                      EnPulse2Strobe=int(self.config.PULSE_TO_STROBE), # pulse followed by strobe
                                      EnRotatePulseLines=0x0,
                                      TriggerDelay=0x0)

            if self.tuned:
                self.set_vcasn(rdo)
                self.set_ithr(rdo)
            else:
                ch.setreg_VCASN(self.config.VCASN, commitTransaction=False)
                ch.setreg_VCASN2(self.config.VCASN2, commitTransaction=False)
                ch.setreg_ITHR(self.config.ITHR, commitTransaction=False)
            ch.setreg_VPULSEH(self.config.VPULSEH, commitTransaction=False)
            ch.setreg_VRESETD(self.config.VRESETD, commitTransaction=False)
            ch.setreg_IDB(self.config.IDB, commitTransaction=False)

            if self.pulsed:
                ## Mask activation
                n = 10
                pixels = []
                for j in range(2):
                    pixels += [(int(1024/n)*i,255+j) for i in range(n)]
                    pixels += [(int(1024/n)*i+1,255+j) for i in range(n)]
                ch.unmask_pixel(pixels)
                ch.pulse_pixel_enable(pixels)
                rdo.wait(0xFFFF, commitTransaction=True)
                ch.send_PRST(commitTransaction=True)

    def get_excluded_chip_list_from_config(self, rdo, silent=False):
        gbt_channel = rdo.get_gbt_channel()
        stave_number = self.testbench.get_stave_number(gbt_channel=gbt_channel)
        excluded_chipid_ext = []
        if stave_number in self.config.staves:
            if 'excluded-chips' in self.config.staves[stave_number]:
                excluded_chipid_ext = self.config.staves[stave_number]['excluded-chips']
            else:
                self.logger.warning(f"stave {stave_number} has no excluded-chips")
        else:
            self.logger.warning(f"Stave {stave_number} not in {self.config.staves}")
        if not silent: self.logger.info(f"Stave {stave_number}, excluded chipid from config: {excluded_chipid_ext}")

        if self.chipid != -1:
            excluded_chipid_ext.append(int(self.chipid))

        return excluded_chipid_ext

    def set_test_duration(self):
        if self.test_duration != -1:
            self.config.TEST_DURATION = self.test_duration
