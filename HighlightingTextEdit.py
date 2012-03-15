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

from PyQt4.QtCore import * 
from PyQt4.QtGui import *

class Highlighter:
    def __init__(self):
        pass
        
    # Return a list of touples with (charFormat,start,length)
    def highlightBlock (self, postion,  text):
        return []

class HighlightingTextEdit (QPlainTextEdit):
    def __init__ (self, parent):
        super(HighlightingTextEdit, self).__init__(parent)
        self.highlighter = None
        self.dynamicHighlight = None
        
    def setHighlighter (self, highlighter):
        self.highlighter = highlighter
        
    def setDynamicHighlight(self,  text):
        if self.dynamicHighlight != text:
            self.dynamicHighlight = text
            self.viewport().update()
        
    def paintEvent(self, event):
        firstVisibleBlock = self.firstVisibleBlock()
        self.colorizeVisibleBlocks(firstVisibleBlock)
        super(HighlightingTextEdit, self).paintEvent(event)
        
        if self.dynamicHighlight:
            painter = QPainter(self.viewport())
            metrics = painter.fontMetrics()
            for block, bound in self.visibleBlocks(firstVisibleBlock,  True):
                bound = QRect(bound.left(), bound.top(), bound.width(), bound.height())
                startIndex = block.text().find(self.dynamicHighlight)
                if startIndex != -1:
                    partBefore = block.text()[:startIndex]
                    rectBefore = metrics.boundingRect(bound, Qt.TextExpandTabs, partBefore,  self.tabStopWidth())
                    rectText = metrics.boundingRect(bound, Qt.TextExpandTabs,  self.dynamicHighlight, self.tabStopWidth())
                    rectResult = QRect(rectBefore.right()+4,  rectBefore.top()+1,  rectText.width()+2,  rectText.height()-2)
                    painter.setPen(Qt.darkGray)
                    painter.drawRect(rectResult)
    
    @pyqtSlot()
    def colorizeVisibleBlocks(self,  firstVisibleBlock):
        for block in self.visibleBlocks(firstVisibleBlock):
            # -1 means the block has not been highlighted yet
            if block.userState() == -1:
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


