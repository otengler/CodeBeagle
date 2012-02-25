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

class LocationControl:
    def __init__(self, settingsItem,  listView,  searchLocations,  readOnly):
        self.settingsItem = settingsItem
        self.listView = listView
        self.readOnly = readOnly
        
        self.model = QStandardItemModel()
        self.listView.setModel(self.model)
        self.listView.setItemDelegate (SettingsEditorDelegate(self.listView))

        self.listView.selectionModel().currentChanged.connect(self.selectionChanged)
        self.settingsItem.dataChanged.connect(self.updateDisplayRole)
        
        for location in searchLocations:
            self.addLocation(location)
            
        index = self.model.index(0, 0)
        if index.isValid():
            self.listView.setCurrentIndex(index)
        else:
            self.settingsItem.resetAndDisable()
        
    @pyqtSlot()
    def updateDisplayRole(self):
        index = self.listView.currentIndex ()
        if index.isValid():
            self.saveDataForItem (index)
        
    @pyqtSlot('QModelIndex', 'QModelIndex')
    def selectionChanged(self, current,  previous):
        self.saveDataForItem (previous)
        self.loadDataFromItem(current)
        
    def saveDataForItem (self,  index):
        if not index.isValid():
            return
        editor = self.settingsItem
        location = IndexConfiguration (editor.name(),  
                                                       editor.extensions(), 
                                                       editor.directories(), 
                                                       editor.dirExcludes(),  
                                                       editor.indexDB(), 
                                                       editor.indexGenerationEnabled())
        self.model.setData (index,  location,  Qt.UserRole+1)

    def loadDataFromItem (self,  index):
        editor = self.settingsItem
        if not index.isValid():
            return editor.resetAndDisable()
        location = index.data(Qt.UserRole+1)
        editor.setData (location.displayName(), 
                                location.directoriesAsString(), 
                                location.extensionsAsString(),  
                                location.dirExcludesAsString(), 
                                location.generateIndex, 
                                location.indexdb)
        editor.enable (not self.readOnly)
        
    def addLocation (self,  location,  activateLocation=False):
        rows = self.model.rowCount()
        if self.model.insertRow(rows):
            item = QStandardItem(location.displayName())
            item.setData(location)
            self.model.setItem(rows, item)
            index = self.model.index(rows, 0)
            if activateLocation and index.isValid():
                self.listView.setCurrentIndex(index)
                self.settingsItem.setFocus(Qt.ActiveWindowFocusReason)
                self.settingsItem.nameSelectAll()
                
    def locations(self):
        locs = []
        for row in range(self.model.rowCount()):
            index = self.model.index(row, 0)
            locs.append(index.data(Qt.UserRole+1))
        return locs

class SettingsDialog (QDialog):
    def __init__ (self, parent,  searchLocations,  globalSearchLocations,  config):
        super (SettingsDialog, self).__init__(parent)
        self.ui = Ui_SettingsDialog()
        self.ui.setupUi(self)
        self.setProperty("shadeBackground", True) # fill background with gradient as defined in style sheet

        self.ui.fontComboBox.setCurrentFont(QFont(config.SourceViewer.FontFamily))
        self.ui.editFontSize.setText(str(config.SourceViewer.FontSize))
        self.ui.editTabWidth.setText(str(config.SourceViewer.TabWidth))
        setCheckBox (self.ui.checkMatchOverFiles,  config.matchOverFiles)
        setCheckBox (self.ui.checkConfirmClose,  config.showCloseConfirmation)

        self.myLocations = LocationControl(self.ui.settingsItem,  self.ui.listViewLocations,  searchLocations, False)
        self.globalLocations = LocationControl(self.ui.globalSettingsItem,  self.ui.listViewGlobalLocations,  globalSearchLocations, True)
            
        self.ui.settingsItem.setFocus(Qt.ActiveWindowFocusReason)
        
    def locations(self):
        return self.myLocations.locations()
            
    @pyqtSlot()
    def addLocation (self):
        location = IndexConfiguration(self.trUtf8("New location"))
        self.myLocations.addLocation(location, True)
        
    @pyqtSlot()
    def duplicateLocation(self):
        index = self.ui.listViewLocations.currentIndex ()
        if index.isValid():
            location = index.data(Qt.UserRole+1)
            duplicated = IndexConfiguration (self.trUtf8("Duplicated ") + location.displayName(), 
                                                            location.extensionsAsString(), 
                                                            location.directoriesAsString(), 
                                                            location.dirExcludesAsString(), 
                                                            "", 
                                                            location.generateIndex)
            self.myLocations.addLocation(duplicated, True)
        
    @pyqtSlot()
    def removeLocation (self):
        index = self.ui.listViewLocations.currentIndex ()
        if index.isValid():
            self.myLocations.model.removeRow(index.row())
            
    @pyqtSlot()
    def okClicked(self):
        index = self.ui.listViewLocations.currentIndex()
        if index.isValid():
            self.myLocations.saveDataForItem (index)
            
        # Check if there are search location with the same name and reject this
        names = set()
        for location in self.locations():
            name = location.displayName().lower()
            if name in names:
                QMessageBox.warning(self,
                    self.trUtf8("Duplicate search location names"),
                    self.trUtf8("Please choose a unique name for each search location.") + " '" + location.displayName() + "' " +   self.trUtf8("is used more than once."),
                    QMessageBox.StandardButtons(QMessageBox.Ok))
                return
            names.add(name)
        self.accept()
        
def main():    
    import sys
    from Config import Config
    app = QApplication(sys.argv) 
    locations = [IndexConfiguration("Qt Source",  "h,cpp", "D:\\qt", "","D:\\index.dat"), IndexConfiguration("Linux", "", "", "", "", False)]
    conf = Config()
    conf.sourceViewer = Config()
    conf.sourceViewer.tabwidth = 4
    conf.matchOverFiles=True
    conf.showCloseConfirmation=True
    w = SettingsDialog(None,locations, locations, conf) 
    w.show() 
    sys.exit(app.exec_()) 

if __name__ == "__main__":
    main()

