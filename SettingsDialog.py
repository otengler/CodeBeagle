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
    itemHeight = 40
    
    def __init__(self,  parent=None):
        super (QStyledItemDelegate,  self).__init__(parent)
        # These two variables contain the row number and the height of the row which is being edited
        self.editRow = -1
        self.editorHeight = 0
        self.closeEditor.connect(self.resetEditRow)
        if parent:
            self.boldFont = QFont (parent.font())
        else:
            self.boldFont = QFont (QApplication.font())
        self.boldFont.setBold (True)
        
        self.gradient = QLinearGradient()
        self.gradient.setColorAt(0.0, QColor("#fff"))
        self.gradient.setColorAt(0.5, QColor("#eee"))
        self.gradient.setColorAt(1.0, QColor("#fff"))
        
        self.selectedGradient = QLinearGradient()
        self.selectedGradient.setColorAt(0.0, QColor("#eef"))
        self.selectedGradient.setColorAt(1.0, QColor("#ccf"))
        
    @pyqtSlot('QWidget')
    def resetEditRow(self, editor):
        self.editRow = -1
        self.editorHeight = 0
        
    def createEditor (self,  parent,  option,  index):
        item = SettingsItem (parent,  True)
        item.commitChanges.connect(self.commitChanges)
        self.editRow = index.row()
        self.editorHeight = item.minimumSizeHint().height()
        self.sizeHintChanged.emit (index)
        return item
        
    @pyqtSlot('QWidget')
    def commitChanges(self, editor):
        self.commitData.emit(editor)
    
    def setEditorData (self,  editor,  index):
        location = index.data(Qt.UserRole+1)
        editor.setName (location.displayName())
        editor.setDirectories(location.directoriesAsString())
        editor.setExtensions(location.extensionsAsString())
        if location.indexdb:
            editor.setIndexDB(location.indexdb)
        editor.enableIndexGeneration(location.generateIndex)
        updateIndex = False
        if hasattr(location,"updateIndex"):
            updateIndex = location.updateIndex
        editor.enableIndexUpdate(updateIndex)
        
    def setModelData (self, editor,  model,  index):
        name = editor.name()
        model.setData (index,  name,  Qt.DisplayRole)
        location = IndexConfiguration (name,  editor.extensions(), editor.directories(), editor.indexDB(), editor.indexGenerationEnabled())
        location.updateIndex = editor.indexUpdateEnabled()
        model.setData (index,  location,  Qt.UserRole+1)
        
    def updateEditorGeometry(self,  editor,  option,  index):
        editor.setGeometry(option.rect.x(), option.rect.y()+self.itemHeight,  option.rect.width(),  self.editorHeight)
        
    def paint (self,  painter, option, index):
        rect = QRect(option.rect)
        rect.setHeight(self.itemHeight)
        
        selected = self.editRow == index.row()
        if selected:
            grad = self.selectedGradient
            grad.setStart(rect.left(), 0)
            grad.setFinalStop (rect.right(), 0)
        else:
            grad = self.gradient
            grad.setStart(0, rect.top())
            grad.setFinalStop (0, rect.bottom())
        painter.fillRect(rect, QBrush(grad))
        
        third = (rect.width()-12) / 3
        
        rect1 = QRect(rect)
        rect1.translate(12, 0)
        rect1.setWidth(third)
        rect2 = QRect(rect1)
        rect2.translate(third, 0)
        rect2.setWidth(third*2)
        
        painter.save()
        
        location = index.data(Qt.UserRole+1)
        
        if len(location.directories)>0:
            dirs = self.trUtf8("Directories: ") + ",".join(location.directories)
            if len(location.extensions)>0:
                dirs += " ("
                dirs += self.trUtf8("Extensions: ") + ",".join(location.extensions)
                dirs += ")"
            painter.drawText (rect2, Qt.AlignVCenter+Qt.TextWordWrap, dirs)
            
        painter.setFont(self.boldFont)
        painter.drawText (rect1, Qt.AlignVCenter+Qt.TextWordWrap, location.displayName())
        
        painter.restore()
        
    def sizeHint (self,  option,  index):
        if index.row() == self.editRow:
            return QSize (option.rect.width(),  self.editorHeight+self.itemHeight)
        else:
            baseHint = super(SettingsEditorDelegate, self).sizeHint(option, index)
            return QSize(baseHint.width(), self.itemHeight)

class SettingsDialog (QDialog):
    def __init__ (self, parent,  searchLocations):
        super (SettingsDialog, self).__init__(parent)
        self.ui = Ui_SettingsDialog()
        self.ui.setupUi(self)
        self.setProperty("shadeBackground", True) # fill background with gradient as defined in style sheet

        self.model = QStandardItemModel()
        self.ui.listViewLocations.setModel(self.model)
        self.ui.listViewLocations.setItemDelegate (SettingsEditorDelegate(self.ui.listViewLocations))
        
        for location in searchLocations:
            self.__addLocation(location)
            
        index = self.model.index(0, 0)
        if index.isValid():
            self.ui.listViewLocations.setCurrentIndex(index)
            self.ui.listViewLocations.edit(index)
        
    def locations(self):
        locs = []
        for row in range(self.model.rowCount()):
            index = self.model.index(row, 0)
            locs.append(index.data(Qt.UserRole+1))
        
        return locs
        
    def __addLocation (self,  location):
        rows = self.model.rowCount()
        if self.model.insertRow(rows):
            item = QStandardItem(location.displayName())
            item.setData(location)
            self.model.setItem(rows, item)
            return self.model.index(rows, 0)
            
    @pyqtSlot()
    def addLocation (self):
        location = IndexConfiguration(self.trUtf8("New location"))
        location.updateIndex = True # As this is a new location, mark this index for update
        index = self.__addLocation(location)
        if index.isValid():
            self.ui.listViewLocations.setCurrentIndex(index)
        
    @pyqtSlot()
    def removeLocation (self):
        index = self.ui.listViewLocations.currentIndex ()
        if index.isValid():
            self.model.removeRow(index.row())
        
def main():    
    app = QApplication(sys.argv) 
    locations = [IndexConfiguration("Qt Source",  "h,cpp", "D:\\qt", "D:\\index.dat"), IndexConfiguration("Linux")]
    w = SettingsDialog(None,locations) 
    w.show() 
    sys.exit(app.exec_()) 

if __name__ == "__main__":
    main()

