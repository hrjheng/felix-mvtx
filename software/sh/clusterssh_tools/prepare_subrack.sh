#!/bin/bash -x

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
     "alio2-cr1-flp191")
        subracks=( "l3b_pp1i5_pp1o5" "l3t_pp1i2_pp1o2" )
        ;;
    "alio2-cr1-flp192")
        subracks=( "l4ti_pp1i2" "l4to_pp1o2" )
        ;;
    "alio2-cr1-flp193")
        subracks=( "l4bi_pp1i5" "l4bo_pp1o5" )
        ;;
    "alio2-cr1-flp194")
        subracks=( "l5ti_pp1i1" "l5to_pp1o1" )
        ;;
    "alio2-cr1-flp195")
        subracks=( "l5bi_pp1i6" "l5bo_pp1o6" )
        ;;
    "alio2-cr1-flp196")
        subracks=( "l6ti_pp1i0" "l6to_pp1o0" )
        ;;
    "alio2-cr1-flp197")
        subracks=( "l6bi_pp1i7" "l6bo_pp1o7" )
        ;;

esac

which o2-readout-exe
if [[ $? -ne 0 ]]
then
    echo "Could not load o2-readout-exe"
    exit 1
fi
python3 <<EOF
import libO2Lla
EOF
if [[ $? -ne 0 ]]
then
    echo "Could not load the LLA library into python3"
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
        ${testbench} info_for_log_entry
	echo -e "\n\nLogging all gbtx status after configuration: \n" 
	${testbench} log_all_gbtx_status
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
