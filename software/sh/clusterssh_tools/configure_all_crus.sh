#!/bin/bash -x

SCRIPT_PATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

H=$(hostname -s)
timestamp=$(date +%Y%m%d_%H%M%S)

which o2-roc-config
if [[ $? -ne 0 ]]
then
    echo "Could not load o2-roc-config"
    exit 1
fi

which o2-roc-status
if [[ $? -ne 0 ]]
then
    echo "Could not load o2-roc-status"
    exit 1
fi

mkdir -p ~/logs

{
    for CARD in $(o2-roc-list-cards | grep CRU | awk '{print $4}' | sort -u)
    do
	    for EP in 0 1
        do
	        CONFIG_FILE="$(readlink -f ${SCRIPT_PATH}/../../config/roc_${H}_sn${CARD}_ep${EP}.cfg)"
	        o2-roc-config --config-uri=ini://${CONFIG_FILE} --id=${CARD}:${EP} --force-config --bypass-fw
	        o2-roc-status --id=${CARD}:${EP} --onu-status
        done
    done
} 2>&1 | tee ~/logs/cru_configuration_${H}_${timestamp}.log

