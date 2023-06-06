echo 'can' > /etc/modules-load.d/can.conf
echo 'vcan' >> /etc/modules-load.d/can.conf

echo 'install vcan /sbin/modprobe --ignore-install vcan;/sbin/ip link add dev vcan0 type vcan;/sbin/ip link set up vcan0' > /etc/modprobe.d/can.conf

# restarting service
systemctl restart systemd-modules-load.service
