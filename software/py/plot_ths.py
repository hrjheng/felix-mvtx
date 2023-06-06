#!/usr/bin/env python3.9
"""
File for plotting staves ThresholdScans (OB, ML)
Original file by @jiddon
"""

import argparse

from stave_plotter import THScanStavePlotter

if __name__ == '__main__':
    # Parse input
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--filepath", required=False, help="Path to file to analyse", default="/dev/stdin")
    parser.add_argument("-g", "--filepath2", required=False, help="Path to 2nd file to analyse (allows to supply the hitmaps of different FEEIDs at the same time)", default="")
    parser.add_argument("-i", "--injections", type=int, required=False, help="Number of injections per charge", default=21)
    parser.add_argument("-sr", "--skipped_rows", type=int, required=False, help="Number of rows skipped in thresholdscan", default=11)
    parser.add_argument("-mc", "--max_charge", type=int, required=False, help="Maximum injected charge", default=50)
    parser.add_argument("-pe", "--plot_extension", required=False, help="Extension for the image saved", default="pdf")
    parser.add_argument("-ml", "--middle_layer", required=False, help="Set for middle layer staves", action='store_true')
    parser.add_argument("-o", "--output_plot_name", required=False, help="plot name to be saved in /plots/", default="nameless_stave")
    parser.add_argument("-n", "--name_stave", required=True, help="Stave name in form L#_##, e.g. L5_42")
    args = parser.parse_args()

    filename = args.filepath
    filename2 = args.filepath2
    max_charge = args.max_charge
    injections = args.injections
    plot_extension = args.plot_extension
    skipped_rows = args.skipped_rows
    middle_layer = args.middle_layer
    plot_name = args.output_plot_name
    stave_name = args.name_stave

    # analyse
    plotter = THScanStavePlotter(filename=filename,
                                 filename2=filename2,
                                 middle_layer=middle_layer,
                                 injections=injections,
                                 max_charge=max_charge,
                                 skipped_rows=skipped_rows,
                                 plot_extension=plot_extension,
                                 plot_name=plot_name,
                                 stave_name=stave_name)
    # plot
    plotter.plot_stack()
    plotter.plot_stave()
