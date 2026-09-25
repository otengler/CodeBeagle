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

from typing import List, Optional
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QHBoxLayout,
                             QHeaderView, QLabel, QLineEdit, QPushButton,
                             QTableWidget, QTableWidgetItem, QVBoxLayout,
                             QWidget)
from ..AgentHistory import AgentHistory, HistoryEntry


COL_TIME = 0
COL_ENDPOINT = 1
COL_PARAMS = 2
COL_RESULTS = 3
COL_STATUS = 4
COL_DURATION = 5
COLUMN_COUNT = 6


class _ParamItem(QTableWidgetItem):
    """Item which shows the full parameters as a tooltip."""

    def __init__(self, params: str) -> None:
        super().__init__(params)
        self.setToolTip(params)


class _ResultItem(QTableWidgetItem):
    """Item which shows the full result as a tooltip."""

    def __init__(self, result: str) -> None:
        super().__init__(result)
        self.setToolTip(result)


class HistoryDialog(QDialog):
    """Dialog which shows the AI agent API call history. Latest action first."""

    def __init__(self, history: Optional[AgentHistory], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("AI Agent History"))
        self.resize(900, 480)
        self.setProperty("shadeBackground", True)

        self.history = history
        self.external = history is None

        layout = QVBoxLayout(self)

        self.labelUnavailable = QLabel(
            self.tr("No API call history could be retrieved from the external server "
                     "(CodeBeagleAgentServer)."), self)
        self.labelUnavailable.setWordWrap(True)
        self.labelUnavailable.setStyleSheet("color: gray;")
        self.labelUnavailable.setVisible(False)
        layout.addWidget(self.labelUnavailable)

        # Quick search filter input
        searchLayout = QHBoxLayout()
        self.searchEdit = QLineEdit(self)
        self.searchEdit.setPlaceholderText(self.tr("Quick filter..."))
        self.searchEdit.textChanged.connect(self._filterRows)
        searchLayout.addWidget(self.searchEdit)
        layout.addLayout(searchLayout)

        self.table = QTableWidget(0, COLUMN_COUNT, self)
        self.table.setHorizontalHeaderLabels([
            self.tr("Time"), self.tr("Endpoint"), self.tr("Parameters"),
            self.tr("Results"), self.tr("Status"), self.tr("Duration")])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)

        header = self.table.horizontalHeader()
        if header:
            # Interactive mode lets the user resize every column.
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            # Sensible initial widths so the most common content is visible
            # without manual resizing.
            header.resizeSection(COL_TIME, 140)       # Time (with date)
            header.resizeSection(COL_ENDPOINT, 160)   # Endpoint
            header.resizeSection(COL_PARAMS, 300)     # Parameters
            header.resizeSection(COL_RESULTS, 150)    # Results
            header.resizeSection(COL_STATUS, 55)       # Status
            header.resizeSection(COL_DURATION, 65)     # Duration
        layout.addWidget(self.table)

        buttonRow = QHBoxLayout()
        buttonRow.addStretch(1)
        self.buttonReload = QPushButton(self.tr("&Reload"), self)
        self.buttonReload.clicked.connect(self.reload)
        buttonRow.addWidget(self.buttonReload)
        self.buttonClear = QPushButton(self.tr("&Clear history"), self)
        self.buttonClear.clicked.connect(self.clearHistory)
        self.buttonClear.setEnabled(not self.external)
        buttonRow.addWidget(self.buttonClear)
        self.buttonClose = QPushButton(self.tr("Close"), self)
        self.buttonClose.clicked.connect(self.accept)
        buttonRow.addWidget(self.buttonClose)
        layout.addLayout(buttonRow)

        self.reload()

        QTimer.singleShot(0, self._showHint)

    def _showHint(self) -> None:
        from dialogs.UserHintDialog import showUserHint, ButtonType
        showUserHint(
            self, "agent_history",
            self.tr("AI Agent History"),
            self.tr(
                "<html><body>"
                "<p>This dialog shows the history of API calls made by AI agents to the CodeBeagle search server.</p>"
                "<p>Each row shows:</p>"
                "<ul>"
                "<li>When the call was made</li>"
                "<li>Endpoint that was called</li>"
                "<li>Parameters passed in the request</li>"
                "<li>Results returned (e.g. number of matches/total files)</li>"
                "<li>HTTP status code of the response</li>"
                "<li>Duration of the request</li>"
                "</ul>"
                "<p>Use the quick filter above the table to search across all columns.</p>"
                "<p>You can reload the list or clear the history using the buttons at the bottom.</p>"
                "</body></html>"
            ),
            ButtonType.OK
        )

    def _currentEntries(self) -> List[HistoryEntry]:
        """Return the entries to display, either from the local history object
        or fetched from the external server."""
        if self.history is not None:
            return self.history.entries()
        from ..AgentState import fetchExternalHistory
        return fetchExternalHistory()

    def reload(self) -> None:
        """Fill the table with the current history, newest entry first."""
        entries = self._currentEntries()
        self.table.setRowCount(0)
        for entry in entries:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, COL_TIME, QTableWidgetItem(entry.timeStr()))
            self.table.setItem(row, COL_ENDPOINT, QTableWidgetItem(entry.path))
            self.table.setItem(row, COL_PARAMS, _ParamItem(entry.params))
            self.table.setItem(row, COL_RESULTS, _ResultItem(entry.result))
            self.table.setItem(row, COL_STATUS, QTableWidgetItem(str(entry.statusCode)))
            self.table.setItem(row, COL_DURATION, QTableWidgetItem(entry.durationStr()))
        self.labelUnavailable.setVisible(self.external and not entries)
        self._filterRows()

    def clearHistory(self) -> None:
        if not self.history:
            return
        self.history.clear()
        self.reload()

    def _filterRows(self) -> None:
        """Filter table rows by the quick search text, matching all columns."""
        text = self.searchEdit.text().casefold()
        if not text:
            for row in range(self.table.rowCount()):
                self.table.setRowHidden(row, False)
            return
        for row in range(self.table.rowCount()):
            visible = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text in item.text().casefold():
                    visible = True
                    break
            self.table.setRowHidden(row, not visible)