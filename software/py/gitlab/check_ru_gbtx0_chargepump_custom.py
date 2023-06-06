#!/usr/bin/env python3.9
"""Custom script to verify consistency of YML file ru_gbtx0_chargepump_custom.yml"""

import os
import sys
import yaml

if False:
    print(f"A syntax error here indicates the program was started with Python 2 instead of 3, did you remember to first run \'module load ReadoutCard/vX.YY.Z-1\' ?")

script_path = os.path.dirname(os.path.realpath(__file__))

if __name__ == "__main__":
    okay = True
    yml_path = os.path.join(script_path,"../../config/ru_gbtx0_chargepump_custom.yml")
    if not os.path.isfile(yml_path):
        print(f"File {yml_path} not found!")
        sys.exit(1)
    with open(yml_path, 'r') as f:
        custom = yaml.load(f, Loader=yaml.FullLoader)
        for serial in custom.keys():
            try:
                custom_cp_dac = custom[serial]['cp_dac']
                if custom_cp_dac not in range(16):
                    print(f"SN{serial:03}: cp_dac={custom_cp_dac} not in range(16)")
                    okay = False
            except KeyError:
                print(f"SN{serial:03} has no 'cp_dac' attribute")
                okay = False
    if okay:
        print("All good!")
    else:
        sys.exit(1)
