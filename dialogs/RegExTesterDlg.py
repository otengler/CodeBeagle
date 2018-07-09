# -*- coding: utf-8 -*-
"""
Copyright (C) 2018 Oliver Tengler

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
from typing import List, Optional, Pattern, Match
from enum import IntEnum
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont
from PyQt5.QtWidgets import QDialog, QApplication, QWidget
from .Ui_RegExTesterDlg import Ui_RegExTesterDlg

class ExprHighlighter(QSyntaxHighlighter):
    def __init__(self, parent: QWidget=None) -> None:
        super().__init__(parent)

        self.bracketFormat = QTextCharFormat()
        self.bracketFormat.setFontWeight(QFont.Bold)
        self.bracketFormat.setForeground(Qt.darkBlue)

        self.repeatFormat = QTextCharFormat()
        self.repeatFormat.setFontWeight(QFont.Bold)
        self.repeatFormat.setForeground(Qt.darkRed)

    def highlightBlock(self, text: str) -> None:
        for i, c in enumerate(text):
            if c in ("(", ")", "{", "}", "[", "]"):
                self.setFormat(i, 1,  self.bracketFormat)
            if c in ("*", "+", "?"):
                self.setFormat(i, 1,  self.repeatFormat)

class SearchModes(IntEnum):
    SearchFirst = 1
    SearchAll = 2
    Match = 3

class TextHighlighter(QSyntaxHighlighter):
    def __init__(self, parent: QWidget=None) -> None:
        super().__init__(parent)

        self.matchFormat = QTextCharFormat()
        self.matchFormat.setBackground(Qt.yellow)
        self.matchFormat.setForeground(Qt.darkBlue)
        self.groupFormats: List[QTextCharFormat] = []
        for color in (Qt.green, Qt.cyan, Qt.gray, Qt.blue,  Qt.magenta):
            groupFormat = QTextCharFormat()
            groupFormat.setBackground(color)
            groupFormat.setForeground(Qt.darkBlue)
            self.groupFormats.append(groupFormat)

        self.expr: Optional[Pattern] = None
        self.iMode = SearchModes.SearchFirst
        self.bColorizeGroups = False

    def setMode(self,  iMode: SearchModes) -> None:
        self.iMode = iMode
        self.rehighlight()

    def setExpr (self, exprText: str) -> None:
        try:
            self.expr = re.compile(exprText, re.IGNORECASE)
        except:
            self.expr = None
        self.rehighlight()

    def setColorizeGroups(self,  bColorizeGroups: bool) -> None:
        self.bColorizeGroups = bColorizeGroups
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        if not self.expr:
            return

        if self.iMode == SearchModes.Match:
            result = self.expr.match(text)
            if result:
                self.highlightMatch (result)
        else:
            cur = 0
            while True:
                result = self.expr.search(text, cur)
                if result:
                    startPos, endPos = result.span()
                    self.highlightMatch(result)
                    cur = endPos
                    if endPos-startPos<=0:
                        break
                else:
                    break
                if self.iMode == SearchModes.SearchFirst:
                    break

    def highlightMatch(self, reMatch: Match) -> None:
        regs = reMatch.regs
        start, end = regs[0]
        self.setFormat(start,  end-start,  self.matchFormat)

        if self.bColorizeGroups:
            groupFormatIndex = 0
            for start, end in regs[1:]:
                self.setFormat(start,  end-start,  self.groupFormats[groupFormatIndex])
                groupFormatIndex = (groupFormatIndex+1)%len(self.groupFormats)

class RegExTesterDlg (QDialog):
    def __init__ (self, parent: QWidget=None) -> None:
        super().__init__(parent)
        self.ui = Ui_RegExTesterDlg()
        self.ui.setupUi(self)
        self.setProperty("shadeBackground", True) # fill background with gradient as defined in style sheet
        self.exprHighlighter = ExprHighlighter(self.ui.textEditExpr.document())
        self.textHighlighter = TextHighlighter(self.ui.textEditText.document())

    @pyqtSlot ()
    def exprTextChanged(self) -> None:
        self.textHighlighter.setExpr(self.ui.textEditExpr.toPlainText())

    @pyqtSlot ()
    def setModeSearchFirst(self) -> None:
        self.textHighlighter.setMode(TextHighlighter.SearchFirst)

    @pyqtSlot ()
    def setModeSearchAll(self) -> None:
        self.textHighlighter.setMode(TextHighlighter.SearchAll)

    @pyqtSlot ()
    def setModeMatch(self) -> None:
        self.textHighlighter.setMode(TextHighlighter.Match)

    @pyqtSlot (bool)
    def checkColorizeGroups(self,  bChecked: bool) -> None:
        self.textHighlighter.setColorizeGroups(bChecked)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    wnd = RegExTesterDlg()
    wnd.show()
    sys.exit(app.exec_())
