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

from PyQt4.QtCore import * 
from PyQt4.QtGui import *
from Ui_SettingsDialog import Ui_SettingsDialog
from IndexConfiguration import IndexConfiguration

class SettingsEditorDelegate (QStyledItemDelegate):
    itemHeight = 40
    
    def __init__(self,  parent=None):
        super (QStyledItemDelegate,  self).__init__(parent)
        if parent:
            self.boldFont = QFont (parent.font())
        else:
            self.boldFont = QFont (QApplication.font())
        self.boldFont.setBold (True)

    def paint (self,  painter, option, index):
        QApplication.style().drawPrimitive(QStyle.PE_PanelItemViewItem, option, painter,  self.parent())
        
        rect = QRect(option.rect)
        rect.setHeight(self.itemHeight)
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
        baseHint = super(SettingsEditorDelegate, self).sizeHint(option, index)
        return QSize(baseHint.width(), self.itemHeight)

def setCheckBox (check, value):
    if value:
        check.setCheckState(Qt.Checked)
    else:
        check.setCheckState(Qt.Unchecked)

class SettingsDialog (QDialog):
    def __init__ (self, parent,  searchLocations,  config):
        super (SettingsDialog, self).__init__(parent)
        self.ui = Ui_SettingsDialog()
        self.ui.setupUi(self)
        self.setProperty("shadeBackground", True) # fill background with gradient as defined in style sheet

        self.model = QStandardItemModel()
        self.ui.listViewLocations.setModel(self.model)
        self.ui.listViewLocations.setItemDelegate (SettingsEditorDelegate(self.ui.listViewLocations))
        
        self.ui.listViewLocations.selectionModel().currentChanged.connect(self.selectionChanged)
        self.ui.settingsItem.dataChanged.connect(self.updateDisplayRole)
        
        self.ui.editTabWidth.setText(str(config.SourceViewer.TabWidth))
        setCheckBox (self.ui.checkMatchOverFiles,  config.matchOverFiles)
        setCheckBox (self.ui.checkConfirmClose,  config.showCloseConfirmation)
        
        for location in searchLocations:
            self.__addLocation(location)
            
        index = self.model.index(0, 0)
        if index.isValid():
            self.ui.listViewLocations.setCurrentIndex(index)
        else:
            self.ui.settingsItem.resetAndDisable()
            
        self.ui.settingsItem.setFocus(Qt.ActiveWindowFocusReason)
        
    def locations(self):
        locs = []
        for row in range(self.model.rowCount()):
            index = self.model.index(row, 0)
            locs.append(index.data(Qt.UserRole+1))
        return locs
        
    @pyqtSlot()
    def updateDisplayRole(self):
        index = self.ui.listViewLocations.currentIndex ()
        if index.isValid():
            self.saveDataForItem (index)
        
    @pyqtSlot('QModelIndex', 'QModelIndex')
    def selectionChanged(self, current,  previous):
        self.saveDataForItem (previous)
        self.loadDataFromItem(current)
        
    def saveDataForItem (self,  index):
        if not index.isValid():
            return
        editor = self.ui.settingsItem
        editor.enable()
        location = IndexConfiguration (editor.name(),  editor.extensions(), editor.directories(), editor.dirExcludes(),  editor.indexDB(), editor.indexGenerationEnabled())
        self.model.setData (index,  location,  Qt.UserRole+1)

    def loadDataFromItem (self,  index):
        editor = self.ui.settingsItem
        if not index.isValid():
            return editor.resetAndDisable()
        location = index.data(Qt.UserRole+1)
        editor.setName (location.displayName())
        editor.setDirectories(location.directoriesAsString())
        editor.setExtensions(location.extensionsAsString())
        editor.setDirExcludes(location.dirExcludesAsString())
        if location.indexdb:
            editor.setIndexDB(location.indexdb)
        editor.enableIndexGeneration(location.generateIndex)
        
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
        index = self.__addLocation(location)
        if index.isValid():
            self.ui.listViewLocations.setCurrentIndex(index)
        self.ui.settingsItem.setFocus(Qt.ActiveWindowFocusReason)
        self.ui.settingsItem.nameSelectAll()
        
    @pyqtSlot()
    def removeLocation (self):
        index = self.ui.listViewLocations.currentIndex ()
        if index.isValid():
            self.model.removeRow(index.row())
            
    @pyqtSlot()
    def okClicked(self):
        index = self.ui.listViewLocations.currentIndex()
        if index.isValid():
            self.saveDataForItem (index)
        self.accept()
        
def main():    
    import sys
    from Config import Config
    app = QApplication(sys.argv) 
    locations = [IndexConfiguration("Qt Source",  "h,cpp", "D:\\qt", "D:\\index.dat"), IndexConfiguration("Linux")]
    conf = Config()
    conf.sourceViewer = Config()
    conf.sourceViewer.tabwidth = 4
    conf.matchOverFiles=True
    conf.showCloseConfirmation=True
    w = SettingsDialog(None,locations, conf) 
    w.show() 
    sys.exit(app.exec_()) 

if __name__ == "__main__":
    main()

