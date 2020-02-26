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

from typing import Tuple, Optional, Iterator
from enum import IntEnum
from PyQt5.QtCore import Qt, pyqtSignal, QRect, QRectF, pyqtSlot
from PyQt5.QtGui import QFont, QFontMetrics, QTextLayout, QPainter, QPaintEvent, QTextBlock, QResizeEvent, QTextCursor
from PyQt5.QtWidgets import QPlainTextEdit, QWidget
from .LineNumberArea import LineNumberArea
from .SyntaxHighlighter import SyntaxHighlighter

class HighlightStyle(IntEnum):
    Outline = 1
    Solid = 2

class HighlightingTextEdit (QPlainTextEdit):
    updateNeeded = pyqtSignal()
    parentheses = [('(',')'), ('[',']'), ('{', '}')]

    def __init__ (self, parent: QWidget) -> None:
        super().__init__(parent)
        self.highlighter = SyntaxHighlighter()
        self.dynamicHighlight: Optional[str] = None
        self.parenthesisPair: Optional[Tuple[int,int]] = None
        self.highlightParenthesis = True
        self.setUndoRedoEnabled(False)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setReadOnly(True)
        self.setTextInteractionFlags(Qt.TextSelectableByKeyboard|Qt.TextSelectableByMouse)

        self.lineNumberArea: Optional[LineNumberArea] = None

        self.cursorPositionChanged.connect (self.cursorChanged)
        self.selectionChanged.connect (self.onSelectionChanged)

    @pyqtSlot()
    def cursorChanged(self) -> None:
        text = self.document().toPlainText()
        pos = self.textCursor().position()
        char = text[pos:pos+1]
        paren = self.__isParenthesis(char)
        if not paren and pos > 0:
            pos -= 1
            char = text[pos:pos+1]
            paren = self.__isParenthesis(char)
        if paren:
            closePos = self.__findMatchingParenthesis(char, pos, paren)
        if paren and closePos != -1:
            self.setParenthesisPair((pos, closePos))
        else:
            self.setParenthesisPair(None)

    @pyqtSlot()
    def onSelectionChanged(self) -> None:
        highlightParenthesis = not self.textCursor().selectedText()
        if highlightParenthesis != self.highlightParenthesis:
            self.highlightParenthesis = highlightParenthesis
            self.viewport().update()

    @pyqtSlot()
    def jumpToMatchingBrace(self) -> None:
        if self.parenthesisPair:
            self.scrollToPosition(self.parenthesisPair[1], self.parenthesisPair[1] - self.parenthesisPair[0])

    def scrollToPosition(self, index: int, scrollDir: int) -> None:
        """scrollHint is positive for scolling down and negative for scrolling up"""
        cursor = self.textCursor()
        cursor.setPosition(index)
        if scrollDir > 0:
            cursor.movePosition(QTextCursor.Down, QTextCursor.MoveAnchor,  5)
        elif scrollDir < 0:
            cursor.movePosition(QTextCursor.Up, QTextCursor.MoveAnchor,  5)
        self.setTextCursor (cursor) # otherwise 'ensureCursorVisible' doesn't work
        self.ensureCursorVisible ()
        cursor.setPosition(index)
        self.setTextCursor(cursor) # jump back to match to make sure the line number of the match is correct

    def __findMatchingParenthesis(self, char: str, start: int, paren: Tuple[str, str]) -> int:
        text = self.document().toPlainText()
        openCount = 1
        if char == paren[0]:
            direction = 1
            end = len(text)
            start += 1
            openChar, closeChar = paren[0],paren[1]
        else:
            direction = -1
            start -= 1
            end = -1
            openChar, closeChar = paren[1],paren[0]

        for i in range(start, end, direction):
            char = text[i]
            if char == openChar and not self.highlighter.isInsideComment(i):
                openCount += 1
            elif char == closeChar and not self.highlighter.isInsideComment(i):
                openCount -= 1
                if openCount == 0:
                    return i
        return -1

    def __isParenthesis(self, char: str) -> Optional[Tuple[str, str]]:
        for p in self.parentheses:
            if char in p:
                return p
        return None

    def areLineNumbersShown(self) -> bool:
        return bool(self.lineNumberArea)

    def showLineNumbers(self, show: bool, firstLineNumber:int=1) -> None:
        if show:
            if not self.lineNumberArea:
                self.lineNumberArea = LineNumberArea(self, firstLineNumber)
                self.lineNumberArea.show()
        else:
            if self.lineNumberArea:
                self.lineNumberArea.close()
                self.lineNumberArea = None

    def resizeEvent(self, e: QResizeEvent) -> None:
        super().resizeEvent(e)
        if self.lineNumberArea:
            self.lineNumberArea.reactOnResize(e)

    def setPlainText(self, text: str) -> None:
        self.highlighter.setText(text)
        super().setPlainText(text)

    def setDynamicHighlight(self, text: str) -> None:
        if self.dynamicHighlight != text:
            self.dynamicHighlight = text
            self.viewport().update()

    def setParenthesisPair(self, pair: Optional[Tuple[int,int]]) -> None:
        if not pair and not self.parenthesisPair:
            return
        self.parenthesisPair = pair
        self.viewport().update()

    def setFont(self, font: QFont) -> None:
        super().setFont (font)
        self.viewport().setFont(font)
        self.highlighter.setFont(font)

    def paintEvent(self, event: QPaintEvent) -> None:
        firstVisibleBlock: QTextBlock = self.firstVisibleBlock()
        bColorizedBlocks = self.__colorizeVisibleBlocks(firstVisibleBlock)

        super().paintEvent(event)

        if not self.dynamicHighlight and not self.parenthesisPair:
            return

        painter = QPainter(self.viewport())
        metrics = painter.fontMetrics()
        for block, bound in self.__visibleBlocks(firstVisibleBlock):
            bound = QRect(bound.left(), bound.top(), bound.width(), bound.height())
            # Highlight all occurrences of selected word
            if self.dynamicHighlight:
                startIndex = 0
                while startIndex != -1:
                    startIndex = block.text().find(self.dynamicHighlight, startIndex)
                    if startIndex != -1:
                        self.__highlightPartOfLine(painter, metrics, block, bound, startIndex, len(self.dynamicHighlight), HighlightStyle.Outline)
                        startIndex += len(self.dynamicHighlight)
            # Highlight parenthesis pair
            if self.highlightParenthesis and self.parenthesisPair:
                p1, p2 = self.parenthesisPair
                if block.position() <= p1 < block.position()+block.length():
                    self.__highlightPartOfLine(painter, metrics, block, bound, p1 - block.position(), 1, HighlightStyle.Solid)
                if block.position() <= p2 < block.position()+block.length():
                    self.__highlightPartOfLine(painter, metrics, block, bound, p2 - block.position(), 1, HighlightStyle.Solid)

        # Sometimes lines which are highlighted for the first time are not updated properly.
        # This happens regularily if the text edit is scolled using the page down key.
        # The following signal is emited if new lines were highlighted. The receiver
        # is expected to call "update" on the control. Not nice but it works...
        if bColorizedBlocks:
            self.updateNeeded.emit()

    def __highlightPartOfLine(self, painter: QPainter, metrics: QFontMetrics, block: QTextBlock, bound: QRect, startIndex: int, length: int, style: HighlightStyle) -> None:
        text = block.text()[startIndex:startIndex+length]
        partBefore = block.text()[:startIndex]
        rectBefore = metrics.boundingRect(bound, Qt.TextExpandTabs, partBefore,  self.tabStopWidth())
        rectText = metrics.boundingRect(bound, Qt.TextExpandTabs,  text, self.tabStopWidth())

        if style == HighlightStyle.Outline:
            rectResult = QRect(rectBefore.right()+4,  rectBefore.top()+1,  rectText.width()+2,  rectText.height()-2)
            painter.setPen(Qt.darkGray)
            painter.drawRect(rectResult)
        elif style == HighlightStyle.Solid:
            rectResult = QRect(rectBefore.right()+4,  rectBefore.top(),  rectText.width()+3,  rectText.height()+2)
            painter.fillRect(rectResult, Qt.lightGray)
            painter.setPen(Qt.black)
            painter.drawText(QRectF(rectBefore.right()+5,rectBefore.top(),rectText.width(),rectText.height()), text)

    def __colorizeVisibleBlocks(self, firstVisibleBlock: QTextBlock) -> bool:
        bColorizedBlocks = False
        for block, _ in self.__visibleBlocks(firstVisibleBlock):
            # -1 means the block has not been highlighted yet
            if block.userState() == -1:
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
                if addFormats:
                    block.layout().setAdditionalFormats(addFormats)
                block.setUserState(1)
        return bColorizedBlocks

    def __visibleBlocks (self, firstVisibleBlock: QTextBlock) -> Iterator[Tuple[QTextBlock, QRectF]]:
        size = self.viewport().size()
        block = firstVisibleBlock
        while block.isValid():
            bound = self.blockBoundingGeometry(block).translated(self.contentOffset())
            if bound.top() > size.height():
                break
            yield block, bound
            block = block.next()
