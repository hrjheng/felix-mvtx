"""
@author = magnus.ersdal@uib.no
"""
import os

import fire

from ecc_functions import make_ecc_file

def make_parameter_file(paramfile_name, startblock, scrubstartblock, goldstartblock, verbose=False):
    """Generate parameter files for storing in flash"""
    paramfile_name = os.path.realpath(paramfile_name)
    PAGE_SIZE = 4096
    # some constants from Gitle M.
    PAGE_PER_BLOCK = 64
    BLOCK_SIZE = PAGE_SIZE * PAGE_PER_BLOCK
    PATTERN = 0x665599AA  # 0xAA995566 in other endian ! .
    # magical constants for xilinx xkcu! please please do not touch..
    FWSIZE = 5889
    BSSIZE = 4504

    if verbose:
        print([hex(x) for x in [PAGE_SIZE, PAGE_PER_BLOCK, BLOCK_SIZE, FWSIZE, BSSIZE]])

    FW_PAGE_ADDR = startblock * PAGE_PER_BLOCK
    FW_PAGE_END_ADDR = FW_PAGE_ADDR + FWSIZE
    SCRUB_PAGE_ADDR = scrubstartblock * PAGE_PER_BLOCK
    SCRUB_PAGE_END_ADDR = SCRUB_PAGE_ADDR + BSSIZE
    GOLD_PAGE_ADDR = goldstartblock * PAGE_PER_BLOCK
    GOLD_PAGE_END_ADDR = GOLD_PAGE_ADDR + FWSIZE

    data = [(FW_PAGE_ADDR, 3), (0, 1),
            (FW_PAGE_END_ADDR, 3), (0, 1), (PATTERN, 4)]
    data += [(SCRUB_PAGE_ADDR, 3), (0, 1),
             (SCRUB_PAGE_END_ADDR, 3), (0, 1), (PATTERN, 4)]
    data += [(GOLD_PAGE_ADDR, 3), (0, 1),
             (GOLD_PAGE_END_ADDR, 3), (0, 1), (PATTERN, 4)]

    result = bytearray()
    for d, size in data:
        try:
            bytesdata = d.to_bytes(length=size, byteorder='big')
        except OverflowError as oe:
            print(f"d = 0x{d}")
            raise oe
        result.extend(bytesdata)

    remlen = PAGE_SIZE - len(result)
    result.extend(b'\xFF' * (remlen))
    assert len(result) == PAGE_SIZE
    with open(paramfile_name, 'wb') as f:
        nchrs = f.write(result[:])
    assert nchrs == PAGE_SIZE, "Not all bytes written to disk"
    if verbose:
        print("Parameter file of {} chars written".format(nchrs))
    return paramfile_name, result[:]


def make_parameter_file_and_ecc(paramfile_name, startblock, scrubstartblock, goldstartblock, verbose=True):
    """ make file and ecc it
    """
    pfile, pdata = make_parameter_file(paramfile_name, startblock, scrubstartblock, goldstartblock, verbose=verbose)
    eccfile, eccdata = make_ecc_file(infilename=pfile, indata=pdata, verbose=verbose)
    return eccfile, eccdata

if __name__ == '__main__':
    fire.Fire(make_parameter_file_and_ecc)
