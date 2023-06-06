#!/bin/bash

if [ $# -lt 1 ]
then
    DIR=./
elif [ $# -eq 1 ]
then
    DIR=$1
else
    DIR=$1
    STAVE_ARG=$2
fi

DIR=$(readlink -f "${DIR}")
cd "$DIR" || exit

for f in *.log
do
    #f=L6_0_verification_20200305_105038.log
    [[ -e "$f" ]] || break

    stave=$(head -n1 "${f}" | grep "===" | awk '{print $3}')

    [[ ${#stave} -lt 0 ]] && echo "No stave recognized!" && continue
    [[ ${#STAVE_ARG} -gt 0 ]] && [[ "${stave}" != "${STAVE_ARG}" ]] && continue # different stave requested
    echo "${f}"
    echo "${stave}"

    grep "run_info" "${f}" | grep Test

    excl_chips=$(grep "excluded chipid from config" "${f}" | cut -d'[' -f2 | cut -d']' -f1)
    echo "=== Excluded chips: ${excl_chips}"

    echo "=== Chips failing the control test:"
    grep "Test Chips" "${f}" -A1 | grep -v "Done. Errors: 0" | grep "Done. Errors" -B1
    echo "==="
    
    grep "Could not align all transceivers" "${f}"
    grep ": No delay found" "${f}"
    #grep "Transceiver" "${f}" | grep -v ": No delay found" | cut -d':' -f8 | cut -d')' -f1

    #grep "Triggers Sent:" "${f}" | grep -v "Echoed: 0, Gated: 0"
    grep "Events GPIO:" "${f}" | grep -v "EventErrors: 0, DecodeErrors: 0, OotErrors: 0"
    #grep "WARNING Trigger FIFO full:" -A31 ${f}

    grep "INFO - Read Values" -A34 "${f}" | grep RU -A33 | grep Triggers -A32 | grep WARNING
    exit 1
done
