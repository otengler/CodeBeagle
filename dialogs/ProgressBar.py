# -*- coding: utf-8 -*-
"""
Copyright (C) 2011 Oliver Tengler

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

from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QDialog
from .Ui_ProgressBar import Ui_ProgressBar

class ProgressBar (QDialog):
    onCancelClicked = pyqtSignal()

    def __init__ (self, parent, bEnableCancel=False):
        super().__init__(parent,  Qt.SplashScreen)
        self.ui = Ui_ProgressBar()
        self.ui.setupUi(self)
        self.ui.frame.setProperty("shadeBackground", True) # fill background with gradient as defined in style sheet
        if not bEnableCancel:
            self.ui.buttonCancel.setEnabled(False)

    def keyPressEvent(self,  e):
        """Disable closing the dialog with Esc and emit onCancelClicked instead."""
        if e.key() != Qt.Key_Escape:
            super ().keyPressEvent(e)
        else:
            self.onCancelClicked.emit()

    @pyqtSlot()
    def cancelClicked(self):
        self.ui.buttonCancel.setEnabled(False)
        self.onCancelClicked.emit()
