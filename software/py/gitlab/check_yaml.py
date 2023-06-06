import argparse
import os
import sys
import traceback
import warnings
script_path = os.path.dirname(os.path.realpath(__file__))
modules_path = os.path.join(
    script_path, '../../modules/board_support_software/software/py/')
py_path = os.path.join(script_path, '../')
sys.path.append(modules_path)
sys.path.append(py_path)

from daq_test_configurator import DaqTestConfig
from threshold_scan import ThresholdConfig
from fakehitrate import FHRConfig
import testbench

def custom_formatwarning(msg, *args, **kwargs):
    # ignore everything except the message
    return str(msg) + '\n'

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', action='store', nargs='+', type=str, help='Config file (list) to check', required=True, dest='config')
    options = parser.parse_args()

    warnings.formatwarning = custom_formatwarning
    error_count = 0

    for config in options.config:
        with warnings.catch_warnings(record=True) as w_msgs:
            print(f'Testing {config}')
            config_filepath = os.path.realpath(config)
            config_filename = os.path.basename(config_filepath)
            if config_filename.startswith("daq_test"):
                try:
                    dt = DaqTestConfig(only_warn=True)
                    dt.configure_run(config_filepath, './')
                except:
                    warnings.warn(f"Uncaught exception loading {config_filename}, no further processing of this file\n{traceback.format_exc()}")
            elif config_filename.startswith("threshold_"):
                try:
                    dt = ThresholdConfig(only_warn=True)
                    dt.configure_run(config_filepath, './')
                except:
                    warnings.warn(f"Uncaught exception loading {config_filename}, no further processing of this file\n{traceback.format_exc()}")
            elif config_filename.startswith("obtest_"):
                try:
                    dt = ThresholdConfig(only_warn=True)
                    dt.configure_run(config_filepath, './')
                except:
                    warnings.warn(f"Uncaught exception loading {config_filename}, no further processing of this file\n{traceback.format_exc()}")
                try:
                    dt = FHRConfig(only_warn=True)
                    dt.configure_run(config_filepath, './')
                except:
                    warnings.warn(f"Uncaught exception loading {config_filename}, no further processing of this file\n{traceback.format_exc()}")
            elif config_filename.startswith("testbench"):
                try:
                    testbench.configure_testbench(config_filepath,
                                                  run_standalone=False,
                                                  check_yml=True)
                except:
                    warnings.warn(f"Uncaught exception loading {config_filename}, no further processing of this file\n{traceback.format_exc()}")
            else:
                warnings.warn(f"Unknown file type {config_filename}")
        for w_msg in w_msgs:
            warnings.warn(f"Error: {w_msg.message}")
            error_count += 1

    if error_count:
        sys.exit(1)