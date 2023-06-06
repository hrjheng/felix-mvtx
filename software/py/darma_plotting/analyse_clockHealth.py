#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import datetime


def epoch_to_datetime(x): # convert epoch values from DARMA to datetime values which can be plotted nicely
    return datetime.datetime.fromtimestamp(x) # handled as timestamps

def to_int(x):
    return int(x)

def decode_flags(flags):
    los = flags & 0x1
    lol = (flags >> 1) & 0x1
    xcku_lol = (flags >> 3) & 0x1
    return los, lol, xcku_lol

MINIMUM = 0
filename="clockHealth"


font = {'family': 'monospace',
        'color':  'black',
        'weight': 'normal',
        'size': 10,
        }

### plot all
plt.rc('xtick', labelsize=3)
nstaves=[ 12, 16, 20, 24, 30, 42, 48 ]
f=f"{filename}.txt"
df = pd.read_csv(f, sep=';', header=None, names=( "Timestamp", "DataPoint", "Value" ))
#df['Timestamp']=df['Timestamp'].apply(epoch_to_datetime)
df["Value"] = df["Value"].apply(to_int)
cH = df.loc[df["DataPoint"].str.endswith("clockHealth")]

staves = pd.DataFrame(columns=["Stave", "JC_LOS", "JC_LOL", "TB_LOL", "XCKU_LOL"])
num_lols = 0
prev_los, prev_lol, prev_xcku_lol = 0,0,0
for l in range(7):
    for st in range(nstaves[l]):
        datapoint=f"L{l}_{st:02d}"
        if l==6 and st==38:
            continue
        sel = cH.loc[cH['DataPoint'].str.contains(datapoint)]
        for i, row in sel.iterrows():
            # Not flag set, just reset prev value
            if row["Value"] == 0x0:
                prev_los, prev_lol, prev_xcku_lol = 0,0,0
                continue
            # Ignore pure Timebase LOL
            if row["Value"] == 0x4:
                prev_los, prev_lol, prev_xcku_lol = 0,0,0
                continue
            # Ignore invalid
            if row["Value"] not in range(16):
                prev_los, prev_lol, prev_xcku_lol = 0,0,0
                continue
            # Ignore pure xcku lol
            # if row["Value"] == 0x8:
            #     prev_los, prev_lol, prev_xcku_lol = 0,0,0
            #     continue
            # Ignore xcku/timebase lol
            # if row["Value"] == 0xc:
            #     prev_los, prev_lol, prev_xcku_lol = 0,0,0
            #     continue
            los, lol, xcku_lol = decode_flags(row["Value"])
            num_lols += 1
            # Ensure that a flag is not counted twice
            if prev_los != 0:
                los = 0
            if prev_lol != 0:
                lol = 0
            if prev_xcku_lol != 0:
                xcku_lol = 0
            prev_los, prev_lol, prev_xcku_lol = los, lol, xcku_lol
            staveflags = pd.Series({"Stave": datapoint, "JC_LOS": los, "JC_LOL": lol, "XCKU_LOL": xcku_lol}).to_frame().T
            staves = pd.concat([staves, staveflags])


aggregation_functions = {'JC_LOS': 'sum', 'JC_LOL': 'sum', 'XCKU_LOL': 'sum'}
staves_new = staves.groupby(staves['Stave']).aggregate(aggregation_functions)

s = staves_new.reset_index()
s = s.assign(CRU=None)

# L0T - CRU 183
s.loc[s["Stave"].str.contains(r'L0_0[0-5]'), "CRU"] = 183
# L0B - CRU 172
s.loc[s["Stave"].str.contains(r'L0_(0[6789]|[1].)'), "CRU"] = 172

# L1T - CRU 181
s.loc[s["Stave"].str.contains(r'L1_0[0-7]'), "CRU"] = 181
# L1B - CRU 196
s.loc[s["Stave"].str.contains(r'L1_(0[89]|[1].)'), "CRU"] = 196

# L2TI - CRU 184
s.loc[s["Stave"].str.contains(r'L2_0[0-4]'), "CRU"] = 184
# L2TO - CRU 191
s.loc[s["Stave"].str.contains(r'L2_0[5-9]'), "CRU"] = 191
# L2BO - CRU 179
s.loc[s["Stave"].str.contains(r'L2_1[0-4]'), "CRU"] = 179
# L2BI - CRU 192
s.loc[s["Stave"].str.contains(r'L2_1[5-9]'), "CRU"] = 192

# L3T - CRU 175
s.loc[s["Stave"].str.contains(r'L3_(0[0-9]|1[0-1])'), "CRU"] = 172
# L3B - CRU 182
s.loc[s["Stave"].str.contains(r'L3_(1[2-9]|2[0-3])'), "CRU"] = 182

# L4TI - CRU 187
s.loc[s["Stave"].str.contains(r'L4_0[0-7]'), "CRU"] = 187
# L4TO - CRU 176
s.loc[s["Stave"].str.contains(r'L4_(0[8-9]|1[0-4])'), "CRU"] = 176
# L4BO - CRU 178
s.loc[s["Stave"].str.contains(r'L4_(1[5-9]|2[0-2])'), "CRU"] = 178
# L4BI - CRU 177
s.loc[s["Stave"].str.contains(r'L4_2[3-9]'), "CRU"] = 177

# L5TI - CRU 194
s.loc[s["Stave"].str.contains(r'L5_0[0-9]'), "CRU"] = 194
# L5TO - CRU 174
s.loc[s["Stave"].str.contains(r'L5_(1[0-9]|20)'), "CRU"] = 174
# L5BO - CRU 193
s.loc[s["Stave"].str.contains(r'L5_(2[1-9]|30)'), "CRU"] = 193
# L5BI - CRU 180
s.loc[s["Stave"].str.contains(r'L5_(3[1-9]|4[0-1])'), "CRU"] = 180

# L6TI - CRU 185
s.loc[s["Stave"].str.contains(r'L6_(0[0-9]|1[0-1])'), "CRU"] = 185
# L6TO - CRU 189
s.loc[s["Stave"].str.contains(r'L6_(1[2-9]|2[0-3])'), "CRU"] = 189
# L6BO - CRU 195
s.loc[s["Stave"].str.contains(r'L6_(2[4-9]|3[0-5])'), "CRU"] = 195
# L6BI - CRU 186
s.loc[s["Stave"].str.contains(r'L6_(3[6-9]|4[0-7])'), "CRU"] = 186

# Subtract baseline based on CRU
s["XCKU_LOL"] = s.groupby("CRU")["XCKU_LOL"].transform(lambda x: (x-x.min()))
s["JC_LOL"] = s.groupby("CRU")["JC_LOL"].transform(lambda x: (x-x.min()))
s["JC_LOS"] = s.groupby("CRU")["JC_LOS"].transform(lambda x: (x-x.min()))



jc_lol = s['JC_LOL'].sum()
jc_los = s['JC_LOS'].sum()
xcku_lol = s['XCKU_LOL'].sum()

textstr = '\n'.join((
    r'jc_lol   = %d' % (jc_lol, ),
    r'jc_los   = %d' % (jc_los, ),
    r'xcku_lol = %d' % (xcku_lol, )))

# Only plot above zero staves
s = s[(s['XCKU_LOL'] > MINIMUM) | (s['JC_LOL'] > MINIMUM) | (s['JC_LOS'] > MINIMUM)]

s.plot.bar(rot=0, x="Stave", y=["XCKU_LOL", "JC_LOS", "JC_LOL"])
plt.text(1, 7, textstr, fontdict=font)

#plt.show()
plt.savefig(f"{filename}.png", dpi=300, format='png')

print(f"JC_LOL: {jc_lol}")
print(f"JC_LOS: {jc_los}")
print(f"XCKU_LOL: {xcku_lol}")
