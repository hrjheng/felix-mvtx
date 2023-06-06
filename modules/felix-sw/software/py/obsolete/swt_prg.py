#!/usr/bin/env python3

import module_include_felix

import sys
import argparse

import SWT
from SWT import Swt


def main():

    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", type=int, choices=(0,1), default=0, help="card ID")
    parser.add_argument("-l", "--links", type=int, default=0, help="specifiy link ID")
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true", default=False)
    parser.add_argument("-swt", "--swt-word", required=True, help="80 bit swt word")
    parser.add_argument("-wr", "--swt-wr", action="store_true", default=False, help="80 bit swt word")
    parser.add_argument("-rd", "--swt-rd", action="store_true", default=False, help="80 bit swt word")
    parser.add_argument("-rs", "--reset", action="store_true", default=False, help="80 bit swt word")
    args = parser.parse_args()

    id_card = int(args.id)
    gbt_ch = args.links

    swt = Swt(id_card, 2, gbt_ch)

    swt_int = int(args.swt_word, 0)

    if args.swt_wr :
        swt.wr(swt_int)

    if args.swt_rd :
        swt.rd()

    if args.reset :
        swt.reset()

if __name__ == '__main__' :
    main()
