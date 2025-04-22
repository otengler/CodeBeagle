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
from typing import List, Dict, Optional, Any
from PyQt5.QtCore import Qt, QFileInfo, QAbstractListModel, QModelIndex, QSize
from PyQt5.QtWidgets import QWidget
import SourceViewer
from typing import Optional

# Returns the first difference in two strings
def firstDifference(s1: str, s2: str) -> int:
    for (i,c1),c2 in zip(enumerate(s1),s2):
        if c1 != c2:
            return i
    return min(len(s1),len(s2))

class StringListModel(QAbstractListModel):
    def __init__(self, filelist: List[str],  parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.filelist = filelist
        self.editorState: Dict[QModelIndex, SourceViewer.EditorState] = {} # maps from file index to an editor state object
        self.sizeHint: Optional[QSize] = None
        self.cutLeft = self.__computeCutLeft()
        self.selectedFileIndex = -1

    def getEditorState(self, row:QModelIndex) -> Optional[SourceViewer.EditorState]:
        return self.editorState.get(row)

    def setEditorState(self, row:QModelIndex, state:SourceViewer.EditorState) -> None:
        self.editorState[row] = state

    def getSelectedFileIndex (self) -> int:
        return self.selectedFileIndex

    def setSelectedFileIndex (self,  index: int) -> None:
        self.selectedFileIndex = index

    def setSizeHint(self, sizeHint: QSize) -> None:
        self.sizeHint = sizeHint

    # If all entries in the list start with the same directory we don't need to display this prefix.
    def __computeCutLeft (self) -> int:
        if len(self.filelist)<2:
            return 0
        first = os.path.split(self.filelist[0])[0] + os.path.sep
        last = os.path.split(self.filelist[-1])[0] + os.path.sep
        firstDiff = firstDifference(first, last)
        if firstDiff is not None:
            # Only cut full directories - go back to the last path seperator
            common = first[:firstDiff]
            lastSep = common.rfind(os.path.sep)
            if lastSep != -1:
                return lastSep
            return firstDiff
        return len(first) # The whole string is equal

    def rowCount(self, _:QModelIndex = QModelIndex()) -> int:
        return len(self.filelist)

    def data(self, index: QModelIndex, role = ...) -> Any:
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            if self.cutLeft:
                return "..."+self.filelist[index.row()][self.cutLeft:]
            return self.filelist[index.row()]
        if role == Qt.ItemDataRole.UserRole:
            return self.filelist[index.row()]
        if role == Qt.ItemDataRole.SizeHintRole:
            return self.sizeHint
        if role == Qt.ItemDataRole.ToolTipRole and self.cutLeft:
            name = self.filelist[index.row()]
            fileinfo = QFileInfo(name)
            lastmodified = fileinfo.lastModified().toString()
            # replace with slahses as this will not break the tooltip after the drive letter
            return name.replace("\\", "/") + "<br/>" + lastmodified
        return None
