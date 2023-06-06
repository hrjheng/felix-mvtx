#!/bin/bash

# cp roc_hugepages_startup.sh /etc/flp.d/.
# cp roc_hugepages_config.service /etc/systemd/system/.
# systemctl enable roc_hugepages_config.service
# systemctl start roc_hugepages_config.service
# systemctl daemon-reload

hugeadm --create-global-mounts
chgrp -R pda /var/lib/hugetlbfs/global/*
chmod -R g+rwx /var/lib/hugetlbfs/global/*
echo 128 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
echo 24 > /sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages
