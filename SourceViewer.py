# -*- coding: utf-8 -*-
"""
Copyright (C) 2011 Oliver Tengler

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
from Ui_SourceViewer import Ui_SourceViewer 
from FileTools import fopen
from AppConfig import appConfig
import HighlighterConfiguration  
import bisect
import os

class SourceViewer (QWidget):
    # Triggered if a selection was finished while holding a modifier key down
    selectionFinishedWithKeyboardModifier = pyqtSignal('QString',  int)
    noPreviousMatch = pyqtSignal()
    noNextMatch = pyqtSignal()
    directoryDropped = pyqtSignal('QString')
    
    def __init__ (self, parent):
        super (SourceViewer, self).__init__(parent)
        self.ui = Ui_SourceViewer()
        self.ui.setupUi(self)
        self.ui.frameSearch.hide()
        self.highlighter = SyntaxHighlighter ()
        self.ui.textEdit.setHighlighter(self.highlighter)
        
        # Use the same color for active and inactive selections of text. The contrast of inactive selections is too low.
        palette = QPalette()
        brush = palette.brush (QPalette.Active,  QPalette.Highlight)
        palette.setBrush (QPalette.Inactive,  QPalette.Highlight,  brush)
        self.ui.textEdit.setPalette(palette)
        
        self.sourceFont = None
        self.searchData = None
        self.__reset()
        self.__processConfig()
        
        self.actionReloadFile = QAction(self, shortcut=Qt.Key_F5, triggered= self.reloadFile)
        self.addAction(self.actionReloadFile)
        
    def reloadConfig (self):
        self.__processConfig()
        
    def __processConfig (self):
        config = appConfig().SourceViewer
        self.bMatchOverFiles = appConfig().matchOverFiles
        
        if not self.sourceFont:
            self.sourceFont = QFont()
        
        # Apply font and tab changes (if any)
        if self.sourceFont.family().lower() != config.FontFamily.lower() or self.sourceFont.pointSize() != config.FontSize:
            self.sourceFont.setFamily(config.FontFamily)
            self.sourceFont.setPointSize(config.FontSize)
            self.ui.textEdit.setFont(self.sourceFont)
        
        if self.ui.textEdit.tabStopWidth() != config.TabWidth*10:
            self.ui.textEdit.setTabStopWidth(config.TabWidth*10)
        
    def __reset (self):
        self.matches = [] # touples with position and length
        self.curMatch = -1
        self.ui.labelCursor.setText("")
        self.ui.labelFile.setText(self.trUtf8("No document loaded"))
        self.ui.textEdit.setPlainText("")
        self.__resetTextCursor()
        self.__setInfoLabel()
        self.ui.textEdit.setDynamicHighlight(None)
    
    def setSearchData (self,  searchData):
        self.__reset()
        self.searchData = searchData
        self.highlighter.setSearchData (searchData)
        
    def showFile (self,  name):
        self.__reset()
        self.ui.labelFile.setText(name)
        
        try:
            with fopen(name) as file:
                text = file.read()
        except:
            text = self.trUtf8("Failed to open file")
        
        self.highlighter.setRulesByFileName(name,  text,  self.sourceFont)
        self.ui.textEdit.setPlainText(text)
            
        if self.searchData:
            self.matches = [match for match in self.searchData.matches (text)]
            self.nextMatch ()
            
    def currentFile(self):
        return self.ui.labelFile.text()
        
    @pyqtSlot()
    def reloadFile(self):
        self.showFile(self.currentFile())
        
    @pyqtSlot()
    def nextMatch (self):
        if self.curMatch < len(self.matches)-1:
            self.curMatch += 1
            self.__scrollToMatch (self.curMatch,)
            self.__setInfoLabel ()
        else:
            if self.bMatchOverFiles:
                self.noNextMatch.emit()
        
    @pyqtSlot()
    def previousMatch (self):
        if self.curMatch > 0:
            self.curMatch -= 1
            self.__scrollToMatch (self.curMatch,)
            self.__setInfoLabel ()
        else:
            if self.bMatchOverFiles:
                self.noPreviousMatch.emit()
            
    @pyqtSlot()
    def nextSearch(self):
        search = self.ui.editSearch.text()
        if search:
            self.ui.textEdit.find(search)
            
    @pyqtSlot()
    def previousSearch(self):
        search = self.ui.editSearch.text()
        if search:
            self.ui.textEdit.find(search,  QTextDocument.FindBackward)

    @pyqtSlot()
    def updateCurrentLine (self):
        line = self.ui.textEdit.textCursor().blockNumber()+1
        self.ui.labelCursor.setText(self.trUtf8("Line") + " %u" % (line, ))
    
    @pyqtSlot()    
    def highlightSelection(self):
        if QApplication.mouseButtons() != Qt.NoButton: # only react on a finished selection. otherwise we update the highlight too often
            return
        text = self.ui.textEdit.textCursor().selectedText().strip()
        if not text or len(text)>64:
            return
        
        # Allow other components to react on selection of tokens with keyboard modifiers
        modifiers = int(QApplication.keyboardModifiers())
        if modifiers & int(Qt.ShiftModifier)==0:
            if modifiers != Qt.NoModifier:
                self.selectionFinishedWithKeyboardModifier.emit(text, modifiers)
            else:
                self.ui.textEdit.setDynamicHighlight(text)
        
    @pyqtSlot()
    def showSearchFrame(self):
        self.ui.frameSearch.show()
        self.ui.editSearch.setFocus(Qt.MouseFocusReason)
        text = self.ui.textEdit.textCursor().selectedText().strip()
        if text:
            self.ui.editSearch.setText(text)
        self.ui.editSearch.selectAll()
        
    def __resetTextCursor (self):
        cursor = self.ui.textEdit.textCursor()
        cursor.setPosition(0)
        self.ui.textEdit.setTextCursor(cursor)
        extra = QTextEdit.ExtraSelection ()
        extra.cursor = cursor
        self.ui.textEdit.setExtraSelections((extra,))
        
    def __setInfoLabel (self):
        str = ""
        if len(self.matches) and self.curMatch != -1:
            str = str + "%u/%u " % (self.curMatch+1, len(self.matches))
        self.ui.labelInfo.setText (str)
        
    def __scrollToMatch (self, num):
        if num < 0 or num >= len(self.matches):
            return
        index, length = self.matches[num]
        
        scrollDir = index - self.ui.textEdit.textCursor().position() # Determine if we need to scroll down or up

        extras = []
        extra1 = QTextEdit.ExtraSelection ()
        extra1.cursor = self.ui.textEdit.textCursor()
        extra1.cursor.setPosition (index)
        extra1.format.setProperty (QTextFormat.FullWidthSelection,  True)
        extra1.format.setBackground (QColor(170,255,127))
        extras.append(extra1)
       
        extra2 = QTextEdit.ExtraSelection ()
        extra2.cursor = self.ui.textEdit.textCursor()
        extra2.cursor.setPosition (index)
        extra2.cursor.setPosition (index+length,  QTextCursor.KeepAnchor)
        extra2.format.setBackground (Qt.yellow)
        extras.append(extra2)
        
        self.ui.textEdit.setExtraSelections (extras)
        if scrollDir > 0:
            extra2.cursor.movePosition(QTextCursor.Down, QTextCursor.MoveAnchor,  5)
        elif scrollDir < 0:
            extra2.cursor.movePosition(QTextCursor.Up, QTextCursor.MoveAnchor,  5)
        self.ui.textEdit.setTextCursor (extra2.cursor) # otherwise 'ensureCursorVisible' doesn't work
        self.ui.textEdit.ensureCursorVisible ()
        
        matchCursor = self.ui.textEdit.textCursor()
        matchCursor.setPosition(index)
        self.ui.textEdit.setTextCursor(matchCursor) # jump back to match to make sure the line number of the match is correct
        
    def dragEnterEvent(self, event):
        # check if the data contains urls
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        
    def dropEvent(self, event):
        # check if the data contains urls
        if event.mimeData().hasUrls():
            name = event.mimeData().urls()[0].toLocalFile()
            if os.path.isfile(name):
                self.showFile(name)
            elif os.path.isdir(name):
                self.directoryDropped.emit(name)
       
class HighlightingRules:
    def __init__(self,  font):
        self.rules = []
        self.lineComment = None
        self.multiCommentStart = None
        self.multiCommentStop = None
        self.commentFormat = None
        self.font = font
        
    # Adds a list of comma seperated keywords
    def addKeywords (self,  keywords,  fontWeight,  foreground):
        keywords = keywords.strip()
        kwList = keywords.split(",")
        # We build a single expression which matches all keywords
        expr = "|".join(("\\b" + kw + "\\b" for kw in kwList))
        self.addRule (expr,  fontWeight,  foreground)
        
    # Adds comment rules. Each parameter is a regular expression  string. The multi line parameter are optional and can be empty.
    def addCommentRule (self, singleLine,  multiLineStart,  multiLineEnd,  fontWeight,  foreground):
        self.commentFormat = self.__createFormat(fontWeight,  foreground)
        self.lineComment = QRegExp(singleLine)
        if multiLineStart and multiLineEnd:
            self.multiCommentStart = QRegExp(multiLineStart)
            self.multiCommentStop = QRegExp(multiLineEnd)
        
    # Adds an arbitrary highlighting rule 
    def addRule (self, expr,  fontWeight,  foreground):
        format = self.__createFormat(fontWeight,  foreground)
        self.__addRule (expr,  format)
        
    def __addRule (self, expr,  format):
        self.rules.append((QRegExp(expr),  format))
        
    def __createFormat (self,  fontWeight, foreground):
        format = QTextCharFormat()
        format.setFont(self.font)
        format.setFontWeight(fontWeight)
        format.setForeground(foreground)
        return format
       
def rulesFromFile (rulesFile,  font):
    rules = HighlightingRules(font)
   
    localsDict = { "Light" : QFont.Light,  
                          "Normal" : QFont.Normal,  
                          "DemiBold" : QFont.DemiBold,  
                          "Bold" : QFont.Bold,  
                          "Black" : QFont.Black,  
                          
                          "white" : Qt.white, 
                          "black" : Qt.black, 
                          "red" : Qt.red, 
                          "darkRed" : Qt.darkRed, 
                          "green" : Qt.green, 
                          "darkGreen" : Qt.darkGreen, 
                          "blue" : Qt.blue, 
                          "darkBlue" : Qt.darkBlue, 
                          "cyan" : Qt.cyan, 
                          "darkCyan" : Qt.darkCyan, 
                          "magenta" : Qt.magenta, 
                          "darkMagenta" : Qt.darkMagenta, 
                          "yellow" : Qt.yellow, 
                          "darkYellow" : Qt.darkYellow, 
                          "gray" : Qt.gray,
                          "darkGray" : Qt.darkGray,
                          "lightGray" : Qt.lightGray, 
                    
                          "addKeywords" : rules.addKeywords, 
                          "addCommentRule" : rules.addCommentRule, 
                          "addRule" : rules.addRule}

    with open(os.path.join("config", rulesFile)) as script: 
        code = compile(script.read(), rulesFile, 'exec')
    exec(code,  globals(),  localsDict)
        
    return rules

class SyntaxHighlighter:
    def __init__(self):
        self.highlighterConfig = HighlighterConfiguration.highlighter(appConfig().SourceViewer)
        
        # A dict mapping a file extension to a HighlightingRules object
        self.highlightingRulesCache = {}
        self.extensionsToRulesFile = {}
        
        # The current rules
        self.highlightingRules = None
        
        self.searchStringFormat = QTextCharFormat()
        self.searchStringFormat.setFontWeight(QFont.Bold)
        self.searchStringFormat.setBackground(Qt.yellow)
        self.searchStringFormat.setForeground(Qt.black)
        
        self.comments = []
        self.searchData = None
        
    # Choose a set of highlighting rules depending on the file extension
    def setRulesByFileName(self,  name,  text,  font):
        ext = os.path.splitext(name)[1].lower()
        if ext.startswith("."):
            ext = ext[1:]
            
        if ext in self.extensionsToRulesFile:
            rulesFile = self.extensionsToRulesFile[ext]
        else:
            rulesFile = self.highlighterConfig.lookup(ext)
            self.extensionsToRulesFile[ext] = rulesFile
            
        if rulesFile in self.highlightingRulesCache:
            self.highlightingRules = self.highlightingRulesCache[rulesFile]
        else:
            self.highlightingRules = rulesFromFile(rulesFile,  font)
            self.highlightingRulesCache[rulesFile] = self.highlightingRules
            
        self.__setText(text)
        
    class CommentRange:
        def __init__(self, index, length=0):
            self.index = index
            self.length = length
            
        def __lt__ (left,  right):
            return left.index < right.index
        
    def __textLineBefore(self,  text,  index):
        pos = index
        while pos > 0:
            pos -= 1
            if text[pos] == "\n":
                return text[pos+1:index]
        return text[0:index]
        
    # Find all multiline comments in the document and store them as CommentRange objects in self.comments
    def __setText(self,  text):
        comments = []
        if self.highlightingRules:
            if self.highlightingRules.multiCommentStart and self.highlightingRules.multiCommentStop:
                regStart = self.highlightingRules.multiCommentStart
                regEnd = self.highlightingRules.multiCommentStop
                startIndex = regStart.indexIn(text)
                while startIndex>=0: 
                    matchedLenStart = regStart.matchedLength()
                    line = self.__textLineBefore (text, startIndex+matchedLenStart) # +matchedLenStart too catch things like "//*" 
                    # Check if the multi line comment is commented out
                    if self.highlightingRules.lineComment.indexIn (line) == -1:
                        endIndex = regEnd.indexIn(text, startIndex+matchedLenStart)
                        if endIndex == -1: # comment opened but not closed
                            comments.append (self.CommentRange(startIndex,  len(text)-startIndex))
                            break
                        matchedLenEnd = regEnd.matchedLength()
                        comments.append (self.CommentRange(startIndex,  endIndex+matchedLenEnd-startIndex))
                    else:
                        endIndex = startIndex
                        matchedLenEnd = matchedLenStart
                    startIndex = regStart.indexIn(text,  endIndex+matchedLenEnd)
        self.comments = comments
        
    def setSearchData (self, searchData):
        self.searchData = searchData

    def highlightBlock(self, position, text):
        formats = []
        if not self.highlightingRules:
            return formats
            
        # Single line highlighting rules
        for expression, format in self.highlightingRules.rules:
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                formats.append((format, index, length))
                index = expression.indexIn(text, index + length)
                    
        # Colorize multiline comments
        pos = bisect.bisect_right (self.comments,  self.CommentRange(position))
        if pos > 0:
            pos -= 1
            while pos < len(self.comments):
                comment = self.comments[pos]
                # Comment starts before end of line
                if comment.index < position+len(text): 
                    formats.append((self.highlightingRules.commentFormat,  comment.index-position,  comment.length))
                else:
                    break
                pos += 1
        
        # Single line comments
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
    
def main():    
    import sys
    app = QApplication(sys.argv) 
    w = SourceViewer(None) 
    w.show() 
    #w.showFile(r"D:\C++\qt-everywhere-opensource-src-4.7.3\src\svg\qsvghandler.cpp")
    w.showFile(r"D:\test.cpp")
    sys.exit(app.exec_()) 

if __name__ == "__main__":
    main()
    


