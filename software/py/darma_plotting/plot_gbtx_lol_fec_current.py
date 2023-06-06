#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

def loop_and_create_dataframe(string):
    l = list()
    for str in [line.split() for line in lines if string in line]:
        val = float(str[-1])
        time = str[0] + " " + str[1]
        dt = datetime.strptime(time, "%Y-%m-%d %H:%M:%S,%f")
        l.append((dt,val))
    return l

filename="testbench"

I_1V5 = None
V_1V5 = None
LOL = None
FEC = None



with open(f"{filename}.log") as fp:
    lines = fp.readlines()
    lines = [line for line in lines if "RDO  0" in line]
    I_1V5 = pd.DataFrame(loop_and_create_dataframe("I_1V5:"), columns=["Time", "I"])
    V_1V5 = pd.DataFrame(loop_and_create_dataframe("V_1V5:"), columns=["Time", "V"])
    LOL = pd.DataFrame(loop_and_create_dataframe("LOL:"), columns=["Time", "LOL"])
    FEC = pd.DataFrame(loop_and_create_dataframe("FEC:"), columns=["Time", "FEC"])

# print(I_1V5.head())
# print(V_1V5.head())
# print(LOL.head())
# print(FEC.head())

ax = I_1V5.plot(x="Time", y="I", linewidth=0.2)
V_1V5.plot(ax=ax, x="Time", y="V", linewidth=0.2)
LOL.plot(ax=ax, x="Time", y="LOL", linewidth=0.5)
ax2 = ax.twinx()
color = 'tab:red'
ax2.set_ylabel("FEC", color=color)
FEC.plot(ax=ax2, x="Time", y="FEC", linewidth=0.5, color=color)

lines_123, labels_123 = ax.get_legend_handles_labels()
lines_4, labels_4 = ax2.get_legend_handles_labels()
lines = lines_123 + lines_4
labels = labels_123 + labels_4

ax.legend(lines, labels, loc=0)
ax2.legend().set_visible(False)

plt.savefig(f"{filename}.png", dpi=300, format='png')