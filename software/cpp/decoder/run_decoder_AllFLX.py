import time
import os
import sys
import re
from argparse import ArgumentParser
from datetime import datetime

def replacetext(filename, search_text, replace_text):
    with open(filename, 'r+') as f:
        file = f.read()
        file = re.sub(search_text, replace_text, file)
        f.seek(0)
        f.write(file)
        f.truncate()

# Command to get the filenames on SDCC nodes: find /sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX*/20230623_1914* -type f -name *.evt
# Run 14133, 56x56, 1.5kHZ ZDC rate, 11kHz trigger rate, Data-run configuration
filenames = ['/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX0/20230622_082224_FelixFakeHitRate/mvtx_mvtx-flx0-00014133-0000.evt',
             '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX1/20230622_082226_FelixFakeHitRate/mvtx_mvtx-flx1-00014133-0000.evt',
             '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX2/20230622_082224_FelixFakeHitRate/mvtx_mvtx-flx2-00014133-0000.evt',
             '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX3/20230622_082224_FelixFakeHitRate/mvtx_mvtx-flx3-00014133-0000.evt',
             '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX4/20230622_082224_FelixFakeHitRate/mvtx_mvtx-flx4-00014133-0000.evt',
             '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX5/20230622_082224_FelixFakeHitRate/mvtx_mvtx-flx5-00014133-0000.evt']

# Yellow-beam only 
# filenames = ['/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX0/20230623_191422_FelixFakeHitRate/mvtx_mvtx-flx0-00014142-0000.evt', 
#              '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX1/20230623_191425_FelixFakeHitRate/mvtx_mvtx-flx1-00014142-0000.evt',
#              '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX2/20230623_191423_FelixFakeHitRate/mvtx_mvtx-flx2-00014142-0000.evt',
#              '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX3/20230623_191423_FelixFakeHitRate/mvtx_mvtx-flx3-00014142-0000.evt',
#              '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX4/20230623_191422_FelixFakeHitRate/mvtx_mvtx-flx4-00014142-0000.evt',
#              '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX5/20230623_191423_FelixFakeHitRate/mvtx_mvtx-flx5-00014142-0000.evt']

# Blue-beam only, test-run configuration
# filenames = ['/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX0/20230623_100745_FelixFakeHitRate/mvtx_mvtx-flx0-00014137-0000.evt', 
#              '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX1/20230623_100748_FelixFakeHitRate/mvtx_mvtx-flx1-00014137-0000.evt',
#              '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX2/20230623_100746_FelixFakeHitRate/mvtx_mvtx-flx2-00014137-0000.evt',
#              '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX3/20230623_100746_FelixFakeHitRate/mvtx_mvtx-flx3-00014137-0000.evt',
#              '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX4/20230623_100746_FelixFakeHitRate/mvtx_mvtx-flx4-00014137-0000.evt',
#              '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX5/20230623_100746_FelixFakeHitRate/mvtx_mvtx-flx5-00014137-0000.evt']

# Blue-beam only, data-run configuration
# filenames = ['/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX0/20230623_102148_FelixFakeHitRate/mvtx_mvtx-flx0-00014138-0000.evt',
#              '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX1/20230623_102150_FelixFakeHitRate/mvtx_mvtx-flx1-00014138-0000.evt',
#              '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX2/20230623_102147_FelixFakeHitRate/mvtx_mvtx-flx2-00014138-0000.evt',
#              '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX3/20230623_102148_FelixFakeHitRate/mvtx_mvtx-flx3-00014138-0000.evt',
#              '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX4/20230623_102148_FelixFakeHitRate/mvtx_mvtx-flx4-00014138-0000.evt',
#              '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX5/20230623_102147_FelixFakeHitRate/mvtx_mvtx-flx5-00014138-0000.evt']

# Without beam
# filenames = ['/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX0/20230623_200732_FelixFakeHitRate/mvtx_mvtx-flx0-00014144-0000.evt',
#              '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX1/20230623_200733_FelixFakeHitRate/mvtx_mvtx-flx1-00014144-0000.evt',
#              '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX2/20230623_200732_FelixFakeHitRate/mvtx_mvtx-flx2-00014144-0000.evt',
#              '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX3/20230623_200732_FelixFakeHitRate/mvtx_mvtx-flx3-00014144-0000.evt',
#              '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX4/20230623_200732_FelixFakeHitRate/mvtx_mvtx-flx4-00014144-0000.evt',
#              '/sphenix/lustre01/sphnxpro/commissioning/MVTX/data/runs/MVTX_FLX5/20230623_200732_FelixFakeHitRate/mvtx_mvtx-flx5-00014144-0000.evt']

prefix = '20230622_Run14133_56x56_ZDC1p5kHz_Trg11kHz_DataRunConfig_MagOff_2mrad_FEEID'
# prefix = '20230623_Run14142_111_0Hz_YBeamOnly_FEEID'
# prefix = '20230623_Run14137_111_0Hz_BBeamOnly_FEEID'
# prefix = '20230623_Run14138_111_0Hz_BBeamOnly_FEEID'
# prefix = '20230623_Run14144_NoBeam_FEEID'

prefix_log = prefix.split('_FEEID')[0]

FEEIDs = [[[0,256,512,4099,4355,4611,8198,8199,8454,8455,8710,8711],[1,257,513,4100,4356,4612,8200,8201,8456,8457,8712,8713]],
          [[2,258,514,4101,4102,4357,4358,4613,4614,8202,8458,8714], [3,259,515,4103,4359,4615,8203,8204,8459,8460,8715,8716]],
          [[4,260,516,4104,4105,4360,4361,4616,4617,8205,8461,8717],[5,261,517,4106,4362,4618,8206,8207,8462,8463,8718,8719]],
          [[6,262,518,4107,4363,4619,8208,8209,8464,8465,8720,8721],[7,263,519,4108,4364,4620,8210,8211,8466,8467,8722,8723]],
          [[8,264,520,4109,4110,4365,4366,4621,4622,8192,8448,8704],[9,265,521,4111,4367,4623,8193,8194,8449,8450,8705,8706]],
          [[10,266,522,4096,4097,4352,4353,4608,4609,8195,8451,8707],[11,267,523,4098,4354,4610,8196,8197,8452,8453,8708,8709]]]


for flx in range(6):
    feeidlist_ep1 = ''
    for i in range(len(FEEIDs[flx][0])):
        if i == len(FEEIDs[flx][0])-1:
            feeidlist_ep1 += '{}'.format(FEEIDs[flx][0][i])
        else:
            feeidlist_ep1 += '{} '.format(FEEIDs[flx][0][i])

    feeidlist_ep2 = ''
    for i in range(len(FEEIDs[flx][1])):
        if i == len(FEEIDs[flx][1])-1:
            feeidlist_ep2 += '{}'.format(FEEIDs[flx][1][i])
        else:
            feeidlist_ep2 += '{} '.format(FEEIDs[flx][1][i])

    newfile = 'run_decoder_FLX{}.sh'.format(flx)
    os.system('cp run_decoder.sh {}'.format(newfile))

    replacetext(newfile, 'FILENAME', '{}'.format(filenames[flx]))
    replacetext(newfile, 'PREFIX', '{}'.format(prefix))
    replacetext(newfile, 'FEEIDLISTEP1', '{}'.format(feeidlist_ep1))
    replacetext(newfile, 'FEEIDLISTEP2', '{}'.format(feeidlist_ep2))
    replacetext(newfile, 'ARG_EP1', '{}'.format(2000+flx*10+1))
    replacetext(newfile, 'ARG_EP2', '{}'.format(2000+flx*10+2))

    cmd = 'chmod 755 run_decoder_FLX{}.sh;nohup ./run_decoder_FLX{}.sh &> ./rundecoder_log/rundecoder_FLX{}_{}_log.out &'.format(flx, flx, flx, prefix_log)
    os.system(cmd)

    time.sleep(2)