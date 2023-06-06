"""
@author = magnus.ersdal@uib.no
For usage see make_all_ECC_files.py
"""

import os
import numpy as np
import sys

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from ecc_functions_opt import gen_ecc, precalc_indices

def make_ecc_file(infilename, fileending="_ecc.bit", indata=None, verbose=False):
    """Create ECC bitfile from bitfile"""
    i_fn = os.path.realpath(infilename)
    o_fn = i_fn[:-4] + fileending
    if verbose:
        print("Generating ECC file for ", i_fn)
    if indata is None:
        with open(i_fn, 'rb') as f:
            indata = f.read()
    eccdata = make_ecc(indata, verbose=verbose)
    with open(o_fn, 'wb') as f:
        nchrs = f.write(eccdata[:])
    assert nchrs == len(eccdata), "Not all bytes written to disk"
    if verbose:
        print("Generated ECC file " + o_fn)
    return o_fn, eccdata[:]

def make_ecc(data, verbose=False):
    """Create ECC data"""
    s = bytearray(data)
    assert len(s) > 0, "0 length data provided to function"
    # padding functions
    modlarge = len(s) % 4096
    if modlarge != 0:
        if verbose:
            print("Padding to 4096")
        s.extend([0xff] * (4096 - modlarge))

    nbytes = 128
    schunks = chunks(s, nbytes)
    # generator obj

    ab = np.array(list(schunks), dtype=np.uint8)
    finallen = len(ab[-1])
    if finallen != 128:
        temp = bytearray(ab[-1])
        temp.extend(b'\xFF' * (128 - finallen))
        ab[-1] = temp
        # we need to pad.
    # end padding
    if verbose:
        print("Running ECC code generation")
    ec_codes_li, ec_codes_col  = gen_ecc(ab, precalc_indices)

    result = bytearray()
    for data, li, co in zip(ab, ec_codes_li, ec_codes_col):
        lico = (li << 6) | co  # 2 lsbit in li = 2 msb in co
        lico = int(lico).to_bytes(3, byteorder='little')  # should be little
        data = list(data) + list(lico)  # li + co
        result.extend(data)
    return result[:]

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]
