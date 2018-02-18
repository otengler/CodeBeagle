#! /usr/bin/python3
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
from PyQt5.QtCore import QSettings, QUrl, pyqtSlot
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
import tools.FileTools as FileTools
import dialogs.UserHintDialog as UserHintDialog
import AppConfig
from UpdateCheck import UpdateCheck
from Ui_MainWindow import Ui_MainWindow


userHintNewVersionAvailable = """
<p align='justify'>Version %(version)s is available for download. Do you want to visit the download page now?</p>
"""

def main():
    app = QApplication(sys.argv)

    # Switch to application directory to be able to load the configuration and search scripts even if we are
    # executed from a different working directory.
    FileTools.switchToAppDir()

    wnd = MainWindow()
    wnd.show()
    sys.exit(app.exec_())

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        # Restore last used search location name
        self.appSettings = QSettings(AppConfig.appCompany, AppConfig.appName)
        if self.appSettings.value("lastUsedSearchLocation"):
            AppConfig.setLastUsedConfigName(
                self.appSettings.value("lastUsedSearchLocation"))
        # Now setup UI. This already uses the restored search location name
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.initialWindowTitle = self.windowTitle()
        self.ui.tabWidget.requestWindowTitleChange.connect(self.changeWindowTitle)
        self.__restoreGeometryAndState()
        # Finally prepare and launch the update check
        self.updateCheck = UpdateCheck(self)
        if self.appSettings.value("lastUpdateCheck"):
            self.updateCheck.lastUpdateCheck = int(
                self.appSettings.value("lastUpdateCheck"))
        self.updateCheck.newerVersionFound.connect(self.newerVersionFound)
        self.updateCheck.checkForUpdates()

    def closeEvent(self, event):
        if AppConfig.appConfig().showCloseConfirmation:
            res = QMessageBox.question(self,
                                       self.tr("Really close?"),
                                       self.tr(
                                           "Do you really want to close the application?"),
                                       QMessageBox.StandardButtons(
                                           QMessageBox.No | QMessageBox.Yes),
                                       QMessageBox.Yes)
            if QMessageBox.Yes != res:
                event.ignore()
                return

        # this waits for the update check thread to complete
        self.updateCheck.shutdownUpdateCheck()
        if self.updateCheck.lastUpdateCheck:
            self.appSettings.setValue(
                "lastUpdateCheck", self.updateCheck.lastUpdateCheck)
        self.appSettings.setValue(
            "lastUsedSearchLocation", AppConfig.lastUsedConfigName())
        self.__saveGeometryAndState()
        event.accept()

    def newerVersionFound(self, version):
        text = userHintNewVersionAvailable % {"version": version}
        result = UserHintDialog.showUserHint(self, "newVersion" + version, self.tr("New version available"), text,
                                             UserHintDialog.Yes, True, UserHintDialog.No, False, bShowHintAgain=True)
        if result == UserHintDialog.Yes:
            url = QUrl("http://sourceforge.net/projects/codebeagle/files/")
            QDesktopServices.openUrl(url)

    def __restoreGeometryAndState(self):
        if self.appSettings.value("geometry"):
            self.restoreGeometry(self.appSettings.value("geometry"))
        if self.appSettings.value("windowState"):
            self.restoreState(self.appSettings.value("windowState"))

    def __saveGeometryAndState(self):
        self.appSettings.setValue("geometry", self.saveGeometry())
        self.appSettings.setValue("windowState", self.saveState())

    @pyqtSlot(str)
    def changeWindowTitle(self, name):
        if name:
            self.setWindowTitle(self.initialWindowTitle + "  -  " + name)
        else:
            self.setWindowTitle(self.initialWindowTitle)

if __name__ == "__main__":
    main()
