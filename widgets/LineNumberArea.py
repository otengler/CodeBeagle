# -*- coding: utf-8 -*-
"""
Copyright (C) 2018 Oliver Tengler

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

from PyQt5.QtCore import Qt, pyqtSlot, QRect, QSize
from PyQt5.QtGui import QPainter, QPaintEvent, QTextBlock, QColor, QResizeEvent
from PyQt5.QtWidgets import QWidget, QPlainTextEdit

class LineNumberArea (QWidget):
    padding = 20

    def __init__(self, textEdit: QPlainTextEdit, firstLineNumber:int = 1) -> None:
        super().__init__(textEdit)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.textEdit: QPlainTextEdit = textEdit
        self.firstLineNumber = firstLineNumber

        self.areaColor = QColor(235,235,235)
        self.textColor = QColor(130,130,130)

        self.textEdit.blockCountChanged.connect(self.adjustAreaWidth)
        self.textEdit.updateRequest.connect(self.scrollArea)
        self.adjustAreaWidth()

    def close(self) -> None:
        super().close()
        self.textEdit.setViewportMargins(0, 0, 0, 0)

    @pyqtSlot(int)
    def adjustAreaWidth(self, newBlockCount: int = 0) -> None:
        self.textEdit.setViewportMargins(self.areaWidth(newBlockCount), 0, 0, 0)

    @pyqtSlot(QRect, int)
    def scrollArea(self, rect: QRect, dy: int) -> None:
        if dy:
            self.scroll(0, dy)
        else:
            self.update(0, rect.y(), self.width(), rect.height())

    def sizeHint(self) -> QSize:
        return QSize(self.areaWidth(), 0)

    def reactOnResize(self, e: QResizeEvent) -> None:
        cr:QRect = self.textEdit.contentsRect()
        self.setGeometry(QRect(cr.left(), cr.top(), self.areaWidth(), cr.height()))

    def areaWidth(self, newBlockCount: int = 0) -> int:
        if not newBlockCount:
            newBlockCount = self.textEdit.blockCount()
        digits = len(f"{newBlockCount}")
        space:int = self.padding + self.textEdit.fontMetrics().horizontalAdvance("9") * digits
        return space

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setFont(self.textEdit.font())
        painter.fillRect(event.rect(), self.areaColor)

        block: QTextBlock = self.textEdit.firstVisibleBlock()
        blockNumber: int = block.blockNumber()
        top = int(self.textEdit.blockBoundingGeometry(block).translated(self.textEdit.contentOffset()).top())
        bottom = top + int(self.textEdit.blockBoundingRect(block).height())

        painter.setPen(self.textColor)
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = f"{blockNumber+self.firstLineNumber}"
                painter.drawText(0, top, self.width()-self.padding//2, self.textEdit.fontMetrics().height(), Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + int(self.textEdit.blockBoundingRect(block).height())
            blockNumber += 1