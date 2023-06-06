# Subrack verify

This document describes how to run the test on a new subrack to verify that the RUs are correctly connected.

## Preparation

1. Log into the flp in which the RUs are connected (See [CRU/FLP/RU mapping](https://espace.cern.ch/alice-project-itsug-electronics/_layouts/15/WopiFrame.aspx?sourcedoc=/alice-project-itsug-electronics/Shared%20Documents/Matteo/cru_to_ru_mapping.xlsx&action=default)). The user is ```its```. Ask the password to the commissioning coordinator.
2. If you do not already have it, create a folder with your CERN user in home. Clone this repository inside the folder.
3. From ```CRU_ITS/software/py/subrack_verify``` enter the ReadoutCard environment (see [Direct use of O2 ReadoutCard](../doc/HowTo.md))
4.  Indentify the ```testbench[|_xyz].yml``` file relative to the layer the RUs are used with.
 **NOTE:** the testbench yml files are stored in the [config folder](../software/config).
5. Make sure that the RUs are powered and programmed (1.7 A current comsumption).


## Running the test

1. Run

``` shell
./subrack_verify.py -c <relative path the testbench yml file>
```
