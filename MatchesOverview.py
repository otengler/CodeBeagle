# -*- coding: utf-8 -*-
"""
Copyright (C) 2013 Oliver Tengler

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

from PyQt4.QtCore import * 
from PyQt4.QtGui import *
from Ui_MatchesOverview import Ui_MatchesOverview
import HighlightingRulesCache
import SourceHighlightingTextEdit
import AsynchronousTask
from FileTools import fopen
from AppConfig import appConfig
import RecyclingVerticalScrollArea
import unittest
import bisect
import re

# Accepts a list of touples each containing a start and end index. After calling the function
# consecutive touples which overlapped or adjoin are collapsed into one touple. This is done in place.
# ranges = [(1,3),(2,5),(7,2)]
# Result is [(1,5),(7,2)]
def collapseAdjoiningRanges(ranges):
    i=0
    while i+1 < len(ranges):
        r1 = ranges[i]
        r2 = ranges[i+1]
        if r1[1]+1>=r2[0]:
            rn = (r1[0],r2[1])
            del ranges[i]
            del ranges[i]
            ranges.insert(i,rn)
        else:
            i+= 1
            
class TestCollapseOverlappingRanges(unittest.TestCase):
    def test(self):
        ranges = []
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

class FixedSizeSourcePreview(SourceHighlightingTextEdit.SourceHighlightingTextEdit):
    def __init__(self, parent=None):
        super(FixedSizeSourcePreview, self).__init__(parent)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

class FixedSizeSourcePreviewItem (RecyclingVerticalScrollArea.ScrollAreaItem):
    def __init__(self, matchesOverview,  text,  name,  height):
        super (FixedSizeSourcePreviewItem,  self).__init__(height)
        self.matchesOverview = matchesOverview
        self.text = text
        self.name = name
        
    def generateItem (self, parent):
        return FixedSizeSourcePreview(parent)
        
    def configureItem(self, edit):
        rules = HighlightingRulesCache.rules().getRulesByFileName(self.name,  self.matchesOverview.sourceFont)
        edit.setFont(self.matchesOverview.sourceFont)
        edit.setTabStopWidth(self.matchesOverview.tabWidth*10)
        edit.highlighter.setHighlightingRules (rules,  self.text)
        edit.highlighter.setSearchData (self.matchesOverview.searchData)
        edit.setPlainText(self.text)
        
        # Forward the signal to MatchesOverview instance
        edit.selectionFinishedWithKeyboardModifier.connect (self.matchesOverview.selectionFinishedWithKeyboardModifier)
        
    def getType(self):
        return FixedSizeSourcePreview

class Line:
    def __init__(self, charPos, lineNumber):
        self.charPos = charPos
        self.lineNumber = lineNumber
        
    def __lt__ (left,  right):
        return left.charPos < right.charPos

# Detects quickly which character position corresponds to which line number.
# The first line numer is 1.
class LineMapping:
    def __init__(self,text):
        self.list = []
        self.numberMap = {1:0} # line 1 always starts at 0
        self.text = text
        
        reLineBreak = re.compile("\\n")
        cur = 0
        line = 1
        while True:
            result = reLineBreak.search(text, cur)
            if result:
                startPos, endPos = result.span()
                self.list.append(Line(startPos,line))
                self.numberMap[line+1] = endPos
                cur = endPos
                line = line + 1
            else:
                break

    def findLineNumber (self, charPos):
        if not self.list:
            return 0
        pos = bisect.bisect_left (self.list,  Line(charPos,0))
        if pos >= len(self.list):
            return self.list[-1].lineNumber+1
        return self.list[pos].lineNumber
        
    def getLine(self,  lineNumber):
        if 0 == lineNumber or lineNumber > len(self.numberMap):
            return ""
        startPos = self.numberMap[lineNumber]
        if lineNumber == len(self.numberMap):
            endPos = len(self.text)
        else:
            endPos = self.numberMap[lineNumber+1]-1
        return self.text [startPos:endPos]
        
    def lineCount(self):
        return len(self.numberMap)
        
class TestLineMapping(unittest.TestCase):
    def test(self):
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
    def __init__(self,  name):
        self.name = name
        self.matches = []
        
    def addMatches (self,  nLineNumberStart,  lines):
        self.matches.append((nLineNumberStart, lines))

# Returns a list of all matches in all files
# This read sall files and retrieves the matches with some lines surounding them
def extractMatches ( matches, searchData, linesOfContext):     
    results = []
    for name in matches:
        matchList = MatchesInFile(name)
        try:
            with fopen(name) as file:
                text = file.read()
        except:
            matchList.addMatches(0, ["Failed to open file"])
            self.matchesInFileFound.emit(matchList)
        else:
            lineIndex = LineMapping(text)
            ranges = []
            for startPos, length in searchData.matches(text):
                lineNumber = lineIndex.findLineNumber(startPos)
                startLine = lineNumber-linesOfContext
                if startLine < 1:
                    startLine = 1
                endLine = lineNumber+linesOfContext
                if endLine > lineIndex.lineCount():
                    endLine = lineIndex.lineCount()
                ranges.append((startLine, endLine))
            # Collapse overlapping ranges into one
            collapseAdjoiningRanges (ranges)
            for startLine, endLine in ranges:
                lines = []
                for i in range(startLine, endLine+1):
                    lines.append(lineIndex.getLine(i))
                matchList.addMatches(startLine, lines)
            results.append(matchList)
    return results

class MatchesOverview (QWidget):
    # Triggered if a selection was finished while holding a modifier key down
    selectionFinishedWithKeyboardModifier = pyqtSignal('QString',  int)
    
    def __init__ (self, parent):
        super(MatchesOverview, self).__init__(parent)
        self.ui = Ui_MatchesOverview()
        self.ui.setupUi(self)
        self.matches = None
        self.searchData = None
        self.resultHandled = True
        self.sourceFont = None
        self.lineHeight = 0
        self.tabWidth = 4
        self.linesOfContext = 2
        self.scrollItems = RecyclingVerticalScrollArea.SrollAreaItemList()
        self.matchIndexes = []
        
    def reloadConfig (self,  font):
        self.sourceFont = font
        metrics = QFontMetrics(self.sourceFont)
        self.lineHeight = metrics.height()
        
        linesOfContext = appConfig().previewLines
        if linesOfContext % 2:
            linesOfContext /= 2
        else:
            linesOfContext = (linesOfContext+1)/2
        if linesOfContext < 1:
            linesOfContext = 1
        self.linesOfContext = int(linesOfContext)
        
        config = appConfig().SourceViewer
        self.tabWidth = config.TabWidth
        
        # TODO: rebuild self.scrollItems if the font changed or tab width changed...
        
    def setSearchResult(self,  matches,  searchData):
        self.matches = matches
        self.searchData = searchData
        self.resultHandled = False
        
        if self.isVisible():
            self.__handleResult()
        
    def activate (self):
        if not self.resultHandled:
            self.__handleResult ()
            
    def scrollToFile (self, index):
        if index >= len(self.matchIndexes):
            return
        self.ui.scrollArea.scrollToNthItem(self.matchIndexes[index])
        
    def __handleResult(self):
        self.resultHandled = True
                
        self.scrollItems.clear()
        self.matchIndexes = []
        
        if self.matches:
            results = AsynchronousTask.execute (self, extractMatches,  self.matches,  self.searchData,  self.linesOfContext)
        
            for result in results:
                index = self.__addHeader(result.name)
                self.matchIndexes.append(index)
                for startLine, lines in result.matches:
                    self.__addLine("Lines %u - %u:" % (startLine, startLine+len(lines)-1))
                    self.__addText(result.name, lines)
                
        self.ui.scrollArea.setItems(self.scrollItems)
        
    def __addHeader(self, text):
        return self.__addLine(text,  True)
    
    def __addLine(self, text,  bIsBold = False):
        labelItem = RecyclingVerticalScrollArea.Labeltem(text,  bIsBold,  14)
        return self.scrollItems.addItem(labelItem)
        
    def __addText(self, name,  lines):
        text = "\n".join(lines)
        scrollBarHeight = 24
        height = len(lines)*self.lineHeight+11+scrollBarHeight
        editItem = FixedSizeSourcePreviewItem (self,  text,  name,  height)
        return self.scrollItems.addItem(editItem)
    
def main():    
    import sys
    app = QApplication(sys.argv) 
    w = MatchesOverview(None) 
    w.show() 
    sys.exit(app.exec_()) 

if __name__ == "__main__":
    unittest.main()
    #main()