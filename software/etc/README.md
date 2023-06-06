# FLP Operating System Configuration Files

Files in this folder are mostly for documentation of OS configuration files necessary on the FLP.

## Huge Pages Configuration

There are two files that currently facilitate the configuration of the hugepages in FLP:

* roc_hugepages_startup.sh
* roc_hugepages_config.service

To use these files do the following as root:

``` shell
mkdir /etc/flp.d
cp roc_hugepages_startup.sh /etc/flp.d/.
cp roc_hugepages_config.service /etc/systemd/system/.
systemctl enable roc_hugepages_config.service
systemctl start roc_hugepages_config.service
systemctl daemon-reload
```

