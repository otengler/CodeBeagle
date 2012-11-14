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

import os
from PyQt4.QtCore import * 
from PyQt4.QtGui import *

# Parent must be the view (otherwise the focus drawing doesn't work)
class PathVisualizerDelegate (QStyledItemDelegate):
    def __init__ (self, parent):
        super (QStyledItemDelegate, self).__init__(parent)
        self.pathDarkGrayColor = QPen(QColor(50, 50, 50))
        self.pathGrayColor = QPen(QColor(150, 150, 150))
        self.fileColor = QPen(QColor(0, 0,  50))
        if parent:
            self.pathBoldFont = QFont (parent.font())
        else:
            self.pathBoldFont = QFont (QApplication.font())
        self.pathBoldFont.setBold (True)
        self.pathBoldFontMetrics = QFontMetrics(self.pathBoldFont)
        self.selectedPathColor = self.pathDarkGrayColor
        self.seletedFileColor = self.fileColor
        
    def paint (self,  painter, option,  index):
        if option.type != QStyleOption.SO_ViewItem:
            return
    
        # Always paint as active otherwise the selection of the current item(s) is very hard to see on Win 7
        option.state |= QStyle.State_Active
        
        QApplication.style().drawPrimitive(QStyle.PE_PanelItemViewItem, option, painter,  self.parent())
            
        bSelected = option.state & QStyle.State_Selected
            
        model = index.model()
        path, name = os.path.split(model.data(index,  Qt.DisplayRole))
        if not bSelected:
            fileColor = self.fileColor
            if index.row() > 0:
                indexAbove = model.index(index.row()-1, 0, QModelIndex())
                pathAbove,nameAbove  =  os.path.split(model.data (indexAbove, Qt.DisplayRole))
                if pathAbove == path:
                    pathColor = self.pathGrayColor
                else:
                    pathColor = self.pathDarkGrayColor
            else:
                pathColor = self.pathDarkGrayColor
        else:
            fileColor = self.seletedFileColor
            pathColor = self.selectedPathColor
            
        path += os.path.sep
            
        rect = QRect(option.rect)
        rect.setLeft (rect.left()+3)
        
        font = painter.font()
        painter.save()
        
        if pathColor == self.pathDarkGrayColor and index.row() > 0:
            painter.setPen(self.pathGrayColor)
            painter.drawLine(option.rect.left(),  option.rect.top(),  option.rect.right(),  option.rect.top())
        
        painter.setFont (self.pathBoldFont)
        painter.setPen(pathColor)
        bound = painter.drawText (rect, Qt.AlignVCenter, path)
        
        painter.setFont (font)
        painter.setPen(fileColor)
        rect.setLeft(bound.right())
        painter.drawText (rect, Qt.AlignVCenter,  name)
        
        painter.restore()
        
    # Computes the size of the longest string in data. This is just an assumption because you cannot deduce the length from 
    # the number of letters. But most of the time this is true and much faster than computing the bounding rect for 20000
    # matches...
    def computeSizeHint (self, data,  cutLeft):
        maxLen = 0
        longestMatch = None
        for match in data:
            if cutLeft:
                match = match[cutLeft:]
            currLen = len(match)
            if currLen > maxLen:
                maxLen = currLen
                longestMatch = match
        if not longestMatch:
            return QSize(0, 0)
        rect = self.pathBoldFontMetrics.boundingRect(longestMatch)
        return QSize(rect.width(),  rect.height()+4)

