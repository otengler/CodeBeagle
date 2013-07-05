# -*- coding: utf-8 -*-
"""
Copyright (C) 2012 Oliver Tengler

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

import re
from PyQt4.QtCore import * 
from PyQt4.QtGui import *
import AppConfig
from urllib.request import urlopen

# Formats a version string "1.1.2" as "01.01.02" which makes the version easily comparable
def formatVersion (version):
    return ".".join(("%02u" % i) for i in map(int,version.split(".")))
    
class UpdateCheckThread (QThread):
    def __init__(self):
        super(QThread, self).__init__(None) # Called with None to get rid of the thread once the python object is destroyed
        self.latestVersion = ""
        
    def run(self):
        try:
            self.__runInternal()
        except Exception:
            pass
            
    def __runInternal(self):
        html = str (urlopen("http://sourceforge.net/projects/codebeagle/files").readall(), "latin_1")
        reVersion = re.compile("CodeBeagle[-\w]*\.(\d+\.\d+\.\d+)\.(zip|7z)",re.IGNORECASE)
        cur=0
        versions = set ()
        while True:
            result = reVersion.search(html, cur)
            if result:
                startPos, endPos = result.span()
                versions.add((formatVersion(result.group(1)),  result.group(1)))
                cur = endPos
            else:
                break
        sortedVersions = sorted([ver for ver in versions],reverse=True)
        self.latestVersion = sortedVersions[0][1]
    
# Check for program updates
class UpdateCheck (QObject):
    newerVersionFound = pyqtSignal('QString')
    
    def __init__ (self,  parent=None):
        super(UpdateCheck, self).__init__(parent)
        self.lastUpdateCheck = None
        self.updateThread = None

    # Initiates a check if there is a newer version of CodeBeagle available
    def checkForUpdates(self):
        updateCheckPeriod = AppConfig.appConfig().updateCheckPeriod
        # 0 disables the update check
        if 0 == updateCheckPeriod:
            return
        
        now = QDateTime.currentDateTime()
        if self.lastUpdateCheck:
            nextCheck = QDateTime.fromMSecsSinceEpoch (self.lastUpdateCheck).addDays(updateCheckPeriod)
            if now < nextCheck:
                return
        self.lastUpdateCheck = now.toMSecsSinceEpoch()
        
        self.updateThread = UpdateCheckThread ()
        self.updateThread.finished.connect(self.__checkFinished)
        self.updateThread.terminated.connect(self.__checkFinished)
        self.updateThread.start()
        
    def shutdownUpdateCheck (self):
        if self.updateThread:
            self.updateThread.wait()
            self.updateThread = None
        
    def __checkFinished(self):
        if self.updateThread and self.updateThread.latestVersion:
            currentVersion = ".".join(AppConfig.appVersion.split(".")[0:3])
            if formatVersion(self.updateThread.latestVersion) > formatVersion(currentVersion):
                self.newerVersionFound.emit(self.updateThread.latestVersion)
            self.shutdownUpdateCheck()

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv) 
    checker = UpdateCheck()
    checker.checkForUpdates()
    sys.exit(app.exec_()) 
    
