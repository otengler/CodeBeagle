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

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QApplication, QWidget
from tools.FileTools import freadall
from typing import cast, Optional
from .Ui_HelpViewerDialog import Ui_HelpViewerDialog

class HelpViewerDialog (QDialog):
    def __init__ (self, parent: Optional[QWidget]) -> None:
        super().__init__(parent,  cast(Qt.WindowType, Qt.WindowType.Dialog | Qt.WindowType.WindowMinMaxButtonsHint))
        self.ui = Ui_HelpViewerDialog()
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]
        self.ui.okButton.clicked.connect(self.accept)
        self.setProperty("shadeBackground", True) # fill background with gradient as defined in style sheet

    def showFile (self, name: str) -> None:
        try:
            text = freadall(name)
        except:
            text = self.tr("Failed to open file")

        self.ui.textBrowserHelp.setHtml (text)

def main() -> None:
    import sys
    app = QApplication(sys.argv)
    w = HelpViewerDialog(None)
    w.showFile("help.html")
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
