#!/bin/bash

SH_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PY_DIR=$(readlink -f "${SH_DIR}/../../py")
PLT_DIR="${PY_DIR}/plots"
LOG_DIR="${PY_DIR}/logs"

rsync -rv --size-only "${LOG_DIR}" "${PLT_DIR}" -e ssh jiddon@lxplus:/eos/user/j/jiddon/ob_verification
