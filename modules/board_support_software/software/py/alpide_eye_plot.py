#!/usr/bin/env python3.9
# coding: utf-8
"""Script derived from software/jupyter/alpide_eye_plot.py"""

import argparse
import os
import re
import sys

from matplotlib import pyplot as plt
from matplotlib import colors
from matplotlib.ticker import LogFormatter
from scipy.interpolate import griddata

import numpy as np

from ru_eyescan import VerticalRange

script_path = os.path.dirname(os.path.realpath(__file__))


def load_data(file_name):
    """Loads the data file from csv and fills a table
    {(a,b):(c,d)}
    """
    table = {}
    # fill table
    with open(file_name,'r') as f:
        for line in f:
            dat = line.rstrip("\n").split(",")
            table[(int(dat[1]),int(dat[2]))] = (int(dat[3]),int(dat[4]))
    print("Recovered {0} data points".format(len(table)))
    return table

def draw_plot(table,
              cmap,
              figure=1,
              voltage_codes = 2.8,
              title=None,
              save=False,
              out_directory=None):
    plt.style.use('ggplot')
    data = table
    sx = set()
    sy = set()
    for coords in data:
        sx.add(coords[0])
        sy.add(coords[1])

    n = 1e5

    px = sorted(list(sx))
    py = sorted(list(sy))

    max_samples = 0

    X,Y = np.meshgrid(px,py)
    Z = np.zeros(X.shape)
    for i,pi in enumerate(px):
        for j,pj in enumerate(py):
            if (pi,pj) in data:
                datItem = data[(pi,pj)]
            else:
                datItem = (1,1)
            if datItem[0] == -1:
                Z[j,i] = 0
            elif datItem[1] == 0:
                Z[j,i] = 1/(datItem[0] + 1)
            else:
                Z[j,i]= datItem[1]/datItem[0]
            max_samples = max(max_samples,datItem[0])

    min_val = 1/(max_samples)
    max_val = 0.5

    for x in np.nditer(Z,op_flags=['readwrite']):
        if x[...] < min_val:
            x[...] = min_val
        elif x[...] >  max_val:
            x[...] = max_val

    w, h = plt.figaspect(0.35)
    plt.figure(figure,figsize=(w,h))

    X = X * (0.5/128)
    Y = Y * voltage_codes

    levels = np.logspace(np.log10(min_val),np.log10(max_val),100)
    cs = plt.contourf(X, Y, Z,levels,norm=colors.LogNorm(),cmap=cmap)
    if title:
        plt.title('Statistical Eye: {0}'.format(title))
    else:
        plt.title('Statistical Eye')
    plt.xlabel('Phase offset [UI]')
    plt.ylabel('Voltage offset [mV]')

    lvls = np.logspace(np.log10(min_val),np.log10(max_val),12)
    l_f = LogFormatter(10, labelOnlyBase=True)
    cbar = plt.colorbar(cs,ticks=lvls,format=l_f)
    cbar.set_label('BER')
    colors.Normalize(vmin=min_val,vmax=max_val)
    cbar.ax.set_yticklabels(['{0:.1E}'.format(l) for l in lvls])
    if save:
        out_directory = os.path.join(script_path,out_directory)
        if not os.path.isdir(out_directory):
            os.mkdir(out_directory)
        out_filename=os.path.join(out_directory,title)+'.pdf'
        plt.savefig(out_filename,bbox_inches='tight')
        plt.close()
    else:
        plt.show()

def sample2ber(samples,errors):
    """Calculates the BER based on the number of samples and errors
    Assumes no CL"""
    if errors > 0:
        return errors/samples
    else:
        return 1/samples #TODO: add confidence level measurement

def slice_at_y(table, y_slice=0):
    """Returns a slice at y=y_slice of the eye

    x vector is the UI position
    y is the BER at that point"""
    sliced = {x:(sample,error) for (x,y),(sample,error) in table.items() if y==y_slice}
    bers = {key: sample2ber(samples,errors) for key,(samples,errors) in sliced.items()}
    x = sorted(list(bers.keys()))
    y = [bers[ax] for ax in x]
    x = [i*0.5/128 for i in x] # Applies the index=>UI trasformnation
    return (x,y)

def draw_horizontal_slice(table,
                          figure,
                          title,
                          voltage_codes,
                          out_directory,
                          save=False):
    plt.style.use('ggplot')
    max_samples = max([samples for (x,y),(samples,errors) in table.items() if errors==0])
    w, h = plt.figaspect(0.35)
    plt.figure(figure,figsize=(w,h))
    ax = plt.gca()
    for y in [-32,-16,0,16,32]:
        (x1,y1) = slice_at_y(table, y_slice=y)
        ax.plot(x1 ,y1,'.-',label=f'Phase offset = {y*voltage_codes:.3f} mV')
        plt.xlim(min(x1),max(x1))
    ymin = sample2ber(max_samples,0)
    plt.axhline(y=ymin,label="Lower Bound",ls='--')
    plt.ylim(ymin*0.9,0.5+0.1)
    ax.set_yscale('log')
    plt.xlabel('Phase offset [UI]')
    plt.ylabel('BER')
    plt.title('Horizontal slices of the statistical eye')
    plt.legend(loc="best", shadow=True, fancybox=True)
    if save:
        out_directory = os.path.join(script_path,out_directory)
        if not os.path.isdir(out_directory):
            os.mkdir(out_directory)
        out_filename=os.path.join(out_directory,title)+'_horz.pdf'
        plt.savefig(out_filename,bbox_inches='tight')
        plt.close()
    else:
        plt.show()

def slice_at_x(table, x_slice=0, voltage_codes=2.8):
    """Returns a slice at x=x_slice of the eye

    x vector is the opening in mV of the eye,
    y is the BER at that point"""
    sliced = {y:(sample,error) for (x,y),(sample,error) in table.items() if x==x_slice}
    bers = {key: sample2ber(samples,errors) for key,(samples,errors) in sliced.items()}
    x = sorted(list(bers.keys()))
    y = [bers[ax] for ax in x]
    x = [i*voltage_codes for i in x] # Applies the voltage code transformation
    return (x,y)

def draw_vertical_slice(table,
                        figure,
                        title,
                        voltage_codes,
                        out_directory,
                        save=False):
    plt.style.use('ggplot')
    max_samples = max([samples for (x,y),(samples,errors) in table.items() if errors==0])
    w, h = plt.figaspect(0.35)
    plt.figure(figure,figsize=(w,h))
    ax = plt.gca()
    for x in [-32,-16,0,16,32,48,64]:
        (x1,y1) = slice_at_x(table, x_slice=x, voltage_codes=voltage_codes)
        ax.plot(x1 ,y1,'.-',label=f'Phase offset = {x*0.5/128:.3f} UI')
        plt.xlim(min(x1),max(x1))
    ymin = sample2ber(max_samples,0)
    plt.axhline(y=ymin,label="Lower Bound",ls='--')
    plt.ylim(ymin*0.9,0.5+0.1)
    ax.set_yscale('log')
    plt.xlabel('Voltage offset [mV]')
    plt.ylabel('BER')
    plt.title('Vertical slices of the statistical eye')
    plt.legend(loc="best", shadow=True, fancybox=True)
    if save:
        out_directory = os.path.join(script_path,out_directory)
        if not os.path.isdir(out_directory):
            os.mkdir(out_directory)
        out_filename=os.path.join(out_directory,title)+'_vert.pdf'
        plt.savefig(out_filename,bbox_inches='tight')
        plt.close()
    else:
        plt.show()

def _filter_or_default(a_list, default, verbose=False):
    """Creates the filter input list"""
    if a_list:
        assert isinstance(a_list,(list,tuple)), "f{a_list} is not a list or tuple"
    else:
        a_list = default
    if verbose:
        print(a_list)
    return a_list

def filter_accepted(a_layer,a_stave,a_driver,a_pre,a_chargepump,a_stages,a_chip):
    """Creates the list to filter for"""
    a_layer      = _filter_or_default(a_layer, list(range(7)))
    a_stave      = _filter_or_default(a_stave, list(range(48)))
    a_driver     = _filter_or_default(a_driver, list(range(16)))
    a_pre        = _filter_or_default(a_pre, list(range(16)))
    a_chargepump = _filter_or_default(a_chargepump, list(range(16)))
    a_stages     = _filter_or_default(a_stages, [3,4,5])
    a_chip       = _filter_or_default(a_chip, list(range(9)))
    return a_layer,a_stave,a_driver,a_pre,a_chargepump,a_stages,a_chip

def get_filelist(csv_directory,
                 a_layer=None,
                 a_stave=None,
                 a_driver=None,
                 a_pre=None,
                 a_chargepump=None,
                 a_stages=None,
                 a_chip=None):
    """Returns a sorted list of files to be used for eye diagram.
    If a(ccepted)_{layer|staves|driver|pre|chargepump|stages} are specified,
     it only filters for these.
    """
    a_layer,a_stave,a_driver,a_pre,a_chargepump,a_stages,a_chip = filter_accepted(a_layer,a_stave,a_driver,a_pre,a_chargepump,a_stages,a_chip)

    re_str = r"L(\d)_(\d+)_eyescan_flp_d(\d)p(\d)c(\d)s(\d)_chip_(\d)_vr(\d)"
    r = re.compile(re_str)

    filenames = []
    vrs = []
    onlyfiles = [f for f in os.listdir(csv_directory) if os.path.isfile(os.path.join(csv_directory, f))]
    onlyfiles.sort()
    for f in onlyfiles:
        match = r.match(f)
        if match:
            layer      = int(match.group(1))
            stave      = int(match.group(2))
            driver     = int(match.group(3))
            pre        = int(match.group(4))
            chargepump = int(match.group(5))
            stages     = int(match.group(6))
            chip       = int(match.group(7))

            if layer in a_layer and stave in a_stave and driver in a_driver and pre in a_pre and chargepump in a_chargepump and stages in a_stages and chip in a_chip:
                filenames.append(match.group(0).rstrip('.csv'))
                vrs.append(float(VerticalRange(int(match.group(8))).name[2:5].replace('_','.')))
    print(f"found {len(filenames)} file(s)")
    return filenames, vrs

def plot_all(filenames, vrs, cmap, csv_directory, out_directory, save):
    for idx,filename in enumerate(filenames):
        try:
            vr = vrs[idx]
            table = load_data(os.path.join(csv_directory, filename+'.csv'))
            draw_plot(table,
                      figure=idx,
                      voltage_codes=vr,
                      title=filename[:-4],
                      cmap=cmap,
                      out_directory=out_directory,
                      save=save)
            draw_vertical_slice(table,
                                figure=idx+len(filenames),
                                voltage_codes=vr,
                                title=filename[:-4],
                                out_directory=out_directory,
                                save=save)
            draw_horizontal_slice(table,
                                  figure=idx+2*len(filenames),
                                  voltage_codes=vr,
                                  title=filename[:-4],
                                  out_directory=out_directory,
                                  save=save)
        except FileNotFoundError:
             print(f'ERROR: {filename}.csv not found')

def main(csv_directory,
         out_directory,
         cm,
         save,
         accepted_layer=None,
         accepted_stave=None,
         accepted_driver=None,
         accepted_pre=None,
         accepted_chargepump=None,
         accepted_stages=None,
         accepted_chip=None):
    filenames, vrs = get_filelist(csv_directory,
                                  accepted_layer,accepted_stave,
                                  accepted_driver,accepted_pre,
                                  accepted_chargepump,accepted_stages,
                                  accepted_chip)
    plot_all(filenames, vrs, cm, csv_directory, out_directory, save)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--plot", "-p", required=False, help="Switch, if enabled only shows", action='store_true')
    parser.add_argument("-cd", "--csv_dir", required=False, help="Folder containing the CSV files", default='eyes_csv')
    parser.add_argument("-od", "--out_dir", required=False, help="Folder containing the output files", default='eyes_plot')
    parser.add_argument("-al",  "--a_layer", required=False, nargs='+', help="list (space-separated) of layers to be analysed, leave empty for all", default=None)
    parser.add_argument("-as",  "--a_stave", required=False, nargs='+', help="list (space-separated) of staves to be analysed, leave empty for all", default=None)
    parser.add_argument("-ac",  "--a_chip", required=False, nargs='+', help="list (space-separated) of chips to be analysed, leave empty for all", default=None)
    parser.add_argument("-ad",  "--a_driver", required=False, nargs='+', help="list (space-separated) of DTU driver to be analysed, leave empty for all", default=None)
    parser.add_argument("-ap",  "--a_pre", required=False, nargs='+', help="list (space-separated) of DTU preemphasis to be analysed, leave empty for all", default=None)
    parser.add_argument("-acp",  "--a_chargepump", required=False, nargs='+', help="list (space-separated) of DTU PLL chargepump to be analysed, leave empty for all", default=None)
    parser.add_argument("-aps", "--a_stages", required=False, nargs='+', help="list (space-separated) of DTU PLL stages to be analysed, leave empty for all", default=None)

    args = parser.parse_args()

    csv_directory = args.csv_dir
    out_directory = args.out_dir
    save = not args.plot
    accepted_layer = args.a_layer
    accepted_stave = args.a_stave
    accepted_chip = args.a_chip
    accepted_driver = args.a_driver
    accepted_pre = args.a_pre
    accepted_chargepump = args.a_chargepump
    accepted_stages = args.a_stages

    if accepted_layer is not None:accepted_layer = [int(x) for x in accepted_layer if x is not None]
    if accepted_stave is not None:accepted_stave = [int(x) for x in accepted_stave if x is not None]
    if accepted_chip is not None:accepted_chip = [int(x) for x in accepted_chip if x is not None]
    if accepted_driver is not None:accepted_driver = [int(x) for x in accepted_driver if x is not None]
    if accepted_pre is not None:accepted_pre = [int(x) for x in accepted_pre if x is not None]
    if accepted_chargepump is not None:accepted_chargepump = [int(x) for x in accepted_chargepump if x is not None]
    if accepted_stages is not None:accepted_stages = [int(x) for x in accepted_stages if x is not None]

    cmap = plt.get_cmap('jet')
    main(csv_directory, out_directory,
         cmap, save,
         accepted_layer,
         accepted_stave,
         accepted_driver,
         accepted_pre,
         accepted_chargepump,
         accepted_stages,
         accepted_chip)
