#!/bin/bash

SH_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_DIR="/data/ob_comm/logs"
RAW_DIR="/data/ob_comm/raw"

rsync -rv --size-only "${LOG_DIR}" "${RAW_DIR}" -e ssh aliceits@lxplus:/eos/project/a/alice-its-commissioning/OuterBarrel/cosmics

