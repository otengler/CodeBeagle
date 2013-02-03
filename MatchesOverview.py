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
import HighlightingTextEdit
import AsynchronousTask
from FileTools import fopen
from AppConfig import appConfig
import unittest
import bisect
import re

class FixedSizeSourcePreview(HighlightingTextEdit.HighlightingTextEdit):
    def __init__(self, width, lineCount, lineHeight,  parent=None):
        super(FixedSizeSourcePreview, self).__init__(parent)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.lineHeight = lineHeight
        scrollBarHeight = self.verticalScrollBar().height()
        self.setFixedSize(width, lineCount*lineHeight+11+scrollBarHeight) # without adding at least 11 pixels a vertical scrollbar is needed

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
        
        #                               0000000000011111111111
        #                               012345 67890 12345 678
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

class SearchResultHandler(QObject):
    matchesInFileFound = pyqtSignal(MatchesInFile)
    
    def __call__(self,  matches,  searchData):        
        # Read all files and retrieve all matches with the suurounding lines from them
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
                for startPos, length in searchData.matches(text):
                    lineNumber = lineIndex.findLineNumber(startPos)
                    startLine = lineNumber-2
                    if startLine < 1:
                        startLine = 1
                    endLine = lineNumber+2
                    if endLine > lineIndex.lineCount():
                        endLine = lineIndex.lineCount()
                    lines = []
                    for i in range(startLine, endLine+1):
                        lines.append(lineIndex.getLine(i))
                    matchList.addMatches(startLine, lines)
                self.matchesInFileFound.emit(matchList)

class MatchesOverview (QWidget):
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
        self.textEdits = []
        
    def reloadConfig (self,  font):
        self.sourceFont = font
        metrics = QFontMetrics(self.sourceFont)
        self.lineHeight = metrics.height()
        
        config = appConfig().SourceViewer
        self.tabWidth = config.TabWidth
        
        for textEdit in self.textEdits:
            textEdit.setFont(self.sourceFont)
            if textEdit.tabStopWidth() != self.tabWidth*10:
                textEdit.setTabStopWidth(self.tabWidth*10)
                
    def resizeEvent(self, event):
        super(MatchesOverview, self).resizeEvent(event)
        if event:
            for textEdit in self.textEdits:
                textEdit.setFixedWidth(event.size().width()-self.__getScrollViewWidthMargin())
                
    def __getScrollViewWidthMargin (self):
        margins = self.ui.scrollArea.widget().layout().contentsMargins ()
        # Again not so nice. Without adding 7 pixels the text edit is too close to the scrollbar
        width = margins.left()+margins.right()+7+self.ui.scrollArea.verticalScrollBar().width()
        return width
        
    def setSearchResult(self,  matches,  searchData):
        self.matches = matches
        self.searchData = searchData
        self.resultHandled = False
        
        if self.isVisible():
            self.__handleResult()
        
    def activate (self):
        if not self.resultHandled:
            self.resultHandled = True
            self.__handleResult ()
        
    def __handleResult(self):
        # Clear current results
        self.setUpdatesEnabled(False)
        self.textEdits = []
        layout = self.ui.scrollArea.widget().layout()
        while True:
            child = layout.takeAt(0)
            if child:
                del child
            else:
                break
        self.setUpdatesEnabled(True)
                
        if not self.matches:
            return
            
        searchHandler = SearchResultHandler()
        searchHandler.matchesInFileFound.connect(self.onMatchesInFileFound)
        self.setUpdatesEnabled(False)
        AsynchronousTask.execute (self, searchHandler,  self.matches,  self.searchData)
        self.setUpdatesEnabled(True)
        
        # Finally add a spacer to move the elements up
        spacerItem = QSpacerItem(40, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.ui.scrollArea.widget().layout().addItem(spacerItem)
        
    @pyqtSlot(SearchResultHandler)
    def onMatchesInFileFound(self,  matchesInFile):
        self.__addHeader(matchesInFile.name)
        for startLine, lines in matchesInFile.matches:
            self.__addLine("Lines %u - %u:" % (startLine, startLine+len(lines)-1))
            self.__addText(matchesInFile.name, lines)
    
    def __addHeader(self, text):
        self.__addLine(text,  True)
    
    def __addLine(self, text,  bIsBold = False):
        if bIsBold:
            str =  "<b>"
            str +=  text
            str +=  "</b>"
        else:
            str = text
        label = QLabel(str)
        self.ui.scrollArea.widget().layout().addWidget(label)
        
    def __addText(self, name,  lines):
        text = "\n".join(lines)
        rules = HighlightingRulesCache.rules().getRulesByFileName(name,  self.sourceFont)
        textEdit = FixedSizeSourcePreview(self.width()-self.__getScrollViewWidthMargin(), len(lines), self.lineHeight)
        textEdit.highlighter.setSearchData (self.searchData)
        textEdit.setFont(self.sourceFont)
        textEdit.highlighter.setHighlightingRules (rules,  text)
        textEdit.setPlainText(text)
        self.textEdits.append(textEdit)
        self.ui.scrollArea.widget().layout().addWidget(textEdit)
    
def main():    
    import sys
    app = QApplication(sys.argv) 
    w = MatchesOverview(None) 
    w.show() 
    sys.exit(app.exec_()) 

if __name__ == "__main__":
    unittest.main()
    main()
