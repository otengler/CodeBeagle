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

from typing import Tuple, List, Optional, Iterator
import bisect
from PyQt5.QtCore import Qt, QRegExp, pyqtSignal, QTimer, QRect, QRectF
from PyQt5.QtGui import QTextCharFormat, QFont, QTextLayout, QPainter, QBrush, QPaintEvent, QTextBlock, QResizeEvent
from PyQt5.QtWidgets import QPlainTextEdit, QWidget
from fulltextindex.FullTextIndex import Query
from AppConfig import appConfig
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
        self.rules: List[Tuple[QRegExp, QTextCharFormat]] = []
        self.lineComment: Optional[QRegExp] = None
        self.multiCommentStart: Optional[QRegExp] = None
        self.multiCommentStop: Optional[QRegExp] = None
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
        self.lineComment = QRegExp(singleLine)
        if multiLineStart and multiLineEnd:
            self.multiCommentStart = QRegExp(multiLineStart)
            self.multiCommentStop = QRegExp(multiLineEnd)

    def addRule (self, expr: QRegExp, fontWeight: int, foreground: QBrush) -> None:
        """Adds an arbitrary highlighting rule."""
        fmt = self.__createFormat(fontWeight, foreground)
        self.__addRule (expr, fmt)

    def setFont (self, font: QFont) -> None:
        """Needed to change the font after the HighlightingRules object has been created."""
        for rule in self.rules:
            rule[1].setFont(font)
        if self.commentFormat:
            self.commentFormat.setFont(font)

    def __addRule (self, expr: QRegExp, fmt: QTextCharFormat) -> None:
        self.rules.append((QRegExp(expr), fmt))

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

    def setHighlightingRules (self, rules: HighlightingRules, text: str) -> None:
        self.highlightingRules = rules
        self.searchStringFormat.setFont(rules.font)
        self.searchStringFormat.setFontWeight(QFont.Bold)
        # Text is needed to compute the syntax highlighting for multiline comments
        self.__setText(text)

    # Find all multiline comments in the document and store them as CommentRange objects in self.comments
    def __setText(self, text: str) -> None:
        comments: List[CommentRange] = []
        if self.highlightingRules:
            if self.highlightingRules.multiCommentStart and self.highlightingRules.multiCommentStop:
                regLine = self.highlightingRules.lineComment
                regStart = self.highlightingRules.multiCommentStart
                regEnd = self.highlightingRules.multiCommentStop
                startIndex = regStart.indexIn(text)
                while startIndex>=0:
                    matchedLenStart = regStart.matchedLength()
                    line = textLineBefore (text, startIndex+matchedLenStart) # +matchedLenStart too catch things like "//*"
                    # Check if the multi line comment is commented out
                    if regLine and regLine.indexIn (line) == -1:
                        endIndex = regEnd.indexIn(text, startIndex+matchedLenStart)
                        if endIndex == -1: # comment opened but not closed
                            comments.append (CommentRange(startIndex,  len(text)-startIndex))
                            break
                        matchedLenEnd = regEnd.matchedLength()
                        comments.append (CommentRange(startIndex,  endIndex+matchedLenEnd-startIndex))
                    else:
                        endIndex = startIndex
                        matchedLenEnd = matchedLenStart
                    startIndex = regStart.indexIn(text,  endIndex+matchedLenEnd)
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
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                formats.append((fmt, index, length))
                index = expression.indexIn(text, index + length)

        # Colorize multiline comments
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

        # Single line comments
        if self.highlightingRules.lineComment:
            index = self.highlightingRules.lineComment.indexIn(text)
            while index >= 0:
                length = self.highlightingRules.lineComment.matchedLength()
                formats.append((self.highlightingRules.commentFormat,  index, length))
                index = self.highlightingRules.lineComment.indexIn(text, index + length)

        # Search match highlight
        if self.searchData:
            for index, length in self.searchData.matches (text):
                formats.append((self.searchStringFormat, index, length))

        return formats

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

        self.lineNumberArea: LineNumberArea = LineNumberArea(self)
        self.showLineNumbers(appConfig().SourceViewer.showLineNumbers)

    def areLineNumbersShown(self) -> bool:
        return bool(self.lineNumberArea.isVisible())

    def showLineNumbers(self, show: bool) -> None:
        if show:
            self.lineNumberArea.show()
        else:
            self.lineNumberArea.hide()

    def resizeEvent(self, e: QResizeEvent) -> None:
        super().resizeEvent(e)
        if self.lineNumberArea.isVisible():
            self.lineNumberArea.reactOnResize(e)

    def setPlainText(self, text: str) -> None:
        super().setPlainText(text)
        # For whatever reasons some lines are not highlighted properly without another 'update'
        QTimer.singleShot (10, self.viewport().update)

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
