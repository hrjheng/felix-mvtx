#!/usr/bin/env python3.9
"""
File for plotting staves FakeHitRate (OB, ML)
Original file by @jiddon
"""

import argparse

from stave_plotter_subrack import FHRateStavePlotter

if __name__ == '__main__':
    # Parse input
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--filename_list", nargs="+", required=True, help="Path to file to analyse", default="/dev/stdin")
    parser.add_argument("-pe", "--plot_extension", required=False, help="Extension for the image saved", default="pdf")
    parser.add_argument("-ml", "--middle_layer", required=False, help="Set for middle layer staves", action='store_true')
    parser.add_argument("-fb", "--force_binary", required=False, help="Forces the binary color map if used", action='store_true')
    parser.add_argument("-s", "--show", required=False, help="If used, it shows the image instead of storing it to file", action='store_true')
    parser.add_argument("-sub", "--subrack", type=str, required=True, help="Subrack")
    args = parser.parse_args()

    filename_list = args.filename_list
    plot_extension = args.plot_extension
    show = args.show
    middle_layer = args.middle_layer
    force_binary = args.force_binary
    subrack = args.subrack

    # analyse
    plotter = FHRateStavePlotter(filename_list=filename_list,
                                 middle_layer=middle_layer,
                                 plot_extension=plot_extension,
                                 subrack=subrack)

    plotter.plot_stave(show=show, force_binary=force_binary)
