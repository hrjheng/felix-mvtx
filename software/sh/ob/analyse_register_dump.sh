#!/bin/bash

##########################################################################################
### FUNCTIONS ############################################################################
##########################################################################################
analyse_verification_folder() {
    local LOG_FOLDER="$1"
    local PREV_FOLDER="$(pwd)"
    cd "${LOG_FOLDER}"
    for dir in $(find "${LOG_FOLDER}" -name "*202*" -type d | grep -v gz)
    do
	cd "${dir}"
	pwd
	for i in $(seq 0 23)
	do
	    if [[ -f rdo_${i}_alpide_config_start_of_run ]] && [[ -f rdo_${i}_alpide_config_end_of_run ]] && [[ -f daq_test.log ]]
	    then
		## Triggers / Frame Counter
		TRIGGERS_SENT=$(grep "Triggers Sent" daq_test.log | tail -n1 | awk '{print $3}')
		TRIGGERS_SENT_OVERFLOW=$(python -c "print(${TRIGGERS_SENT} % 0xFFFF)")

		MEDIAN_FC=$(grep FrameCounter rdo_${i}_alpide_config_end_of_run | cut -d':' -f2 | sort | uniq -c | sort -rn | head -n1 | tr -s ' ' | cut -d' ' -f3)
		MEDIAN_FC_DEC=$(python -c "print(int("${MEDIAN_FC}"))")

		MEDIAN_TC=$(grep TriggerCounter rdo_${i}_alpide_config_end_of_run | cut -d':' -f2 | sort | uniq -c | sort -rn | head -n1 | tr -s ' ' | cut -d' ' -f3)
		MEDIAN_TC_DEC=$(python -c "print(int("${MEDIAN_TC}"))")

		echo "### Most frequent Frame Counter: ${MEDIAN_FC} / ${MEDIAN_FC_DEC}"
		if [[ "${MEDIAN_TC}" -ne "${MEDIAN_FC}" ]]
		then
		    echo "### Mismatch of most frequent Frame Counter and Trigger Counter: ${MEDIAN_TC} / ${MEDIAN_TC_DEC}"
		fi
		echo "### Trigers sent: ${TRIGGERS_SENT} / truncated to 16 bit: ${TRIGGERS_SENT_OVERFLOW}"
		if [[ ${TRIGGERS_SENT_OVERFLOW} -ne ${MEDIAN_TC_DEC} ]]
		then
		    echo "### Mismatch of triggers and trigger counter!!"
		fi
		egrep "FrameCounter|-- Alpide configuration of chip" rdo_${i}_alpide_config_end_of_run | grep -v "${MEDIAN_FC}" | grep FrameCounter -B1
		egrep "FrameCounter|-- Alpide configuration of chip" rdo_${i}_alpide_config_end_of_run | grep -v "${MEDIAN_FC}" | grep FrameCounter -B1

		# Lock Counter
		egrep -n "of chip|LockCounter" rdo_${i}_alpide_config_end_of_run | grep -v 0X0 > LockCounterEOR
		egrep -n "of chip|LockCounter" rdo_${i}_alpide_config_start_of_run | grep -v 0X0 > LockCounterSOR
		if [[ "$(diff LockCounter* -c | grep "\!" -B1 | wc -l )" -ne 0 ]]
		then
		    echo "### LOCK COUNTER DIFFERENCES ###"
		    diff LockCounter* -c | grep "\!" -B1
		    echo "### ###"
		fi

		# Frame Extended
		FE_CNT=$(grep "FrameExtended" rdo_${i}_alpide_config_start_of_run | grep -v 0X0 | wc -l)
		if [[ ${FE_CNT} -gt 16 ]]
		then
		    echo "### FrameExtended found in ${FE_CNT} chips at Start of Run!!"
		else
		    egrep "FrameExtended|-- Alpide configuration of chip" rdo_${i}_alpide_config_start_of_run | grep -v 0X0 | grep FrameExtended -B1
		fi

		FE_CNT=$(grep "FrameExtended" rdo_${i}_alpide_config_end_of_run | grep -v 0X0 | wc -l)
		if [[ ${FE_CNT} -gt 16 ]]
		then
		    echo "### FrameExtended found in ${FE_CNT} chips at Start of Run!!"
		else
		    egrep "FrameExtended|-- Alpide configuration of chip" rdo_${i}_alpide_config_end_of_run | grep -v 0X0 | grep FrameExtended -B1
		fi
	    fi
	done
    done
    cd "${PREV_FOLDER}"
}


LOG=post_analysis.log
for f in $(find ../py/logs/ -name "verification.log" | grep "L5_28" | sort  )
do
    d="$(readlink -f "$(dirname "${f}")")"
    #d="$(readlink -f ${d})"
    echo "$d"
    analyse_verification_folder "$d"
done 2>&1 | tee ${LOG}
