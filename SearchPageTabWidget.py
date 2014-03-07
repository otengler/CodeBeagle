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
import sys
from PyQt4.QtCore import * 
from PyQt4.QtGui import *
from  LeaveLastTabWidget import LeaveLastTabWidget
from SearchPage import SearchPage
from Config import Config
import AppConfig
import FileTools
import IndexConfiguration
import UserHintDialog
import StackTraceMessageBox
import UpdateIndex

userHintUpdateIndex = """
<p align='justify'>You added or changed indexed search locations:
%(locations)s
</p>
<p align='justify'>Do you want me to update the indexes now?</p>
<p align='jusitfy'> The update runs in the background and continues even if you close the program. During the update the index cannot be used. 
To manually start the index update press the 'Update Index' button in the toolbar. See the help for more details.</p>
"""

userHintInitialSetup= """
<p align='justify'>There are no search locations defined so far. </p>
<p align='justify'>Would you like to open the settings dialog and create a first search location now?</p>
"""
  
def setConfigBoolFromCheck (config,  check,  value):
    state = check.checkState() == Qt.Checked
    if Qt.Checked == state:
       setattr(config, value, True)
    elif Qt.Unchecked == state:
       setattr(config, value, False) 
  
# This widget attempts to look like a flat QPushButton. It shows a spinning gear icon to indicate
# work in progress. 
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
    configChanged = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super(SearchPageTabWidget, self).__init__(parent)
        self.setNewTabButtonText(self.trUtf8("New search"))
        self.setPrototypeForNewTab(SearchPage, self.trUtf8("Search"))
        self.addNewTab()
        
        # Add new tab (QKeySequence.AddTab is the same as Qt.CTRL + Qt.Key_T)
        self.actionNewTab = QAction(self, shortcut=QKeySequence.AddTab, triggered= self.addNewTab)
        self.addAction(self.actionNewTab)
        # Close current tab
        self.actionRemoveCurrentTab = QAction(self, shortcut=Qt.CTRL + Qt.Key_W, triggered= self.removeCurrentTab)
        self.addAction(self.actionRemoveCurrentTab)
        
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
        
        self.indexUpdateTimer = None
        self.indexTriggerPath = os.path.join (AppConfig.userDataPath (),  "TriggerUpdate")
        
        self.handleUncleanShutdown()
        
        # A list of index names which are currently disabled because the update is running
        self.disabledIndexes = []
        # If the index update is still running this will start the timer which watches for it to finish
        self.__watchForIndexUpdate()
        
        # Wait a little for the main window to display, then ask user for initial setup
        QTimer.singleShot (500,  self.initialSetup)        
     
    # If UpdateIndex.exe crashes or is terminated by the user some files are 
    # left behind which cause CodeBeagle to think that there is an update index running.
    # Clean this up.
    def handleUncleanShutdown(self):
        UpdateIndex.handleUncleanShutdown(self.indexTriggerPath)
     
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
    
    # Register a button in the corner widget to open the settings dialog. This function is called by the base class.
    def addWidgetsToCornerWidget (self,  hbox):
        super (SearchPageTabWidget,  self).addWidgetsToCornerWidget(hbox)
        self.buttonSettings = self.addButtonToCornerWidget (hbox,  self.trUtf8("Settings"),  "Settings.png",  self.openSettings)
        self.buttonUpdate = self.addButtonToCornerWidget (hbox,  self.trUtf8("Update index"),  "Update.png",  self.updateIndex)
        self.indexOfUpdateButton = hbox.count()-1
        self.buttonHelp = self.addButtonToCornerWidget (hbox,  self.trUtf8("Help"),  "Help.png",  self.openHelp)
        self.buttonAbout = self.addButtonToCornerWidget (hbox,  self.trUtf8("About"),  "CodeBeagle.png",  self.openAbout)
        self.labelUpdate = None
        
    # The settings allow to configure search locations.
    @pyqtSlot()
    def openSettings(self, createInitialLocation=False, locationToAdd=None):
        try:
            config = AppConfig.userConfig()
            globalConfig = AppConfig.globalConfig()
        except:
            self.userConfigFailedToLoadMessage()
        else:
            searchLocations = IndexConfiguration.readConfig(config)
            globalSearchLocations = IndexConfiguration.readConfig(globalConfig)
            from SettingsDialog import SettingsDialog
            settingsDlg = SettingsDialog(self, searchLocations,  globalSearchLocations, config)
            if createInitialLocation:
                settingsDlg.addLocation()
            if locationToAdd:
                settingsDlg.addExistingLocation(locationToAdd)
            if settingsDlg.exec():
                self.__saveUserConfig (searchLocations, settingsDlg)

    def __saveUserConfig (self,  currentSearchLocations,  settingsDlg):
        locations = settingsDlg.locations()
        config = Config (typeInfoFunc=AppConfig.configTypeInfo)
        for location in locations:
            locConf = Config(typeInfoFunc=IndexConfiguration.indexTypeInfo)
            locConf.indexName = location.indexName
            locConf.extensions = location.extensionsAsString()
            locConf.directories =  location.directoriesAsString()
            locConf.dirExcludes = location.dirExcludesAsString()
            locConf.generateIndex = location.generateIndex
            locConf.indexdb = location.indexdb
            setattr(config,  "Index_" + FileTools.removeInvalidFileChars(location.indexName),  locConf)
        config.sourceViewer.FontFamily = settingsDlg.ui.fontComboBox.currentFont().family()
        config.sourceViewer.FontSize = settingsDlg.ui.editFontSize.text()
        config.sourceViewer.TabWidth = settingsDlg.ui.editTabWidth.text()
        config.matchOverFiles = settingsDlg.ui.checkMatchOverFiles.checkState() == Qt.Checked
        config.showCloseConfirmation = settingsDlg.ui.checkConfirmClose.checkState() == Qt.Checked
        config.showMatchList = settingsDlg.ui.checkShowMatchList.checkState() == Qt.Checked
        config.defaultLocation = settingsDlg.defaultLocation()
        config.previewLines = int(settingsDlg.ui.editPreviewLines.text())
        try:
            AppConfig.saveUserConfig (config)
        except:
            self.failedToSaveUserConfigMessage()
        else: 
            updateDisplayNames = self.__getAddedOrChangedIndexedSearchLocations (currentSearchLocations,  locations)
            if updateDisplayNames:
                # Show a user hint which allows to update added or changed indexes<ul>
                locationsHtml = "<ul>"
                for displayName in updateDisplayNames:
                   locationsHtml += "<li>" + displayName + "</li>"
                locationsHtml += "</ul>"
                text = self.trUtf8(userHintUpdateIndex) % {"locations" : locationsHtml}
                result = UserHintDialog.showUserHint (self, "updateIndexes",  self.trUtf8("Update indexes"), text,  
                                                                            UserHintDialog.Yes, False,  UserHintDialog.No,  True,  bShowHintAgain=True)
                if result == UserHintDialog.Yes:
                    try:
                        self.__triggerIndexUpdate (updateDisplayNames)
                    except:
                        self.failedToUpdateIndexesMessage()
                
            # Refresh config
            AppConfig.refreshConfig()
            searchLocations = IndexConfiguration.readConfig(AppConfig.appConfig())
            self.configChanged.emit(searchLocations)
        
    # Returns a list of display names of added or changed indexed search locations 
    def __getAddedOrChangedIndexedSearchLocations (self,  currentSearchLocations,  newSearchLocations):
        changedLocations = []
        for location in newSearchLocations:
            if location.generateIndex:
                bFound = False
                for oldLocation in currentSearchLocations:
                    if location == oldLocation:
                        bFound = True
                        break
                if not bFound:
                    changedLocations.append(location.displayName())
        return changedLocations
    
    # This is called when a directory is dropped on the application. This is a shortcut to create a search location.
    @pyqtSlot('QString')
    def addSearchLocationFromPath (self,  directory):
        ext = FileTools.getMostCommonExtensionInDirectory (directory)
        location = IndexConfiguration.IndexConfiguration(self.trUtf8("Search") + " '" + directory + "'", ext,  directory, "", "", False)
        
        self.openSettings (locationToAdd=location)
               
    @pyqtSlot()
    def updateIndex(self):
        try:
            config = AppConfig.userConfig()
        except:
            self.userConfigFailedToLoadMessage()
        else:
            searchLocations = IndexConfiguration.readConfig(config)
            displayNames = [config.displayName() for config in searchLocations if config.generateIndex]
            from CheckableItemsDialog import CheckableItemsDialog
            updateDialog = CheckableItemsDialog(self.trUtf8("Choose indexes to update"),  True, self)
            for name in displayNames:
                updateDialog.addItem(name)
            updateDialog.checkAll(True)
            if updateDialog.exec():
                # The items returned are touples: (index,value)
                updateDisplayNames = [name for i, name in updateDialog.checkedItems()]
                try:
                    self.__triggerIndexUpdate (updateDisplayNames)
                except:
                    self.failedToUpdateIndexesMessage()
                    
    @pyqtSlot()
    def openHelp(self):
        from HelpViewerDialog import HelpViewerDialog
        helpDialog = HelpViewerDialog(self)
        helpDialog.setAttribute(Qt.WA_DeleteOnClose)
        helpDialog.showFile("help.html")
        helpDialog.show()
        
    @pyqtSlot()
    def openAbout(self):
        from AboutDialog import AboutDialog
        aboutDialog = AboutDialog(self)
        aboutDialog.exec()
               
    # Check which indexes should be updated and trigger an asynchronous update 
    # This works by putting an file with the name of the index config group into %APPDATA%\CodeBeagle\IndexUpdate.
    # It is picked up by UpdateIndex.py which has a special mode for this task.
    def __triggerIndexUpdate (self,  updateDisplayNames):
        if not os.path.isdir(self.indexTriggerPath):
            os.makedirs(self.indexTriggerPath)
        for name in updateDisplayNames:
            open(os.path.join(self.indexTriggerPath, FileTools.removeInvalidFileChars(name)), "w").close()
    
        # Now start UpdateIndex.py as a subprocess. If we are running as "CodeBeagle.exe" then start "UpdateIndex.exe" instead
        import subprocess
        runningInInterpreter = os.path.basename(sys.executable).lower().startswith("python")
        args = ["--jobmode",  self.indexTriggerPath, "--config",  AppConfig.userConfigFileName()]
        if runningInInterpreter:
            subprocess.Popen ([sys.executable, "UpdateIndex.py"] + args)
        else:
            if os.path.exists("UpdateIndex.exe"):
                si = subprocess.STARTUPINFO()
                si.dwFlags = subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE
                subprocess.Popen (["UpdateIndex.exe"] + args,  startupinfo=si)
            else:
                raise RuntimerError("UpdateIndex.exe not found")
        
        self.__watchForIndexUpdate()
    
    # Check regularily if the update finished
    def __watchForIndexUpdate(self):
        running = self.__indexUpdateRunning()
        self.__maintainRunningIndexUpdates(running)
        if running:
            self.__showIndexUpdateInProgress(True)
            if not self.indexUpdateTimer:
                self.indexUpdateTimer = QTimer(self)
                self.indexUpdateTimer.timeout.connect(self.__checkIndexUpdateProgress)
            self.indexUpdateTimer.start(2000)
   
    def __checkIndexUpdateProgress (self):
        running = self.__indexUpdateRunning()
        self.__maintainRunningIndexUpdates(running)
        if not running:
            self.indexUpdateTimer.stop()
            self.__showIndexUpdateInProgress(False)
            self.__informAboutIndexUpdate("Index update finshed")
            
    def __indexUpdateRunning (self):
        try:
            files = os.listdir(self.indexTriggerPath)
            return files
        except:
            return []
            
    # Informs all search pages which search locations are currently not available
    def __maintainRunningIndexUpdates(self,  running):
        if len(running) != len(self.disabledIndexes):
            self.disabledIndexes = running
            searchLocations = IndexConfiguration.readConfig(AppConfig.appConfig())
            availableLocations = []
            for location in searchLocations:
                if not FileTools.removeInvalidFileChars(location.displayName()) in self.disabledIndexes:
                    availableLocations.append (location)
            self.configChanged.emit(availableLocations)
        else:
            self.disabledIndexes = running
            
    def __informAboutIndexUpdate(self,  text):
        pos = self.labelUpdate.parent().mapToGlobal(self.labelUpdate.pos())
        pos.setX(pos.x())
        QToolTip.showText (pos, text,  self)
        
    def __addAnimatedUpdateLabel (self,  hbox,  text):
        widget = AnimatedUpdateWidget (text, self)
        widget.hide()
        hbox.insertWidget(self.indexOfUpdateButton,  widget)
        return widget
        
    def __showIndexUpdateInProgress (self, bInProgress):
        if not self.labelUpdate:
            self.labelUpdate = self.__addAnimatedUpdateLabel (self.cornerWidgetLayout(),  self.trUtf8("Update running..."))
        if bInProgress:
            self.buttonUpdate.hide()
            self.labelUpdate.show()
            self.buttonSettings.setEnabled(False)
            self.labelUpdate.movie.start()
        else:
            self.labelUpdate.movie.stop()
            self.buttonUpdate.show()
            self.labelUpdate.hide()
            self.buttonSettings.setEnabled(True)

    # This is called by the base class when a new tab is added. We use this to connect the request for a new search
    # to open up in a new tab.
    def newTabAdded(self,  searchPage):
        searchPage.newSearchRequested.connect (self.searchInNewTab)
        searchPage.searchFinished.connect (self.changeTabName)
        searchPage.ui.sourceViewer.directoryDropped.connect(self.addSearchLocationFromPath)
        self.configChanged.connect (searchPage.reloadConfig)
        # Initially reload the config to pass the current search locations to the search page 
        searchPage.reloadConfig(IndexConfiguration.readConfig(AppConfig.appConfig()))
        
    @pyqtSlot('QString', 'QString')
    def searchInNewTab (self,  text, searchLocationName):
        searchPage = self.addNewTab ()
        searchPage.setCurrentSearchLocation(searchLocationName)
        searchPage.searchForText(text)
        
    @pyqtSlot('QWidget', 'QString')
    def changeTabName (self,  searchPage,  text):
        index = self.indexOf(searchPage)
        if -1 != index:
            if text:
                self.setTabText(index, text)
            else:
                self.setTabText(index, self.trUtf8("Search"))
            
    @pyqtSlot()
    def initialSetup(self):
        if UserHintDialog.hintWouldBeShown("noLocations"):
            locations = IndexConfiguration.readConfig(AppConfig.appConfig())
            if len(locations)==0:
                text = self.trUtf8(userHintInitialSetup)
                res = UserHintDialog.showUserHint (self, "noLocations",  self.trUtf8("Initial setup"), text,  UserHintDialog.Yes,  True,  UserHintDialog.No)
                if res == UserHintDialog.Yes:
                    self.openSettings(createInitialLocation=True)
        
    def failedToSaveUserConfigMessage(self):
        StackTraceMessageBox.show(self,
                self.trUtf8("Failed to save user config"),
                self.trUtf8("The user config file could not be saved to the user profile"))
            
    def userConfigFailedToLoadMessage(self):
        StackTraceMessageBox.show(self,
                        self.trUtf8("Failed to load user config"),
                        self.trUtf8("The user config file could not be loaded from the user profile"))
                        
    def failedToUpdateIndexesMessage(self):
        StackTraceMessageBox.show(self,
                        self.trUtf8("Error during index update"),
                        self.trUtf8("The update process failed to update the desired indexes"))
                        



