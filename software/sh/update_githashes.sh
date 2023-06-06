GITHASH=${1^^}

./update_githashes_ibtest.sh $GITHASH
./update_githashes_ibtable.sh $GITHASH
./update_githashes_mltest.sh $GITHASH
./update_githashes_oltest.sh $GITHASH
./update_deployment_test_yml.sh $GITHASH