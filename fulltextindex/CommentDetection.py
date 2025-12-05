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

from typing import List, Optional, Pattern, Iterator
import bisect
import re
import unittest
from dataclasses import dataclass

class TextSpan:
    """Represents a comment range in text with start index and length."""
    def __init__(self, index: int, length: int = 0) -> None:
        self.index = index
        self.length = length

    def __lt__(self, other: 'TextSpan') -> bool:
        return self.index < other.index
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TextSpan):
            return NotImplemented
        return self.index == other.index and self.length == other.length

@dataclass
class TextSegments:
    strings: List[TextSpan] 
    comments: List[TextSpan]

    def __iter__(self) -> Iterator[List[TextSpan]]:
        # return values in order you want to unpack
        yield self.strings
        yield self.comments


reQuote = re.compile("[\"\']")
reTripleQuote = re.compile(r'"""|\'\'\'')

def findAllStrings(line: str, findTripleQuotes: bool) -> List[TextSpan]:
    """Returns the position of all strings in a line as a list of TextSpan."""

    quotes = __findAllStrings(line, reQuote, allowMultiline=False)
    if not findTripleQuotes:
        return quotes
    
    tripleQuoteRanges = __findAllStrings(line, reTripleQuote, allowMultiline=True)
    quotes = [span for span in quotes if not isInsideTextSpan(span.index, tripleQuoteRanges)]
    quotes.extend(tripleQuoteRanges)
    quotes.sort()
    return quotes

def __findAllStrings(line: str, reQuote: Pattern, allowMultiline: bool = False) -> List[TextSpan]:
    """Returns the position of all strings in a line as a list of TextSpan."""
    strings: List[TextSpan] = []

    startPos = -1
    type = None  # None, ", '
    quotes = reQuote.finditer(line)
    for quote in quotes:
        quotePos = quote.start()

        # Check if quote is escaped. It counts as a valid quote if the number of backslashes is equal
        if __backSlashesBefore(line, quotePos) % 2 == 0:
            quoteChar = quote.group(0)
            if type is None:
                # type != quoteChar handles corrupt strings: ' "  or " ', use new char as type
                type = quoteChar
                startPos = quotePos
            elif type == quoteChar:
                # Check if there's a newline between start and end quote (only for single-line strings)
                if not allowMultiline and (line.find('\n', startPos, quotePos) != -1 or line.find('\r', startPos, quotePos) != -1):
                    # Not a valid single-line string - reset and treat current quote as new start
                    type = quoteChar
                    startPos = quotePos
                else:
                    # Found valid string
                    # Empty strings ("") or single quotes followed immediately by another quote
                    # should not be treated as string ranges
                    if quotePos > startPos:
                        strings.append(TextSpan(startPos, quote.end()-startPos))
                    type = None

    # Sort strings by start position
    strings.sort()
    return strings

def __backSlashesBefore(line: str, pos: int) -> int:
    """Count backslashes before a position."""
    pos -= 1
    backslashes = 0
    while pos >= 0:
        if line[pos] == '\\':
            backslashes += 1
            pos -= 1
        else:
            break
    return backslashes

def analyzeText(text: str,
                lineCommentPattern: Optional[Pattern],
                multiCommentStart: Optional[Pattern],
                multiCommentStop: Optional[Pattern],
                hasTripleQuotes: bool) -> TextSegments:
    r"""
    Find all comments and string ranges in the document and return them as TextSpan objects.

    Args:
        text: The text to analyze
        lineCommentPattern: Compiled regex pattern for single-line comments (e.g., r'//[^\n]*')
        multiCommentStart: Compiled regex pattern for multiline comment start (e.g., r'/\*')
        multiCommentStop: Compiled regex pattern for multiline comment end (e.g., r'\*/')
        hasTripleQuotes: True if the language has triple quote strings that are handled as comments. The expressions
          for multiCommentStart and multiCommentStop are left to None then.

    Returns:
        List of TextSpan objects representing all comments in the text
    """
    # First, find all string literals to exclude them from comment detection
    stringRanges = findAllStrings(text, hasTripleQuotes)

    commentRanges: List[TextSpan] = []

    # Collect all single line comments
    if lineCommentPattern:
        regLine = lineCommentPattern
        end = 0
        while True:
            beginMatch = regLine.search(text, end)
            if not beginMatch:
                break
            start, end = beginMatch.span()
            # Only add comment if it's not inside a string literal
            if not isInsideTextSpan(start, stringRanges):
                commentRanges.append(TextSpan(start, end - start))

    multiComments: List[TextSpan] = []

    # Now all multi line comments
    if multiCommentStart and multiCommentStop:
        regStart = multiCommentStart
        regEnd = multiCommentStop
        end = 0
        while True:
            beginMatch = regStart.search(text, end)
            if not beginMatch:
                break
            beginStart, end = beginMatch.span()
            # Only process if not inside a string literal or existing comment
            if not isInsideTextSpan(beginStart, stringRanges) and not isInsideTextSpan(beginStart, commentRanges):
                while True:
                    endMatch = regEnd.search(text, end)
                    if not endMatch:
                        multiComments.append(TextSpan(beginStart, len(text) - beginStart))
                        break
                    endStart, end = endMatch.span()
                    multiComments.append(TextSpan(beginStart, end - beginStart))
                    break

    commentRanges.extend(multiComments)
    commentRanges.sort()

    # Remove comments which are completely included in other comments
    i = 1
    while True:
        if i >= len(commentRanges):
            break
        prevComment = commentRanges[i - 1]
        comment = commentRanges[i]
        if comment.index >= prevComment.index and comment.index + comment.length < prevComment.index + prevComment.length:
            del commentRanges[i]
        else:
            i += 1

    return TextSegments(stringRanges, commentRanges)

def isInsideTextSpan(position: int, textSpans: List[TextSpan]) -> bool:
    """
    Check if a position is inside a TextSpan.

    Args:
        position: The position to check
        comments: List of TextSpan objects (must be sorted by index)

    Returns:
        True if the position is inside a TextSpan, False otherwise
    """
    if not textSpans:
        return False
    pos = bisect.bisect_right(textSpans, TextSpan(position))
    if pos > 0:
        pos -= 1
    comment = textSpans[pos]
    if comment.index <= position < comment.index + comment.length:
        return True
    return False


# ============================================================================
# Unit Tests
# ============================================================================

class TestGetAllStrings(unittest.TestCase):
    def test(self) -> None:
        import os
        r = findAllStrings("no string", False)
        self.assertEqual(r, [])

        testFile = os.path.join(os.getcwd(), "quoted_strings.txt")
        for fullLine in open(testFile,"r"):
            pos = fullLine.find("|")
            if pos == -1:
                continue
            quotedStrings: List[TextSpan] = []
            line = fullLine[0:pos]
            segments = fullLine[pos+1:].strip()
            findTripleQuotes = segments.startswith("T") # triple quotes
            if findTripleQuotes:
                segments = segments[1:]
            parts = segments.strip().split(";")
            for part in parts:
                part = part.strip()
                range = part.split(",")
                start = int(range[0].replace("(", ""))
                stop = int(range[1].replace(")", ""))
                quotedStrings.append(TextSpan(start,stop-start+1))
            findAllStringTest(self, line, quotedStrings, findTripleQuotes=findTripleQuotes)

def findAllStringTest(test: unittest.TestCase, line: str, expected: list, findTripleQuotes: bool = False) -> None:
    r = findAllStrings(line, findTripleQuotes)
    test.assertListEqual(r, expected)

class TestFindAllComments(unittest.TestCase):
    """Test comment detection for various languages."""

    def test_cpp_single_line_comments(self) -> None:
        text = """int main() {
    // This is a comment
    return 0;
}"""
        strings, comments = analyzeText(text, re.compile(r'//[^\n]*'), None, None, False)
        self.assertEqual(len(comments), 1)
        self.assertTrue("// This is a comment" in text[comments[0].index:comments[0].index + comments[0].length])

    def test_cpp_multiline_comments(self) -> None:
        text = """int main() {
    /* This is a
       multiline comment */
    return 0;
}"""
        strings, comments = analyzeText(text, None, re.compile(r'/\*'), re.compile(r'\*/'), False)
        self.assertEqual(len(comments), 1)
        self.assertTrue("/* This is a" in text[comments[0].index:comments[0].index + comments[0].length])

    def test_python_comments(self) -> None:
        text = """def hello():
    # This is a comment
    print("hello")
    # Another comment
"""
        strings, comments = analyzeText(text, re.compile(r'#[^\n]*'), None, None, False)
        self.assertEqual(len(comments), 2)

    def test_comments_inside_strings_ignored(self) -> None:
        text = 'char* s = "// not a comment";'
        string, comments = analyzeText(text, re.compile(r'//[^\n]*'), None, None, False)
        self.assertEqual(len(comments), 0)

    def test_multiline_comment_inside_string_ignored(self) -> None:
        text = 'char* s = "/* not a comment */";'
        strings, comments = analyzeText(text, None, re.compile(r'/\*'), re.compile(r'\*/'), False)
        self.assertEqual(len(comments), 0)

    def test_mixed_comments_and_strings(self) -> None:
        text = '''// First comment
char* s1 = "// not a comment";
/* Second comment */
char* s2 = "/* also not a comment */";
// Third comment'''

        strings, comments = analyzeText(text, re.compile(r'//[^\n]*'), re.compile(r'/\*'), re.compile(r'\*/'), False)
        self.assertEqual(len(comments), 3)

    def test_unclosed_multiline_comment(self) -> None:
        text = "/* This comment never closes"
        strings, comments = analyzeText(text, None, re.compile(r'/\*'), re.compile(r'\*/'), False)
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].length, len(text))


class TestIsInsideComment(unittest.TestCase):
    """Test position checking within comments."""

    def test_empty_comments(self) -> None:
        self.assertFalse(isInsideTextSpan(0, []))
        self.assertFalse(isInsideTextSpan(100, []))

    def test_inside_single_comment(self) -> None:
        comments = [TextSpan(10, 10)]
        self.assertFalse(isInsideTextSpan(9, comments))
        self.assertTrue(isInsideTextSpan(10, comments))
        self.assertTrue(isInsideTextSpan(19, comments))
        self.assertFalse(isInsideTextSpan(20, comments))
        self.assertFalse(isInsideTextSpan(35, comments))

    def test_multiple_comments(self) -> None:
        comments = [TextSpan(10, 2), TextSpan(30, 10), TextSpan(50, 10)]
        self.assertFalse(isInsideTextSpan(5, comments))
        self.assertTrue(isInsideTextSpan(11, comments))
        self.assertFalse(isInsideTextSpan(25, comments))
        self.assertTrue(isInsideTextSpan(35, comments))
        self.assertTrue(isInsideTextSpan(39, comments))
        self.assertFalse(isInsideTextSpan(45, comments))
        self.assertTrue(isInsideTextSpan(55, comments))
        self.assertFalse(isInsideTextSpan(65, comments))

class TestCommentExclusionInQueries(unittest.TestCase):
    """Test that queries correctly exclude matches in comments."""

    def test_match_outside_comment(self) -> None:
        from .Query import QueryParams, ContentQuery
        from .CommentRule import CommentRule

        text = """int foo() {
    return 42;  // foo in comment
}"""
        # Create comment rules for C++
        def getCommentRule(_: str) -> Optional[CommentRule]:
            return CommentRule(lineComment=re.compile(r'//[^\n]*'),
                               multiCommentStart=re.compile(r'/\*'),
                               multiCommentStop=re.compile(r'\*/'),
                               hasTripleQuotes=False)

        # Search without comment exclusion
        params = QueryParams("foo", bExcludeComments=False)
        query = ContentQuery(params)
        matches = list(query.matches(text, "test.cpp"))
        self.assertEqual(len(matches), 2)  # Both "foo" matches

        # Search with comment exclusion
        params = QueryParams("foo", bExcludeComments=True, commentRuleFetcher=getCommentRule)
        query = ContentQuery(params)
        matches = list(query.matches(text, "test.cpp"))
        self.assertEqual(len(matches), 1)  # Only the function name, not the comment

    def test_match_in_multiline_comment_excluded(self) -> None:
        from .Query import QueryParams, ContentQuery
        from .CommentRule import CommentRule

        text = """/* This is a BLUB
   that spans multiple lines */
int main() {
    // Another BLUB
    return 0;  // BLUB fix this
}"""

        # Create comment rules for C++
        def getCommentRule(_: str) -> Optional[CommentRule]:
            return CommentRule(lineComment=re.compile(r'//[^\n]*'),
                               multiCommentStart=re.compile(r'/\*'),
                               multiCommentStop=re.compile(r'\*/'),
                               hasTripleQuotes=False)

        # Without exclusion: should find 3 BLUBs
        params = QueryParams("BLUB", bExcludeComments=False)
        query = ContentQuery(params)
        matches = list(query.matches(text, "test.cpp"))
        self.assertEqual(len(matches), 3)

        # With exclusion: should find 0 BLUBs (all in comments)
        params = QueryParams("BLUB", bExcludeComments=True, commentRuleFetcher=getCommentRule)
        query = ContentQuery(params)
        matches = list(query.matches(text, "test.cpp"))
        self.assertEqual(len(matches), 0)

    def test_no_comment_rules_for_extension(self) -> None:
        from .Query import QueryParams, ContentQuery
        from .CommentRule import CommentRule

        text = "# BLUB fix this\nprint('hello')"
        
        def getCommentRule(_: str) -> Optional[CommentRule]:
            return None
        
        # No rules for .txt extension, should show all matches
        params = QueryParams("BLUB", bExcludeComments=True, commentRuleFetcher=getCommentRule)
        query = ContentQuery(params)
        matches = list(query.matches(text, "test.txt"))
        self.assertEqual(len(matches), 1)


if __name__ == "__main__":
    unittest.main()
