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

### PARAMETER: sub-rack
if [ $# -ne 2 ]
then
    echo "Please specify sub-rack and timestamp as parameters: e.g. pp1i1 <timestamp>"
    exit 1
else
    subrack=$1
    timestamp=$2
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

set_up_env

rawsubdir="${RAW_DIR}/${subrack}_${timestamp}"
raw="${rawsubdir}/${subrack}_data.lz4"

cd ${PY_DIR}
for s in "${staves[@]}"
do
    stavename="${layer}_${s}"
    if [ ${s} -lt 10 ]
    then
	stavename="${layer}_0${s}"
    fi

    logsubdir="${LOG_DIR}/${stavename}_${timestamp}"
    mkdir -p "${logsubdir}"
    logstring="${logsubdir}/${stavename}_stave_plotter_${timestamp}.txt"

    datsubdir="${DAT_DIR}/${subrack}_${timestamp}/${stavename}_${timestamp}"
    pltsubdir="${PLT_DIR}/${subrack}_${timestamp}/${stavename}_${timestamp}"
    plot="${pltsubdir}/${stavename}_tuned_fhr_${timestamp}_"
    mkdir -p "${pltsubdir}"

    l=${layer:1}
    fee_id=$(( $(( $(( l & 0x7 )) << 12  )) | $(( s & 0x3F )) ))
    fee_ids=( ${fee_id} $(( fee_id | $(( 0x1 << 8 )) )) )

    ./plot_fhr.py -f "${datsubdir}/hitmap_${stavename}_feeid_${fee_ids[0]}.dat" -g "${datsubdir}/hitmap_${stavename}_feeid_${fee_ids[1]}.dat" -y "${stavename}" -o "${plot}" -r > "${logstring}" 2>&1 &
    wait
done
