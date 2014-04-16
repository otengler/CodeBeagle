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

import bisect
from PyQt4.QtCore import * 
from PyQt4.QtGui import *
        
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
        
    # Needed to change the font after the HighlightingRules object has been created
    def setFont (self,  font):
        for rule in self.rules:
            rule[1].setFont(font)
        self.commentFormat.setFont(font)
        
    def __addRule (self, expr,  format):
        self.rules.append((QRegExp(expr),  format))
        
    def __createFormat (self,  fontWeight, foreground):
        format = QTextCharFormat()
        format.setFont(self.font)
        format.setFontWeight(fontWeight)
        format.setForeground(foreground)
        return format
        
class SyntaxHighlighter:
    def __init__(self):
        # The current rules
        self.highlightingRules = None
        
        self.searchStringFormat = QTextCharFormat()
        self.searchStringFormat.setBackground(Qt.yellow)
        self.searchStringFormat.setForeground(Qt.black)
        
        self.comments = []
        self.searchData = None
        
    def setFont (self,  font):
        if self.highlightingRules:
            self.highlightingRules.setFont (font)
        
    def setHighlightingRules (self,  rules,  text):
        self.highlightingRules = rules
        self.searchStringFormat.setFont(rules.font)
        self.searchStringFormat.setFontWeight(QFont.Bold)
        # Text is needed to compute the syntax highlighting for multiline comments
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
        
    # searchData must support the function 'matches' which yields the tuple (start, length) for each match
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
    
    def __init__ (self, parent):
        super(HighlightingTextEdit, self).__init__(parent)
        self.highlighter = SyntaxHighlighter()
        self.dynamicHighlight = None
        self.setUndoRedoEnabled(False)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setReadOnly(True)
        self.setTextInteractionFlags(Qt.TextSelectableByKeyboard|Qt.TextSelectableByMouse)
        
    def setPlainText(self,  text):
        super(HighlightingTextEdit, self).setPlainText(text)
        # For whatever reasons some lines are not highlighted properly without another 'update'
        QTimer.singleShot (10, self.viewport().update)
        
    def setDynamicHighlight(self,  text):
        if self.dynamicHighlight != text:
            self.dynamicHighlight = text
            self.viewport().update()
            
    def setFont(self,  font):
        super(HighlightingTextEdit, self).setFont (font)
        self.viewport().setFont(font)
        self.highlighter.setFont(font)
 
    def paintEvent(self, event):
        firstVisibleBlock = self.firstVisibleBlock()
        bColorizedBlocks = self.colorizeVisibleBlocks(firstVisibleBlock)
        
        super(HighlightingTextEdit, self).paintEvent(event)
        
        if self.dynamicHighlight:
            painter = QPainter(self.viewport())
            metrics = painter.fontMetrics()
            for block, bound in self.visibleBlocks(firstVisibleBlock,  True):
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
    
    def colorizeVisibleBlocks(self,  firstVisibleBlock):
        bColorizedBlocks = False
        for block in self.visibleBlocks(firstVisibleBlock):
            # -1 means the block has not been highlighted yet
            if block.userState() == -1:
                bColorizedBlocks = True
                blockLength = len(block.text())
                formats = self.highlighter.highlightBlock(block.position(), block.text())
                addFormats = []
                for (format, start, length) in formats:
                    formatRange = QTextLayout.FormatRange ()
                    formatRange.format = format
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
            
    def visibleBlocks (self,  firstVisibleBlock,  bIncludeBound=False):
        size = self.viewport().size()
        block = firstVisibleBlock
        while block.isValid():
            bound = self.blockBoundingGeometry(block).translated(self.contentOffset())
            if bound.top() > size.height():
                break
            if bIncludeBound:
                yield block, bound
            else:
                yield block
            block = block.next()


