#!/usr/bin/env python3
"""Setup an RU for MVTX"""

import argparse

import daq_test

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config_file", required=True, help="Configuration file relative path", default=None)
args = parser.parse_args()

daq_test = daq_test.DaqTest()
daq_test.setup_logging()
# read the config file
daq_test.configure_run(args.config_file)

# initialize the testbench and setup
daq_test.initialize_testbench()
daq_test.testbench.setup_cru()
daq_test.testbench.setup_comms()
daq_test.testbench.setup_rdos(connector_nr=daq_test.config.MAIN_CONNECTOR)
daq_test.testbench.initialize_boards()
daq_test.testbench.initialize_all_gbtx12()

# now assuming just one RDO:
print("RU githash: ", hex(daq_test.testbench.rdo_list[0].identity.get_git_hash()))

print("Trigger handler setup")
daq_test.setup_trigger_handler()
print(daq_test.testbench.rdo_list[0].trigger_handler.dump_config())
