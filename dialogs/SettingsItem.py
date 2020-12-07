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
from typing import cast
from PyQt5.QtGui import QFocusEvent
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QWidget, QFileDialog
from tools import FileTools
import AppConfig
from fulltextindex.IndexConfiguration import IndexMode, IndexType
from .Ui_SettingsItem import Ui_SettingsItem

class SettingsItem (QWidget):
    dataChanged = pyqtSignal()

    def __init__ (self, parent: QWidget) -> None:
        super ().__init__(parent)
        self.ui = Ui_SettingsItem()
        self.ui.setupUi(self)

        self.buildDBName = True
        self.ui.editName.textEdited.connect(self.nameEdited)
        self.ui.editIndexDB.textEdited.connect(self.indexDBEdited)

        self.ui.editName.textEdited.connect(self.dataChanged)
        self.ui.editDirectories.textEdited.connect(self.dataChanged)
        self.ui.comboExtensions.lineEdit().textEdited.connect(self.dataChanged)
        self.ui.comboIndexUpdateMode.currentIndexChanged.connect(self.updateIndexModeChanged)
        self.__addEntriesForExtensionsCombo()
        self.__addEntriesForIndexUpdateModeCombo()
        self.__addEntriesForIndexTypeCombo()

    def __addEntriesForExtensionsCombo (self) -> None:
        try:
            for exts in AppConfig.appConfig().PredefinedExtensions.values():
                self.ui.comboExtensions.addItem(exts)
        except AttributeError:
            pass

    def __addEntriesForIndexUpdateModeCombo(self) -> None:
        self.ui.comboIndexUpdateMode.addItem("Do not generate an index")
        self.ui.comboIndexUpdateMode.addItem("Manual index update with CodeBeagle")
        self.ui.comboIndexUpdateMode.addItem("Update index when UpdateIndex.exe is run")
        #self.ui.comboIndexUpdateMode.addItem("Keep index permanently up to date")

    def __addEntriesForIndexTypeCombo(self) -> None:
        self.ui.comboIndexType.addItem("Index file content")
        self.ui.comboIndexType.addItem("Index file name")
        self.ui.comboIndexType.addItem("Index file content and name")

    def focusInEvent (self, _: QFocusEvent) -> None:
        self.ui.editName.setFocus(Qt.ActiveWindowFocusReason)

    @pyqtSlot(str)
    def nameEdited(self, text: str) -> None:
        """Suggest a name for the index db."""
        if self.buildDBName and self.indexGenerationEnabled():
            self.__updateDBName(text)

    def __updateDBName(self, text: str) -> None:
        location = AppConfig.userConfigPath()
        location = os.path.join (location,  FileTools.removeInvalidFileChars(text)+".dat")
        self.ui.editIndexDB.setText(location)

    @pyqtSlot(str)
    def indexDBEdited(self, text: str) -> None:
        if text:
            self.buildDBName = False
        else:
            self.buildDBName = True

    @pyqtSlot(int)
    def updateIndexModeChanged (self,  index: IndexMode) -> None:
        self.__enableBasedOnUpdateModeSetting(index)
        indexWanted = (index != IndexMode.NoIndexWanted)
        if indexWanted and not self.indexDB():
            self.__updateDBName(self.name())
        self.dataChanged.emit()

    @pyqtSlot()
    def browseForDirectory(self) -> None:
        directory = QFileDialog.getExistingDirectory (
            self,
            self.tr("Choose directory to search or index"),
            "",
            QFileDialog.Options(QFileDialog.ShowDirsOnly))

        if directory:
            self.ui.editDirectories.setText (FileTools.correctPath(directory))
            self.dataChanged.emit()

    @pyqtSlot()
    def browseForIndexDB(self) -> None:
        indexDB = QFileDialog.getSaveFileName(
            None,
            self.tr("Choose file for index DB"),
            "",
            self.tr("*.dat"),
            None,
            QFileDialog.Options(QFileDialog.DontConfirmOverwrite))[0] # tuple returned, selection and used filter

        if indexDB:
            self.ui.editIndexDB.setText (FileTools.correctPath(indexDB))

    def nameSelectAll (self) -> None:
        self.ui.editName.selectAll()

    def setData (self, name: str, directories: str, extensions: str,  dirExcludes: str, indexUpdateMode: IndexMode, indexDB: str, indexType: IndexType) -> None:
        self.ui.editName.setText (name)
        self.ui.editDirectories.setText (directories)
        self.ui.editExcludeDirectories.setText (dirExcludes)
        self.ui.comboExtensions.lineEdit().setText (extensions)

        self.buildDBName = False
        if indexDB:
            self.ui.editIndexDB.setText (indexDB)
        else:
            if indexUpdateMode != IndexMode.NoIndexWanted:
                self.buildDBName = True
                self.__updateDBName (name)
            else:
                self.ui.editIndexDB.setText ("")

        self.ui.comboIndexType.setCurrentIndex(indexType)
        self.ui.comboIndexUpdateMode.setCurrentIndex(indexUpdateMode)

    def name (self) -> str:
        return cast(str,self.ui.editName.text())

    def directories (self) -> str:
        return cast(str,self.ui.editDirectories.text())

    def dirExcludes (self) -> str:
        return cast(str,self.ui.editExcludeDirectories.text())

    def extensions (self) -> str:
        return cast(str,self.ui.comboExtensions.currentText())

    def indexDB (self) -> str:
        return cast(str,self.ui.editIndexDB.text())

    def indexGenerationEnabled (self) -> bool:
        return cast(bool, self.ui.comboIndexUpdateMode.currentIndex() != IndexMode.NoIndexWanted)

    def indexUpdateMode(self) -> IndexMode:
        return cast(IndexMode,self.ui.comboIndexUpdateMode.currentIndex())

    def indexType(self) -> IndexType:
        return cast(IndexType,self.ui.comboIndexType.currentIndex())

    def resetAndDisable(self) -> None:
        self.ui.editName.setText("")
        self.ui.editExcludeDirectories.setText("")
        self.ui.comboExtensions.lineEdit().setText("")
        self.ui.editDirectories.setText("")
        self.ui.editIndexDB.setText("")
        self.ui.comboIndexType.setCurrentIndex(IndexType.FileContentAndName)
        self.enable(False)

    def enable(self, bEnable:bool=True) -> None:
        self.ui.editName.setEnabled(bEnable)
        self.ui.editExcludeDirectories.setEnabled(bEnable)
        self.ui.comboExtensions.setEnabled(bEnable)
        self.ui.editDirectories.setEnabled(bEnable)
        self.ui.buttonDirectory.setEnabled(bEnable)
        if bEnable and not self.indexGenerationEnabled():
            bEnable = False
        self.ui.editIndexDB.setEnabled(bEnable)
        self.ui.buttonBrowseIndexLocation.setEnabled(bEnable)
        self.ui.comboIndexType.setEnabled(bEnable)

    def __enableBasedOnUpdateModeSetting(self, indexMode: IndexMode) -> None:
        indexWanted = (indexMode != IndexMode.NoIndexWanted)
        self.ui.editIndexDB.setEnabled(indexWanted)
        self.ui.comboIndexType.setEnabled(indexWanted)
        self.ui.buttonBrowseIndexLocation.setEnabled(indexWanted)