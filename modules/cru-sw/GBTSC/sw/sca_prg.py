#!/usr/bin/env python

import setThisPath

import sys
import argparse

import SCA 
from SCA import Sca


def showOption() :
    print ('-------------------')
    print('1) INIT SCA')
    print('2) TPC config')
    print('3) MID config')
    print('4) MCH config')
    print('20) ENABLE GPIO')
    print('21) Push DATA to GPIO')
    print('22) GPIO INTENABLE')
    print('23) GPIO INTSEL')
    print('40) ENABLE ADC ch')
    print('41) SCA ID')
    print('Else) QUIT')
    print ('-------------------')
    
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", required=True, help="card ID")
    parser.add_argument("-b", "--board", default="CRU", help="card type CRU/GRORC")
    parser.add_argument("-l", "--links", type=int, default=0, help="specifiy link ID")
    args = parser.parse_args()
        
    id_card = args.id
    gbt_ch = args.links
    board = args.board
    
    if len(sys.argv) == 5 : 
        debug = sys.argv[4]
    else :
        debug = None
        
    sca = Sca(id_card, 2, gbt_ch, board, debug)

    sca.displayAdd()

    prev_choice = ''

    while True:
        showOption()
        try : 
            choice = input('Enter a choice : ')
        except : 
            choice = prev_choice

        if choice == 1 :
            sca.init(debug)
            sca.reset(debug)
        elif choice == 2 :
            try : 
                tpc_file = raw_input('TPC cfg file [tpc_cmds]: ')
            except:
                tpc_file = tpc_cmds
                
            try : 
                slow = input('SLOW[0/1]: ')
            except:
                slow = 0
            
            sca.TpcCfgFile(tpc_file)
            sca.TPCEN(slow, debug)
        elif choice == 3 :
            try : 
                mid_file = raw_input('MID cfg file [mid_cmds]: ')
            except:
                mid_file = mid_cmds
                
            sca.MidCfgFile(mid_file)
            sca.MIDEN(debug)

        elif choice == 4 :
            try : 
                mch_file = raw_input('MCH cfg file [mch_cmds]: ')
            except:
                mch_file = mch_cmds
                
            sca.MchCfgFile(mch_file)
            sca.MCHEN(debug)            
        elif choice == 20 :
            sca.gpioEn(debug)
        elif choice == 21 :
            data = input('DATA to GPIO : ')
            sca.gpioWr(data, debug)
        elif choice == 22 :
            data = input('DATA to GPIO [0/1]: ')
            sca.gpioINTENABLE(ch, data)
        elif choice == 23 :
            data = input('DATA to GPIO : ')
            sca.gpioINTSEL(ch, data)
        elif choice == 40 :
            sca.adcEn()
        elif choice == 41 :
            sca.scaID()
        else:
            sys.exit()
            
        prev_choice = choice
    
if __name__ == '__main__' :
    main()
