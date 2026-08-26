# -*- coding: utf-8 -*-
"""
Copyright (C) 2024 Oliver Tengler

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

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QWidget, QApplication
from .Ui_AgentInstructionsDialog import Ui_AgentInstructionsDialog

class AgentInstructionsDialog(QDialog):
    """Dialog that shows setup instructions for connecting an AI agent to CodeBeagle."""

    def __init__(self, parent: Optional[QWidget], title: str, instructions: str, description: Optional[str] = None) -> None:
        super().__init__(parent, Qt.WindowType.Dialog)
        self.ui = Ui_AgentInstructionsDialog()
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]
        if description:
            self.ui.labelHint.setText(description)
        self.setProperty("shadeBackground", True)
        self.setWindowTitle(title)
        # setText() auto-detects rich text (HTML) vs plain text, so
        # instructions can use HTML for captions and code blocks.
        # QTextBrowser with openExternalLinks=True opens <a href=...> links
        # in the default browser automatically.
        self.ui.textEditInstructions.setText(instructions)

        # Wire up buttons (kept in code, not in .ui)
        self.ui.buttonCopy.clicked.connect(self.__copyToClipboard)
        self.ui.buttonClose.clicked.connect(self.accept)

    def __copyToClipboard(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.ui.textEditInstructions.toPlainText())