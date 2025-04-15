# -*- coding: utf-8 -*-
"""
Copyright (C) 2020 Oliver Tengler

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

from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt5.QtGui import QMovie
from typing import Optional

class AnimatedProgressWidget(QWidget):
    """
    This widget attempts to look like a flat QPushButton. It shows a spinning gear icon to indicate
    work in progress.
    """
    def __init__(self, parent: QWidget, text: Optional[str] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(4)
        labelAnimation = QLabel(self)
        self.movie = QMovie("resources/Update.gif")
        self.movie.setScaledSize(QSize(20, 20))
        labelAnimation.setMovie(self.movie)
        self.labelText = QLabel(self)
        if text:
            self.labelText.setText(text)
        layout.addWidget (labelAnimation)
        layout.addWidget(self.labelText)

    def start(self) -> None:
        self.movie.start()

    def stop(self) -> None:
        self.movie.stop()