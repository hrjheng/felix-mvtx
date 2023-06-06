#!/usr/bin/env python3

import sys
import json
import re
import os
import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

path=sys.argv[1]
XX=10 if len(sys.argv)<3 else float(sys.argv[2])
params=json.loads(open(path+'/run_parameters.json').read())
vcasn_ithr_list=params['_vcasn_ithr_list']
vcasns=set(s[0] for s in vcasn_ithr_list)
ithrs =set(s[1] for s in vcasn_ithr_list)
ithrs =sorted(ithrs)
vcasns=sorted(vcasns)

feeids = [ feeid | (2<<12) | (gbt<<8) for feeid in range(20,28) for gbt in range(3)]

data=[]
for i,(vcasn,ithr) in enumerate(vcasn_ithr_list):
    for feeid in feeids:
        fname=f'{path}/thrtun/thr_map_{feeid}-{i}.dat'
        if not os.path.isfile(fname): continue
        thrs=np.fromfile(fname,dtype=np.float32)
#        print(fname,thrs,thrs.shape)
        if not len(thrs): continue
        thrs=thrs.reshape((6,3,1024)).swapaxes(0,1)
        gbt = (feeid >> 8) & 0x3
        stave_feeid = feeid & 0xF03F
        for chip in range(3):
#            print(stave_feeid, gbt, 3*gbt+chip)
            data.append((vcasn,ithr,stave_feeid,3*gbt+chip,np.mean(thrs[chip]),
                        np.var(thrs[chip]),np.sum(thrs[chip]!=0)))

stave_feeids = set(feeid & 0xF03F for feeid in feeids)
print(stave_feeids)
data=[d for d in data if d[4]<30 and d[6]>6*1024*0.9]
class FitFunction:
    def __init__(self,vcasn0):
        self.vcasn0=vcasn0
    def __call__(self,vcasn,A,B,a):
        return A+B*np.exp(-(vcasn-self.vcasn0)/a)

class GlobalFitFunction:
    def __init__(self,vcasn0,ithr1,ithr2):
        self.vcasn0=vcasn0
        self.ithr1=ithr1
        self.ithr2=ithr2
    def __call__(self,vi,A1,B1,A2,B2,a):
        vcasn,ithr=vi
        t1=A1+B1*np.exp(-(vcasn-self.vcasn0)/a)
        t2=A2+B2*np.exp(-(vcasn-self.vcasn0)/a)
        return t1+(t2-t1)/(self.ithr2-self.ithr1)*(ithr-self.ithr1)

fig,axes=plt.subplots(ncols=9,nrows=len(stave_feeids),sharex=True,sharey=True)
fig.subplots_adjust(wspace=0,hspace=0)
data=sorted(data)

config={}

for feeid in stave_feeids:
    layer = feeid >> 12
    stave = feeid & 0x1F
    staveid='L%01d_%02d'%(layer,stave)
    config[staveid]={}
    for chip in range(9):
        chipid='CHIP_%d'%chip
        #if staveid+chipid not in ["L0_01CHIP_8","L1_03CHIP_5","L1_03CHIP_8"]: continue
        axis=axes[stave-20][chip]
        axis.grid()
        if (chip==0): axis.set_ylabel("stave %d"%stave)
        if (stave==27): axis.set_xlabel("chip %d"%chip)
        for ithr in reversed(ithrs):
            x=np.array([vcasn for (vcasn,ithrp,feeidp,chipp,m,s,n) in data if feeidp==feeid and chipp==chip and ithrp==ithr])
            y=np.array([m     for (vcasn,ithrp,feeidp,chipp,m,s,n) in data if feeidp==feeid and chipp==chip and ithrp==ithr])
            axis.scatter(x,y,label='ITHR=%d'%ithr)
            #f=FitFunction(min(vcasns))
            #(A,B,a),pcov=curve_fit(f,x,y,(5,5,2))
            #x=np.linspace(x[0],x[-1])
            #axis.plot(x,f(x,A,B,a))
            #if chip==2 and stave==8:
            #    for xi,yi in zip(x,y):
            #        print (ithr,xi,yi)
            #    print()
            #    print()

        x1=np.array([vcasn for (vcasn,ithrp,feeidp,chipp,m,s,n) in data if feeidp==feeid and chipp==chip and ithrp==ithrs[0]])
        y1=np.array([m     for (vcasn,ithrp,feeidp,chipp,m,s,n) in data if feeidp==feeid and chipp==chip and ithrp==ithrs[0]])
        x2=np.array([vcasn for (vcasn,ithrp,feeidp,chipp,m,s,n) in data if feeidp==feeid and chipp==chip and ithrp==ithrs[-1]])
        y2=np.array([m     for (vcasn,ithrp,feeidp,chipp,m,s,n) in data if feeidp==feeid and chipp==chip and ithrp==ithrs[-1]])

        if len(x1)==0: continue

        f=FitFunction(min(vcasns))
        #if not all(x1==x2): print('WARNING X:',staveid,chipid,x1,x2)
        #if not all(y1<y2): print('WARNING Y:',staveid,chipid,y1,y2)
        (A1,B1,a1),pcov=curve_fit(f,x1,y1,(10,10,5))
        (A2,B2,a2),pcov=curve_fit(f,x2,y2,(10,10,5))
        #if A2<0: print(x1,y1,x2,y2)
        #print(staveid,chipid,A1,B1,a1,A2,B2,a2)
        g=GlobalFitFunction(min(vcasns),ithrs[0],ithrs[-1])
        x=np.array([(vcasn,ithr) for (vcasn,ithr,feeidp,chipp,m,s,n) in data if feeidp==feeid and chipp==chip]).T
        y=np.array([m            for (vcasn,ithr,feeidp,chipp,m,s,n) in data if feeidp==feeid and chipp==chip]).T
        (A1,B1,A2,B2,a),pcov=curve_fit(g,x,y,(A1,B1,A2,B2,(a1+a2)/2))
        delta=g(x,A1,B1,A2,B2,a)-y
        if (np.max(np.abs(delta))>0.2):
            print(staveid,chipid,np.max(np.abs(delta)))
        for ithr in reversed(ithrs):
            x=np.linspace(vcasns[0],vcasns[-1])
            y=g((x,ithr),A1,B1,A2,B2,a)
            axis.plot(x,y)
        t=g((np.arange(vcasns[0]-5,vcasns[-1]+1+5),50),A1,B1,A2,B2,a)
        #print(vcasns,t)
        vcasn10=vcasns[0]-5+(np.abs(t-10)).argmin()
        vcasnXX=vcasns[0]-5+(np.abs(t-XX)).argmin()
        t10=g((vcasn10,np.arange(ithrs[0],ithrs[-1]+1)),A1,B1,A2,B2,a)
        tXX=g((vcasnXX,np.arange(ithrs[0],ithrs[-1]+1)),A1,B1,A2,B2,a)
        ithr10=ithrs[0]+(np.abs(t10-10)).argmin()
        ithrXX=ithrs[0]+(np.abs(tXX-XX)).argmin()
        print(stave,chip,vcasn10,ithr10,g((vcasn10,ithr10),A1,B1,A2,B2,a))
        #print(stave,chip,vcasnXX,ithrXX,g((vcasnXX,ithrXX),A1,B1,A2,B2,a))
        #config[staveid][chipid]={'ITHR':int(ithr10),'VCASN':int(vcasn10),'VCASN2':int(vcasn10+12)}
        config[staveid][chipid]={'ITHR':int(ithrXX),'VCASN':int(vcasnXX),'VCASN2':int(vcasnXX+12)}
print(json.dumps(config, indent=4, sort_keys=True))
with open(path+'/threshold_tuned.json', 'w') as jsonfile:
    json.dump(config, jsonfile, indent=4, sort_keys=True)

for vcasnp in vcasns:
    try:
        m1=next(m for (vcasn,ithrp,stavep,chipp,m,s,n) in data if stavep==8 and chipp==2 and vcasn==vcasnp and ithrp==min(ithrs))
        m2=next(m for (vcasn,ithrp,stavep,chipp,m,s,n) in data if stavep==8 and chipp==2 and vcasn==vcasnp and ithrp==max(ithrs))
        #print(vcasnp,m1,m2)
    except: pass

axes[0][0].set_xlim(min(vcasns)-2,max(vcasns)+2)
axes[0][0].set_ylim(0,35)

axes[0][-1].legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0)

plt.show()

