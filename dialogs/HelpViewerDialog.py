# -*- coding: utf-8 -*-
"""
Copyright (C) 2021 Oliver Tengler

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

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QKeySequence, QTextCursor
from PySide6.QtWidgets import QDialog, QApplication, QWidget, QTextEdit
from AppConfig import appConfig
from tools.FileTools import freadall
from tools.QHelper import createQAction
from widgets.InDocumentSearchWidget import InDocumentSearchResult
from widgets.SyntaxHighlighter import SyntaxHighlighter
from typing import Optional, List
from .Ui_HelpViewerDialog import Ui_HelpViewerDialog

class HelpViewerDialog (QDialog):
    def __init__ (self, parent: Optional[QWidget]) -> None:
        super().__init__(parent,  Qt.WindowType.Dialog | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint)
        self.ui = Ui_HelpViewerDialog()
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]
        self.ui.okButton.clicked.connect(self.accept)
        self.setProperty("shadeBackground", True) # fill background with gradient as defined in style sheet

        # In document search of the help text
        self.ui.widgetInDocumentSearch.hide()
        self.addAction(createQAction(self, shortcut=QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_F), triggered=self.toggleSearchFrame))
        self.ui.buttonSearch.clicked.connect(self.showSearchFrame)
        self.ui.widgetInDocumentSearch.searchFinished.connect(self.inDocumentSearchFinished)
        self.ui.widgetInDocumentSearch.currentMatchChanged.connect(self.inDocumentSearchMatchChanged)

    def showFile (self, name: str) -> None:
        try:
            text = freadall(name)
        except:
            text = self.tr("Failed to open file")

        # Replace the API server port placeholder with the configured port
        text = text.replace("__PORT__", str(appConfig().agent.port))
        self.ui.textBrowserHelp.setHtml (text)
        self.ui.widgetInDocumentSearch.setText(self.ui.textBrowserHelp.toPlainText())

    @Slot()
    def toggleSearchFrame(self) -> None:
        text = self.ui.textBrowserHelp.textCursor().selectedText().strip()
        if text:
            self.ui.widgetInDocumentSearch.setSearch(text)
            self.ui.buttonSearch.setChecked(True)
        else:
            self.ui.buttonSearch.setChecked(not self.ui.buttonSearch.isChecked())
        self.showSearchFrame()

    @Slot()
    def showSearchFrame(self) -> None:
        if self.ui.buttonSearch.isChecked():
            self.ui.widgetInDocumentSearch.show()
            self.ui.widgetInDocumentSearch.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        else:
            self.ui.widgetInDocumentSearch.hide()
            self.ui.widgetInDocumentSearch.setSearch("")
            self.__clearHighlights()

    @Slot(int, int, int)
    def inDocumentSearchMatchChanged(self, _: int, index: int, length: int) -> None:
        cursor = self.ui.textBrowserHelp.textCursor()
        cursor.setPosition(index)
        cursor.setPosition(index + length, QTextCursor.MoveMode.KeepAnchor)
        self.ui.textBrowserHelp.setTextCursor(cursor)
        self.ui.textBrowserHelp.ensureCursorVisible()

    @Slot(InDocumentSearchResult)
    def inDocumentSearchFinished(self, searchResult: InDocumentSearchResult) -> None:
        extras: List[QTextEdit.ExtraSelection] = []
        for match in searchResult.results:
            extra = QTextEdit.ExtraSelection()
            extra.cursor = QTextCursor(self.ui.textBrowserHelp.document())
            extra.cursor.setPosition(match.index)
            extra.cursor.setPosition(match.index + match.length, QTextCursor.MoveMode.KeepAnchor)
            extra.format.setBackground(SyntaxHighlighter.match2BackgroundColor)
            extra.format.setForeground(SyntaxHighlighter.match2ForegroundColor)
            extras.append(extra)
        self.ui.textBrowserHelp.setExtraSelections(extras)

    def __clearHighlights(self) -> None:
        self.ui.textBrowserHelp.setExtraSelections([])

def main() -> None:
    import sys
    app = QApplication(sys.argv)
    w = HelpViewerDialog(None)
    w.showFile("help.html")
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
