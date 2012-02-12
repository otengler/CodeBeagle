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

import os
from PyQt4.QtCore import * 
from PyQt4.QtGui import *
from  LeaveLastTabWidget import LeaveLastTabWidget
from SearchPage import SearchPage
from SettingsDialog import SettingsDialog
import IndexConfiguration
import AppConfig
from Config import Config
  
def setConfigBoolFromCheck (config,  check,  value):
    state = check.checkState() == Qt.Checked
    if Qt.Checked == state:
       setattr(config, value, True)
    elif Qt.Unchecked == state:
       setattr(config, value, False) 
  
class AnimatedUpdateWidget(QWidget):
    def __init__(self, text, parent):
        super(AnimatedUpdateWidget, self).__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(4)
        labelAnimation = QLabel(self)
        self.movie = QMovie(":/default/resources/Update.gif")
        self.movie.setScaledSize(QSize(20, 20))
        labelAnimation.setMovie(self.movie)
        labelText = QLabel(text,  self)
        layout.addWidget (labelAnimation)
        layout.addWidget(labelText)
  
class SearchPageTabWidget (LeaveLastTabWidget):
    configChanged = pyqtSignal()
    
    def __init__(self, parent=None):
        super(SearchPageTabWidget, self).__init__(parent)
        self.setNewTabButtonText(self.trUtf8("New search"))
        self.setPrototypeForNewTab(SearchPage, self.trUtf8("Search"))
        searchPage = self.addNewTab()
        searchPage.showFile ("help.html",  "html")
        
        # Add new tab (QKeySequence.AddTab is the same as Qt.CTRL + Qt.Key_T)
        self.actionNewTab = QAction(self, shortcut=QKeySequence.AddTab, triggered= self.addNewTab)
        self.addAction(self.actionNewTab)
        
        # Open settings
        self.actionOpenSettings = QAction(self, shortcut=Qt.CTRL + Qt.Key_S, triggered= self.openSettings)
        self.addAction(self.actionOpenSettings)
        
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
    
    def addAnimatedUpdateLabel (self,  hbox,  text):
        widget = AnimatedUpdateWidget (text, self)
        widget.hide()
        hbox.addWidget(widget)
        return widget
    
    # Register a button in the corner widget to open the settings dialog. This function is called by the base class.
    def addWidgetsToCornerWidget (self,  hbox):
        super (SearchPageTabWidget,  self).addWidgetsToCornerWidget(hbox)
        self.buttonSettings = self.addButtonToCornerWidget (hbox,  self.trUtf8("Settings"),  "Settings.png",  self.openSettings)
        self.buttonUpdate = self.addButtonToCornerWidget (hbox,  self.trUtf8("Update index"),  "Update.gif",  self.updateIndex)
        self.labelUpdate = self.addAnimatedUpdateLabel (hbox,  self.trUtf8("Update running..."))
        
    # The settings allow to configure search locations (and index them).
    @pyqtSlot()
    def openSettings(self):
        config = AppConfig.userConfig()
        if not config:
            QMessageBox.critical(self,
                        self.trUtf8("Failed to load user config"),
                        self.trUtf8("The user config file could not be loaded from the user profile"),
                        QMessageBox.StandardButtons(QMessageBox.Ok))
        else:
            indexes = IndexConfiguration.readConfig(config)
            settingsDlg = SettingsDialog(self, indexes,  config)
            if settingsDlg.exec():
                locations = settingsDlg.locations()
                self.saveUserConfig (settingsDlg,  locations)
               
    @pyqtSlot()
    def updateIndex(self):
        self.buttonUpdate.hide()
        self.labelUpdate.show()
        self.buttonSettings.setEnabled(False)
        self.labelUpdate.movie.start()
               
    # Check which indexes should be updated and trigger an asynchronous update 
    # This works by putting an file with the name of the index config group into %APPDATA%\CodeBeagle\IndexUpdate.
    # It is picked up by UpdateIndex.py which has a special mode for this task.
    def triggerIndexUpdate (self,  locations):
        indexTriggerPath = os.path.join (AppConfig.getUserDataPath (),  "TriggerUpdate")
        if not os.path.isdir(indexTriggerPath):
            os.mkdir(indexTriggerPath)
        for location in locations:
            if location.generateIndex and hasattr(location, "updateIndex") and location.updateIndex:
                open(os.path.join(indexTriggerPath, groupNameFromLocation(location)), "w").close()
    
    def saveUserConfig (self,  settingsDlg,  locations):
        config = Config (typeInfoFunc=AppConfig.configTypeInfo)
        for location in locations:
            locConf = Config(typeInfoFunc=IndexConfiguration.indexTypeInfo)
            locConf.indexName = location.indexName
            locConf.extensions = location.extensionsAsString()
            locConf.directories =  location.directoriesAsString()
            locConf.dirExcludes = location.dirExcludesAsString()
            locConf.generateIndex = location.generateIndex
            locConf.indexdb = location.indexdb
            setattr(config,  groupNameFromLocation(location),  locConf)
        tabWidth = settingsDlg.ui.editTabWidth.text()
        if tabWidth:
            config.sourceViewer.TabWidth = tabWidth
        config.matchOverFiles = settingsDlg.ui.checkMatchOverFiles.checkState() == Qt.Checked
        config.showCloseConfirmation = settingsDlg.ui.checkConfirmClose.checkState() == Qt.Checked
        try:
            AppConfig.saveUserConfig (config)
        except:
            QMessageBox.critical(self,
                self.trUtf8("Failed to save user config"),
                self.trUtf8("The user config file could not be saved to the user profile"),
                QMessageBox.StandardButtons(QMessageBox.Ok))
        else:    
            # Refresh config
            AppConfig.refreshConfig()
            self.configChanged.emit()
     
    # This is called by the base class when a new tab is added. We use this to connect the request for a new search
    # to open up in a new tab.
    def newTabAdded(self,  searchPage):
        searchPage.newSearchRequested.connect (self.searchInNewTab)
        searchPage.searchFinished.connect (self.changeTabName)
        self.configChanged.connect (searchPage.reloadConfig)
        
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
                self.setTabText(index, self.trUtf8("Search"))
    
def groupNameFromLocation(location):
    return "index_" + location.indexName.replace(" ", "_")
    
    #pos = self.mapToGlobal(self.ui.buttonCustomScripts.pos())
    #QToolTip.showText (pos, "Updating indexes",  self)


