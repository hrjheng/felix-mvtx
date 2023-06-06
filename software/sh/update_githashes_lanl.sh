GITHASH=${1^^}

#update daq_test configs for LANL
sed -i "/RDO/ c RDO = 0x$GITHASH" ../config/daq_test_LANL_flx.cfg
sed -i "/RDO/ c RDO = 0x$GITHASH" ../config/daq_test_LANL_seq.cfg

#update threshold config for LANL
sed -i "/RDO/ c RDO = 0x$GITHASH" ../config/threshold_LANL.cfg

#update crate mapping for LANL
for i in $(seq 1 8); do
NEWENTRY=`grep 'LANL' ../../modules/board_support_software/software/py/crate_mapping.py -A $i | tail -n 1 | sed "s/0x.\{8\}/0x$GITHASH/"`
SED_SKIP="$SED_SKIP"'n;'
sed -i "/LANL/{"$SED_SKIP"s/.*mvtx-flx-amd.*/$NEWENTRY/}" ../../modules/board_support_software/software/py/crate_mapping.py
done
