#!/usr/bin/env python3

import os
import argparse
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.colors import LogNorm
from mpl_toolkits.axes_grid1 import make_axes_locatable


class HitMapReader:
    def __init__(self, filename):
        self.filename = filename
        self.data = None
        self.f = open(self.filename, 'r')

    def main(self,noise_cut=10, ntrg=1e6):

        eventTime = 4.455e-5 # 44.550 us
        fname = os.path.basename(self.filename)
        noiseOccMap = np.zeros((512,1024), dtype=float)
        self.data = np.fromfile(self.f, dtype=np.uint32)
        self.f.close()

        num_of_chips_in_file = len(self.data) // (512*1024)

        print("Number of chips in file: " + str(num_of_chips_in_file))
        data_pixels = np.zeros((num_of_chips_in_file, 512,1024) , dtype=np.uint32)
        # fill hitmap
        for j in range(0,512):
            for k in range(0,1024*num_of_chips_in_file):
                i = k // 1024
                data_pixels[i][j][k - i*1024] = self.data[j*3*1024 + k]

        print('filling histogram')
        total_hits = 0
        for chip in range(0,num_of_chips_in_file):

            n_hits = np.sum(data_pixels[chip,:,:])
            print("hits on chip",chip,":",n_hits)
            if n_hits == 0:
                continue

            totalnoisy = np.count_nonzero(data_pixels[chip, data_pixels[chip] >= noise_cut])
            total_hits += n_hits
            noisypixels = np.argwhere(data_pixels[chip] >= noise_cut)
            print("chip",chip)
            print("noisy",noisypixels)
            print("totalnoisy",totalnoisy)
            noiseOccMap = np.divide(data_pixels[chip], ntrg)
            noiseOccMap[noiseOccMap==0] = np.nan

            cmap = plt.colormaps["cool"].copy()
            cmap.set_under(color='white')
            noiseocc = n_hits/(1024*eventTime*ntrg)

            plt.figure(f"Noise occupancy map {chip}", figsize=(10,6))
            plt.subplots_adjust(left=0.08, right=0.78)
            ax = plt.gca()
            plt.imshow(noiseOccMap,cmap=cmap,norm=LogNorm())
            divider = make_axes_locatable(ax)
            cax = divider.append_axes("right", size="5%", pad=0.05)
            plt.colorbar(format='%.0e', cax=cax).set_label('Noise occupancy (hits event$^{-1}$)')
            ax.set_ylabel('Row')
            ax.set_xlabel('Column')
            ax.set_title(f'Noise occupancy map {chip}')
            ax.text(1.17, 1, f"Triggers: {ntrg:.1e}\nHits: {n_hits}\nNoise occ.: {noiseocc:.2e}\n# noisy pixels: {totalnoisy}\n+ noisy pixel",
                    fontsize = 10,horizontalalignment='left',verticalalignment='center',transform=ax.transAxes)
            ax.scatter(noisypixels[:,1],noisypixels[:,0], color='black', marker="+", label="Noisy Pixel")
            plt.savefig(fname + f"_{chip}_noiseOccupancymap.png")


        print("Total hits: " + str(total_hits))
        return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--filepath", required=False, help="Path to file to analyse", default="/dev/stdin")
    parser.add_argument("-n", "--noise_cut", required=False, type=int, help="Noise cut", default=10)
    parser.add_argument("-t", "--ntrg", required=False, type=int, help="Number of triggers", default=1e6)
    parser.add_argument("-s", "--show", required=False, type=int, help="Show plots", default=0)
    args = parser.parse_args()

    filepath = args.filepath
    noise_cut = args.noise_cut
    ntrg = args.ntrg
    showplots = args.show

    print("Reading file: " + filepath)
    print("Noise cut: " + str(noise_cut))
    print("Number of triggers: " + str(ntrg))
    reader = HitMapReader(filepath)
    reader.main(noise_cut, ntrg)

    if showplots:
        plt.show()

    exit(0)
