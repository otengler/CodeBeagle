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

from typing import Optional, Callable
from StringListModel import StringListModel
from PyQt5.QtCore import Qt, QObject, pyqtSlot
from tools.QHelper import createQAction
from BookmarkStorage import getBookmarkStorage

class SearchPageBookmarks (QObject):
    def __init__(self, searchPage) -> None:
        from SearchPage import SearchPage # avoid circular import
        super().__init__(searchPage)
        self.searchPage = searchPage # type: SearchPage
    
        # Bookmarks
        self.searchPage.addAction(createQAction(self, shortcut=Qt.Key.Key_F2, triggered=self.setBookmark))
        self.searchPage.addAction(createQAction(self, shortcut=Qt.KeyboardModifier.ControlModifier+Qt.Key.Key_F2, triggered=self.nextBookmark))
        self.searchPage.addAction(createQAction(self, shortcut=Qt.KeyboardModifier.ShiftModifier+Qt.Key.Key_F2, triggered=self.previousBookmark))
        numberKeys = [Qt.Key.Key_1,Qt.Key.Key_2,Qt.Key.Key_3,Qt.Key.Key_4,Qt.Key.Key_5,Qt.Key.Key_6,Qt.Key.Key_7,Qt.Key.Key_8,Qt.Key.Key_9]
        for idx, key in enumerate(numberKeys):
            number = idx + 1
            self.searchPage.addAction(createQAction(self, shortcut=Qt.KeyboardModifier.ControlModifier+Qt.KeyboardModifier.ShiftModifier+key, triggered=self.__createSetNumberedBookmarkFunc(number)))
            self.searchPage.addAction(createQAction(self, shortcut=Qt.KeyboardModifier.ControlModifier+key, triggered=self.__createJumpToNumberedBookmarkFunc(number)))

    def __createSetNumberedBookmarkFunc(self, number: int) -> Callable:
        return lambda: self.setNumberedBookmark(number)
    def __createJumpToNumberedBookmarkFunc(self, number: int) -> Callable:
        return lambda: self.jumpToNumberedBookmark(number)

    @pyqtSlot()
    def setBookmark(self) -> None:
        self.searchPage.ui.sourceViewer.setBookmark()

    @pyqtSlot()
    def setNumberedBookmark(self, number: int) -> None:
        self.searchPage.ui.sourceViewer.setNumberedBookmark(number)

    @pyqtSlot()
    def nextBookmark(self) -> None:
        if bookmark := getBookmarkStorage().nextBookmark():
            fileName, line = bookmark
            self.__navigateToBookmark(fileName, line)

    @pyqtSlot()
    def previousBookmark(self) -> None:
        if bookmark := getBookmarkStorage().previousBookmark():
            fileName, line = bookmark
            self.__navigateToBookmark(fileName, line)

    @pyqtSlot()
    def jumpToNumberedBookmark(self, number: int) -> None:
        if numberedBookmark := getBookmarkStorage().getNumberedBookmark(number):
            self.__navigateToBookmark(numberedBookmark.fileName, numberedBookmark.line)

    def __navigateToBookmark(self, fileName: str, line: int) -> None:
        # Show file and jump to line
        self.searchPage.showFileLine(fileName, line)
