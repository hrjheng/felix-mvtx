# Instructions on how to setup the environment on FLP for python 3 (J. Schambach, 8/9/2018)

some development packages that might be needed (I didn't install those explicitly on my system,
since many of those are already installed as part of the OS install)

``` shell
yum install -y mysql-devel curl curl-devel  bzip2 bzip2-devel unzip autoconf automake texinfo gettext gettext-devel libtool freetype freetype-devel libpng libpng-devel sqlite sqlite-devel ncurses-devel mesa-libGLU-devel libX11-devel libXpm-devel libXext-devel libXft-devel libxml2 libxml2-devel motif motif-devel kernel-devel pciutils-devel kmod-devel bison flex perl-ExtUtils-Embed environment-modules tmux vim
```

It is necessary to first install the latest FLP prototype software
I installed v0.9.0-5 as described on [this web page](https://alice-o2.web.cern.ch/node/153)

**!!!!!!!!!!!!! IMPORTANT!!!!!!!!!!!**
However, don't initialize the  FLP environment, since their python variables will
interfere with the installation below

# Install Emacs 25

I find it useful to install a newer version of emacs, since CC7 emacs is pretty old:

``` shell
yum install -y libXpm-devel libjpeg-turbo-devel openjpeg-devel openjpeg2-devel turbojpeg-devel giflib-devel libtiff-devel gnutls-devel libxml2-devel GConf2-devel dbus-devel wxGTK-devel gtk3-devel texinfo-5.1-5.el7.x86_64
cd /tmp
wget http://git.savannah.gnu.org/cgit/emacs.git/snapshot/emacs-25.1.tar.gz
tar zxf emacs-25.1.tar.gz
cd emacs-25.1/
./autogen.sh
./configure
```

Then as sudo:

``` shell
make install
```

``` shell
emacs --version
```

# Installing git 2.xx

``` shell
yum install curl-devel expat-devel gettext-devel openssl-devel zlib-devel gcc perl-ExtUtils-MakeMaker
cd /tmp
wget https://www.kernel.org/pub/software/scm/git/git-2.21.0.tar.gz
tar xzf git-2.21.0.tar.gz
cd git-2.21.0
sudo make prefix=/usr/local/git all
sudo make prefix=/usr/local/git install
echo "export PATH=/usr/local/git/bin:$PATH" >> ~/.bashrc
source ~/.bashrc
git --version
```


# Getting python3 to work

From FLP Suite v0.18.x, all O2 modules are always present in the environment and the user
does not need to load them manually.

## Using ReadoutCard (OBSOLETE)

**NOTE:** see [here](HowTo.md) which version of ReadoutCard to use!

``` shell
module load ReadoutCard
```

``` shell
which python
```

should return ```/opt/alisw/el7/Python/v3.6.10-27/bin/python```

**NOTE**: if you already used ReadoutCard before version v0.11, you should restart the FLP after before using version 0.11.

## Installing python modules (OBSOLETE)

login as ```its-admin``` then

**NOTE:** see [here](HowTo.md) which version of ReadoutCard to use!

``` shell
module load ReadoutCard
sudo chmod 777 -R $(which python | cut -d'/' -f-6)/lib/python3.6/site-packages
sudo chmod 777 -R $(which python | cut -d'/' -f-6)/bin
```

``` shell
cd CRU_ITS/software/py/
pip install -r requirements.txt
```

If you are installing on a system which is used to run CI, then also install

``` shell
cd CRU_ITS/software/py/
pip install -r requirements_ci.txt
```

Finally

``` shell
sudo chmod 755 -R $(which python | cut -d'/' -f-6)/lib/python3.6/site-packages
sudo chmod 755 -R $(which python | cut -d'/' -f-6)/bin
```

## Install Anaconda3 for Python3 environment (OBSOLETE)

``` shell
cd /tmp
wget https://repo.anaconda.com/archive/Anaconda3-2019.03-Linux-x86_64.sh
```

Then as sudo:

``` shell
bash Anaconda3-2019.03-Linux-x86_64.sh
```

Place the installation in ```/opt/anaconda3``` and **do not add** it to the ```.bashrc```

### Testing it:

In order to use it, the script source [setup_its.sh](../software/sh/setup_its.sh) should be called before using it.
Then:

``` shell
which python
```

should return ```/opt/anaconda3/bin/python```

### Alternative installation:

You can also download from [here](https://www.anaconda.com/download/), install it

# Additional installation
Some of the instructions for  the compilation are modified from [this web page](https://alice-o2.web.cern.ch/node/158)

As sudo run:

``` shell
yum install -y wget git cmake3 graphviz doxygen
```

# Install the software collection devtoolset

As sudo run:

``` shell
yum install -y centos-release-scl
yum-config-manager --enable rhel-server-rhscl-7-rpms
yum install -y devtoolset-7
source scl_source enable devtoolset-7
```

# Installing ReadoutCard and Readout (OBSOLETE)

As root

``` shell
yum search ReadoutCard
```

**NOTE:** see [here](HowTo.md) which version of ReadoutCard to use!

``` shell
yum install -y alisw-ReadoutCard+v0.xx.y-z.x86_64
```

**NOTE:** see [here](HowTo.md) which version of Readout to use!

``` shell
yum search Readout
```

``` shell
yum install -y alisw-Readout+v0.aa-b.x86_64
```

# Installing boost (OBSOLETE)

Boost needs to be recompiled with python3. download boost v1.67.0 [here](https://dl.bintray.com/boostorg/release/1.67.0/source/) or
[here](https://sourceforge.net/projects/boost/files/boost/1.67.0/)

``` shell
cd /home/software
tar zxf ~/Downloads/boost_1_67_0.tar.gz
cd boost_1_67_0/
./bootstrap.sh --with-python=python3.6m
./b2
./b2 install
```

# Installing O2 software (OBSOLETE)

DIM is needed for the alf client, but compilation will just skip this if not installed

``` shell
yum install -y dim
```

``` shell
cd ALICE/O2
git clone https://github.com/AliceO2Group/Common.git
git clone https://github.com/AliceO2Group/InfoLogger.git
git clone https://github.com/AliceO2Group/ReadoutCard.git
```

``` shell
cd ~/ALICE/O2/Common
git checkout v1.3.0
mkdir build
cd build/
source scl_source enable devtoolset-7
cmake3 -DCMAKE_PREFIX_PATH="/usr/local;/opt/o2-dependencies;/opt/o2-modules" ..
make
sudo make install
```

``` shell
cd ~/ALICE/O2/InfoLogger
git checkout v1.0.9
mkdir build
cd build/
source scl_source enable devtoolset-7
cmake3 -DCMAKE_PREFIX_PATH="/usr/local;/opt/o2-dependencies;/opt/o2-modules" -DPYTHON_EXECUTABLE=/opt/anaconda3/bin/python3 -DPYTHON_INCLUDE_DIR=/opt/anaconda3/include/python3.6m -DPYTHON_LIBRARY=/opt/anaconda3/lib/libpython3.6m.so ..
make
sudo make install
```

``` shell
cd ~/ALICE/O2/ReadoutCard
git checkout v0.9.2
```
Apply the following two patches
``` cmake
diff --git a/cmake/ReadoutCardDependencies.cmake b/cmake/ReadoutCardDependencies.cmake
index 3901ded..4a43934 100644
--- a/cmake/ReadoutCardDependencies.cmake
+++ b/cmake/ReadoutCardDependencies.cmake
@@ -3,7 +3,7 @@ if(APPLE)
     set(boost_python_component "")
 else()
     set(rt_lib "rt")
-    set(boost_python_component "python27")
+    set(boost_python_component "python36")
 endif()
```
``` python
--- a/src/Cru/cru_constants_populate.py
+++ b/src/Cru/cru_constants_populate.py
@@ -18,17 +18,17 @@ roc_regs = {'add_bsp_hkeeping_tempstat':'TEMPERATURE',
 # e.g. 'TEMPERATURE':0x00010008
 to_replace = {}

-for key0,value0 in roc_regs.iteritems():
-  for key,value in table.CRUADD.iteritems():
+for key0,value0 in roc_regs.items():
+  for key,value in table.CRUADD.items():
     if (key0 == key):
       to_replace[value0] = '0x' + str(format(value, '08x'))

-print to_replace
+print(to_replace)

 cfile = open('Constants.h')
 contents = cfile.readlines()

-for key,value in to_replace.iteritems():
+for key,value in to_replace.items():
   for (i, line) in enumerate(contents):
     if (key in line):
       contents[i] = re.sub("\([^)]*\)", '(' + value + ')', line)
```
``` shell
mkdir build
cd build/
source scl_source enable devtoolset-7
cmake3 -DCMAKE_PREFIX_PATH="/usr/local;/opt/o2-dependencies;/opt/o2-modules" -DPYTHON_EXECUTABLE=/opt/anaconda3/bin/python3 -DPYTHON_INCLUDE_DIR=/opt/anaconda3/include/python3.6m -DPYTHON_LIBRARY=/opt/anaconda3/lib/libpython3.6m.so -DDIM_ROOT=/opt/dim -Wno-dev ..
make
sudo make install
```

After all of that, libO2ReadoutCard is now available to be imported in python3.
