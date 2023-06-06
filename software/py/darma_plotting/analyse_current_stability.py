#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import datetime


filename="L1_09_self_reset"


f=f"{filename}.txt"
df = pd.read_csv(f, sep=';', header=None, names=( "Timestamp", "DataPoint", "Value" ))
#df['Timestamp']=df['Timestamp'].apply(datetime_to_epoch)
I_INT = df[df["DataPoint"].str.endswith("I_INT") & df["Value"] > 0]
I_1V2 = df[df["DataPoint"].str.endswith("I_1V2") & df["Value"] > 0]
I_1V5 = df[df["DataPoint"].str.endswith("I_1V5") & df["Value"] > 0]
I_1V8 = df[df["DataPoint"].str.endswith("I_1V8") & df["Value"] > 0]
I_2V5 = df[df["DataPoint"].str.endswith("I_2V5") & df["Value"] > 0]
I_3V3 = df[df["DataPoint"].str.endswith("I_3V3") & df["Value"] > 0]
I_IN = df[df["DataPoint"].str.endswith("I_IN")   & df["Value"] > 0]
V_IN = df[df["DataPoint"].str.endswith("V_IN")   & df["Value"] > 0]

# df = pd.DataFrame([, I_1V2, I_1V5, I_1V8, I_2V5, I_3V3, I_IN, V_IN], index=["I_INT", "I_1V2", "I_1V5", "I_1V8", "I_2V5", "I_3V3", "I_IN", "V_IN"]).T
# 
#print(I_INT.head())
ax = I_INT.plot(x="Timestamp", y="Value", linewidth=0.2, label="I_INT")
I_1V2.plot(ax=ax, x="Timestamp", y="Value", linewidth=0.2, label="I_1V2")
#I_1V5.plot(ax=ax, x="Timestamp", y="Value", linewidth=0.2, label="I_1V5")
I_1V8.plot(ax=ax, x="Timestamp", y="Value", linewidth=0.2, label="I_1V8")
#I_2V5.plot(ax=ax, x="Timestamp", y="Value", linewidth=0.2, label="I_2V5")
I_3V3.plot(ax=ax, x="Timestamp", y="Value", linewidth=0.2, label="I_3V3")
I_IN.plot(ax=ax, x="Timestamp", y="Value", linewidth=0.2, label="I_IN")

#V_IN.plot(ax=ax, x="Timestamp", y="Value", linewidth=0.2, label="V_IN")

ax.set_xticks([1645475714, 1645568529])
ax.set_xticklabels(["21.02.2022;20:35", "22.02.2022;22:22"])

# ax.set_ylim([6.6, 7.1])

plt.savefig(f"{filename}.png", dpi=300, format='png')