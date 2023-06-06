#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import datetime

GLOBAL_RUNS = 17

def epoch_to_datetime(x): # convert epoch values from DARMA to datetime values which can be plotted nicely
    return datetime.datetime.fromtimestamp(x) # handled as timestamps

def to_int(x):
    return int(x)
  
def reduce_global_runs(x):
  return x - GLOBAL_RUNS
  
filename="timebaseLOL_2002-2302"

### plot all
plt.rc('xtick', labelsize=3)
nstaves=[ 12, 16, 20, 24, 30, 42, 48 ]
f=f"{filename}.txt"
df = pd.read_csv(f, sep=';', header=None, names=( "Timestamp", "DataPoint", "Value" ))
#df['Timestamp']=df['Timestamp'].apply(epoch_to_datetime)
df["Value"] = df["Value"].apply(to_int)
df.to_csv("pre_filter.txt", sep=';', header=None)
df = df.loc[df["DataPoint"].str.contains("timebaseLOL")]
df = df[df["Value"] > 0]

#df = df.loc[~(df["DataPoint"].str.contains("L1_09"))] # Filtered because of scrubbing issues


df.to_csv("post_filter.txt", sep=';', header=None)

staves = pd.DataFrame(columns=["Stave", "TB LOL"])

for l in range(7):
    for st in range(nstaves[l]):
        datapoint=f"L{l}_{st:02d}"
        sel = df.loc[df['DataPoint'].str.contains(datapoint)]
        first = True
        for i, row in sel.iterrows():
            staveflags = pd.Series({"Stave": datapoint, "TB LOL": 1}).to_frame().T
            staves = pd.concat([staves, staveflags])
            

aggregation_functions = {'TB LOL': 'sum'}
staves_new = staves.groupby(staves['Stave']).aggregate(aggregation_functions)

staves_new['TB LOL'] = staves_new["TB LOL"].apply(reduce_global_runs)
staves_new = staves_new[staves_new["TB LOL"] > 0]
print(f"RUs with LOLs: {len(staves_new)}")
staves_new.plot.bar(rot=0)
plt.savefig(f"{filename}.png", dpi=300, format='png')
