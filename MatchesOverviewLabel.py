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

from typing import Optional, Callable, cast
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QIcon, QPixmap
from widgets.RecyclingVerticalScrollArea import ScrollAreaItem
from Ui_MatchesOverviewLabel import Ui_MatchesOverviewLabel
import AppConfig

class MatchesOverviewLabel (QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.ui = Ui_MatchesOverviewLabel()
        self.ui.setupUi(self)  # type: ignore[no-untyped-call]
        if AppConfig.appConfig().theme == AppConfig.darkTheme:
            icon = QIcon()
            icon.addPixmap(QPixmap("resources/currentLighter.png"))
            self.ui.buttonJumpTo.setIcon(icon)

class MatchesOverviewLabelItem (ScrollAreaItem):
    def __init__(self, fileName: str, startLine: int) -> None:
        super ().__init__(24)
        self.fileName = fileName
        self.startLine = startLine
        self.navigateToCallback: Optional[Callable[[], None]] = None

    def generateItem (self, parent: Optional[QWidget]) -> QWidget:
        return MatchesOverviewLabel(parent)

    def configureItem(self, item: QWidget) -> None:
        overviewLabel = cast(MatchesOverviewLabel, item)
        overviewLabel.setFixedHeight(self.height)
        overviewLabel.ui.labelText.setText("<b>" + self.fileName + "</b>")
        if self.navigateToCallback:
            try: # raises an exception if there are no connections
                overviewLabel.ui.buttonJumpTo.clicked.disconnect()
            except:
                pass
            overviewLabel.ui.buttonJumpTo.clicked.connect(self.navigateToCallback)

    def getType(self) -> str:
        return "MatchesOverviewLabel"