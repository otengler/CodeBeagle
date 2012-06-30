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
from PyQt4.QtCore import * 
from PyQt4.QtGui import *
from  Ui_MainWindow import Ui_MainWindow
import AppConfig
import FileTools
from UpdateCheck import UpdateCheck
import UserHintDialog

userHintNewVersionAvailable = """
<p align='justify'>Version %(version)s is available for download. Do you want to visit the download page now?</p>
"""

def main(): 
    app = QApplication(sys.argv) 
    
    # Switch to application directory to be able to load the configuration and search scripts even if we are 
    # executed from a different working directory.
    FileTools.switchToAppDir()
    
    w = MainWindow() 
    w.show() 
    sys.exit(app.exec_()) 
    
class MainWindow (QMainWindow):
    def __init__ (self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.updateCheck = UpdateCheck(self)
        self.__restoreGeometryAndState()
        self.updateCheck.newerVersionFound.connect(self.newerVersionFound)
        self.updateCheck.checkForUpdates()
        
    def closeEvent(self,  event):
        if  AppConfig.appConfig().showCloseConfirmation:
            res = QMessageBox.question(self,
                                                         self.trUtf8("Really close?"),
                                                         self.trUtf8("Do you really want to close the application?"),
                                                         QMessageBox.StandardButtons(QMessageBox.No | QMessageBox.Yes),
                                                         QMessageBox.Yes)
            if QMessageBox.Yes != res:
                event.ignore()
                return
        
        self.updateCheck.shutdownUpdateCheck() # this waits for the update check thread to complete
        self.__saveGeometryAndState()
        event.accept()
        
    def newerVersionFound(self, version):
        text = userHintNewVersionAvailable % {"version":version}
        result = UserHintDialog.showUserHint (self, "newVersion"+version,  self.trUtf8("New version available"), text,  
                                                                    UserHintDialog.Yes, True,  UserHintDialog.No,  False,  bShowHintAgain=True)
        if result == UserHintDialog.Yes:
            url = QUrl ("http://sourceforge.net/projects/codebeagle/files/")
            QDesktopServices.openUrl (url)
        
    def __restoreGeometryAndState(self):
        settings = QSettings(AppConfig.appCompany, AppConfig.appName)
        if settings.value("geometry"):
            self.restoreGeometry(settings.value("geometry"))
        if settings.value("windowState"):
            self.restoreState (settings.value("windowState"))
        if settings.value("lastUpdateCheck"):
            self.updateCheck.lastUpdateCheck = settings.value("lastUpdateCheck")
        
    def __saveGeometryAndState (self):
        settings = QSettings(AppConfig.appCompany, AppConfig.appName)
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        if self.updateCheck.lastUpdateCheck:
            settings.setValue("lastUpdateCheck", self.updateCheck.lastUpdateCheck)

if __name__ == "__main__":
    main()
