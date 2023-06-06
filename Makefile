# Makefile

################################################################################
## Title        : CRU_ITS Makefile
## Project      : CRU_ITS
################################################################################
## File         : Makefile
## Author       : Matteo Lupi (matteo.lupi@cern.ch)
## Company      : CERN
## Created      : 2019-01-16
## Last update  : 2019-03-07
################################################################################
## Description: Makefile
##
## targets:
##
##    ci_lint_check
##      Checks the linting and the code for errors as done in the CI
##    bug_report
##      Generates a bug report file to be attached to the gitlab.cern.ch in the issue
##    help
##      guess what it does...
##############################################################################/
##-----------------------------------------------------------------------------
## Revisions  :
## Date        Version  Author        Description
## 2019-01-16           ML            Added bug_report target
## 2019-03-07           ML            Added CI lint check for errors
## 2019-11-20           ML,JS         Added canbus subtree for lint check
## 2020-11-15           ML            Added yml checker for ru_gbtx0_chargepump_custom
##-----------------------------------------------------------------------------
BUG_REPORT_FILE = bug_report.log

#targets
pip_install:
	python3.9 -m pip install --upgrade pip --quiet
	python3.9 -m pip install -r software/py/requirements.txt --user --quiet
	python3.9 -m pip install -r software/py/requirements_ci.txt --user --quiet

ci_lint_check: pip_install
	find ./modules/board_support_software/software/py ./software/py ./modules/cru_support_software/software/py ./modules/felix-sw/software/py ./modules/ltu_support_software/software/py ./modules/usb_if/software/usb_communication ./modules/dcs_canbus/software/can_hlp -iname "*.py" ! -path '*/obsolete/*' | xargs pylint --rcfile=.pylintrc --errors-only

ci_lint_all: pip_install
	find ./modules/board_support_software/software/py ./software/py ./modules/cru_support_software/software/py ./modules/ltu_support_software/software/py ./modules/usb_if/software/usb_communication ./modules/dcs_canbus/software/can_hlp -iname "*.py" ! -path '*/obsolete/*' | xargs pylint --rcfile=.pylintrc

config_check: pip_install
	@(find ./software/config -iname "daq_test*NL*.cfg" -o -iname "threshold_*NL*.cfg" -o -iname "testbench*.yml" | xargs python3.9 ./software/py/gitlab/check_yaml.py -c)

yml_check: pip_install
	python3.9 ./software/py/gitlab/check_ru_gbtx0_chargepump_custom.py

shell_check:
	find software -iname "*.sh" | xargs shellcheck -s bash -Calways -S error

shell_check_all:
	find software -iname "*.sh" | xargs shellcheck -s bash -Calways

shell_check_apply:
	-(find software -iname "*.sh" | xargs shellcheck -s bash -f diff > shellcheck.patch)
	git apply shellcheck.patch

bug_report:
	(echo -e 'Head:\n'>$(BUG_REPORT_FILE) && git log -1 --decorate >> $(BUG_REPORT_FILE) && echo -e "\n\nStatus:\n" >> $(BUG_REPORT_FILE) && git status --porcelain >> $(BUG_REPORT_FILE) && echo -e "\n\nDiff:\n" >> $(BUG_REPORT_FILE) && git diff >> $(BUG_REPORT_FILE) && echo -e "\nDone! You can find the bur report in "$(BUG_REPORT_FILE))

help:
	(cat Makefile | grep '##')
%:
	@:
