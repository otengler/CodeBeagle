# -*- coding: utf-8 -*-
"""
Copyright (C) 2026 Oliver Tengler

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

import bisect
import re
import unittest
import threading
from typing import List, Tuple, Optional, Callable, TYPE_CHECKING
from tools.FileTools import freadall

if TYPE_CHECKING:
    from fulltextindex.Query import ContentQuery

# exports when importing with "*"
__all__ = ['LineMapping', 'MatchesInFile', 'extractMatches', 'collapseAdjoiningRanges']

# Accepts a list of tuples each containing a start and end index. After calling the function
# consecutive tuples which overlapped or adjoin are collapsed into one tuple. This is done in place.
# ranges = [(1,3),(2,5),(7,2)]
# Result is [(1,5),(7,2)]
def collapseAdjoiningRanges(ranges: List[Tuple[int,int]]) -> None:
    if len(ranges) <= 1:
        return

    result = [ranges[0]]

    for r2 in ranges[1:]:
        r1 = result[-1]
        if r1[1] + 1 >= r2[0]:
            result[-1] = (r1[0], r2[1])
        else:
            result.append(r2)

    ranges[:] = result

class TestCollapseOverlappingRanges(unittest.TestCase):
    def test(self) -> None:
        ranges: List[Tuple[int,int]] = []
        collapseAdjoiningRanges(ranges)
        self.assertEqual(ranges, [])
        ranges = [(1, 3), (5, 7)]
        collapseAdjoiningRanges(ranges)
        self.assertEqual(ranges, [(1, 3), (5, 7)])
        ranges = [(1,3),(2,5),(7, 9)]
        collapseAdjoiningRanges(ranges)
        self.assertEqual(ranges, [(1, 5), (7, 9)])
        ranges = [(1,2),(3,5),(4, 9)]
        collapseAdjoiningRanges(ranges)
        self.assertEqual(ranges, [(1, 9)])

class Line:
    def __init__(self, charPos: int, lineNumber: int) -> None:
        self.charPos = charPos
        self.lineNumber = lineNumber

    def __lt__ (self, other: 'Line') -> bool:
        return self.charPos < other.charPos

# Detects quickly which character position corresponds to which line number.
# The first line number is 1.
class LineMapping:
    def __init__(self, text: str) -> None:
        self.list: List[Line] = []
        self.numberMap = {1:0} # line 1 always starts at 0
        self.text = text

        reLineBreak = re.compile("\\n")
        cur = 0
        line = 1
        while True:
            result = reLineBreak.search(text, cur)
            if result:
                startPos, endPos = result.span()
                self.list.append(Line(startPos, line))
                self.numberMap[line+1] = endPos
                cur = endPos
                line = line + 1
            else:
                break

    def findLineNumber(self, charPos: int) -> int:
        if not self.list:
            return 0
        pos = bisect.bisect_left(self.list, Line(charPos, 0))
        if pos >= len(self.list):
            return self.list[-1].lineNumber+1
        return self.list[pos].lineNumber

    def getLine(self, lineNumber: int) -> str:
        if lineNumber == 0 or lineNumber > len(self.numberMap):
            return ""
        startPos = self.numberMap[lineNumber]
        if lineNumber == len(self.numberMap):
            endPos = len(self.text)
        else:
            endPos = self.numberMap[lineNumber+1]-1
        return self.text[startPos:endPos]

    def lineCount(self) -> int:
        return len(self.numberMap)

class TestLineMapping(unittest.TestCase):
    def test(self) -> None:
        m = LineMapping("")
        self.assertEqual(m.lineCount(), 1)
        self.assertEqual(m.findLineNumber(0), 0)
        self.assertEqual(m.findLineNumber(10), 0)

        #                0000000000011111111111
        #                012345 67890 12345 678
        m = LineMapping("hallo\nwelt\ntest\n123")
        self.assertEqual(m.lineCount(), 4)
        exp = {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 2, 7: 2, 8: 2, 9: 2, 10: 2, 11: 3, 12: 3, 13: 3, 14: 3, 15: 3, 16: 4, 17: 4, 18: 4, 19: 4, 20: 4, 21: 4, 22: 4, 23: 4, 24: 4}
        for charPos, lineNumber in exp.items():
            self.assertEqual(m.findLineNumber(charPos), lineNumber)
        self.assertEqual(m.getLine(0),  "")
        self.assertEqual(m.getLine(1),  "hallo")
        self.assertEqual(m.getLine(2),  "welt")
        self.assertEqual(m.getLine(3),  "test")
        self.assertEqual(m.getLine(4),  "123")
        self.assertEqual(m.getLine(5),  "")

class MatchesInFile:
    def __init__(self, name: str) -> None:
        self.name = name
        self.matches: List[Tuple[int, List[str]]] = []

    def addMatches(self, nLineNumberStart: int, lines: List[str]) -> None:
        self.matches.append((nLineNumberStart, lines))

ProgressFunction = Callable[[int], None]

# Returns a list of all matches in all files
# This reads all files and retrieves the matches with some lines surrounding them
def extractMatches(matches: List[str], searchData: 'ContentQuery', linesOfContext: int,
                   cancelEvent: Optional[threading.Event]=None,
                   reportProgress: Optional[ProgressFunction]=None) -> List[MatchesInFile]:
    results: List[MatchesInFile] = []
    lenMatches = len(matches)
    lastProgress = None
    idx = 1
    for name in matches:
        matchList = MatchesInFile(name)
        try:
            text = freadall(name)
        except Exception:
            matchList.addMatches(0, ["Failed to open file"])
        else:
            lineIndex = LineMapping(text)
            ranges = []
            for startPos, _ in searchData.matches(text, name):
                lineNumber = lineIndex.findLineNumber(startPos)
                startLine = lineNumber-linesOfContext
                if startLine < 1:
                    startLine = 1
                endLine = lineNumber+linesOfContext
                if endLine > lineIndex.lineCount():
                    endLine = lineIndex.lineCount()
                ranges.append((startLine, endLine))
            # Collapse overlapping ranges into one
            collapseAdjoiningRanges(ranges)
            for startLine, endLine in ranges:
                lines = []
                for i in range(startLine, endLine+1):
                    lines.append(lineIndex.getLine(i))
                matchList.addMatches(startLine, lines)
            results.append(matchList)
        if cancelEvent and cancelEvent.is_set():
            return results
        if reportProgress:
            progress = (int((idx*100)/lenMatches))
            idx += 1
            if lastProgress != progress:
                lastProgress = progress
                reportProgress(progress)
    return results

if __name__ == "__main__":
    unittest.main()