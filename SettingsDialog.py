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

import sys
from PyQt4.QtCore import * 
from PyQt4.QtGui import *
from Ui_SettingsDialog import Ui_SettingsDialog
from SettingsItem import SettingsItem
from IndexConfiguration import IndexConfiguration

class SettingsEditorDelegate (QStyledItemDelegate):
    def __init__(self,  parent=None):
        super (QStyledItemDelegate,  self).__init__(parent)
        # These two variables contain the row number and the height of the row which is being edited
        self.editRow = -1
        self.editorHeight = 0
        self.closeEditor.connect(self.resetEditRow)
        
    @pyqtSlot('QWidget')
    def resetEditRow(self, editor):
        self.editRow = -1
        self.editorHeight = 0
        
    def createEditor (self,  parent,  option,  index):
        item = SettingsItem (parent,  True)
        self.editRow = index.row()
        self.editorHeight = item.minimumSizeHint().height()
        self.sizeHintChanged.emit (index)
        return item
    
    def setEditorData (self,  editor,  index):
        name = index.data(Qt.DisplayRole)
        editor.setName (name)
        
    def setModelData (self, editor,  model,  index):
        model.setData (index,  editor.name(),  Qt.DisplayRole)
        
    def updateEditorGeometry(self,  editor,  option,  index):
        editor.setGeometry(option.rect.x(), option.rect.y(),  option.rect.width(),  self.editorHeight)
        
    def paint (self,  painter, option, index):
        if self.editRow != index.row():
            super(SettingsEditorDelegate, self).paint(painter, option, index)
        
    def sizeHint (self,  option,  index):
        if index.row() == self.editRow:
            return QSize (option.rect.width(),  self.editorHeight)
        else:
            return super(SettingsEditorDelegate, self).sizeHint(option, index)+QSize(0, 20)

class SettingsDialog (QDialog):
    def __init__ (self, parent=None):
        super (SettingsDialog, self).__init__(parent)
        self.ui = Ui_SettingsDialog()
        self.ui.setupUi(self)
        self.setProperty("shadeBackground", True) # fill background with gradient as defined in style sheet

        self.model = QStringListModel (["My search location", "Welt"])
        self.ui.listViewLocations.setModel(self.model)
        self.ui.listViewLocations.setItemDelegate (SettingsEditorDelegate())
        
    @pyqtSlot()
    def addLocation (self):
        rows = self.model.rowCount()
        if self.model.insertRow(rows):
            addedIndex = self.model.index(rows, 0)
            conf = IndexConfiguration()
            self.model.setData(addedIndex, self.trUtf8("New location"), Qt.DisplayRole)
        
    @pyqtSlot()
    def removeLocation (self):
        pass
        
def main():    
    app = QApplication(sys.argv) 
    w = SettingsDialog() 
    w.show() 
    sys.exit(app.exec_()) 

if __name__ == "__main__":
    main()

