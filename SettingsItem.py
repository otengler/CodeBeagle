# -*- coding: utf-8 -*-
"""
Copyright (C) 2012 Oliver Tengler

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

from PyQt4.QtCore import * 
from PyQt4.QtGui import *
from Ui_SettingsItem import Ui_SettingsItem

class SettingsItem (QWidget):
    def __init__ (self, parent,  shadeBackground=False):
        super (SettingsItem, self).__init__(parent)
        self.ui = Ui_SettingsItem()
        self.ui.setupUi(self)
        if shadeBackground:
            self.gradient = QLinearGradient()
            self.gradient.setStart(0, 0)
            self.gradient.setColorAt(0, QColor("#eef"))
            self.gradient.setColorAt(1, QColor("#ccf"))
        else:
            self.gradient = None
   
    def focusInEvent (self, event):
        self.ui.editName.setFocus(Qt.ActiveWindowFocusReason)
        
    def paintEvent(self, event):
        if self.gradient:
            rect = event.rect()
            self.gradient.setFinalStop (rect.width(), 0)
            painter = QPainter(self)
            painter.fillRect(rect, QBrush(self.gradient))
        super(SettingsItem, self).paintEvent(event)
        
    def setName(self, name):
        self.ui.editName.setText (name)
    def name (self):
        return self.ui.editName.text()
