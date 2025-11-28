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
import unittest
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCharFormat, QFont, QBrush, QColor
from fulltextindex.IStringMatcher import IStringMatcher
from fulltextindex.CommentDetection import TextSpan, analyzeText, isInsideTextSpan

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
        self.hasTripleQuotes = False
      
    def addKeywords (self, keywords: str, fontWeight: int, foreground: foregroundType) -> None:
        """Adds a list of comma separated keywords."""
        keywords = keywords.strip()
        kwList = keywords.split(",")
        # We build a single expression which matches all keywords
        expr = "|".join(("\\b" + kw + "\\b" for kw in kwList))
        self.addRule (expr, fontWeight, foreground)

    def setStrings(self, fontWeight: int, foreground: foregroundType, supportTripleQuotes: bool = False) -> None:
        self.hasTripleQuotes = supportTripleQuotes
        self.stringFormat = self.__createFormat(fontWeight, foreground)

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

class SyntaxHighlighter:
    matchBackgroundColor = Qt.GlobalColor.yellow
    matchBackgroundColorLigher  = QColor.lighter(QColor(Qt.GlobalColor.yellow))
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

        self.strings: List[TextSpan]  = []
        self.comments: List[TextSpan]  = []
        self.searchDatas: List[Optional[IStringMatcher]] = [None, None]
        self.filename = ""

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

    # Find all comments in the document and store them as TextSpan objects in self.comments
    def setTextDocument(self, text: str, filename = "") -> None:
        self.filename = filename
        if not self.highlightingRules:
            self.comments = []
            return

        # Use the shared comment detection logic from CommentDetection module
        self.strings, self.comments = analyzeText(text,
            self.highlightingRules.lineComment,
            self.highlightingRules.multiCommentStart,
            self.highlightingRules.multiCommentStop,
            self.highlightingRules.hasTripleQuotes)

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

        # Colorize strings
        if formatStrings := self.highlightingRules.stringFormat:
            SyntaxHighlighter.__colorizeTextSpans(text, position, self.strings, formatStrings, formats)

        # Colorize comments
        if formatComments := self.highlightingRules.commentFormat:
            SyntaxHighlighter.__colorizeTextSpans(text, position, self.comments, formatComments, formats)

        # Highlight search match
        for index, matchPos, length in self.getSearchDataMatches(text):
            formats.append((self.searchStringFormats[index], matchPos, length))

        return formats
    
    @staticmethod
    def __colorizeTextSpans(text: str, position: int, textSpans: List[TextSpan], format: QTextCharFormat, formats: List[Tuple[QTextCharFormat, int, int]]) -> None:
        pos = bisect.bisect_right (textSpans,  TextSpan(position))
        if pos > 0:
            pos -= 1
        while pos < len(textSpans):
            textSpan = textSpans[pos]
            # Comment or string starts before end of line
            if textSpan.index < position+len(text):
                formats.append((format, textSpan.index-position, textSpan.length))
            else:
                break
            pos += 1

    def getSearchDataMatches(self, text: str) -> List[Tuple[int, int, int]]:
        # Return tuple of highlight search matches. Each tuple contains:
        # [0]: index of match 0 = match, 1 = in document search
        # [1]: match position
        # [2]: match length
        formats: List[Tuple[int, int, int]] = []
        for index, searchData in enumerate(self.searchDatas):
            if searchData:
                for matchPos, length in searchData.matches (text, self.filename):
                    formats.append((index, matchPos, length))
        return formats

    def isInsideComment(self, position: int) -> bool:
        return isInsideTextSpan(position, self.comments)
    
class TestCommentDetectionWithStrings(unittest.TestCase):
    """Test that comment markers inside strings are not treated as comments."""

    def setUp(self) -> None:
        """Set up a highlighter with C-style comment rules."""
        from PyQt5.QtGui import QFont, QBrush
        from PyQt5.QtCore import Qt

        self.rules = HighlightingRules(QFont())
        self.rules.addCommentRule(r'//.*', r'/\*', r'\*/', 400, QBrush(Qt.GlobalColor.darkGreen))

        self.highlighter = SyntaxHighlighter()
        self.highlighter.setHighlightingRules(self.rules)

    def test_multiline_comment_inside_string_ignored(self) -> None:
        """Test that /* */ inside a string is not treated as a comment."""
        text = 'char* pattern = "/* not a comment */";'
        self.highlighter.setTextDocument(text)

        # Should find no comments
        self.assertEqual(len(self.highlighter.comments), 0,
                        "Comment markers inside strings should be ignored")

    def test_single_line_comment_inside_string_ignored(self) -> None:
        """Test that // inside a string is not treated as a comment."""
        text = 'char* url = "https://example.com";'
        self.highlighter.setTextDocument(text)

        # Should find no comments
        self.assertEqual(len(self.highlighter.comments), 0,
                        "Single-line comment markers inside strings should be ignored")

    def test_real_comments_still_detected(self) -> None:
        """Test that real comments outside strings are still detected."""
        text = '''char* url = "https://example.com";
/* real comment */
char* pattern = "/* not a comment */";
// real line comment'''

        self.highlighter.setTextDocument(text)

        # Should find exactly 2 comments (the real ones)
        self.assertEqual(len(self.highlighter.comments), 2,
                        "Should detect exactly 2 real comments")

        # Verify the real multiline comment
        comment1 = self.highlighter.comments[0]
        self.assertEqual(text[comment1.index:comment1.index + comment1.length],
                        "/* real comment */",
                        "First comment should be the real multiline comment")

        # Verify the real line comment
        comment2 = self.highlighter.comments[1]
        self.assertEqual(text[comment2.index:comment2.index + comment2.length],
                        "// real line comment",
                        "Second comment should be the real line comment")

    def test_escaped_quotes_with_comments(self) -> None:
        """Test that escaped quotes don't confuse the comment detection."""
        text = r'char* s = "He said \"hello /* world */\""; /* real comment */'
        self.highlighter.setTextDocument(text)

        # Should find exactly 1 comment (the real one at the end)
        self.assertEqual(len(self.highlighter.comments), 1,
                        "Should detect only the real comment outside the string")

        comment = self.highlighter.comments[0]
        self.assertEqual(text[comment.index:comment.index + comment.length],
                        "/* real comment */",
                        "Should detect the real comment at the end")

    def test_multiple_strings_and_comments(self) -> None:
        """Test complex scenario with multiple strings and comments."""
        text = '''// First comment
char* s1 = "// not a comment";
/* Second comment */
char* s2 = "/* also not a comment */";
// Third comment'''

        self.highlighter.setTextDocument(text)

        # Should find exactly 3 real comments
        self.assertEqual(len(self.highlighter.comments), 3,
                        "Should detect exactly 3 real comments")

        # Verify each comment
        self.assertTrue(text[self.highlighter.comments[0].index:].startswith("// First comment"))
        self.assertTrue(text[self.highlighter.comments[1].index:].startswith("/* Second comment */"))
        self.assertTrue(text[self.highlighter.comments[2].index:].startswith("// Third comment"))

    def test_single_quote_strings(self) -> None:
        """Test that comment markers in single-quoted strings are also ignored."""
        text = "char c = '/*'; /* real comment */ char d = '//';"
        self.highlighter.setTextDocument(text)

        # Should find exactly 1 comment (the real multiline comment)
        self.assertEqual(len(self.highlighter.comments), 1,
                        "Should detect only the real comment, not markers in single-quoted strings")

        comment = self.highlighter.comments[0]
        self.assertEqual(text[comment.index:comment.index + comment.length],
                        "/* real comment */",
                        "Should detect the real comment")

if __name__ == "__main__":
    unittest.main()