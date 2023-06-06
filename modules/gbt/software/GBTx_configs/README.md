## GBTx Register configuration files

Files in this directory are to be used with the GBT project's GBTx I2C dongle to load the GBTx chips register
configurations. The python scripts in the board support software module can also read these files and
send it to the appropriate GBTx on the RU.

### GBTx0\_Config.xml
Not used anymore.

### GBTx0\_Config\_RUv1\_1.xml
Configuration used for GBTx0 in RUv1.1

### GBTx0\_Config\_RUv2.xml
Configuration used for GBTx0 in RUv2.0 and RUv2.1 
(Currently the same as GBTx2\_Config\_RUv1\_1.xml, but kept for clarity)

### GBTx0\_Config\_RUv1\_1\_fuse.xml
Configuration used for fusing RUv2.x boards. This configuration is the same as GBTx0\_Config\_RUv1\_1.xml,
except that the following registers have been removed on recommendation from the GBTx team and thus
will not be fused (i.e. will contain "0"): 274, 275, 276, 284, 285, 286, 291, 292,
296, 297, 298, 302, 307, 308, 309

### GBTx1\_Config\_RUv1\_1.xml
Configuration used for GBTx1 in RUv1.1

### GBTx1\_Config\_RUv2.xml
Configuration used for GBTx1 in RUv2.0 and RUv2.1 
Different configuration of the sampling phase of the input link compared to RUv1.1

### GBTx2\_Config\_RUv1\_1.xml
Configuration used for GBTx2 in RUv1.1
Differs from the GBTx0\_Config\_RUv1\_1.xml only in configuration of the sampling phase of the input link

### GBTx2\_Config\_RUv2.xml
Configuration used for GBTx2 in RUv2.0 and RUv2.1 
(Currently the same as GBTx2\_Config\_RUv1\_1.xml, but kept for clarity)

