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

from typing import Dict, Any, Tuple
import threading
import time

class TTLCache:
    """Simple thread-safe TTL cache mapping keys to values."""

    def __init__(self, ttlSeconds: int = 300) -> None:
        self._ttl = ttlSeconds
        self._data: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expiresAt, value = item
            if time.time() > expiresAt:
                del self._data[key]
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = (time.time() + self._ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()