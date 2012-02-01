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
import uuid
from PyQt4.QtCore import * 
from PyQt4.QtGui import *
from Ui_SettingsItem import Ui_SettingsItem

class SettingsItem (QWidget):
    commitChanges = pyqtSignal('QWidget')
    
    def __init__ (self, parent,  shadeBackground=False):
        super (SettingsItem, self).__init__(parent)
        self.ui = Ui_SettingsItem()
        self.ui.setupUi(self)
        
        self.buildDBName = True
        self.ui.editName.textEdited.connect(self.nameEdited)
        self.ui.editIndexDB.textEdited.connect(self.indexDBEdited)
        
        if shadeBackground:
            self.gradient = QLinearGradient()
            self.gradient.setStart(0, 0)
            self.gradient.setColorAt(0, QColor("#eef"))
            self.gradient.setColorAt(1, QColor("#ccf"))
        else:
            self.gradient = None
            
        # Part of a UUID to make the generated DB file unique
        self.uniqueStr = str(uuid.uuid1()).split("-")[0]
   
    def focusInEvent (self, event):
        self.ui.editName.setFocus(Qt.ActiveWindowFocusReason)
        
    # This is a bit of a hack: Everytime the mouse leaves the widget commitChanges it emitted to save
    # the data back into the model. This solves the problem that the data was not saved if you edited
    # just one location and closed the dialog
    def leaveEvent(self, event):
        self.commitChanges.emit(self)
        
    def paintEvent(self, event):
        if self.gradient:
            rect = event.rect()
            self.gradient.setFinalStop (rect.width(), 0)
            painter = QPainter(self)
            painter.fillRect(rect, QBrush(self.gradient))
        super(SettingsItem, self).paintEvent(event)
    
    # Suggest a name for the index db
    @pyqtSlot('QString')
    def nameEdited(self, text):
        if self.buildDBName:
            self.__updateDBName(text)
            
    def __updateDBName(self, text):
        location = ""
        if "APPDATA" in os.environ:
            location = "$APPDATA"
        elif "HOME" in os.environ:
            location = "$HOME"
        if location:
            location += os.path.sep
            location += "CodeBeagle"
            location += os.path.sep
            location += text.replace(" ", "_")
            location += "."
            location += self.uniqueStr
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
            self.trUtf8("Choose directory to index"),
            "",
            QFileDialog.Options(QFileDialog.ShowDirsOnly))
        
        if directory:
            self.setDirectories(directory)

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
            
    @pyqtSlot()
    def updateIndex(self):
        self.enableIndexUpdate(not self.updateIndex)
       
    def setName(self, name):
        self.ui.editName.setText (name)
        if not self.indexDB():
            self.__updateDBName (name)
    def name (self):
        return self.ui.editName.text()
        
    def setDirectories(self, directories):
        self.ui.editDirectories.setText (directories)
    def directories (self):
        return self.ui.editDirectories.text()
        
    def setExtensions(self, extensions):
        self.ui.editExtensions.setText (extensions)
    def extensions (self):
        return self.ui.editExtensions.text()
        
    def setIndexDB(self, indexDB):
        if indexDB:
            self.buildDBName = False
        self.ui.editIndexDB.setText (indexDB)
    def indexDB (self):
        return self.ui.editIndexDB.text()
        
    def enableIndexGeneration (self, bEnable):
        if bEnable:
            self.ui.checkBoxGenerateIndex.setCheckState(Qt.Checked)
        else:
            self.ui.checkBoxGenerateIndex.setCheckState(Qt.Unchecked)
    def indexGenerationEnabled (self):
        return self.ui.checkBoxGenerateIndex.checkState() == Qt.Checked
    
    def enableIndexUpdate (self, bEnable):
        if bEnable:
            self.ui.checkUpdateIndex.setCheckState(Qt.Checked)
        else:
            self.ui.checkUpdateIndex.setCheckState(Qt.Unchecked)
    def indexUpdateEnabled (self):
        return self.ui.checkUpdateIndex.checkState() == Qt.Checked    

        
        
