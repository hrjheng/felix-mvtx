#!/usr/bin/env python3.9

import yaml
import os
import argparse
from collections import defaultdict
script_path = os.path.dirname(os.path.realpath(__file__))

def merge_yml(yaml_filename):
    folder_path = os.path.join(script_path, "../config/mask_double_cols/")
    with open(os.path.join(folder_path, f"{yaml_filename}_bad_dcols_dcol_test.yml"), 'r') as f:
        bad_dcols=yaml.load(f, Loader=yaml.FullLoader) or {}
    with open(os.path.join(folder_path, f"{yaml_filename}_bad_dcols_tuned_fhr.yml"), 'r') as f:
        bad_dcols_analyse_hits=yaml.load(f, Loader=yaml.FullLoader) or {}

    merge_bad_dcols = bad_dcols.copy()
    merge_bad_dcols.update(bad_dcols_analyse_hits)
    for k in bad_dcols:
        if bad_dcols[k] != merge_bad_dcols[k]:
            for v in bad_dcols[k]:
                if v not in merge_bad_dcols[k]:
                    merge_bad_dcols[k].append(v)
            
    with open(os.path.join(folder_path, f"{yaml_filename}_stave_plotter.yml"), 'w') as f:
        yaml.dump(bad_dcols, f)
    with open(os.path.join(folder_path, f"{yaml_filename}.yml"), 'w') as f:
        yaml.dump(merge_bad_dcols, f)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-y", "--yaml_filename", required=True, help="yaml file prefix. Something of the form L5_42")
    args = parser.parse_args()

    merge_yml(args.yaml_filename)


