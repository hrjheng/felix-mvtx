#!/bin/bash

H=$(hostname)
timestamp=$(date +%Y%m%d_%H%M%S)

mkdir -p ~/logs

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

{
    for tb in $(grep -rnH "\"${H}\"" ../../config/*.yml | grep -v "LTU" | cut -d':' -f1 | cut -d'/' -f4 | cut -d'.' -f1)
    do
	echo "========= ${tb} ========="
	../../py/${tb}.py info-for-corrupt-ru
    done

    for card in $(seq 0 3)
    do
	o2-roc-status --id=#${card} --onu-status
    done
} 2>&1 | tee ~/logs/rdo_status_extended_${H}_${timestamp}.log
