# -*- coding: utf-8 -*-
"""
Copyright (C) 2026 Oliver Tengler

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

from typing import Optional
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (QAbstractItemView, QDialog, QHBoxLayout,
                             QHeaderView, QPushButton, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)
from .AgentHistory import AgentHistory


class _ParamItem(QTableWidgetItem):
    """Item which shows the full parameters as a tooltip."""

    def __init__(self, params: str) -> None:
        super().__init__(params)
        self.setToolTip(params)


class HistoryDialog(QDialog):
    """Dialog which shows the AI agent API call history. Latest action first."""

    def __init__(self, history: AgentHistory, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("AI Agent History"))
        self.resize(900, 480)
        self.setProperty("shadeBackground", True)

        self.history = history

        layout = QVBoxLayout(self)

        self.table = QTableWidget(0, 6, self)
        self.table.setHorizontalHeaderLabels([
            self.tr("Time"), self.tr("Method"), self.tr("Endpoint"),
            self.tr("Parameters"), self.tr("Status"), self.tr("Duration")])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)

        header = self.table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)

        buttonRow = QHBoxLayout()
        buttonRow.addStretch(1)
        self.buttonReload = QPushButton(self.tr("&Reload"), self)
        self.buttonReload.clicked.connect(self.reload)
        buttonRow.addWidget(self.buttonReload)
        self.buttonClear = QPushButton(self.tr("&Clear history"), self)
        self.buttonClear.clicked.connect(self.clearHistory)
        buttonRow.addWidget(self.buttonClear)
        self.buttonClose = QPushButton(self.tr("Close"), self)
        self.buttonClose.clicked.connect(self.accept)
        buttonRow.addWidget(self.buttonClose)
        layout.addLayout(buttonRow)

        self.reload()

    def reload(self) -> None:
        """Fill the table with the current history, newest entry first."""
        self.table.setRowCount(0)
        for entry in self.history.entries():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(entry.timeStr()))
            self.table.setItem(row, 1, QTableWidgetItem(entry.method))
            self.table.setItem(row, 2, QTableWidgetItem(entry.path))
            self.table.setItem(row, 3, _ParamItem(entry.params))
            self.table.setItem(row, 4, QTableWidgetItem(str(entry.statusCode)))
            self.table.setItem(row, 5, QTableWidgetItem(entry.durationStr()))

    def clearHistory(self) -> None:
        self.history.clear()
        self.reload()


def agentIcon() -> QIcon:
    """Create a small status icon which indicates that the AI agent is running."""
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    # Blue round "agent head" with an antenna
    painter.setBrush(QColor(52, 120, 246))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(4, 6, 16, 16)
    painter.drawRect(11, 2, 2, 5)
    # Pulse line inside the head
    painter.setPen(QPen(QColor(255, 255, 255), 2))
    painter.drawLine(7, 15, 10, 15)
    painter.drawLine(10, 15, 12, 12)
    painter.drawLine(12, 12, 14, 19)
    painter.drawLine(14, 19, 16, 14)
    painter.drawLine(16, 14, 18, 15)
    painter.end()
    return QIcon(pixmap)
