# -*- coding: utf-8 -*-
"""
Copyright (C) 2018 Oliver Tengler

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

from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QRect, QSize
from PyQt5.QtGui import QPainter, QPaintEvent, QTextBlock, QColor, QResizeEvent, QPixmap, QMouseEvent
from PyQt5.QtWidgets import QWidget, QPlainTextEdit
from typing import Optional, Iterator, Tuple

class LineNumberArea (QWidget):
    bookmarkChanged = pyqtSignal(int) # line where bookmark is set or removed

    padding = 24
    areaColor = QColor(235,235,235)
    textColor = QColor(130,130,130)

    def __init__(self, textEdit: QPlainTextEdit, firstLineNumber:int = 1, enableBookmarks = False) -> None:
        super().__init__(textEdit)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.textEdit: QPlainTextEdit = textEdit
        self.firstLineNumber = firstLineNumber

        self.areaColor = LineNumberArea.areaColor
        self.textColor = LineNumberArea.textColor

        self.textEdit.blockCountChanged.connect(self.adjustAreaWidth)
        self.textEdit.updateRequest.connect(self.scrollArea)
        self.adjustAreaWidth()

        self.enableBookmarks = enableBookmarks
        bookMarkPixmap = QPixmap("resources/bookmark.png")
        iconHeight = self.textEdit.fontMetrics().height() - 2
        factor = iconHeight/bookMarkPixmap.height()
        self.bookMarkPixmap = bookMarkPixmap.scaled(int(bookMarkPixmap.width() * factor), iconHeight, 
                                                    Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        self.bookmarkLines: set[int] = set()

    def setBookmarks(self, lines: Optional[set[int]]) -> None:
        if lines is None:
            lines = set()
        else:
            self.bookmarkLines = lines
        self.repaint()

    def close(self) -> bool:
        super().close()
        self.textEdit.setViewportMargins(0, 0, 0, 0)
        return True

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
        cr:QRect = self.textEdit.contentsRect()
        return QSize(self.areaWidth(), cr.height())

    def reactOnResize(self, e: QResizeEvent) -> None:
        cr:QRect = self.textEdit.contentsRect()
        self.setGeometry(QRect(cr.left(), cr.top(), self.areaWidth(), cr.height()))

    def areaWidth(self, newBlockCount: int = 0) -> int:
        if not newBlockCount:
            newBlockCount = self.textEdit.blockCount()
        newBlockCount = self.firstLineNumber + newBlockCount
        digits = len(f"{newBlockCount}")
        space:int = self.padding + self.textEdit.fontMetrics().horizontalAdvance("9") * digits
        return space

    def mouseReleaseEvent(self, event: Optional[QMouseEvent]) -> None:
        if not event or not self.enableBookmarks:
            return
        pos = event.pos()
        for number, rect in self.__visibleBlocks(self.rect()):
            if pos.y() > rect.top() and pos.y() < rect.bottom():
                self.bookmarkChanged.emit(number)
                break

    def paintEvent(self, event: Optional[QPaintEvent]) -> None:
        if not event:
            return
        painter = QPainter(self)
        painter.setFont(self.textEdit.font())
        painter.fillRect(event.rect(), self.areaColor)
        painter.setPen(self.textColor)
        
        for number, rect in self.__visibleBlocks(event.rect()):
            painter.drawText(rect.left(), rect.top(), rect.width()-self.padding//2, rect.height(), Qt.AlignmentFlag.AlignRight, str(number))
            if self.enableBookmarks and number in self.bookmarkLines:
                painter.drawPixmap(2, rect.top() + 3, self.bookMarkPixmap)

    def __visibleBlocks (self, updateRect: QRect) -> Iterator[Tuple[int, QRect]]:
        block: QTextBlock = self.textEdit.firstVisibleBlock()
        blockNumber: int = block.blockNumber()
        top = int(self.textEdit.blockBoundingGeometry(block).translated(self.textEdit.contentOffset()).top())
        bottom = top + int(self.textEdit.blockBoundingRect(block).height())

        while block.isValid() and top <= updateRect.bottom():
            if block.isVisible() and bottom >= updateRect.top():
                number = blockNumber+self.firstLineNumber
                yield number, QRect(0, top, self.width(), bottom-top)

            block = block.next()
            top = bottom
            bottom = top + int(self.textEdit.blockBoundingRect(block).height())
            blockNumber += 1
