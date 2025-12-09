# -*- coding: utf-8 -*-
"""
Copyright (C) 2021 Oliver Tengler

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from enum import IntEnum
import sys
import os
import codecs
import time
import collections
from typing import IO, DefaultDict, Any, Optional, Literal, Tuple, cast
import unittest

# pylint: disable=import-outside-toplevel

def getModulePath() -> str:
    import __main__
    return os.path.split(__main__.__file__)[0]

class Encoding(IntEnum):
    Default = 1,
    UTF8 = 2,
    UTF8_BOM = 3,
    UTF16_BOM = 4

def fopenEx (name:str, mode: str='r', defaultEncoding: Optional[str]="latin_1") -> Tuple[IO[str], Encoding]:
    f = open(name, mode, -1, "latin-1")
    try:
        start = f.read(3)
        if len(start) >=3:
            if codecs.BOM_UTF8 == bytes(start[:3],"latin-1"):
                f.close()
                return (open (name, mode, -1, "utf_8_sig"), Encoding.UTF8_BOM)
        if len(start) >=2:
            bom = bytes(start[:2],"latin-1")
            if codecs.BOM_UTF16_LE == bom:
                f.close()
                f = open (name, mode, -1, "utf_16_le")
                f.seek(2)
                return (f, Encoding.UTF16_BOM)
            if codecs.BOM_UTF16_BE == bom:
                f.close()
                f = open (name, mode, -1, "utf_16_be")
                f.seek(2)
                return (f, Encoding.UTF16_BOM)
            if defaultEncoding and defaultEncoding != "latin-1":
                f.close()
                return (open(name, mode, -1, defaultEncoding), Encoding.Default)
        f.seek(0)
        return (f, Encoding.Default)
    except:
        f.close()
        raise

def fopen (name: str, mode: str='r', defaultEncoding: str="latin_1") -> IO[str]:
    return fopenEx(name, mode, defaultEncoding)[0]

def freadall(name: str, mode: str='r', defaultEncoding: str="latin_1") -> str:
    """
    Reads the whole content of a text file. If the file does not contain a byte order mark
    the content is first decoded using UTF8 and if this fails using the given defaultEncoding
    if that differs from UTF8.
    """
    return freadallEx(name, mode, defaultEncoding)[0]

def freadallEx(name: str, mode: str='r', defaultEncoding: str="latin_1") -> Tuple[str, Encoding]:
    """
    Reads the whole content of a text file. If the file does not contain a byte order mark
    the content is first decoded using UTF8 and if this fails using the given defaultEncoding
    if that differs from UTF8.
    Returns the text and the encoding.
    """
    try:
        file, encoding = fopenEx(name, mode, defaultEncoding="utf_8")
        with file:
            text = file.read()
            if encoding == Encoding.Default:
                encoding = Encoding.UTF8
            return (text, encoding)
    except:
        if defaultEncoding == "utf_8": # already tried that
            raise
        file, _ = fopenEx(name, mode, defaultEncoding=defaultEncoding)
        with file:
            text = file.read()
            return (text, Encoding.Default)

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
    if "HOME" in os.environ:
        return os.path.expandvars("$HOME")
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
        self.pidfile: Optional[IO[str]] = None

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
    """Check whether pid exists in the current process table."""
    if sys.platform != "win32":
        import errno
        if pid < 0:
            return False
        try:
            os.kill(pid, 0)
        except OSError as e:
            return e.errno == errno.EPERM
        else:
            return True
    else:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        synchronize = 0x100000
        process = kernel32.OpenProcess(synchronize, 0, pid)
        if not process:
            return False
        kernel32.CloseHandle(process)
        return True

def correctPath(name: str) -> str:
    if os.path.sep == "/":
        return name
    return name.replace("/", os.path.sep)

class TestConfig(unittest.TestCase):
    def test(self) -> None:
        res = freadallEx("encodings\\latin-1.txt")
        self.assertEqual(res[0], "äö")
        self.assertEqual(res[1], Encoding.Default)
        res = freadallEx("encodings\\utf-8.txt")
        self.assertEqual(res[0], "äö")
        self.assertEqual(res[1], Encoding.UTF8_BOM)
        res = freadallEx("encodings\\utf-8-no-bom.txt")
        self.assertEqual(res[0], "äö")
        self.assertEqual(res[1], Encoding.UTF8)
        res = freadallEx("encodings\\utf-16-be.txt")
        self.assertEqual(res[0], "äö")
        self.assertEqual(res[1], Encoding.UTF16_BOM)
        res = freadallEx("encodings\\utf-16-le.txt")
        self.assertEqual(res[0], "äö")
        self.assertEqual(res[1], Encoding.UTF16_BOM)       

if __name__ == "__main__":
    unittest.main()

