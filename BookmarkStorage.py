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

from typing import Optional
import json
from PyQt5.QtCore import QSettings
import AppConfig

class BookmarkStorage:
    def __init__(self) -> None:
        self.bookmarks: Optional[dict[str, list[int]]] = None

    def getBookmarksForFile(self, fileName: str) -> list[int]:
        return self.__readBookmarks().get(fileName) or []
    
    def setBookmarksForFile(self, fileName, lines: list[int]) -> None:
        bookmarks = self.__readBookmarks()
        bookmarks[fileName] = lines
        settings = QSettings(AppConfig.appCompany, AppConfig.appName)
        settings.setValue("bookmarks", json.dumps(self.bookmarks))

    def __readBookmarks(self) -> dict[str, list[int]]:
        if self.bookmarks is None:
            settings = QSettings(AppConfig.appCompany, AppConfig.appName)
            try:
                self.bookmarks = json.loads(settings.value("bookmarks"))
                if self.bookmarks is None or not isinstance(self.bookmarks, dict):
                    self.bookmarks = {}
            except:
                self.bookmarks = {}
        return self.bookmarks

bookmarkStorage = BookmarkStorage()
def getBookmarkStorage() -> BookmarkStorage:
    return bookmarkStorage