#!/usr/bin/env python3

import sys
import subprocess
import os
import json
from multiprocessing import Pool

SCRIPT_PATH=os.path.dirname(os.path.realpath(__file__))+'/'
DECODER=SCRIPT_PATH+'../../../cpp/decoder/mvtx-decoder'
if not os.path.isfile(DECODER):
    print('decoder executable not found, is it compiled?')
    sys.exit(1)

PACKETS= [ 2001, 2002 ]
INPUTS=[ (8212,8213,8214,8215,8468,8469,8470,8471,8724,8725,8726,8727),
         (8216,8217,8218,8219,8472,8473,8474,8475,8728,8729,8730,8731)
]

def thrana(path, packet, feeid, n, cwd):
  subprocess.run(f'source /home/mvtx/software/setup.sh > /dev/null && ddump -s -g -p {packet}  -n 0 {path} | {DECODER} -t 2 -f {feeid} -n {n} > /dev/null', cwd=cwd, shell=True)

def process(path):
    dir = os.path.dirname(path)
    n=None
    print('Processing "%s"...'%path)
    with open(dir+'/run_parameters.json') as f:
        p=json.loads(f.read())
        n=len(p['_vcasn_ithr_list'])
    if n==None:
        print('Error reading run_parameters.json')
        return

    outdir = dir+'/thrtun/'
    try:
        os.mkdir(outdir)
    except FileExistsError:
        pass
    print('  ... decoding to "%s"...'%outdir)
    with Pool(None) as pool:
        if os.path.isfile(path):
            for i,packet in enumerate(PACKETS):
                for feeid in INPUTS[i]:
                    pool.apply_async(thrana,(path,packet,feeid,n,outdir))
        pool.close()
        pool.join()

paths=sys.argv[1:]

for path in paths:
    process(path)

