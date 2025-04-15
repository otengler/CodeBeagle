# -*- coding: utf-8 -*-
"""
Copyright (C) 2011 Oliver Tengler

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

from typing import Callable, Optional
from PyQt5.QtWidgets import QTabWidget, QWidget, QHBoxLayout, QPushButton, QMenu
from PyQt5.QtGui import QIcon, QPixmap, QMouseEvent
from PyQt5.QtCore import Qt, pyqtSlot
from .Ui_LeaveLastTabWidget import Ui_LeaveLastTabWidget

class LeaveLastTabWidget (QTabWidget):
    def __init__(self, parent: QWidget=None) -> None:
        super().__init__(parent)
        self.buttonNewTab = None
        self.ui = Ui_LeaveLastTabWidget()
        self.ui.setupUi(self)
        self.setupUi()

        self.strTabName = "Tab"
        self.objType: Optional[Callable[[QWidget], QWidget]] = None
        self.removeTab(0)

    def setupUi (self) -> None:
        widget = QWidget(self)
        self.hbox = QHBoxLayout(widget)
        self.hbox.setContentsMargins(0, 0, 0, 0)
        self.addWidgetsToCornerWidget (self.hbox)
        self.setCornerWidget(widget)

        self.tabCloseRequested.connect(self.removeTabButNotLast)
        self.currentChanged.connect(self.focusSetter)

    def cornerWidgetLayout (self) -> QHBoxLayout:
        return self.hbox

    def addWidgetsToCornerWidget (self, hbox: QHBoxLayout) -> None:
        """Derived classes can implement this to add additional buttons to the corner widget."""
        self.buttonNewTab = self.addButtonToCornerWidget (hbox,  self.tr("New tab"),  "NewTab.png",  self.addNewTab)

    def addButtonToCornerWidget (self, hbox: QHBoxLayout, name: str, iconFile: str, handler: Callable) -> QPushButton:
        button = QPushButton(name, self)
        icon = QIcon()
        icon.addPixmap(QPixmap("resources/" + iconFile), QIcon.Normal, QIcon.Off)
        button.setIcon(icon)
        button.setFlat(True)
        hbox.addWidget (button)
        button.clicked.connect(handler)
        return button

    @pyqtSlot(int)
    def removeTabButNotLast (self, index: int) -> None:
        if self.count() <= 1:
            return
        widget = self.widget(index)
        super().removeTab(index)
        widget.close()

    def setNewTabButtonText (self, text: str) -> None:
        if self.buttonNewTab:
            self.buttonNewTab.setText(text)

    def setPrototypeForNewTab (self, objType: Callable[[QWidget], QWidget], strTabName: str) -> None:
        self.objType = objType
        self.strTabName = strTabName

    @pyqtSlot()
    def addNewTab(self) -> QWidget:
        if not self.objType:
            return None
        prevTabWidget = self.currentWidget()
        newTabWidget = self.objType(self)
        newTabWidget.setAttribute(Qt.WA_DeleteOnClose)
        self.addTab(newTabWidget, self.strTabName)
        self.setCurrentWidget(newTabWidget)
        self.newTabAdded(prevTabWidget, newTabWidget)
        return newTabWidget

    def newTabAdded(self, prevTabWidget: QWidget, newTabWidget: QWidget) -> None:
        pass

    def removeCurrentTab(self) -> None:
        index = self.currentIndex()
        if -1 != index:
            self.removeTabButNotLast(index)

    @pyqtSlot(int)
    def focusSetter(self, index: int) -> None:
        widget = self.widget(index)
        if widget:
            widget.setFocus(Qt.ActiveWindowFocusReason)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Show context menu which offers the possibility to close multiple tabs at once"""
        if event.button() != Qt.RightButton or self.count() == 1:
            return
        tabIndex = self.tabBar().tabAt(event.pos())
        if tabIndex == -1:
            return
        menu = QMenu()
        menu.addAction(self.tr("Close &others tabs"), lambda: self.__closeAllTabsExceptThis(tabIndex))
        if tabIndex > 0:
            menu.addAction(self.tr("Close all to the &left"), lambda: self.__closeAllToTheLeft(tabIndex))
        if tabIndex < self.count()-1:
            menu.addAction(self.tr("Close all to the &right"), lambda: self.__closeAllToTheRight(tabIndex))

        menu.exec(self.ui.tab.mapToGlobal(event.pos()))

    @pyqtSlot(int)
    def __closeAllTabsExceptThis(self, tabIndex: int) -> None:
        self.__closeTabs(lambda index : index != tabIndex)

    @pyqtSlot(int)
    def __closeAllToTheLeft(self, tabIndex: int) -> None:
        self.__closeTabs(lambda index: index < tabIndex)

    @pyqtSlot(int)
    def __closeAllToTheRight(self, tabIndex: int) -> None:
        self.__closeTabs(lambda index: index > tabIndex)

    def __closeTabs(self, filterPred: Callable[[int],bool]) -> None:
        closeIndexes = []
        for i in range(self.count()):
            if filterPred(i):
                closeIndexes.append(i)
        closeIndexes.sort(reverse=True)
        for index in closeIndexes:
            self.removeTab(index)


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
