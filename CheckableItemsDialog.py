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
from Ui_CheckableItemsDialog import Ui_CheckableItemsDialog

class CheckableItemsDialog (QDialog):
    def __init__ (self, title,  parent):
        super (CheckableItemsDialog, self).__init__(parent)
        self.ui = Ui_CheckableItemsDialog()
        self.ui.setupUi(self)
        self.setWindowTitle(title)
        self.setProperty("shadeBackground", True) # fill background with gradient as defined in style sheet
        
        self.model = QStandardItemModel()
        self.ui.listViewItems.setModel(self.model)
        
    def addItem (self, name):
        item = QStandardItem(name)
        item.setFlags(Qt.ItemIsUserCheckable | item.flags())
        item.setData(Qt.Unchecked, Qt.CheckStateRole)
        self.model.appendRow(item)
        
    def checkedItems(self):
        items = []
        for i in range(self.model.rowCount()):
            index = self.model.index(i, 0)
            if index.data (Qt.CheckStateRole) == Qt.Checked:
                items.append (index.data())
        return items
        
    @pyqtSlot(bool)
    def checkAll (self, bCheckAll):
        if bCheckAll:
            flag = Qt.Checked
        else:
            flag = Qt.Unchecked
        for i in range(self.model.rowCount()):
            index = self.model.index(i, 0)
            self.model.setData(index, flag,  Qt.CheckStateRole)

def main():    
    import sys
    app = QApplication(sys.argv)  
    w = CheckableItemsDialog("Choose indexes to update",  None) 
    w.addItem("Amber")
    w.addItem("Silver")
    w.addItem("Gold")
    w.show() 
    if w.exec():
        items = w.checkedItems()
        print (items)
    sys.exit(app.exec_()) 

if __name__ == "__main__":
    main()
    main()
