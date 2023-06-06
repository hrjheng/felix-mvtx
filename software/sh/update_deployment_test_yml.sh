echo $1
#update bitfile for all the deployment test setups
sed -i "s/BITFILE \: .*/BITFILE \: '\/shareFS\/its\/RU_bitfiles\/RU_mainFPGA\/pre_release\/${1}.bit'/g" ../py/deployment/deployment_test_ibs.yml
sed -i "s/BITFILE \: .*/BITFILE \: '\/shareFS\/its\/RU_bitfiles\/RU_mainFPGA\/pre_release\/${1}.bit'/g" ../py/deployment/deployment_test_ibs_short.yml
sed -i "s/BITFILE \: .*/BITFILE \: '\/shareFS\/its\/RU_bitfiles\/RU_mainFPGA\/pre_release\/${1}.bit'/g" ../py/deployment/deployment_test_ibtable.yml
sed -i "s/BITFILE \: .*/BITFILE \: '\/shareFS\/its\/RU_bitfiles\/RU_mainFPGA\/pre_release\/${1}.bit'/g" ../py/deployment/deployment_test_ibtable_short.yml
sed -i "s/BITFILE \: .*/BITFILE \: '\/shareFS\/its\/RU_bitfiles\/RU_mainFPGA\/pre_release\/${1}.bit'/g" ../py/deployment/deployment_test_mls.yml
sed -i "s/BITFILE \: .*/BITFILE \: '\/shareFS\/its\/RU_bitfiles\/RU_mainFPGA\/pre_release\/${1}.bit'/g" ../py/deployment/deployment_test_mls_short.yml
sed -i "s/BITFILE \: .*/BITFILE \: '\/shareFS\/its\/RU_bitfiles\/RU_mainFPGA\/pre_release\/${1}.bit'/g" ../py/deployment/deployment_test_ols.yml
sed -i "s/BITFILE \: .*/BITFILE \: '\/shareFS\/its\/RU_bitfiles\/RU_mainFPGA\/pre_release\/${1}.bit'/g" ../py/deployment/deployment_test_ols_short.yml
