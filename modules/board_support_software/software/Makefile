include ../../../env_var.mk
-include ../../../env_var_local.mk

help:
	($(VIVADO_PATH)_Lab/$(VIVADO_VER)/bin/vivado_lab -help)

program_RUv0_CRU:
	($(VIVADO_PATH)_Lab/$(VIVADO_VER)/bin/vivado_lab -mode batch -source "tcl/program_RUv0_CRU.tcl" -notrace -tclargs $(filter-out $@,$(MAKECMDGOALS)))

program_RU:
	($(VIVADO_PATH)_Lab/$(VIVADO_VER)/bin/vivado_lab -mode batch -source "tcl/program_RU.tcl" -notrace -tclargs $(filter-out $@,$(MAKECMDGOALS)))

program_PA3:
	-(rm tcl/ITS-RU/bitfile.pdb)
	(cp $(filter-out $@,$(MAKECMDGOALS)) tcl/ITS-RU/bitfile.pdb)
	(cd tcl && $(FP_PATH)/FPExpress SCRIPT:program_PA3.tcl)

program_PA3_chain:
	-(rm tcl/ITS-RU/bitfile.pdb)
	(cp $(filter-out $@,$(MAKECMDGOALS)) tcl/ITS-RU/bitfile.pdb)
	(cd tcl && $(FP_PATH)/FPExpress SCRIPT:program_PA3_chain.tcl)
