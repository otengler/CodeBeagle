# -*- coding: utf-8 -*-
"""
Copyright (C) 2013 Oliver Tengler

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

from typing import Optional
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QDialog, QWidget
from tools.ExceptionTools import exceptionAsString
from widgets.SyntaxHighlighter import HighlightingRules
from .Ui_StackTraceMessageBox import Ui_StackTraceMessageBox

class StackTraceMessageBox (QDialog):
    def __init__ (self, parent: Optional[QWidget], title:str, text:str, stackTrace:str) -> None:
        super().__init__(parent)
        self.ui = Ui_StackTraceMessageBox()
        self.ui.setupUi(self)
        self.setProperty("shadeBackground", True) # fill background with gradient as defined in style sheet

        rules = HighlightingRules(self.font())
        keywords="import,from,def,class,return,if,else,elif,for,in,while,None"
        rules.addKeywords (keywords, QFont.Bold, Qt.GlobalColor.darkBlue)
        rules.addRule ("\".*\"", QFont.Normal, Qt.GlobalColor.darkGreen) # Quotations
        rules.addRule ("\\b[A-Za-z0-9_]+(?=\\()", QFont.Normal, Qt.GlobalColor.blue) # Functions
        self.ui.stackTraceTextEdit.highlighter.setHighlightingRules (rules)
        self.ui.stackTraceTextEdit.setPlainText(stackTrace)

        self.setTitle(title)
        self.setText(text)
        self.showDetails(False)

    def setTitle(self, title: str) -> None:
        self.setWindowTitle(title)

    def setText(self, text: str) -> None:
        self.ui.labelText.setText (text)

    @pyqtSlot(bool)
    def showDetails(self, bShow: bool) -> None:
        self.ui.stackTraceTextEdit.setVisible(bShow)
        self.adjustSize()
        if bShow:
            self.resize(self.width(),self.height()+200)

def show (parent: Optional[QWidget], title: str, text: str) -> None:
    stackTrace = exceptionAsString(None)
    dlg = StackTraceMessageBox(parent, title, text, stackTrace)
    dlg.exec()

def main() -> None:
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    try:
        1/0
    except:
        show(None,"Exception","Something went wrong")
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
