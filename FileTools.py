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

def fopen (name, mode='r'):
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

# Return a path where the application may store data. For Windows this is where APPDATA points to. 
# For Linux HOME should work.
def getAppDataPath (appName):
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
    
def getTempPath ():
    return os.path.expandvars("$TEMP")
    
# Switch to application directory. This helps to locate files by a relative path.
def switchToAppDir ():
    try:
        dirName = os.path.dirname(sys.argv[0])
        if dirName:
            os.chdir(dirName)
    except Exception as  e:
        print ("Failed to switch to application directory: " + str(e))
        
# Creates a directory during a context manager scope.
# with lockDir("C:\\dir"):
#     pass
class lockDir:
    def __init__(self,  name, retries=5, delay=200):
        self.name = name
        self.retries = retries
        self.delay = delay
        
    def __enter__(self):
        for i in range(self.retries):
            try:
                os.mkdir (self.name)
            except:
                time.sleep(self.delay/1000.0)
            else:
                return self
        raise RuntimeError("Failed to create lock directory")
       
    def __exit__(self, exc_type, exc_val, exc_tb):
        os.rmdir (self.name)
        return False

# Removes all character which are invalid for files
def removeInvalidFileChars (text):
    for c in "\\/:*?\"<>|":
        text = text.replace(c, "")
    return text
    

    
        

