'''
Created on 4. apr. 2019

@author: Magnus Ersdal, Arild Velure

Optimized functions for ECC generation.
Don't add to modules_includes as the loader doesn't handle numba
'''
from functools import lru_cache
import operator as op
from numba import njit
import numpy as np

# precalc values
C_precalc = tuple([0x55, 0xaa, 0x33, 0xcc, 0x0f, 0xf0])
A_precalc = tuple([0b1 << i for i in range(7)])

@lru_cache(maxsize=None)
def indices_with_cache(cnt):
    f_a = list(map(lambda x: (cnt & x) != x, A_precalc))  # 0x1, 0x2, 0x4 etc.
    return np.fromiter(map(op.sub, range(1, 15, 2), f_a), dtype=np.uint8)  # 1 - True = 0. make parity indices

# more precalculated values for ecc function
precalc_indices = tuple([indices_with_cache(x) for x in range(128)])

@njit(nogil=True)
def ecc(userbytes, precalc):
    """Makes error correcting codes with 14 bits of line parity and 6 bits of column parity"""
    lp = [0]*14
    cp = [0]*6
    for cnt in range(128):
        # line parity
        prty = parity_byte(userbytes[cnt])
        for i in precalc[cnt]:
            lp[i] = lp[i] ^ prty
        for i in range(6):
            cp[i] = parity_byte(userbytes[cnt] & C_precalc[i]) ^ cp[i]
    return [bit_array_to_int(lp), bit_array_to_int(cp)]

@njit(nogil=True)
def gen_ecc(ab, precalc):
    """Generates the ECC code"""
    ret_l = [0]*len(ab)
    ret_c = [0]*len(ab)
    for i in range(len(ab)):
        ret_l[i], ret_c[i] = ecc(ab[i], precalc)
    return ret_l, ret_c

@njit(nogil=True)
def bit_array_to_int(bit_array):
    a = 0
    for i in range(len(bit_array)):
        a |= (bit_array[i]&0x1) << i
    return a

@njit(nogil=True)
def parity_byte(v):
    """Gets parity of byte, even parity"""
    par = 0
    for i in range(8):
        par = par ^ ((v >> i)&0x1)
    return par
