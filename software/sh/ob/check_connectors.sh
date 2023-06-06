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

cleanup_sub_rack  2>&1 | tee "${LOG_DIR}/${subrack}_verification_${timestamp}.log"

for s in "${staves[@]}"
do
    stavename="${layer}_${s}"
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

    # GET CONFIGURATION
    NINJ=$(grep "NINJ" "${config}" | tr -d ' ' | cut -d'=' -f2)
    STEP_ROWS=$(grep "STEP_ROWS" "${config}" | tr -d ' ' | cut -d'=' -f2)
    MAX_CHARGE=$(grep "END_CHARGE" "${config}" | tr -d ' ' | cut -d'=' -f2)

    l=${layer:1}
    fee_id=$(( $(( $(( l & 0x7 )) << 12  )) | $(( s & 0x3F )) ))
    fee_ids=( ${fee_id} $(( fee_id | $(( 0x1 << 8 )) )) )

    # setup parameters
    testpar="-c ${config} -s ${s} -v True -p ${stavename}_${timestamp}/"

    cd "${PY_DIR}"
    RET=0
    {
	# block needed to combine the logs without add a | tee -a ${logfile} to every line
	echo "=== Stave ${stavename} ==="
	echo "=== POWERING ===="
	${obtest} ${testpar} -t PowerOn
	RET=$?
	if [[ ${RET} -ne 0 ]]; then ${obtest} ${testpar} -t PowerOff ; exit ${RET}; fi
	echo "=== CONTROL ===="	
	${obtest} ${testpar} -t Control
	RET=$?
	if [[ ${RET} -ne 0 ]]; then ${obtest} ${testpar} -t PowerOff ; exit ${RET}; fi
		# -----------------------------------------------------------------------------------------
	# fake hit scan
	echo "=== UNTUNED FAKE-HIT RATE ==="
	mv ../config/vcasn/"${stavename}"{,-HIDE}.yml
	mv ../config/ithr/"${stavename}"{,-HIDE}.yml
	${obtest} ${testpar} -t FakeHitScan
	RET=$?
	check_lock_counter "${logsubdir}"
	mv ../config/vcasn/"${stavename}"{-HIDE,}.yml
	mv ../config/ithr/"${stavename}"{-HIDE,}.yml
	# -----------------------------------------------------------------------------------------
	${obtest} ${testpar} -t PowerOff
	#${obtest} ${testpar} -t PowerOn
	echo "====="
	echo "====="
	echo "====="
    } 2>&1 | tee -a "${logfile}"
done
