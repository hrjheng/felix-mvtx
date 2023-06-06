#!/bin/bash

H=$(hostname)
timestamp=$(date +%Y%m%d_%H%M%S)

which o2-readout-exe > /dev/null 2>&1
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
	../../py/${tb}.py log_all_clock_health_status
    done
} 2>&1 | tee ~/logs/clock_health_status_${H}_${timestamp}.log
