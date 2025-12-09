#! /usr/bin/python3
# -*- coding: utf-8 -*-
"""
Copyright (C) 2011 Oliver Tengler

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

from tools import FileTools
# Switch to application directory to be able to load the configuration and search scripts even 
# if we are executed from a different working directory. This must even be done before other imports. 
FileTools.switchToAppDir()

import os, sys, subprocess, shutil
from PyQt5.QtCore import QSettings, QUrl, pyqtSlot, Qt
from PyQt5.QtGui import QDesktopServices, QCloseEvent, QColor
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from dialogs.UserHintDialog import ButtonType, showUserHint
from dialogs.RegExTesterDlg import RegExTesterDlg
import AppConfig
from widgets.LineNumberArea import LineNumberArea
from widgets.HighlightingTextEdit import HighlightingTextEdit
from widgets.SyntaxHighlighter import SyntaxHighlighter
from PathVisualizerDelegate import PathVisualizerDelegate
from UpdateCheck import UpdateCheck
from SourceViewer import SourceViewer
from Ui_MainWindow import Ui_MainWindow
from typing import Optional
from tools.CustomFont import installCustomFont

userHintNewVersionAvailable = """
<p align='justify'>Version %(version)s is available for download. Do you want to visit the download page now?</p>
"""

def main() -> None:
    # dark title bar on Win
    if sys.platform == "win32":
        if AppConfig.appConfig().theme == AppConfig.darkTheme:
            # https://www.qt.io/blog/dark-mode-on-windows-11-with-qt-6.5
            os.environ["QT_QPA_PLATFORM"] = "windows:darkmode=1"
    elif sys.platform == "linux":
        installDesktopFile()

    app = QApplication(sys.argv)

    installCustomFont()
    configureTheme(app)

    if AppConfig.appConfig().fontSize != -1:
        font = app.font()
        font.setPointSize(AppConfig.appConfig().fontSize)
        app.setFont(font)

    wnd = MainWindow()
    wnd.show()
    sys.exit(app.exec_())

def configureTheme(app: QApplication) -> None: 
    if AppConfig.appConfig().theme == AppConfig.darkTheme:
        from themes import dark
        LineNumberArea.areaColor = QColor(dark.DarkPalette.COLOR_BACKGROUND_NORMAL).darker(120)
        PathVisualizerDelegate.newPathColor = QColor(204,204,204)
        PathVisualizerDelegate.samePathColor = QColor(dark.DarkPalette.COLOR_FOREGROUND_DARK)
        PathVisualizerDelegate.fileColor = QColor(dark.DarkPalette.COLOR_SELECTION_LIGHT).lighter(150)
        PathVisualizerDelegate.selectedFileColor = QColor(dark.DarkPalette.COLOR_SELECTION_LIGHT).lighter(200)
        PathVisualizerDelegate.selectedPathColor = QColor(dark.DarkPalette.COLOR_SELECTION_LIGHT).lighter(150)
        PathVisualizerDelegate.selectionBackground = QColor(dark.DarkPalette.COLOR_BACKGROUND_LIGHT)
        HighlightingTextEdit.highlightOutlineColor = QColor(dark.DarkPalette.COLOR_BACKGROUND_LIGHT).lighter(150)
        HighlightingTextEdit.highlightSolidBackgroundColor = QColor(dark.DarkPalette.COLOR_BACKGROUND_LIGHT).lighter(140)
        HighlightingTextEdit.highlightSolidForegroundColor = None
        SourceViewer.currentLineBackgroundColor = QColor(dark.DarkPalette.COLOR_BACKGROUND_DARK).lighter(130)
        SourceViewer.currentMatchLineBackgroundColor = QColor(dark.DarkPalette.COLOR_SELECTION_DARK).darker(120)
        SyntaxHighlighter.matchBackgroundColor = QColor(Qt.GlobalColor.yellow).darker(120)
        SyntaxHighlighter.matchForegroundColor = Qt.GlobalColor.black
        RegExTesterDlg.matchBackgroundColor = QColor(Qt.GlobalColor.yellow).darker(120)
        RegExTesterDlg.bracketColor = QColor(200,200,240)
        RegExTesterDlg.repeatColor = QColor(240,200,200)
        dark.apply_stylesheet(app)
    else:
        from themes import light
        light.apply_stylesheet(app)

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        # Restore last used search location name
        self.appSettings = QSettings(AppConfig.appCompany, AppConfig.appName)
        if self.appSettings.value("lastUsedSearchLocation"):
            AppConfig.setLastUsedConfigName(
                self.appSettings.value("lastUsedSearchLocation"))
        # Now setup UI. This already uses the restored search location name
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]
        self.initialWindowTitle = self.windowTitle()
        self.ui.tabWidget.requestWindowTitleChange.connect(self.changeWindowTitle)
        self.__restoreGeometryAndState()
        # Finally prepare and launch the update check
        lastUpdateCheck: Optional[int] = None
        if self.appSettings.value("lastUpdateCheck"):
            lastUpdateCheck = int(self.appSettings.value("lastUpdateCheck"))
        self.updateCheck = UpdateCheck(self, lastUpdateCheck)
        self.updateCheck.newerVersionFound.connect(self.newerVersionFound)
        self.updateCheck.checkForUpdates()

    def closeEvent(self, event: Optional[QCloseEvent]) -> None:
        if not event:
            return
        if AppConfig.appConfig().showCloseConfirmation:
            res = QMessageBox.question(self,
                                       self.tr("Really close?"),
                                       self.tr("Do you really want to close the application?"),
                                       QMessageBox.StandardButtons(QMessageBox.No | QMessageBox.Yes),
                                       QMessageBox.Yes)
            if QMessageBox.Yes != res:
                event.ignore()
                return

        # this waits for the update check thread to complete
        self.updateCheck.shutdownUpdateCheck()
        if self.updateCheck.lastUpdateCheck:
            self.appSettings.setValue("lastUpdateCheck", self.updateCheck.lastUpdateCheck)
        self.appSettings.setValue(
            "lastUsedSearchLocation", AppConfig.lastUsedConfigName())
        self.__saveGeometryAndState()
        event.accept()

    def newerVersionFound(self, version: str) -> None:
        text = userHintNewVersionAvailable % {"version": version}
        result = showUserHint(self, "newVersion" + version, self.tr("New version available"), text,
                              ButtonType.Yes, True, ButtonType.No, False, bShowHintAgain=True)
        if result == ButtonType.Yes:
            url = QUrl("https://github.com/otengler/CodeBeagle/releases/latest")
            QDesktopServices.openUrl(url)

    def __restoreGeometryAndState(self) -> None:
        if self.appSettings.value("geometry"):
            self.restoreGeometry(self.appSettings.value("geometry"))
        if self.appSettings.value("windowState"):
            self.restoreState(self.appSettings.value("windowState"))

    def __saveGeometryAndState(self) -> None:
        self.appSettings.setValue("geometry", self.saveGeometry())
        self.appSettings.setValue("windowState", self.saveState())

    @pyqtSlot(str)
    def changeWindowTitle(self, name: str) -> None:
        if name:
            self.setWindowTitle(self.initialWindowTitle + "  -  " + name)
        else:
            self.setWindowTitle(self.initialWindowTitle)

def installDesktopFile() -> None:
    try:
        targetDir = os.path.join(os.environ["HOME"], ".local/share/applications")
        if not os.path.isdir(targetDir):
            os.makedirs(targetDir)
        targetFile = os.path.join(targetDir, "CodeBeagle.desktop")
        if os.path.isfile(targetFile):
            return
        print(f"Installing .desktop file to {targetFile}")
        with open("resources/CodeBeagle.desktop","r") as input:
            desktopFile = input.read()        
        desktopFile = desktopFile.replace("{InstallDir}", os.getcwd())
        with open(targetFile, "w") as output:
            output.write(desktopFile)
        if shutil.which("update-desktop-database"):
            print("Updating desktop database")
            subprocess.Popen (["update-desktop-database", targetDir])
    except Exception as e:
        print("Failed to install Desktop file: " + str(e))

if __name__ == "__main__":
    main()
