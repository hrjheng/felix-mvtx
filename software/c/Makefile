SHELL:=/bin/bash
# Makefile

################################################################################
## Title        : CRU_ITS c decoder Makefile
## Project      : CRU_ITS
################################################################################
## File         : Makefile
## Author       : Matteo Lupi (matteo.lupi@cern.ch)
## Company      : CERN
## Created      : 2019-11-07
## Last update  : 2019-11-13
################################################################################
## Description: Makefile
##
## targets:
##
##    all
##      Compiles the decoder
##        NOTE: you should not be in Readout.ReadoutCard environment
##              to compile it!
##    clean
##      Removes the generated files
##    help
##      guess what it does...
##############################################################################/
##-----------------------------------------------------------------------------
## Revisions  :
## Date        Version  Author        Description
## 2019-11-07           ML            Created
## 2019-11-13           ML            Moved -lm at end
##                                    Added -Wall option
##                                     following suggestion from @avelure
## 2023-03-13           YCM           Change for MVTX decoder
##-----------------------------------------------------------------------------
DECODER=mvtx-decoder

#targets
all: $(DECODER)

$(DECODER): $(DECODER).c
	gcc --std=gnu99 -march=native -gdwarf-4 -pedantic -Wall -O3 -o $(DECODER) $(DECODER).c -lm -g

clean:
	rm -f $(DECODER)

help:
	(cat Makefile | grep '##')

%:
	@:
