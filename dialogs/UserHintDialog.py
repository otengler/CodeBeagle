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

from PyQt5.QtCore import Qt, pyqtSlot, QSettings
from PyQt5.QtWidgets import QDialog
import AppConfig
from .Ui_UserHintDialog import Ui_UserHintDialog

NoResult = 1 # This is not a button but the result if the hint was not shown at all
OK = 2
Yes = 4
No = 8

class UserHintDialog (QDialog):
    def __init__ (self,  parent):
        super(UserHintDialog, self).__init__(parent,  Qt.Tool)
        self.ui = Ui_UserHintDialog()
        self.ui.setupUi(self)
        self.setProperty("shadeBackground", True) # fill background with gradient as defined in style sheet
        self.ui.pushButton1.hide()
        self.ui.pushButton2.hide()
        self.button1 = None
        self.button2 = None
        self.closeButton = NoResult

    def setTitle(self, title):
        self.setWindowTitle(title)

    def setHtmlText(self, text):
        self.ui.textEditHint.setHtml (text)

    def setShowHintAgainCheckbox (self,  bCheck):
        if bCheck:
            self.ui.checkShowHint.setCheckState(Qt.Checked)
        else:
            self.ui.checkShowHint.setCheckState(Qt.Unchecked)

    def showHintAgain(self):
        return self.ui.checkShowHint.checkState() == Qt.Checked

    def addButton (self,  buttonID,  bIsDefault=False):
        if not self.button1:
            self.button1 = buttonID
            self.__configButton(self.ui.pushButton1, buttonID, bIsDefault)
        elif not self.button2:
            self.button2 = buttonID
            self.__configButton(self.ui.pushButton2, buttonID, bIsDefault)
        else:
            raise RuntimeError("No more buttons available")

    def __configButton(self,  button, buttonID,  bIsDefault):
        if OK == buttonID:
            button.setText(self.tr("OK"))
        elif Yes == buttonID:
            button.setText(self.tr("Yes"))
        elif No == buttonID:
            button.setText(self.tr("No"))
        else:
            raise RuntimeError("Unknown button")
        if bIsDefault:
            button.setDefault(True)
        button.show()

    @pyqtSlot()
    def button1clicked(self):
        self.closeButton = self.button1
        self.accept()

    @pyqtSlot()
    def button2clicked(self):
        self.closeButton = self.button2
        self.accept()

# Checks if a particular user hint would be shown by calling "showUserHint".
def hintWouldBeShown(hintID):
    settings = QSettings(AppConfig.appCompany, AppConfig.appName)
    hintStore = "hint_" + hintID
    value = settings.value(hintStore)
    if value is None or int(value):
        return True
    return False

# Show the user a hint which can be suppressed with a check box in the future.
# hintID is an arbitrary string which must be unique for each user hint. The return value is the button which was pressed to
# close the dialog or NoResult if the hint dialog was not shown or closed by any other mean.
def showUserHint (parent,  hintID,  title,  htmlText,  button1,  default1=True,  button2=None, default2=False,  bShowHintAgain=False):
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
    return NoResult

def main():
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    showUserHint (None, "test",  "Create location",  "Create an initial search location?",  Yes,  True,  No)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
