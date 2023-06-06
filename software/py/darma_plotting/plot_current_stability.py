#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def loop_and_add_to_list(list, string):
    for val in [float(line.split()[-2]) for line in lines if string in line]:
       list.append(val)

filename="SN53_scrubbing"

I_INT = []
I_1V2 = []
I_1V5 = []
I_1V8 = []
I_2V5 = []
I_3V3 = []
I_IN  = []
V_IN  = []

with open(f"{filename}.log") as fp:
    lines = fp.readlines()
    loop_and_add_to_list(I_INT, "I_INT:")
    loop_and_add_to_list(I_1V2, "I_1V2:")
    loop_and_add_to_list(I_1V5, "I_1V5:")
    loop_and_add_to_list(I_1V8, "I_1V8:")
    loop_and_add_to_list(I_2V5, "I_2V5:")
    loop_and_add_to_list(I_3V3, "I_3V3:")
    loop_and_add_to_list(I_IN, "I_IN:")
    loop_and_add_to_list(V_IN, "V_IN:")

df = pd.DataFrame([I_INT, I_1V2, I_1V5, I_1V8, I_2V5, I_3V3, I_IN, V_IN], index=["I_INT", "I_1V2", "I_1V5", "I_1V8", "I_2V5", "I_3V3", "I_IN", "V_IN"]).T
#ax = df.plot(y=["I_INT", "I_1V2", "I_1V5", "I_1V8", "I_2V5", "I_3V3", "I_IN"])
ax = df.plot(y=["V_IN"])

ax.set_xticks([0, 730])
ax.set_xticklabels(["2022-02-18 09:56", "2022-02-18 22:43"])

ax.set_ylim([6.6, 7.1])

plt.savefig(f"{filename}.png", dpi=300, format='png')