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
from Ui_SearchPage import Ui_SearchPage 
import PathVisualizerDelegate
from AppConfig import appConfig
import IndexConfiguration
import SearchMethods

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
            return self.filelist[index.row()]
        return None

class SearchPage (QWidget):
    # Triggered when a new search tab is requested which should be opened using a given search string
    # First parameter is the search string, the second the index of the database
    newSearchRequested = pyqtSignal('QString', int)
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
        self.ui.sourceViewer.noPreviousMatch.connect(self.previousMatch)
        self.ui.sourceViewer.noNextMatch.connect(self.nextMatch)
        self.perfReport = None
        self.updateDatabaseList()
        # Hide the custom scripts button if there are no custom scripts on disk
        if len(getCustomScriptsFromDisk())==0:
            self.ui.buttonCustomScripts.hide()
          
    @pyqtSlot()
    def reloadConfig (self):
        i = self.ui.comboDB.currentIndex()
        self.updateDatabaseList()
        self.ui.comboDB.setCurrentIndex(i)
        
    def updateDatabaseList(self):
        self.indexConfig = IndexConfiguration.readConfig(appConfig())
        self.ui.comboDB.clear()
        if len(self.indexConfig) <=1:
            self.ui.comboDB.hide()
            self.ui.labelDB.hide()
        else:
            self.ui.comboDB.show()
            self.ui.labelDB.show()
        for config in self.indexConfig:
            self.ui.comboDB.insertItem(1000, config.displayName(), config)
            
    def setCurrentDatabase(self,  index):
        self.ui.comboDB.setCurrentIndex (index)
        
    def focusInEvent (self, event):
        self.ui.comboSearch.setFocus(Qt.ActiveWindowFocusReason)
        
    @pyqtSlot(QModelIndex)
    def fileSelected (self,  index):
        name = index.data(Qt.UserRole)
        self.showFile (name)
        
    def showFile (self, name,  format="source"):
        if self.ui.sourceViewer.currentFile() != name:
            self.ui.sourceViewer.showFile(name,  format)
        
    @pyqtSlot()
    def nextMatch (self):
        self.changeSelectedFile (1)
        
    @pyqtSlot()
    def previousMatch (self):
        self.changeSelectedFile (-1)
                
    def changeSelectedFile (self, increment):
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
                self.newSearchRequested.emit(text,  self.ui.comboDB.currentIndex())
        
    def getSearchParameterFromUI (self):
        strSearch = self.ui.comboSearch.currentText().strip()
        strFolderFilter = self.ui.comboFolderFilter.currentText().strip()
        strExtensionFilter = self.ui.comboExtensionFilter.currentText().strip()
        bCaseSensitive = self.ui.checkCaseSensitive.checkState() == Qt.Checked
        return (strSearch, strFolderFilter,  strExtensionFilter,  bCaseSensitive)
        
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
        self.updateSearchResult(SearchMethods.ResultSet())
        
        i = self.ui.comboDB.currentIndex()
        indexConf = self.ui.comboDB.model().index(i, 0).data(Qt.UserRole)
        
        try:
            result = SearchMethods.customSearch (self, script,  params, indexConf)
        except Exception as e:
            self.reportCustomSearchFailed (e)
        else:
            self.updateSearchResult(result)
        
    def searchForText (self,  text):
        self.ui.comboSearch.setEditText(text)
        self.performSearch()
        
    @pyqtSlot()
    def performSearch (self):
        params = self.getSearchParameterFromUI()
        self.updateSearchResult(SearchMethods.ResultSet())
        
        i = self.ui.comboDB.currentIndex()
        indexConf = self.ui.comboDB.model().index(i, 0).data(Qt.UserRole)
        
        try:
            result = SearchMethods.search (self, params, indexConf)
        except Exception as e:
            self.reportFailedSearch(indexConf, e)
        else:
            self.updateSearchResult(result)
        
    def updateSearchResult (self, result):
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
        return index.data(Qt.UserRole)

    # Show the user possible reason why the search threw an exception
    def reportFailedSearch(self, indexConf, e):
        print ("Search failed: " + str(e))
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
            
    def reportCustomSearchFailed (self,  e):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        import io
        import traceback
        memFile = io.StringIO()
        traceback.print_exception(exc_type, exc_value, exc_traceback, limit=5, file=memFile)
        
        QMessageBox.warning(self,
                self.trUtf8("Custom search failed"),
                self.trUtf8("Custom search scripts are written in Python. The following exception info might help to find the problem:\n") + memFile.getvalue(),
                QMessageBox.StandardButtons(QMessageBox.Ok))
        
        
    
