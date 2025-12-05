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

from typing import Tuple, Optional, Iterator, cast
from enum import IntEnum
from PyQt5.QtCore import Qt, pyqtSignal, QRect, QRectF
from PyQt5.QtGui import QFont, QFontMetrics, QTextLayout, QPainter, QPaintEvent, QTextBlock, QResizeEvent, QTextCursor, QColor, QWheelEvent
from PyQt5.QtWidgets import QPlainTextEdit, QWidget
from .LineNumberArea import LineNumberArea
from .SyntaxHighlighter import SyntaxHighlighter

class HighlightStyle(IntEnum):
    Outline = 1
    Solid = 2

class HighlightingTextEdit (QPlainTextEdit):
    updateNeeded = pyqtSignal()
    
    highlightOutlineColor: QColor|Qt.GlobalColor = Qt.GlobalColor.darkGray
    highlightSolidBackgroundColor: QColor|Qt.GlobalColor = Qt.GlobalColor.lightGray
    highlightSolidForegroundColor: Optional[QColor|Qt.GlobalColor] = Qt.GlobalColor.black

    def __init__ (self, parent: Optional[QWidget]) -> None:
        super().__init__(parent)
        self.highlighter = SyntaxHighlighter()
        self.__highlightUpdateCounter = 0 # Increment every time the highlight changes
        self.dynamicHighlight: Optional[str] = None
        self.setUndoRedoEnabled(False)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setReadOnly(True)
        self.setTextInteractionFlags(cast(Qt.TextInteractionFlag, Qt.TextInteractionFlag.TextSelectableByKeyboard|Qt.TextInteractionFlag.TextSelectableByMouse))

        self.lineNumberArea: Optional[LineNumberArea] = None

    def scrollToPosition(self, index: int, scrollDir: int) -> None:
        """scrollDir is positive for scolling down and negative for scrolling up"""
        cursor = self.textCursor()
        cursor.setPosition(index)
        if scrollDir > 0:
            cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.MoveAnchor,  5)
        elif scrollDir < 0:
            cursor.movePosition(QTextCursor.MoveOperation.Up, QTextCursor.MoveMode.MoveAnchor,  5)
        self.setTextCursor (cursor) # otherwise 'ensureCursorVisible' doesn't work
        self.ensureCursorVisible ()
        cursor.setPosition(index)
        self.setTextCursor(cursor) # jump back to match to make sure the line number of the match is correct

    def getLineByLineNumber(self, line: int) -> Optional[Tuple[int, int, str]]:
        """
        Returns tuple with start position, end position and text given an index within the document.
        """
        if line > 0:
            line -= 1
        if doc := self.document():
            if block := doc.findBlockByLineNumber(line):
                return (block.position(), block.position() + block.length() - 1, block.text())
        return None
    
    def getLineByIndex(self, index: int) -> Optional[Tuple[int, int, str]]:
        """
        Returns tuple with start position, end position and text given an index within the document.
        """
        if doc := self.document():
            if block := doc.findBlock(index):
                return (block.position(), block.position() + block.length() - 1, block.text())
        return None

    def areLineNumbersShown(self) -> bool:
        return bool(self.lineNumberArea)

    def showLineNumbers(self, show: bool, firstLineNumber:int=1, enableBookmarks:bool=False) -> None:
        if show:
            if not self.lineNumberArea:
                self.lineNumberArea = LineNumberArea(self, firstLineNumber, enableBookmarks=enableBookmarks)
                self.lineNumberArea.show()
        else:
            if self.lineNumberArea:
                self.lineNumberArea.close()
                self.lineNumberArea = None

    def currentLineNumber(self) -> int:
        if self.lineNumberArea:
            return int(self.textCursor().blockNumber()) + self.lineNumberArea.firstLineNumber
        else:
            return int(self.textCursor().blockNumber()) + 1

    def resizeEvent(self, e: QResizeEvent) -> None:
        super().resizeEvent(e)
        if self.lineNumberArea:
            self.lineNumberArea.reactOnResize(e)

    def setPlainText(self, text: Optional[str]) -> None:
        self.setTextDocument(text, "")

    def setTextDocument(self, text: Optional[str], filename: Optional[str] = None) -> None:
        if text:
            self.highlighter.setTextDocument(text, filename or "")
            super().setPlainText(text)

    def setDynamicHighlight(self, text: str) -> None:
        if self.dynamicHighlight != text:
            self.dynamicHighlight = text
            if viewport := self.viewport():
                viewport.update()

    def setFont(self, font: QFont) -> None:
        super().setFont (font)
        viewport = self.viewport()
        if viewport:
            viewport.setFont(font)
        self.highlighter.setFont(font)
        if self.lineNumberArea:
            self.lineNumberArea.setFont(font)
        self.rehighlight()

    def wheelEvent(self, event: QWheelEvent) -> None:
        super().wheelEvent(event)
        # Qt automatically supports channging the font size using CTRL+mouse wheel. We need to intercept this to propagate the font change to all components
        if event.modifiers() and Qt.KeyboardModifier.ControlModifier:
            self.setFont(self.font())           

    def rehighlight(self) -> None:
        """
        Evaluate syntax highlighting again
        """
        self.__highlightUpdateCounter += 1 # causes all blocks to highlight again
        if viewport := self.viewport():
            viewport.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        firstVisibleBlock: QTextBlock = self.firstVisibleBlock()
        bColorizedBlocks = self.__colorizeVisibleBlocks(firstVisibleBlock)

        super().paintEvent(event)

        if self.dynamicHighlight or self.additionalHighlightingNeeded():
            painter = QPainter(self.viewport())
            metrics = painter.fontMetrics()
            for block, bound in self.__visibleBlocks(firstVisibleBlock):
                # Highlight all occurrences of selected word
                if self.dynamicHighlight:
                    startIndex = 0
                    while startIndex != -1:
                        startIndex = block.text().find(self.dynamicHighlight, startIndex)
                        if startIndex != -1:
                            self._highlightPartOfLine(painter, metrics, block, bound, startIndex, len(self.dynamicHighlight), HighlightStyle.Outline)
                            startIndex += len(self.dynamicHighlight)

                self.applyAdditionalHighlighting(painter, metrics, block, bound)

        # Sometimes lines which are highlighted for the first time are not updated properly.
        # This happens regularily if the text edit is scolled using the page down key.
        # The following signal is emited if new lines were highlighted. The receiver
        # is expected to call "update" on the control. Not nice but it works...
        if bColorizedBlocks:
            self.updateNeeded.emit()

    def additionalHighlightingNeeded(self) -> bool:
        return False

    def applyAdditionalHighlighting(self, painter: QPainter, metrics: QFontMetrics, block: QTextBlock, bound: QRect) -> None:
        # To be used by sub classes
        pass

    def _highlightPartOfLine(self, painter: QPainter, metrics: QFontMetrics, block: QTextBlock, bound: QRect, startIndex: int, length: int, style: HighlightStyle) -> None:
        # Can be used by sub classes
        text = block.text()[startIndex:startIndex+length]
        partBefore = block.text()[:startIndex]
        rectBefore = metrics.boundingRect(bound, Qt.TextFlag.TextExpandTabs, partBefore,  self.tabStopWidth())
        rectText = metrics.boundingRect(bound, Qt.TextFlag.TextExpandTabs,  text, self.tabStopWidth())

        if style == HighlightStyle.Outline:
            rectResult = QRect(rectBefore.right()+4,  rectBefore.top()+1,  rectText.width()+2,  rectText.height()-2)
            painter.setPen(HighlightingTextEdit.highlightOutlineColor)
            painter.drawRect(rectResult)
        elif style == HighlightStyle.Solid:
            rectResult = QRect(rectBefore.right()+4,  rectBefore.top(),  rectText.width()+2,  rectText.height()+2)
            painter.fillRect(rectResult, HighlightingTextEdit.highlightSolidBackgroundColor)
            if HighlightingTextEdit.highlightSolidForegroundColor:
                painter.setPen(HighlightingTextEdit.highlightSolidForegroundColor)
            painter.drawText(QRectF(rectBefore.right()+5,rectBefore.top(),rectText.width(),rectText.height()), text)

    def __colorizeVisibleBlocks(self, firstVisibleBlock: QTextBlock) -> bool:
        bColorizedBlocks = False
        for block, _ in self.__visibleBlocks(firstVisibleBlock):
            # -1 means the block has not been highlighted yet
            if block.userState() != self.__highlightUpdateCounter:
                bColorizedBlocks = True
                blockLength = len(block.text())
                formats = self.highlighter.highlightBlock(block.position(), block.text())
                addFormats = []
                for (fmt, start, length) in formats:
                    formatRange = QTextLayout.FormatRange ()
                    formatRange.format = fmt
                    if start >= 0:
                        formatRange.start = start
                    else:
                        formatRange.start = 0
                        length += start
                    if formatRange.start + length > blockLength:
                        formatRange.length = blockLength - formatRange.start
                    else:
                        formatRange.length = length
                    if formatRange.length >= 0:
                        addFormats.append(formatRange)
                if layout := block.layout():
                    layout.setAdditionalFormats(addFormats)
                block.setUserState(self.__highlightUpdateCounter)
        return bColorizedBlocks

    def __visibleBlocks (self, firstVisibleBlock: QTextBlock) -> Iterator[Tuple[QTextBlock, QRect]]:
        if viewport := self.viewport():
            size = viewport.size()
            block = firstVisibleBlock
            while block.isValid():
                bound = self.blockBoundingGeometry(block).translated(self.contentOffset())
                if bound.top() > size.height():
                    break
                yield block, QRect(int(bound.left()), int(bound.top()), int(bound.width()), int(bound.height()))
                block = block.next()
