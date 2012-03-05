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
from FileTools import fopen
from Ui_HelpViewerDialog import Ui_HelpViewerDialog

class HelpViewerDialog (QDialog):
    def __init__ (self, parent):
        super(HelpViewerDialog, self).__init__(parent,  Qt.Dialog | Qt.WindowMinMaxButtonsHint)
        self.ui = Ui_HelpViewerDialog()
        self.ui.setupUi(self)
        self.setProperty("shadeBackground", True) # fill background with gradient as defined in style sheet
        
    def showFile (self, name):
        try:
            with fopen(name) as file:
                text = file.read()
        except:
            text = self.trUtf8("Failed to open file")
        
        self.ui.textEditHelp.setFont(self.font())
        self.ui.textEditHelp.setLineWrapMode(QTextEdit.WidgetWidth)
        self.ui.textEditHelp.setHtml (text)
        
def main():    
    import sys
    app = QApplication(sys.argv) 
    w = HelpViewerDialog(None) 
    w.showFile("help.html")
    w.show() 
    sys.exit(app.exec_()) 

if __name__ == "__main__":
    main()
