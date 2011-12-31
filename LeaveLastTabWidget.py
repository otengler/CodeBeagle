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

from PyQt4.QtCore import * 
from PyQt4.QtGui import *
from  Ui_LeaveLastTabWidget import Ui_LeaveLastTabWidget
  
class LeaveLastTabWidget (QTabWidget):
    def __init__(self, parent=None):
        super(LeaveLastTabWidget, self).__init__(parent)
        self.ui = Ui_LeaveLastTabWidget()
        self.ui.setupUi(self)
        self.setupUi()
        
        self.strTabName = "Tab"
        self.objType = None
        self.removeTab(0)
        
    def setupUi (self):
        self.button = QPushButton(self.trUtf8("New tab"), self)
        icon = QIcon()
        icon.addPixmap(QPixmap(":/default/resources/NewTab.png"), QIcon.Normal, QIcon.Off)
        self.button.setIcon(icon)
        self.setCornerWidget(self.button)
        QObject.connect(self, SIGNAL("tabCloseRequested(int)"),  self.removeTabButNotLast)
        QObject.connect(self, SIGNAL("currentChanged(int)"),  self.focusSetter)
        QObject.connect(self.button, SIGNAL("clicked()"),  self.addNewTab)
        
    @pyqtSlot(int)
    def removeTabButNotLast (self, index):
        if self.count() <= 1:
            return
        widget = self.widget(index)
        super(LeaveLastTabWidget, self).removeTab(index)
        widget.close()
        
    def setNewTabButtonText (self, strText):
        self.button.setText(strText)
    
    def setPrototypeForNewTab (self, objType,  strTabName):
        self.objType = objType
        self.strTabName = strTabName
    
    @pyqtSlot()
    def addNewTab(self):
        widget = self.objType(self)
        widget.setAttribute(Qt.WA_DeleteOnClose)
        self.addTab(widget, self.strTabName)
        self.setCurrentWidget(widget)
        self.newTabAdded(widget)
        return widget
        
    def newTabAdded(self,  widget):
        pass
        
    @pyqtSlot(int)
    def focusSetter(self, index):
        widget = self.widget(index)
        if widget:
            widget.setFocus(Qt.ActiveWindowFocusReason)
            
        
# The following code removes the close box if only one tab is left. The problem is that the size of the TabBar jumps
# if the close box is shown when the second tab is added
#    def tabInserted (self,  index):
#        self.maintainCloseBox()
#        
#    def tabRemoved (self,  index):
#        self.maintainCloseBox()
#        
#    def maintainCloseBox (self):
#        if self.count() > 1:
#            self.setTabsClosable(True)
#        else:
#            self.setTabsClosable(False)
            