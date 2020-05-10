# -*- coding: utf-8 -*-
"""
Copyright (C) 2020 Oliver Tengler

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

from typing import Tuple, Pattern, List, Optional
import re
import threading
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QFocusEvent, QColor
from tools.AsynchronousTask import AsynchronousTask
from .Ui_InDocumentSearchWidget import Ui_InDocumentSearchWidget

class InDocumentSearchWidget(QWidget):
    """
    This widget provides search capabilities inside a text document.
    Simple expressions as well as regular expressions are supported.
    """

    notFoundColor = QColor(255, 127, 84)

    searchFinished = pyqtSignal(list) # List[Tuple[int,int]])
    nextMatch = pyqtSignal()
    previousMatch = pyqtSignal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.ui = Ui_InDocumentSearchWidget()
        self.ui.setupUi(self)
        self.ui.editSearch.textEdited.connect(self.__textEdited)
        self.ui.checkBoxCaseSensitive.clicked.connect(self.__optionsChanged)
        self.ui.checkBoxRegex.clicked.connect(self.__optionsChanged)
        self.ui.buttonSearchNext.clicked.connect(self.nextMatch)
        self.ui.buttonSearchPrevious.clicked.connect(self.previousMatch)

        self.editTimeoutTimer = QTimer(self)
        self.editTimeoutTimer.setSingleShot(True)
        self.editTimeoutTimer.timeout.connect(self.__editTimeout)

        self.__searchTask: Optional[AsynchronousTask] = None
        self.text = ""
        self.searchRegex: Optional[Pattern] = None
        self.totalMatches = 0
        self.setCurrentMatch(0)

    def setText(self, text: str) -> None:
        self.text = text
        self.__startSearch()

    def setCurrentMatch(self, num: int) -> None:
        if not self.totalMatches:
            self.currentMatch = 0
            self.ui.labelCurrentMatch.setText("")
        else:
            self.currentMatch = num
            self.ui.labelCurrentMatch.setText(f"{num}/{self.totalMatches}")

    def __textEdited(self, _: str) -> None:
        self.__resetColor()
        self.editTimeoutTimer.start(400)

    def __editTimeout(self) -> None:
        self.__updateSearchRegex()
        self.__startSearch()

    def __optionsChanged(self) -> None:
        self.ui.editSearch.setFocus(Qt.ActiveWindowFocusReason)
        self.__resetColor()
        self.__updateSearchRegex()
        self.__startSearch()

    def __startSearch(self) -> None:
        text = self.text
        searchRegex = self.searchRegex
        if not text or not searchRegex:
            self.totalMatches = 0
            self.setCurrentMatch(0)
            return

        if self.__searchTask:
            self.__searchTask.cancel()

        self.ui.widgetProgress.show()
        self.ui.widgetProgress.start()
        self.__searchTask = AsynchronousTask(self.__asyncSearch, text, searchRegex, bEnableCancel=True)
        self.__searchTask.finished.connect(self.__searchDone)
        self.__searchTask.start()

    def __searchDone(self) -> None:
        self.ui.widgetProgress.stop()
        self.ui.widgetProgress.hide()

        if not self.__searchTask:
            return
        results = self.__searchTask.result
        if not results:
            self.__nothingFoundColor()
            self.totalMatches = 0
            self.setCurrentMatch(0)
        else:
            self.totalMatches = len(results)
            self.setCurrentMatch(1)
        self.searchFinished.emit(results)

    def __asyncSearch(self, text: str, searchRegex: Pattern, cancelEvent: threading.Event) -> List[Tuple[int,int]]:
        if not text or not searchRegex:
            return []

        results: List[Tuple[int,int]] = []
        cur = 0
        while True:
            result = searchRegex.search(text, cur)
            if result:
                startPos, endPos = result.span()
                results.append((startPos, endPos-startPos))
                cur = endPos
            else:
                break
            if cancelEvent and cancelEvent.is_set():
                return []

        return results

    def __updateSearchRegex(self) -> None:
        reFlags: int = re.IGNORECASE
        if self.ui.checkBoxCaseSensitive.isChecked():
            reFlags = 0

        expr = self.ui.editSearch.text()
        if not expr:
            self.searchRegex = None
        else:
            if not self.ui.checkBoxRegex.isChecked():
                for c in r"[\^$.|?+()":
                    expr = expr.replace(c, "\\" + c)
                expr = expr.replace("*", r"\w*")
            try:
                self.searchRegex = re.compile(expr, reFlags)
            except:
                self.searchRegex = None # Can happen quite often while you type the regex

    def __resetColor(self) -> None:
        self.setStyleSheet("")

    def __nothingFoundColor(self) -> None:
        col = "#%02x%02x%02x" % (InDocumentSearchWidget.notFoundColor.red(), InDocumentSearchWidget.notFoundColor.green(), InDocumentSearchWidget.notFoundColor.blue())
        self.setStyleSheet("QLineEdit { background: %s }" % (col,))

    def focusInEvent (self, _: QFocusEvent) -> None:
        self.ui.editSearch.setFocus(Qt.ActiveWindowFocusReason)

