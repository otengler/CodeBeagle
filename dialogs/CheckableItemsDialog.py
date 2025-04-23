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

from typing import List,Tuple
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import QApplication, QDialog, QWidget
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from typing import cast, Optional
from .Ui_CheckableItemsDialog import Ui_CheckableItemsDialog

class CheckableItemsDialog(QDialog):
    def __init__(self, title: str, bCheckAllState: bool, parent: Optional[QWidget]) -> None:
        super().__init__(parent)
        self.ui = Ui_CheckableItemsDialog()
        self.ui.setupUi(self)
        self.ui.buttonOK.clicked.connect(self.accept)
        self.ui.buttonCancel.clicked.connect(self.reject)
        self.ui.checkToggleAll.toggled.connect(self.checkAll)
        self.setWindowTitle(title)
        self.setProperty("shadeBackground", True) # fill background with gradient as defined in style sheet

        self.model = QStandardItemModel()

        self.ui.listViewItems.setModel(self.model)
        if bCheckAllState:
            self.ui.checkToggleAll.setCheckState(Qt.CheckState.Checked)
        else:
            self.ui.checkToggleAll.setCheckState(Qt.CheckState.Unchecked)

    def addItem(self, name: str, bCheck: bool=True) -> None:
        item = QStandardItem(name)
        item.setFlags(cast(Qt.ItemFlag, Qt.ItemFlag.ItemIsUserCheckable | item.flags()))
        if bCheck:
            item.setData(Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
        else:
            item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        self.model.appendRow(item)

    def checkedItems(self) -> List[Tuple[int,str]]:
        items = []
        for i in range(self.model.rowCount()):
            index = self.model.index(i, 0)
            if index.data(Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked:
                items.append((i, index.data()))
        return items

    @pyqtSlot(bool)
    def checkAll(self, bCheckAll: bool) -> None:
        if bCheckAll:
            flag = Qt.CheckState.Checked
        else:
            flag = Qt.CheckState.Unchecked
        for i in range(self.model.rowCount()):
            index = self.model.index(i, 0)
            self.model.setData(index, flag, Qt.ItemDataRole.CheckStateRole)

def main() -> None:
    import sys
    QApplication(sys.argv)
    w = CheckableItemsDialog("Choose indexes to update", True, None)
    w.addItem("Amber")
    w.addItem("Silver")
    w.addItem("Gold")
    w.show()
    if w.exec():
        items = w.checkedItems()
        print(items)
    sys.exit(0)

if __name__ == "__main__":
    main()
