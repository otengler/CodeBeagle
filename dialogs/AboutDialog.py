# -*- coding: utf-8 -*-
"""
Copyright (C) 2012 Oliver Tengler

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

import sys
from PyQt5.QtWidgets import QDialog, QApplication, QWidget
from PyQt5 import QtCore
import AppConfig
from typing import Optional
from .Ui_AboutDialog import Ui_AboutDialog

class AboutDialog(QDialog):
    def __init__(self, parent: Optional[QWidget]) -> None:
        super().__init__(parent)
        self.ui = Ui_AboutDialog()
        self.ui.setupUi(self)
        version = sys.version_info
        pythonAndQt = " (Python %u.%u.%u, Qt %s)" % (version.major, version.minor, version.micro, QtCore.qVersion())
        self.ui.labelVersion.setText(self.tr("Version") + " " + AppConfig.appVersion + pythonAndQt)
        self.setProperty("shadeBackground", True) # fill background with gradient as defined in style sheet

def main() -> None:
    app = QApplication(sys.argv)
    wnd = AboutDialog(None)
    wnd.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
