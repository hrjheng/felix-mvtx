<!---
Please read this!

Before opening a new issue, make sure to search for keywords in the issues
filtered by the "bug" label.

and verify the issue you're about to submit isn't a duplicate.
--->

### Summary

(Summarize the bug encountered concisely)

### Describe your setup

(Summarize the setup you are using; the more information you provide, the easier it will be to reproduce it and fix it)

### Software Version

(Upload here the output of ```make bug_report``` run from the main folder of the repository.)

### Bitfile version

(Paste here the output of

```shell
./testbench.py cru initialize --gbt_ch=<CH>  # Replace <CH> with the channel where the Readout Unit is connected
./testbench.py cru setGbtTxMux 2
./testbench.py version
```

run from ```software/py``` - please use code blocks (```) to format console output, logs, and code as it's very hard to read otherwise.
If it does not work, note it here.)

### Steps to reproduce

(How one can reproduce the issue - this is very important)

### What is the current *bug* behavior?

(What actually happens)

### What is the expected *correct* behavior?

(What you should see instead)

### Relevant logs and/or screenshots

(Paste any relevant logs - please use code blocks (```) to format console output,
logs, and code as it's very hard to read otherwise.)

### Possible fixes

(If you can, link to the line of code that might be responsible for the problem)

/label ~bug
