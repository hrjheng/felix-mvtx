#!/usr/bin/env python3.9
"""
File for plotting staves ThresholdScans (OB, ML)
Original file by @jiddon
"""

import matplotlib as mpl
mpl.use('Agg')
from matplotlib.colors import ListedColormap
import matplotlib.pyplot as plt
import numpy as np

from scipy import stats

import argparse
import gzip
import os
import re
import sys
import yaml
import math

script_path = os.path.dirname(os.path.realpath(__file__))

# colormap handling (not present in matplotlib)
# DO NOT EDIT WITHOUT ASKING @jiddon for confirmation first
import viridis_cmap

viridis = ListedColormap(viridis_cmap._viridis_data, name='viridis')
plt.register_cmap(name='viridis', cmap=viridis)
plt.set_cmap(viridis)
palette = plt.get_cmap(name="viridis")
palette.set_bad(alpha = 1.0) # bad values: no color
palette.set_over("k") # overflow color: black

# Constants
ALPIDE_COLS = 1024
ALPIDE_ROWS = 512
QUAD_STAVES = 4
CHIP_PER_LANE = 7
MAX_LANES = 28

ML_MODULES = 4
OL_MODULES = 7

STAVE_SIZE_MODIFIER=2

CUT_HIT_PIXELS_PER_DCOL = 50
NOISE_CUT = 1e-6
N_EVENTS_FHR = 3360000 # TODO: replace this by a parameter. 300s data taking for FHR at 11.2kHz

# careful: this is the module index, not the ID: moduleID := moduleIndex + 1
link2module_lut = {6:0,  7:0, 20:0, 21:0,
                   5:1,  8:1, 19:1, 22:1,
                   4:2,  9:2, 18:2, 23:2,
                   3:3, 10:3, 17:3, 24:3,
                   2:4, 11:4, 16:4, 25:4,
                   1:5, 12:5, 15:5, 26:5,
                   0:6, 13:6, 14:6, 27:6}

# careful: this is the module index, not the ID: moduleID := moduleIndex + 1
link2master_chip_id_lut = {6:24,   7:16,  20:152, 21:144,
                           5:40,   8:32,  19:168, 22:160,
                           4:56,   9:48,  18:184, 23:176,
                           3:72,  10:64,  17:200, 24:192,
                           2:88,  11:80,  16:216, 25:208,
                           1:104, 12:96,  15:232, 26:224,
                           0:120, 13:112, 14:248, 27:240}

class StavePlotter:
    """Class used for plotting the output of decoder.c (by @mmager)"""
    def __init__(self,
                 filename,
                 filename2,
                 middle_layer,
                 plot_extension,
                 stave_name):
        if middle_layer:
            self.modules = ML_MODULES
            self.lane_list = (3,4,5,6,7,8,9,10,17,18,19,20,21,22,23,24)
        else:
            self.modules = OL_MODULES
            self.lane_list = range(QUAD_STAVES*self.modules)
        self.lanes = len(self.lane_list)
        self._plot_extension = plot_extension
        self.basename = ""
        self.data = None
        self.skipped_rows = 0
        self.stave_name = stave_name
        self.excluded_chips = self.get_excluded_chips()
        self.hit_counts = []

        self.is_fhrate = False
        self.get_data(filename=filename, append=False)
        if filename2 != "":
            self.get_data(filename=filename2, append=True)
        assert np.count_nonzero(self.data<0) == 0

        print(f"Entries below 0: {np.count_nonzero(self.data<0)}")
        print(f"Non-zero entries 0: {np.count_nonzero(self.data)}")
        print(f"Maximum: {np.max(self.data)}")
        print(f"Minimum: {np.min(self.data)}")
        print(f"Sum: {np.sum(self.data)}")

    def get_data(self, filename, append=False):
        """Parses the file and retrieves the data"""
        filename = os.path.realpath(filename)
        print(filename)
        assert os.path.isfile(filename), f"{filename} not existing"
        self.filename = filename
        match = re.match( r'hitmap(\d*).*', os.path.split(self.filename)[1])
        if match:
            feeid = match.group(1)
            self.feeid = f"_{feeid}"
        else:
            self.feeid = ""

        if self.filename.endswith('.gz'):
            d=np.fromstring(gzip.open(self.filename,'r').read(),dtype=np.int32).reshape((ALPIDE_ROWS*MAX_LANES/2,ALPIDE_COLS*CHIP_PER_LANE))
        else:
            d=np.fromfile(self.filename,dtype=np.int32).reshape((ALPIDE_ROWS*MAX_LANES,ALPIDE_COLS*CHIP_PER_LANE))


        print(f"Hit Pixels input file: {np.count_nonzero(d)}")
        print(f"Hits input file: {np.sum(d)}")# / {self.hit_counts[-1]}")

        if self.data is not None or append:
            self.data = np.add(self.data, d)
        else:
            self.data = d
        self.hit_counts.append(np.sum(d))
        print(f"Total hits: {np.sum(self.data)}")
        print(f"Total hit pixels: {np.count_nonzero(self.data)}")
        print(f"Hits between 0 and 1: {np.count_nonzero(self.data<1)-np.count_nonzero(self.data==0)}")
        # data is an array with each element representing a pixel.
        # Array is arranged such that each master and 6 slaves are stacked on top of one another.

    def get_excluded_chips(self):
        """Return excluded chips list when given stave name in format L#_##, e.g. L5_42"""
        try:
            ob_staves_yml_path = os.path.join(script_path, "../config/ob_staves.yml")
            with open(ob_staves_yml_path, 'r') as f:
                config = yaml.load(f, Loader=yaml.FullLoader)
                try:
                    excluded_chips = config['layer'][int(self.stave_name[1])]['stave'][int(self.stave_name[3:])]['excluded-chips']
                except:
                    excluded_chips = []
            return excluded_chips
        except:
            raise ValueError

    def remap_to_stave(self, verbose=False):
        """Remaps a stave view to stave view

        stave is an array shaped like pixel arrangement of a full stave as viewed from above

                                           <= end ML      <= end OL
        SAMTEC HS0 A |  6 |  5 |  4 |  3 ||  2 |  1 |  0 |
        SAMTEC HS0 B |  7 |  8 |  9 | 10 || 11 | 12 | 13 |
        SAMTEC HS1 A | 20 | 19 | 18 | 17 || 16 | 15 | 14 |
        SAMTEC HS1 B | 21 | 22 | 23 | 24 || 25 | 26 | 27 |
        """
        stave=np.zeros((ALPIDE_ROWS*QUAD_STAVES,ALPIDE_COLS*CHIP_PER_LANE*self.modules))
        for link in self.lane_list:
            for chipid in range(CHIP_PER_LANE):
                chip=self.data[link*ALPIDE_ROWS:(link+1)*ALPIDE_ROWS,chipid*ALPIDE_COLS:(chipid+1)*ALPIDE_COLS]
                if self.skipped_rows:
                    # used when there are skipped rows (i.e. thscan)
                    for row in range(ALPIDE_ROWS):
                        # if row was scanned, copy results for the following rows until the next scanned row.
                        if row%self.skipped_rows!=0:
                            chip[row,:]=chip[row-1,:]
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
                stave[(hs*2+ro)*ALPIDE_ROWS:(hs*2+ro+1)*ALPIDE_ROWS,(mo*CHIP_PER_LANE+po)*ALPIDE_COLS:(mo*CHIP_PER_LANE+po+1)*ALPIDE_COLS]=chip
                #[lower hs, a side]
                #[lower hs, b side]
                #[upper hs, a side]
                #[upper hs, b side]
        return stave

    def remap_to_stack(self, verbose=False):
        """Remaps a stack view to copy every skipped row
        """
        stack=np.zeros((ALPIDE_ROWS*QUAD_STAVES*OL_MODULES,ALPIDE_COLS*CHIP_PER_LANE))
        stave_thr = []
        for link in self.lane_list:
            chipids = [i for i in range(link2master_chip_id_lut[link], link2master_chip_id_lut[link]+7)]
            for chipid in range(CHIP_PER_LANE):
                chip=self.data[link*ALPIDE_ROWS:(link+1)*ALPIDE_ROWS,chipid*ALPIDE_COLS:(chipid+1)*ALPIDE_COLS]
                if self.skipped_rows:
                    for row in range(ALPIDE_ROWS):
                        # if row was scanned, copy results for the following rows until the next scanned row.
                        if row%self.skipped_rows!=0:
                            chip[row,:]=chip[row-1,:]
                if not self.is_fhrate:
                    if chipids[chipid] not in self.excluded_chips:
                        thr_chip=np.mean(chip)
                        std_chip=np.std(chip)
                        stave_thr.append(thr_chip)
                        print(f"chipid {chipids[chipid]}, threshold {thr_chip}, std {std_chip} ")

                if verbose:
                    print(f"link {link}, chipid {chipid}, stave {len(stack)}x{len(stack[0])} chip {len(chip)}x{len(chip[0])}")
                    print(f"{link*ALPIDE_ROWS}:{(link+1)*ALPIDE_ROWS},{chipid*ALPIDE_COLS}:{(chipid+1)*ALPIDE_COLS}")
                stack[link*ALPIDE_ROWS:(link+1)*ALPIDE_ROWS,chipid*ALPIDE_COLS:(chipid+1)*ALPIDE_COLS]=chip

        if not self.is_fhrate:
            stave_thr.sort()
            avg_stave = np.mean(stave_thr)
            std_stave = np.std(stave_thr)
            print(f"average threshold over stave: {avg_stave}, standard deviation: {std_stave}")

        return stack

    def plot_datamap(self):
        """Unclear what it does (ask @jiddon).
        Left but not printed"""
        raise NotImplementedError

    def plot_stack(self):
        """Plots the stave seen as a stack"""
        raise NotImplementedError

    def plot_stave(self):
        """Plots the full stave"""
        raise NotImplementedError


class THScanStavePlotter(StavePlotter):
    """Class used for plotting the output of decoder.c (by @mmager)"""

    def __init__(self, filename, filename2, middle_layer, injections, max_charge, plot_extension, skipped_rows, plot_name, stave_name):
        super(THScanStavePlotter, self).__init__(filename=filename,
                                                 filename2=filename2,
                                                 middle_layer=middle_layer,
                                                 plot_extension=plot_extension,
                                                 stave_name=stave_name)
        self.injections = injections
        self.max_charge = max_charge
        self.skipped_rows = skipped_rows
        self.basename = plot_name
        self._is_thscan = True
        self.calculate_threshold()


    def calculate_threshold(self):
        """
        data=self.max_charge-data/self.injections
        # e.g. charge of 0 to 50 (self.max_charge), 1 injection, threshold of 20.
        # first 20 injections have 0 hits.
        # next 30 have hits.
        # so data = 30, and then threshold = endcharge - data/ninj = 20
        # multiply by 10 to convert from DAC to electrons
        """
        self.data=(self.max_charge-self.data/self.injections)*10

    def plot_datamap(self):
        """Unclear what it does (ask @jiddon).
        Left but not printed"""
        plt.imshow(self.data)
        plt.clim(0, self.max_charge+1)
        cbar = plt.colorbar()
        cbar.set_label("Threshold (electrons)")
        filename = f"{self.basename}datamap{self.feeid}.{self._plot_extension}"
        print(f"Image stored in {filename}")
        plt.savefig(filename, bbox_inches='tight')
        plt.close()

    def plot_stave(self):
        """Plots the full stave"""
        plt.figure(figsize=(self.modules*(ALPIDE_COLS//ALPIDE_ROWS)*STAVE_SIZE_MODIFIER,QUAD_STAVES*STAVE_SIZE_MODIFIER))
        stave=self.remap_to_stave()

        plt.imshow(stave,interpolation='bilinear')
        plt.clim(0, 10*(self.max_charge+1))
        plt.xticks(list(range(0,ALPIDE_COLS*CHIP_PER_LANE*self.modules,ALPIDE_COLS*CHIP_PER_LANE))+[ALPIDE_COLS*self.modules*CHIP_PER_LANE-1])
        plt.xlabel('Pixel')
        plt.yticks(list(range(0,ALPIDE_ROWS*QUAD_STAVES +1,ALPIDE_ROWS)))
        plt.ylabel('Pixel')
        cbar = plt.colorbar()
        cbar.set_label("Threshold (electrons)")
        filename = f"{self.basename}stave{self.feeid}.{self._plot_extension}"
        print(f"Image stored in {filename}")
        plt.savefig(filename, bbox_inches='tight', dpi=1200)
        plt.close()

    def plot_stack(self):
        """Plots the stave seen as a stack"""
        plt.figure()
        stack=self.remap_to_stack()
        plt.imshow(stack,interpolation='bilinear')
        plt.clim(0, 10*(self.max_charge+1))
        plt.xticks(list(range(0,ALPIDE_COLS*CHIP_PER_LANE,ALPIDE_COLS))+[ALPIDE_COLS*CHIP_PER_LANE-1], rotation=-45)
        plt.xlabel('Pixel')
        plt.yticks(list(range(0,ALPIDE_ROWS*MAX_LANES,ALPIDE_ROWS))+[ALPIDE_ROWS*MAX_LANES-1], list(range(0,MAX_LANES+1)))
        plt.ylabel('Lane')
        cbar = plt.colorbar()
        cbar.set_label("Threshold (electrons)")
        filename = f"{self.basename}stack{self.feeid}.{self._plot_extension}"
        print(f"Image stored in {filename}")
        plt.savefig(filename, bbox_inches='tight', dpi=1200)
        plt.close()


class THTuneStavePlotter(StavePlotter):
    """Class used for plotting the output of decoder.c from a tuning scan (by @mmager)"""

    def __init__(self, filename, filename2, plot_name, yaml_filename, middle_layer, injections, ithr_not_vcasn):
        super(THTuneStavePlotter, self).__init__(filename=filename,
                                                 filename2=filename2,
                                                 middle_layer=middle_layer,
                                                 stave_name=yaml_filename,
                                                 plot_extension=None)
        self.injections = injections
        self.value_list = range(30, 70, 1) if not ithr_not_vcasn else range(20, 130, 1)
        self._is_thscan = True
        self.rows = [1,2,254,255,509,510]
        self.basename = plot_name
        self.yaml_filename = yaml_filename
        self.ithr_not_vcasn = ithr_not_vcasn
        if self.ithr_not_vcasn:
            print("#### ITHR ####")
        else:
            print("#### VCASN ####")
        self.calculate_register()
        self.calculate_optimum()

    def calculate_register(self):
        if self.ithr_not_vcasn:
            self.data=self.value_list[0]+(self.data/self.injections) - 2 # 2 is magic to give final tune of 100 e
        else:
            self.data=self.value_list[-1]-self.data/self.injections

    def calculate_optimum(self):
        value = {link: {chipid:0 for chipid in range(CHIP_PER_LANE)} for link in self.lane_list}
        print_value=[]
        for link in self.lane_list:
            chipids = [i for i in range(link2master_chip_id_lut[link], link2master_chip_id_lut[link]+7)]
            for chipid in range(CHIP_PER_LANE):
                if chipids[chipid] not in self.excluded_chips:
                    chip=self.data[link*ALPIDE_ROWS:(link+1)*ALPIDE_ROWS,chipid*ALPIDE_COLS:(chipid+1)*ALPIDE_COLS]

                    scanned_rows = np.zeros(shape=(len(self.rows),ALPIDE_COLS))
                    for r,row in enumerate(self.rows):
                         scanned_rows[r][:]=chip[row][:]

                    value[link][chipid]=int(np.mean(scanned_rows))
                    print_value.append([chipids[chipid], value[link][chipid]])

        print_value.sort()
        value_dict = {}
        for i in range(len(print_value)):
            value_dict[print_value[i][0]] = int(print_value[i][1])

        if self.ithr_not_vcasn:
            folder_path = os.path.join(script_path, "../config/ithr/")
        else:
            folder_path = os.path.join(script_path, "../config/vcasn/")

        filename = os.path.join(folder_path, f"{self.yaml_filename}.yml")
        with open(filename, 'w') as f:
            yaml.dump(value_dict, f)
        with open(f"{self.basename}_values.yml", 'w') as f:
            yaml.dump(value_dict, f)

        print(f"tuning values saved in {filename}")


class FHRateStavePlotter(StavePlotter):
    """Class used for plotting the output of decoder.c (by @mmager)"""

    def __init__(self, filename, filename2, middle_layer, plot_extension, plot_name, yaml_filename, rewrite_masks):
        super(FHRateStavePlotter, self).__init__(filename=filename,
                                                 filename2=filename2,
                                                 middle_layer=middle_layer,
                                                 plot_extension=plot_extension,
                                                 stave_name=yaml_filename)
        self.basename = plot_name
        self.is_fhrate = True
        self.n_events= N_EVENTS_FHR
        self.noise_threshold = NOISE_CUT
        self.magic = 1
        self.yaml_filename = yaml_filename
        self.rewrite_masks=rewrite_masks

    def plot_stave(self, force_binary):
        """Plots the full stave"""
        plt.figure(figsize=(self.modules*(ALPIDE_COLS//ALPIDE_ROWS)*STAVE_SIZE_MODIFIER,QUAD_STAVES*STAVE_SIZE_MODIFIER))
        stave = self.remap_to_stave()
        assert np.count_nonzero(stave<0) == 0
        stave = stave/float(self.n_events)
        stave = self.interpolate(stave,scale=20)

        plt.imshow(stave, cmap='Greys')#plt.cm.gray)#"binary")
        #plt.clim(0,self.magic)
        plt.xticks(list(range(0,ALPIDE_COLS*CHIP_PER_LANE*self.modules,ALPIDE_COLS*CHIP_PER_LANE))+[ALPIDE_COLS*self.modules*CHIP_PER_LANE-1])
        plt.xlabel('Pixel')
        plt.yticks(list(range(0,ALPIDE_ROWS*QUAD_STAVES +1,ALPIDE_ROWS)))
        plt.ylabel('Pixel')
        cbar = plt.colorbar()
        cbar.set_label("Fake-Hit Rate / Pixel / Event")
        filename = f"{self.basename}stave{self.feeid}.{self._plot_extension}"
        print(f"Image stored in {filename}")
        plt.savefig(filename, bbox_inches='tight', dpi=1200)
        plt.close()

    def plot_stack(self, force_binary):
        """Plots the stave seen as a stack"""
        plt.figure()
        stave=self.remap_to_stack()
        assert np.count_nonzero(stave<0) == 0
        print(np.count_nonzero(stave))
        print(np.max(stave))
        print(np.min(stave))
        print(np.sum(stave))
        print(np.count_nonzero(stave<1./float(self.n_events)))
        print(1./float(self.n_events))

        stave = stave.astype(float) / float(self.n_events)
        stave = self.interpolate(stave, scale=25)
        zeros=np.count_nonzero(stave==0)
        assert zeros == np.count_nonzero(stave<1./float(self.n_events))
        if False:
            print(f"0<x<1: {np.count_nonzero(stave<1)-zeros}")
            print(f"<0: {np.count_nonzero(stave<0)}")
            print(f"!=0: {np.count_nonzero(stave)}")
            print(f"==0: {zeros}")
            print(f"Max: {np.max(stave)}")
            print(f"Min: {np.min(stave)}")
            print(f"Sum: {np.sum(stave)}")
            print(f"Smaller than 1/nev but not 0: {np.count_nonzero(stave<1./float(self.n_events))-zeros}")

        stave[stave==0]=np.nan # make zeros invisable
        #plt.imshow(stave, cmap="tab20c", norm=mpl.colors.LogNorm(vmin=1./float(self.n_events), vmax=1.))
        #plt.imshow(stave, cmap="tab20c", norm=mpl.colors.LogNorm(vmin=1./np.min(stave), vmax=1.))
        #plt.imshow(stave, cmap="tab20c", norm=mpl.colors.LogNorm(vmin=1e-10, vmax=1.))
        plt.imshow(stave, cmap="viridis", norm=mpl.colors.LogNorm(vmin=1./float(self.n_events), vmax=1.))
        plt.xticks(list(range(0,ALPIDE_COLS*CHIP_PER_LANE,ALPIDE_COLS))+[ALPIDE_COLS*CHIP_PER_LANE-1], rotation=-45)
        plt.xlabel('Pixel')
        plt.yticks(list(range(0,ALPIDE_ROWS*MAX_LANES,ALPIDE_ROWS))+[ALPIDE_ROWS*MAX_LANES-1], list(range(0,MAX_LANES+1)))
        plt.ylabel('Lane')
        cbar = plt.colorbar()
        cbar.set_label("Fake-Hit Rate / Pixel / Event")
        filename = f"{self.basename}stack{self.feeid}_log.{self._plot_extension}"
        print(f"Image stored in {filename}")
        plt.savefig(filename, bbox_inches='tight', dpi=1200)

    def analyse_hits(self, yaml_filename, debug=False):
        """Mask double columns with a high number of hits
        """
        dcol_hits       = np.zeros(shape=(28*CHIP_PER_LANE,512))
        dcol_hit_pixels = np.zeros(shape=(28*CHIP_PER_LANE,512))
        hits            = np.zeros(shape=(28,CHIP_PER_LANE))
        bad_dcols   = {}
        bad_pixels  = {}
        bad_dcol_cnt = 0
        bad_pixel_cnt = 0
        empty_chips = []
        noise_list = np.array([[0,0,0,0]])

        assert np.count_nonzero(self.data<0) == 0
        data = self.data.astype(float) / self.n_events
        print(f"Pixels>1: {np.count_nonzero(data>1)}")
        data[data>1] = 1
        #data[data==0] = np.nan
        print(f"Entries below 0: {np.count_nonzero(data<0)}")
        print(f"Non-zero entries 0: {np.count_nonzero(data)}")
        print(f"Maximum: {np.max(data)}")
        print(f"Minimum: {np.min(data)}")
        print(f"Sum: {np.sum(data)}")

        for link in self.lane_list:
            print(f"#### Link : {link} ####")
            chipids = [i for i in range(link2master_chip_id_lut[link], link2master_chip_id_lut[link]+7)]
            for chipid in range(CHIP_PER_LANE):
                print(f"### ChipID: {chipids[chipid]}")
                chip_bad_dcols = []
                chip_bad_pixels = []
                chip=data[link*ALPIDE_ROWS:(link+1)*ALPIDE_ROWS,chipid*ALPIDE_COLS:(chipid+1)*ALPIDE_COLS]

                # noisy pixels
                x, y = np.where(chip>self.noise_threshold)
                for i in range(len(y)):
                    chip_bad_pixels.append([int(y[i]), int(x[i]), float(chip[x[i], y[i]])])
                    bad_pixel_cnt += 1
                    if debug:
                        print(f"BAD PIXEL: chipid {chipids[chipid]}, row {y[i]}, column {x[i]}, hits {chip[x[i],y[i]]}")

                x, y = np.where(chip>0)
                for i in range(len(y)):
                    noise_list=np.vstack([noise_list, [int(y[i]), int(x[i]), float(chip[x[i], y[i]]), 0.]])


                if len(chip_bad_pixels) > 0:
                    bad_pixels.update({chipids[chipid]:chip_bad_pixels})
                    #print(f"BAD PIXELS: {chip_bad_pixels}")
                    print(f"BAD PIXEL COUNT: {len(chip_bad_pixels)}")

                hits[link,chipid]=np.sum(chip)/1024./512.

                if debug or hits[link,chipid]>1e-7:
                    chip_map=self.interpolate(chip, scale=5)
                    #plt.figure()
                    #plt.imshow(chip_map)
                    #plt.xlabel("Columns")
                    #plt.ylabel("Rows")
                    #plt.colorbar()
                    #filename = f"{self.basename}_MAP_{self.feeid}_link{link}_chip{chipid}_chipId{chipids[chipid]}.{self._plot_extension}"
                    #plt.savefig(filename, bbox_inches='tight', dpi=600)
                    #plt.close()

                    plt.figure()
                    plt.imshow(chip_map,cmap="tab20c",norm=mpl.colors.LogNorm(vmin=1./float(self.n_events), vmax=1.))
                    plt.xlabel("Columns")
                    plt.ylabel("Rows")
                    cbar = plt.colorbar()
                    cbar.set_label("Fake-Hit Rate / Pixel / Event")
                    filename = f"{self.basename}_MAP_{self.feeid}_link{link}_chip{chipid}_chipId{chipids[chipid]}_log.{self._plot_extension}"
                    plt.savefig(filename, bbox_inches='tight', dpi=300)
                    plt.close()

                ## Bad double columns
                for dcol in range(512):
                    dcol_hit_pixels[link*CHIP_PER_LANE+chipid,dcol]=np.count_nonzero(chip[:,2*dcol:2*(dcol+1)]>0)
                    dcol_hits[link*CHIP_PER_LANE+chipid,dcol]=np.sum(chip[:,2*dcol:2*(dcol+1)]) / 1024. # normalise to pixel/hit/event
                    dcol_hit_pixels[link*CHIP_PER_LANE+chipid,dcol]=np.count_nonzero(chip[:,2*dcol:2*(dcol+1)])
                    if dcol_hit_pixels[link*CHIP_PER_LANE+chipid,dcol] > CUT_HIT_PIXELS_PER_DCOL:
                        chip_bad_dcols.append(dcol)
                        bad_dcol_cnt +=1
                        print(f"BAD DCOL: chipid {chipids[chipid]}, double column {dcol}, hit pixels {dcol_hit_pixels[link*CHIP_PER_LANE+chipid,dcol]}")

                if len(chip_bad_dcols) > 0:
                    bad_dcols.update({chipids[chipid]:chip_bad_dcols})
                    #print(f"BAD DCOLS: {chip_bad_dcols}")
                    print(f"BAD DCOLS COUNT: {len(chip_bad_dcols)}")


                x=[i for i in range(512)]
                if debug or len(chip_bad_dcols):
                    plt.figure()
                    y=(dcol_hit_pixels[link*CHIP_PER_LANE+chipid:link*CHIP_PER_LANE+chipid+1,:])[0]
                    plt.plot(x, y )
                    plt.xlabel("Double Column")
                    plt.ylabel("Hit Pixels")
                    filename = f"{self.basename}_DCOL_HIT_PIXELS_{self.feeid}_link{link}_chip{chipid}_chipId{chipids[chipid]}.{self._plot_extension}"
                    plt.savefig(filename, bbox_inches='tight', dpi=300)
                    plt.yscale("symlog", linthresh=1)
                    filename = f"{self.basename}_DCOL_HIT_PIXELS_{self.feeid}_link{link}_chip{chipid}_chipId{chipids[chipid]}_log.{self._plot_extension}"
                    plt.savefig(filename, bbox_inches='tight', dpi=300)
                    plt.close()

                if debug or hits[link,chipid]>1e-7:
                    plt.figure()
                    y=(dcol_hits[link*CHIP_PER_LANE+chipid:link*CHIP_PER_LANE+chipid+1,:])[0]
                    plt.plot(x, y)
                    plt.xlabel("Double Column")
                    plt.ylabel("Hits")
                    filename = f"{self.basename}_DCOL_HITS_{self.feeid}_link{link}_chip{chipid}_chipId{chipids[chipid]}.{self._plot_extension}"
                    plt.savefig(filename, bbox_inches='tight', dpi=300)
                    plt.yscale("symlog", linthresh=1)
                    filename = f"{self.basename}_DCOL_HITS_{self.feeid}_link{link}_chip{chipid}_chipId{chipids[chipid]}_log.{self._plot_extension}"
                    plt.savefig(filename, bbox_inches='tight', dpi=300)
                    plt.close()

        ## Detect empty chips
        for link in self.lane_list:
            chipids = [i for i in range(link2master_chip_id_lut[link], link2master_chip_id_lut[link]+7)]
            for chipid in range(CHIP_PER_LANE):
                if hits[link,chipid]==0:
                    empty_chips.append(chipids[chipid])
                    if debug:
                        print(f"chipid {chipids[chipid]} (lane {link}, chipid {chipid}) found empty")
        print(f"Empty chips: {empty_chips}")

        ## Hits chip by chip
        plt.figure()
        plt.imshow(hits,
                   cmap="tab20c",
                   norm=mpl.colors.LogNorm(vmin=1./float(self.n_events)/512/1024, vmax=1.))
        plt.xlabel("Chip ID (inside lane)")
        plt.ylabel("Lane")
        cbar = plt.colorbar()
        cbar.set_label("Fake-Hit Rate / Pixel / Event")
        filename = f"{self.basename}chip_hits{self.feeid}.{self._plot_extension}"
        plt.savefig(filename, bbox_inches='tight', dpi=300)
        plt.close()

        ## Hits by double column
        """Plots the stave seen as a stack"""
        plt.figure()
        plt.imshow(dcol_hits, norm=mpl.colors.LogNorm(vmin=1./float(self.n_events), vmax=1.))
        plt.xlabel("Double Column")
        plt.ylabel("Lane * 7 + Chip ID (inside lane)")
        cbar = plt.colorbar()
        cbar.set_label("Fake-Hit Rate / Pixel / Event")
        filename = f"{self.basename}chip_dcols{self.feeid}.{self._plot_extension}"
        plt.savefig(filename, bbox_inches='tight', dpi=300)
        plt.close()

        if self.rewrite_masks:
            folder_path = os.path.join(script_path, "../config/mask_double_cols/")
            ## Double column mask
            with open(os.path.join(folder_path, f"{self.yaml_filename}_stave_plotter.yml"), 'w') as f:
                yaml.dump(bad_dcols, f)

            ## Empty chips
            with open(os.path.join(folder_path, f"{self.yaml_filename}_empty_chips.yml"), 'w') as f:
                yaml.dump(empty_chips, f)

            folder_path = os.path.join(script_path, "../config/noise_masks/")
            ## Noisy pixels
            with open(os.path.join(folder_path, f"{self.yaml_filename}.yml"), 'w') as f:
                yaml.dump(bad_pixels, f)

        print("")
        print(f"Masking a total of {bad_pixel_cnt} pixels with a firing frequency larger than 1e-6/event")
        print(f"Masking fraction of {float(bad_pixel_cnt)/self.lanes/7./1024./512.} pixels with a firing frequency larger than 1e-6/event")


        noise_list = np.delete(noise_list, (0), axis=0)
        noise_list = noise_list[(-noise_list[:,2]).argsort()] # sort in decending order
        noise_list[-1][3] = noise_list[-1][2]/1024./512./float(self.lanes)/7.
        for i in range(len(noise_list)-2, -1, -1):
            noise_list[i][3] = noise_list[i+1][3]+noise_list[i][2]/1024./512./float(self.lanes)/7.

        print(f"Resulting FHR of {noise_list[bad_pixel_cnt][3]}")
        print("")
        with open(f"{self.basename}_working_point.txt", 'w') as f:
            f.write(f"{self.calculate_fhr()}\t{bad_pixel_cnt}\t{float(bad_pixel_cnt)/self.lanes/7./1024./512.}\t{noise_list[bad_pixel_cnt][3]}\t{self.yaml_filename}\n")

        np.savetxt(f"{self.basename}_noisehits.txt", noise_list, delimiter=',')

        x=[i for i in range(len(noise_list))]
        plt.figure()
        plt.plot(x, noise_list[:,3])
        plt.xlabel(f"Masked Pixels (out of {512*1024*self.lanes*7:0.2e})")
        plt.ylabel("Fake-Hit Rate / Pixel / Event")
        #plt.xscale("symlog", linthresh=50)
        plt.xscale("log")
        plt.yscale("log")
        plt.grid()
        filename = f"{self.basename}masking{self.feeid}.{self._plot_extension}"
        plt.savefig(filename, bbox_inches='tight', dpi=300)
        plt.close()
        x=[float(i)/self.lanes/7./512./1024. for i in range(len(noise_list))]
        plt.figure()
        plt.plot(x, noise_list[:,3])
        plt.xlabel(f"Fraction of masked pixels")
        plt.ylabel("Fake-Hit Rate / Pixel / Event")
        #plt.xscale("symlog", linthresh=50)
        plt.xscale("log")
        plt.yscale("log")
        plt.grid()
        filename = f"{self.basename}masking_relative{self.feeid}.{self._plot_extension}"
        plt.savefig(filename, bbox_inches='tight', dpi=300)
        plt.close()

        if debug:
            print("===BAD DCOLS")
            print(bad_dcols)
            print("===HITS")
            print(hits)
            print("===DCOL_HITS")
            print(dcol_hits)
            print("===HITS")
            print(hits)

    def calculate_fhr(self):
        """Calculate the Fake-Hit Rate"""
        chip_count = self.lanes * 7
        pixel_count = chip_count * 1024 * 512
        hits = np.sum(self.data)
        fhr = hits/pixel_count/self.n_events
        print(f"Fake-hit rate: {fhr:0.2e}/pixel/event ({chip_count}, {pixel_count}, {hits}, {self.n_events})")
        return fhr

    def interpolate(self,original_chip, scale=20):
        chip = original_chip.copy()
        non_zero_pixels = np.nonzero(chip)

        for i in range(non_zero_pixels[0].size):
            value = chip[non_zero_pixels[0][i]][non_zero_pixels[1][i]]
            chip[non_zero_pixels[0][i]][non_zero_pixels[1][i]] = 0

            if non_zero_pixels[0][i]+scale < chip.shape[0]:
                max_x = non_zero_pixels[0][i]+scale
            else:
                max_x = chip.shape[0]
            if non_zero_pixels[0][i]-scale > 0:
                min_x = non_zero_pixels[0][i]-scale
            else:
                min_x = 0

            if non_zero_pixels[1][i]+scale < chip.shape[1]:
                max_y = non_zero_pixels[1][i]+scale
            else:
                max_y = chip.shape[1]
            if non_zero_pixels[1][i]-scale > 0:
                min_y = non_zero_pixels[1][i]-scale
            else:
                min_y = 0

            for x in range(min_x,max_x):
                for y in range(min_y,max_y):
                    chip[x][y] = max(value, chip[x][y])
        return chip

    def analyse_dcols(self, yaml_filename, middle_layer=False, debug=False):
        """Mask double columns with a high number of hits
        """
        dcol_hits       = np.zeros(shape=(28*CHIP_PER_LANE,512))
        dcol_hit_pixels = np.zeros(shape=(28*CHIP_PER_LANE,512))
        hits            = np.zeros(shape=(28,CHIP_PER_LANE))
        bad_dcols   = {}
        bad_pixels  = {}
        bad_dcol_cnt = 0
        bad_pixel_cnt = 0

        data = self.data - 21
        print(f"Entries below 0 (inefficient / unresponsive / dead): {np.count_nonzero(data<0)}")
        print(f"Non-zero entries 0: {np.count_nonzero(data)}")
        print(f"Maximum: {np.max(data)}")
        print(f"Minimum: {np.min(data)}")
        print(f"Sum: {np.sum(data)}")

        self.n_events = 512*21

        for link in self.lane_list:
            print(f"#### Link : {link} ####")
            chipids = [i for i in range(link2master_chip_id_lut[link], link2master_chip_id_lut[link]+7)]
            for chipid in range(CHIP_PER_LANE):
                chip_bad_dcols = []
                chip_bad_pixels = []
                chip=data[link*ALPIDE_ROWS:(link+1)*ALPIDE_ROWS,chipid*ALPIDE_COLS:(chipid+1)*ALPIDE_COLS]
                chip_masked_dcols=data[link*ALPIDE_ROWS:(link+1)*ALPIDE_ROWS,chipid*ALPIDE_COLS:(chipid+1)*ALPIDE_COLS]

                # Find inefficient pixels (which are not responding to the analogue pulsing)
                x, y = np.where(chip<0)
                for i in range(len(y)):
                    chip_bad_pixels.append([int(y[i]), int(x[i]), float(chip[x[i], y[i]])])
                    bad_pixel_cnt += 1
                    if debug:
                        print(f"NOT RESPONDING PIXEL: chipid {chipids[chipid]}, row {y[i]}, column {x[i]}, hits {chip[x[i],y[i]]}")

                if len(chip_bad_pixels) > 0:
                    bad_pixels.update({chipids[chipid]:chip_bad_pixels})

                hits[link,chipid]=np.sum(chip)

                ## Bad double columns
                for dcol in range(512):
                    dcol_hit_pixels[link*CHIP_PER_LANE+chipid,dcol]=np.count_nonzero(chip[:,2*dcol:2*(dcol+1)])
                    dcol_hits[link*CHIP_PER_LANE+chipid,dcol]=np.sum(chip[:,2*dcol:2*(dcol+1)])

                    if dcol_hit_pixels[link*CHIP_PER_LANE+chipid,dcol] > CUT_HIT_PIXELS_PER_DCOL:
                        chip_bad_dcols.append(dcol)
                        bad_dcol_cnt +=1
                        if debug:
                            print(f"BAD DCOL: chipid {chipids[chipid]}, double column {dcol}, hit pixels {dcol_hit_pixels[link*CHIP_PER_LANE+chipid,dcol]}")
                    chip_masked_dcols[:,2*dcol:2*(dcol+1)]=0
                # known bad double_colums to be added by hand:
                if self.yaml_filename == "L3_19" and chipids[chipid] == 196:
                    chip_bad_dcols.append(61)
                    bad_dcol_cnt +=1
                elif self.yaml_filename == "L6_29" and chipids[chipid] == 101:
                    chip_bad_dcols.append(400)
                    bad_dcol_cnt +=1

                if len(chip_bad_dcols) > 0 and len(chip_bad_dcols) < 256:
                    bad_dcols.update({chipids[chipid]:chip_bad_dcols})

                if len(chip_bad_dcols) == 256:
                    print(f"FULL CHIP MASKED: chipid {chipids[chipid]}")

                ## MAP
                if debug or len(chip_bad_dcols)>10:
                    #chip_map=chip.copy() #self.interpolate(chip, scale=5)
                    plt.figure()
                    plt.imshow(chip,cmap="tab20c")
                    plt.xlabel("Columns")
                    plt.ylabel("Rows")
                    cbar = plt.colorbar()
                    cbar.set_label("Fake-Hit Rate / Pixel / Event")
                    filename = f"{self.basename}_MAP_{self.feeid}_link{link}_chip{chipid}_chipId{chipids[chipid]}.{self._plot_extension}"
                    plt.savefig(filename, bbox_inches='tight', dpi=300)
                    plt.close()
                    #chip_map[chip_map<0]=50000
                    plt.figure()
                    plt.imshow(chip,cmap="tab20c",norm=mpl.colors.LogNorm(vmin=1., vmax=1.e5))
                    plt.xlabel("Columns")
                    plt.ylabel("Rows")
                    cbar = plt.colorbar()
                    cbar.set_label("Fake-Hit Rate / Pixel / Event")
                    filename = f"{self.basename}_MAP_{self.feeid}_link{link}_chip{chipid}_chipId{chipids[chipid]}_log.{self._plot_extension}"
                    plt.savefig(filename, bbox_inches='tight', dpi=300)
                    plt.close()

                ## HIT PIXEL COUNT / DCOL
                x=[i for i in range(512)]
                if debug or len(chip_bad_dcols)>10:
                    plt.figure()
                    y=(dcol_hit_pixels[link*CHIP_PER_LANE+chipid:link*CHIP_PER_LANE+chipid+1,:])[0]
                    plt.plot(x, y)
                    plt.xlabel("Double Column")
                    plt.ylabel("Hit Pixels")
                    plt.ylim(0, 1025)
                    plt.grid()
                    filename = f"{self.basename}_DCOL_HIT_PIXELS_{self.feeid}_link{link}_chip{chipid}_chipId{chipids[chipid]}.{self._plot_extension}"
                    plt.savefig(filename, bbox_inches='tight', dpi=300)
                    plt.close()

                ## HITS / DCOL
                if debug or len(chip_bad_dcols)>10: # or hits[link,chipid]>self.n_events:
                    plt.figure()
                    y=(dcol_hits[link*CHIP_PER_LANE+chipid:link*CHIP_PER_LANE+chipid+1,:])[0]
                    plt.plot(x, y)
                    plt.xlabel("Double Column")
                    plt.ylabel("Hits")
                    plt.grid()
                    filename = f"{self.basename}_DCOL_HITS_{self.feeid}_link{link}_chip{chipid}_chipId{chipids[chipid]}.{self._plot_extension}"
                    plt.savefig(filename, bbox_inches='tight', dpi=300)
                    #plt.yscale("symlog", linthresh=1)
                    #filename = f"{self.basename}_DCOL_HITS_{self.feeid}_link{link}_chip{chipid}_chipId{chipids[chipid]}_log.{self._plot_extension}"
                    #plt.savefig(filename, bbox_inches='tight', dpi=300)
                    plt.close()

                print(f"ChipId: {chipids[chipid]}, bad double columns: {len(chip_bad_dcols)}, not responding pixels: {len(chip_bad_pixels)}")

        ## Hits chip by chip
        plt.figure()
        plt.imshow(hits,
                   cmap="tab20c",
                   norm=mpl.colors.LogNorm(vmin=1., vmax=self.n_events*10))
        plt.xlabel("Chip ID (inside lane)")
        plt.ylabel("Lane")
        cbar = plt.colorbar()
        cbar.set_label("Fake-Hit Rate / Pixel / Event")
        filename = f"{self.basename}chip_hits{self.feeid}.{self._plot_extension}"
        plt.savefig(filename, bbox_inches='tight', dpi=300)
        plt.close()

        ## Hits by double column
        """Plots the stave seen as a stack"""
        plt.figure()
        plt.imshow(dcol_hits, norm=mpl.colors.LogNorm(vmin=1., vmax=self.n_events*10))
        plt.xlabel("Double Column")
        plt.ylabel("Lane * 7 + Chip ID (inside lane)")
        cbar = plt.colorbar()
        cbar.set_label("Fake-Hit Rate / Pixel / Event")
        filename = f"{self.basename}chip_dcols{self.feeid}.{self._plot_extension}"
        plt.savefig(filename, bbox_inches='tight', dpi=300)
        plt.close()

        ## Double column mask
        folder_path = os.path.join(script_path, "../config/mask_double_cols/")
        with open(os.path.join(folder_path, f"{self.yaml_filename}.yml"), 'w') as f:
            yaml.dump(bad_dcols, f)
        with open(f"{self.basename}_bad_dcols.yml", 'w') as f:
            yaml.dump(bad_dcols, f)

        ## Inefficient / unresponsive / dead pixels
        with open(f"{self.basename}_dead_pixels.yml", 'w') as f:
            yaml.dump(bad_pixels, f)
