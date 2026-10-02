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

import os
from typing import cast, Optional
from PySide6.QtGui import QFocusEvent
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import QWidget, QFileDialog
from tools import FileTools
import AppConfig
from fulltextindex.IndexConfiguration import IndexMode, IndexType
from .Ui_SettingsItem import Ui_SettingsItem

class SettingsItem (QWidget):
    dataChanged = Signal()
    showExcludedExtensionsClicked = Signal()

    def __init__ (self, parent: QWidget) -> None:
        super ().__init__(parent)
        self.ui = Ui_SettingsItem()
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]

        self.buildDBName = True
        self.ui.editName.textEdited.connect(self.nameEdited)
        self.ui.editIndexDB.textEdited.connect(self.indexDBEdited)

        self.ui.editName.textEdited.connect(self.dataChanged)
        self.ui.editDirectories.textEdited.connect(self.dataChanged)
        if extLineEdit := self.ui.comboExtensions.lineEdit():
            extLineEdit.textEdited.connect(self.dataChanged)
        self.ui.checkApiAccess.stateChanged.connect(self.dataChanged)
        self.ui.comboIndexUpdateMode.currentIndexChanged.connect(self.updateIndexModeChanged)

        # Wire button signals in code (not in .ui file)
        self.ui.buttonDirectory.clicked.connect(self.browseForDirectory)
        self.ui.buttonBrowseIndexLocation.clicked.connect(self.browseForIndexDB)
        self.ui.buttonShowExcluded.clicked.connect(self.showExcludedExtensions)
        self.ui.buttonExcludeDirectory.clicked.connect(self.browseForExcludeDirectory)
        self.ui.buttonExcludeFile.clicked.connect(self.browseForExcludeFile)

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
        self.ui.comboIndexUpdateMode.addItem("Manual index update in CodeBeagle")
        self.ui.comboIndexUpdateMode.addItem("Update index when UpdateIndex.exe is run")
        #self.ui.comboIndexUpdateMode.addItem("Keep index permanently up to date")

    def __addEntriesForIndexTypeCombo(self) -> None:
        self.ui.comboIndexType.addItem("Index file content")
        self.ui.comboIndexType.addItem("Index file name")
        self.ui.comboIndexType.addItem("Index file content and name")

    def focusInEvent (self, _: Optional[QFocusEvent]) -> None:
        self.ui.editName.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    @Slot(str)
    def nameEdited(self, text: str) -> None:
        """Suggest a name for the index db."""
        if self.buildDBName and self.indexGenerationEnabled():
            self.__updateDBName(text)

    def __updateDBName(self, text: str) -> None:
        location = AppConfig.userConfigPath()
        location = os.path.join (location,  FileTools.removeInvalidFileChars(text)+".dat")
        self.ui.editIndexDB.setText(location)

    @Slot(str)
    def indexDBEdited(self, text: str) -> None:
        if text:
            self.buildDBName = False
        else:
            self.buildDBName = True

    @Slot(int)
    def updateIndexModeChanged (self,  index: IndexMode) -> None:
        self.__enableBasedOnUpdateModeSetting(index)
        indexWanted = (index != IndexMode.NoIndexWanted)
        if indexWanted and not self.indexDB():
            self.__updateDBName(self.name())
        self.dataChanged.emit()

    @Slot()
    def browseForDirectory(self) -> None:
        directory = QFileDialog.getExistingDirectory (
            self,
            self.tr("Choose directory to search or index"),
            "",
            QFileDialog.Option(QFileDialog.Option.ShowDirsOnly))

        if directory:
            self.ui.editDirectories.setText (FileTools.correctPath(directory))
            self.dataChanged.emit()

    @Slot()
    def browseForExcludeDirectory(self) -> None:
        directory = QFileDialog.getExistingDirectory (
            self,
            self.tr("Choose directory to exclude"),
            "",
            QFileDialog.Option(QFileDialog.Option.ShowDirsOnly))

        if directory:
            currentText = self.ui.editExcludeDirectories.text()
            cleaned = FileTools.correctPath(directory)
            if currentText:
                self.ui.editExcludeDirectories.setText(currentText + "," + cleaned)
            else:
                self.ui.editExcludeDirectories.setText(cleaned)
            self.dataChanged.emit()

    @Slot()
    def browseForExcludeFile(self) -> None:
        file, _ = QFileDialog.getOpenFileName (
            self,
            self.tr("Choose file to exclude"),
            "")

        if file:
            currentText = self.ui.editExcludeFiles.text()
            cleaned = FileTools.correctPath(file)
            if currentText:
                self.ui.editExcludeFiles.setText(currentText + "," + cleaned)
            else:
                self.ui.editExcludeFiles.setText(cleaned)
            self.dataChanged.emit()

    @Slot()
    def browseForIndexDB(self) -> None:
        indexDB = QFileDialog.getSaveFileName(
            None,
            self.tr("Choose file for index DB"),
            "",
            self.tr("*.dat"),
            options=QFileDialog.Option(QFileDialog.Option.DontConfirmOverwrite))[0] # tuple returned, selection and used filter

        if indexDB:
            self.ui.editIndexDB.setText (FileTools.correctPath(indexDB))

    def nameSelectAll (self) -> None:
        self.ui.editName.selectAll()

    def setData (self, name: str, directories: str, extensions: str,  dirExcludes: str, indexUpdateMode: IndexMode, indexDB: str, indexType: IndexType, apiAccess: bool = False, fileExcludes: str = "") -> None:
        self.ui.editName.setText (name)
        self.ui.editDirectories.setText (directories)
        self.ui.editExcludeDirectories.setText (dirExcludes)
        self.ui.editExcludeFiles.setText (fileExcludes)
        extLineEdit = self.ui.comboExtensions.lineEdit()
        if extLineEdit:
            extLineEdit.setText (extensions)

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
        self.ui.checkApiAccess.setChecked(apiAccess)

    def apiAccess(self) -> bool:
        return self.ui.checkApiAccess.isChecked()

    def name (self) -> str:
        return self.ui.editName.text()

    def directories (self) -> str:
        return self.ui.editDirectories.text()

    def dirExcludes (self) -> str:
        return self.ui.editExcludeDirectories.text()

    def fileExcludes (self) -> str:
        return self.ui.editExcludeFiles.text()

    def extensions (self) -> str:
        return self.ui.comboExtensions.currentText()

    def indexDB (self) -> str:
        return self.ui.editIndexDB.text()

    def indexGenerationEnabled (self) -> bool:
        return self.ui.comboIndexUpdateMode.currentIndex() != IndexMode.NoIndexWanted

    def indexUpdateMode(self) -> IndexMode:
        return cast(IndexMode,self.ui.comboIndexUpdateMode.currentIndex())

    def indexType(self) -> IndexType:
        return cast(IndexType,self.ui.comboIndexType.currentIndex())

    def resetAndDisable(self) -> None:
        self.ui.editName.setText("")
        self.ui.editExcludeDirectories.setText("")
        self.ui.editExcludeFiles.setText("")
        if le := self.ui.comboExtensions.lineEdit():
            le.setText("")
        self.ui.editDirectories.setText("")
        self.ui.editIndexDB.setText("")
        self.ui.comboIndexType.setCurrentIndex(IndexType.FileContentAndName)
        self.ui.checkApiAccess.setChecked(False)
        self.enable(False)

    def enable(self, bEnable:bool=True) -> None:
        self.ui.editName.setEnabled(bEnable)
        self.ui.editExcludeDirectories.setEnabled(bEnable)
        self.ui.buttonExcludeDirectory.setEnabled(bEnable)
        self.ui.editExcludeFiles.setEnabled(bEnable)
        self.ui.buttonExcludeFile.setEnabled(bEnable)
        self.ui.comboExtensions.setEnabled(bEnable)
        self.ui.editDirectories.setEnabled(bEnable)
        self.ui.buttonDirectory.setEnabled(bEnable)
        if bEnable and not self.indexGenerationEnabled():
            bEnable = False
        self.ui.editIndexDB.setEnabled(bEnable)
        self.ui.buttonBrowseIndexLocation.setEnabled(bEnable)
        self.ui.comboIndexType.setEnabled(bEnable)
        self.ui.comboIndexUpdateMode.setEnabled(bEnable)
        self.ui.checkApiAccess.setEnabled(bEnable)
        # Note: buttonShowExcluded visibility is controlled by LocationControl.__updateShowExcludedButtonVisibility

    def __enableBasedOnUpdateModeSetting(self, indexMode: IndexMode) -> None:
        indexWanted = (indexMode != IndexMode.NoIndexWanted)
        self.ui.editIndexDB.setEnabled(indexWanted)
        self.ui.comboIndexType.setEnabled(indexWanted)
        self.ui.buttonBrowseIndexLocation.setEnabled(indexWanted)

    @Slot()
    def showExcludedExtensions(self) -> None:
        """Emit signal to show excluded extensions dialog."""
        self.showExcludedExtensionsClicked.emit()