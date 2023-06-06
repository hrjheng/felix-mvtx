#!/usr/bin/env python3.9
"""
File for calculating tuned vcasn value (OB, ML)
Original file by @jiddon
"""

import argparse

from stave_plotter import THTuneStavePlotter

if __name__ == '__main__':
    # Parse input
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--filepath", required=False, help="Path to file to analyse", default="/dev/stdin")
    parser.add_argument("-g", "--filepath2", required=False, help="Path to 2nd file to analyse (allows to supply the hitmaps of different FEEIDs at the same time)", default="")
    parser.add_argument("-y", "--yaml_filename", required=False, help="Filename of yml file with vcasn values", default="nameless")
    parser.add_argument("-i", "--injections", type=int, required=False, help="Number of injections per charge", default=21)
    parser.add_argument("-ml", "--middle_layer", required=False, help="Set for middle layer staves", action='store_true')
    parser.add_argument("-t", "--ithr_not_vcasn", required=False, help="Tuning Ithr not Vcasn", action='store_true')
    parser.add_argument("-o", "--output_file_name", required=False, help="output file name", default="nameless_stave")
    args = parser.parse_args()

    filename = args.filepath
    filename2 = args.filepath2
    yaml_filename=args.yaml_filename
    output_file_name = args.output_file_name
    injections = args.injections
    middle_layer = args.middle_layer
    ithr_not_vcasn = args.ithr_not_vcasn

    # analyse
    plotter = THTuneStavePlotter(filename=filename,
                                 filename2=filename2,
                                 plot_name=output_file_name,
                                 yaml_filename=yaml_filename,
                                 middle_layer=middle_layer,
                                 injections=injections,
                                 ithr_not_vcasn=ithr_not_vcasn)
