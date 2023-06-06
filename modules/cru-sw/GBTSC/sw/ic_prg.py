#!/usr/bin/env python

import setThisPath


import sys

import IC 
from IC import Ic


def showOption() :
    print ('-------------------')
    print('20) SET ADD')
    print('21) WRITE REG')
    print('22) READ REG')
    print('Else) QUIT')
    print ('-------------------')
    
def main():
    id_card = sys.argv[1]
    gbt_ch = sys.argv[2]
    bar = 2 
    debug = None

    ic = Ic(id_card, bar, gbt_ch, debug)

    prev_choice = ''

    while True:
        showOption()
        try : 
            choice = input('Enter a choice : ')
        except : 
            choice = prev_choice

        if choice == 20 :
            reg = input('REG  : ')
            ic.wrGBTI2Cadd(reg, debug)
        elif choice == 21 :
            data = input('DATA  : ')
            reg = input('REG  : ')
            ic.wr(reg, data, debug)
        elif choice == 22 :
            data = input('DATA  : ')
            reg = input('REG  : ')
            ic.rd(reg, data, debug)
        elif choice == 23 :
            ic.rdfifo()
        elif choice == 24 :
            ic.rdsm()
        else:
            sys.exit()
            
        prev_choice = choice
    
if __name__ == '__main__' :
    main()
