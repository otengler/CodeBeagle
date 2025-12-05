# -*- coding: utf-8 -*-
"""
Copyright (C) 2012 Oliver Tengler

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

import os, json
from typing import Optional
from urllib.request import urlopen
from PyQt5.QtCore import QThread, QObject, pyqtSignal, QDateTime
import AppConfig

def formatVersion (version: str) -> str:
    """Formats a version string "1.1.2" as "01.01.02" which makes the version easily comparable."""
    return ".".join(("%02u" % i) for i in map(int,version.split(".")))

class UpdateCheckThread (QThread):
    def __init__(self) -> None:
        super().__init__(None) # Called with None to get rid of the thread once the python object is destroyed
        self.latestVersion = ""

    def run(self) -> None:
        try:
            self.__runInternal()
        except Exception:
            from tools.ExceptionTools import exceptionAsString
            print(exceptionAsString())

    def __runInternal(self) -> None:
        if sys.platform != "win32":
            # MAC and Linux: Use the certificates provided by the certifi package
            import ssl, certifi
            url = urlopen("https://raw.githubusercontent.com/otengler/CodeBeagle/main/VERSION", context=ssl.create_default_context(cafile=certifi.where()))
        else:
            # Under Windows Python seems to use the certificate store
            url = urlopen("https://raw.githubusercontent.com/otengler/CodeBeagle/main/VERSION")
        versionStr = str (url.read(), "utf8")
        versionDoc = json.loads(versionStr)
        if "version" in versionDoc:
            self.latestVersion = versionDoc["version"]

class UpdateCheck (QObject):
    """
    Check for program updates.
    """
    newerVersionFound = pyqtSignal('QString')

    def __init__ (self,  parent: Optional[QObject] = None, lastUpdateCheck: Optional[int] = None) -> None:
        super().__init__(parent)
        self.lastUpdateCheck: Optional[int] = lastUpdateCheck
        self.updateThread: Optional[UpdateCheckThread] = None

    def checkForUpdates(self, forceCheck: bool = False) -> None:
        """Initiates a check if there is a newer version of CodeBeagle available."""
        updateCheckPeriod = AppConfig.appConfig().updateCheckPeriod
        # 0 disables the update check
        if updateCheckPeriod == 0:
            return

        if not forceCheck:
            now = QDateTime.currentDateTime()
            if self.lastUpdateCheck:
                nextCheck = QDateTime.fromMSecsSinceEpoch (self.lastUpdateCheck).addDays(updateCheckPeriod)
                if now.secsTo(nextCheck) > 0:
                    return
            self.lastUpdateCheck = now.toMSecsSinceEpoch()

        self.updateThread = UpdateCheckThread ()
        self.updateThread.finished.connect(self.__checkFinished)
        self.updateThread.start()

    def shutdownUpdateCheck (self) -> None:
        if self.updateThread:
            self.updateThread.wait()
            self.updateThread = None

    def __checkFinished(self) -> None:
        if self.updateThread and self.updateThread.latestVersion:
            currentVersion = ".".join(AppConfig.appVersion.split(".")[0:3])
            if formatVersion(self.updateThread.latestVersion) > formatVersion(currentVersion):
                self.newerVersionFound.emit(self.updateThread.latestVersion)
            self.shutdownUpdateCheck()

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    checker = UpdateCheck()
    checker.checkForUpdates()
    sys.exit(app.exec_())