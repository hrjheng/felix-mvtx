# Makefile

include ../../../../../env_var.mk
-include ../../../../../env_var_local.mk

#Paths
RUN_DIR =../run
MODELSIM = $(MODELSIM_PATH)/vsim

MODELSIM_CMD = $(MODELSIM) -modelsimini $(SIMLIB_MODELSIM_PATH)/modelsim.ini -do "do ../scripts/1_all_incl_sim.do"


#targets
main: gui

gui:
	(cd $(RUN_DIR) && $(MODELSIM_CMD))

console:
	(cd $(RUN_DIR) && $(MODELSIM_CMD) -c)

update_filelist:
	(make -C ../../ create_filelist)
