"""Include paths for external module files"""

import importlib
import importlib.util
import sys, os

_MODULES_FOLDER_PATH = os.path.split(os.path.realpath(__file__))[0] + "/../"
_MODULES = [
    # (<module_name>, <relative path (from modules folder)>),
    ('flx_roc',   'felix-sw/LIB/flx_roc.py'  ),
    ('flx_table', 'felix-sw/LIB/flx_table.py'),
    ('flx_bsp',   'felix-sw/LIB/flx_bsp.py  '),
    ('flx_gbt',   'felix-sw/LIB/flx_gbt.py'  ),
]

for module_name, module_path in _MODULES:
    if importlib.util.find_spec(module_name) is None and module_name not in sys.modules:
        spec = importlib.util.spec_from_file_location(module_name, _MODULES_FOLDER_PATH + module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[module_name] = module
