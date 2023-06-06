#!/usr/bin/env python

import setThisPath

import sys
import argparse

import IC 
from IC import Ic
   
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", required=True, help="card ID")
    parser.add_argument("-b", "--board", default="CRU", help="card type CRU/GRORC")
    parser.add_argument("-l", "--links", type=int, default=0, help="specifiy link ID")
    parser.add_argument("-a", "--add", default="0x0", help=" ")
    parser.add_argument("-d", "--data", default="0x0", help=" ")
    args = parser.parse_args()
        
    id_card = args.id
    gbt_ch = args.links
    board = args.board
    add = int(args.add, 0)
    data = int(args.data, 0)
    
    debug = None
    
    ic = Ic(id_card, 2, gbt_ch, debug)
    ic.wrGBTI2Cadd(3, debug)
    ic.wr(add, data, debug)
    ic.rd(add, data, debug)

    
if __name__ == '__main__' :
    main()
