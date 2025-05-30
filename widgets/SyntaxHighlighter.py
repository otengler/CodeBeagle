# -*- coding: utf-8 -*-
"""
Copyright (C) 2020 Oliver Tengler

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

from typing import Tuple, List, Optional, Pattern
import bisect
import re
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCharFormat, QFont, QBrush, QColor
from fulltextindex.IStringMatcher import IStringMatcher

type foregroundType = QBrush|Qt.GlobalColor|QColor

class HighlightingRules:
    def __init__(self, font: QFont) -> None:
        self.rules: List[Tuple[Pattern, QTextCharFormat]] = []
        self.lineComment: Optional[Pattern] = None
        self.multiCommentStart: Optional[Pattern] = None
        self.multiCommentStop: Optional[Pattern] = None
        self.commentFormat: Optional[QTextCharFormat] = None
        self.font = font
        self.color: Optional[QColor] = None
        self.defaultFormat: Optional[QTextCharFormat] = None

    def addKeywords (self, keywords: str, fontWeight: int, foreground: foregroundType) -> None:
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

    def addRule (self, expr: str, fontWeight: int, foreground: foregroundType) -> None:
        """Adds an arbitrary highlighting rule."""
        fmt = self.__createFormat(fontWeight, foreground)
        self.__addRule (expr, fmt)

    def setColor(self, color: QColor) -> None:
        self.color = color
        fmt = QTextCharFormat() 
        fmt.setFont(self.font)
        fmt.setForeground(self.color)
        self.defaultFormat = fmt

    def setFont (self, font: QFont) -> None:
        """Needed to change the font after the HighlightingRules object has been created."""
        for rule in self.rules:
            rule[1].setFont(font)
        if self.commentFormat:
            self.commentFormat.setFont(font)
        if self.defaultFormat:
            self.defaultFormat.setFont(font)

    def __addRule (self, expr: str, fmt: QTextCharFormat) -> None:
        self.rules.append((re.compile(expr), fmt))

    def __createFormat (self, fontWeight:int, foreground: foregroundType) -> QTextCharFormat:
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
    matchBackgroundColor = Qt.GlobalColor.yellow
    matchForegroundColor = Qt.GlobalColor.black
    match2BackgroundColor = QColor(194, 217, 255)
    match2ForegroundColor = Qt.GlobalColor.black

    def __init__(self) -> None:
        # The current rules
        self.highlightingRules: Optional[HighlightingRules] = None

        self.searchStringFormats = [QTextCharFormat(), QTextCharFormat()]
        self.searchStringFormats[0].setBackground(SyntaxHighlighter.matchBackgroundColor)
        self.searchStringFormats[0].setForeground(SyntaxHighlighter.matchForegroundColor)
        self.searchStringFormats[1].setBackground(SyntaxHighlighter.match2BackgroundColor)
        self.searchStringFormats[1].setForeground(SyntaxHighlighter.match2ForegroundColor)

        self.comments: List[CommentRange]  = []
        self.searchDatas: List[Optional[IStringMatcher]] = [None, None]

    def setFont (self, font: QFont) -> None:
        if self.highlightingRules:
            self.highlightingRules.setFont (font)
        for strFormat in self.searchStringFormats:
            strFormat.setFont (font)

    def setHighlightingRules (self, rules: Optional[HighlightingRules]) -> None:
        self.highlightingRules = rules
        for strFormat in self.searchStringFormats:
            if rules:
                strFormat.setFont(rules.font)
            strFormat.setFontWeight(QFont.Bold)

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

    def setSearchData (self, searchData: Optional[IStringMatcher]) -> None:
        """searchData must support the function 'matches' which yields the tuple (start, length) for each match."""
        self.searchDatas[0] = searchData

    def setSearchData2 (self, searchData: Optional[IStringMatcher]) -> None:
        """searchData must support the function 'matches' which yields the tuple (start, length) for each match."""
        self.searchDatas[1] = searchData

    def highlightBlock(self, position: int, text: str) -> List[Tuple[QTextCharFormat, int, int]]:
        formats: List[Tuple[QTextCharFormat, int, int]] = []
        if not self.highlightingRules:
            return formats

        if self.highlightingRules.defaultFormat:
            formats.append((self.highlightingRules.defaultFormat, 0, len(text)))

        # Single line highlighting rules
        for expression, fmt in self.highlightingRules.rules:
            match = expression.search(text)
            while match:
                start,end = match.span()
                formats.append((fmt, start, end-start))
                match = expression.search(text, end)

        # Colorize comments
        if commentFormat := self.highlightingRules.commentFormat:
            pos = bisect.bisect_right (self.comments,  CommentRange(position))
            if pos > 0:
                pos -= 1
            while pos < len(self.comments):
                comment = self.comments[pos]
                # Comment starts before end of line
                if comment.index < position+len(text):
                    formats.append((commentFormat, comment.index-position, comment.length))
                else:
                    break
                pos += 1

        # Highlight search match
        for index, searchData in enumerate(self.searchDatas):
            if searchData:
                for matchPos, length in searchData.matches (text):
                    formats.append((self.searchStringFormats[index], matchPos, length))

        return formats

    def isInsideComment(self, position: int) -> bool:
        if not self.comments:
            return False
        pos = bisect.bisect_right (self.comments,  CommentRange(position))
        if pos > 0:
            pos -= 1
        comment = self.comments[pos]
        if comment.index <= position < comment.index + comment.length:
            return True
        return False
