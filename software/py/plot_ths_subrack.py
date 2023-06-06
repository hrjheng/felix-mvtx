#!/usr/bin/env python3.9
"""
File for plotting staves ThresholdScans (OB, ML)
Original file by @jiddon
"""

import argparse

from stave_plotter_subrack import THScanStavePlotter

if __name__ == '__main__':
    # Parse input
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--filename_list", nargs="+", required=True, help="Path to file to analyse", default="/dev/stdin")
    parser.add_argument("-i", "--injections", type=int, required=False, help="Number of injections per charge", default=21)
    parser.add_argument("-sr", "--skipped_rows", type=int, required=False, help="Number of rows skipped in thresholdscan", default=11)
    parser.add_argument("-mc", "--max_charge", type=int, required=False, help="Maximum injected charge", default=50)
    parser.add_argument("-pe", "--plot_extension", required=False, help="Extension for the image saved", default="pdf")
    parser.add_argument("-ml", "--middle_layer", required=False, help="Set for middle layer staves", action='store_true')
    parser.add_argument("-s", "--show", required=False, help="If used, it shows the image instead of storing it to file", action='store_true')
    parser.add_argument("-sub", "--subrack", type=str, required=True, help="Subrack")
    args = parser.parse_args()

    filename_list = args.filename_list
    max_charge = args.max_charge
    injections = args.injections
    plot_extension = args.plot_extension
    skipped_rows = args.skipped_rows
    show = args.show
    middle_layer = args.middle_layer
    subrack = args.subrack

    # analyse
    plotter = THScanStavePlotter(filename_list=filename_list,
                                 middle_layer=middle_layer,
                                 injections=injections,
                                 max_charge=max_charge,
                                 skipped_rows=skipped_rows,
                                 plot_extension=plot_extension,
                                 subrack=subrack)

    plotter.plot_stave(show=show)
