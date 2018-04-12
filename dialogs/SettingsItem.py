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
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QWidget, QFileDialog
import tools.FileTools as FileTools
import AppConfig
import IndexConfiguration
from .Ui_SettingsItem import Ui_SettingsItem

class SettingsItem (QWidget):
    dataChanged = pyqtSignal()

    def __init__ (self, parent):
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

    def __addEntriesForExtensionsCombo (self):
        try:
            for exts in AppConfig.appConfig().PredefinedExtensions.values():
                self.ui.comboExtensions.addItem(exts)
        except AttributeError:
            pass

    def __addEntriesForIndexUpdateModeCombo(self):
        self.ui.comboIndexUpdateMode.addItem("Do not generate an index")
        self.ui.comboIndexUpdateMode.addItem("Manual index update with CodeBeagle")
        self.ui.comboIndexUpdateMode.addItem("Update index when UpdateIndex.exe is run")
        #self.ui.comboIndexUpdateMode.addItem("Keep index permanently up to date")

    def focusInEvent (self, event):
        self.ui.editName.setFocus(Qt.ActiveWindowFocusReason)

    @pyqtSlot(str)
    def nameEdited(self, text):
        """Suggest a name for the index db."""
        if self.buildDBName and self.indexGenerationEnabled():
            self.__updateDBName(text)

    def __updateDBName(self, text):
        location = AppConfig.userConfigPath()
        location = os.path.join (location,  FileTools.removeInvalidFileChars(text)+".dat")
        self.ui.editIndexDB.setText(location)

    @pyqtSlot(str)
    def indexDBEdited(self, text):
        if text:
            self.buildDBName = False
        else:
            self.buildDBName = True

    @pyqtSlot(int)
    def updateIndexModeChanged (self,  index):
        indexWanted = (index != IndexConfiguration.NoIndexWanted)
        self.ui.editIndexDB.setEnabled(indexWanted)
        self.ui.buttonBrowseIndexLocation.setEnabled(indexWanted)
        if indexWanted and not self.indexDB():
            self.__updateDBName(self.name())
        self.dataChanged.emit()

    @pyqtSlot()
    def browseForDirectory(self):
        directory = QFileDialog.getExistingDirectory (
            self,
            self.tr("Choose directory to search or index"),
            "",
            QFileDialog.Options(QFileDialog.ShowDirsOnly))

        if directory:
            self.ui.editDirectories.setText (FileTools.correctPath(directory))
            self.dataChanged.emit()

    @pyqtSlot()
    def browseForIndexDB(self):
        indexDB = QFileDialog.getSaveFileName(
            None,
            self.tr("Choose file for index DB"),
            "",
            self.tr("*.dat"),
            None,
            QFileDialog.Options(QFileDialog.DontConfirmOverwrite))[0] # tuple returned, selection and used filter

        if indexDB:
            self.ui.editIndexDB.setText (FileTools.correctPath(indexDB))

    def nameSelectAll (self):
        self.ui.editName.selectAll()

    def setData (self, name, directories, extensions,  dirExcludes, indexUpdateMode, indexDB):
        self.ui.editName.setText (name)
        self.ui.editDirectories.setText (directories)
        self.ui.editExcludeDirectories.setText (dirExcludes)
        self.ui.comboExtensions.lineEdit().setText (extensions)

        self.buildDBName = False
        if indexDB:
            self.ui.editIndexDB.setText (indexDB)
        else:
            if indexUpdateMode != IndexConfiguration.NoIndexWanted:
                self.buildDBName = True
                self.__updateDBName (name)
            else:
                self.ui.editIndexDB.setText ("")

        self.ui.comboIndexUpdateMode.setCurrentIndex(indexUpdateMode)

    def name (self):
        return self.ui.editName.text()

    def directories (self):
        return self.ui.editDirectories.text()

    def dirExcludes (self):
        return self.ui.editExcludeDirectories.text()

    def extensions (self):
        return self.ui.comboExtensions.currentText()

    def indexDB (self):
        return self.ui.editIndexDB.text()

    def indexGenerationEnabled (self):
        return self.ui.comboIndexUpdateMode.currentIndex != IndexConfiguration.NoIndexWanted

    def indexUpdateMode(self):
        return self.ui.comboIndexUpdateMode.currentIndex()

    def resetAndDisable(self):
        self.ui.editName.setText("")
        self.ui.editExcludeDirectories.setText("")
        self.ui.comboExtensions.lineEdit().setText("")
        self.ui.editDirectories.setText("")
        self.ui.editIndexDB.setText("")
        self.enable(False)

    def enable(self, bEnable=True):
        self.ui.editName.setEnabled(bEnable)
        self.ui.editExcludeDirectories.setEnabled(bEnable)
        self.ui.comboExtensions.setEnabled(bEnable)
        self.ui.editDirectories.setEnabled(bEnable)
        self.ui.buttonDirectory.setEnabled(bEnable)
        if bEnable and not self.indexGenerationEnabled():
            bEnable = False
        self.ui.editIndexDB.setEnabled(bEnable)
        self.ui.buttonBrowseIndexLocation.setEnabled(bEnable)
