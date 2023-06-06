"""
File for plotting staves ThresholdScans (OB, ML)
Original file by @jiddon
"""

from matplotlib.colors import ListedColormap
import matplotlib.pyplot as plt
import numpy as np

import argparse
import gzip
import os
import re
import sys

# colormap handling (not present in matplotlib)
# DO NOT EDIT WITHOUT ASKING @jiddon for confirmation first
import viridis_cmap
viridis = ListedColormap(viridis_cmap._viridis_data, name='viridis')
plt.register_cmap(name='viridis', cmap=viridis)
plt.set_cmap(viridis)
palette = plt.get_cmap(name="viridis")
palette.set_bad(alpha = 0.0)
palette.set_over("k")
palette.set_under("k")

# Constants
ALPIDE_COLS = 1024
ALPIDE_ROWS = 512
QUAD_STAVES = 4
CHIP_PER_LANE = 7
PLOT_DIRECTORY = 'plots'
MAX_LANES = 28

ML_MODULES = 4
OL_MODULES = 7

DPI=500
STAVE_SIZE_MODIFIER=2

link2module_lut = {6:0, 7:0, 20:0, 21:0,
                   5:1, 8:1, 19:1, 22:1,
                   4:2, 9:2, 18:2, 23:2,
                   3:3, 10:3, 17:3, 24:3,
                   2:4, 11:4, 16:4, 25:4,
                   1:5, 12:5, 15:5, 26:5,
                   0:6, 13:6, 14:6, 27:6}

feeid_to_stave_lut = {"pp1o5":{"16384":0, "16385":1, "16386":2, "16387":3, "16388":4, "16389":5, "16390":6, "16391":7},
                      "pp1i7":{"24600":0, "24601":1, "24602":2, "24603":3, "24604":4, "24605":5, "24606":6, "24607":7, "24608":8, "24609":9, "24610":10, "24611":11}}

class StavePlotter:
    """Class used for plotting the output of decoder.c (by @mmager)"""

    def __init__(self,
                 filename_list,
                 middle_layer,
                 plot_extension,
                 subrack,
                 max_charge):
        if middle_layer:
            self.modules = ML_MODULES
            self.lane_list = (3,4,5,6,7,8,9,10,17,18,19,20,21,22,23,24)
        else:
            self.modules = OL_MODULES
            self.lane_list = range(QUAD_STAVES*self.modules)
        self.lanes = len(self.lane_list)
        self._plot_extension = plot_extension
        self.basename = ""
        self.skipped_rows = 0
        self.max_charge = max_charge
        self.is_fhrate = False

        if not os.path.exists(PLOT_DIRECTORY):
            os.makedirs(PLOT_DIRECTORY)

        self.subrack_lut = feeid_to_stave_lut[subrack]
        self.number_of_staves = len(self.subrack_lut)
        self.get_data(filename_list)

    def get_data(self, filename_list):
        """Parses the file and retrieves the data"""
        self.data = {i:np.zeros((ALPIDE_ROWS*MAX_LANES,ALPIDE_COLS*CHIP_PER_LANE)) for i in self.subrack_lut.keys()}
        for filename in filename_list:
            assert os.path.isfile(filename), f"{filename} not existing"
            assert filename.split('/')[-1].startswith('hitmap')
            self.filename = filename
            match = re.match( r'hitmap(\d*).*', self.filename.split('/')[-1])
            if match:
                feeid = match.group(1)
            if self.filename.endswith('.gz'):
                single_file_data=np.fromstring(gzip.open(self.filename,'r').read(),dtype=np.int32).reshape((ALPIDE_ROWS*MAX_LANES,ALPIDE_COLS*CHIP_PER_LANE))
            else:
                single_file_data=np.fromfile(self.filename,dtype=np.int32).reshape((ALPIDE_ROWS*MAX_LANES,ALPIDE_COLS*CHIP_PER_LANE))
            print(f"Total hits {np.sum(single_file_data>0)}")
            for key in self.subrack_lut.keys():
                if feeid == key:
                    self.data[feeid] = single_file_data
                    print(f"{feeid} found in subrack_lut")
            # file_data is an array with each element representing a pixel.
            # Array is arranged such that each master and 6 slaves are stacked on top of one another.
            # data is an array of file_data such that file_data is stacked on top of each other

    def remap_to_stave(self, verbose=False):
        """Remaps a stave view to stave view

        stave is an array shaped like pixel arrangement of a full stave as viewed from above

                                           <= end ML      <= end OL
        SAMTEC HS0 A |  6 |  5 |  4 |  3 ||  2 |  1 |  0 |
        SAMTEC HS0 B |  7 |  8 |  9 | 10 || 11 | 12 | 13 |
        SAMTEC HS1 A | 20 | 19 | 18 | 17 || 16 | 15 | 14 |
        SAMTEC HS1 B | 21 | 22 | 23 | 24 || 25 | 26 | 27 |
        """
        stave={i:np.zeros((ALPIDE_ROWS*QUAD_STAVES,ALPIDE_COLS*CHIP_PER_LANE*self.modules)) for i in self.subrack_lut.keys()}
        stuck_pixels = {i:0 for i in self.subrack_lut.keys()}
        low_threshold_pixels = {i:0 for i in self.subrack_lut.keys()}
        total_pixels = {i:0 for i in self.subrack_lut.keys()}
        pixels_1_hit = {i:0 for i in self.subrack_lut.keys()}
        pixels_2_hit = {i:0 for i in self.subrack_lut.keys()}
        pixels_3_hit = {i:0 for i in self.subrack_lut.keys()}
        pixels_4_hit = {i:0 for i in self.subrack_lut.keys()}
        pixels_5_hit = {i:0 for i in self.subrack_lut.keys()}
        pixels_above_5_hit = {i:0 for i in self.subrack_lut.keys()}
        pixels_above_10_hit = {i:0 for i in self.subrack_lut.keys()}
        pixels_above_100_hit = {i:0 for i in self.subrack_lut.keys()}

        for feeid in self.subrack_lut.keys():
            stave_number = self.subrack_lut[feeid]
            print(f"remapping {feeid}...")
            for link in self.lane_list:
                for chipid in range(CHIP_PER_LANE):
                    chip=self.data[feeid][link*ALPIDE_ROWS:(link+1)*ALPIDE_ROWS,chipid*ALPIDE_COLS:(chipid+1)*ALPIDE_COLS]
                    if self.skipped_rows:
                        # used when there are skipped rows (i.e. thscan)
                        for row in range(ALPIDE_ROWS):
                            # if row was scanned, copy results for the following rows until the next scanned row.
                            if row%self.skipped_rows!=0:
                                chip[row,:]=chip[row-1,:]

                            else:
                                for column in range(ALPIDE_COLS):
                                    total_pixels[feeid] +=1
                                    if not self.is_fhrate:
                                        if chip[row,column] == self.max_charge:
                                            stuck_pixels[feeid] +=1
                                        elif chip[row,column] < 5:
                                            low_threshold_pixels[feeid] += 1
                    elif self.is_fhrate:
                        non_zero_event_position = np.nonzero(chip)
                        non_zero_elements = chip[non_zero_event_position]
                        for i in non_zero_elements:
                            if i == 1:
                                pixels_1_hit[feeid] +=1
                            if i == 2:
                                pixels_2_hit[feeid] += 1
                            if i == 3:
                                pixels_3_hit[feeid] += 1
                            if i == 4:
                                pixels_4_hit[feeid] += 1
                            if i == 5:
                                pixels_5_hit[feeid] += 1
                            if i > 5:
                                pixels_above_5_hit[feeid] += 1
                            if i > 10:
                                pixels_above_10_hit[feeid] += 1
                            if i > 100:
                                pixels_above_100_hit[feeid] += 1


                    hs=link//(MAX_LANES//2) # half stave number: 0 for lower, 1 for upper
                    ro=link//CHIP_PER_LANE%2 # data connector, a side = 0, b side = 1
                    mo=link2module_lut[link]
                    po=chipid                # chip number, 0-6
                    if ro==0: # revert order of chips for b side ([14|13|12|11|10|9 |8 ]
                        #                                             [0 |1 |2 |3 |4 |5 |6 ])
                        po=CHIP_PER_LANE-1-po
                        chip=chip[::-1,::-1]
                    if verbose:
                        print(f"hs {hs}, ro {ro}, mosule {mo}, position {po}, stave {len(stave)}x{len(stave[0])} chip {len(chip)}x{len(chip[0])}")
                        print(f"{(hs*2+ro)*ALPIDE_ROWS}:{(hs*2+ro+1)*ALPIDE_ROWS},{(mo*CHIP_PER_LANE+po)*ALPIDE_COLS}:{(mo*CHIP_PER_LANE+po+1)*ALPIDE_COLS}")
                    stave[feeid][(hs*2+ro)*ALPIDE_ROWS:(hs*2+ro+1)*ALPIDE_ROWS,(mo*CHIP_PER_LANE+po)*ALPIDE_COLS:(mo*CHIP_PER_LANE+po+1)*ALPIDE_COLS]=chip
                    #[lower hs, a side]
                    #[lower hs, b side]
                    #[upper hs, a side]
                    #[upper hs, b side]
            print(f"remapped {feeid}")
        if not self.is_fhrate:
            print(f"stuck pixels: {stuck_pixels}")
            print(f"low_threshold_pixels: {low_threshold_pixels}")
            total_low = 0
            for feeid in self.subrack_lut.keys():
                total_low += low_threshold_pixels[feeid]
            print(f"total pixels with threshold below 5: {total_low}")

        elif self.is_fhrate:
            print(f"pixels with 1 hits: {pixels_1_hit}")
            print(f"pixels with 2 hits: {pixels_2_hit}")
            print(f"pixels with 3 hits: {pixels_3_hit}")
            print(f"pixels with 4 hits: {pixels_4_hit}")
            print(f"pixels with 5 hits: {pixels_5_hit}")
            print(f"pixels with more than 5 hits: {pixels_above_5_hit}")
            print(f"pixels with more than 10 hits: {pixels_above_10_hit}")
            print(f"pixels with more than 100 hits: {pixels_above_100_hit}")
        print(f"total pixels scanned: {total_pixels}")
        return stave

    def plot_datamap(self, show):
        """Unclear what it does (ask @jiddon).
        Left but not printed"""
        raise NotImplementedError

    def plot_stave(self, show):
        """Plots the full stave"""
        raise NotImplementedError


class THScanStavePlotter(StavePlotter):
    """Class used for plotting the output of decoder.c (by @mmager)"""

    def __init__(self, filename_list, middle_layer, injections, max_charge, plot_extension, skipped_rows, subrack):
        super(THScanStavePlotter, self).__init__(filename_list=filename_list,
                                                 middle_layer=middle_layer,
                                                 plot_extension=plot_extension,
                                                 subrack=subrack,
                                                 max_charge=max_charge)
        self.injections = injections
        self.skipped_rows = skipped_rows
        self.basename = "ths_"
        self._is_thscan = True
        self.calculate_threshold()
        self.subrack = subrack

    def calculate_threshold(self):
        """
        data=self.max_charge-data/self.injections
        # e.g. charge of 0 to 50 (self.max_charge), 1 injection, threshold of 20.
        # first 20 injections have 0 hits.
        # next 30 have hits.
        # so data = 30, and then threshold = endcharge - data/ninj = 20
        """
        for feeid in self.subrack_lut:
            self.data[feeid]=self.max_charge-self.data[feeid]/self.injections

    def plot_datamap(self, show):
        """Unclear what it does (ask @jiddon).
        Left but not printed"""
        plt.imshow(self.data)
        plt.clim(0, self.max_charge+1)
        plt.colorbar()
        if show:
            plt.show()
        else:
            filename = f"{PLOT_DIRECTORY}/{self.basename}datamap{self.subrack}.{self._plot_extension}"
            print(f"Image stored in {filename}")
            plt.savefig(filename, bbox_inches='tight')

    def plot_stave(self, show):
        """Plots the full stave"""
        stave=self.remap_to_stave()
        plt.subplots(self.number_of_staves, sharex=True, gridspec_kw={'hspace': 0})
        for feeid in self.subrack_lut:
            print(f"plotting feeid {feeid}")
            stave[feeid][stave[feeid]<1]=0
            fig = plt.subplot(self.number_of_staves, 1, self.subrack_lut[feeid]+1)
            fig = plt.imshow(stave[feeid],interpolation='bilinear')
            fig.axes.get_xaxis().set_visible(False)
            fig.axes.get_yaxis().set_visible(False)
        fig.axes.get_xaxis().set_visible(True)
        plt.xlabel('Pixel')
        if show:
           plt.show()
        else:
            filename = f"{PLOT_DIRECTORY}/{self.basename}stave{self.subrack}.{self._plot_extension}"
            print(f"Image stored in {filename}")
            plt.savefig(filename, bbox_inches='tight', dpi=DPI)

class FHRateStavePlotter(StavePlotter):
    """Class used for plotting the output of decoder.c (by @mmager)"""

    def __init__(self, filename_list, middle_layer, plot_extension, subrack, max_charge=0):
        super(FHRateStavePlotter, self).__init__(filename_list=filename_list,
                                                 middle_layer=middle_layer,
                                                 plot_extension=plot_extension,
                                                 subrack=subrack,
                                                 max_charge=max_charge)
        self.basename = "fhr_"
        self.is_fhrate = True
        self.magic = 100
        self.subrack = subrack
        self.skipped_rows = 0
        self.max_charge = max_charge #presumably not being used for FHR but I'm sure there's a good reason why "max charge" is in the init of the parent class......... - Ryan

    def plot_stave(self, show, force_binary):
        """Plots the full stave"""
        stave=self.remap_to_stave()
        plt.subplots(self.number_of_staves, sharex=True, gridspec_kw={'hspace': 0})
        for feeid in self.subrack_lut:
            stave[feeid][stave[feeid]<0]=0
            fig = plt.subplot(self.number_of_staves, 1, self.subrack_lut[feeid]+1)
            non_zero_event_positions = np.nonzero(stave[feeid])
            non_zero_events = stave[feeid][non_zero_event_positions]
            print(len(non_zero_events))
            for i in range(len(non_zero_events)):
                if non_zero_events[i] == 1:
                    plt.scatter(non_zero_event_positions[1][i],non_zero_event_positions[0][i], alpha=1, s=0.05,c='blue', marker='o')
                elif non_zero_events[i] == 2:
                    plt.scatter(non_zero_event_positions[1][i],non_zero_event_positions[0][i], alpha=1, s=0.05,c='red', marker='o')
                elif non_zero_events[i] == 3:
                    plt.scatter(non_zero_event_positions[1][i],non_zero_event_positions[0][i], alpha=1, s=0.05,c='green', marker='o')
                elif non_zero_events[i] == 4:
                    plt.scatter(non_zero_event_positions[1][i],non_zero_event_positions[0][i], alpha=1, s=0.05,c='yellow', marker='o')
                elif non_zero_events[i] > 4:
                    plt.scatter(non_zero_event_positions[1][i],non_zero_event_positions[0][i], alpha=1, s=0.05,c='black', marker='o')
            fig.axes.get_xaxis().set_visible(False)
            fig.axes.get_yaxis().set_visible(False)
            y_ticks = np.arange(0,4,1)
            x_ticks = np.arange(0,49,1)
            plt.grid(which='both')
            fig.grid(which='major', alpha = 0.5)
        if show:
            plt.show()
        else:
            filename = f"{PLOT_DIRECTORY}/{self.basename}stave{self.subrack}.{self._plot_extension}"
            print(f"Image stored in {filename}")
            plt.savefig(filename, bbox_inches='tight', dpi=DPI)
        plt.close()

        plt.hist(non_zero_event_positions[1], density=True, facecolor='g')
        filename = f"{PLOT_DIRECTORY}/{self.basename}row_hist{self.subrack}.{self._plot_extension}"
        print(f"Image stored in {filename}")
        plt.savefig(filename, bbox_inches='tight', dpi=DPI)
