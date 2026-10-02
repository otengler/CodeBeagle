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
import threading
from AppConfig import appConfig
from fulltextindex import IndexConfiguration

class TimeoutEvent:
    cancelEvent: Optional[threading.Event] = None
    timer: Optional[threading.Timer] = None

    def __init__(self, indexConf: IndexConfiguration.IndexConfiguration) -> None:
        """
        Create a cancelEvent with a timeout for non-indexed (ad-hoc) searches.

        The timeout prevents the search from blocking indefinitely when walking
        a large directory tree without an index. Returns None for indexed searches
        or when the timeout is disabled (set to 0).
        """
        self.indexConf = indexConf
        self._createCancelEventForSearch()

    def _createCancelEventForSearch(self) -> None:
        if self.indexConf.generatesIndex():
            return None
        try:
            timeout = int(appConfig().agent.searchTimeout)
        except (ValueError, TypeError):
            timeout = 60
        if timeout <= 0:
            return None
        cancelEvent = threading.Event()
        timer = threading.Timer(timeout, cancelEvent.set)
        timer.start()
        self.cancelEvent = cancelEvent
        self.timer = timer

    def happened(self) -> bool:
        if self.cancelEvent and self.cancelEvent.is_set():
            return True
        return False