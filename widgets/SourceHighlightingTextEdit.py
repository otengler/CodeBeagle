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

from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QApplication, QWidget
from .HighlightingTextEdit import HighlightingTextEdit
from typing import Optional

class SourceHighlightingTextEdit (HighlightingTextEdit):
    # Triggered if a selection was finished while holding a modifier key down
    selectionFinishedWithKeyboardModifier = pyqtSignal('QString',  int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.selectionChanged.connect (self.highlightSelection)

    @pyqtSlot()
    def highlightSelection(self) -> None:
        text = self.textCursor().selectedText().strip()
        if not text or len(text)>64:
            return

        # Allow other components to react on selection of tokens with keyboard modifiers
        modifiers = int(QApplication.keyboardModifiers())
        if modifiers != Qt.KeyboardModifier.NoModifier:
            self.selectionFinishedWithKeyboardModifier.emit(text, modifiers)
        else:
            self.setDynamicHighlight(text)
