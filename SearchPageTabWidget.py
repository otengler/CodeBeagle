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
from  LeaveLastTabWidget import LeaveLastTabWidget
from SearchPage import SearchPage
  
class SearchPageTabWidget (LeaveLastTabWidget):
    def __init__(self, parent=None):
        super(SearchPageTabWidget, self).__init__(parent)
        self.setNewTabButtonText(self.trUtf8("New search"))
        self.setPrototypeForNewTab(SearchPage, self.trUtf8("Search"))
        searchPage = self.addNewTab()
        searchPage.showFile ("help.html",  "html")
        
        # Add new tab (QKeySequence.AddTab is the same as Qt.CTRL + Qt.Key_T)
        self.actionNewTab = QAction(self, shortcut=QKeySequence.AddTab, triggered= self.addNewTab)
        self.addAction(self.actionNewTab)
        
        self.actionTab1 = QAction(self, shortcut=Qt.ALT + Qt.Key_1, triggered= self.activateTab1)
        self.addAction(self.actionTab1)
        self.actionTab2 = QAction(self, shortcut=Qt.ALT + Qt.Key_2, triggered= self.activateTab2)
        self.addAction(self.actionTab2)
        self.actionTab3 = QAction(self, shortcut=Qt.ALT + Qt.Key_3, triggered= self.activateTab3)
        self.addAction(self.actionTab3)
        self.actionTab4 = QAction(self, shortcut=Qt.ALT + Qt.Key_4, triggered= self.activateTab4)
        self.addAction(self.actionTab4)
        self.actionTab5 = QAction(self, shortcut=Qt.ALT + Qt.Key_5, triggered= self.activateTab5)
        self.addAction(self.actionTab5)
        self.actionTab6 = QAction(self, shortcut=Qt.ALT + Qt.Key_6, triggered= self.activateTab6)
        self.addAction(self.actionTab6)
     
    @pyqtSlot()
    def activateTab1(self):
        self.setCurrentIndex(0)
    @pyqtSlot()
    def activateTab2(self):
        self.setCurrentIndex(1)
    @pyqtSlot()
    def activateTab3(self):
        self.setCurrentIndex(2)
    @pyqtSlot()
    def activateTab4(self):
        self.setCurrentIndex(3)
    @pyqtSlot()
    def activateTab5(self):
        self.setCurrentIndex(4)
    @pyqtSlot()
    def activateTab6(self):
        self.setCurrentIndex(5)
     
    # This is called by the base class when a new tab is added. We use this to connect the request for a new search
    # to open up in a new tab.
    def newTabAdded(self,  searchPage):
        QObject.connect(searchPage, SIGNAL("newSearchRequested(QString,int)"),  self.searchInNewTab)
        QObject.connect(searchPage,  SIGNAL("searchStarted(QWidget, QString)"),  self.changeTabName)
        
    @pyqtSlot('QString', int)
    def searchInNewTab (self,  text, dbIndex):
        searchPage = self.addNewTab ()
        searchPage.setCurrentDatabase(dbIndex)
        searchPage.searchForText(text)
        
    @pyqtSlot('QWidget', 'QString')
    def changeTabName (self,  searchPage,  text):
        index = self.indexOf(searchPage)
        if -1 != index:
            if text:
                self.setTabText(index, text)
            else:
                self.setTabText(index, "Search")
        
