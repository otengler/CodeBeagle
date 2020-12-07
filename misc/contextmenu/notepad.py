# 'files' is populated with all file names

import subprocess
import time

def doIt():
    for file in files:
        subprocess.Popen ([r"C:\windows\notepad.exe"] + [file])

doIt()
