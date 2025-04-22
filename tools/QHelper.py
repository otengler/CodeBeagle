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

from PyQt5.QtWidgets import QAction
from PyQt5.QtCore import QObject, pyqtBoundSignal
from PyQt5.QtGui import QKeySequence
from typing import Optional, Union, Callable, Any

def createQAction(parent: Optional[QObject],
                  shortcut: Union[QKeySequence, QKeySequence.StandardKey, Optional[str], int], 
                  triggered: Union[Callable[..., Any], pyqtBoundSignal]) -> QAction:
    action = QAction(parent)
    action.setShortcut(shortcut)
    action.triggered.connect(triggered)
    return action