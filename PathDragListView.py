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

from PyQt5.QtCore import Qt, QUrl, QMimeData
from PyQt5.QtGui import QDrag, QMouseEvent
from PyQt5.QtWidgets import QListView, QApplication, QWidget

class PathDragListView (QListView):
    def __init__ (self, parent: QWidget) -> None:
        super().__init__(parent)
        self.startPos = None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.startPos = event.pos()
        super ().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.startPos and event.buttons() and Qt.LeftButton:
            distance = (event.pos() - self.startPos).manhattanLength()
            if distance >= QApplication.startDragDistance():
                self.performDrag()
        super ().mouseMoveEvent(event)

    def performDrag(self) -> None:
        if self.model():
            paths = (self.model().data(index,  Qt.UserRole) for index in self.selectedIndexes())
            urls = [QUrl.fromLocalFile(path) for path in paths]
            mimeData = QMimeData()
            mimeData.setUrls (urls)
            drag = QDrag(self)
            drag.setMimeData(mimeData)
            drag.exec(Qt.CopyAction)
