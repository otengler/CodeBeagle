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
from typing import List
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QAction, QToolTip, QPushButton
from widgets.LeaveLastTabWidget import LeaveLastTabWidget
from widgets.AnimatedProgressWidget import AnimatedProgressWidget
from tools import FileTools
from dialogs import StackTraceMessageBox
from dialogs.UserHintDialog import ButtonType,hintWouldBeShown,showUserHint
from dialogs.SettingsDialog import SettingsDialog
from SearchPage import SearchPage
import AppConfig
from fulltextindex import IndexConfiguration
import UpdateIndex

userHintInitialSetup= """
<p align='justify'>There are no search locations defined so far. </p>
<p align='justify'>Would you like to open the settings dialog and create a first search location now?</p>
"""

userHintDarkTheme="""
<p align='justify'>There is a dark theme available now. It can be selected from the options dialog.</p>
<p align='justify'>Would you like to give it a try?</p>
"""

class SearchPageTabWidget (LeaveLastTabWidget):
    configChanged = pyqtSignal(list)
    requestWindowTitleChange = pyqtSignal(str)

    def __init__(self, parent:QWidget=None) -> None:
        self.buttonSettings: QPushButton
        self.buttonUpdate: QPushButton
        self.indexOfUpdateButton:int
        self.buttonHelp: QPushButton
        self.buttonAbout: QPushButton
        self.labelUpdate: QLabel

        super().__init__(parent)

        self.setNewTabButtonText(self.tr("New search"))
        self.setPrototypeForNewTab(SearchPage, self.tr("Search"))
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

        self.indexUpdateTimer: QTimer = None
        self.indexTriggerPath = os.path.join (AppConfig.userDataPath (),  "TriggerUpdate")

        self.handleUncleanShutdown()

        # A list of index names which are currently disabled because the update is running
        self.disabledIndexes: List[str] = []
        # If the index update is still running this will start the timer which watches for it to finish
        self.__watchForIndexUpdate()

        # Wait a little for the main window to display, then ask user for initial setup
        QTimer.singleShot (500,  self.initialSetup)

    def handleUncleanShutdown(self) -> None:
        """
        If UpdateIndex.exe crashes or is terminated by the user some files are
        left behind which cause CodeBeagle to think that there is an update index running.
        Clean this up.
        """
        UpdateIndex.handleUncleanShutdown(self.indexTriggerPath)

    @pyqtSlot()
    def activateTab1(self) -> None:
        self.setCurrentIndex(0)
    @pyqtSlot()
    def activateTab2(self) -> None:
        self.setCurrentIndex(1)
    @pyqtSlot()
    def activateTab3(self) -> None:
        self.setCurrentIndex(2)
    @pyqtSlot()
    def activateTab4(self) -> None:
        self.setCurrentIndex(3)
    @pyqtSlot()
    def activateTab5(self) -> None:
        self.setCurrentIndex(4)
    @pyqtSlot()
    def activateTab6(self) -> None:
        self.setCurrentIndex(5)

    # Register a button in the corner widget to open the settings dialog. This function is called by the base class.
    def addWidgetsToCornerWidget (self,  hbox: QHBoxLayout) -> None:
        super ().addWidgetsToCornerWidget(hbox)
        self.buttonSettings = self.addButtonToCornerWidget (hbox,  self.tr("Settings"),  "Settings.png",  self.openSettings)
        self.buttonUpdate = self.addButtonToCornerWidget (hbox,  self.tr("Update index"),  "Update.png",  self.updateIndex)
        self.indexOfUpdateButton = hbox.count()-1
        self.buttonHelp = self.addButtonToCornerWidget (hbox,  self.tr("Help"),  "Help.png",  self.openHelp)
        self.buttonAbout = self.addButtonToCornerWidget (hbox,  self.tr("About"),  "CodeBeagle.png",  self.openAbout)
        self.labelUpdate = None

    # The settings allow to configure search locations.
    @pyqtSlot()
    def openSettings(self, createInitialLocation: bool=False, locationToAdd: IndexConfiguration.IndexConfiguration=None) -> None:
        try:
            config = AppConfig.userConfig()
            globalConfig = AppConfig.globalConfig()
        except:
            self.userConfigFailedToLoadMessage()
        else:
            searchLocations = IndexConfiguration.readConfig(config)
            globalSearchLocations = IndexConfiguration.readConfig(globalConfig)
            settingsDlg = SettingsDialog(self, searchLocations,  globalSearchLocations, config)
            settingsDlg.updateChangedIndexes.connect(self.triggerIndexUpdate)

            if createInitialLocation:
                settingsDlg.addLocation()
            if locationToAdd:
                settingsDlg.addExistingLocation(locationToAdd)
            if settingsDlg.exec():
                # Refresh config
                AppConfig.refreshConfig()
                searchLocations = IndexConfiguration.readConfig(AppConfig.appConfig())
                self.configChanged.emit(searchLocations)

    @pyqtSlot('QString')
    def addSearchLocationFromPath (self, directory: str) -> None:
        """This is called when a directory is dropped on the application. This is a shortcut to create a search location."""
        ext = FileTools.getMostCommonExtensionInDirectory (directory)
        location = IndexConfiguration.IndexConfiguration(self.tr("Search") + " '" + directory + "'", ext,  directory, "", "", IndexConfiguration.IndexMode.NoIndexWanted)

        self.openSettings (locationToAdd=location)

    @pyqtSlot()
    def updateIndex(self) -> None:
        try:
            config = AppConfig.userConfig()
        except:
            self.userConfigFailedToLoadMessage()
        else:
            searchLocations = IndexConfiguration.readConfig(config)
            displayNames = [conf.displayName() for conf in searchLocations if conf.generatesIndex()]
            from dialogs.CheckableItemsDialog import CheckableItemsDialog
            updateDialog = CheckableItemsDialog(self.tr("Choose indexes to update"),  True, self)
            for name in displayNames:
                updateDialog.addItem(name)
            updateDialog.checkAll(True)
            if updateDialog.exec():
                # The items returned are touples: (index,value)
                updateDisplayNames = [name for i, name in updateDialog.checkedItems()]
                self.triggerIndexUpdate (updateDisplayNames)

    @pyqtSlot()
    def openHelp(self) -> None:
        from dialogs.HelpViewerDialog import HelpViewerDialog
        helpDialog = HelpViewerDialog(self)
        helpDialog.setAttribute(Qt.WA_DeleteOnClose)
        helpDialog.showFile("help.html")
        helpDialog.show()

    @pyqtSlot()
    def openAbout(self) -> None:
        from dialogs.AboutDialog import AboutDialog
        aboutDialog = AboutDialog(self)
        aboutDialog.exec()

    @pyqtSlot()
    def triggerIndexUpdate (self,  updateDisplayNames: List[str]) -> None:
        try:
            self.__triggerIndexUpdate (updateDisplayNames)
        except:
            self.failedToUpdateIndexesMessage()

    def __triggerIndexUpdate (self,  updateDisplayNames: List[str]) -> None:
        r"""
        Check which indexes should be updated and trigger an asynchronous update
        This works by putting an file with the name of the index config group into %APPDATA%\CodeBeagle\IndexUpdate.
        It is picked up by UpdateIndex.py which has a special mode for this task.
        """
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
                raise RuntimeError("UpdateIndex.exe not found")

        self.__watchForIndexUpdate()

    def __watchForIndexUpdate(self) -> None:
        """Check regularily if the update finished."""
        running = self.__indexUpdateRunning()
        self.__maintainRunningIndexUpdates(running)
        if running:
            self.__showIndexUpdateInProgress(True)
            if not self.indexUpdateTimer:
                self.indexUpdateTimer = QTimer(self)
                self.indexUpdateTimer.timeout.connect(self.__checkIndexUpdateProgress)
            self.indexUpdateTimer.start(2000)

    def __checkIndexUpdateProgress (self) -> None:
        running = self.__indexUpdateRunning()
        self.__maintainRunningIndexUpdates(running)
        if not running:
            self.indexUpdateTimer.stop()
            self.__showIndexUpdateInProgress(False)
            self.__informAboutIndexUpdate("Index update finshed")

    def __indexUpdateRunning (self) -> List[str]:
        try:
            files = os.listdir(self.indexTriggerPath)
            return files
        except:
            return []

    def __maintainRunningIndexUpdates(self,  running: List[str]) -> None:
        """Informs all search pages which search locations are currently not available."""
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

    def __informAboutIndexUpdate(self,  text: str) -> None:
        pos = self.labelUpdate.parent().mapToGlobal(self.labelUpdate.pos())
        pos.setX(pos.x())
        QToolTip.showText (pos, text,  self)

    def __addAnimatedUpdateLabel (self,  hbox: QHBoxLayout,  text: str) -> QWidget:
        widget = AnimatedProgressWidget (self, text)
        widget.hide()
        hbox.insertWidget(self.indexOfUpdateButton,  widget)
        return widget

    def __showIndexUpdateInProgress (self, bInProgress: bool) -> None:
        if not self.labelUpdate:
            self.labelUpdate = self.__addAnimatedUpdateLabel (self.cornerWidgetLayout(),  self.tr("Update running..."))
        if bInProgress:
            self.buttonUpdate.hide()
            self.labelUpdate.show()
            self.buttonSettings.setEnabled(False)
            self.labelUpdate.start()
        else:
            self.labelUpdate.stop()
            self.buttonUpdate.show()
            self.labelUpdate.hide()
            self.buttonSettings.setEnabled(True)

    def newTabAdded(self,  prevTabWidget:SearchPage, newTabWidget:SearchPage) -> None:
        """
        This is called by the base class when a new tab is added. We use this to connect the request for a new search
        to open up in a new tab.
        """
        newTabWidget.newSearchRequested.connect (self.searchInNewTab)
        newTabWidget.searchFinished.connect (self.changeTabName)
        newTabWidget.documentShown.connect (self.requestWindowTitleChange)
        self.requestWindowTitleChange.emit("")
        newTabWidget.ui.sourceViewer.directoryDropped.connect(self.addSearchLocationFromPath)
        self.configChanged.connect (newTabWidget.reloadConfig)
        # Initially reload the config to pass the current search locations to the search page
        newTabWidget.reloadConfig(IndexConfiguration.readConfig(AppConfig.appConfig()))

        # Copy search location from previous search page
        if prevTabWidget:
            newTabWidget.setCurrentSearchLocation(prevTabWidget.currentConfigName)

    @pyqtSlot(str, str)
    def searchInNewTab (self, text: str, searchLocationName: str) -> None:
        searchPage = self.addNewTab ()
        searchPage.setCurrentSearchLocation(searchLocationName)
        searchPage.searchForText(text)

    @pyqtSlot(QWidget, str)
    def changeTabName (self,  searchPage: SearchPage,  text: str) -> None:
        index = self.indexOf(searchPage)
        if -1 != index:
            if text:
                self.setTabText(index, text)
            else:
                self.setTabText(index, self.tr("Search"))

    @pyqtSlot()
    def initialSetup(self) -> None:
        if hintWouldBeShown("noLocations"):
            locations = IndexConfiguration.readConfig(AppConfig.appConfig())
            if not locations:
                text = self.tr(userHintInitialSetup)
                res = showUserHint (self, "noLocations",  self.tr("Initial setup"), text,  ButtonType.Yes,  True,  ButtonType.No)
                if res == ButtonType.Yes:
                    self.openSettings(createInitialLocation=True)
        if AppConfig.appConfig().theme != AppConfig.darkTheme:
            text = self.tr(userHintDarkTheme)
            if showUserHint (self, "darkTheme",  self.tr("Dark theme"), text,  ButtonType.Yes, True, ButtonType.No) == ButtonType.Yes:
                AppConfig.appConfig().theme = AppConfig.darkTheme
                AppConfig.saveUserConfig(AppConfig.appConfig())
                self.__restartCodeBeagle()
                sys.exit(0)

    def __restartCodeBeagle(self) -> None:
        import subprocess
        runningInInterpreter = os.path.basename(sys.executable).lower().startswith("python")
        if runningInInterpreter:
            subprocess.Popen ([sys.executable, "CodeBeagle.pyw"])
        else:
            if os.path.exists("CodeBeagle.exe"):
                si = subprocess.STARTUPINFO()
                si.dwFlags = subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE
                subprocess.Popen (["CodeBeagle.exe"], startupinfo=si)
            else:
                raise RuntimeError("CodeBeagle.exe not found")

    def userConfigFailedToLoadMessage(self) -> None:
        StackTraceMessageBox.show(self,
                                  self.tr("Failed to load user config"),
                                  self.tr("The user config file could not be loaded from the user profile"))

    def failedToUpdateIndexesMessage(self) -> None:
        StackTraceMessageBox.show(self,
                                  self.tr("Error during index update"),
                                  self.tr("The update process failed to update the desired indexes"))