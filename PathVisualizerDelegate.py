# -*- coding: utf-8 -*-
"""
Copyright (C) 2011 Oliver Tengler

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

import os
from typing import List, Optional
from PyQt5.QtCore import Qt, QRect, QSize, QModelIndex
from PyQt5.QtGui import QFont, QPen, QColor, QFontMetrics, QPainter
from PyQt5.QtWidgets import QStyledItemDelegate, QApplication, QStyleOption, QStyle, QWidget, QStyleOptionViewItem

class PathVisualizerDelegate (QStyledItemDelegate):
    newPathColor = QColor(50, 50, 50)
    samePathColor = QColor(150, 150, 150)
    fileColor = QColor(0, 0, 50)
    selectedPathColor = QColor(50, 50, 50)
    selectedFileColor = QColor(0, 0, 50)
    selectionBackground = QColor(205, 232, 255)

    """Parent must be the view (otherwise the focus drawing doesn't work)"""
    def __init__ (self, parent: QWidget) -> None:
        super().__init__(parent)
        self.newPathColor = QPen(PathVisualizerDelegate.newPathColor)
        self.samePathColor = QPen(PathVisualizerDelegate.samePathColor)
        self.fileColor = QPen(PathVisualizerDelegate.fileColor)
        self.selectedPathColor = QPen(PathVisualizerDelegate.selectedPathColor)
        self.seletedFileColor = QPen(PathVisualizerDelegate.selectedFileColor)
        self.selectionBackground = QColor(PathVisualizerDelegate.selectionBackground)
        if parent:
            self.pathBoldFont = QFont (parent.font())
        else:
            self.pathBoldFont = QFont (QApplication.font())
        self.pathBoldFont.setBold (True)
        self.pathBoldFontMetrics = QFontMetrics(self.pathBoldFont)

    def paint (self, painter: Optional[QPainter], option: QStyleOptionViewItem, index: QModelIndex) -> None:
        if not painter or option.type != QStyleOption.SO_ViewItem:
            return

        model = index.model()
        if not model:
            return

        bSelected = option.state & QStyle.State.State_Selected

        rect = QRect(option.rect)
        if bSelected:
            painter.fillRect(rect,self.selectionBackground)

        rect.setLeft (rect.left()+3)

        painter.save()

        path, name = os.path.split(model.data(index,  Qt.ItemDataRole.DisplayRole))
        if not bSelected:
            fileColor = self.fileColor
            if index.row() > 0:
                indexAbove = model.index(index.row()-1, 0, QModelIndex())
                pathAbove,_ = os.path.split(model.data (indexAbove, Qt.ItemDataRole.DisplayRole))
                if pathAbove == path:
                    pathColor = self.samePathColor
                else:
                    pathColor = self.newPathColor
                    painter.setPen(self.samePathColor)
                    painter.drawLine(option.rect.left(),  option.rect.top(),  option.rect.right(),  option.rect.top())

            else:
                pathColor = self.newPathColor
        else:
            fileColor = self.seletedFileColor
            pathColor = self.selectedPathColor

        path += os.path.sep

        font = painter.font()
        painter.setFont(self.pathBoldFont)
        painter.setPen(pathColor)
        bound = painter.drawText (rect, Qt.Alignment.AlignVCenter, path)

        painter.setFont (font)
        painter.setPen(fileColor)
        rect.setLeft(bound.right())
        painter.drawText (rect, Qt.Alignment.AlignVCenter,  name)

        painter.restore()

    def computeSizeHint (self, data: List[str], cutLeft: int) -> QSize:
        """
        Computes the size of the longest string in data. This is just an assumption because you cannot deduce the length from
        the number of letters. But most of the time this is true and much faster than computing the bounding rect for 20000
        matches...
        """
        maxLen = 0
        longestMatch = None
        for match in data:
            currLen = len(match)
            if cutLeft:
                currLen -= cutLeft
            if currLen > maxLen:
                maxLen = currLen
                longestMatch = match
        if not longestMatch:
            return QSize(0, 0)
        rect = self.pathBoldFontMetrics.boundingRect(longestMatch)
        return QSize(rect.width(), rect.height()+4)
