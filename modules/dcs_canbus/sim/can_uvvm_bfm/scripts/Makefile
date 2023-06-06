# Makefile

include ../../../../../env_var.mk
-include ../../../../../env_var_local.mk

#Paths
RUN_DIR =../run
MODELSIM = $(MODELSIM_PATH)/vsim

MODELSIM_CMD = $(MODELSIM) -do "do ../scripts/07-compile_and_run.do"
MODELSIM_CMD_CI = $(MODELSIM) -do "do ../scripts/07-compile_and_run.do --ci" -c

#targets
main: gui

gui:
	(cd $(RUN_DIR) && $(MODELSIM_CMD))

console:
	(cd $(RUN_DIR) && $(MODELSIM_CMD) -c)

ci:
	(cd $(RUN_DIR) && $(MODELSIM_CMD_CI))

environment:
	/bin/bash
