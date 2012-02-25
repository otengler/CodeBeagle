# -*- coding: utf-8 -*-
"""
Copyright (C) 2012 Oliver Tengler

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
from Ui_SettingsItem import Ui_SettingsItem
import AppConfig

class SettingsItem (QWidget):   
    dataChanged = pyqtSignal()
    
    def __init__ (self, parent):
        super (SettingsItem, self).__init__(parent)
        self.ui = Ui_SettingsItem()
        self.ui.setupUi(self)
        
        self.buildDBName = True
        self.ui.editName.textEdited.connect(self.nameEdited)
        self.ui.editIndexDB.textEdited.connect(self.indexDBEdited)
        
        self.ui.editName.textEdited.connect(self.dataChanged)
        self.ui.editDirectories.textEdited.connect(self.dataChanged)
        self.ui.editExtensions.textEdited.connect(self.dataChanged)
   
    def focusInEvent (self, event):
        self.ui.editName.setFocus(Qt.ActiveWindowFocusReason)
    
    # Suggest a name for the index db
    @pyqtSlot('QString')
    def nameEdited(self, text):
        if self.buildDBName and self.indexGenerationEnabled():
            self.__updateDBName(text)
            
    def __updateDBName(self, text):
        location = ""
        if "APPDATA" in os.environ:
            location = os.path.expandvars("$APPDATA")
        elif "HOME" in os.environ:
            location = os.path.expandvars("$HOME")
        if location:
            location += os.path.sep
            location += AppConfig.appName
            location += os.path.sep
            location += text.replace(" ", "_")
            location += ".dat"
            self.ui.editIndexDB.setText(location)
    
    @pyqtSlot('QString')
    def indexDBEdited(self, text):
        if text:
            self.buildDBName = False
        else:
            self.buildDBName = True
        
    @pyqtSlot()
    def browseForDirectory(self):
        directory = QFileDialog.getExistingDirectory (
            self,          
            self.trUtf8("Choose directory to search or index"),
            "",
            QFileDialog.Options(QFileDialog.ShowDirsOnly))
        
        if directory:
            self.ui.editDirectories.setText (directory)
            self.dataChanged.emit()

    @pyqtSlot()
    def browseForIndexDB(self):
        indexDB = QFileDialog.getSaveFileNameAndFilter(
            None,
            self.trUtf8("Choose file for index DB"),
            "",
            self.trUtf8("*.dat"),
            None,
            QFileDialog.Options(QFileDialog.DontConfirmOverwrite))
                
        if len(indexDB[0]): # indexDB is a touple: file,filter
            self.setIndexDB(indexDB[0]) 
       
    def nameSelectAll (self):
        self.ui.editName.selectAll()
       
    def setData (self, name, directories, extensions,  dirExcludes, bGeneratesIndex, indexDB):
        self.ui.editName.setText (name)
        self.ui.editDirectories.setText (directories)
        self.ui.editExcludeDirectories.setText (dirExcludes)
        self.ui.editExtensions.setText (extensions)
        
        self.buildDBName = False
        if indexDB:
            self.ui.editIndexDB.setText (indexDB)
        else:
            if bGeneratesIndex:
                self.buildDBName = True
                self.__updateDBName (name)
            else:
                self.ui.editIndexDB.setText (indexDB)
        
        if bGeneratesIndex:
            self.ui.checkBoxGenerateIndex.setCheckState(Qt.Checked)
        else:
            self.ui.checkBoxGenerateIndex.setCheckState(Qt.Unchecked)
            
        self.ui.editIndexDB.setEnabled(bGeneratesIndex)
        self.ui.buttonBrowseIndexLocation.setEnabled(bGeneratesIndex)

    def name (self):
        return self.ui.editName.text()
          
    def directories (self):
        return self.ui.editDirectories.text()

    def dirExcludes (self):
        return self.ui.editExcludeDirectories.text()
        
    def extensions (self):
        return self.ui.editExtensions.text()
        
    def indexDB (self):
        return self.ui.editIndexDB.text()

    def indexGenerationEnabled (self):
        return self.ui.checkBoxGenerateIndex.checkState() == Qt.Checked

    def resetAndDisable(self):
        self.ui.editName.setText("")
        self.ui.editExcludeDirectories.setText("")
        self.ui.editExtensions.setText("")
        self.ui.editDirectories.setText("")
        self.ui.editIndexDB.setText("")
        self.ui.checkBoxGenerateIndex.setCheckState(Qt.Unchecked)
        self.enable(False)
        
    def enable(self, bEnable=True):
        self.ui.editExtensions.setEnabled(bEnable)
        self.ui.editName.setEnabled(bEnable)
        self.ui.editExcludeDirectories.setEnabled(bEnable)
        self.ui.editDirectories.setEnabled(bEnable)
        self.ui.checkBoxGenerateIndex.setEnabled(bEnable)
        self.ui.buttonDirectory.setEnabled(bEnable)
        if bEnable and not self.indexGenerationEnabled():
            bEnable=False
        self.ui.editIndexDB.setEnabled(bEnable)
        self.ui.buttonBrowseIndexLocation.setEnabled(bEnable)
