echo $1
#update bitfile for all the deployment test setups
sed -i "s/BITFILE \: .*/BITFILE \: '\/home\/maps\/mvtx_readout\/RU_bitfiles\/RU_mainFPGA\/latest\/${1}.bit'/g" ../py/deployment/deployment_test_LANL.yml
