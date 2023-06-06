# IB Tools

Tools for operating Inner Barrel staves.

DISCLAIMER: the existence of the code doesn't mean it works!

Verified tests:
- `ReadoutTest`
- `ThresholdScan`
- `ThresholdTuning`
- `DACScan`
- `CableResistanceMeasurement`
- `ReadWrite`
- `FIFOTest`

## INSTALLATION

`cp setup-template.cfg setup.cfg` and edit `setup.cfg` according to your usage (documentation in comments in the file).

## USAGE

`./ibcmd.py ARG` # Operations on IB. ARG can be one of the following:
    - pon - Power ON
    - poff - Power OFF
    - ps - Power Status
    - For more options see the code

`./run_test.py ARGs` # run with --help for information
