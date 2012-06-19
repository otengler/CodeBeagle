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

import sys
import re
from PyQt4.QtCore import * 
from PyQt4.QtGui import *
from PyQt4.QtNetwork import *
import AppConfig
    
class UpdateCheck (QObject):
    newerVersionFound = pyqtSignal('QString')
    
    def __init__ (self,  parent=None):
        super(UpdateCheck, self).__init__(parent)
        self.lastUpdateCheck = None
        
    @pyqtSlot('QNetworkReply')
    def __checkUpdateResult(self,  reply):
        if reply.error() == QNetworkReply.NoError:
            status = int(reply.attribute(QNetworkRequest.HttpStatusCodeAttribute))
            if 2 == status/100:
                html = str (reply.readAll().data(),  "latin_1")
                reVersion = re.compile("CodeBeagle\.(\d+\.\d+\.\d+)\.(zip|7z)",re.IGNORECASE)
                cur=0
                versions = set ()
                while True:
                    result = reVersion.search(html, cur)
                    if result:
                        startPos, endPos = result.span()
                        versions.add(result.group(1))
                        cur = endPos
                    else:
                        break
                sortedVersions = sorted([ver for ver in versions],reverse=True)
                
                currentVersion = ".".join(AppConfig.appVersion.split(".")[0:3])
                if sortedVersions[0] > currentVersion:
                    self.newerVersionFound.emit(sortedVersions[0])
        
    # Initiates a check if there is a newer version of CodeBeagle available
    def checkForUpdates(self):
        now = QDateTime.currentDateTime()
        if self.lastUpdateCheck:
            nextCheck = QDateTime.fromMSecsSinceEpoch (self.lastUpdateCheck).addDays(7)
            if now < nextCheck:
                return
        self.lastUpdateCheck = now.toMSecsSinceEpoch()
        
        networkManager = QNetworkAccessManager(self)
        networkManager.finished.connect(self.__checkUpdateResult)
        url = QUrl("http://sourceforge.net/projects/codebeagle/files/")
        networkManager.get(QNetworkRequest(url))

if __name__ == "__main__":
    app = QApplication(sys.argv) 
    checker = UpdateCheck()
    checker.checkForUpdates()
    sys.exit(app.exec_()) 
    
