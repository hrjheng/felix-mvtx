#!/bin/bash

### PATHS
SH_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PY_DIR=$(readlink -f "${SH_DIR}/../../py")

flp=$(hostname -s)
timestamp=$(date +%Y%m%d_%H%M%S)

mkdir -p ~/logs

case ${flp} in
    "alio2-cr1-flp187")
        subracks=( "l0b_pp1o4" "l0t_pp1i3" )
        ;;
    "alio2-cr1-flp188")
        subracks=( "l1b_pp1o4" "l1t_pp1i3" )
        ;;
    "alio2-cr1-flp189")
        subracks=( "l2ti_pp1i4" "l2to_pp1i4" )
        ;;
    "alio2-cr1-flp190")
        subracks=( "l2bi_pp1o3" "l2bo_pp1o3" )
        ;;
esac

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
    o2-roc-list-cards
    for i in $(seq 0 3)
    do
	echo "# o2-roc-status --id=#${i} --onu-status:"
        o2-roc-status --id=#${i} --onu-status
    done
    for subrack in "${subracks[@]}"
    do
        testbench=${PY_DIR}/testbench_${subrack}.py

        # setup the sub-rack
        ${testbench} cru initialize
        ${testbench} initialize_all_rdos    # change GBTx charge pump setting (potential glitch on clock to detector / CANbus)
        sleep 1                             # let the FPGA recover
        ${testbench} program_all_xcku
        ${testbench} cru initialize         # clean up the CRoU
        ${testbench} version
        ${testbench} feeid
        ${testbench} dna
        ${testbench} reset_all_temp_interlocks # configure the interlocks according to the stave type

        echo "First time initialize_all_gbtx12"
        ${testbench} initialize_all_gbtx12 # activate the second GBT link
        echo "Second time initialize_all_gbtx12"
        ${testbench} initialize_all_gbtx12 # activate the second GBT link
        ${testbench} clean_all_datapaths
        ${testbench} info_for_log_entry # cannot be executed currently
        #echo "Enabling scrubbing after the log entry was generated:"
        #${testbench} enable_all_scrubbing  # activate scrubbing
        #echo "Scrubbing activated"
    done
    o2-roc-list-cards
    for i in $(seq 0 3)
    do
	echo "# o2-roc-status --id=#${i} --onu-status:"
        o2-roc-status --id=#${i} --onu-status
    done
} 2>&1 | tee "~/logs/${flp}_preparation_${timestamp}.log"
