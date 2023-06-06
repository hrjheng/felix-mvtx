#!/bin/bash
#
# Script to reenumerate CRU(s) after programming the FPGA
# so no reboot is required.
# Arguments: PCIe ID of the CRU(s)
#

usage() {
  echo ""
  echo "Script to reenumerate CRU(s) after programming the FPGA"
  echo "so no reboot is required."
  echo "Arguments: PCIe ID of the CRU(s)"
  echo ""
  echo "Example usage:"
  echo "  bash reenumerate-pci.sh 02:00.0 83:00.0"
  echo ""
}


if [ $# -eq 0 ]; then
  echo "No PCIe ID is given!"
  usage
  exit 0
fi

if [ $1 == "-h" ] || [ $1 == "--help" ]; then
  usage
  exit 0
fi

for pciid in $@;
do
  echo 1 > /sys/bus/pci/devices/0000\:$pciid/remove
done

echo 1 > /sys/bus/pci/rescan
