#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import datetime


def epoch_to_datetime(x): # convert epoch values from DARMA to datetime values which can be plotted nicely
    return datetime.datetime.fromtimestamp(x) # handled as timestamps

### single curve    
#datapoint="L0_01"
#f="VTRx1_MM.txt"
#
#df = pd.read_csv(f, sep=';', header=None, names=( "Timestamp", "DataPoint", "Value" ))
#df['Timestamp']=df['Timestamp'].apply(epoch_to_datetime)
#sel = df.loc[(df['Value']>0.) & df['DataPoint'].str.contains(datapoint) & ((df['Timestamp'] < datetime.datetime(2021,10,12,16,0,0)) | (df['Timestamp'] > datetime.datetime(2021,10,12,18,0,0))) & ((df['Timestamp'] < datetime.datetime(2021,8,17,10,0,0)) | (df['Timestamp'] > datetime.datetime(2021,8,17,11,0,0))) & ((df['Timestamp'] < datetime.datetime(2021,8,19,0,0,0)) | (df['Timestamp'] > datetime.datetime(2021,8,25,23,59,50)))]
#sel.plot(x='Timestamp', y='Value', xlabel="Time", ylabel="VTRx0 MM RSSI current (uA)", legend=False)
#plt.savefig("output.png", dpi=300, format='png')
#plt.show() # show for further inspection
#quit()

### plot all

nstaves=[ 12, 16, 20, 24, 30, 42, 48 ]
f="clockHealth.txt"
df = pd.read_csv(f, sep=';', header=None, names=( "Timestamp", "DataPoint", "Value" ))
df['Timestamp']=df['Timestamp'].apply(epoch_to_datetime)


for layer in range(7):
    for stave in range(nstaves[layer]):
        datapoint=f"L{layer}_{stave:02d}"
        sel = df.loc[(df['Value']>0.) & df['DataPoint'].str.contains(datapoint) & ((df['Timestamp'] < datetime.datetime(2021,10,12,16,0,0)) | (df['Timestamp'] > datetime.datetime(2021,10,12,18,0,0))) & ((df['Timestamp'] < datetime.datetime(2021,8,17,10,0,0)) | (df['Timestamp'] > datetime.datetime(2021,8,17,11,0,0))) & ((df['Timestamp'] < datetime.datetime(2021,8,19,0,0,0)) | (df['Timestamp'] > datetime.datetime(2021,8,25,23,59,59)))]
        sel = sel.rename(columns={"Value":datapoint})
        sel.plot(x='Timestamp', y=datapoint, xlabel="Time", ylabel="VTRx0 MM RSSI current (uA)") # ylim=(200,400))
        plt.xlabel("Time")
        plt.ylabel("VTRx RSSI (uA)")
        plt.savefig(datapoint+"_VTRx0_MM.png", dpi=300, format='png')
        plt.close()

# f="VTRx2_SM.txt"   
# df = pd.read_csv(f, sep=';', header=None, names=( "Timestamp", "DataPoint", "Value" ))
# df['Timestamp']=df['Timestamp'].apply(epoch_to_datetime)
# for layer in range(7):
#     for stave in range(nstaves[layer]):
#         datapoint=f"L{layer}_{stave:02d}"
#         sel = df.loc[(df['Value']>0.) & df['DataPoint'].str.contains(datapoint) & ((df['Timestamp'] < datetime.datetime(2021,10,12,16,0,0)) | (df['Timestamp'] > datetime.datetime(2021,10,12,18,0,0))) & ((df['Timestamp'] < datetime.datetime(2021,8,17,10,0,0)) | (df['Timestamp'] > datetime.datetime(2021,8,17,11,0,0))) & ((df['Timestamp'] < datetime.datetime(2021,8,19,0,0,0)) | (df['Timestamp'] > datetime.datetime(2021,8,25,23,59,59)))]
#         sel = sel.rename(columns={"Value":datapoint})
#         sel.plot(x='Timestamp', y=datapoint, xlabel="Time", ylabel="VTRx2 SM RSSI current (uA)") #, ylim=(0,100))
#         plt.savefig(datapoint+"_VTRx2_SM.png", dpi=300, format='png')
#         plt.close()
        
