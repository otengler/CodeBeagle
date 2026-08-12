# -*- coding: utf-8 -*-
"""
Copyright (C) 2021 Oliver Tengler

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

import unittest
from typing import List, Optional, Callable, cast
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFontMetrics, QFont, QWheelEvent
from PyQt5.QtWidgets import QWidget
from tools import AsynchronousTask
from tools.ContextExtraction import MatchesInFile, extractMatches
from fulltextindex import FullTextIndex
from widgets.SourceHighlightingTextEdit import SourceHighlightingTextEdit
from widgets import RecyclingVerticalScrollArea
from AppConfig import appConfig
import HighlightingRulesCache
from MatchesOverviewLabel import MatchesOverviewLabelItem
from Ui_MatchesOverview import Ui_MatchesOverview

class FixedSizeSourcePreview(SourceHighlightingTextEdit):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        # Scrolling should not be needed and is not wanted. This is just a way to make it 100% sure that it is switched off:
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.wheelEvent = lambda event: None  # type: ignore[method-assign]

class MatchesOverview (QWidget):
    # Triggered if a selection was finished while holding a modifier key down
    selectionFinishedWithKeyboardModifier = pyqtSignal('QString',  int)
    navigateToFile = pyqtSignal(str, int) # fileName and start line

    def __init__ (self, parent: Optional[QWidget]) -> None:
        super().__init__(parent)
        self.ui = Ui_MatchesOverview()
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]
        self.matches: Optional[List[str]] = None
        self.searchData: Optional[FullTextIndex.Query] = None
        self.resultHandled = True
        self.sourceFont: QFont = self.font()
        self.lineHeight = 0
        self.tabWidth = 4
        self.linesOfContext = 2
        self.scrollItems = RecyclingVerticalScrollArea.ScrollAreaItemList()
        self.matchIndexes: List[int] = []

    def reloadConfig (self, font: QFont) -> None:
        self.sourceFont = font
        metrics = QFontMetrics(self.sourceFont)
        self.lineHeight = metrics.height()

        linesOfContext = appConfig().previewLines
        if linesOfContext % 2:
            linesOfContext /= 2
        else:
            linesOfContext = (linesOfContext+1)/2
        if linesOfContext < 1:
            linesOfContext = 1
        self.linesOfContext = int(linesOfContext)

        config = appConfig().SourceViewer
        self.tabWidth = config.TabWidth

        self.__rebuildScrollItems()

    def __rebuildScrollItems(self) -> None:
        if self.matches and self.isVisible():
            self.__handleResult()

    def setSearchResult(self, matches: List[str], searchData: Optional[FullTextIndex.Query]) -> None:
        self.matches = matches
        self.searchData = searchData
        self.resultHandled = False

        if self.isVisible():
            self.__handleResult()

    def activate (self) -> None:
        if not self.resultHandled:
            self.__handleResult ()

    def scrollToFile (self, index: int) -> None:
        if index >= len(self.matchIndexes):
            return
        self.ui.scrollArea.scrollToNthItem(self.matchIndexes[index])

    def __handleResult(self) -> None:
        self.resultHandled = True

        self.scrollItems.clear()
        self.matchIndexes = []

        if self.matches:
            results = AsynchronousTask.execute (self, extractMatches, self.matches, self.searchData, self.linesOfContext,
                                                bEnableCancel=True, hasProgress=True)

            for result in results:
                firstMatchLine = result.matches[0][0]
                index = self.__addHeader(result.name, firstMatchLine)
                self.matchIndexes.append(index)
                for startLine, lines in result.matches:
                    self.__addText(result.name, startLine, lines)

        self.ui.scrollArea.setItems(self.scrollItems)

    def __addHeader(self, fileName: str, startLine: int) -> int:
        labelItem = MatchesOverviewLabelItem(fileName, startLine)
        labelItem.navigateToCallback = self.__createNavigateToFileFunc(labelItem)
        return self.scrollItems.addItem(labelItem)

    def __addText(self, name: str, startLine: int, lines: List[str]) -> int:
        text = "\n".join(lines)
        # Calculate height: line height * number of lines + top/bottom document margins (4+4) + frame (2+2) + padding (1)
        # Needed to add 2 because the are item still scrolled.
        height = len(lines)*self.lineHeight + 15
        editItem = FixedSizeSourcePreviewItem (self, startLine, text, name, height)
        return self.scrollItems.addItem(editItem)
    
    def __createNavigateToFileFunc(self, labelItem: MatchesOverviewLabelItem) -> Callable[[], None]:
        return lambda: self.emitNavigateToFile(labelItem)

    @pyqtSlot(MatchesOverviewLabelItem)
    def emitNavigateToFile(self, item: MatchesOverviewLabelItem) -> None:
        self.navigateToFile.emit(item.fileName, item.startLine)

class FixedSizeSourcePreviewItem (RecyclingVerticalScrollArea.ScrollAreaItem):
    def __init__(self, matchesOverview: MatchesOverview, startLine: int, text: str, name: str, height: int) -> None:
        super ().__init__(height)
        self.matchesOverview = matchesOverview
        self.startLine = startLine
        self.text = text
        self.name = name

    def generateItem (self, parent: Optional[QWidget]) -> QWidget:
        item = FixedSizeSourcePreview(parent)
        # Forward the signal to MatchesOverview instance
        item.selectionFinishedWithKeyboardModifier.connect (self.matchesOverview.selectionFinishedWithKeyboardModifier)
        return item

    def configureItem(self, item: QWidget) -> None:
        preview = cast(FixedSizeSourcePreview, item)
        rules = HighlightingRulesCache.rules().getRulesByFileName(self.name, self.matchesOverview.sourceFont)
        preview.setFont(self.matchesOverview.sourceFont)
        preview.setTabStopWidth(self.matchesOverview.tabWidth*10)
        preview.highlighter.setHighlightingRules (rules)
        preview.highlighter.setSearchData (self.matchesOverview.searchData)
        preview.setTextDocument(self.text, self.name)
        preview.showLineNumbers(True, self.startLine)

    def getType(self) -> str:
        return "FixedSizeSourcePreview"

def main() -> None:
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    w = MatchesOverview(None)
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    unittest.main()
    #main()
