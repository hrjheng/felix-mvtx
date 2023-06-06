#!/usr/bin/env python3

import argparse
import json
import glob
import os
from pathlib import Path
from tqdm import tqdm
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.colors import LogNorm
from mpl_toolkits.axes_grid1 import make_axes_locatable


def analyse_fhr(npyfile, jsonfile, outdir, noise_cut, mask, verbose=True):
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    fname = os.path.join(outdir,Path(npyfile).stem)

    with open(jsonfile) as jf:
        pars = json.load(jf)

    if mask is not None:
        mask=np.load(mask)
        if verbose:
            print("Using a mask:")
            print(mask)

    data_pixels = np.load(npyfile)

    eventTime = 4.455e-5 # 44.550 us

    # sensitivity limit of the measurement
    # senselimit = 1/(pars['ntrg']*eventTime*1024)

    noiseOccMap = np.zeros((512,1024), dtype=float)

    for chip in range(3):
        n_hits = np.sum(data_pixels[chip])
        if n_hits == 0:
            continue

        totalnoisy = np.count_nonzero(data_pixels[chip, data_pixels[chip] >= noise_cut])
        noisypixels = np.argwhere(data_pixels[chip] >= noise_cut)
        #print("noisy",noisypixels)
        noiseOccMap = np.divide(data_pixels[chip], pars['ntrg'])
        noiseOccMap[noiseOccMap==0] = np.nan

        #cmap = plt.colormaps["viridis"].copy()
        cmap = plt.colormaps.get_cmap("cool").copy()
        cmap.set_under(color='white')
        noiseocc = n_hits/(1024*eventTime*pars['ntrg'])

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
        ax.text(1.17, 1, f"Triggers: {pars['ntrg']:.1e}\nHits: {n_hits}\nNoise occ.: {noiseocc:.2e}\n# noisy pixels: {totalnoisy}\n+ noisy pixel", fontsize = 10,horizontalalignment='left',verticalalignment='center',transform=ax.transAxes)
        # plot_parameters(pars, x=1.28, y=0.7)
        ax.scatter(noisypixels[:,1],noisypixels[:,0], color='black', marker="+", label="Noisy Pixel")
        plt.savefig(fname + f"_{chip}_noiseOccupancymap.png")

    return True


if __name__=="__main__":
    parser = argparse.ArgumentParser("Fake hit-rate analysis.",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("file", help="npy or json file created by fhr.py or directory containing such files.")
    parser.add_argument('--outdir' , default="./plots", help="Directory with output files")
    parser.add_argument('-q', '--quiet', action='store_true', help="Do not display plots.")
    parser.add_argument('--noise-cut',default=10, type=int, help="The cut on the number of hits above which a pixel is masked.")
    parser.add_argument('--mask', help="Path to the masking file that contains the pixels to be masked.", default=None)
    args = parser.parse_args()

    if '.npy' in args.file:
        analyse_fhr(args.file, args.file.replace('.npy','.json'),args.outdir,args.noise_cut,args.mask)
    elif '.json' in args.file:
        analyse_fhr(args.file.replace('.json','.npy'),args.file,args.decoding_calib,args.outdir,args.noise_cut,args.mask)
    else:
        if '*' not in args.file: args.file+='*.npy'
        print("Processing all file matching pattern ", args.file)
        for f in tqdm(glob.glob(args.file),desc="Processing file"):
            if '.npy' in f and "thr" not in f.split("/")[-1]:
                analyse_fhr(f, f.replace('.npy','.json'), args.outdir, args.noise_cut, args.mask, False)
                plt.close('all')

    if not args.quiet:
        plt.show()
