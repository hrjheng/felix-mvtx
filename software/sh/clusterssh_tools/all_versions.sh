#!/bin/bash

H=$(hostname)
timestamp=$(date +%Y%m%d_%H%M%S)

which o2-readout-exe
if [[ $? -ne 0 ]]
then
    echo "Could not load o2-readout-exe"
    exit 1
fi
python3.9 <<EOF
import libO2Lla
EOF
if [[ $? -ne 0 ]]
then
    echo "Could not load the LLA library into python3.9"
    exit 1
fi

mkdir -p ~/logs

{
    for tb in $(grep -rnH "\"${H}\"" ../../config/*.yml | grep -v "LTU" | cut -d':' -f1 | cut -d'/' -f4 | cut -d'.' -f1)
    do
        echo "========= ${tb} ========="
        ../../py/${tb}.py cru initialize
        ../../py/${tb}.py program-all-xcku
        ../../py/${tb}.py version
        ../../py/${tb}.py feeid
    done
} 2>&1 | tee ~/logs/all_versions_${H}_${timestamp}.log
