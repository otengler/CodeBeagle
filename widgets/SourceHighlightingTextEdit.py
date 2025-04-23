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

from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QRect
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtGui import QPainter, QFontMetrics, QTextBlock
from .HighlightingTextEdit import HighlightingTextEdit, HighlightStyle
from typing import Optional, Tuple

class SourceHighlightingTextEdit (HighlightingTextEdit):
    parentheses = [('(',')'), ('[',']'), ('{', '}')]

    # Triggered if a selection was finished while holding a modifier key down
    selectionFinishedWithKeyboardModifier = pyqtSignal('QString',  int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.parenthesisPair: Optional[Tuple[int,int]] = None
        self.highlightParenthesis = True

        self.cursorPositionChanged.connect (self.cursorChanged)
        self.selectionChanged.connect (self.onSelectionChanged)

    def setParenthesisPair(self, pair: Optional[Tuple[int,int]]) -> None:
        if not pair and not self.parenthesisPair:
            return
        self.parenthesisPair = pair
        if viewport := self.viewport():
            viewport.update()

    @pyqtSlot()
    def cursorChanged(self) -> None:
        document = self.document()
        if not document:
            return
        
        text = document.toPlainText()
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
        text = self.textCursor().selectedText().strip()

        # Disable parenthesis matching during selection of text
        highlightParenthesis = not text
        if highlightParenthesis != self.highlightParenthesis:
            self.highlightParenthesis = highlightParenthesis
            if viewport := self.viewport():
                viewport.update()
                
        # Enable dynamic highlighting of selected text (outline matches)
        if text and len(text)<=64:
            # Allow other components to react on selection of tokens with keyboard modifiers
            modifiers = int(QApplication.keyboardModifiers())
            if modifiers != Qt.KeyboardModifier.NoModifier:
                self.selectionFinishedWithKeyboardModifier.emit(text, modifiers)
            else:
                self.setDynamicHighlight(text)

    @pyqtSlot()
    def jumpToMatchingBrace(self) -> None:
        if self.parenthesisPair:
            self.scrollToPosition(self.parenthesisPair[1], self.parenthesisPair[1] - self.parenthesisPair[0])

    def applyAdditionalHighlighting(self, painter: QPainter, metrics: QFontMetrics, block: QTextBlock, bound: QRect) -> None:
        # Highlight parenthesis pair
        if self.highlightParenthesis and self.parenthesisPair:
            p1, p2 = self.parenthesisPair
            if block.position() <= p1 < block.position()+block.length():
                self._highlightPartOfLine(painter, metrics, block, bound, p1 - block.position(), 1, HighlightStyle.Solid)
            if block.position() <= p2 < block.position()+block.length():
                self._highlightPartOfLine(painter, metrics, block, bound, p2 - block.position(), 1, HighlightStyle.Solid)

    def __findMatchingParenthesis(self, char: str, start: int, paren: Tuple[str, str]) -> int:
        document = self.document()
        if not document:
            return -1
        
        text = document.toPlainText()
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
