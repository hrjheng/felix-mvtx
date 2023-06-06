# it seems it does not work well if using echo for function return value, and calling inside $() (is a subprocess spawned?)
function wait_and_get_exit_codes() {
    children=("$@")
    EXIT_CODE=0
    for job in "${children[@]}"; do
       echo "PID => ${job}"
       CODE=0;
       wait ${job} || CODE=$?
       if [[ "${CODE}" != "0" ]]; then
           echo "At least one test failed with exit code => ${CODE}" ;
           EXIT_CODE=1;
       fi
   done
}

DIRN=$(dirname "$0");

echo "Decompressing ~/tmp_data/daqtest_ibs.lz4 ..." && env -i bash -c "lz4 -d -f ~/tmp_data/daqtest_ibs.lz4 ~/tmp_data/daqtest_ibs.raw"
echo "Decompressing ~/tmp_data/daqtest_ibs_excl_0.lz4 ..." && env -i bash -c "lz4 -d -f ~/tmp_data/daqtest_ibs_excl_0.lz4 ~/tmp_data/daqtest_ibs_excl_0.raw"
echo "Decompressing ~/tmp_data/daqtest_ibs_excl_2.lz4 ..." && env -i bash -c "lz4 -d -f ~/tmp_data/daqtest_ibs_excl_2.lz4 ~/tmp_data/daqtest_ibs_excl_2.raw"
echo "Decompressing ~/tmp_data/threshold_mls.lz4 ..." && env -i bash -c "lz4 -d -f ~/tmp_data/threshold_mls.lz4 ~/tmp_data/threshold_mls.raw"
echo "Decompressing ~/tmp_data/threshold_ols.lz4 ..." && env -i bash -c "lz4 -d -f ~/tmp_data/threshold_ols.lz4 ~/tmp_data/threshold_ols.raw"

commands=(
    'echo "IBS: Fee id 12 decoding in background..." && ../py/decode.py -f ~/tmp_data/daqtest_ibs.raw -i 12 -cp ~/tmp_data/daqtest_ibs_final_counters.json'
    'echo "IBS: Fee id 268 decoding in background..." && ../py/decode.py -f ~/tmp_data/daqtest_ibs.raw -i 268 -cp ~/tmp_data/daqtest_ibs_final_counters.json'
    'echo "IBS: Fee id 524 decoding in background..." && ../py/decode.py -f ~/tmp_data/daqtest_ibs.raw -i 524 -cp ~/tmp_data/daqtest_ibs_final_counters.json'
    'echo "IBS_Excl_0: Fee id 12 decoding in background..." && ../py/decode.py -f ~/tmp_data/daqtest_ibs_excl_0.raw -i 12 -cp ~/tmp_data/daqtest_excl0_final_counters.json -cll 1,2,3,4,5,6,7,8'
    'echo "IBS_Excl_2: Fee id 12 decoding in background..." && ../py/decode.py -f ~/tmp_data/daqtest_ibs_excl_2.raw -i 12 -cp ~/tmp_data/daqtest_ibs_excl2_final_counters.json -cll 0,1,3,4,5,6,7,8'
    'echo "MLS: Fee id 12312 decoding in background..." && ../py/decode.py -f ~/tmp_data/threshold_mls.raw -i 12312 -ts -ada -cp ~/tmp_data/threshold_mls_final_counters.json'
    'echo "MLS: Fee id 12568 decoding in background..." && ../py/decode.py -f ~/tmp_data/threshold_mls.raw -i 12568 -ts -ada -cp ~/tmp_data/threshold_mls_final_counters.json'
    'echo "OLS: Fee id 20522 decoding in background..." && ../py/decode.py -f ~/tmp_data/threshold_ols.raw -i 20522 -ts -ada -cp ~/tmp_data/threshold_ols_final_counters.json'
    'echo "OLS: Fee id 20778 decoding in background..." && ../py/decode.py -f ~/tmp_data/threshold_ols.raw -i 20778 -ts -ada -cp ~/tmp_data/threshold_ols_final_counters.json'
    )

clen=`expr "${#commands[@]}" - 1` # get length of commands - 1

children_pids=()
for i in `seq 0 "$clen"`; do
    (echo "${commands[$i]}" | bash) &   # run the command via bash in subshell
    children_pids+=("$!")
done
# wait; # wait for all subshells to finish - its still valid to wait for all jobs to finish, before processing any exit-codes if we wanted to
#EXIT_CODE=0;  # exit code of overall script
wait_and_get_exit_codes "${children_pids[@]}"

echo "EXIT_CODE => $EXIT_CODE"
exit "$EXIT_CODE"
# end
