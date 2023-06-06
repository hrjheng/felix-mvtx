#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

filename="lol_fec_comparison"

### plot all
labels = ['L0_00', 'L0_05', 'L6_26', 'L6_32', 'L6_33', 'L6_34', 'L6_35']
LOL = [2, 1, 0, 1, 1, 0, 1]
FEC = [2, 1, 1, 4, 1, 1, 2]

x = np.arange(len(labels))  # the label locations
width = 0.35  # the width of the bars

fig, ax = plt.subplots()
rects1 = ax.bar(x - width/2, LOL, width, label='LOL')
rects2 = ax.bar(x + width/2, FEC, width, label='FEC')

# Add some text for labels, title and custom x-axis tick labels, etc.
ax.set_ylabel('Events')
ax.set_title('LOL/FEC Comparison')
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.legend()


# def autolabel(rects):
#     """Attach a text label above each bar in *rects*, displaying its height."""
#     for rect in rects:
#         height = rect.get_height()
#         ax.annotate('{}'.format(height),
#                     xy=(rect.get_x() + rect.get_width() / 2, height),
#                     xytext=(0, 3),  # 3 points vertical offset
#                     textcoords="offset points",
#                     ha='center', va='bottom')


# autolabel(rects1)
# autolabel(rects2)

fig.tight_layout()
plt.savefig(f"{filename}.png", dpi=300, format='png')
