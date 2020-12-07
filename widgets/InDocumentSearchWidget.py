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

from typing import Tuple, Pattern, List, Optional, Iterable
import re
import threading
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QFocusEvent, QColor
from tools.AsynchronousTask import AsynchronousTask
from .Ui_InDocumentSearchWidget import Ui_InDocumentSearchWidget
from .IStringMatcher import IStringMatcher

class StringMatcher (IStringMatcher):
    def __init__(self) -> None:
        self.regex: Optional[Pattern] = None

    def setRegex(self, expr: Pattern) -> None:
        self.regex = expr

    def matches(self, data: str) -> Iterable[Tuple[int,int]]:
        if not self.regex:
            return

        cur = 0
        while True:
            result = self.regex.search(data, cur)
            if result:
                startPos, endPos = result.span()
                yield (startPos, endPos-startPos)
                cur = endPos
            else:
                return

class InDocumentSearchResult:
    def __init__(self, results: List[Tuple[int,int]], matcher: Optional[IStringMatcher]) -> None:
        self.results = results
        self.matcher = matcher

def findAllMatches(text: str, searchRegex: Pattern, cancelEvent: threading.Event) -> InDocumentSearchResult:
    if not text or not searchRegex:
        return InDocumentSearchResult([], None)

    matcher = StringMatcher()
    matcher.setRegex(searchRegex)

    results: List[Tuple[int,int]] = []
    for match in matcher.matches(text):
        results.append(match)
        if cancelEvent and cancelEvent.is_set():
            return InDocumentSearchResult([], None)

    return InDocumentSearchResult(results, matcher)

class InDocumentSearchWidget(QWidget):
    """
    This widget provides search capabilities inside a text document.
    Simple expressions as well as regular expressions are supported.
    """

    notFoundColor = QColor(255, 127, 84)
    searchDelay = 300

    searchFinished = pyqtSignal(InDocumentSearchResult)
    currentMatchChanged = pyqtSignal(int, int, int) # num, index, length

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
        self.currentMatch = -1
        self.matches: List[Tuple[int,int]] = []
        self.ui.labelCurrentMatch.setText("")

    def setSearch(self, search: str) -> None:
        self.ui.editSearch.setText(search)
        self.__resetColor()
        self.__updateSearchRegex()
        self.__startSearch()

    def setText(self, text: str) -> None:
        self.text = text
        self.__resetColor()
        self.__startSearch()

    @pyqtSlot()
    def nextMatch(self) -> None:
        self.setCurrentMatch(self.currentMatch + 1)

    @pyqtSlot()
    def previousMatch(self) -> None:
        self.setCurrentMatch(self.currentMatch - 1)

    def setCurrentMatch(self, num: int) -> None:
        if num + 1 > len(self.matches):
            num = len(self.matches) - 1
        if num < 0:
            num = 0
        self.__updateCurrentMatch(num)
        self.__enableButtons()

    def __setMatches(self, results: List[Tuple[int,int]]) -> None:
        self.matches = results
        self.currentMatch = -1
        self.__updateCurrentMatch(0)
        self.__enableButtons()

    def __updateCurrentMatch(self, num: int) -> None:
        if self.currentMatch == num:
            return
        numChanged = self.currentMatch != num
        self.currentMatch = num
        if not self.matches:
            self.ui.labelCurrentMatch.setText("")
        else:
            self.ui.labelCurrentMatch.setText(f"{num+1}/{len(self.matches)}")
            if numChanged and 0 <= num < len(self.matches):
                self.currentMatchChanged.emit(num, *self.matches[num])

    def __textEdited(self, _: str) -> None:
        self.__resetColor()
        self.editTimeoutTimer.start(InDocumentSearchWidget.searchDelay)

    def __editTimeout(self) -> None:
        self.__updateSearchRegex()
        self.__startSearch()

    def __optionsChanged(self) -> None:
        self.ui.editSearch.setFocus(Qt.ActiveWindowFocusReason)
        self.__resetColor()
        self.__updateSearchRegex()
        self.__startSearch()

    def __startSearch(self) -> None:
        self.__setMatches([])

        text = self.text
        searchRegex = self.searchRegex
        if not text or not searchRegex:
            self.searchFinished.emit(InDocumentSearchResult([],None))
            return

        if self.__searchTask:
            self.__searchTask.cancel()

        self.ui.widgetProgress.show()
        self.ui.widgetProgress.start()
        self.__searchTask = AsynchronousTask(findAllMatches, text, searchRegex, bEnableCancel=True)
        self.__searchTask.finished.connect(self.__searchDone)
        self.__searchTask.start()

    def __searchDone(self) -> None:
        self.ui.widgetProgress.stop()
        self.ui.widgetProgress.hide()

        if not self.__searchTask:
            return
        searchResult: InDocumentSearchResult = self.__searchTask.result
        if not searchResult.results:
            self.__nothingFoundColor()       
        self.__setMatches(searchResult.results)
        self.searchFinished.emit(searchResult)

    def __updateSearchRegex(self) -> None:
        reFlags: int = re.IGNORECASE
        if self.ui.checkBoxCaseSensitive.isChecked():
            reFlags = 0

        expr = self.ui.editSearch.text().strip()
        if not expr:
            self.searchRegex = None
        else:
            if not self.ui.checkBoxRegex.isChecked():
                for c in r"[\^$.|?+()*":
                    expr = expr.replace(c, "\\" + c)
                while True: # reduce all adjacent spaces to one which will then be replaced by a regex which matches arbitrary whitespace
                    reduceSpace = expr.replace("  ", " ")
                    if reduceSpace == expr:
                        break
                    expr = reduceSpace
                expr = expr.replace(" ", r"\s*")
            try:
                self.searchRegex = re.compile(expr, reFlags)
            except:
                self.searchRegex = None # Can happen quite often while you type the regex

    def __resetColor(self) -> None:
        self.setStyleSheet("")

    def __nothingFoundColor(self) -> None:
        col = "#%02x%02x%02x" % (InDocumentSearchWidget.notFoundColor.red(), InDocumentSearchWidget.notFoundColor.green(), InDocumentSearchWidget.notFoundColor.blue())
        self.setStyleSheet("QLineEdit { background: %s }" % (col,))

    def __enableButtons(self) -> None:
        self.ui.buttonSearchPrevious.setEnabled(self.currentMatch > 0)
        self.ui.buttonSearchNext.setEnabled(self.currentMatch + 1 < len(self.matches))

    def focusInEvent (self, _: QFocusEvent) -> None:
        self.ui.editSearch.setFocus(Qt.ActiveWindowFocusReason)

