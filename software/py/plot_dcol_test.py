#!/usr/bin/env python3.9
"""
File for plotting staves FakeHitRate (OB, ML)
Original file by @jiddon
"""

import argparse

from stave_plotter import FHRateStavePlotter

if __name__ == '__main__':
    # Parse input
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--filepath", required=False, help="Path to file to analyse", default="/dev/stdin")
    parser.add_argument("-g", "--filepath2", required=False, help="Path to 2nd file to analyse (allows to supply the hitmaps of different FEEIDs at the same time)", default="")
    parser.add_argument("-pe", "--plot_extension", required=False, help="Extension for the image saved", default="pdf")
    parser.add_argument("-ml", "--middle_layer", required=False, help="Set for middle layer staves", action='store_true')
    parser.add_argument("-fb", "--force_binary", required=False, help="Forces the binary color map if used", action='store_true')
    parser.add_argument("-o", "--output_file_name", required=False, help="output file name", default="nameless_stave")
    parser.add_argument("-y", "--yaml_filename", required=False, help="Filename of yml file with vcasn values", default="nameless")
    parser.add_argument("-d", "--debug", required=False, help="Activates the generation of single chip plots", action='store_true')

    args = parser.parse_args()

    filename = args.filepath
    filename2 = args.filepath2
    plot_extension = args.plot_extension
    middle_layer = args.middle_layer
    force_binary = args.force_binary
    output_file_name = args.output_file_name
    yaml_filename = args.yaml_filename
    debug = args.debug
    rewrite_masks = True

    # analyse
    plotter = FHRateStavePlotter(filename=filename,
                                 filename2=filename2,
                                 middle_layer=middle_layer,
                                 plot_extension=plot_extension,
                                 plot_name=output_file_name,
                                 yaml_filename=yaml_filename,
                                 rewrite_masks=rewrite_masks)

    # analysis, needs the unmodified data!
    plotter.analyse_dcols(yaml_filename=output_file_name, middle_layer=middle_layer, debug=debug)
    # plotting ### ALTERS THE DATA NEEDS TO BE EXECUTED LAST #### W A R N I N G ###
    #plotter.plot_stack(force_binary=force_binary)
    #plotter.plot_stave(force_binary=force_binary)
