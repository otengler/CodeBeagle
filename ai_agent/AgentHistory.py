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

import json
import threading
import time
from typing import Any, Dict, List


class HistoryEntry:
    """A single API call record."""

    def __init__(self, timestamp: float, method: str, path: str,
                 params: str, statusCode: int = 0, durationSecs: float = 0.0,
                 result: str = "", isRunning: bool = False) -> None:
        self.timestamp = timestamp
        self.method = method
        self.path = path
        self.params = params
        self.statusCode = statusCode
        self.durationSecs = durationSecs
        self.result = result
        self.isRunning = isRunning

    def timeStr(self) -> str:
        """Return the timestamp as a formatted date/time string."""
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp))

    def durationStr(self) -> str:
        """Return the duration in seconds with one fraction, e.g. '2.3s'.

        When the entry is still running the elapsed time is computed live.
        """
        if self.isRunning:
            elapsed = time.time() - self.timestamp
            return f"{elapsed:.1f}s"
        return f"{self.durationSecs:.1f}s"

    def finish(self, statusCode: int, result: str, params: str = "") -> None:
        """Mark the entry as completed, computing the duration from the start time."""
        self.durationSecs = time.time() - self.timestamp
        self.statusCode = statusCode
        self.result = result
        self.isRunning = False
        if params:
            self.params = params

    def __str__(self) -> str:
        return f"{self.method} {self.path} -> {self.statusCode} | {self.params}"


class AgentHistory:
    """Thread-safe in-memory history of API calls. Max 500 entries."""

    def __init__(self, maxEntries: int = 500) -> None:
        self._maxEntries = maxEntries
        self._entries: List[HistoryEntry] = []
        self._lock = threading.Lock()

    def add(self, entry: HistoryEntry) -> None:
        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self._maxEntries:
                self._entries.pop(0)

    def entries(self) -> List[HistoryEntry]:
        """Return all entries, newest first."""
        with self._lock:
            return list(reversed(self._entries))

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


def formatBodyParams(data: Dict[str, Any]) -> str:
    """Format a POST body dict into a human-readable string."""
    if not data:
        return ""
    parts: List[str] = []
    for key, value in data.items():
        if isinstance(value, bool):
            parts.append(f"{key}: {'yes' if value else 'no'}")
        elif isinstance(value, (int, float)):
            parts.append(f"{key}: {value}")
        elif isinstance(value, dict):
            parts.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
        elif isinstance(value, str) and len(value) > 80:
            parts.append(f"{key}: '{value[:77]}...'")
        elif isinstance(value, str):
            parts.append(f"{key}: '{value}'")
        elif value is None:
            parts.append(f"{key}: (none)")
        else:
            parts.append(f"{key}: {str(value)}")
    return ", ".join(parts)