# -*- coding: utf-8 -*-
"""
Copyright (C) 2013 Oliver Tengler

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

from PyQt5.QtGui import QFocusEvent
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QWidget
from typing import Optional
from .Ui_GotoLineDialog import Ui_GotoLineDialog

class GotoLineDialog (QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.ui = Ui_GotoLineDialog()
        self.ui.setupUi(self)
        self.setProperty("shadeBackground", True) # fill background with gradient as defined in style sheet

    def focusInEvent (self, _: Optional[QFocusEvent]) -> None:
        self.ui.editLine.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def getLine(self) -> int:
        try:
            return int(self.ui.editLine.text())
        except ValueError:
            return 0
