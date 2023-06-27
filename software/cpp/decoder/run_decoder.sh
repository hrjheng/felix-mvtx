#!/bin/bash

filename=FILENAME

prefix=PREFIX

for feeid in FEEIDLISTEP1; do
   echo "Running $filename for FEEID $feeid"
#    echo "ddump -s -g -n 0 -p ARG_EP1 $filename | mvtx-decoder -t 0 -f $feeid -p $prefix$feeid"
   ddump -s -g -n 0 -p ARG_EP1 $filename | mvtx-decoder -t 0 -f $feeid -p $prefix$feeid
done

for feeid in FEEIDLISTEP2; do
   echo "Running $filename for FEEID $feeid"
#    echo "ddump -s -g -n 0 -p ARG_EP2 $filename | mvtx-decoder -t 0 -f $feeid -p $prefix$feeid"
   ddump -s -g -n 0 -p ARG_EP2 $filename | mvtx-decoder -t 0 -f $feeid -p $prefix$feeid
done