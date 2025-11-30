# -*- coding: utf-8 -*-
"""
Copyright (C) 2025 Oliver Tengler

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

from typing import List, Optional
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import QDialog, QWidget, QTableWidgetItem, QMessageBox
from fulltextindex.IndexConfiguration import IndexConfiguration
from fulltextindex.IndexUpdater import IndexUpdater
from .Ui_ExcludedExtensionsDialog import Ui_ExcludedExtensionsDialog

class ExcludedExtensionsDialog(QDialog):
    def __init__(self, parent: Optional[QWidget], indexConfig: IndexConfiguration) -> None:
        super().__init__(parent)
        self.ui = Ui_ExcludedExtensionsDialog()
        self.ui.setupUi(self)
        self.setProperty("shadeBackground", True)

        self.indexConfig = indexConfig

        # Connect signals
        self.ui.buttonAdd.clicked.connect(self.accept)
        self.ui.buttonCancel.clicked.connect(self.reject)
        self.ui.checkSelectAll.toggled.connect(self.selectAll)

        # Load and display data
        self.__loadExcludedExtensions()

    def __loadExcludedExtensions(self) -> None:
        """Load excluded extensions from the database and populate the table."""        
        indexUpdater = IndexUpdater(self.indexConfig.indexdb)
        extensions = indexUpdater.getExcludedExtensions()

        if not extensions:
            self.__showNoDataMessage()
            return

        # Populate table
        self.ui.tableExtensions.setRowCount(len(extensions))
        for row, (ext, count) in enumerate(extensions):
            # Extension column
            extItem = QTableWidgetItem(ext if ext else "(no extension)")
            extItem.setFlags(extItem.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.ui.tableExtensions.setItem(row, 0, extItem)

            # Count column
            countItem = QTableWidgetItem(str(count))
            countItem.setFlags(countItem.flags() & ~Qt.ItemFlag.ItemIsEditable)
            # Right-align the count
            countItem.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.ui.tableExtensions.setItem(row, 1, countItem)

        # Resize columns to content
        self.ui.tableExtensions.resizeColumnsToContents()

    def __showNoDataMessage(self) -> None:
        """Show message when no excluded extensions data is available."""
        QMessageBox.information(self,
            self.tr("No Data"),
            self.tr("No excluded extensions data available. This could mean:\n\n"
                   "1. The index has not been updated yet\n"
                   "2. All files in the directories matched the configured extensions\n"
                   "3. The index database is from an older version"))
        self.reject()

    @pyqtSlot(bool)
    def selectAll(self, checked: bool) -> None:
        """Select or deselect all rows."""
        if checked:
            self.ui.tableExtensions.selectAll()
        else:
            self.ui.tableExtensions.clearSelection()

    def getSelectedExtensions(self) -> List[str]:
        """Return list of selected extensions."""
        extensions = []
        selectedRows = set(index.row() for index in self.ui.tableExtensions.selectedIndexes())

        for row in sorted(selectedRows):
            extItem = self.ui.tableExtensions.item(row, 0)
            if extItem:
                ext = extItem.text()
                if ext != "(no extension)":
                    extensions.append(ext)
                else:
                    extensions.append(".")

        return extensions
