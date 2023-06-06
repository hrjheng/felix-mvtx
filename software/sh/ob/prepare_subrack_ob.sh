#!/bin/bash

### PATHS
SH_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
C_DIR=$(readlink -f "${SH_DIR}/../../c")
PY_DIR=$(readlink -f "${SH_DIR}/../../py")
CNF_DIR=$(readlink -f "${SH_DIR}/../../config")
LOG_DIR="${PY_DIR}/logs"

mkdir -p "${LOG_DIR}"

. ${SH_DIR}/common.sh # load common functions

get_sub_rack ${1}
obtest=${PY_DIR}/obtest.py
decoder=${C_DIR}/decoder

timestamp=$(date +%Y%m%d_%H%M%S)

echo "Layer: ${layer}"
echo "Staves: " "${staves[@]}"
echo "Timestamp: ${timestamp}"

check_folders
compile_decoder ${decoder}


##########################################################################################
### START EXECUTION ######################################################################
##########################################################################################
set_up_env

{
    o2-roc-list-cards
    for i in $(seq 0 3)
    do
	echo "# o2-roc-status --id=#${i} --onu-status:"
	o2-roc-status --id=#${i} --onu-status
    done

    # setup the sub-rack
    ${testbench} cru initialize
    ${testbench} initialize_all_rdos    # change GBTx charge pump setting (potential glitch on clock to detector / CANbus)
    sleep 1                             # let the FPGA recover
    ${testbench} cru initialize         # clean up the CRU
    ${testbench} version
    ${testbench} feeid
    ${testbench} dna
    ${testbench} reset_all_temp_interlocks # configure the interlocks according to the stave type

    ${testbench} initialize_all_gbtx12 # activate the second GBT link
    ${testbench} clean_all_datapaths
    ${testbench} info_for_log_entry

    ${testbench} feeid

    o2-roc-list-cards
    for i in $(seq 0 3)
    do
	echo "# o2-roc-status --id=#${i} --onu-status:"
	o2-roc-status --id=#${i} --onu-status
    done
} 2>&1 | tee "${LOG_DIR}/${subrack}_preparation_${timestamp}.log"
