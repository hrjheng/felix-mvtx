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

cleanup_sub_rack 2>&1 | tee "${LOG_DIR}/${subrack}_verification_${timestamp}.log"

for s in "${staves[@]}"
do
    stavename=$(printf "%s_%02d" ${layer} ${s})
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

    #if [[ ! -f "${CNF_DIR}/powerunit_offsets/${stavename}.yml" ]]
    #then
    #	${testbench} print_pu_offsets_to_yml
    #fi

    cd "${PY_DIR}"
    RET=0
    {
	# block needed to combine the logs without add a | tee -a ${logfile} to every line
	echo "=== Stave ${stavename} ==="
	echo "=== POWERING ===="
	#${obtest} ${testpar} -t PowerOn
	#RET=$?
	#if [[ ${RET} -ne 0 ]]; then ${obtest} ${testpar} -t PowerOff ; exit ${RET}; fi
	echo "=== CONTROL ===="
	${obtest} ${testpar} -t Control
	RET=$?
	if [[ ${RET} -ne 0 ]]; then ${obtest} ${testpar} -t PowerOff ; exit ${RET}; fi
	# -----------------------------------------------------------------------------------------
	# dcol test
	echo "=== UNTUNED FAKE-HIT RATE ==="
	rm ${CNF_DIR}/mask_double_cols/"${stavename}".yml
	${obtest} ${testpar} -t DColTest
	RET=$?
	check_lock_counter "${logsubdir}"
	# -----------------------------------------------------------------------------------------
	# analyse fhr data
	hitmap[0]="${datsubdir}/${stavename}_feeid${fee_ids[0]}_dcol_test_${timestamp}.dat"
	hitmap[1]="${datsubdir}/${stavename}_feeid${fee_ids[1]}_dcol_test_${timestamp}.dat"
	logs[0]="${logsubdir}/${stavename}_feeid${fee_ids[0]}_dcol_test_${timestamp}.txt.gz"
	logs[1]="${logsubdir}/${stavename}_feeid${fee_ids[1]}_dcol_test_${timestamp}.txt.gz"
	plot="${pltsubdir}/${stavename}_dcol_test_${timestamp}_"
	raw="${rawsubdir}/${stavename}_dcol_test_${timestamp}.lz4"
	lz4cat "${rawdata}" | ${decoder} hitmap /dev/stdin "${fee_ids[0]}" 2>&1 | gzip -c > "${logs[0]}" &
	lz4cat "${rawdata}" | ${decoder} hitmap /dev/stdin "${fee_ids[1]}" 2>&1 | gzip -c > "${logs[1]}" &
	wait
	mv "hitmap${fee_ids[0]}.dat" "${hitmap[0]}"
	mv "hitmap${fee_ids[1]}.dat" "${hitmap[1]}"
	mv "${rawdata}" "${raw}"
	./plot_dcol_test.py -pe png ${ML} -f "${hitmap[0]}" -g "${hitmap[1]}" -o "${plot}" -y "${stavename}"
	# -----------------------------------------------------------------------------------------
	# fake hit scan
	echo "=== UNTUNED FAKE-HIT RATE ==="
	rm ${CNF_DIR}/noise_masks/"${stavename}".yml
	mv ${CNF_DIR}/vcasn/"${stavename}"{,-HIDE}.yml
	mv ${CNF_DIR}/ithr/"${stavename}"{,-HIDE}.yml
	${obtest} ${testpar} -t FakeHitScanSequencer
	RET=$?
	mv ${CNF_DIR}/vcasn/"${stavename}"{-HIDE,}.yml
	mv ${CNF_DIR}/ithr/"${stavename}"{-HIDE,}.yml
	check_lock_counter "${logsubdir}"
	# -----------------------------------------------------------------------------------------
	# analyse fhr data
	hitmap[0]="${datsubdir}/${stavename}_feeid${fee_ids[0]}_simple_readout_${timestamp}.dat"
	hitmap[1]="${datsubdir}/${stavename}_feeid${fee_ids[1]}_simple_readout_${timestamp}.dat"
	logs[0]="${logsubdir}/${stavename}_feeid${fee_ids[0]}_simple_readout_${timestamp}.txt.gz"
	logs[1]="${logsubdir}/${stavename}_feeid${fee_ids[1]}_simple_readout_${timestamp}.txt.gz"
	plot="${pltsubdir}/${stavename}_simple_readout_${timestamp}_"
	raw="${rawsubdir}/${stavename}_simple_readout_${timestamp}.lz4"
	lz4cat "${rawdata}" | ${decoder} hitmap /dev/stdin "${fee_ids[0]}" 2>&1 | gzip -c > "${logs[0]}" &
	lz4cat "${rawdata}" | ${decoder} hitmap /dev/stdin "${fee_ids[1]}" 2>&1 | gzip -c > "${logs[1]}" &
	wait
	mv "hitmap${fee_ids[0]}.dat" "${hitmap[0]}"
	mv "hitmap${fee_ids[1]}.dat" "${hitmap[1]}"
	mv "${rawdata}" "${raw}"
	./plot_fhr.py -pe png ${ML} -f "${hitmap[0]}" -g "${hitmap[1]}" -o "${plot}" -y "${stavename}" -r
	# -----------------------------------------------------------------------------------------
	# VCASN tuning scan
	echo "=== TUNE VCASN ===="
	${obtest} ${testpar} -t Tune
	RET=$?
	check_lock_counter "${logsubdir}"
	# -----------------------------------------------------------------------------------------
	# analyse tuning scan
	# tuned vcasn values are saved in ../config/vcasn/<layer>_<stave number>.yml
	hitmap[0]="${datsubdir}/${stavename}_feeid${fee_ids[0]}_vcasn_tuning_${timestamp}.dat"
	hitmap[1]="${datsubdir}/${stavename}_feeid${fee_ids[1]}_vcasn_tuning_${timestamp}.dat"
	logs[0]="${logsubdir}/${stavename}_feeid${fee_ids[0]}_vcasn_tuning_${timestamp}.txt.gz"
	logs[1]="${logsubdir}/${stavename}_feeid${fee_ids[1]}_vcasn_tuning_${timestamp}.txt.gz"
	plot="${pltsubdir}/${stavename}_vcasn_tuning_${timestamp}_"
	raw="${rawsubdir}/${stavename}_vcasn_tuning_${timestamp}.lz4"
	lz4cat "${rawdata}" | ${decoder} hitmap /dev/stdin "${fee_ids[0]}" 2>&1 | gzip -c > "${logs[0]}" &
	lz4cat "${rawdata}" | ${decoder} hitmap /dev/stdin "${fee_ids[1]}" 2>&1 | gzip -c > "${logs[1]}" &
	wait
	mv "hitmap${fee_ids[0]}.dat" "${hitmap[0]}"
	mv "hitmap${fee_ids[1]}.dat" "${hitmap[1]}"
	mv "${rawdata}" "${raw}"
	./plot_tune.py ${ML} -f "${hitmap[0]}" -g "${hitmap[1]}" -i "${NINJ}" -o "${plot}" -y "${stavename}"
	# ----------------------------------------------------------------------------------------
	# ITHR tuning scan
	echo "=== TUNE ITHR ===="
	${obtest} ${testpar} -t TuneITHR
	RET=$?
	check_lock_counter "${logsubdir}"
	# -----------------------------------------------------------------------------------------
	# analyse tuning scan
	# tuned vcasn values are saved in ../config/ithr/<layer>_<stave number>.yml
	hitmap[0]="${datsubdir}/${stavename}_feeid${fee_ids[0]}_ithr_tuning_${timestamp}.dat"
	hitmap[1]="${datsubdir}/${stavename}_feeid${fee_ids[1]}_ithr_tuning_${timestamp}.dat"
	logs[0]="${logsubdir}/${stavename}_feeid${fee_ids[0]}_ithr_tuning_${timestamp}.txt.gz"
	logs[1]="${logsubdir}/${stavename}_feeid${fee_ids[1]}_ithr_tuning_${timestamp}.txt.gz"
	plot="${pltsubdir}/${stavename}_ithr_tuning_${timestamp}_"
	raw="${rawsubdir}/${stavename}_ithr_tuning_${timestamp}.lz4"
	lz4cat "${rawdata}" | ${decoder} hitmap /dev/stdin "${fee_ids[0]}" 2>&1 | gzip -c > "${logs[0]}" &
	lz4cat "${rawdata}" | ${decoder} hitmap /dev/stdin "${fee_ids[1]}" 2>&1 | gzip -c > "${logs[1]}" &
	wait
	mv "hitmap${fee_ids[0]}.dat" "${hitmap[0]}"
	mv "hitmap${fee_ids[1]}.dat" "${hitmap[1]}"
	mv "${rawdata}" "${raw}"
	./plot_tune.py ${ML} -f "${hitmap[0]}" -g "${hitmap[1]}" -i "${NINJ}" -t -o "${plot}" -y "${stavename}"
	#-----------------------------------------------------------------------------------------
	# fake hit scan
	echo "=== TUNED FAKE-HIT RATE W/O MASKING ==="
	rm ${CNF_DIR}/noise_masks/${stavename}.yml # obtain noisy pixels now that chips are tuned
	${obtest} ${testpar} -t TunedFakeHitScanSequencer
	RET=$?
	check_lock_counter "${logsubdir}"
	# -----------------------------------------------------------------------------------------
	hitmap[0]="${datsubdir}/${stavename}_feeid${fee_ids[0]}_simple_readout_tuned_${timestamp}.dat"
	hitmap[1]="${datsubdir}/${stavename}_feeid${fee_ids[1]}_simple_readout_tuned_${timestamp}.dat"
	logs[0]="${logsubdir}/${stavename}_feeid${fee_ids[0]}_simple_readout_tuned_${timestamp}.txt.gz"
	logs[1]="${logsubdir}/${stavename}_feeid${fee_ids[1]}_simple_readout_tuned_${timestamp}.txt.gz"
	plot="${pltsubdir}/${stavename}_simple_readout_tuned_${timestamp}_"
	raw="${rawsubdir}/${stavename}_simple_readout_tuned_${timestamp}.lz4"
	lz4cat "${rawdata}" | ${decoder} hitmap /dev/stdin "${fee_ids[0]}" 2>&1 | gzip -c > "${logs[0]}" &
	lz4cat "${rawdata}" | ${decoder} hitmap /dev/stdin "${fee_ids[1]}" 2>&1 | gzip -c > "${logs[1]}" &
	wait
	mv "hitmap${fee_ids[0]}.dat" "${hitmap[0]}"
	mv "hitmap${fee_ids[1]}.dat" "${hitmap[1]}"
	mv "${rawdata}" "${raw}"
	./plot_fhr.py -pe png ${ML} -f "${hitmap[0]}" -g "${hitmap[1]}" -o "${plot}" -y "${stavename}" -r
	# -----------------------------------------------------------------------------------------
	# fake hit scan
	echo "=== FAKE-HIT RATE W/ MASKING ==="
	#git checkout ${CNF_DIR}/{noise_masks,mask_double_cols}/${stavename}.yml
	${obtest} ${testpar} -t TunedFakeHitScanSequencer
	RET=$?
	check_lock_counter "${logsubdir}"
	# -----------------------------------------------------------------------------------------
	# analyse fhr data
	hitmap[0]="${datsubdir}/${stavename}_feeid${fee_ids[0]}_tuned_fhr_${timestamp}.dat"
	hitmap[1]="${datsubdir}/${stavename}_feeid${fee_ids[1]}_tuned_fhr_${timestamp}.dat"
	logs[0]="${logsubdir}/${stavename}_feeid${fee_ids[0]}_tuned_fhr_${timestamp}.txt.gz"
	logs[1]="${logsubdir}/${stavename}_feeid${fee_ids[1]}_tuned_fhr_${timestamp}.txt.gz"
	plot="${pltsubdir}/${stavename}_tuned_fhr_${timestamp}_"
	raw="${rawsubdir}/${stavename}_tuned_fhr_${timestamp}.lz4"
	lz4cat "${rawdata}" | ${decoder} hitmap /dev/stdin "${fee_ids[0]}" 2>&1 | gzip -c > "${logs[0]}" &
	lz4cat "${rawdata}" | ${decoder} hitmap /dev/stdin "${fee_ids[1]}" 2>&1 | gzip -c > "${logs[1]}" &
	wait
	mv "hitmap${fee_ids[0]}.dat" "${hitmap[0]}"
	mv "hitmap${fee_ids[1]}.dat" "${hitmap[1]}"
	mv "${rawdata}" "${raw}"
	./plot_fhr.py -pe png ${ML} -f "${hitmap[0]}" -g "${hitmap[1]}" -o "${plot}" -y "${stavename}" 2>&1 > "${plot}log.txt" &
	# -----------------------------------------------------------------------------------------
	# threshold scan
	echo "=== THRESHOLD ==="
	${obtest} ${testpar} -t Threshold
	RET=$?
	check_lock_counter "${logsubdir}"
	# ${obtest} ${testpar} -t PowerOff
	# -----------------------------------------------------------------------------------------
	# analyse threshold scan data
	hitmap[0]="${datsubdir}/${stavename}_feeid${fee_ids[0]}_tuned_thr_${timestamp}.dat"
	hitmap[1]="${datsubdir}/${stavename}_feeid${fee_ids[1]}_tuned_thr_${timestamp}.dat"
	logs[0]="${logsubdir}/${stavename}_feeid${fee_ids[0]}_tuned_thr_${timestamp}.txt.gz"
	logs[1]="${logsubdir}/${stavename}_feeid${fee_ids[1]}_tuned_thr_${timestamp}.txt.gz"

	plot="${pltsubdir}/${stavename}_tuned_thr_${timestamp}_"
	raw="${rawsubdir}/${stavename}_tuned_thr_${timestamp}.lz4"
	lz4cat "${rawdata}" | ${decoder} hitmap /dev/stdin "${fee_ids[0]}" 2>&1 | gzip -c > "${logs[0]}" &
	lz4cat "${rawdata}" | ${decoder} hitmap /dev/stdin "${fee_ids[1]}" 2>&1 | gzip -c > "${logs[1]}" &
	wait
	mv "hitmap${fee_ids[0]}.dat" "${hitmap[0]}"
	mv "hitmap${fee_ids[1]}.dat" "${hitmap[1]}"
	mv "${rawdata}" "${raw}"
	./plot_ths.py ${ML} -f "${hitmap[0]}" -g "${hitmap[1]}" -o "${plot}" -i "${NINJ}" -sr "${STEP_ROWS}" -mc "${MAX_CHARGE}" -n "${stavename}" 2>&1 > "${plot}log.txt" &
	# -----------------------------------------------------------------------------------------
	echo "====="
	echo "====="
	echo "====="
    } 2>&1 | tee -a "${logfile}"
    wait
    gzip "${logfile}"
    cp -r "${PY_DIR}/logs/${stavename}_${timestamp}/"* "${logsubdir}/"
done
