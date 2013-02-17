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
import threading

class AsynchronousTask (QThread):
    def __init__(self,  function , *args,  bEnableCancel=False,  cancelAction=None):
        super(AsynchronousTask, self).__init__(None) # Called with None to get rid of the thread once the python object is destroyed
        self.function = function
        self.args = args
        self.bEnableCancel = bEnableCancel
        self.cancelAction = cancelAction
        self.result = None
        self.cancelEvent = None
        if self.bEnableCancel:
            self.cancelEvent = threading.Event()
        
    def run(self):
        try:
            self.result = self.function (*self.args, cancelEvent=self.cancelEvent)
        except Exception as e:
            self.result = e
            
    @pyqtSlot()
    def cancel (self):
        if self.cancelEvent:
            self.cancelEvent.set()
        if self.cancelAction:
            self.cancelAction()

def execute (parent,  func,  *args,  bEnableCancel=False, cancelAction=None):
    progress = None
    try:
        progress = ProgressBar.ProgressBar(parent,  bEnableCancel)
        
        searchTask = AsynchronousTask (func,  *args, bEnableCancel=bEnableCancel, cancelAction=cancelAction)
        QObject.connect(searchTask,  SIGNAL("finished()"),  progress.close)
        QObject.connect(searchTask,  SIGNAL("terminated()"),  progress.close)
        
        progress.onCancelClicked.connect (searchTask.cancel)
        progress.show()
        
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
            
