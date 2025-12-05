# 'files' is populated with all file names

import subprocess
import time

def doIt() -> None:
    for file in files: # type: ignore[name-defined]
        subprocess.Popen ([r"C:\windows\notepad.exe"] + [file])

doIt()
