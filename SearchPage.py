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
from typing import List, Tuple, Optional, cast
from enum import IntEnum
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QPoint, QUrl, QModelIndex, QSettings
from PyQt5.QtGui import QFont, QDesktopServices, QShowEvent, QFocusEvent
from PyQt5.QtWidgets import QFrame, QWidget, QApplication, QMenu, QMessageBox, QFileDialog, QHBoxLayout, QSpacerItem, QSizePolicy
from tools import AsynchronousTask
from dialogs.UserHintDialog import showUserHint, ButtonType
from dialogs.RegExTesterDlg import RegExTesterDlg
from dialogs import StackTraceMessageBox
import PathVisualizerDelegate
from fulltextindex import FullTextIndex
from fulltextindex import Query
from fulltextindex.IndexConfiguration import IndexConfiguration
import SearchMethods
import CustomContextMenu
import AppConfig
from StringListModel import StringListModel
from Ui_SearchPage import Ui_SearchPage

userHintUseWildcards = """
<p align='justify'>The search matches words exactly as entered. In order to match words with unknown parts use the asterisk as wildcard.
E.g. <b>part*</b> matches also <b>partial</b>. See the help for more information about the search syntax.</p>
"""

userHintContentNotIndexed = """
<p align='justify'>The file content is not indexed. Try indexing the content if the search performance is not good enough.</p>
"""

userHintFileNameNotIndexed = """
<p align='justify'>The file names are not indexed. Try indexing file names if the search performance is not good enough.</p>
"""

def getCustomScriptsFromDisk() -> List[str]:
    return [s for s in os.listdir("scripts") if os.path.splitext(s)[1].lower() == ".script"]

SearchParams = Tuple[str, str, str, bool]

class SearchType(IntEnum):
    SearchContent = 1
    SearchName = 2

class SearchPage (QWidget):
    # Triggered when a new search tab is requested which should be opened using a given search string
    # First parameter is the search string, the second the display name of the search configuration (IndexConfiguration)
    newSearchRequested = pyqtSignal(str, str)
    # Triggered when a search has finished
    searchFinished = pyqtSignal(QWidget, str)
    # Triggered whenever the view becomes visible and whenever the current file changes
    documentShown = pyqtSignal(str)

    def __init__ (self, parent: QWidget) -> None:
        super ().__init__(parent)
        self.ui = Ui_SearchPage()
        self.ui.setupUi(self)
        self.ui.frameSearch.setProperty("shadeBackground", True) # fill background with gradient as defined in style sheet
        self.ui.frameResult.setProperty("shadeBackground", True) # fill background with gradient as defined in style sheet
        self.ui.listView.setItemDelegate(PathVisualizerDelegate.PathVisualizerDelegate(self.ui.listView))
        self.ui.listView.activated.connect(self.fileSelected)
        self.ui.listView.doubleClicked.connect(self.openFileWithSystem)
        self.ui.listView.customContextMenuRequested.connect(self.contextMenuRequested)
        self.ui.listView.clicked.connect(self.fileSelected)
        self.ui.comboSearch.lineEdit().returnPressed.connect(self.performSearch)
        self.ui.comboFolderFilter.lineEdit().returnPressed.connect(self.performSearch)
        self.ui.comboExtensionFilter.lineEdit().returnPressed.connect(self.performSearch)
        self.ui.sourceViewer.selectionFinishedWithKeyboardModifier.connect(self.newSearchBasedOnSelection)
        self.ui.sourceViewer.noPreviousMatch.connect(self.previousFile)
        self.ui.sourceViewer.noNextMatch.connect(self.nextFile)
        self.ui.matchesOverview.selectionFinishedWithKeyboardModifier.connect(self.newSearchBasedOnSelection)
        self.ui.buttonRegEx.clicked.connect(self.showRegExTester)
        self.ui.comboLocation.currentIndexChanged[str].connect(self.currentLocationChanged) # pylint: disable=unsubscriptable-object
        self.ui.buttonSwitchView.clicked.connect(self.switchView)
        self.ui.buttonSearch.clicked.connect(self.performSearch)
        self.ui.buttonLockResultSet.clicked.connect(self.lockResultSet)
        self.ui.buttonInfo.clicked.connect(self.performanceInfo)
        self.ui.buttonExport.clicked.connect(self.exportMatches)
        self.ui.buttonCustomScripts.clicked.connect(self.execCustomScripts)
        self.ui.buttonChangeSearchType.clicked.connect(self.changeSearchTypeMenu)

        self.ui.splitter.setSizes((1, 2)) # distribute splitter space 1:2

        self.perfReport: Optional[FullTextIndex.PerformanceReport] = None
        self.searchType: SearchType = SearchType.SearchContent
        self.searchLocationList: List[IndexConfiguration] = []
        self.currentConfigName = self.__chooseInitialLocation ()
        self.unavailableConfigName: str = ""
        self.commonKeywordMap = self.__loadCommonKeywordMap()
        self.matches: FullTextIndex.SearchResult = []
        self.sourceFont: QFont = None
        self.lockedResultSet: Optional[FullTextIndex.SearchResult] = None # matches are filtered with this set
        # Hide the custom scripts button if there are no custom scripts on disk
        if not getCustomScriptsFromDisk():
            self.ui.buttonCustomScripts.hide()
        # Hide the performance info button if showPerformanceButton is false
        if not AppConfig.appConfig().showPerformanceButton:
            self.ui.buttonInfo.hide()

        # Move some elements of the search bar to a second row if the screen width is too small. This avoid
        # clipping errors if the widget has to paint below minimum size.
        screenGeometry = QApplication.desktop().screenGeometry()
        if screenGeometry.width() < 1200:
            self.__layoutForLowScreenWidth()

    def showEvent(self, _: QShowEvent) -> None:
        self.documentShown.emit(self.ui.sourceViewer.currentFile)

    @pyqtSlot()
    def changeSearchTypeMenu(self) -> None:
        self.ui.buttonChangeSearchType.setChecked(True)
        menu = QMenu()
        menu.setMinimumWidth(self.ui.buttonChangeSearchType.x() + self.ui.buttonChangeSearchType.width() - self.ui.buttonSearch.x())
        actions = []
        actions.append(menu.addAction("Find content", lambda: self.setSearchType(SearchType.SearchContent)))
        actions.append(menu.addAction("Find name", lambda: self.setSearchType(SearchType.SearchName)))
        pos = self.mapToGlobal(self.ui.widgetSearch.pos())
        pos += QPoint(0, self.ui.buttonSearch.height())
        menu.exec(pos)
        self.ui.buttonChangeSearchType.setChecked(False)

    def setSearchType(self, searchType: SearchType) -> None:
        if self.searchType == searchType:
            return

        self.searchType = searchType
        self.ui.buttonCustomScripts.setEnabled(self.searchType == SearchType.SearchContent)
        self.ui.buttonSwitchView.setEnabled(self.searchType == SearchType.SearchContent)
        if self.searchType == SearchType.SearchName:
            self.switchView(False)
            self.ui.buttonSwitchView.setChecked(False)
            self.ui.buttonSearch.setText("Find name")
        else:
            self.ui.buttonSearch.setText("Find content")

    # Return the display name of the initial config. This is either the configured default location or if there is no default location
    # the last used location.
    def __chooseInitialLocation (self) -> str:
        configName = cast(str,AppConfig.appConfig().defaultLocation) # Display name of current config
        if not configName:
            configName = cast(str,AppConfig.lastUsedConfigName())
        return configName

    def __loadCommonKeywordMap(self) -> FullTextIndex.CommonKeywordMap:
        try:
            return FullTextIndex.buildMapFromCommonKeywordFile (AppConfig.appConfig().commonKeywords)
        except:
            return {}

    def focusInEvent (self, _: QFocusEvent) -> None:
        self.ui.comboSearch.setFocus(Qt.ActiveWindowFocusReason)

    @pyqtSlot(bool)
    def switchView(self, bChecked: bool) -> None:
        if bChecked:
            self.ui.stackedWidget.setCurrentIndex(1)
            self.ui.matchesOverview.activate()
        else:
            self.ui.stackedWidget.setCurrentIndex(0)

    def __updateSourceFont (self) -> QFont:
        if not self.sourceFont:
            self.sourceFont = QFont()

        config = AppConfig.appConfig().SourceViewer

        # Apply font and tab changes (if any)
        if self.sourceFont.family().lower() != config.FontFamily.lower() or self.sourceFont.pointSize() != config.FontSize:
            self.sourceFont.setFamily(config.FontFamily)
            self.sourceFont.setPointSize(config.FontSize)

        return self.sourceFont

    @pyqtSlot(list)
    def reloadConfig (self, searchLocationList: List[IndexConfiguration]) -> None:
        # updateSearchLocationList rebuilds the list which modifies self.currentConfigName so the current config must be preserved
        backupCurrentConfigName = self.currentConfigName
        self.__updateSearchLocationList (searchLocationList)
        if self.unavailableConfigName and self.setCurrentSearchLocation (self.unavailableConfigName):
            # Successfully switched backed to previous config
            self.unavailableConfigName = ""
        elif not self.setCurrentSearchLocation (backupCurrentConfigName):
            # The config is no longer available. This happens most probably during an index update. If the config becomes available later
            # we can switch back to it.
            self.unavailableConfigName = backupCurrentConfigName
        self.ui.sourceViewer.reloadConfig(self.__updateSourceFont())
        self.ui.matchesOverview.reloadConfig(self.__updateSourceFont())

    def __updateSearchLocationList(self,  searchLocationList: List[IndexConfiguration]) -> None:
        self.searchLocationList = searchLocationList
        self.ui.comboLocation.clear()
        if len(self.searchLocationList) <=1:
            self.ui.comboLocation.hide()
            self.ui.labelLocation.hide()
        else:
            self.ui.comboLocation.show()
            self.ui.labelLocation.show()
        for config in self.searchLocationList:
            self.ui.comboLocation.addItem(config.displayName(), config)

    def setCurrentSearchLocation(self, searchLocationName: str) -> bool:
        foundLocation = False
        configName = ""
        for i, config in enumerate (self.searchLocationList):
            if searchLocationName == config.displayName():
                self.ui.comboLocation.setCurrentIndex(i)
                foundLocation=True
                configName=searchLocationName

        # Nothing found, select first one or nothing if the list is empty
        if not foundLocation:
            if self.searchLocationList:
                self.ui.comboLocation.setCurrentIndex (0)
                configName = self.searchLocationList[0].displayName()
            else:
                self.ui.comboLocation.setCurrentIndex(-1)
                configName = ""

        self.currentConfigName = configName
        self.__restoreSearchTerms()

        return foundLocation

    @pyqtSlot(str)
    def currentLocationChanged(self, currentConfigName: str) -> None:
        self.currentConfigName = currentConfigName
        self.__restoreSearchTerms()

    @pyqtSlot(QModelIndex)
    def fileSelected (self,  index: QModelIndex) -> None:
        model = self.ui.listView.model()
        if model.getSelectedFileIndex() != -1:
            model.setEditorState(model.getSelectedFileIndex(), self.ui.sourceViewer.saveEditorState())
        model.setSelectedFileIndex (index.row())
        name = index.data(Qt.UserRole)
        self.showFile (name)
        self.ui.matchesOverview.scrollToFile(index.row())
        editorState = self.ui.listView.model().getEditorState(index.row())
        if editorState:
            self.ui.sourceViewer.restoreEditorState(editorState)

    def showFile (self, name: str) -> None:
        if self.ui.sourceViewer.currentFile != name:
            self.ui.sourceViewer.showFile(name)
            self.documentShown.emit(name)

    @pyqtSlot()
    def nextFile (self) -> None:
        self.__changeSelectedFile (1)

    @pyqtSlot()
    def previousFile (self) -> None:
        self.__changeSelectedFile (-1)

    def __changeSelectedFile (self, increment: int) -> None:
        index = self.ui.listView.currentIndex()
        if index.isValid():
            nextIndex = self.ui.listView.model().index(index.row()+increment, 0)
            if nextIndex.isValid():
                self.ui.listView.setCurrentIndex(nextIndex)
                self.ui.listView.activated.emit(nextIndex)

    @pyqtSlot(str, int)
    def newSearchBasedOnSelection (self, text: str, modifiers: int) -> None:
        if modifiers & Qt.ControlModifier:
            requestNewTab = False
            if modifiers & Qt.ShiftModifier or self.searchType == SearchType.SearchName:
                requestNewTab = True
            if not requestNewTab:
                # Search in the same search page
                self.searchForText(text)
            else:
                # Search in a new tab
                self.newSearchRequested.emit(text, self.ui.comboLocation.currentText())

    def getSearchParameterFromUI (self) -> SearchParams:
        strSearch = self.ui.comboSearch.currentText().strip()
        strFolderFilter = self.ui.comboFolderFilter.currentText().strip()
        strExtensionFilter = self.ui.comboExtensionFilter.currentText().strip()
        bCaseSensitive = self.ui.checkCaseSensitive.checkState() == Qt.Checked
        return (strSearch, strFolderFilter,  strExtensionFilter,  bCaseSensitive)

    def __currentIndexConf(self) -> IndexConfiguration:
        i = self.ui.comboLocation.currentIndex()
        config: IndexConfiguration = self.ui.comboLocation.model().index(i, 0).data(Qt.UserRole)
        return config

    # Returns the search parameters from the UI and the current search configuration (IndexConfiguration) object
    def __prepareSearch (self) -> Tuple[SearchParams, IndexConfiguration]:
        self.__updateSearchResult(SearchMethods.ResultSet()) # clear current results
        indexConf = self.__currentIndexConf()
        params = self.getSearchParameterFromUI()
        return (params, indexConf)

    @pyqtSlot()
    def execCustomScripts (self) -> None:
        scripts = getCustomScriptsFromDisk()
        menu = QMenu()
        actions = []
        for script in scripts:
            actions.append(menu.addAction(os.path.splitext(script)[0]))
        pos = self.mapToGlobal(self.ui.buttonCustomScripts.pos())
        pos += QPoint(0, self.ui.buttonCustomScripts.height())
        result = menu.exec(pos)
        if not result:
            return

        try:
            script = scripts[actions.index(result)]
        except ValueError:
            return

        params, indexConf = self.__prepareSearch ()
        if not indexConf:
            return

        try:
            result = SearchMethods.customSearch (self, script, params, indexConf,  self.commonKeywordMap)
        except:
            self.reportCustomSearchFailed ()
        else:
            self.__updateSearchResult(result)

    def searchForText (self,  text: str) -> None:
        self.ui.comboSearch.setEditText(text)
        self.ui.comboSearch.insertItem(0, text)
        self.performSearch()

    @pyqtSlot()
    def performSearch (self) -> None:
        params, indexConf = self.__prepareSearch ()
        if not indexConf:
            return

        AppConfig.setLastUsedConfigName(indexConf.displayName())

        try:
            if self.searchType == SearchType.SearchContent:
                result = SearchMethods.searchContent (self, params, indexConf,  self.commonKeywordMap)
            else:
                result = SearchMethods.searchFileName (self, params, indexConf)
        except Query.QueryError as error:
            self.reportQueryError(error)
        except:
            self.reportFailedSearch(indexConf)
        else:
            self.__updateSearchResult(result)
            self.__rememberSearchTerms()
            text = self.tr(userHintUseWildcards)
            if self.searchType == SearchType.SearchContent:
                showUserHint (self, "useWildcards",  self.tr("Try using wildcards"), text,  ButtonType.OK)
            if self.searchType == SearchType.SearchContent and not indexConf.isContentIndexed():
                text = self.tr(userHintContentNotIndexed)
                showUserHint (self, "contentSearchNotIndexed_" + indexConf.displayName(), self.tr("This search can be faster"), text, ButtonType.OK)
            if self.searchType == SearchType.SearchName and not indexConf.isFileNameIndexed():
                text = self.tr(userHintFileNameNotIndexed)
                showUserHint (self, "fileNameSearchNotIndexed_" + indexConf.displayName(), self.tr("This search can be faster"), text, ButtonType.OK)

    def __updateSearchResult (self, result: SearchMethods.ResultSet) -> None:
        if result.label:
            self.searchFinished.emit(self, result.label)
        self.perfReport = result.perfReport
        # Filter results if we currently have a locked result set
        if self.lockedResultSet:
            matches = FullTextIndex.intersectSortedLists (self.lockedResultSet, result.matches)
        else:
            matches = result.matches
        self.matches = matches
        self.ui.sourceViewer.setSearchData (result.searchData)
        self.ui.matchesOverview.setSearchResult(self.matches, result.searchData)
        self.ui.labelMatches.setText("%u " % (len(matches), ) + self.tr("matches"))
        model = StringListModel(matches)
        sizeHint = self.ui.listView.itemDelegate().computeSizeHint(matches,  model.cutLeft)
        model.setSizeHint(sizeHint)
        self.ui.listView.setModel(model)
        # Activate first match if enabled in config
        if AppConfig.appConfig().activateFirstMatch:
            if model.rowCount() > 0:
                index = self.ui.listView.model().index(0, 0)
                if index.isValid():
                    self.ui.listView.setCurrentIndex(index)
                    self.ui.listView.activated.emit(index)

    @pyqtSlot(bool)
    def lockResultSet (self,  bChecked: bool) -> None:
        if bChecked:
            self.lockedResultSet = self.matches[:] # copy the matches, a reference is not enough
        else:
            self.lockedResultSet = None

    @pyqtSlot(QModelIndex)
    def openFileWithSystem(self, index: QModelIndex) -> None:
        name = index.data(Qt.UserRole)
        url = QUrl.fromLocalFile (name)
        QDesktopServices.openUrl (url)

    @pyqtSlot()
    def performanceInfo (self) -> None:
        if not self.perfReport:
            return
        QMessageBox.information(self, self.tr("Performance info"), str(self.perfReport),
                                QMessageBox.StandardButtons(QMessageBox.Ok), QMessageBox.Ok)

    @pyqtSlot()
    def exportMatches(self) -> None:
        model = self.ui.listView.model()
        if not model or model.rowCount()==0:
            return
        result = ""
        for row in range(model.rowCount()):
            index = model.index(row, 0)
            if result:
                result += os.linesep
            result += model.data(index, Qt.UserRole)

        exportFile = QFileDialog.getSaveFileName(
            self,
            self.tr("Export matches"),
            self.tr("export.txt"),
            self.tr("txt"))[0] # tuple returned, selection and used filter

        if not exportFile:
            return

        with open (exportFile, "w",  -1,  "utf_8_sig") as output:
            output.write(result)

    @pyqtSlot(QPoint)
    def contextMenuRequested(self, pos: QPoint) -> None:
        files = self.__getSelectedFiles()
        if not files:
            return
        fullpath = files[0]
        name = os.path.split(fullpath)[1]
        menu = QMenu()
        menu.addAction(self.tr("Copy &full path"),  lambda: self.__copyFullPaths(files))
        if len(files)==1:
            menu.addAction(self.tr("Copy &path of containing folder"),  lambda: self.__copyPathOfContainingFolder(fullpath))
        menu.addAction(self.tr("Copy file &name"),  lambda: self.__copyFileNames(files))
        if len(files)==1:
            menu.addAction(self.tr("Open containing f&older"),  lambda: self.__browseToFolder(fullpath))
            menu.addAction(self.tr("Search for") + " '" + name + "'",  lambda: self.__searchForFileName(name))

        entries = CustomContextMenu.customMenuEntries (AppConfig.appConfig())
        for entry in entries:
            try:
                entry.executionFailed.disconnect() # will raise error if there are no connections
            except:
                pass
            entry.executionFailed.connect (self.reportCustomContextMenuFailed)
            # The default lambda argument is used to preserve the value of entry for each lambda. Otherwise all lambdas would call the last entry.execute
            # See http://stackoverflow.com/questions/2295290/what-do-lambda-function-closures-capture-in-python
            menu.addAction(entry.title,  lambda entry=entry: AsynchronousTask.execute (self, entry.execute,  self.__getSelectedFiles()))

        menu.exec(self.ui.listView.mapToGlobal(pos))

    @pyqtSlot()
    def showRegExTester(self) -> None:
        tester = RegExTesterDlg(self)
        tester.setAttribute(Qt.WA_DeleteOnClose)
        tester.show()

    def __copyFullPaths(self,  names: List[str]) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(os.linesep.join(names))

    def __copyPathOfContainingFolder(self,  name: str) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(os.path.split(name)[0])

    def __copyFileNames(self,  names: List[str]) -> None:
        clipboard = QApplication.clipboard()
        text = os.linesep.join(os.path.split(name)[1] for name in names)
        clipboard.setText(text)

    def __browseToFolder (self,  name: str) -> None:
        if os.name != "nt":
            url = QUrl.fromLocalFile (os.path.split(name)[0])
            QDesktopServices.openUrl (url)
        else:
            import subprocess
            subprocess.Popen (["explorer.exe", "/select,", name])

    def __searchForFileName (self,  name: str) -> None:
        self.newSearchRequested.emit(name,  self.ui.comboLocation.currentText())

    def __getSelectedFiles (self) -> List[str]:
        filenames = []
        indexes = self.ui.listView.selectedIndexes ()
        for index in indexes:
            if index.isValid():
                filenames.append (index.data(Qt.UserRole))
        return filenames

    def __layoutForLowScreenWidth (self) -> None:
        self.ui.frameSearch2 = QFrame(self) # type: ignore
        self.ui.frameSearch2.setProperty("shadeBackground", True) # type: ignore
        self.ui.horizontalLayout2 = QHBoxLayout(self.ui.frameSearch2) # type: ignore
        self.ui.horizontalLayout2.setContentsMargins(22, 0, 22, -1) # type: ignore
        layout = self.ui.horizontalLayout2 # type: ignore
        layout.removeWidget(self.ui.labelFolderFilter)
        layout.removeWidget(self.ui.comboFolderFilter)
        layout.removeWidget(self.ui.labelExtensionFilter)
        layout.removeWidget(self.ui.comboExtensionFilter)
        layout.removeWidget(self.ui.checkCaseSensitive)
        layout.addWidget(self.ui.labelFolderFilter)
        layout.addWidget(self.ui.comboFolderFilter)
        layout.addWidget(self.ui.labelExtensionFilter)
        layout.addWidget(self.ui.comboExtensionFilter)
        layout.addWidget(self.ui.checkCaseSensitive)
        layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.layout().insertWidget(1, self.ui.frameSearch2) # type: ignore

    def __restoreSearchTerms(self) -> None:
        currentText = self.ui.comboSearch.currentText()
        self.ui.comboSearch.clear()
        if self.currentConfigName:
            settings = QSettings(AppConfig.appCompany, AppConfig.appName)
            key = "SearchTerms_"+self.currentConfigName
            if settings.value(key):
                strList = settings.value(key)
                self.ui.comboSearch.addItems(strList)
        self.ui.comboSearch.setEditText(currentText)

    def __rememberSearchTerms(self) -> None:
        model = self.ui.comboSearch.model()
        if not model or model.rowCount()==0:
            return
        terms=[]
        for row in range(min(20,model.rowCount())):
            index = model.index(row, 0)
            terms.append(model.data(index, Qt.DisplayRole))
        settings = QSettings(AppConfig.appCompany, AppConfig.appName)
        settings.setValue("SearchTerms_"+self.currentConfigName, terms)

    @pyqtSlot(CustomContextMenu.ContextMenuError)
    def reportCustomContextMenuFailed (self, contextMenuError: CustomContextMenu.ContextMenuError) -> None:
        if not contextMenuError.exception:
            QMessageBox.warning(self,
                                self.tr("Custom context menu failed"),
                                self.tr("Failed to start '") + contextMenuError.program + self.tr("' for:\n") + "\n".join(contextMenuError.failedFiles),
                                QMessageBox.StandardButtons(QMessageBox.Ok))
        else:
            QMessageBox.warning(self,
                                self.tr("Custom context menu failed"),
                                self.tr("The custom context menu script '") + contextMenuError.program + self.tr("' failed to execute:\n") + contextMenuError.exception,
                                QMessageBox.StandardButtons(QMessageBox.Ok))

    def reportQueryError(self,  error: Query.QueryError) -> None:
        StackTraceMessageBox.show(self,
                                  self.tr("Search not possible"),
                                  str(error))

    def reportFailedSearch(self, indexConf: IndexConfiguration) -> None:
        """Show the user possible reason why the search threw an exception."""
        if indexConf.generatesIndex():
            StackTraceMessageBox.show(self,
                                      self.tr("Search failed"),
                                      self.tr("""Maybe the index has not been generated yet or is not accessible?"""))
        else:
            StackTraceMessageBox.show(self,
                                      self.tr("Search failed"),
                                      self.tr("""Please check that the search location exists and is accessible."""))

    def reportCustomSearchFailed (self) -> None:
        StackTraceMessageBox.show(self,
                                  self.tr("Custom search failed"),
                                  self.tr("Custom search scripts are written in Python. Click on 'Show details' to display the stack trace."))
