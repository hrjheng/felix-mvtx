#!/bin/bash -x

### BASH settings
# sets exit code ($?) to the last non-zero exit code. Needed for scrip to exit on python script exit codes and not piped exit code.
set -o pipefail

### CONFIGURATION
test_identifier=simple_readout


### PATHS
SH_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
C_DIR=$(readlink -f "${SH_DIR}/../../c")
PY_DIR=$(readlink -f "${SH_DIR}/../../py")
DAT_DIR="/home/its/data/ob_comm/hitmaps"
LOG_DIR="/home/its/data/ob_comm/logs"
PLT_DIR="/home/its/data/ob_comm/plots"
RAW_DIR="/home/its/data/ob_comm/raw"

mkdir -p "${DAT_DIR}" "${LOG_DIR}" "${PLT_DIR}"

decoder=${C_DIR}/decoder

# compile the decoder
if [ ! -f "${decoder}" ]
then
    cd "${C_DIR}"
    make
    if [ ! -f "${decoder}" ]
    then
	exit 2
    fi
fi

if [ ! -d "${RAW_DIR}" ]
then
    echo "Did not find the raw data directory"
    exit 3
fi

script_timestamp=$(date +%Y%m%d_%H%M%S)


cd ${PY_DIR}
{
    for l in $(seq 3 6)
    do
	for s in $(seq 0 47)
	do
	    stavename=$(printf "L%d_%02d" ${l} ${s})
	    raw=$(find ${RAW_DIR} -name "${stavename}*${test_identifier}*" | sort | tail -n1)
	    if [[ -f ${raw} ]]
	    then
		timestamp="TODO"

		datsubdir="${DAT_DIR}/${stavename}_${timestamp}_reprocessing_${test_identifier}"
		pltsubdir="${PLT_DIR}/${stavename}_${timestamp}_reprocessing_${test_identifier}"
		mkdir -p ${datsubdir}
		mkdir -p ${pltsubdir}

		hitmap[0]="${datsubdir}/${stavename}_feeid${fee_ids[0]}_${test_identifier}_${timestamp}.dat"
		hitmap[1]="${datsubdir}/${stavename}_feeid${fee_ids[1]}_${test_identifier}_${timestamp}.dat"

		fee_id=$(( $(( $(( l & 0x7 )) << 12  )) | $(( s & 0x3F )) ))
		fee_ids=( ${fee_id} $(( fee_id | $(( 0x1 << 8 )) )) )

		lz4cat "${raw}" | ${decoder} hitmap /dev/stdin "${fee_ids[0]}" &
		lz4cat "${raw}" | ${decoder} hitmap /dev/stdin "${fee_ids[1]}" &
		wait
		plot="${pltsubdir}/${stavename}_simple_readout_${timestamp}_"
		mv "hitmap${fee_ids[0]}.dat" "${hitmap[0]}"
		mv "hitmap${fee_ids[1]}.dat" "${hitmap[1]}"

		./plot_fhr.py -pe png ${ML} -f "${hitmap[0]}" -g "${hitmap[1]}" -o "${plot}" -y "${stavename}"
	    else
		stavename_old=$(printf "L%d_%d" ${l} ${s})
		raw=$(find ${RAW_DIR} -name "${stavename_old}*${test_identifier}*" | sort | tail -n1)
		if [[ -f ${raw} ]]
		then
		    timestamp="TODO"

		    datsubdir="${DAT_DIR}/${stavename_old}_${timestamp}_reprocessing_${test_identifier}"
		    pltsubdir="${PLT_DIR}/${stavename_old}_${timestamp}_reprocessing_${test_identifier}"
		    mkdir -p ${datsubdir}
		    mkdir -p ${pltsubdir}

		    hitmap[0]="${datsubdir}/${stavename_old}_feeid${fee_ids[0]}_${test_identifier}_${timestamp}.dat"
		    hitmap[1]="${datsubdir}/${stavename_old}_feeid${fee_ids[1]}_${test_identifier}_${timestamp}.dat"

		    fee_id=$(( $(( $(( l & 0x7 )) << 12  )) | $(( s & 0x3F )) ))
		    fee_ids=( ${fee_id} $(( fee_id | $(( 0x1 << 8 )) )) )

		    lz4cat "${raw}" | ${decoder} hitmap /dev/stdin "${fee_ids[0]}" &
		    lz4cat "${raw}" | ${decoder} hitmap /dev/stdin "${fee_ids[1]}" &
		    wait
		    plot="${pltsubdir}/${stavename_old}_simple_readout_${timestamp}_"
		    mv "hitmap${fee_ids[0]}.dat" "${hitmap[0]}"
		    mv "hitmap${fee_ids[1]}.dat" "${hitmap[1]}"

		    ./plot_fhr.py -pe png ${ML} -f "${hitmap[0]}" -g "${hitmap[1]}" -o "${plot}" -y "${stavename}"
		fi
	    fi
	done
    done
} 2>&1 | tee -a "${PY_DIR}/logs/reprocess_$(hostname -s)_${script_timestamp}.log"
