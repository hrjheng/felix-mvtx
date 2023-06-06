include ../../../env_var.mk
-include ../../../env_var_local.mk

help:
	($(VIVADO_PATH)_Lab/$(VIVADO_VER)/bin/vivado_lab -help)

program_RUv0_CRU:
	($(VIVADO_PATH)_Lab/$(VIVADO_VER)/bin/vivado_lab -mode batch -source "../../../modules/board_support_software/software/tcl/program_RUv0_CRU.tcl" -notrace -tclargs $(filter-out $@,$(MAKECMDGOALS)))

program_RU:
	($(VIVADO_PATH)_Lab/$(VIVADO_VER)/bin/vivado_lab -mode batch -source "../../../modules/board_support_software/software/tcl/program_RU.tcl" -notrace -tclargs $(filter-out $@,$(MAKECMDGOALS)))

program_PA3:
	-(rm ../../../modules/board_support_software/software/tcl/ITS-RU/bitfile.pdb)
	(cp $(filter-out $@,$(MAKECMDGOALS)) ../../../modules/board_support_software/software/tcl/ITS-RU/bitfile.pdb)
	(cd ../../../modules/board_support_software/software/tcl && $(FP_PATH)/FPExpress SCRIPT:program_PA3.tcl)

program_PA3_chain:
	-(rm ../../../modules/board_support_software/software/tcl/ITS-RU/bitfile.pdb)
	(cp $(filter-out $@,$(MAKECMDGOALS)) ../../../modules/board_support_software/software/tcl/ITS-RU/bitfile.pdb)
	(cd ../../../modules/board_support_software/software/tcl && $(FP_PATH)/FPExpress SCRIPT:program_PA3_chain.tcl)
