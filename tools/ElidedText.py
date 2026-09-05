# -*- coding: utf-8 -*-
"""
Copyright (C) 2026 Oliver Tengler

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

from typing import List
from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import QPainter, QFontMetrics, QTextLayout, QTextLine

def wrap_and_elide(text: str, painter: QPainter, rect: QRect, centerVertically: bool = True) -> None:
    """
    Draw elided text that is word broken inside a rect. Optionally verically aligned.
    """
    if not text or not rect or rect.width() <= 0 or rect.height() <= 0:
        return

    font = painter.font()
    fm = QFontMetrics(font)
    line_height = fm.lineSpacing()
    max_lines = rect.height() // line_height

    layout = QTextLayout(text, font)
    layout.beginLayout()

    lines: List[QTextLine] = []
    while True:
        line = layout.createLine()
        if not line.isValid():
            break
        line.setLineWidth(rect.width())
        line.setPosition(QPoint(0, len(lines) * line_height))
        lines.append(line)

    layout.endLayout()

    total_height = min(len(lines), max_lines) * fm.lineSpacing()
    y = rect.top() 
    if centerVertically:
        y += (rect.height() - total_height) // 2

    if len(lines) <= max_lines:
        # This branch is taken if the text fits inside max_lines. No eliding needed.
        topLeft = QPoint(rect.left(), y)
        layout.draw(painter, topLeft)
        return

    # Draw line by line and elide the last line
    for i, line in enumerate(lines[:max_lines]):
        line_text = text[
            line.textStart():
            line.textStart() + line.textLength()
        ]
        if i == max_lines - 1:
            line_text = fm.elidedText(line_text, Qt.TextElideMode.ElideRight, rect.width())

        yt = y + i * line_height
        rectL = QRect(rect.left(), yt, rect.width(), yt + line_height)
        painter.drawText(rectL, line_text)