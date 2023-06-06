#!/usr/bin/env python3
"""Generic Testbench for testing different routines and interactive access to RU modules"""
import fire
import os
import sys

import testbench

script_path = os.path.dirname(os.path.realpath(__file__))
modules_path = os.path.join(
    script_path, '../../modules/board_support_software/software/py/')
sys.path.append(modules_path)

if __name__ == "__main__":

    RUN_STANDALONE=True
    config_file_path = script_path + '/../config/testbench_can_LANL.yml'
    tb = testbench.configure_testbench(config_file_path=config_file_path,
                                       run_standalone=RUN_STANDALONE)

    try:
        fire.Fire(tb)
    except:
        raise
    finally:
        tb.stop()
