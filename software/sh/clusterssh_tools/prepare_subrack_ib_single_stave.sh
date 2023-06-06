#!/bin/bash

### PATHS
SH_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PY_DIR=$(readlink -f "${SH_DIR}/../../py")

flp=$(hostname -s)
case ${flp} in
    "alio2-cr1-flp187")
        subracks=( "l0b_pp1o4" "l0t_pp1i3" )
        ;;
    "alio2-cr1-flp188")
        subracks=( "l1b_pp1o4" "l1t_pp1i3" )
        ;;
    "alio2-cr1-flp189")
        subracks=( "l2ti_pp1i4" "l2to_pp1i4" )
        ;;
    "alio2-cr1-flp190")
        subracks=( "l2bi_pp1o3" "l2bo_pp1o3" )
        ;;
esac

which o2-readout-exe
if [[ $? -ne 0 ]]
then
    echo "Could not load o2-readout-exe"
    exit 1
fi
python3.9 <<EOF
import libO2Lla
EOF
if [[ $? -ne 0 ]]
then
    echo "Could not load the LLA library into python3.9"
    exit 1
fi

echo -e "List of available subracks on this FLP:\n"
echo ${subracks[0]}
echo ${subracks[1]}

echo -e "\nChoose a subrack: \t"
read singlesubrack
echo -e "\nList of RDOS <-> Stave ID:\n"
testbench=${PY_DIR}/testbench_${singlesubrack}.py
${testbench} feeid
echo -e "\nChoose a rdo: \t"
read rdoid

${testbench} cru initialize ${rdoid}
${testbench} rdos ${rdoid} initialize 
sleep 1
${testbench} cru initialize ${rdoid}
${testbench} reset_temp_interlock
${testbench} rdos ${rdoid} initialize_gbtx12
${testbench} rdos ${rdoid} clean_datapath
