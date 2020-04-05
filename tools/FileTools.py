# -*- coding: utf-8 -*-
"""
Copyright (C) 2011 Oliver Tengler

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import sys
import os
import codecs
import time
import collections
from typing import IO, DefaultDict, Any, Optional, Literal

def fopen (name:str, mode: str='r') -> IO:
    f = open(name, mode, -1, "latin_1")
    try:
        start = f.read(3)
        if len(start) >=3:
            if codecs.BOM_UTF8 == bytes(start[:3],"latin_1"):
                f.close()
                return open (name, mode, -1, "utf_8_sig")
        if len(start) >=2:
            if codecs.BOM_UTF16 == bytes(start[:2],"latin_1"):
                f.close()
                return open (name, mode, -1, "utf_16")
        f.seek(0)
        return f
    except:
        f.close()
        raise

def getAppDataPath (appName: str) -> str:
    """
    Return a path where the application may store data. For Windows this is where APPDATA points to.
    For Linux HOME should work.
    """
    if "APPDATA" in os.environ:
        appdata = os.path.expandvars("$APPDATA")
        location = os.path.join(os.path.split(appdata)[0],"Local")
        if not os.path.isdir(location):
            location = appdata
    elif "HOME" in os.environ:
        location = os.path.expandvars("$HOME")
        appName = "." + appName # By convention config data is stored with a leading dot
    else:
        location = ""
    location = os.path.join(location, appName)
    location += os.path.sep
    return location

def getTempPath () -> str:
    """Return a path which can be used to store temporary data"""
    if "TEMP" in os.environ:
        return os.path.expandvars("$TEMP")
    elif "HOME" in os.environ:
        return os.path.expandvars("$HOME")
    else:
        return ""

def switchToAppDir () -> None:
    """Switch to application directory. This helps to locate files by a relative path."""
    try:
        dirName = os.path.dirname(sys.argv[0])
        if dirName:
            os.chdir(dirName)
    except Exception as  e:
        print ("Failed to switch to application directory: " + str(e))

class LockDir:
    """
    Creates a directory during a context manager scope.
    with LockDir("C:\\dir"):
        pass
    """
    def __init__(self,  name: str, retries: int=5, delay: int=200) -> None:
        self.name = name
        self.retries = retries
        self.delay = delay

    def __enter__(self) -> object:
        for _ in range(self.retries):
            try:
                os.mkdir (self.name)
            except Exception as e:
                print ("LockDir: " + str(e))
                time.sleep(self.delay/1000.0)
            else:
                return self
        raise RuntimeError("Failed to create lock directory")

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Literal[False]:
        os.rmdir (self.name)
        return False # do not suppress exception

def removeInvalidFileChars (text: str) -> str:
    """Removes all character which are invalid for files."""
    for c in "\\/:*?\"<>|":
        text = text.replace(c, "")
    return text

def getMostCommonExtensionInDirectory (directory: str) -> str:
    try:
        entries = os.listdir(directory)
    except:
        return ""
    m:DefaultDict[str,int] = collections.defaultdict(lambda:0)
    count = 0
    mostCommon = ""
    for entry in entries:
        ext = os.path.splitext(entry)[1].lower()
        if ext:
            curr = m[ext]+1
            m[ext]=curr
            if curr > count:
                count = curr
                mostCommon = ext
                if count > len(entries)/2:
                    break
    return mostCommon

class PidFile:
    """Pass full path to file where current process ID is stored."""
    def __init__(self, name: str) -> None:
        self.name = name
        self.pidfile: Optional[IO] = None

    def exists(self) -> bool:
        """Reads the PID from a pid file or returns 0 if there is no PID file."""
        return os.path.isfile(self.name)

    def read(self) -> int:
        try:
            with open(self.name, "r") as file:
                pid = int(file.read())
        except:
            return 0
        return pid

    def remove(self) -> None:
        if os.path.isfile(self.name):
            try:
                os.unlink(self.name)
            except:
                pass

    def __enter__(self) -> object:
        pid = os.getpid()
        try:
            self.pidfile = open(self.name, "x")
            self.pidfile.write("%u" % pid)
            self.pidfile.flush()
        except:
            print("Failed to create PID file at '%s'" % self.name)
            raise
        return self

    def __exit__(self, exc_type: None, exc_val: None, exc_tb: None) -> Literal[False]:
        if self.pidfile:
            self.pidfile.close()
        self.remove()
        return False # do not suppress exception

def isProcessAlive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except:
        return False

def correctPath(name: str) -> str:
    if os.path.sep == "/":
        return name
    return name.replace("/", os.path.sep)
