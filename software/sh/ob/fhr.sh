#!/bin/bash -x

### BASH settings
# sets exit code ($?) to the last non-zero exit code. Needed for scrip to exit on python script exit codes and not piped exit code.
set -o pipefail

READOUTCARD_VER="its-consistency-patch-1"

### PATHS
SH_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
C_DIR=$(readlink -f "${SH_DIR}/../../c")
PY_DIR=$(readlink -f "${SH_DIR}/../../py")
CNF_DIR=$(readlink -f "${SH_DIR}/../../config")
DAT_DIR="/home/its/data/ob_comm/hitmaps"
LOG_DIR="/home/its/data/ob_comm/logs"
PLT_DIR="/home/its/data/ob_comm/plots"
RAW_DIR="/home/its/data/ob_comm/raw"


mkdir -p "${DAT_DIR}" "${LOG_DIR}" "${PLT_DIR}"

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

cleanup_sub_rack 2>&1 | tee "${LOG_DIR}/${subrack}_verification_${timestamp}.log"

stavename="${subrack}"

logsubdir="${LOG_DIR}/${stavename}_${timestamp}"
datsubdir="${DAT_DIR}/${stavename}_${timestamp}"
pltsubdir="${PLT_DIR}/${stavename}_${timestamp}"
rawsubdir="${RAW_DIR}/${stavename}_${timestamp}"
mkdir -p "${logsubdir}"
mkdir -p "${datsubdir}"
mkdir -p "${pltsubdir}"
mkdir -p "${rawsubdir}"
logfile="${logsubdir}/verification.log"
git log -1 >> ${logsubdir}/git_log.txt
git diff >> ${logsubdir}/git_diff.txt
git status >> ${logsubdir}/git_status.txt

# setup parameters
testpar="-c ${config} -s "${staves[@]}" -v True -p ${stavename}_${timestamp}/"

echo ${testpar}

cd "${PY_DIR}"
RET=0
{
    echo "=== Stave ${stavename} ==="
    # -----------------------------------------------------------------------------------------
    #fake hit scan.
    ${testbench} ltu send_eoc    
    echo "=== FAKE-HIT RATE==="
    ${obtest} ${testpar} -t TunedFakeHitScan
    RET=$?
    check_lock_counter "${logsubdir}"
    raw="${rawsubdir}/${stavename}_tuned_fhr_${timestamp}.lz4"
    mv "${rawdata}" "${raw}"
    if [[ ${RET} -ne 0 ]]; then exit ${RET}; fi
    # -----------------------------------------------------------------------------------------
    echo "=== Plotting fake hit data ==="
    cd "${SH_DIR}"
    wait
    ./decode_subrack.sh "${subrack}" "${timestamp}"
    wait
    ./plot_subrack.sh "${subrack}" "${timestamp}"
    wait
    # -----------------------------------------------------------------------------------------
    cd "${PY_DIR}"
    wait
    echo "====="
    echo "====="
    echo "====="
} 2>&1 | tee -a "${logfile}"
