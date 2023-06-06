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

def filter_false_fec(df):
  df = df[df["Value"] != 0]

  # Filter out row that is negative because of ITS comm restarted
  # Current row is negative
  cond1 = df["Value"] < 0
  # Next row is positive and absolute value of negative row
  cond2 = abs(df["Value"]) == df.shift(-1)["Value"]
  filter_itscomm_restarted = cond1 & cond2

  # Filter out row that is positive because of monitoring restarted
  # Prev row was negative
  cond1 = df.shift(1)["Value"] < 0
  # Current row is positive and absolute value of negative row
  cond2 = df["Value"] == abs(df.shift(1)["Value"])
  filter_monitoring_restarted = cond1 & cond2

  return df[~(filter_itscomm_restarted | filter_monitoring_restarted)]

filename="deltaGBTx0_0305_1705"

### plot all
plt.rc('xtick', labelsize=3)
nstaves=[ 12, 16, 20, 24, 30, 42, 48 ]
f=f"{filename}.txt"
df = pd.read_csv(f, sep=';', header=None, names=( "Timestamp", "DataPoint", "Value" ))
#df['Timestamp']=df['Timestamp'].apply(epoch_to_datetime)
df["Value"] = df["Value"].apply(to_int)
df.to_csv("pre_filter.txt", sep=';', header=None)
df = df.loc[df["DataPoint"].str.contains("deltaFEC.GBTx")]

#df = df.loc[~(df["DataPoint"].str.contains("L1_09"))] # Filtered because of scrubbing issues

df = filter_false_fec(df)

df.to_csv("post_filter.txt", sep=';', header=None)

#print(df[df["DataPoint"].str.contains("L3_17")])

staves = pd.DataFrame(columns=["Stave", "FEC"])
for l in range(7):
    for st in range(nstaves[l]):
        datapoint=f"L{l}_{st:02d}"
        sel = df.loc[df['DataPoint'].str.contains(datapoint)]
        first = True
        for i, row in sel.iterrows():
            if first:
              first = False
              continue
            staveflags = pd.Series({"Stave": datapoint, "FEC": 1}).to_frame().T
            staves = pd.concat([staves, staveflags])


aggregation_functions = {'FEC': 'sum'}
staves_new = staves.groupby(staves['Stave']).aggregate(aggregation_functions)
staves_new = staves_new[staves_new["FEC"] > 9]
staves_new.plot.bar(rot=0)
plt.savefig(f"{filename}.png", dpi=300, format='png')