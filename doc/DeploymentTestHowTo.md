# Deployment Test HowTo

## What is a deployment test

The deployment test is a set of test which are run on the specified setup to verify that the software and bitfile are operating correctly and that a regression is not introduced when a new branch is merged.
The script makes use of [python unittest](https://docs.python.org/3.6/library/unittest.html) to executed all the script.
The script is executed by the manual continuous integration jobs, which are defined in the `gitlab-ci.yml` file.

Before trying it out on a physical setup in the CI environment, please manually debug it on the machine where it is supposed to run.

## What does the deployment test do?

The deployment test does the following:

* flashes the BITFILE onto the RDO(s) in the setup (if it doesn't already have the corresponding firmware), then loads and verifies the firmware
* powers on the setup(s) stave
* runs through a series of SWT + DCTRL tests, the number of which are specifies in the cfg file
* runs 4 daq_tests (regular, exclude lane 0, exclude lane 2 and no recording. Also it's "IBS only", though you can comment out the "skip" for the corresponding ols/mls daq_test - it's already there)
* runs a threshold scan on all of the setup(s)
* powers off the setup(s) stave
* reports any failures

Note that this script uses unittest, which runs the tests in alphabetical order, so some of the class names have been prepended with letters to ensure they run in the order they need to run in. You can also run any individual test via

```bash
./deployment_test.py -c /config/path -b bitfile TestName
```

## Developing a new test

### Python unittest basics

A test is a python method in a class inheriting from `unittest.TestCase`.
Each test is returning `ok`, if it is passed, `fail` if it fails one of the defined checks, or `error` if it fails for other reasons.

Each class defines a `setUp` and `tearDown` method.
These methods are executed before and after each test, in particular, the tearDown is executed even if the test is failing, cleaning up the setup.
The philosophy here is to start from a clean setup and leave a clean setup, independently of the test result.

A class can also define a `setUpClass` and `tearDownClass` class methods, which are executed before the first and after the last test of the class, respectively.

An important thing to remember when developing a test, is that the test class name is important when it comes to execution order.
The tests are executed in alphabetical order (per class first, then per test in each class).

Various checks are defined in `unittest.Testcase` to assert on certain properties.
These should be used to let a test pass or fail: in particular, each test should contain at least one call to one `assert*` methods.

### Deployment test basics

The class structur can be observed inside the `deployment_test.py` script.
All tests in this file shall inherit from the `TestCaseBase` class which extends the `unittest.TestCase` class adding some data members which reflect the setup.

A Test class shall assume that a `cru`, `rdo` (i.e. the Readout Unit main FPGA), `pa3`, `sca` are available.
If one of these devices is not present, the test will be skipped automatically.

If the test only requires one Readout Unit and a CRU, a test can be added to the class `RdoBaseTest.TestRuOnChannel`.
These tests get run on every Readout Unit connected to the CRU at runtime.
Most of the tests (relative to CRU GBT channels with no Readout Unit connected) will be skipped.

## Running the deployment test

### 0: Clone the repo and go into the right directory..

```bash
git clone https://gitlab.cern.ch/alice-its-wp10-firmware/CRU_ITS.git
git checkout development
cd CRU_ITS/software/py/deployment
```

### 1: Determine the setup(s) you want to run the test on
You can run the test individually on the IBS, OLS or MLS, or you can run the setup with either IBS+OLS+MLS, IBS+OLS or IBS+MLS. When multiple setups are selected the test will run through them serially. **Ensure that these setup(s) are not in use via [the 301 mattermost channel](https://mattermost.web.cern.ch/aliitscomm/channels/b301-setup)**.

### 2: Pick the bitfile you want to deploy

You can either update the corresponding yml file in the same directory with the path to the BITFILE or you can pass the path as an argument to the script via

```bash
./deployment_test.py -c /path/to/cfg -b /path/to/bitfile
```

**NOTE THAT YOU MUST SUPPLY THE FULL NAME OF THE BITFILE, including .bit** (you can use any of the 4 e.g. XCKU\_top\_*.bit, XCKU\_top\_*\_ecc.bit,  XCKU\_top\_*\_bs.bit or  XCKU\_top\_*\_ecc\_bs.bit )

### 3: Update the githashes in all of the cfgs + cratemapping (not required for CI)
Depending on your setup(s), you run

```bash
cd ../../sh/
./update_githashes_[setup].sh [githash]
cd ../py/deployment/
```

where [setup] is either ibs, ols or mls. If you're running with all three setups, you can simply run

```bash
cd ../../sh/
./update_githashes.sh [githash]
cd ../py/deployment/
```

**Note that this step must be done before the test as the test depends on these values being updated**

Also (obviously) make sure this githash matches the githash of your bitfile...

### 4: Run the test with the corresponding config file for your setup

The config files are as follows:

* IBS + OLS + MLS (default): deployment\_test.yml
* IBS + OLS: deployment\_test\_ibs\_ols.yml
* IBS + MLS: deployment\_test\_ibs\_mls.yml
* IBS: deployment\_test\_ibs.yml
* OLS: deployment\_test\_ols.yml
* ML: deployment\_test\_mls.yml

For example, if you wanted to run both IBS and MLS with the bitfile given in the yml file:

```bash
./deployment_test.py -c deployment_test_ibs_mls.yml
```

### 5: Decode the data generated from the test
There are now simpler bash scripts to do this:

For example,

```bash
../../sh/decode_ibs.sh
```

decodes the data from the regular daq_test, while

```bash
../../sh/decode_ibs_excl0.sh
```

decodes the excl\_0 daq\_test. All of the scripts are similarly named (for threshold they are prepended with "threshold").

If you don't care about exit codes, I'd recommend decoding whatever is relevant to you in parallel (decode\_1.sh & decode\_2.sh & ...) Note that these already decode the relevant links in parallel, so the output would get messy quickly.

If you've selected all 3 setups, you can simply run

```bash
../../sh/decode_all.sh
```

## Important note about CI environment variable
While it's extremely unlikely the environment variable "CI" is set while you're running the test manually, if it happens to be set (you would have had to do this yourself), please unset it:

```bash
unset CI
```

## Questions?
Ask [Ryan](@rhanniga), he's happy to help.
