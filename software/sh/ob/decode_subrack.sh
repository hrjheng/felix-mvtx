#!/bin/bash -x

### BASH settings
# sets exit code ($?) to the last non-zero exit code. Needed for scrip to exit on python script exit codes and not piped exit code.
set -o pipefail

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

rawsubdir="${RAW_DIR}/${subrack}_${timestamp}"
#raw="${rawsubdir}/${subrack}_tuned_fhr_${timestamp}.lz4"
raw="${rawsubdir}/${subrack}_data.lz4"
for s in "${staves[@]}"
do
    l=${layer:1}
    fee_id=$(( $(( $(( l & 0x7 )) << 12  )) | $(( s & 0x3F )) ))
    fee_ids=( ${fee_id} $(( fee_id | $(( 0x1 << 8 )) )) )

    logsubdir="${LOG_DIR}/${stavename}_${timestamp}"
    mkdir -p "${logsubdir}"
    logs[0]="${logsubdir}/${stavename}_feeid${fee_ids[0]}_decode_${timestamp}.txt"
    logs[1]="${logsubdir}/${stavename}_feeid${fee_ids[1]}_decode_${timestamp}.txt"

    lz4cat "${raw}" | ${decoder} hitmap /dev/stdin "${fee_ids[0]}" > "${logs[0]}" 2>&1 &
    lz4cat "${raw}" | ${decoder} hitmap /dev/stdin "${fee_ids[1]}" > "${logs[1]}" 2>&1 &
done

echo "Decoding lz4..."
echo "Stave numbers " "${staves[@]}"
wait

for s in "${staves[@]}"
do
    stavename="${layer}_${s}"
    if [ ${s} -lt 10 ]
    then
	stavename="${layer}_0${s}"
    fi

    datsubdir="${DAT_DIR}/${subrack}_${timestamp}/${stavename}_${timestamp}"
    mkdir -p "${datsubdir}"
    
    l=${layer:1}
    fee_id=$(( $(( $(( l & 0x7 )) << 12  )) | $(( s & 0x3F )) ))
    fee_ids=( ${fee_id} $(( fee_id | $(( 0x1 << 8 )) )) )
    mv "hitmap${fee_ids[0]}.dat" "${datsubdir}/hitmap_${stavename}_feeid_${fee_ids[0]}.dat"
    mv "hitmap${fee_ids[1]}.dat" "${datsubdir}/hitmap_${stavename}_feeid_${fee_ids[1]}.dat" 
done

