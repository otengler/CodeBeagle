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

from typing import cast
from enum import IntEnum
from PyQt5.QtCore import Qt, pyqtSlot, QSettings
from PyQt5.QtWidgets import QDialog, QWidget, QPushButton
import AppConfig
from .Ui_UserHintDialog import Ui_UserHintDialog

class ButtonType(IntEnum):
    NoButton = 0
    NoResult = 1 # This is not a button but the result if the hint was not shown at all
    OK = 2
    Yes = 4
    No = 8

class UserHintDialog (QDialog):
    def __init__ (self, parent: QWidget) -> None:
        super().__init__(parent,  Qt.Tool)
        self.ui = Ui_UserHintDialog()
        self.ui.setupUi(self)
        self.setProperty("shadeBackground", True) # fill background with gradient as defined in style sheet
        self.ui.pushButton1.hide()
        self.ui.pushButton2.hide()
        self.button1: ButtonType = ButtonType.NoButton
        self.button2: ButtonType = ButtonType.NoButton
        self.closeButton = ButtonType.NoResult

    def setTitle(self, title: str) -> None:
        self.setWindowTitle(title)

    def setHtmlText(self, text: str) -> None:
        self.ui.textEditHint.setHtml (text)

    def setShowHintAgainCheckbox (self, bCheck: bool) -> None:
        if bCheck:
            self.ui.checkShowHint.setCheckState(Qt.Checked)
        else:
            self.ui.checkShowHint.setCheckState(Qt.Unchecked)

    def showHintAgain(self) -> bool:
        return cast(bool, self.ui.checkShowHint.checkState() == Qt.Checked)

    def addButton (self, buttonID: ButtonType, bIsDefault:bool=False) -> None:
        if not self.button1:
            self.button1 = buttonID
            self.__configButton(self.ui.pushButton1, buttonID, bIsDefault)
        elif not self.button2:
            self.button2 = buttonID
            self.__configButton(self.ui.pushButton2, buttonID, bIsDefault)
        else:
            raise RuntimeError("No more buttons available")

    def __configButton(self, button: QPushButton, buttonID: ButtonType, bIsDefault: bool) -> None:
        if ButtonType.OK == buttonID:
            button.setText(self.tr("OK"))
        elif ButtonType.Yes == buttonID:
            button.setText(self.tr("Yes"))
        elif ButtonType.No == buttonID:
            button.setText(self.tr("No"))
        else:
            raise RuntimeError("Unknown button")
        if bIsDefault:
            button.setDefault(True)
        button.show()

    @pyqtSlot()
    def button1clicked(self) -> None:
        self.closeButton = self.button1
        self.accept()

    @pyqtSlot()
    def button2clicked(self) -> None:
        self.closeButton = self.button2
        self.accept()

# Checks if a particular user hint would be shown by calling "showUserHint".
def hintWouldBeShown(hintID: str) -> bool:
    settings = QSettings(AppConfig.appCompany, AppConfig.appName)
    hintStore = "hint_" + hintID
    value = settings.value(hintStore)
    if value is None or int(value):
        return True
    return False

# Show the user a hint which can be suppressed with a check box in the future.
# hintID is an arbitrary string which must be unique for each user hint. The return value is the button which was pressed to
# close the dialog or NoResult if the hint dialog was not shown or closed by any other mean.
def showUserHint (parent: QWidget, hintID: str, title: str, htmlText: str, button1: ButtonType, default1:bool=True,
                  button2:ButtonType=None, default2:bool=False, bShowHintAgain:bool=False) -> ButtonType:

    settings = QSettings(AppConfig.appCompany, AppConfig.appName)
    hintStore = "hint_" + hintID
    value = settings.value(hintStore)
    if value is None or int(value):
        dialog = UserHintDialog(parent)
        dialog.setTitle(title)
        dialog.setHtmlText(htmlText)
        dialog.setShowHintAgainCheckbox (bShowHintAgain)
        dialog.addButton(button1, default1)
        if button2:
            dialog.addButton(button2, default2)
        dialog.activateWindow()
        if dialog.exec():
            settings.setValue(hintStore, int(dialog.showHintAgain()))
            return dialog.closeButton
    return ButtonType.NoResult

def main() -> None:
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    showUserHint (None, "test", "Create location", "Create an initial search location?",  ButtonType.Yes, True, ButtonType.No)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
