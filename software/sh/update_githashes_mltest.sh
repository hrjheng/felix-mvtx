GITHASH=${1^^}

#update daq_test configs for ML-test
sed -i "/RDO/ c RDO = 0x$GITHASH" ../config/daq_test_mls.cfg
sed -i "/RDO/ c RDO = 0x$GITHASH" ../config/daq_test_mls_short.cfg
sed -i "/RDO/ c RDO = 0x$GITHASH" ../config/threshold_mls.cfg

#update crate mapping for ML-test
NEWENTRY=`grep 'ML-test' ../../modules/board_support_software/software/py/crate_mapping.py -A 1 | tail -n 1 | sed "s/0x.\{8\}/0x$GITHASH/"`
sed -i "/ML-test/{n;s/.*flpits12.cern.ch.*/$NEWENTRY/}" ../../modules/board_support_software/software/py/crate_mapping.py
