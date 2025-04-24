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

from typing import Optional, Tuple
import json, unittest, os
from bisect import bisect_left, bisect_right
from PyQt5.QtCore import QSettings
from tools.ExceptionTools import ignoreExcepion
import AppConfig

class BookmarkStorage:
    BookmarkStorageKey = "bookmarks"
    PropAll = "all"
    PropName = "name"
    PropLines = "lines"
    PersistenceEnabled = True

    def __init__(self) -> None:
        self.bookmarks: Optional[dict[str, list[int]]] = None
        self.current: Optional[Tuple[str, int]] = None # (file, line)

    def getBookmarksForFile(self, fileName: str) -> set[int]:
        lines = self.__readBookmarks().get(fileName)
        if lines:
            return {line for line in lines}
        return set()
    
    def setBookmarksForFile(self, fileName, lines: set[int]) -> None:
        bookmarks = self.__readBookmarks()
        sortedLines = [line for line in lines]
        if sortedLines:
            sortedLines.sort()
            bookmarks[fileName] = sortedLines
        else:
            if fileName in bookmarks:
                del bookmarks[fileName]
        if self.PersistenceEnabled:
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
    
    def nextBookmark(self) -> Optional[Tuple[str, int]]:
        bookmarks = self.__readBookmarks()
        if not bookmarks:
            return None
        if not self.current:
            self.current = self.__initCurrentBookmark()
            return self.current
        currFile, currLine = self.current
        # Get next bookmark in file
        lines: list[int] = bookmarks.get(currFile) # type: ignore
        if not lines:
            self.current = self.__initCurrentBookmark()
            return self.current
        nextIndex = bisect_right(lines, currLine)
        if nextIndex < len(lines):
            self.current = (currFile, lines[nextIndex])
            return self.current
        else:
            # Move to next file
            nextBookmark = self.__moveFile(currFile, True)
            if nextBookmark:
                self.current = (nextBookmark[0], nextBookmark[1])
                return self.current
        return None
    
    def previousBookmark(self) -> Optional[Tuple[str, int]]:
        bookmarks = self.__readBookmarks()
        if not bookmarks:
            return None
        if not self.current:
            self.current = self.__initCurrentBookmark()
            return self.current
        currFile, currLine = self.current
        # Get previous bookmark in file
        lines: list[int] = bookmarks.get(currFile) # type: ignore
        if not lines:
            self.current = self.__initCurrentBookmark()
            return self.current
        nextIndex = bisect_left(lines, currLine) -1
        if nextIndex >= 0:
            self.current = (currFile, lines[nextIndex])
            return self.current
        else:
            # Move to previous file
            nextBookmark = self.__moveFile(currFile, False)
            if nextBookmark:
                self.current = (nextBookmark[0], nextBookmark[1])
                return self.current
        return None

    def __initCurrentBookmark(self) -> Optional[Tuple[str, int]]:
        bookmarks = self.__readBookmarks()
        if not bookmarks:
            self.current = None
            return None
        if not self.current:
            self.current = self.__firstBookmark()
        lines = bookmarks.get(self.current[0]) # type: ignore
        if not lines:
            self.current = self.__firstBookmark()
        return self.current

    def __moveFile(self, fileName: str, forward: bool) -> Optional[Tuple[str,int]]:
        bookmarks = self.__readBookmarks()
        if not bookmarks:
            return None
        names = [k for k in bookmarks.keys()]
        index = names.index(fileName)
        if index == -1:
            nextName = names[0]
        else:
            if forward:
                index += 1
            else:
                index -= 1
            if index < 0:
                index = len(names) - 1
            elif index >= len(names):
                index = 0
            nextName = names[index]
        lineIndex = 0
        if not forward:
            lineIndex = -1
        return (nextName, bookmarks[nextName][lineIndex])

    def __firstBookmark(self) -> Optional[Tuple[str, int]]:
        bookmarks = self.__readBookmarks()
        if not bookmarks: 
            return None
        for name, lines in bookmarks.items():
            return (name, lines[0])
        return None

    def __readBookmarks(self) -> dict[str, list[int]]:
        if self.bookmarks is None:
            if self.PersistenceEnabled:
                settings = QSettings(AppConfig.appCompany, AppConfig.appName)
                self.bookmarks = self.__deserializeBookmarks(settings.value(self.BookmarkStorageKey))
            else:
                self.bookmarks = {}
        return self.bookmarks
    
    def __serializeBookmarks(self) -> str:
        data: dict = {}
        if self.bookmarks:
            all = []
            for fileName, lines in self.bookmarks.items():
                all.append({self.PropName: fileName, self.PropLines: lines})
            data[self.PropAll] = all
        return json.dumps(data)
    
    def __deserializeBookmarks(self, serialized: str, removeNotExistingFiles: bool = True) -> dict[str, list[int]]:
        bookmarks = {}
        try:
            deserialized = json.loads(serialized)
            if deserialized and isinstance(deserialized, dict):
                all: list[Tuple[str, int]]
                if all := deserialized.get(self.PropAll): 
                    for item in all:
                        name = item.get(self.PropName)
                        lines = item.get(self.PropLines)
                        if name and lines:
                            if removeNotExistingFiles:
                                if not ignoreExcepion(os.path.isfile, False, name):
                                    continue
                            lines.sort()
                            bookmarks[name] = lines
        except:
            bookmarks = {}

        self.bookmarks = bookmarks

        return bookmarks

bookmarkStorage = BookmarkStorage()
def getBookmarkStorage() -> BookmarkStorage:
    return bookmarkStorage

class TestBookmarks(unittest.TestCase):
    def test(self) -> None:
        BookmarkStorage.PersistenceEnabled = False
        storage = BookmarkStorage()
        json = storage._BookmarkStorage__serializeBookmarks() # type: ignore
        self.assertEqual("{}", json)

        storage = BookmarkStorage()
        storage.setBookmarksForFile("a", set((10,)))
        json = storage._BookmarkStorage__serializeBookmarks() # type: ignore
        self.assertListEqual([k for k in storage.bookmarks.keys()], ["a"]) # type: ignore
        self.assertIsNone(storage.current)

        storage = BookmarkStorage()
        storage.setBookmarksForFile("a", set((20,30,10)))
        storage.setBookmarksForFile("b", set((15,)))
        storage.setBookmarksForFile("c", set()) # empty must be removed when serializing
        json = storage._BookmarkStorage__serializeBookmarks() # type: ignore
        
        storage = BookmarkStorage()
        storage._BookmarkStorage__deserializeBookmarks(json, False) # type: ignore
        self.assertListEqual([k for k in storage.bookmarks.keys()], ["a", "b"]) # type: ignore
        self.assertListEqual(storage.bookmarks["a"], [10,20,30]) # type: ignore
        self.assertListEqual(storage.bookmarks["b"], [15]) # type: ignore
        self.assertIsNone(storage.current)
        storage.setBookmarksForFile("c", set()) # make sure empty file is skipped in next/previous

        self.assertTupleEqual(storage.nextBookmark(), ("a", 10)) # type: ignore
        self.assertTupleEqual(storage.nextBookmark(), ("a", 20)) # type: ignore
        self.assertTupleEqual(storage.nextBookmark(), ("a", 30)) # type: ignore
        self.assertTupleEqual(storage.nextBookmark(), ("b", 15)) # type: ignore
        self.assertTupleEqual(storage.nextBookmark(), ("a", 10)) # type: ignore

        self.assertTupleEqual(storage.previousBookmark(), ("b", 15)) # type: ignore
        self.assertTupleEqual(storage.previousBookmark(), ("a", 30)) # type: ignore
        self.assertTupleEqual(storage.previousBookmark(), ("a", 20)) # type: ignore
        self.assertTupleEqual(storage.previousBookmark(), ("a", 10)) # type: ignore

        # does not exist in list, start with first 
        storage.current = ("z", 1) 
        self.assertTupleEqual(storage.nextBookmark(), ("a", 10)) # type: ignore
        storage.current = ("z", 1) 
        self.assertTupleEqual(storage.previousBookmark(), ("a", 10)) # type: ignore

if __name__ == "__main__":
    unittest.main()