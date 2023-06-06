#!/usr/bin/env python3

import os
import sys

script_path = os.path.dirname(os.path.realpath(__file__))
modules_path = os.path.join(
    script_path, '../')
sys.path.append(modules_path)
import module_include_felix

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
    parser.add_argument("-i", "--id", type=int, choices=(0,1), default=0, help="card ID")
    parser.add_argument("-l", "--links", type=int, default=0, help="specifiy link ID")
    parser.add_argument("-d", "--debug", action='store_true', help="run in debug mode")
    args = parser.parse_args()

    id_card = int(args.id)
    gbt_ch = args.links

    if  args.debug:
        debug = args.debug
    else :
        debug = None

    sca = Sca(id_card, 2, gbt_ch, debug)

    prev_choice = ''

    while True:
        showOption()
        try :
            choice = input('Enter a choice : ')
        except :
            choice = prev_choice

        if choice == '1' :
            #sca.reset(debug)
            sca.init(debug)
        elif choice == '2' :
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
        elif choice == '3' :
            try :
                mid_file = raw_input('MID cfg file [mid_cmds]: ')
            except:
                mid_file = mid_cmds

            sca.MidCfgFile(mid_file)
            sca.MIDEN(debug)

        elif choice == '4' :
            try :
                mch_file = raw_input('MCH cfg file [mch_cmds]: ')
            except:
                mch_file = mch_cmds

            sca.MchCfgFile(mch_file)
            sca.MCHEN(debug)
        elif choice == '20' :
            sca.gpioEn(debug)
        elif choice == '21' :
            data = input('DATA to GPIO : ')
            sca.gpioWr(int(data,16), debug)
        elif choice == '22' :
            data = input('DATA to GPIO [0/1]: ')
            sca.gpioINTENABLE(ch, int(data,16))
        elif choice == '23' :
            data = input('DATA to GPIO : ')
            sca.gpioINTSEL(ch, int(data,16))
        elif choice == '40' :
            sca.adcEn()
        elif choice == '41' :
            sca.scaID()
        else:
            sys.exit()

        prev_choice = choice

if __name__ == '__main__' :
    main()
