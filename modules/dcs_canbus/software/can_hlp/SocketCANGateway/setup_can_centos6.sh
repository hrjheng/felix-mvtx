echo '#!/bin/sh' > /etc/sysconfig/modules/can.modules
echo '/sbin/modprobe can >/dev/null 2>&1' >> /etc/sysconfig/modules/can.modules
echo '/sbin/modprobe can_raw >/dev/null 2>&1' >> /etc/sysconfig/modules/can.modules
echo '/sbin/modprobe can_bcm >/dev/null 2>&1' >> /etc/sysconfig/modules/can.modules
echo '/sbin/modprobe vcan >/dev/null 2>&1' >> /etc/sysconfig/modules/can.modules
chmod 755 /etc/sysconfig/modules/can.modules

echo 'install vcan /sbin/modprobe --ignore-install vcan; /sbin/ip link add dev vcan0 type vcan;/sbin/ip link set up vcan0' > /etc/modprobe.d/can.conf

# restarting service
systemctl restart systemd-modules-load.service
