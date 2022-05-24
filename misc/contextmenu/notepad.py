# 'files' is populated with all file names

import subprocess
import time

def doIt():
    for file in files: # noqa: F821
        subprocess.Popen ([r"C:\windows\notepad.exe"] + [file])

doIt()
