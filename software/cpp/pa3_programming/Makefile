CC = gcc
CXX = g++

CFLAGS = -O2 -Wall
CXXFLAGS = -std=c++14 -O2 -Wall
CXXFLAGS += -I$(FELIX_ROOT)/flxcard -I$(FELIX_ROOT)/drivers_rcc -I$(FELIX_ROOT)/regmap
CXXFLAGS += -I$(BOOST_INCLUDEDIR)

LDFLAGS = -g
LDFLAGS += -L$(BOOST_LIBRARYDIR)
LDFLAGS += -lstdc++
LDFLAGS += -lboost_program_options -lboost_filesystem -lFELIXwrapper

OBJS = main.o \
         dpalg.o dpcom.o dpuser.o dputil.o \
         dpcore.o dpfrom.o dpG3alg.o dpnvm.o dpsecurity.o \
         dpchain.o dpjtag.o \
         Sca.o

EXE = main

$(EXE) : main.o $(OBJS)
	$(CXX) $(CXXFLAGS) $(LDFLAGS) -o pa3jtag $(OBJS)

main.o :
dpalg.o : dpuser.h dputil.h dpalg.h dpG3alg.h dpjtag.h
dpcom.o : dpuser.h dpcom.h dpjtag.h
dpuser.o : dpuser.h dpalg.h dputil.h
dputil.o : dpuser.h dputil.h dpcom.h dpalg.h
dpcore.o : dpcore.h dputil.h dpalg.h dpG3alg.h dpnvm.h dpsecurity.h dpcom.h dpjtag.h
dpfrom.o : dpfrom.h dpuser.h dputil.h dpalg.h dpG3alg.h dpsecurity.h dpcom.h dpjtag.h
dpG3alg.o : dpG3alg.h dpuser.h dputil.h dpcom.h dpalg.h dpcore.h dpfrom.h dpnvm.h dpsecurity.h dpjtag.h
dpnvm.o : dpnvm.h dpuser.h dputil.h dpalg.h dpG3alg.h dpcom.h dpjtag.h
dpsecurity.o : dpsecurity.h dpuser.h dputil.h dpalg.h dpG3alg.h dpcom.h dpjtag.h
dpchain.o : dpchain.h dpuser.h dpjtag.h dpcom.h
dpjtag.o : dpjtag.h dpuser.h dputil.h dpcom.h dpchain.h dpalg.h dpG3alg.h

Sca.o : GBT_SCA_src/Sca.cpp GBT_SCA_src/Sca.h
	$(CXX) $(CXXFLAGS) -c GBT_SCA_src/Sca.cpp

clean :
	-rm -f pa3jtag $(OBJS) tms.log tdi.log log.log
