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

from PyQt5.QtCore import Qt, QUrl, QMimeData, QPoint
from PyQt5.QtGui import QDrag, QMouseEvent
from PyQt5.QtWidgets import QListView, QApplication, QWidget
from typing import Optional

class PathDragListView (QListView):
    def __init__ (self, parent: QWidget) -> None:
        super().__init__(parent)
        self.startPos: Optional[QPoint] = None

    def mousePressEvent(self, event: Optional[QMouseEvent]) -> None:
        if event and event.button() == Qt.LeftButton:
            self.startPos = event.pos()
        super ().mousePressEvent(event)

    def mouseMoveEvent(self, event: Optional[QMouseEvent]) -> None:
        if self.startPos and event and event.buttons() and Qt.LeftButton:
            distance = (event.pos() - self.startPos).manhattanLength()
            if distance >= QApplication.startDragDistance():
                self.performDrag()
        super ().mouseMoveEvent(event)

    def performDrag(self) -> None:
        if model := self.model():
            paths = (model.data(index,  Qt.UserRole) for index in self.selectedIndexes())
            urls = [QUrl.fromLocalFile(path) for path in paths]
            mimeData = QMimeData()
            mimeData.setUrls (urls)
            drag = QDrag(self)
            drag.setMimeData(mimeData)
            drag.exec(Qt.CopyAction)