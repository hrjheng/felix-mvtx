#!/usr/bin/env python

import setPath
import subprocess

from GBT import *
from CRU import *

parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("-i", "--id", required=True, help="card ID")
parser.add_argument("-l", "--links", default="all", help="specifiy link IDs, eg. all, 1-4 or 1,3,4,16")
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true", default=False)
parser.add_argument("-cid", "--cruid", default="0", help="CRU ID")
parser.add_argument("-start", "--cru_start", action="store_true", default=False, help="CRU ENABLE")
parser.add_argument("-stop", "--cru_stop", action="store_true", default=False, help="CRU DISABLE (add -g option to stop generator at the same time)")
parser.add_argument("-g", "--gene", action="store_true", default=False, help="Use dwrapper data generator (commutator to use for stoppping as well)")

args = parser.parse_args()


cru = Cru(args.id, args.links, args.verbose)

id_card = args.id
cru_id = int(args.cruid, 0)

cru = Cru(args.id, args.links, args.verbose)

cru.bsp.setCRUid(cru_id)
 

if args.cru_start :
    if args.gene :
        cru.dwrapper.use_datagenerator_source(True)
        cmd=("o2-roc-reg-write --id={} --channel=0 --address=0xc00 --value=0x2".format(args.id))
        print ("BEWARE DEBUG mode was SET on only one endpoint !")
        ps=subprocess.check_output(cmd.split())
        cru.dwrapper.datagenerator_resetpulse()
        cru.dwrapper.datagenerator_enable(True)

    cru.bsp.enableRun()

if args.cru_stop :
    if args.gene :
        cru.dwrapper.use_datagenerator_source(False)
        cru.dwrapper.datagenerator_enable(False)
        cmd=("o2-roc-reg-write --id={} --channel=0 --address=0xc00 --value=0x0".format(args.id))
        print ("BEWARE DEBUG mode was REMOVED on only one endpoint !")
        ps=subprocess.check_output(cmd.split())
    cru.bsp.disableRun()
