GITHASH=${1^^}

#update daq_test configs for IB-test
sed -i "/RDO/ c RDO = 0x$GITHASH" ../config/daq_test_ibtable.cfg
sed -i "/RDO/ c RDO = 0x$GITHASH" ../config/daq_test_ibtable_short.cfg

#update threshold config for IB-test
sed -i "/RDO/ c RDO = 0x$GITHASH" ../config/threshold_ibtable.cfg

#update crate mapping for IB-test
NEWENTRY=`grep 'IB-table' ../../modules/board_support_software/software/py/crate_mapping.py -A 1 | tail -n 1 | sed "s/0x.\{8\}/0x$GITHASH/"`
sed -i "/IB-table/{n;s/.*flpits12.cern.ch.*/$NEWENTRY/}" ../../modules/board_support_software/software/py/crate_mapping.py
