#!/usr/bin/env python3

import argparse
import json
import glob
import os
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle
from scipy.optimize import curve_fit
from tqdm import tqdm
from mpl_toolkits.axes_grid1 import make_axes_locatable


def gaus(x,a,x0,sigma):
    return a*np.exp(-(x-x0)**2/(2*sigma**2))


def scurve_fit(steps, ninj):
    dvs=sorted(steps.keys())
    m=0
    s=0
    den=0
    for dv1,dv2 in zip(dvs[:-1],dvs[1:]):
        ddv=dv2-dv1
        mdv=0.5*(dv2+dv1)
        n1=1.0*steps[dv1]/ninj
        n2=1.0*steps[dv2]/ninj
        dn=n2-n1
        den+=dn/ddv
        m+=mdv*dn/ddv
        s+=mdv**2*dn/ddv/ddv
    if den>0:
        if s>m*m:
            s=(s-m*m)**0.5
        m/=den
        s/=den
    return m,s


def analyse_threshold_scan(npyfile, jsonfile, outdir, xmin, xmax, pixel=None, verbose=True):
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    fname = outdir+'/'+npyfile[npyfile.rfind('/')+1:].replace('.npy','')

    with open(jsonfile) as jf:
        pars = json.load(jf)
    vmin = float(min(pars["vsteps"]))

    data = np.load(npyfile)

    thrmap = np.zeros((3,512,1024))
    noisemap = np.zeros((3,512,1024))

    for chip in tqdm(range(3), desc="Chip", leave=False):  # 3 chips per FEEID
        n_hits = np.sum(data[chip])
        if n_hits == 0:  # no data for this chip
            continue

        thrs = []
        noise = []

        plt.figure(f"scurve {chip}")
        npix = 0
        for r in tqdm(pars["rows"], desc="Row", leave=False):
            for c in tqdm(pars["cols"], desc="Col", leave=False):
                m,s = scurve_fit({pars["vsteps"][i]:data[chip,r,c,i] for i in range(len(pars["vsteps"]))}, pars["ninj"])
                if (m < vmin) or (m > float(pars["vmax"])):
                    continue
                if (c % 32 == 0) and (r % 16 == 0):
                    npix += 1
                    plt.plot(pars["vsteps"], data[chip,r,c,:], color='tab:red', alpha=0.1, linewidth=1)  # , \
                        # label=f"{c}-{r}: Thr: {m:.1f}, Noise: {s:.1f}")
                thrs.append(m)
                noise.append(s)
                thrmap[chip,r,c] = m
                noisemap[chip,r,c] = s
        if pixel:
            c = pixel[0]
            r = pixel[1]
            plt.plot(pars["vsteps"], data[chip, r, c,:], color='tab:blue', alpha=1, linewidth=1,
                     label=f"c:{c}-r:{r}: Thr: {thrmap[chip,r,c]:.1f}, Noise: {noisemap[chip,r,c]:.1f}")

        plt.xlabel("Injected charge (e$^-$)")
        plt.ylabel("# hits")
        plt.title(f"Chip {chip} S-curve measurement ({npix} pixels)")
        if pixel:
            plt.legend(loc="upper left")

        plt.xlim(xmin, xmax if xmax else pars["vmax"])
        plt.ylim(0,pars["ninj"]+1)
        # plot_parameters(pars)
        plt.savefig(fname+f"_{chip}_scurve.png")

        nbins = 70
        npix = len(pars["rows"])*len(pars["cols"])

        xmax = xmax if xmax else pars["vmax"]
        plt.figure(f"threshold {chip}")
        plt.xlabel('Threshold (e$^-$)')
        plt.ylabel(f'# pixels / ({(xmax-xmin)/nbins:.1f} e$^-$)')
        plt.title(f'Chip {chip} Threshold distribution ({npix} pixels)')
        hist,bin_edges,_ = plt.hist(thrs, range=(xmin,xmax), bins=nbins,
                                    label=f"Mean: {np.mean(thrs):5.1f} e$^-$\nRMS:  {np.std(thrs):5.1f} e$^-$")
        bin_mid = (bin_edges[:-1] + bin_edges[1:])/2
        try:
            popt,_  = curve_fit(gaus, bin_mid, hist, [10, np.mean(thrs), np.std(thrs)])
            plt.plot(np.arange(xmin, xmax, (xmax-xmin)/nbins), gaus(np.arange(xmin, xmax, (xmax-xmin)/nbins), *popt),
                     label=f'$\mu$:    {popt[1]:5.1f} e$^-$\n$\sigma$:    {popt[2]:5.1f} e$^-$')
        except Exception as e:
            if verbose:
                print("Fitting error", e)

        plt.legend(loc="upper right", prop={"family":"monospace"})
        plt.xlim(xmin,xmax)
        # plot_parameters(pars)
        plt.savefig(fname+f"_{chip}_threshold.png")

        cmap = plt.cm.get_cmap("viridis").copy()
        cmap.set_under(color='white')

        plt.figure(f"Chip {chip} Threshold map")
        thrmap[thrmap==0] = np.nan
        plt.subplots_adjust(left=0.085, right=0.85)
        ax = plt.gca()
        plt.imshow(thrmap[chip], cmap=cmap)
        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="5%", pad=0.05)
        plt.colorbar(format='%.0e', cax=cax).set_label('Threshold (e$^-$)')
        if pixel:
            plt.gca().add_patch(Rectangle((pixel[0]-.5, pixel[1]-.5), 1, 1, edgecolor="red", facecolor="none"))
        ax.set_xlabel('Column')
        ax.set_ylabel('Row')
        ax.set_title(f'Chip {chip} Threshold map')
        # plot_parameters(pars, x=1.23, y=0.7)
        plt.savefig(fname+f"_{chip}_thrmap.png")

    np.savez(fname+"_analyzed.npz",thresholds=thrmap,noise=noisemap)
    if not verbose:
        plt.close('all')


if __name__=="__main__":
    parser = argparse.ArgumentParser("Threshold analysis.",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("file", help="npy or json file created by dpts_threshold.py or directory containing such files.")
    parser.add_argument('--outdir', default="./plots", help="Directory with output files")
    parser.add_argument('--xmin', default=0, type=int, help="X axis low limit")
    parser.add_argument('--xmax', default=0, type=int, help="X axis high limit (0 = use vmax)")
    parser.add_argument('-q', '--quiet', action='store_true', help="Do not display plots.")
    parser.add_argument('--pixel', default=None, nargs=2, type=int, help="Highlight one pixel in the s-curves and matrices.")
    args = parser.parse_args()

    if '.npy' in args.file:
        analyse_threshold_scan(args.file, args.file.replace('.npy','.json'), args.outdir, args.xmin, args.xmax, args.pixel)
    elif '.json' in args.file:
        analyse_threshold_scan(args.file.replace('.json','.npy'),args.file, args.outdir, args.xmin, args.xmax, args.pixel)
    else:
        if '*' not in args.file: args.file+='*.npy'
        print("Processing all file matching pattern ", args.file)
        for f in tqdm(glob.glob(args.file),desc="Processing file"):
            if '.npy' in f and "fhr" not in f.split("/")[-1]:
                analyse_threshold_scan(f, f.replace('.npy','.json'), args.outdir, args.xmin, args.xmax, args.pixel, False)
                plt.close('all')

    if not args.quiet:
        plt.show()
