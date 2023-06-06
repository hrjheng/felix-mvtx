if [[ "${BASH_SOURCE[0]}" = "${0}" ]]; then
  echo "Error: This script needs to be sourced"
  exit 1
fi

# User specific aliases and functions
export PYTHONPATH=/opt/anaconda3:$PYTHONPATH
export PATH=/opt/anaconda3/bin:$PATH

export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
export PYTHONPATH=/usr/local/lib:$PYTHONPATH
