#!/usr/bin/env python3

import argparse
import json

import matplotlib
import matplotlib.pyplot as plt


argparser = argparse.ArgumentParser(description="Very simple analysis of DAC scan")
argparser.add_argument('fname', metavar='FILE', help='Path to file to analyse.')
argparser.add_argument('stave', help='Stave ID to analyse.')
argparser.add_argument('chip', help='Chip ID to analyse.')
argparser.add_argument('--avdd-correction', action='store_true', help='Correct DAC measurement for AVDD shifts')
args=argparser.parse_args()

fname = args.fname
stave = args.stave
chip = args.chip
correction = args.avdd_correction

DACS = [
    'VRESETP',
    'VRESETD',
    'VCASP',
    'VCASN',
    'VPULSEH',
    'VPULSEL',
    'VCASN2',
    'VCLIP',
    'VTEMP',
    'IAUX2',
    'IRESET',
    'IDB',
    'IBIAS',
    'ITHR',
]

with open(fname) as f:
    data_all = json.load(f)

data = data_all[stave]
data['STEPS'] = data_all['STEPS']

if correction:
    for dac in data[chip].keys():
        for step in data['STEPS'][1:]:
            corr = data[chip][dac]['AVDD'][step-1]/data[chip][dac]['AVDD'][step]
            data[chip][dac]['AVDD'][step] *= corr
            data[chip][dac]['Value'][step] *= corr

font = {'size'   : 13}
matplotlib.rc('font', **font)
fig, ax = plt.subplots(2,2, figsize=(13,8))
fig.subplots_adjust(left=0.07, right=0.95, top=0.95, bottom=0.1)

for dac in DACS:
    if dac[0]=='V':
        ax[0,0].plot(data['STEPS'], data[chip][dac]['AVDD'], label=dac)
        ax[1,0].plot(data['STEPS'], data[chip][dac]['Value'], label=dac)
    elif dac[0]=='I':
        ax[0,1].plot(data['STEPS'], data[chip][dac]['AVDD'], label=dac)
        ax[1,1].plot(data['STEPS'], data[chip][dac]['Value'], label=dac)

#ax[0,1].plot(data['STEP'], corr, label='CORR')

for j in range(2):
    ax[0,j].set_ylabel('AVDD [ADC]')
    ax[1,j].set_ylabel('Value [ADC]')
    for i in range(2):
        #plt.xticks(dvdds)
        ax[i,j].set_xlim(-5, 310)
        ax[i,j].set_xlabel('DAC')
        ax[i,j].legend(loc='best')

plt.show()
