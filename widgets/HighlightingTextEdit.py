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

from typing import Tuple, List, Optional, Iterator, Pattern
import bisect
import re
from PyQt5.QtCore import Qt, pyqtSignal, QRect, QRectF, pyqtSlot
from PyQt5.QtGui import QTextCharFormat, QFont, QTextLayout, QPainter, QBrush, QPaintEvent, QTextBlock, QResizeEvent
from PyQt5.QtWidgets import QPlainTextEdit, QWidget
from fulltextindex.FullTextIndex import Query
from .LineNumberArea import LineNumberArea

def textLineBefore(text: str, index: int) -> str:
    pos = index
    while pos > 0:
        pos -= 1
        if text[pos] == "\n":
            return text[pos+1:index]
    return text[0:index]

class HighlightingRules:
    def __init__(self, font: QFont) -> None:
        self.rules: List[Tuple[Pattern, QTextCharFormat]] = []
        self.lineComment: Optional[Pattern] = None
        self.multiCommentStart: Optional[Pattern] = None
        self.multiCommentStop: Optional[Pattern] = None
        self.commentFormat: Optional[QTextCharFormat] = None
        self.font = font

    def addKeywords (self, keywords: str, fontWeight: int, foreground: QBrush) -> None:
        """Adds a list of comma separated keywords."""
        keywords = keywords.strip()
        kwList = keywords.split(",")
        # We build a single expression which matches all keywords
        expr = "|".join(("\\b" + kw + "\\b" for kw in kwList))
        self.addRule (expr, fontWeight, foreground)

    def addCommentRule (self, singleLine: str, multiLineStart: str, multiLineEnd: str, fontWeight: int, foreground: QBrush) -> None:
        """Adds comment rules. Each parameter is a regular expression  string. The multi line parameter are optional and can be empty."""
        self.commentFormat = self.__createFormat(fontWeight,  foreground)
        self.lineComment = re.compile(singleLine)
        if multiLineStart and multiLineEnd:
            self.multiCommentStart = re.compile(multiLineStart)
            self.multiCommentStop = re.compile(multiLineEnd)

    def addRule (self, expr: str, fontWeight: int, foreground: QBrush) -> None:
        """Adds an arbitrary highlighting rule."""
        fmt = self.__createFormat(fontWeight, foreground)
        self.__addRule (expr, fmt)

    def setFont (self, font: QFont) -> None:
        """Needed to change the font after the HighlightingRules object has been created."""
        for rule in self.rules:
            rule[1].setFont(font)
        if self.commentFormat:
            self.commentFormat.setFont(font)

    def __addRule (self, expr: str, fmt: QTextCharFormat) -> None:
        self.rules.append((re.compile(expr), fmt))

    def __createFormat (self, fontWeight:int, foreground: QBrush) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setFont(self.font)
        fmt.setFontWeight(fontWeight)
        fmt.setForeground(foreground)
        return fmt

class CommentRange:
    def __init__(self, index: int, length: int=0) -> None:
        self.index = index
        self.length = length

    def __lt__ (self, other: 'CommentRange') -> bool:
        return self.index < other.index

class SyntaxHighlighter:
    def __init__(self) -> None:
        # The current rules
        self.highlightingRules: Optional[HighlightingRules] = None

        self.searchStringFormat = QTextCharFormat()
        self.searchStringFormat.setBackground(Qt.yellow)
        self.searchStringFormat.setForeground(Qt.black)

        self.comments: List[CommentRange]  = []
        self.searchData: Optional[Query] = None

    def setFont (self, font: QFont) -> None:
        if self.highlightingRules:
            self.highlightingRules.setFont (font)

    def setHighlightingRules (self, rules: HighlightingRules) -> None:
        self.highlightingRules = rules
        self.searchStringFormat.setFont(rules.font)
        self.searchStringFormat.setFontWeight(QFont.Bold)

    # Find all comments in the document and store them as CommentRange objects in self.comments
    def setText(self, text: str) -> None:
        if not self.highlightingRules:
            self.comments = []
            return

        comments: List[CommentRange] = []

        # Collect all single line comments
        if self.highlightingRules.lineComment:
            regLine = self.highlightingRules.lineComment
            end = 0
            while True:
                beginMatch = regLine.search(text, end)
                if not beginMatch:
                    break
                start,end = beginMatch.span()
                comments.append (CommentRange(start, end - start))

        self.comments = comments

        multiComments: List[CommentRange] = []

        # Now all multi line comments
        if self.highlightingRules.multiCommentStart and self.highlightingRules.multiCommentStop:
            regStart = self.highlightingRules.multiCommentStart
            regEnd = self.highlightingRules.multiCommentStop
            end = 0
            while True:
                beginMatch = regStart.search(text, end)
                if not beginMatch:
                    break
                beginStart,end = beginMatch.span()
                if not self.isInsideComment(beginStart):
                    while True:
                        endMatch = regEnd.search(text, end)
                        if not endMatch:
                            multiComments.append (CommentRange(beginStart, len(text) - beginStart))
                            break
                        endStart,end = endMatch.span()
                        if not self.isInsideComment(endStart):
                            multiComments.append (CommentRange(beginStart, end - beginStart))
                            break

        comments.extend(multiComments)
        comments.sort()

        # Remove comments which are completely included in other comments
        i = 1
        while True:
            if i >= len(comments):
                break
            prevComment = comments[i-1]
            comment = comments[i]
            if comment.index >= prevComment.index and comment.index + comment.length < prevComment.index + prevComment.length:
                del comments[i]
            else:
                i += 1

        self.comments = comments

    def setSearchData (self, searchData: Query) -> None:
        """searchData must support the function 'matches' which yields the tuple (start, length) for each match."""
        self.searchData = searchData

    def highlightBlock(self, position: int, text: str) -> List[Tuple[QTextCharFormat, int, int]]:
        formats: List[Tuple[QTextCharFormat, int, int]] = []
        if not self.highlightingRules:
            return formats

        # Single line highlighting rules
        for expression, fmt in self.highlightingRules.rules:
            match = expression.search(text)
            while match:
                start,end = match.span()
                formats.append((fmt, start, end-start))
                match = expression.search(text, end)

        # Colorize comments
        pos = bisect.bisect_right (self.comments,  CommentRange(position))
        if pos > 0:
            pos -= 1
        while pos < len(self.comments):
            comment = self.comments[pos]
            # Comment starts before end of line
            if comment.index < position+len(text):
                formats.append((self.highlightingRules.commentFormat, comment.index-position, comment.length))
            else:
                break
            pos += 1

        # Search match highlight
        if self.searchData:
            for index, length in self.searchData.matches (text):
                formats.append((self.searchStringFormat, index, length))

        return formats

    def isInsideComment(self, position: int) -> bool:
        if not self.comments:
            return False
        pos = bisect.bisect_right (self.comments,  CommentRange(position))
        if pos > 0:
            pos -= 1
        comment = self.comments[pos]
        if comment.index >= position < comment.index + comment.length:
            return True
        return False

class HighlightingTextEdit (QPlainTextEdit):
    updateNeeded = pyqtSignal()

    def __init__ (self, parent: QWidget) -> None:
        super().__init__(parent)
        self.highlighter = SyntaxHighlighter()
        self.dynamicHighlight: Optional[str] = None
        self.setUndoRedoEnabled(False)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setReadOnly(True)
        self.setTextInteractionFlags(Qt.TextSelectableByKeyboard|Qt.TextSelectableByMouse)

        self.lineNumberArea: Optional[LineNumberArea] = None

        self.cursorPositionChanged.connect (self.cursorChanged)

    @pyqtSlot()
    def cursorChanged(self) -> None:
        pos = self.textCursor().position()
        text = self.document().toPlainText()
        char = text[pos:pos+1]
        # if char in ['(','[','{']:
        #     print("Zeichen" , char)

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

    def setFont(self, font: QFont) -> None:
        super().setFont (font)
        self.viewport().setFont(font)
        self.highlighter.setFont(font)

    def paintEvent(self, event: QPaintEvent) -> None:
        firstVisibleBlock: QTextBlock = self.firstVisibleBlock()
        bColorizedBlocks = self.colorizeVisibleBlocks(firstVisibleBlock)

        super().paintEvent(event)

        if self.dynamicHighlight:
            painter = QPainter(self.viewport())
            metrics = painter.fontMetrics()
            for block, bound in self.visibleBlocks(firstVisibleBlock):
                bound = QRect(bound.left(), bound.top(), bound.width(), bound.height()) 
                startIndex = 0
                while startIndex != -1:
                    startIndex = block.text().find(self.dynamicHighlight, startIndex)
                    if startIndex != -1:
                        partBefore = block.text()[:startIndex]
                        rectBefore = metrics.boundingRect(bound, Qt.TextExpandTabs, partBefore,  self.tabStopWidth())
                        rectText = metrics.boundingRect(bound, Qt.TextExpandTabs,  self.dynamicHighlight, self.tabStopWidth())
                        rectResult = QRect(rectBefore.right()+4,  rectBefore.top()+1,  rectText.width()+2,  rectText.height()-2)
                        painter.setPen(Qt.darkGray)
                        painter.drawRect(rectResult)
                        painter.drawText(QRectF(rectBefore.right()+5,rectBefore.top(),rectText.width(),rectText.height()), self.dynamicHighlight)
                        startIndex += len(self.dynamicHighlight)

        # Sometimes lines which are highlighted for the first time are not updated properly.
        # This happens regularily if the text edit is scolled using the page down key.
        # The following signal is emited if new lines were highlighted. The receiver
        # is expected to call "update" on the control. Not nice but it works...
        if bColorizedBlocks:
            self.updateNeeded.emit()

    def colorizeVisibleBlocks(self, firstVisibleBlock: QTextBlock) -> bool:
        bColorizedBlocks = False
        for block, _ in self.visibleBlocks(firstVisibleBlock):
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

    def visibleBlocks (self, firstVisibleBlock: QTextBlock) -> Iterator[Tuple[QTextBlock, QRectF]]:
        size = self.viewport().size()
        block = firstVisibleBlock
        while block.isValid():
            bound = self.blockBoundingGeometry(block).translated(self.contentOffset())
            if bound.top() > size.height():
                break
            yield block, bound
            block = block.next()
