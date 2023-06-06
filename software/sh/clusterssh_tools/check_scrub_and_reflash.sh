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
        ../../py/${tb}.py check_scrub_and_reflash_all ~/RU_bitfiles/RU_mainFPGA/v1.18.0/XCKU_top_221107_1020_109ac916_bs_ecc.bit --num_checks=2 --ic=1
        ../../py/${tb}.py check_scrub_and_reflash_all ~/RU_bitfiles/RU_mainFPGA/v1.18.0/XCKU_top_221107_1020_109ac916_bs_ecc.bit --num_checks=2 --ic=2
    done

} 2>&1 | tee ~/logs/check_scrub_and_reflash_${H}_${timestamp}.log
