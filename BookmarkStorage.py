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

from typing import Optional, Tuple, Any
import json, unittest, os
from bisect import bisect_left, bisect_right
from PyQt5.QtCore import QSettings
from tools.ExceptionTools import ignoreExcepion
import AppConfig

def findStrInList(items: list[str], item: str) -> int:
    try:
        return items.index(item)
    except ValueError:
        return -1
    
class NumberedBookmark:
    def __init__(self, number: int, fileName: str, line: int) -> None:
        self.number = number
        self.fileName = fileName
        self.line = line

class BookmarkData:
    def __init__(self) -> None:
        self.bookmarks: dict[str, list[int]] = {}
        self.numberedBookmarks: list[NumberedBookmark] = []
        self.initialized = False

    def setData(self, bookmarks: dict[str, list[int]], numberedBookmarks: list[NumberedBookmark]) -> None:
        self.bookmarks = bookmarks
        self.numberedBookmarks = numberedBookmarks
        self.initialized = True

    def removeBookmarkFromLine(self, fileName: str, line: int) -> int:
        """Returns the number of the bookmark or -1"""
        for item in self.numberedBookmarks:
            if item.fileName == fileName and item.line == line:
                self.numberedBookmarks.remove(item)
                return item.number
        return -1

    def removeNumberedBookmark(self, number: int) -> int:
        """Returns the line number of the removed bookmark or -1"""
        for item in self.numberedBookmarks:
            if item.number == number:
                self.numberedBookmarks.remove(item)
                return item.line
        return -1

class BookmarkStorage:
    BookmarkStorageKey = "bookmarks"
    PropAll = "all"
    PropNumbered = "numbered"
    PropName = "name"
    PropNumber = "number"
    PropLine = "line"
    PropLines = "lines"
    PersistenceEnabled = True

    def __init__(self) -> None:
        self.bookmarkData: BookmarkData = BookmarkData()
        self.current: Optional[Tuple[str, int]] = None # (file, line)

    def getBookmarksForFile(self, fileName: str) -> set[int]:
        lines = self.__readBookmarks().bookmarks.get(fileName)
        if lines:
            return {line for line in lines}
        return set()
    
    def getNumberedBookmarksByLine(self, fileName: str) -> dict[int,int]:
        lines = {}
        for item in self.__readBookmarks().numberedBookmarks:
            if item.fileName == fileName:
                lines[item.line] = item.number
        return lines
    
    def getNumberedBookmark(self, number: int) -> Optional[NumberedBookmark]:
        for item in self.__readBookmarks().numberedBookmarks:
            if item.number == number:
                return item
        return None
    
    def setBookmarksForFile(self, fileName: str, lines: set[int]) -> None:
        bookmarks = self.__readBookmarks().bookmarks
        sortedLines = [line for line in lines]
        if sortedLines:
            sortedLines.sort()
            bookmarks[fileName] = sortedLines
        else:
            if fileName in bookmarks:
                del bookmarks[fileName]
        self.__storeBookmarks()

    def toggleBookmarkForFile(self, fileName: str, line: int) -> set[int]:
        lines = self.getBookmarksForFile(fileName)
        if line in lines:
            lines.remove(line)
        else:
            lines.add(line)
        self.setBookmarksForFile(fileName, lines)
        return lines
    
    def toggleNumberedBookmark(self, number: int, fileName: str, line: int) -> dict[int,int]:
        """ number is from 1 to 9 """
        if number < 1 or number > 9:
            return {}
        # Remove numbered bookmark if it is already set. If the new bookmark if on the same line treat it as a removal
        bookmarkData = self.__readBookmarks()
        removedCurrent = bookmarkData.removeBookmarkFromLine(fileName, line) == number
        if not removedCurrent:
            bookmarkData.removeNumberedBookmark(number)
            bookmarkData.numberedBookmarks.append(NumberedBookmark(number, fileName, line))
        self.__storeBookmarks()
        return self.getNumberedBookmarksByLine(fileName)
    
    def nextBookmark(self) -> Optional[Tuple[str, int]]:
        if not self.current:
            self.current = self.__initCurrentBookmark()
            return self.current
        currFile, currLine = self.current
        # Get next bookmark in file
        lines: list[int] = self.__readBookmarks().bookmarks.get(currFile) or []
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
        if not self.current:
            self.current = self.__initCurrentBookmark()
            return self.current
        currFile, currLine = self.current
        # Get previous bookmark in file
        lines: list[int] = self.__readBookmarks().bookmarks.get(currFile) or []
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
        if not self.current:
            self.current = self.__firstBookmark()
        return self.current

    def __moveFile(self, fileName: str, forward: bool) -> Optional[Tuple[str,int]]:
        bookmarks = self.__readBookmarks().bookmarks
        if not bookmarks:
            return None
        names = [k for k in bookmarks.keys()]
        index = findStrInList(names, fileName)
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
        for name, lines in self.__readBookmarks().bookmarks.items():
            return (name, lines[0])
        return None

    def __readBookmarks(self) -> BookmarkData:
        if not self.bookmarkData.initialized:
            if self.PersistenceEnabled:
                settings = QSettings(AppConfig.appCompany, AppConfig.appName)
                self.__deserializeBookmarks(settings.value(self.BookmarkStorageKey))
            else:
                self.bookmarkData.setData({}, [])
        return self.bookmarkData
    
    def __storeBookmarks(self) -> None:
        if self.PersistenceEnabled:
            settings = QSettings(AppConfig.appCompany, AppConfig.appName)
            settings.setValue(self.BookmarkStorageKey, self.__serializeBookmarks())

    def __serializeBookmarks(self) -> str:
        data: dict[str, Any] = {}
        if self.bookmarkData.bookmarks:
            all = []
            for fileName, lines in self.bookmarkData.bookmarks.items():
                all.append({self.PropName: fileName, self.PropLines: lines})
            data[self.PropAll] = all
        if self.bookmarkData.numberedBookmarks:
            numbered = []
            for bookmark in self.bookmarkData.numberedBookmarks:
                numbered.append({self.PropNumber: bookmark.number, self.PropName: bookmark.fileName, self.PropLine: bookmark.line})
            data[self.PropNumbered] = numbered
        return json.dumps(data)
    
    def __deserializeBookmarks(self, serialized: str, removeNotExistingFiles: bool = True) -> BookmarkData:
        bookmarks = {}
        numberedBookmarks = []
        try:
            deserialized = json.loads(serialized)
            if deserialized and isinstance(deserialized, dict):
                all: list[Any]
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
                numbered: list[Any]
                if numbered := deserialized.get(self.PropNumbered):
                    for item in numbered:
                        number = item.get(self.PropNumber)
                        name = item.get(self.PropName)
                        line = item.get(self.PropLine)
                        if number and name and line:
                            if removeNotExistingFiles:
                                if not ignoreExcepion(os.path.isfile, False, name):
                                    continue
                            if number < 0 or number > 9:
                                continue
                            numberedBookmarks.append(NumberedBookmark(number, name, line))
        except:
            bookmarks = {}
            numberedBookmarks = []

        if self.__numberedBookmarksHaveDuplicates():
            numberedBookmarks = []

        self.bookmarkData.setData(bookmarks, numberedBookmarks)

        return self.bookmarkData

    def __numberedBookmarksHaveDuplicates(self) -> bool:
        if not self.bookmarkData.numberedBookmarks:
            return False
        numbers = set()
        for bm in self.bookmarkData.numberedBookmarks:
            if bm.number in numbers:
                return True
            numbers.add(bm.number)
        return False

bookmarkStorage = BookmarkStorage()
def getBookmarkStorage() -> BookmarkStorage:
    return bookmarkStorage

class TestBookmarks(unittest.TestCase):
    def testNormal(self) -> None:
        BookmarkStorage.PersistenceEnabled = False
        storage = BookmarkStorage()
        json = storage._BookmarkStorage__serializeBookmarks() # type: ignore
        self.assertEqual("{}", json)

        storage = BookmarkStorage()
        storage.setBookmarksForFile("a", set((10,)))
        json = storage._BookmarkStorage__serializeBookmarks()  # type: ignore[attr-defined]
        self.assertListEqual([k for k in storage.bookmarkData.bookmarks.keys()], ["a"])
        self.assertIsNone(storage.current)

        storage = BookmarkStorage()
        storage.setBookmarksForFile("a", set((20,30,10)))
        storage.setBookmarksForFile("b", set((15,)))
        storage.setBookmarksForFile("c", set()) # empty must be removed when serializing
        json = storage._BookmarkStorage__serializeBookmarks()  # type: ignore[attr-defined]

        storage = BookmarkStorage()
        storage._BookmarkStorage__deserializeBookmarks(json, False)  # type: ignore[attr-defined]
        self.assertListEqual([k for k in storage.bookmarkData.bookmarks.keys()], ["a", "b"])
        self.assertListEqual(storage.bookmarkData.bookmarks["a"], [10,20,30])
        self.assertListEqual(storage.bookmarkData.bookmarks["b"], [15])
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
        self.assertTupleEqual(storage.previousBookmark(), ("a", 30)) # type: ignore

    def testNumbered(self) -> None:
        BookmarkStorage.PersistenceEnabled = False
        storage = BookmarkStorage()
        
        bm = storage.getNumberedBookmark(1)
        self.assertIsNone(bm)

        bms = storage.toggleNumberedBookmark(1, "a", 100)
        self.assertEqual(1, len(bms))
        self.assertListEqual([100], [k for k in bms.keys()])
        self.assertListEqual([1], [v for v in bms.values()])

        bms = storage.toggleNumberedBookmark(2, "a", 200)
        self.assertEqual(2, len(bms))
        self.assertListEqual([100, 200], [k for k in bms.keys()])
        self.assertListEqual([1, 2], [v for v in bms.values()])

        nb = storage.getNumberedBookmark(1)
        self.assertEqual(1, nb.number) # type: ignore
        self.assertEqual(100, nb.line) # type: ignore
        self.assertEqual("a", nb.fileName) # type: ignore

        nb = storage.getNumberedBookmark(2)
        self.assertEqual(2, nb.number) # type: ignore
        self.assertEqual(200, nb.line) # type: ignore
        self.assertEqual("a", nb.fileName) # type: ignore
        
        # Move 2 to file "b"
        bms = storage.toggleNumberedBookmark(2, "b", 202)
        self.assertEqual(1, len(bms))
        self.assertListEqual([202], [k for k in bms.keys()])
        self.assertListEqual([2], [v for v in bms.values()])

        # Move 1 inside "a"
        bms = storage.toggleNumberedBookmark(1, "a", 150)
        self.assertEqual(1, len(bms))
        self.assertListEqual([150], [k for k in bms.keys()])
        self.assertListEqual([1], [v for v in bms.values()])

        # Remove 1 inside "a"
        bms = storage.toggleNumberedBookmark(1, "a", 150)
        self.assertEqual(0, len(bms))

if __name__ == "__main__":
    unittest.main()