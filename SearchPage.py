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
from Ui_SearchPage import Ui_SearchPage 
import PathVisualizerDelegate
import ProgressBar
import FullTextIndex
from AppConfig import appConfig
import IndexConfiguration
import os

# Returns the first difference in two iterables
def firstDifference(s1,s2):
    for (i,c1),c2 in zip(enumerate(s1),s2):
        if c1 != c2:
            return i
    return min(len(s1),len(s2))
            
# Remove duplicates and sort
def removeDupsAndSort(matches):
    uniqueMatches = set()
    for m in matches:
        uniqueMatches.add(m)
    matches = [m for m in uniqueMatches]
    matches.sort()
    return matches
    
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
            return self.filelist[index.row()]
        return None
        
class AsynchronousTask (QThread):
    def __init__(self,  function , *args):
        super(AsynchronousTask, self).__init__(None) # Called with None to get rid of the thread once the python object is destroyed
        self.function = function
        self.args = args
        self.result = None
        
    def run(self):
        self.result = self.function (*self.args)

def performAsyncTask (parent,  func,  *args):
    progress = None
    try:
        progress = ProgressBar.ProgressBar(parent)
        progress.show()
        
        searchTask = AsynchronousTask (func,  *args)
        QObject.connect(searchTask,  SIGNAL("finished()"),  progress.close)
        QObject.connect(searchTask,  SIGNAL("terminated()"),  progress.close)
        searchTask.start()
        progress.exec()
        searchTask.wait()
        
        return searchTask.result
    finally:
        if progress:
            progress.close()
            
class ScriptSearchData:
    def __init__(self,  reExpr):
        self.reExpr = reExpr
        
    # Yields all matches in str. Each match is returned as the touple (position,length)
    def matches (self,  str):
        if not self.reExpr:
            return
        cur = 0
        while True:
            result = self.reExpr.search(str, cur)
            if result:
                startPos, endPos = result.span()
                yield (startPos,  endPos-startPos)
                cur = endPos
            else:
                return

class SearchPage (QWidget):
    # Triggered when a new search tab is requested which should be opened using a given search string
    # First parameter is the search string, the second the index of the database
    newSearchRequested = pyqtSignal('QString', int)
    # Triggered when a search is started
    searchStarted = pyqtSignal('QWidget', 'QString')
    
    def __init__ (self, parent):
        super (SearchPage, self).__init__(parent)
        self.ui = Ui_SearchPage()
        self.ui.setupUi(self)
        QObject.connect(self.ui.comboSearch.lineEdit(), SIGNAL("returnPressed()"), self.performSearch)
        QObject.connect(self.ui.comboFolderFilter.lineEdit(), SIGNAL("returnPressed()"), self.performSearch)
        QObject.connect(self.ui.comboExtensionFilter.lineEdit(), SIGNAL("returnPressed()"), self.performSearch)
        self.ui.listView.setItemDelegate(PathVisualizerDelegate.PathVisualizerDelegate(self.ui.listView))
        self.perfReport = None
        self.updateDatabaseList()
        QObject.connect(self.ui.sourceViewer, SIGNAL("selectionFinishedWithKeyboardModifier(QString,int)"),self.newSearchBasedOnSelection) 
        # Hide the custom scripts button if there are no custom scripts on disk
        if len(getCustomScriptsFromDisk())==0:
            self.ui.buttonCustomScripts.hide()
        
    def updateDatabaseList(self):
        self.indexConfig = IndexConfiguration.readConfig(appConfig())
        if len(self.indexConfig) <=1:
            self.ui.comboDB.hide()
            self.ui.labelDB.hide()
        for config in self.indexConfig:
            self.ui.comboDB.insertItem(1000, config.name(), config.indexdb)
            
    def setCurrentDatabase(self,  index):
        self.ui.comboDB.setCurrentIndex(index)
        
    def focusInEvent (self, event):
        self.ui.comboSearch.setFocus(Qt.ActiveWindowFocusReason)
        
    @pyqtSlot('QString', int)
    def newSearchBasedOnSelection (self, text, modifiers):
        if modifiers & Qt.ControlModifier:
            if modifiers & Qt.AltModifier:
                # Search in the same search page
                self.searchForText(text)
            else:
                # Search in a new tab
                self.newSearchRequested.emit(text,  self.ui.comboDB.currentIndex())
        
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
        
        params = self.getSearchParameterFromUI()
        self.updateSearchResult([])
        if not len(params[0]):
            return
        result = performAsyncTask (self,  self.execCustomScriptAsync, os.path.join("scripts", script), params)
        if result:
            matches, highlight, label = result
            matches = removeDupsAndSort(matches)
            if highlight:
                self.ui.sourceViewer.setSearchData (ScriptSearchData (highlight))
            else:
                # Highlight  by default the query
                self.ui.sourceViewer.setSearchData (FullTextIndex.SearchQuery (params[0], "",  "",  params[3]))
            self.searchStarted.emit(self, label)
            self.updateSearchResult(matches)
        
    # Executes a custom search script from disk. The script receives a locals dictionary with all neccessary
    # search parameters and returns its result in the variable "result". The variable "highlight" must be set
    # to a regular expression which is used to highlight the matches in the result.
    def execCustomScriptAsync (self,  script,  params):
        import re
        query, folders, extensions, caseSensitive = params
        def performSearch (strSearch,  strFolderFilter="",  strExtensionFilter="",  bCaseSensitive=False):
            searchData = FullTextIndex.SearchQuery (strSearch,  strFolderFilter,  strExtensionFilter,  bCaseSensitive)
            return self.performSearchAsync(searchData)
        localsDict = { "re":  re, 
                            "performSearch" : performSearch, 
                           "query" : query,  
                           "folders" : folders,  
                           "extensions" : extensions,  
                           "caseSensitive" : caseSensitive,  
                           "results" : [],  
                           "highlight" : None,  
                           "label" : "Custom script"}
        with open(script) as file: 
            code = compile(file.read(), script, 'exec')
        exec(code,  globals(),  localsDict)
        return (localsDict["results"],  localsDict["highlight"],  localsDict["label"])
        
    @pyqtSlot(QModelIndex)
    def fileSelected (self,  index):
        name = self.ui.listView.model().data(index, Qt.UserRole)
        self.showFile (name)
        
    def showFile (self, name,  format="source"):
        if self.ui.sourceViewer.currentFile() != name:
            self.ui.sourceViewer.showFile(name,  format)
        
    def searchForText (self,  text):
        self.ui.comboSearch.setEditText(text)
        self.performSearch()
        
    def getSearchParameterFromUI (self):
        strSearch = self.ui.comboSearch.currentText().strip()
        strFolderFilter = self.ui.comboFolderFilter.currentText().strip()
        strExtensionFilter = self.ui.comboExtensionFilter.currentText().strip()
        bCaseSensitive = self.ui.checkCaseSensitive.checkState() == Qt.Checked
        return (strSearch, strFolderFilter,  strExtensionFilter,  bCaseSensitive)
        
    @pyqtSlot()
    def performSearch (self):
        strSearch, strFolderFilter,  strExtensionFilter, bCaseSensitive = self.getSearchParameterFromUI()
        self.searchStarted.emit(self, strSearch)
        self.updateSearchResult([])
        if not len(strSearch):
            return
        searchData = FullTextIndex.SearchQuery (strSearch,  strFolderFilter,  strExtensionFilter,  bCaseSensitive)
        self.ui.sourceViewer.setSearchData (searchData)
        
        result = performAsyncTask (self,  self.performSearchAsync,  searchData)
        if result:
            self.updateSearchResult(result)
            
    def performSearchAsync(self,  searchData):
        self.perfReport = FullTextIndex.PerformanceReport()
        with self.perfReport.newAction("Init database"):
            i = self.ui.comboDB.currentIndex()
            modelIndex = self.ui.comboDB.model().index(i, 0)
            indexdb = self.ui.comboDB.model().data(modelIndex, Qt.UserRole)
            fti = FullTextIndex.FullTextIndex(indexdb)
        return fti.search (searchData,  self.perfReport)
        
    def updateSearchResult (self, data):
        if not data:
            data = []
        self.ui.labelMatches.setText("%u " % (len(data), ) + self.trUtf8("matches"))
        model = StringListModel(data)
        sizeHint = self.ui.listView.itemDelegate().computeSizeHint(data,  model.cutLeft)
        model.setSizeHint(sizeHint)
        self.ui.listView.setModel(model)
        
    @pyqtSlot(QModelIndex)
    def openFileWithSystem(self, index):
        name = self.ui.listView.model().data(index, Qt.UserRole)
        url = QUrl.fromLocalFile (name)
        QDesktopServices.openUrl (url)
        
    @pyqtSlot(QPoint)
    def contextMenuRequested(self, pos):
        menu = QMenu()
        menu.addAction(self.trUtf8("Copy &full path"),  self.copyFullPath)
        menu.addAction(self.trUtf8("Copy &path of containing folder"),  self.copyPathOfContainingFolder)
        menu.addAction(self.trUtf8("Copy file &name"),  self.copyFileName)
        menu.addAction(self.trUtf8("Open containing f&older"),  self.browseToFolder)
        menu.exec(self.ui.listView.mapToGlobal(pos))

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
            
    @pyqtSlot()
    def copyFullPath(self):
        name = self.getSelectedFile()
        if not name:
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(name)
        
    @pyqtSlot()
    def copyPathOfContainingFolder(self):
        name = self.getSelectedFile()
        if not name:
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(os.path.split(name)[0])
     
    @pyqtSlot()
    def copyFileName(self):
        name = self.getSelectedFile()
        if not name:
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(os.path.split(name)[1])   
        
    @pyqtSlot()
    def browseToFolder (self):
        name = self.getSelectedFile()
        if not name:
            return
        url = QUrl.fromLocalFile (os.path.split(name)[0])
        QDesktopServices.openUrl (url)
        
        # Would be nice to select the file using shell API:
        #ITEMIDLIST *pidl = ILCreateFromPath(filename);
        #if(pidl) {
        #    SHOpenFolderAndSelectItems(pidl,0,0,0);
        #    ILFree(pidl);
        
    def getSelectedFile (self):
        index = self.ui.listView.currentIndex ()
        if not index.isValid():
            return None
        return self.ui.listView.model().data(index, Qt.UserRole)


    
