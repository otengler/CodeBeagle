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
    BookmarkStorageKey = "bookmarks"

    def __init__(self) -> None:
        self.bookmarks: Optional[dict[str, set[int]]] = None

    def getBookmarksForFile(self, fileName: str) -> set[int]:
        return self.__readBookmarks().get(fileName) or set()
    
    def setBookmarksForFile(self, fileName, lines: set[int]) -> None:
        bookmarks = self.__readBookmarks()
        bookmarks[fileName] = lines
        settings = QSettings(AppConfig.appCompany, AppConfig.appName)
        settings.setValue(self.BookmarkStorageKey, self.__serializeBookmarks())

    def toggleBookmarkForFile(self, fileName, line: int) -> set[int]:
        lines = self.getBookmarksForFile(fileName)
        if line in lines:
            lines.remove(line)
        else:
            lines.add(line)
        self.setBookmarksForFile(fileName, lines)
        return lines

    def __readBookmarks(self) -> dict[str, set[int]]:
        if self.bookmarks is None:
            settings = QSettings(AppConfig.appCompany, AppConfig.appName)
            self.bookmarks = self.__deserializeBookmarks(settings.value(self.BookmarkStorageKey))
        return self.bookmarks
    
    def __serializeBookmarks(self) -> str:
        data = {}
        if self.bookmarks:
            for key, value in self.bookmarks.items():
                data[key] = [v for v in value]
        return json.dumps(data)
    
    def __deserializeBookmarks(self, serialized: str) -> dict[str, set[int]]:
        bookmarks = {}
        try:
            deserialized = json.loads(serialized)
            if deserialized and isinstance(deserialized, dict):
                for fileName, lines in deserialized.items():
                    lineSet = set()
                    for line in lines:
                        lineSet.add(line)
                    bookmarks[fileName] = lineSet
        except:
            bookmarks = {}
        return bookmarks

bookmarkStorage = BookmarkStorage()
def getBookmarkStorage() -> BookmarkStorage:
    return bookmarkStorage