#!/bin/bash

subracks=( "pp1i0"   "pp1o7"   "pp1i7"   "pp1o0"   "pp1o6"  "pp1i6"    "pp1i1"   "pp1o1"   "pp1i5"   "pp1i2"   "pp1o5"   "pp1o2"   "pp1i25"  "pp1o25"  )
names=(    "l6bi"    "l6to"    "l6bo"    "l6bi"    "l5bi"   "l5bo"     "l5ti"    "l5to"    "l4bi"    "l4bo"    "l4ti"    "l4to"    "l3b"     "l3t"     )
cards_1=(  "85:00.0" "83:00.0" "02:00.0" "04:00.0" "04:00.0" "02:00.0" "04:00.0" "02:00.0" "04:00.0" "02:00.0" "02:00.0" "04:00.0" "04:00.0" "02:00.0" )
cards_2=(  "86:00.0" "84:00.0" "03:00.0" "05:00.0" "05:00.0" "03:00.0" "05:00.0" "03:00.0" "05:00.0" "03:00.0" "03:00.0" "05:00.0" "05:00.0" "03:00.0" )
linkMasks=("0-11"    "0-11"    "0-11"    "0-11"    "0-9"     "0-10"    "0-9"     "0-10"    "0-6"     "0-7"     "0-7"     "0-6"     "0-11"    "0-11"    )

nfiles=${#subracks[@]}
echo ${nfiles}

for iFile in $(seq 0 $((${nfiles} - 1)))
do
    subrack="${subracks[${iFile}]}"
    name="${names[${iFile}]}"
    card_1="${cards_1[${iFile}]}"
    card_2="${cards_2[${iFile}]}"
    linkMask="${linkMasks[${iFile}]}"
    filename=readout_${name}_${subrack}.cfg
    echo "${filename} ${card_1} ${card_2}"
    cp readout_ob_tmp.cfg "${filename}"
    sed -i "s/<DETECTOR_ELEMENT>/${name}/" "${filename}"
    sed -i "s/<SUBRACK>/${subrack}/" "${filename}"
    sed -i "s/<CARDID_1>/${card_1}/" "${filename}"
    sed -i "s/<CARDID_2>/${card_2}/" "${filename}"
    sed -i "s/<LINK_MASK>/${linkMask}/" "${filename}"
done
