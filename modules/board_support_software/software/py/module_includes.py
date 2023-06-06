"""Include paths for external module files"""

import importlib.util
import sys, os

_MODULES_FOLDER_PATH = os.path.split(os.path.realpath(__file__))[0] + "/../../../"
_MODULES = [
    # (<module_name>, <relative path (from modules folder)>),
    ('libflxcard_py', 'felix-sw/software/py/libflxcard_py/libflxcard_py.py'), # Will be skipped if already loaded by Atlas software, must be first
    ('libO2ReadoutCard', 'cru_support_software/software/py/libo2readoutcard/libO2ReadoutCard.py'), # Will be skipped if already loaded by O2, must be first
    ('libO2Lla', 'cru_support_software/software/py/libo2lla/libO2Lla.py'), # Will be skipped if already loaded by O2, must be first
    ('usb_communication', 'usb_if/software/usb_communication/usb_communication.py'),
    ('cru_table', 'cru_support_software/software/py/cru_table.py'),
    ('roc', 'cru_support_software/software/py/roc.py'),
    ('cru_swt_communication', 'cru_support_software/software/py/cru_swt_communication.py'),
    ('cru_i2c', 'cru_support_software/software/py/cru_i2c.py'),
    ('cru_si534x', 'cru_support_software/software/py/cru_si534x.py'),
    ('cru_ltc2990', 'cru_support_software/software/py/cru_ltc2990.py'),
    ('cru_ttc', 'cru_support_software/software/py/cru_ttc.py'),
    ('cru_dwrapper', 'cru_support_software/software/py/cru_dwrapper.py'),
    ('cru_bsp', 'cru_support_software/software/py/cru_bsp.py'),
    ('cru_gbt', 'cru_support_software/software/py/cru_gbt.py'),
    ('cru_board', 'cru_support_software/software/py/cru_board.py'),
    ('can_hlp', 'dcs_canbus/software/can_hlp/can_hlp.py'),
    ('socketcan_sim_wrapper', 'dcs_canbus/software/can_hlp/socketcan_sim_wrapper.py'),
    ('can_hlp_comm', 'dcs_canbus/software/can_hlp/can_hlp_comm.py'),
    ('ecc_functions', 'board_support_software/software/py/ecc_conversion/ecc_functions.py'),
    ('generateScrubbingFile', 'board_support_software/software/py/ecc_conversion/generateScrubbingFile.py'),
    ('makeparameters', 'board_support_software/software/py/ecc_conversion/makeparameters.py'),
    ('ltu', 'ltu_support_software/software/py/ltu.py'),
    ('flx_roc',   'felix-sw/software/py/flx_roc.py'  ),
    ('flx_table', 'felix-sw/software/py/flx_table.py'),
    ('flx_gbt',   'felix-sw/software/py/flx_gbt.py'  ),
    ('flx_bsp',   'felix-sw/software/py/flx_bsp.py'  ),
    ('flx_ttc',   'felix-sw/software/py/flx_ttc.py'  ),
    ('flx_card',  'felix-sw/software/py/flx_card.py' ),
    ('flx_swt_communication', 'felix-sw/software/py/flx_swt_communication.py')
]

for module_name, module_path in _MODULES:
    if importlib.util.find_spec(module_name) is None and module_name not in sys.modules:
        spec = importlib.util.spec_from_file_location(module_name, _MODULES_FOLDER_PATH + module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[module_name] = module
