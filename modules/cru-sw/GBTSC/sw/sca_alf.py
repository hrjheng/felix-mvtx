#!/usr/bin/env python

import setThisPath

import sys
import argparse

import SCA 
from SCA import Sca
   
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", required=True, help="card ID")
    parser.add_argument("-b", "--board", default="CRU", help="card type CRU/GRORC")
    parser.add_argument("-l", "--links", type=int, default=0, help="specifiy link ID")
    parser.add_argument("-c", "--cmd", default="0x0", help=" ")
    parser.add_argument("-d", "--data", default="0x0", help=" ")
    args = parser.parse_args()
        
    id_card = args.id
    gbt_ch = args.links
    board = args.board
    cmd = int(args.cmd, 0)
    data = int(args.data, 0)
    
    debug = None
        
    sca = Sca(id_card, 2, gbt_ch, board, debug)

    sca.displayAdd()

    sca.alfOPS(cmd, data, debug)
    
if __name__ == '__main__' :
    main()
