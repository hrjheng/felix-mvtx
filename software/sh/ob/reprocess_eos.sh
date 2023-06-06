#!/bin/bash -x

SH_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PY_DIR=$(readlink -f "${SH_DIR}/../../py")

script_timestamp=$(date +%Y%m%d_%H%M%S)

NCORES=16

HITMAPS="/eos/project/a/alice-its-commissioning/OuterBarrel/verification/2nd_attempt/hitmaps/"
[ ! -d ${HITMAPS}  ] && exit 1
WORKINGDIR="/eos/project/a/alice-its-commissioning/OuterBarrel/verification/2nd_attempt/reprocessing/${script_timestamp}"
mkdir -p ${WORKINGDIR}
[ ! -d ${WORKINGDIR}  ] && exit 1

types=( "simple_readout_tuned" "tuned_fhr" )



list_simple_tuned=${WORKINGDIR}/simple_readout_tuned.txt
list_tuned_fhr=${WORKINGDIR}/tuned_fhr.txt

#find /eos/project/a/alice-its-commissioning/OuterBarrel/verification/2nd_attempt/hitmaps/ -name "*simple_readout_tuned*" | tee ${list_simple_tuned}
#find /eos/project/a/alice-its-commissioning/OuterBarrel/verification/2nd_attempt/hitmaps/ -name "*tuned_fhr*" | tee ${list_tuned_fhr}

count=0
cd ${PY_DIR}
{
    for t in "${types[@]}"
    do
        list="${WORKINGDIR}/${t}.txt"
        find ${HITMAPS} -name "*${t}*" | sort > ${list}    
        for l in $(seq 3 6)
        do
            if [ $l -lt 5 ]
            then
                ML="-ml"
            else
                ML=""
            fi
	        for s in $(seq 0 47)
	        do
	            stavename=$(printf "L%d_%02d" ${l} ${s})
                [[ $(grep ${stavename} ${list} | wc -l) -lt 2 ]] && echo "Did not find two files!"
                grep ${stavename} ${list} | tail -n1 
                folder="$(dirname $(grep ${stavename} ${list} | tail -n1 ))"
                [ -z "${folder}" ] && continue
                [ ! -d "${folder}" ] && continue
                [[ $(grep ${folder} ${list} | wc -l) -lt 2 ]] && echo "Did not find two files!"
                echo ${folder}
                outfolder="${folder}/${stavename}_${t}_reprocessing_${script_timestamp}/"
                outfolder=${outfolder/hitmaps/plots}
                echo ${outfolder} >> ${WORKINGDIR}/reprocessing_eos_${script_timestamp}_${t}_folders.txt
                mkdir -p "${outfolder}"

                plot="${outfolder}/${stavename}_${t}_reprocessing_${script_timestamp}_"

		        hitmap[0]="$(grep ${folder##*/} ${list} | tail -n2 | head -n1 )"
		        hitmap[1]="$(grep ${folder##*/} ${list} | tail -n1 )"
                
                #echo ${hitmap[0]}
                #echo ${hitmap[1]}

		        ./plot_fhr.py -pe png ${ML} -f "${hitmap[0]}" -g "${hitmap[1]}" -o "${plot}" -y "${stavename}" > ${outfolder}/plotting.log 2>&1  &
                count=$((count + 1))
                if [[ ${count} -eq ${NCORES} ]]
                then
                    echo "launched ${NCORES} plotting processes."
                    wait
                    count=0
                fi
            done
        done
        wait
        for d in $(cat ${WORKINGDIR}/reprocessing_eos_${script_timestamp}_${t}_folders.txt )
        do
            cat ${d}/*__working_point.txt >> ${WORKINGDIR}/reprocessing_eos_${script_timestamp}_${t}_working_point.txt
        done
    done
} 2>&1 | tee ${WORKINGDIR}/reprocessing_eos_${script_timestamp}.txt


