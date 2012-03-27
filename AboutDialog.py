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

import sys
from PyQt4.QtCore import * 
from PyQt4.QtGui import *
from Ui_AboutDialog import Ui_AboutDialog
import AppConfig

class AboutDialog (QDialog):
    def __init__ (self, parent):
        super(AboutDialog, self).__init__(parent)
        self.ui = Ui_AboutDialog()
        self.ui.setupUi(self)
        version = sys.version_info
        pythonAndQt = " (Python %u.%u.%u, Qt %s)" % (version.major, version.minor, version.micro, qVersion())
        self.ui.labelVersion.setText(self.trUtf8("Version") + " " + AppConfig.appVersion + pythonAndQt)
        self.setProperty("shadeBackground", True) # fill background with gradient as defined in style sheet
        
def main():    
    import sys
    app = QApplication(sys.argv) 
    w = AboutDialog(None) 
    w.show() 
    sys.exit(app.exec_()) 

if __name__ == "__main__":
    main()
