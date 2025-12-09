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

from typing import List, Optional, Tuple, Any
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import QDialog, QWidget, QTableWidgetItem, QMessageBox
from fulltextindex.IndexConfiguration import IndexConfiguration
from fulltextindex.IndexUpdater import IndexUpdater
from .Ui_ExcludedExtensionsDialog import Ui_ExcludedExtensionsDialog


class SortableTableWidgetItem(QTableWidgetItem):
    """QTableWidgetItem that sorts by UserRole data instead of display text."""

    def __lt__(self, other: Any) -> bool:
        """Compare items using UserRole data for sorting."""
        my_data = self.data(Qt.ItemDataRole.UserRole)
        other_data = other.data(Qt.ItemDataRole.UserRole)

        # If both have UserRole data, compare those
        if my_data is not None and other_data is not None:
            return bool(my_data < other_data)

        # Fallback to text comparison
        return bool(super().__lt__(other))

# Extension relevance classification
HIGH_RELEVANCE_EXTENSIONS = {
    # Common programming languages
    'py', 'pyw', 'java', 'c', 'cpp', 'cc', 'cxx', 'h', 'hpp', 'hxx', 'cs', 'vb',
    'js', 'ts', 'jsx', 'tsx', 'go', 'rs', 'rb', 'php', 'pl', 'pm', 'swift', 'kt',
    'kts', 'm', 'mm', 'scala', 'clj', 'cljs', 'erl', 'hrl', 'ex', 'exs', 'elm',
    'hs', 'lhs', 'ml', 'mli', 'fs', 'fsi', 'fsx', 'r', 'lua', 'tcl', 'sh', 'bash',
    'zsh', 'fish', 'ps1', 'psm1', 'bat', 'cmd', 'd', 'nim', 'v', 'zig', 'odin',
    'ada', 'adb', 'ads', 'f', 'f90', 'f95', 'f03', 'f08', 'pas', 'pp', 'asm', 's',
    'sql', 'vbs', 'vba', 'ahk', 'au3', 'dart', 'groovy', 'perl', 'raku', 'jl'
}

MEDIUM_RELEVANCE_EXTENSIONS = {
    # Documents and configuration files
    'xml', 'json', 'yaml', 'yml', 'toml', 'ini', 'cfg', 'conf', 'config', 'md',
    'rst', 'txt', 'csv', 'tsv', 'log', 'properties', 'env',
    # IDE and build files
    'sln', 'csproj', 'vbproj', 'fsproj', 'vcxproj', 'xcodeproj', 'pbxproj',
    'gradle', 'maven', 'pom', 'make', 'cmake', 'makefile', 'dockerfile', 'props',
    'targets', 'nuspec', 'vcproj', 'suo', 'user', 'filters', 'editorconfig',
    'gitignore', 'gitattributes', 'html', 'htm', 'css', 'scss', 'sass', 'less',
    'svg', 'xaml', 'qml', 'ui', 'rc', 'resx', 'settings'
}

def classify_extension_relevance(extension: str) -> str:
    """
    Classify an extension into High, Medium, or Low relevance.

    Args:
        extension: File extension (without dot) or empty string for no extension

    Returns:
        "High", "Medium", or "Low"
    """
    if not extension or extension == ".":
        return "Low"

    ext_lower = extension.lstrip('.').lower()

    if ext_lower in HIGH_RELEVANCE_EXTENSIONS:
        return "High"
    elif ext_lower in MEDIUM_RELEVANCE_EXTENSIONS:
        return "Medium"
    else:
        return "Low"

class ExcludedExtensionsDialog(QDialog):
    def __init__(self, parent: Optional[QWidget], indexConfig: IndexConfiguration) -> None:
        super().__init__(parent)
        self.ui = Ui_ExcludedExtensionsDialog()
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]
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

        # Temporarily disable sorting while populating
        self.ui.tableExtensions.setSortingEnabled(False)

        # Populate table
        self.ui.tableExtensions.setRowCount(len(extensions))
        relevance_order = {"High": 0, "Medium": 1, "Low": 2}

        for row, (ext, count) in enumerate(extensions):
            # Extension column
            extItem = QTableWidgetItem(ext if ext else "(no extension)")
            extItem.setFlags(extItem.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.ui.tableExtensions.setItem(row, 0, extItem)

            # Count column - use numeric sorting
            countItem = SortableTableWidgetItem()
            countItem.setData(Qt.ItemDataRole.DisplayRole, str(count))
            countItem.setData(Qt.ItemDataRole.UserRole, count)  # Store numeric value for sorting
            countItem.setFlags(countItem.flags() & ~Qt.ItemFlag.ItemIsEditable)
            countItem.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
            self.ui.tableExtensions.setItem(row, 1, countItem)

            # Relevance column
            relevance = classify_extension_relevance(ext)
            relevanceItem = SortableTableWidgetItem(relevance)
            relevanceItem.setData(Qt.ItemDataRole.UserRole, relevance_order[relevance])  # Store numeric order for sorting
            relevanceItem.setFlags(relevanceItem.flags() & ~Qt.ItemFlag.ItemIsEditable)
            relevanceItem.setTextAlignment(int(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter))
            self.ui.tableExtensions.setItem(row, 2, relevanceItem)

        # Re-enable sorting and sort by relevance (column 2) in ascending order (High first)
        self.ui.tableExtensions.setSortingEnabled(True)
        self.ui.tableExtensions.sortItems(2, Qt.SortOrder.AscendingOrder)

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
