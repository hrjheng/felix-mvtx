#!/usr/bin/env python3.9

import os, sys, glob, stat

# dir containing testbench configs used to create testbenches
config_dir = sys.argv[1]

for yml_path in glob.glob(config_dir+"/testbench_*.yml"):
    yml = os.path.basename(yml_path)
    with open("template_testbench.py") as f:
        template = f.read()
        
    if not os.path.exists("output"): os.makedirs("output")
    tb = "output/"+yml.replace("yml", "py")
    with open(tb, 'w') as f:
        f.write(template.replace("!!!", yml))
    st = os.stat(tb)
    os.chmod(tb, st.st_mode | stat.S_IEXEC)
    print("Generating testbench:" , tb)
