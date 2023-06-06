GITHASH=${1^^}

#update daq_test configs for OL-test
sed -i "/RDO/ c RDO = 0x$GITHASH" ../config/daq_test_ols.cfg
sed -i "/RDO/ c RDO = 0x$GITHASH" ../config/daq_test_ols_short.cfg
sed -i "/RDO/ c RDO = 0x$GITHASH" ../config/threshold_ols.cfg

#update crate mapping for OL-test
NEWENTRY=`grep 'OL-test' ../../modules/board_support_software/software/py/crate_mapping.py -A 1 | tail -n 1 | sed "s/0x.\{8\}/0x$GITHASH/"`
sed -i "/OL-test/{n;s/.*flpits11.cern.ch.*/$NEWENTRY/}" ../../modules/board_support_software/software/py/crate_mapping.py
