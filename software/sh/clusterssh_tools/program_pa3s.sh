#!/bin/bash

H=$(hostname)
timestamp=$(date +%Y%m%d_%H%M%S)

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

git submodule update --init --recursive

for tb in $(grep -rnH "\"${H}\"" ../../config/*.yml | grep -v "LTU" | cut -d':' -f1 | cut -d'/' -f4 | cut -d'.' -f1)
do
    ../../py/${tb}.py initialize_boards
done

sleep 2

mkdir -p ~/logs

cd ../../cpp/pa3_programming/
{
make
echo "========= EP 0 ========="
./pa3jtag -a PROGRAM -f ~/RU_bitfiles/RU_auxFPGA/v02.0D/RU_auxFPGA_v020D_221017_1558_171751e.dat -e 0
echo "========= EP 1 ========="
./pa3jtag -a PROGRAM -f ~/RU_bitfiles/RU_auxFPGA/v02.0D/RU_auxFPGA_v020D_221017_1558_171751e.dat -e 1
echo "========= EP 2 ========="
./pa3jtag -a PROGRAM -f ~/RU_bitfiles/RU_auxFPGA/v02.0D/RU_auxFPGA_v020D_221017_1558_171751e.dat -e 2
echo "========= EP 3 ========="
./pa3jtag -a PROGRAM -f ~/RU_bitfiles/RU_auxFPGA/v02.0D/RU_auxFPGA_v020D_221017_1558_171751e.dat -e 3
} 2>&1 | tee pa3_programming_${H}_${timestamp}.log
cd ../../sh/clusterssh_tools

sleep 2

{
    for tb in $(grep -rnH "\"${H}\"" ../../config/*.yml | grep -v "LTU" | cut -d':' -f1 | cut -d'/' -f4 | cut -d'.' -f1)
    do
        echo "========= ${tb} ========="
        ../../py/${tb}.py initialize_boards
        ../../py/${tb}.py reset_all_pa3 --force=True
        ../../py/${tb}.py program_all_xcku
        ../../py/${tb}.py info-for-log-entry
    done
} 2>&1 | tee ~/logs/pa3_programming_${H}_${timestamp}.log
