# -*- coding: utf-8 -*-
"""
Copyright (C) 2012 Oliver Tengler

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from typing import List, Set
from PyQt5.QtCore import Qt, QRect, QSize, pyqtSignal, pyqtSlot, QModelIndex, QObject
from PyQt5.QtGui import QFont, QPixmap, QStandardItemModel, QStandardItem, QPainter
from PyQt5.QtWidgets import QApplication, QStyledItemDelegate, QStyleOptionViewItem, QStyle, QDialog, QMessageBox, QWidget, QCheckBox, QListView
from fulltextindex.IndexConfiguration import IndexConfiguration, indexTypeInfo, IndexMode
from tools.Config import Config
import tools.FileTools as FileTools
from dialogs import StackTraceMessageBox
from dialogs.UserHintDialog import ButtonType,showUserHint
from .Ui_SettingsDialog import Ui_SettingsDialog
from .SettingsItem import SettingsItem
import AppConfig


userHintUpdateIndex = """
<p align='justify'>You added or changed indexed search locations:
%(locations)s
</p>
<p align='justify'>Do you want me to update the indexes now?</p>
<p align='jusitfy'> The update runs in the background and continues even if you close the program. During the update the index cannot be used.
To manually start the index update press the 'Update Index' button in the toolbar. See the help for more details.</p>
"""

class SettingsEditorDelegate(QStyledItemDelegate):
    itemHeight = 40

    def __init__(self, parent: QWidget=None) -> None:
        super().__init__(parent)
        if parent:
            self.boldFont = QFont(parent.font())
        else:
            self.boldFont = QFont(QApplication.font())
        self.boldFont.setBold(True)
        self.defaultLocationRow = -1
        self.defaultPixmap = QPixmap("resources/Default.png")
        self.defaultPixmapSize = 20

    def setDefaultLocationRow(self, row: int) -> None:
        self.defaultLocationRow = row

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        QApplication.style().drawPrimitive(QStyle.PE_PanelItemViewItem, option, painter, self.parent())

        rect = QRect(option.rect)
        rect.setHeight(self.itemHeight)
        third = (rect.width()-12) // 3

        rect1 = QRect(rect)
        rect1.translate(12, 0)
        rect1.setWidth(third-self.defaultPixmapSize)
        rect2 = QRect(rect1)
        rect2.translate(third+self.defaultPixmapSize, 0)
        rect2.setWidth(third*2)

        painter.save()

        location = index.data(Qt.UserRole+1)

        if location.directories:
            dirs = self.tr("Directories: ") + location.directoriesAsString()
            if location.extensions:
                dirs += " ("
                dirs += self.tr("Extensions: ") + location.extensionsAsString()
                dirs += ")"
            painter.drawText(rect2, Qt.AlignVCenter + Qt.TextWordWrap, dirs)

        painter.setFont(self.boldFont)
        locationName = location.displayName()
        if index.row() == self.defaultLocationRow:
            locationName = locationName + self.tr(" (Default)")
            painter.drawPixmap(rect1.right(), rect1.center().y()-self.defaultPixmapSize//2, self.defaultPixmapSize, self.defaultPixmapSize, self.defaultPixmap)
        painter.drawText(rect1, Qt.AlignVCenter + Qt.TextWordWrap, locationName)

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        baseHint = super().sizeHint(option, index)
        return QSize(baseHint.width(), self.itemHeight)

def setCheckBox(check: QCheckBox, value: bool) -> None:
    if value:
        check.setCheckState(Qt.Checked)
    else:
        check.setCheckState(Qt.Unchecked)

class LocationControl (QObject):
    def __init__(self, settingsItem: SettingsItem, listView: QListView, searchLocations: List[IndexConfiguration], readOnly: bool) -> None:
        super().__init__(None)
        self.settingsItem = settingsItem
        self.listView = listView
        self.readOnly = readOnly

        self.model = QStandardItemModel()
        self.listView.setModel(self.model)
        self.listView.setItemDelegate(SettingsEditorDelegate(self.listView))

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
    def updateDisplayRole(self) -> None:
        index = self.listView.currentIndex()
        if index.isValid():
            self.saveDataForItem(index)

    @pyqtSlot(QModelIndex, QModelIndex)
    def selectionChanged(self, current: QModelIndex, previous: QModelIndex) -> None:
        self.saveDataForItem(previous)
        self.loadDataFromItem(current)

    def saveDataForItem(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        editor = self.settingsItem
        location = IndexConfiguration(editor.name(),
                                      editor.extensions(),
                                      editor.directories(),
                                      editor.dirExcludes(),
                                      editor.indexDB(),
                                      editor.indexUpdateMode(),
                                      editor.indexType())
        self.model.setData(index, location, Qt.UserRole+1)

    def loadDataFromItem(self, index: QModelIndex) -> None:
        editor = self.settingsItem
        if not index.isValid():
            editor.resetAndDisable()
            return
        location = index.data(Qt.UserRole+1)
        editor.setData(location.displayName(),
                       location.directoriesAsString(),
                       location.extensionsAsString(),
                       location.dirExcludesAsString(),
                       location.indexUpdateMode,
                       location.indexdb,
                       location.indexType)
        editor.enable(not self.readOnly)

    def addLocation(self, location: IndexConfiguration, activateLocation:bool=False) -> None:
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

    def locations(self) -> List[IndexConfiguration]:
        locs = []
        for row in range(self.model.rowCount()):
            index = self.model.index(row, 0)
            locs.append(index.data(Qt.UserRole+1))
        return locs

class SettingsDialog (QDialog):
    updateChangedIndexes = pyqtSignal(list)

    def __init__ (self, parent: QWidget, searchLocations: List[IndexConfiguration], globalSearchLocations: List[IndexConfiguration], config: Config) -> None:
        super ().__init__(parent)
        self.ui = Ui_SettingsDialog()
        self.ui.setupUi(self)
        self.setProperty("shadeBackground", True) # fill background with gradient as defined in style sheet

        self.searchLocations = searchLocations

        self.ui.fontComboBox.setCurrentFont(QFont(config.SourceViewer.FontFamily))
        self.ui.editFontSize.setText(str(config.SourceViewer.FontSize))
        self.ui.editTabWidth.setText(str(config.SourceViewer.TabWidth))
        self.ui.editPreviewLines.setText(str(config.previewLines))
        setCheckBox (self.ui.checkActivateFirstMatch, config.activateFirstMatch)
        setCheckBox (self.ui.checkMatchOverFiles,  config.matchOverFiles)
        setCheckBox (self.ui.checkConfirmClose,  config.showCloseConfirmation)
        setCheckBox (self.ui.checkRegexDialog, config.showRegexDialog)
        setCheckBox (self.ui.checkShowMatchList, config.showMatchList)
        setCheckBox (self.ui.checkShowLineNumbers, config.SourceViewer.showLineNumbers)
        isDarkTheme = config.theme == AppConfig.darkTheme
        setCheckBox (self.ui.checkDarkTheme, isDarkTheme)

        self.myLocations = LocationControl(self.ui.settingsItem,  self.ui.listViewLocations,  searchLocations, False)
        self.globalLocations = LocationControl(self.ui.globalSettingsItem,  self.ui.listViewGlobalLocations,  globalSearchLocations, True)

        # Check which location is the current default location
        defaultLocation = config.defaultLocation
        for row, location in enumerate(searchLocations):
            if defaultLocation == location.displayName():
                self.__defaultLocationChanged (self.ui.listViewLocations,  self.ui.listViewGlobalLocations,  row)
        for row, location in enumerate(globalSearchLocations):
            if defaultLocation == location.displayName():
                self.__defaultLocationChanged (self.ui.listViewGlobalLocations, self.ui.listViewLocations,  row)

        # If there are no search locations from the global config.txt then remove the corresponding tab
        if not globalSearchLocations:
            self.ui.tabWidget.removeTab(1)
            del self.ui.tabGlobalSearchLocations

        self.ui.settingsItem.setFocus(Qt.ActiveWindowFocusReason)

    def defaultLocation (self) -> str:
        index = None
        row = self.ui.listViewLocations.itemDelegate().defaultLocationRow
        if row != -1:
            model = self.ui.listViewLocations.model()
            index = model.index(row, 0)
        row = self.ui.listViewGlobalLocations.itemDelegate().defaultLocationRow
        if row != -1:
            model = self.ui.listViewGlobalLocations.model()
            index = model.index(row, 0)

        if index and index.isValid():
            location: IndexConfiguration = index.data(Qt.UserRole+1)
            return location.displayName()
        return ""

    def locations(self) -> List[IndexConfiguration]:
        return self.myLocations.locations()

    def addExistingLocation(self, location: IndexConfiguration, activateLocation:bool=True) -> None:
        self.myLocations.addLocation(location, activateLocation)

    @pyqtSlot()
    def addLocation (self) -> None:
        location = IndexConfiguration(self.tr("New location"))
        self.addExistingLocation(location, True)

    @pyqtSlot()
    def setDefaultLocation (self) -> None:
        index = self.ui.listViewLocations.currentIndex ()
        if index.isValid():
            self.__defaultLocationChanged (self.ui.listViewLocations,  self.ui.listViewGlobalLocations,  index.row())
        else:
            self.__defaultLocationChanged (self.ui.listViewLocations,  self.ui.listViewGlobalLocations,  -1)

    @pyqtSlot()
    def setDefaultLocationGlobal (self) -> None:
        index = self.ui.listViewGlobalLocations.currentIndex ()
        if index.isValid():
            self.__defaultLocationChanged (self.ui.listViewGlobalLocations, self.ui.listViewLocations, index.row())
        else:
            self.__defaultLocationChanged (self.ui.listViewGlobalLocations, self.ui.listViewLocations,  -1)

    def __defaultLocationChanged(self, listviewCurrent: QListView, listviewOther: QListView, newDefaultRow: int) -> None:
        listviewCurrent.itemDelegate().setDefaultLocationRow(newDefaultRow)
        listviewOther.itemDelegate().setDefaultLocationRow(-1)
        # Refresh the listview
        model = listviewCurrent.model()
        firstIndex = model.index(0, 0)
        lastIndex = model.index(model.rowCount()-1, 0)
        if firstIndex.isValid() and lastIndex.isValid():
            model.dataChanged.emit(firstIndex, lastIndex)

    @pyqtSlot()
    def duplicateLocation(self) -> None:
        index = self.ui.listViewLocations.currentIndex ()
        if index.isValid():
            location = index.data(Qt.UserRole+1)
            duplicated = IndexConfiguration (self.tr("Duplicated ") + location.displayName(),
                                             location.extensionsAsString(),
                                             location.directoriesAsString(),
                                             location.dirExcludesAsString(),
                                             "",
                                             location.indexUpdateMode)
            self.myLocations.addLocation(duplicated, True)

    @pyqtSlot()
    def removeLocation (self) -> None:
        index = self.ui.listViewLocations.currentIndex ()
        if index.isValid():
            self.myLocations.model.removeRow(index.row())

    @pyqtSlot()
    def okClicked(self) -> None:
        index = self.ui.listViewLocations.currentIndex()
        if index.isValid():
            self.myLocations.saveDataForItem (index)

        # Check if there are search location with the same name and reject this
        names: Set[str] = set()
        for location in self.locations():
            name = location.displayName().lower()
            if name in names:
                QMessageBox.warning(self,
                                    self.tr("Duplicate search location names"),
                                    self.tr("Please choose a unique name for each search location.") + " '" + location.displayName() + "' " +   self.tr("is used more than once."),
                                    QMessageBox.StandardButtons(QMessageBox.Ok))
                return
            names.add(name)
        if self.__saveUserConfig():
            self.accept()
        else:
            self.reject()

    def __saveUserConfig (self) -> bool:
        locations = self.locations()
        config = Config (typeInfoFunc=AppConfig.configTypeInfo)
        for location in locations:
            locConf = Config(typeInfoFunc=indexTypeInfo)
            locConf.indexName = location.indexName
            locConf.extensions = location.extensionsAsString()
            locConf.directories =  location.directoriesAsString()
            locConf.dirExcludes = location.dirExcludesAsString()
            locConf.indexUpdateMode = location.indexUpdateMode
            locConf.indexType = location.indexType
            locConf.indexdb = location.indexdb
            setattr(config,  "Index_" + FileTools.removeInvalidFileChars(location.indexName),  locConf)
        config.sourceViewer.FontFamily = self.ui.fontComboBox.currentFont().family()
        config.sourceViewer.FontSize = self.ui.editFontSize.text()
        config.sourceViewer.TabWidth = self.ui.editTabWidth.text()
        config.sourceViewer.showLineNumbers = self.ui.checkShowLineNumbers.checkState() == Qt.Checked
        config.matchOverFiles = self.ui.checkMatchOverFiles.checkState() == Qt.Checked
        config.activateFirstMatch = self.ui.checkActivateFirstMatch.checkState() == Qt.Checked
        config.showCloseConfirmation = self.ui.checkConfirmClose.checkState() == Qt.Checked
        config.showRegexDialog = self.ui.checkRegexDialog.checkState() == Qt.Checked
        config.showMatchList = self.ui.checkShowMatchList.checkState() == Qt.Checked
        config.defaultLocation = self.defaultLocation()
        config.previewLines = int(self.ui.editPreviewLines.text())
        theme = ""
        if self.ui.checkDarkTheme.checkState() == Qt.Checked:
            theme = AppConfig.darkTheme
        config.theme = theme

        try:
            AppConfig.saveUserConfig (config)
        except:
            self.failedToSaveUserConfigMessage()
            return False
        else:
            updateDisplayNames = self.__getAddedOrChangedIndexedSearchLocations (self.searchLocations,  locations)
            if updateDisplayNames:
                # Show a user hint which allows to update added or changed indexes<ul>
                locationsHtml = "<ul>"
                for displayName in updateDisplayNames:
                    locationsHtml += "<li>" + displayName + "</li>"
                locationsHtml += "</ul>"
                text = self.tr(userHintUpdateIndex) % {"locations" : locationsHtml}
                result = showUserHint (self, "updateIndexes",  self.tr("Update indexes"), text, ButtonType.Yes, False, ButtonType.No,  True,  bShowHintAgain=True)
                if result == ButtonType.Yes:
                    self.updateChangedIndexes.emit(updateDisplayNames)

            return True

    def __getAddedOrChangedIndexedSearchLocations (self,  currentSearchLocations: List[IndexConfiguration],
                                                   newSearchLocations: List[IndexConfiguration]) -> List[str]:
        """Returns a list of display names of added or changed indexed search locations."""
        changedLocations: List[str] = []
        for location in newSearchLocations:
            if location.indexUpdateMode == IndexMode.ManualIndexUpdate or location.indexUpdateMode == IndexMode.TriggeredIndexUpdate:
                bFound = False
                for oldLocation in currentSearchLocations:
                    if location == oldLocation:
                        bFound = True
                        break
                if not bFound:
                    changedLocations.append(location.displayName())
        return changedLocations

    def failedToSaveUserConfigMessage(self) -> None:
        StackTraceMessageBox.show(self,
                                  self.tr("Failed to save user config"),
                                  self.tr("The user config file could not be saved to the user profile"))

def main() -> None:
    import sys
    app = QApplication(sys.argv)
    locations = [IndexConfiguration("Qt Source",  "h,cpp", "D:\\qt", "","D:\\index.dat"), IndexConfiguration("Linux", "", "", "", "")]
    conf = Config()
    conf.sourceViewer = Config()
    conf.sourceViewer.tabwidth = 4
    conf.sourceViewer.fontfamily = "Courier"
    conf.sourceViewer.fontsize = 10
    conf.matchOverFiles=True
    conf.showCloseConfirmation=True
    w = SettingsDialog(None,locations, locations, conf)
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()