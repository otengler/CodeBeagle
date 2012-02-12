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
import ProgressBar

class AsynchronousTask (QThread):
    def __init__(self,  function , *args):
        super(AsynchronousTask, self).__init__(None) # Called with None to get rid of the thread once the python object is destroyed
        self.function = function
        self.args = args
        self.result = None
        
    def run(self):
        try:
            self.result = self.function (*self.args)
        except Exception as e:
            self.result = e

def execute (parent,  func,  *args):
    progress = None
    try:
        progress = ProgressBar.ProgressBar(parent)
        progress.show()
        
        searchTask = AsynchronousTask (func,  *args)
        QObject.connect(searchTask,  SIGNAL("finished()"),  progress.close)
        QObject.connect(searchTask,  SIGNAL("terminated()"),  progress.close)
        searchTask.start()
        progress.exec()
        searchTask.wait()
        
        # If the thread raised an exception re-raise it in the main thread
        if isinstance(searchTask.result,Exception):
            raise searchTask.result
        return searchTask.result
    finally:
        if progress:
            progress.close()
            
