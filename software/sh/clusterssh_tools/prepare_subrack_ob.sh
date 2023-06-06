### PATHS
SH_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PY_DIR=$(readlink -f "${SH_DIR}/../../py")

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

mkdir -p ~/logs

{
    for tb in $(grep -rnH "\"${H}\"" ../../config/*.yml | grep -v "LTU" | cut -d':' -f1 | cut -d'/' -f4 | cut -d'.' -f1)
    do
        echo "========= ${tb} ========="
        testbench=${PY_DIR}/${tb}.py

        # setup the sub-rack
        ${testbench} cru initialize
        ${testbench} initialize_all_rdos    # change GBTx charge pump setting (potential glitch on clock to detector / CANbus)
        sleep 1                             # let the FPGA recover
        ${testbench} cru initialize         # clean up the CRoU
        ${testbench} version
        ${testbench} feeid
        ${testbench} dna
        ${testbench} reset_all_temp_interlocks # configure the interlocks according to the stave type

        ${testbench} initialize_all_gbtx12 # activate the second GBT link
        ${testbench} clean_all_datapaths
        ${testbench} info_for_log_entry # cannot be executed currently
    done

    roc-list-cards
    for i in $(seq 0 3)
    do
	echo "# roc-status --id=#${i}:"
        roc-status --id=#${i}
    done
} 2>&1 | tee "~/logs/${H}_prepare_subrack_ob_${timestamp}.log"
