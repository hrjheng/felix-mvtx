#!/bin/bash -x
#
##############################################################################################################
# verify multiple staves in a subrack. uses vcasn, ithr and mask_double_column yml files which already exist #
##############################################################################################################

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

cmd=${2}
if [[ -z ${cmd+x} ]]
then
    echo "Please specify the obtest.py command to be executed"
    exit 1
fi

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

stavename="${subrack}_${cmd}"

logsubdir="${LOG_DIR}/${stavename}_${timestamp}"
mkdir -p "${logsubdir}"
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
    ${obtest} ${testpar} -t ${cmd}
    wait
    echo "====="
    echo "====="
    echo "====="
} 2>&1 | tee -a "${logfile}"

