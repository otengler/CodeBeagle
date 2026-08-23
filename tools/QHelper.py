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

from PySide2.QtWidgets import QAction
from PySide2.QtCore import QObject, Signal, Qt, SignalInstance
from PySide2.QtGui import QKeySequence
from typing import Optional, Union, Callable, Any, cast

def createQAction(parent: Optional[QObject],
                  shortcut: Optional[Union[QKeySequence, QKeySequence.StandardKey, str, int, Qt.Key]],
                  triggered: Union[Callable[..., Any], SignalInstance]) -> QAction:
    action = QAction(parent)
    if shortcut is not None:
        if isinstance(shortcut, QKeySequence):
            action.setShortcut(shortcut)
        else:
            action.setShortcut(QKeySequence(cast(int, shortcut)))
    action.triggered.connect(triggered)
    return action