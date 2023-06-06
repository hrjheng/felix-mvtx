#!/usr/bin/env python3

import sys
import subprocess
import os
import json
from multiprocessing import Pool

SCRIPT_PATH=os.path.dirname(os.path.realpath(__file__))+'/'
DECODER=SCRIPT_PATH+'../decoder/decoder'
if not os.path.isfile(DECODER):
    print('decoder executable not found, is it compiled?')
    sys.exit(1)

INPUTS=[
    # IBT0
    ('data-ep2-link0.lz4' ,      0),
    ('data-ep2-link1.lz4' ,      1),
    ('data-ep2-link2.lz4' ,      2),
    ('data-ep2-link3.lz4' ,      3),
    ('data-ep2-link4.lz4' ,      4),
    ('data-ep2-link5.lz4' ,      5),
    # IBB0                      
    ('data-ep5-link0.lz4' ,      6),
    ('data-ep5-link1.lz4' ,      7),
    ('data-ep5-link2.lz4' ,      8),
    ('data-ep5-link3.lz4' ,      9),
    ('data-ep5-link4.lz4' ,     10),
    ('data-ep5-link5.lz4' ,     11),
    # IBT1
    ('data-ep2-link0.lz4' ,4096+ 0),
    ('data-ep2-link1.lz4' ,4096+ 1),
    ('data-ep2-link2.lz4' ,4096+ 2),
    ('data-ep2-link3.lz4' ,4096+ 3),
    ('data-ep2-link4.lz4' ,4096+ 4),
    ('data-ep2-link5.lz4' ,4096+ 5),
    ('data-ep2-link6.lz4' ,4096+ 6),
    ('data-ep2-link7.lz4' ,4096+ 7),
    # IBT1
    ('data-ep5-link0.lz4' ,4096+ 8),
    ('data-ep5-link1.lz4' ,4096+ 9),
    ('data-ep5-link2.lz4' ,4096+ 10),
    ('data-ep5-link3.lz4' ,4096+ 11),
    ('data-ep5-link4.lz4' ,4096+ 12),
    ('data-ep5-link5.lz4' ,4096+ 13),
    ('data-ep5-link6.lz4' ,4096+ 14),
    ('data-ep5-link7.lz4' ,4096+ 15),
    #IBT2A
    ('data-ep5-link0.lz4' ,8192+ 0),
    ('data-ep5-link1.lz4' ,8192+ 1),
    ('data-ep5-link2.lz4' ,8192+ 2),
    ('data-ep5-link3.lz4' ,8192+ 3),
    ('data-ep5-link4.lz4' ,8192+ 4),
    #IBT2B
    ('data-ep2-link0.lz4' ,8192+ 5),
    ('data-ep2-link1.lz4' ,8192+ 6),
    ('data-ep2-link2.lz4' ,8192+ 7),
    ('data-ep2-link3.lz4' ,8192+ 8),
    ('data-ep2-link4.lz4' ,8192+ 9),
    #IBB2A
    ('data-ep2-link0.lz4' ,8192+10),
    ('data-ep2-link1.lz4' ,8192+11),
    ('data-ep2-link2.lz4' ,8192+12),
    ('data-ep2-link3.lz4' ,8192+13),
    ('data-ep2-link4.lz4' ,8192+14),
    #IBB2B
    ('data-ep5-link0.lz4' ,8192+15),
    ('data-ep5-link1.lz4' ,8192+16),
    ('data-ep5-link2.lz4' ,8192+17),
    ('data-ep5-link3.lz4' ,8192+18),
    ('data-ep5-link4.lz4' ,8192+19),
]

def thrana(path,feeid,n,cwd):
    subprocess.run('lz4cat %s | %s thrmap6 /dev/stdin %d "" %d > /dev/null'%(path,DECODER,feeid,n),cwd=cwd,shell=True)

def process(path):
    n=None
    print('Processing "%s"...'%path)
    with open(path+'/run_parameters.json') as f:
        p=json.loads(f.read())
        n=len(p['_vcasn_ithr_list'])
    if n==None:
        print('Error reading run_parameters.json')
        return
    
    outdir = path+'/thrtun/'
    try:
        os.mkdir(outdir)
    except FileExistsError:
        pass
    print('  ... decoding to "%s"...'%outdir)
    with Pool(8) as pool:
        for fname,feeid in INPUTS:
            if os.path.isfile(path+'/'+fname):
                pool.apply_async(thrana,(path+'/'+fname,feeid,n,outdir))
        pool.close()
        pool.join()

paths=sys.argv[1:]

for path in paths:
    process(path)

