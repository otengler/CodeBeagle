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

import os
from typing import Optional, List, Tuple
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QTextFormat, QColor, QTextCursor, QFont, QDragEnterEvent, QDropEvent
from PyQt5.QtWidgets import QWidget, QAction, QListWidgetItem, QDialog, QTextEdit
from tools.FileTools import Encoding, freadallEx
from AppConfig import appConfig
from fulltextindex import FullTextIndex
import HighlightingRulesCache
from widgets.SyntaxHighlighter import SyntaxHighlighter
from widgets.InDocumentSearchWidget import InDocumentSearchResult
from Ui_SourceViewer import Ui_SourceViewer

class EditorState:
    def __init__(self, scrollPosition: int, currentMatch: int) -> None:
        self.scrollPosition = scrollPosition
        self.currentMatch = currentMatch

class SourceViewer (QWidget):
    # Triggered if a selection was finished while holding a modifier key down
    selectionFinishedWithKeyboardModifier = pyqtSignal('QString',  int)
    noPreviousMatch = pyqtSignal()
    noNextMatch = pyqtSignal()
    directoryDropped = pyqtSignal('QString')
    currentMatchChanged = pyqtSignal(int)

    currentLineBackgroundColor = QColor(240,240,240)
    currentMatchLineBackgroundColor = QColor(170,255,127)

    def __init__ (self, parent: QWidget) -> None:
        self.matches: List[Tuple[int,int]]
        self.curMatch: int
        self.currentFile: str
        self.encoding: Encoding = Encoding.Default
        self.currentLineExtras: List[QTextEdit.ExtraSelection] = []
        self.currentMatchExtras: List[QTextEdit.ExtraSelection] = []

        super ().__init__(parent)
        self.ui = Ui_SourceViewer()
        self.ui.setupUi(self)
        self.ui.widgetInDocumentSearch.hide()

        self.sourceFont: QFont = self.font()
        self.searchData: Optional[FullTextIndex.ContentQuery] = None
        self.__reset()
        self.__processConfig(None)

        self.ui.textEdit.cursorPositionChanged.connect(self.updateCurrentLine)
        self.ui.buttonMatchPrevious.clicked.connect(self.previousMatch)
        self.ui.buttonMatchNext.clicked.connect(self.nextMatch)
        self.ui.buttonMatchList.clicked.connect(self.ui.frameMatchList.setVisible)
        self.ui.buttonMatchCurrent.clicked.connect(self.jumpToCurrentMatch)

        self.actionReloadFile = QAction(self, shortcut=Qt.Key_F5, triggered= self.reloadFile)
        self.addAction(self.actionReloadFile)
        self.actionGotoLine = QAction(self, shortcut=Qt.CTRL+Qt.Key_G, triggered=self.gotoLine)
        self.addAction(self.actionGotoLine)
        self.jumpToMatchingBrace = QAction(self, shortcut=Qt.CTRL+Qt.Key_B, triggered=self.ui.textEdit.jumpToMatchingBrace)
        self.addAction(self.jumpToMatchingBrace)
        self.actionJumpToCurrentMatch = QAction(self, shortcut=Qt.CTRL+Qt.Key_J, triggered=self.jumpToCurrentMatch)
        self.addAction(self.actionJumpToCurrentMatch)

        # In document search
        self.inDocumentSearch = QAction(self, shortcut=Qt.CTRL+Qt.Key_F, triggered=self.toggleSearchFrame)
        self.addAction(self.inDocumentSearch)
        self.ui.buttonSearch.clicked.connect(self.showSearchFrame)
        self.ui.widgetInDocumentSearch.searchFinished.connect(self.inDocumentSearchFinished)
        self.ui.widgetInDocumentSearch.currentMatchChanged.connect(self.inDocumentSearchMatchChanged)

        # Forward the signal
        self.ui.textEdit.selectionFinishedWithKeyboardModifier.connect(self.selectionFinishedWithKeyboardModifier)
        self.ui.listMatchesWidget.currentRowChanged.connect(self.matchListRowChanged)
        self.ui.listMatchesWidget.itemDoubleClicked.connect(self.matchListItemDoubleClicked)

        # Help the text edit to update the syntax highlighting. This works around an
        # update problem of the text edit used in a scroll area.
        self.ui.textEdit.updateNeeded.connect(self.textEditUpdateNeeded)

        # Show match list if button is pressed
        self.ui.buttonMatchList.setChecked(appConfig().showMatchList)
        self.ui.frameMatchList.setVisible(self.ui.buttonMatchList.isChecked())

        # Encoding info label
        self.ui.labelEncoding.hide()

    @pyqtSlot(int)
    def matchListRowChanged(self, row: int) -> None:
        if row != -1:
            self.setCurrentMatch(row)

    @pyqtSlot(QListWidgetItem)
    def matchListItemDoubleClicked(self, _: QListWidgetItem) -> None:
        """Force jumping to a match. Useful to jump to the same match again."""
        row = self.ui.listMatchesWidget.currentRow()
        if row != -1:
            self.setCurrentMatch(row, True)

    @pyqtSlot()
    def textEditUpdateNeeded (self) -> None:
        self.ui.textEdit.viewport().update ()

    def reloadConfig (self, font: QFont) -> None:
        self.__processConfig(font)

    def __processConfig (self, font: QFont) -> None:
        if font:
            self.sourceFont = font
            self.ui.textEdit.setFont(self.sourceFont)

        self.bMatchOverFiles = appConfig().matchOverFiles

        config = appConfig().SourceViewer
        if self.ui.textEdit.tabStopWidth() != config.TabWidth*10:
            self.ui.textEdit.setTabStopWidth(config.TabWidth*10)
        if self.ui.textEdit.areLineNumbersShown() != config.showLineNumbers:
            self.ui.textEdit.showLineNumbers(config.showLineNumbers)

    def __reset (self) -> None:
        self.currentFile = ""
        self.matches = [] # touples with position and length
        self.__setMatchIndex(-1)
        self.ui.labelCursor.setText("")
        self.ui.labelFile.setText(self.tr("No document loaded"))
        self.ui.textEdit.setPlainText("")
        self.__resetTextCursor()
        self.__setInfoLabel()
        self.ui.textEdit.setDynamicHighlight(None)
        self.ui.listMatchesWidget.clear()
        self.__hideInDocumentSearch()

    def __setMatchIndex(self, index: int) -> None:
        self.curMatch = index
        self.currentMatchChanged.emit(self.curMatch)
        self.ui.listMatchesWidget.setCurrentRow(index)

    def setSearchData (self, searchData: FullTextIndex.ContentQuery) -> None:
        self.__reset()
        self.searchData = searchData
        self.ui.textEdit.highlighter.setSearchData (searchData)

    def __readFileAndSetEncoding(self, name: str) -> str:
        encoding: Encoding
        text: str
        try:
            text, encoding = freadallEx(name)
        except:
            text = self.tr("Failed to open file")
            self.ui.labelEncoding.hide()
        else:
            self.ui.labelEncoding.show()
            if encoding == Encoding.UTF8:
                self.ui.labelEncoding.setText("UTF8")
            if encoding == Encoding.UTF8_BOM:
                self.ui.labelEncoding.setText("UTF8 BOM")
            elif encoding == Encoding.UTF16_BOM:
                self.ui.labelEncoding.setText("UTF16 BOM")
            elif encoding == Encoding.Default:
                self.ui.labelEncoding.setText("Latin1")
        return text

    def showFile (self, name: str, editorState: Optional[EditorState] = None) -> None:
        self.__reset()
        self.ui.labelFile.setText(name)
        self.currentFile = name

        text = self.__readFileAndSetEncoding(name)

        rules = HighlightingRulesCache.rules().getRulesByFileName(name,  self.sourceFont)
        self.ui.textEdit.highlighter.setHighlightingRules (rules)
        self.ui.textEdit.setPlainText(text)
        self.ui.widgetInDocumentSearch.setText(text)

        if self.searchData:
            self.matches = [match for match in self.searchData.matches (text)]
            self.ui.listMatchesWidget.clear()
            for i in range(len(self.matches)):
                item = "%u" % (i+1,)
                self.ui.listMatchesWidget.addItem(item)
            if self.matches:
                self.nextMatch ()

        if editorState:
            self.restoreEditorState(editorState)

    @pyqtSlot()
    def reloadFile(self) -> None:
        if self.currentFile:
            self.showFile(self.currentFile)

    @pyqtSlot()
    def gotoLine(self) -> None:
        from dialogs.GotoLineDialog import GotoLineDialog
        gotoDialog = GotoLineDialog(self)
        if gotoDialog.exec() == QDialog.Accepted:
            line = gotoDialog.getLine()-1
            if line < 0:
                line = 0
            elif line >= self.ui.textEdit.document().blockCount():
                line = self.ui.textEdit.document().blockCount()-1
            block = self.ui.textEdit.document().findBlockByLineNumber (line)
            if block.isValid():
                cursor = self.ui.textEdit.textCursor()
                cursor.setPosition(block.position())
                self.ui.textEdit.setTextCursor(cursor)
                self.ui.textEdit.setFocus(Qt.ActiveWindowFocusReason)

    @pyqtSlot()
    def nextMatch (self) -> None:
        if self.curMatch < len(self.matches)-1:
            self.setCurrentMatch(self.curMatch + 1)
        else:
            if self.bMatchOverFiles:
                self.noNextMatch.emit()

    @pyqtSlot()
    def previousMatch (self) -> None:
        if self.curMatch > 0:
            self.setCurrentMatch(self.curMatch - 1)
        else:
            if self.bMatchOverFiles:
                self.noPreviousMatch.emit()

    @pyqtSlot()
    def jumpToCurrentMatch(self) -> None:
        if self.curMatch >= 0:
            self.__scrollToMatch (*self.matches[self.curMatch], SyntaxHighlighter.matchBackgroundColor)

    def setCurrentMatch(self, index: int, forceSet: bool=False) -> None:
        if index>=0 and index<len(self.matches) and (index != self.curMatch or forceSet):
            self.__setMatchIndex(index)
            self.__scrollToMatch (*self.matches[index], SyntaxHighlighter.matchBackgroundColor)
            self.__setInfoLabel ()
            if not self.bMatchOverFiles:
                self.__enableNextPrevious()

    @pyqtSlot()
    def updateCurrentLine (self) -> None:
        line = self.ui.textEdit.textCursor().blockNumber()+1
        self.ui.labelCursor.setText(self.tr("Line") + " %u" % (line, ))

        extra = QTextEdit.ExtraSelection ()
        extra.cursor = self.ui.textEdit.textCursor()
        extra.cursor.setPosition (self.ui.textEdit.textCursor().position())
        extra.format.setProperty (QTextFormat.FullWidthSelection, True)
        extra.format.setBackground (SourceViewer.currentLineBackgroundColor)
        self.__updateCurrentLineExtraSelections([extra])

    @pyqtSlot()
    def toggleSearchFrame(self) -> None:
        text = self.ui.textEdit.textCursor().selectedText().strip()
        self.ui.widgetInDocumentSearch.setSearch(text)
        if not text:
            self.ui.buttonSearch.toggle()
        else:
            self.ui.buttonSearch.setChecked(True)
        self.showSearchFrame()

    @pyqtSlot(int, int, int)
    def inDocumentSearchMatchChanged(self, _: int, index: int, length: int) -> None:
        self.__scrollToMatch(index, length, SyntaxHighlighter.match2BackgroundColor)

    @pyqtSlot()
    def showSearchFrame(self) -> None:
        if self.ui.buttonSearch.isChecked():
            self.ui.widgetInDocumentSearch.show()
            self.ui.widgetInDocumentSearch.setFocus(Qt.FocusReason.MouseFocusReason)
        else:
            self.ui.widgetInDocumentSearch.hide()
            self.ui.widgetInDocumentSearch.setSearch("")
            self.__clearInDocumentSearchHighlighting()

    @pyqtSlot(InDocumentSearchResult)
    def inDocumentSearchFinished(self, searchResult: InDocumentSearchResult) -> None:
        if searchResult.results:
            self.ui.textEdit.highlighter.setSearchData2 (searchResult.matcher)
            self.ui.textEdit.rehighlight()
        else:
            self.__clearInDocumentSearchHighlighting()

    def __clearInDocumentSearchHighlighting(self) -> None:
        self.ui.textEdit.highlighter.setSearchData2 (None)
        self.__updateMatchExtraSelections([]) # remove line highlight
        self.ui.textEdit.rehighlight()

    def __hideInDocumentSearch(self) -> None:
        self.ui.buttonSearch.setChecked(False)
        self.showSearchFrame()

    def __enableNextPrevious (self) -> None:
        """Disable next/previous buttons if they don't make sense."""
        bEnablePrevious = self.curMatch > 0
        if self.ui.buttonMatchPrevious.isEnabled() != bEnablePrevious:
            self.ui.buttonMatchPrevious.setEnabled(bEnablePrevious)
        bEnableNext = self.curMatch < len(self.matches)-1
        if self.ui.buttonMatchNext.isEnabled() != bEnableNext:
            self.ui.buttonMatchNext.setEnabled(bEnableNext)

    def __resetTextCursor (self) -> None:
        cursor = self.ui.textEdit.textCursor()
        cursor.setPosition(0)
        self.ui.textEdit.setTextCursor(cursor)
        extra = QTextEdit.ExtraSelection ()
        extra.cursor = cursor
        self.ui.textEdit.setExtraSelections((extra,))

    def __setInfoLabel (self) -> None:
        text = ""
        if self.matches and self.curMatch != -1:
            text = text + "%u/%u " % (self.curMatch+1, len(self.matches))
        self.ui.labelInfo.setText (text)

    def __scrollToMatch (self, index: int, length: int, highlightColor: QColor) -> None:
        scrollDir = index - self.ui.textEdit.textCursor().position() # Determine if we need to scroll down or up

        extras = []
        extra1 = QTextEdit.ExtraSelection ()
        extra1.cursor = self.ui.textEdit.textCursor()
        extra1.cursor.setPosition (index)
        extra1.format.setProperty (QTextFormat.FullWidthSelection,  True)
        extra1.format.setBackground (SourceViewer.currentMatchLineBackgroundColor)
        extras.append(extra1)

        extra2 = QTextEdit.ExtraSelection ()
        extra2.cursor = self.ui.textEdit.textCursor()
        extra2.cursor.setPosition (index)
        extra2.cursor.setPosition (index+length,  QTextCursor.KeepAnchor)
        extra2.format.setBackground (highlightColor)
        extras.append(extra2)

        self.__updateMatchExtraSelections(extras)
        self.ui.textEdit.scrollToPosition(index, scrollDir)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None: # pylint: disable=no-self-use
        # check if the data contains urls
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        # check if the data contains urls
        mimeData = event.mimeData()
        name = None
        if mimeData.hasUrls() and len(mimeData.urls()) > 0:
            name = mimeData.urls()[0].toLocalFile()
        elif mimeData.hasText() and len(mimeData.text()) > 0:
            name = mimeData.text()
        if not name:
            return
        if os.path.isfile(name):
            self.showFile(name)
        elif os.path.isdir(name):
            self.directoryDropped.emit(name)

    def saveEditorState(self) -> EditorState:
        currentMatch = self.curMatch
        scrollPosition = self.ui.textEdit.verticalScrollBar ().sliderPosition ()
        return EditorState(scrollPosition, currentMatch)

    def restoreEditorState(self, state: EditorState) -> None:
        self.setCurrentMatch(state.currentMatch)
        self.ui.textEdit.verticalScrollBar ().setSliderPosition (state.scrollPosition)

    def __updateMatchExtraSelections(self, extras: List[QTextEdit.ExtraSelection]) -> None:
        self.currentMatchExtras = extras
        self.__updateExtraSelections()
    def __updateCurrentLineExtraSelections(self, extras: List[QTextEdit.ExtraSelection]) -> None:
        self.currentLineExtras = extras
        self.__updateExtraSelections()
    def __updateExtraSelections(self) -> None:
        self.ui.textEdit.setExtraSelections(self.currentLineExtras + self.currentMatchExtras)

def main() -> None:
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    w = SourceViewer(None)
    w.show()
    #w.showFile(r"D:\C++\qt-everywhere-opensource-src-4.7.3\src\svg\qsvghandler.cpp")
    w.showFile(r"D:\test.cpp")
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()