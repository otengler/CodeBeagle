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

import os
import codecs

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
        location = "$APPDATA"
    elif "HOME" in os.environ:
        location = "$HOME"
        appName = "." + appName # By convention config data is stored with a leading dot
    else:
        raise RuntimeError("Path to app data not found. Neither APPDATA nor HOME is defined")
    location = os.path.join(location, appName)
    location += os.path.sep
    return os.path.expandvars(location)
            
