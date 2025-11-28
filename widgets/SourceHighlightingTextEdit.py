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

    def additionalHighlightingNeeded(self) -> bool:
        return self.highlightParenthesis and not self.parenthesisPair is None

    def applyAdditionalHighlighting(self, painter: QPainter, metrics: QFontMetrics, block: QTextBlock, bound: QRect) -> None:
        # Highlight parenthesis pair
        if self.highlightParenthesis and not self.parenthesisPair is None:
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
            if char == openChar and not self.highlighter.isInsideComment(i) and not self.highlighter.isInsideString(i):
                openCount += 1
            elif char == closeChar and not self.highlighter.isInsideComment(i) and not self.highlighter.isInsideString(i):
                openCount -= 1
                if openCount == 0:
                    return i
        return -1

    def __isParenthesis(self, char: str) -> Optional[Tuple[str, str]]:
        for p in self.parentheses:
            if char in p:
                return p
        return None


import unittest

class TestBraceMatchingWithStrings(unittest.TestCase):
    """Test that brace matching correctly ignores braces inside strings."""

    def setUp(self) -> None:
        """Set up a text edit widget with syntax highlighting."""
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtGui import QFont, QBrush
        from PyQt5.QtCore import Qt, QCoreApplication
        from widgets.SyntaxHighlighter import HighlightingRules
        import sys

        # Create QApplication if it doesn't exist
        self.app: Optional[QCoreApplication]
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
        else:
            self.app = QApplication.instance()

        # Create the text edit
        self.textEdit = SourceHighlightingTextEdit()

        # Set up highlighting rules for C-style syntax
        self.rules = HighlightingRules(QFont())
        self.rules.addCommentRule(r'//.*', r'/\*', r'\*/', 400, QBrush(Qt.GlobalColor.darkGreen))
        self.rules.setStrings(400, QBrush(Qt.GlobalColor.darkRed))

        self.textEdit.highlighter.setHighlightingRules(self.rules)

    def test_brace_in_double_quote_string_ignored(self) -> None:
        """Test that braces inside double-quoted strings are ignored."""
        # Example from user: '{ "test }" }' should match outer braces
        text = '{ "test }" }'
        self.textEdit.setPlainText(text)
        self.textEdit.highlighter.setTextDocument(text)

        # Position cursor at first brace (position 0)
        cursor = self.textEdit.textCursor()
        cursor.setPosition(0)
        self.textEdit.setTextCursor(cursor)

        # Trigger brace matching
        self.textEdit.cursorChanged()

        # Should match the first { at position 0 with the last } at position 11
        # NOT with the } inside the string at position 8
        self.assertIsNotNone(self.textEdit.parenthesisPair,
                            "Should find a matching brace pair")
        if self.textEdit.parenthesisPair:
            pos1, pos2 = self.textEdit.parenthesisPair
            self.assertEqual(pos1, 0, "First brace should be at position 0")
            self.assertEqual(pos2, 11, "Matching brace should be at position 11 (outer closing brace)")
            # Verify the matched characters
            self.assertEqual(text[pos1], '{', "First position should be opening brace")
            self.assertEqual(text[pos2], '}', "Second position should be closing brace")

    def test_brace_in_single_quote_string_ignored(self) -> None:
        """Test that braces inside single-quoted strings are ignored."""
        text = "{ '}' }"
        self.textEdit.setPlainText(text)
        self.textEdit.highlighter.setTextDocument(text)

        # Position cursor at first brace
        cursor = self.textEdit.textCursor()
        cursor.setPosition(0)
        self.textEdit.setTextCursor(cursor)

        self.textEdit.cursorChanged()

        self.assertIsNotNone(self.textEdit.parenthesisPair)
        if self.textEdit.parenthesisPair:
            pos1, pos2 = self.textEdit.parenthesisPair
            self.assertEqual(pos1, 0)
            self.assertEqual(pos2, 6, "Should match outer closing brace, not the one in the string")

    def test_nested_braces_with_string(self) -> None:
        """Test nested braces with strings containing braces."""
        text = '{ foo("{"); }'
        self.textEdit.setPlainText(text)
        self.textEdit.highlighter.setTextDocument(text)

        # Position cursor at first brace
        cursor = self.textEdit.textCursor()
        cursor.setPosition(0)
        self.textEdit.setTextCursor(cursor)

        self.textEdit.cursorChanged()

        self.assertIsNotNone(self.textEdit.parenthesisPair)
        if self.textEdit.parenthesisPair:
            pos1, pos2 = self.textEdit.parenthesisPair
            self.assertEqual(pos1, 0)
            self.assertEqual(pos2, 12, "Should match the outer braces, ignoring string content")

    def test_multiple_strings_with_braces(self) -> None:
        """Test multiple strings with braces."""
        text = '{ "}" + "{" }'
        self.textEdit.setPlainText(text)
        self.textEdit.highlighter.setTextDocument(text)

        cursor = self.textEdit.textCursor()
        cursor.setPosition(0)
        self.textEdit.setTextCursor(cursor)

        self.textEdit.cursorChanged()

        self.assertIsNotNone(self.textEdit.parenthesisPair)
        if self.textEdit.parenthesisPair:
            pos1, pos2 = self.textEdit.parenthesisPair
            self.assertEqual(pos1, 0)
            self.assertEqual(pos2, 12, "Should match outer braces, ignoring both strings")

    def test_escaped_quote_in_string(self) -> None:
        """Test that escaped quotes don't break string detection."""
        text = r'{ "test \"}" }'
        self.textEdit.setPlainText(text)
        self.textEdit.highlighter.setTextDocument(text)

        cursor = self.textEdit.textCursor()
        cursor.setPosition(0)
        self.textEdit.setTextCursor(cursor)

        self.textEdit.cursorChanged()

        self.assertIsNotNone(self.textEdit.parenthesisPair)
        if self.textEdit.parenthesisPair:
            pos1, pos2 = self.textEdit.parenthesisPair
            self.assertEqual(pos1, 0)
            self.assertEqual(pos2, 13, "Should match outer braces even with escaped quotes")

    def test_brace_in_comment_ignored(self) -> None:
        """Test that braces in comments are already being ignored (existing functionality)."""
        text = "{ // }\n}"
        self.textEdit.setPlainText(text)
        self.textEdit.highlighter.setTextDocument(text)

        cursor = self.textEdit.textCursor()
        cursor.setPosition(0)
        self.textEdit.setTextCursor(cursor)

        self.textEdit.cursorChanged()

        self.assertIsNotNone(self.textEdit.parenthesisPair)
        if self.textEdit.parenthesisPair:
            pos1, pos2 = self.textEdit.parenthesisPair
            self.assertEqual(pos1, 0)
            self.assertEqual(pos2, 7, "Should match braces ignoring the one in the comment")
