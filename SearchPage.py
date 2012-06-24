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
from Ui_SearchPage import Ui_SearchPage 
import AsynchronousTask
import PathVisualizerDelegate
import FullTextIndex
import SearchMethods
import CustomContextMenu
import UserHintDialog
import AppConfig
from ExceptionTools import exceptionAsString

userHintUseWildcards = """
<p align='justify'>The search matches words exactly as entered. In order to match words with unknown parts use the asterisk as wildcard. 
E.g. <b>part*</b> matches also <b>partial</b>. See the help for more information about the search syntax.</p>
"""

# Returns the first difference in two iterables
def firstDifference(s1,s2):
    for (i,c1),c2 in zip(enumerate(s1),s2):
        if c1 != c2:
            return i
    return min(len(s1),len(s2))

def getCustomScriptsFromDisk():
    return [s for s in os.listdir("scripts") if os.path.splitext(s)[1].lower() == ".script"]

class StringListModel(QAbstractListModel): 
    def __init__(self, filelist,  parent=None): 
        super(StringListModel, self).__init__(parent)
        self.filelist = filelist
        self.sizeHint = None
        self.cutLeft = self.__computeCutLeft()
        
    def setSizeHint(self, sizeHint):
        self.sizeHint = sizeHint
        
    # If all entries in the list start with the same directory we don't need to display this prefix.
    def __computeCutLeft (self):
        if len(self.filelist)<2:
            return None
        first = os.path.split(self.filelist[0])[0]
        last = os.path.split(self.filelist[-1])[0]
        firstDiff = firstDifference(first, last)
        if firstDiff != None:
            # Only cut full directories - go back to the last path seperator
            common = first[:firstDiff]
            lastSep = common.rfind(os.path.sep)
            if lastSep != -1:
                return lastSep+1
            return firstDiff
        return len(first) # The whole string is equal
 
    def rowCount(self, parent=QModelIndex()): 
        return len(self.filelist) 
 
    def data(self, index, role): 
        if not index.isValid():
            return None 
        if role == Qt.DisplayRole:
            if self.cutLeft:
                return "..."+self.filelist[index.row()][self.cutLeft:]
            else:
                return self.filelist[index.row()]
        if role == Qt.UserRole:
            return self.filelist[index.row()]
        if role == Qt.SizeHintRole:
            return self.sizeHint
        if role == Qt.ToolTipRole and self.cutLeft:
            name = self.filelist[index.row()] 
            fileinfo =QFileInfo(name)
            lastmodified = fileinfo.lastModified().toString()
            # replace with slahses as this will not break the tooltip after the drive letter
            return name.replace("\\", "/") + "<br/>" + lastmodified 
        return None

class SearchPage (QWidget):
    # Triggered when a new search tab is requested which should be opened using a given search string
    # First parameter is the search string, the second the display name of the search configuration (IndexConfiguration)
    newSearchRequested = pyqtSignal('QString', 'QString')
    # Triggered when a search is started
    searchFinished = pyqtSignal('QWidget', 'QString')
    
    def __init__ (self, parent):
        super (SearchPage, self).__init__(parent)
        self.ui = Ui_SearchPage()
        self.ui.setupUi(self)
        self.ui.frameSearch.setProperty("shadeBackground", True) # fill background with gradient as defined in style sheet
        self.ui.frameResult.setProperty("shadeBackground", True) # fill background with gradient as defined in style sheet
        QObject.connect(self.ui.comboSearch.lineEdit(), SIGNAL("returnPressed()"), self.performSearch)
        QObject.connect(self.ui.comboFolderFilter.lineEdit(), SIGNAL("returnPressed()"), self.performSearch)
        QObject.connect(self.ui.comboExtensionFilter.lineEdit(), SIGNAL("returnPressed()"), self.performSearch)
        self.ui.listView.setItemDelegate(PathVisualizerDelegate.PathVisualizerDelegate(self.ui.listView))
        QObject.connect(self.ui.sourceViewer, SIGNAL("selectionFinishedWithKeyboardModifier(QString,int)"),self.newSearchBasedOnSelection) 
        self.ui.sourceViewer.noPreviousMatch.connect(self.previousFile)
        self.ui.sourceViewer.noNextMatch.connect(self.nextFile)
        self.perfReport = None
        self.indexConfig = []
        self.currentConfigName = AppConfig.appConfig().defaultLocation # Display name of current config
        self.commonKeywordMap = self.__loadCommonKeywordMap()
        # Hide the custom scripts button if there are no custom scripts on disk
        if len(getCustomScriptsFromDisk())==0:
            self.ui.buttonCustomScripts.hide()
            
    def __loadCommonKeywordMap(self):
        try:
            return FullTextIndex.buildMapFromCommonKeywordFile (AppConfig.appConfig().commonKeywords)
        except:
            return {}
            
    def focusInEvent (self, event):
        self.ui.comboSearch.setFocus(Qt.ActiveWindowFocusReason)
          
    @pyqtSlot(list)
    def reloadConfig (self,searchLocationList):
        # updateSearchLocationList rebuilds the list which modifies self.currentConfigName so the current config must be preserved
        backupCurrentConfigName = self.currentConfigName 
        self.__updateSearchLocationList (searchLocationList)
        self.setCurrentSearchLocation (backupCurrentConfigName)
        self.ui.sourceViewer.reloadConfig()
        
    def __updateSearchLocationList(self,  searchLocationList):
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
            
    def setCurrentSearchLocation(self, searchLocationName):
        for i, config in enumerate (self.searchLocationList):
            if searchLocationName == config.displayName():
                self.ui.comboLocation.setCurrentIndex(i)
                self.currentConfigName = searchLocationName
                return
        # Nothing found, select first one 
        if len(self.searchLocationList) > 0:
            self.ui.comboLocation.setCurrentIndex (0)
            self.currentConfigName = self.searchLocationList[0].displayName()
        else:
            self.ui.comboLocation.setCurrentIndex(-1)
            self.currentConfigName = ""
            
    @pyqtSlot('QString')
    def currentLocationChanged(self, currentConfigName):
        self.currentConfigName = currentConfigName
        
    @pyqtSlot(QModelIndex)
    def fileSelected (self,  index):
        name = index.data(Qt.UserRole)
        self.showFile (name)
        
    def showFile (self, name,  isSourceCode=True):
        if self.ui.sourceViewer.currentFile() != name:
            self.ui.sourceViewer.showFile(name)
        
    @pyqtSlot()
    def nextFile (self):
        self.__changeSelectedFile (1)
        
    @pyqtSlot()
    def previousFile (self):
        self.__changeSelectedFile (-1)
                
    def __changeSelectedFile (self, increment):
        index = self.ui.listView.currentIndex()
        if index.isValid():
            nextIndex = self.ui.listView.model().index(index.row()+increment, 0)
            if nextIndex.isValid():
                self.ui.listView.setCurrentIndex(nextIndex)
                self.ui.listView.activated.emit(nextIndex)
        
    @pyqtSlot('QString', int)
    def newSearchBasedOnSelection (self, text, modifiers):
        if modifiers & Qt.ControlModifier:
            if modifiers & Qt.AltModifier:
                # Search in the same search page
                self.searchForText(text)
            else:
                # Search in a new tab
                self.newSearchRequested.emit(text,  self.ui.comboLocation.currentText())
        
    def getSearchParameterFromUI (self):
        strSearch = self.ui.comboSearch.currentText().strip()
        strFolderFilter = self.ui.comboFolderFilter.currentText().strip()
        strExtensionFilter = self.ui.comboExtensionFilter.currentText().strip()
        bCaseSensitive = self.ui.checkCaseSensitive.checkState() == Qt.Checked
        return (strSearch, strFolderFilter,  strExtensionFilter,  bCaseSensitive)
        
    # Returns the search parameters from the UI and the current search configuration (IndexConfiguration) object
    def __prepareSearch (self):
        self.__updateSearchResult(SearchMethods.ResultSet()) # clear current results
        
        self.currentConfigName = self.ui.comboLocation.currentText()
        i = self.ui.comboLocation.currentIndex()
        indexConf = self.ui.comboLocation.model().index(i, 0).data(Qt.UserRole)
        params = self.getSearchParameterFromUI()
        return (params,  indexConf)
        
    @pyqtSlot()
    def execCustomScripts (self):
        scripts = getCustomScriptsFromDisk()
        menu = QMenu()
        actions = []
        for script in scripts:
            actions.append(menu.addAction(os.path.splitext(script)[0]))
        pos = self.mapToGlobal(self.ui.buttonCustomScripts.pos())
        pos += QPoint(0,  self.ui.buttonCustomScripts.height())
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
            result = SearchMethods.customSearch (self, script,  params, indexConf,  self.commonKeywordMap)
        except:
            self.reportCustomSearchFailed ()
        else:
            self.__updateSearchResult(result)
        
    def searchForText (self,  text):
        self.ui.comboSearch.setEditText(text)
        self.performSearch()
        
    @pyqtSlot()
    def performSearch (self):
        params, indexConf = self.__prepareSearch ()
        if not indexConf:
            return
        
        try:
            result = SearchMethods.search (self, params, indexConf,  self.commonKeywordMap)
        except:
            self.reportFailedSearch(indexConf)
        else:
            self.__updateSearchResult(result)
            text = self.trUtf8(userHintUseWildcards)
            UserHintDialog.showUserHint (self, "useWildcards",  self.trUtf8("Try using wildcards"), text,  UserHintDialog.OK)
        
    def __updateSearchResult (self, result):
        if result.label:
            self.searchFinished.emit(self, result.label)
        self.perfReport = result.perfReport
        self.ui.sourceViewer.setSearchData (result.searchData)
        self.ui.labelMatches.setText("%u " % (len(result.matches), ) + self.trUtf8("matches"))
        model = StringListModel(result.matches)
        sizeHint = self.ui.listView.itemDelegate().computeSizeHint(result.matches,  model.cutLeft)
        model.setSizeHint(sizeHint)
        self.ui.listView.setModel(model)
        
    @pyqtSlot(QModelIndex)
    def openFileWithSystem(self, index):
        name = index.data(Qt.UserRole)
        url = QUrl.fromLocalFile (name)
        QDesktopServices.openUrl (url)

    @pyqtSlot()
    def performanceInfo (self):
        if not self.perfReport:
            return
        QMessageBox.information(self, self.trUtf8("Performance info"), str(self.perfReport),
            QMessageBox.StandardButtons(QMessageBox.Ok), QMessageBox.Ok)
            
    @pyqtSlot()
    def exportMatches(self):
        model = self.ui.listView.model()
        if not model or model.rowCount()==0:
            return
        result = ""
        for row in range(model.rowCount()):
            index = model.index(row, 0)
            if result:
                result += "\n"
            result += model.data(index, Qt.UserRole)
            
        exportFile = QFileDialog.getSaveFileName(
            self,
            self.trUtf8("Export matches"),
            self.trUtf8("export.txt"),
            self.trUtf8("txt"))
        if not exportFile:
            return
            
        with open (exportFile, "w",  -1,  "utf_8_sig") as output:
            output.write(result)
            
    @pyqtSlot(QPoint)
    def contextMenuRequested(self, pos):
        fullpath = self.__getSelectedFile()
        if not fullpath:
            return
        name = os.path.split(fullpath)[1]
        menu = QMenu()
        menu.addAction(self.trUtf8("Copy &full path"),  lambda: self.__copyFullPath(fullpath))
        menu.addAction(self.trUtf8("Copy &path of containing folder"),  lambda: self.__copyPathOfContainingFolder(fullpath))
        menu.addAction(self.trUtf8("Copy file &name"),  lambda: self.__copyFileName(name))
        menu.addAction(self.trUtf8("Open containing f&older"),  lambda: self.__browseToFolder(fullpath))
        menu.addAction(self.trUtf8("Search for") + " '" + name + "'",  lambda: self.__searchForFileName(name))
        
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
            
    def __copyFullPath(self,  name):
        clipboard = QApplication.clipboard()
        clipboard.setText(name)
        
    def __copyPathOfContainingFolder(self,  name):
        clipboard = QApplication.clipboard()
        clipboard.setText(os.path.split(name)[0])
     
    def __copyFileName(self,  name):
        clipboard = QApplication.clipboard()
        clipboard.setText(name)   
        
    def __browseToFolder (self,  name):
        url = QUrl.fromLocalFile (os.path.split(name)[0])
        QDesktopServices.openUrl (url)
    
    def __searchForFileName (self,  name):
        self.newSearchRequested.emit(name,  self.ui.comboLocation.currentText())
        
    def __getSelectedFile (self):
        index = self.ui.listView.currentIndex ()
        if not index.isValid():
            return None
        return index.data(Qt.UserRole)
        
    def __getSelectedFiles (self):
        filenames = []
        indexes = self.ui.listView.selectedIndexes ()
        for index in indexes:
            if index.isValid():
                filenames.append (index.data(Qt.UserRole))
        return filenames

    @pyqtSlot(CustomContextMenu.CustomContextMenu)
    def reportCustomContextMenuFailed (self,  contextMenuError):
        if not contextMenuError.exception:
            QMessageBox.warning(self,
                self.trUtf8("Custom context menu failed"),
                self.trUtf8("Failed to start '") + contextMenuError.program + self.trUtf8("' for:\n") + "\n".join(contextMenuError.failedFiles),
                QMessageBox.StandardButtons(QMessageBox.Ok))
        else:
            QMessageBox.warning(self,
                self.trUtf8("Custom context menu failed"),
                self.trUtf8("The custom context menu script '") + contextMenuError.program + self.trUtf8("' failed to execute:\n") + contextMenuError.exception,
                QMessageBox.StandardButtons(QMessageBox.Ok))

    # Show the user possible reason why the search threw an exception
    def reportFailedSearch(self, indexConf):
        if indexConf.generateIndex:
            QMessageBox.warning(self,
                self.trUtf8("Search failed"),
                self.trUtf8("""Maybe the index has not been generated yet or is not accessible?"""),
                QMessageBox.StandardButtons(QMessageBox.Ok))
        else:
            QMessageBox.warning(self,
                self.trUtf8("Search failed"),
                self.trUtf8("""Please check that the search location exists and is accessible."""),
                QMessageBox.StandardButtons(QMessageBox.Ok))
            
    def reportCustomSearchFailed (self):
        QMessageBox.warning(self,
                self.trUtf8("Custom search failed"),
                self.trUtf8("Custom search scripts are written in Python. The following exception info might help to find the problem:\n") + exceptionAsString(),
                QMessageBox.StandardButtons(QMessageBox.Ok))


    
