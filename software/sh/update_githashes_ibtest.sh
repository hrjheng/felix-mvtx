GITHASH=${1^^}

#update daq_test configs for IB-test
sed -i "/RDO/ c RDO = 0x$GITHASH" ../config/daq_test_ibs.cfg
sed -i "/RDO/ c RDO = 0x$GITHASH" ../config/daq_test_ibs_short.cfg
sed -i "/RDO/ c RDO = 0x$GITHASH" ../config/daq_test_ibs_sequencer_short.cfg
sed -i "/RDO/ c RDO = 0x$GITHASH" ../config/daq_test_ibs_excl_0.cfg
sed -i "/RDO/ c RDO = 0x$GITHASH" ../config/daq_test_ibs_excl_2.cfg

#update threshold config for IB-test
sed -i "/RDO/ c RDO = 0x$GITHASH" ../config/threshold_ibs.cfg

#update crate mapping for IB-test
NEWENTRY=`grep 'IB-test' ../../modules/board_support_software/software/py/crate_mapping.py -A 1 | tail -n 1 | sed "s/0x.\{8\}/0x$GITHASH/"`
sed -i "/IB-test/{n;s/.*flpits11.cern.ch.*/$NEWENTRY/}" ../../modules/board_support_software/software/py/crate_mapping.py
