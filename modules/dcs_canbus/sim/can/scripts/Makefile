# Makefile

include ../../../../../env_var.mk
-include ../../../../../env_var_local.mk

#Paths
RUN_DIR =../run
MODELSIM = $(MODELSIM_PATH)/vsim

MODELSIM_CMD = $(MODELSIM) -do "do ../scripts/07-compile_and_run_can_hlp.do"
MODELSIM_CMD_CI = $(MODELSIM) -do "do ../scripts/07-compile_and_run_can_hlp.do --ci" -c -lic_no_lnl -lic_no_mix -lic_no_slvhdl -lic_no_slvlog
MODELSIM_CMD_CI_SIM = $(MODELSIM) -do "do ../scripts/07-compile_and_run_can_hlp.do --ci_sim" -c

#targets
main: gui

gui:
	(cd $(RUN_DIR) && $(MODELSIM_CMD))

console:
	(cd $(RUN_DIR) && $(MODELSIM_CMD) -c)

ci:
	(cd $(RUN_DIR) && $(MODELSIM_CMD_CI))
	(cd $(RUN_DIR) && $(MODELSIM_CMD_CI_SIM))

environment:
	/bin/bash
