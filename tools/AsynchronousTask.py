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

import threading
from typing import Callable, Any
from PyQt5.QtCore import QThread, pyqtSlot, QObject
from dialogs.ProgressBar import ProgressBar

CancelFunction = Callable[[],None]

class AsynchronousTask (QThread):
    def __init__(self, function: Callable, *args: Any, bEnableCancel: bool=False, cancelAction: CancelFunction=None) -> None:
        super().__init__(None) # Called with None to get rid of the thread once the python object is destroyed
        self.function = function
        self.args = args
        self.bEnableCancel = bEnableCancel
        self.cancelAction = cancelAction
        self.result: Any = None
        self.exception: Exception
        self.hasException = False
        self.cancelEvent = None
        if self.bEnableCancel:
            self.cancelEvent = threading.Event()

    def run(self) -> None:
        try:
            if self.cancelEvent:
                self.result = self.function(*self.args, cancelEvent=self.cancelEvent)
            else:
                self.result = self.function(*self.args)
        except Exception as e:
            self.exception = e
            self.hasException = True

    @pyqtSlot()
    def cancel(self) -> None:
        if self.cancelEvent:
            self.cancelEvent.set()
        if self.cancelAction:
            self.cancelAction()

def execute(parent: QObject, func:Callable, *args: Any, bEnableCancel: bool=False, cancelAction: CancelFunction=None) -> Any:
    """
    Executes the action performed by the callable 'func' called with *args in a seperate thread.
    During the action a progress bar is shown. If 'bEnableCancel' is true the callable is
    passed the named parameter 'cancelEvent'. It contains an event object whose 'is_set' function
    can be used to test if it is signalled.
    """
    try:
        progress = ProgressBar(parent, bEnableCancel)

        searchTask = AsynchronousTask(func, *args, bEnableCancel=bEnableCancel, cancelAction=cancelAction)
        searchTask.finished.connect(progress.close)
        progress.onCancelClicked.connect(searchTask.cancel)
        progress.show()

        searchTask.start()
        progress.exec()
        searchTask.wait()

        # If the thread raised an exception re-raise it in the main thread
        if searchTask.hasException:
            raise searchTask.exception
        return searchTask.result
    finally:
        if progress:
            progress.close()
