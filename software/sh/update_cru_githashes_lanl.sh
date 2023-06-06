GITHASH=${1^^}

#update daq_test configs for LANL
sed -i "/^\<CRU\>/ c CRU = 0x$GITHASH" ../config/daq_test_LANL_flx.cfg
sed -i "/^\<CRU\>/ c CRU = 0x$GITHASH" ../config/daq_test_LANL_seq.cfg

#update threshold config for LANL
sed -i "/^\<CRU\>/ c CRU = 0x$GITHASH" ../config/threshold_LANL.cfg
