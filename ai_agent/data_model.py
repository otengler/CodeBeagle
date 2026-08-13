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

from typing import Dict, List, Optional, Any
from fulltextindex import IndexConfiguration

class SearchLocation:
    """Plain data object describing a search location for the API."""
    def __init__(self, indexConf: IndexConfiguration.IndexConfiguration) -> None:
        self.name: str = indexConf.displayName()
        self.folders: List[str] = list(indexConf.directories)
        self.extensions: List[str] = sorted(indexConf.extensions)
        if indexConf.isContentIndexed() and indexConf.isFileNameIndexed():
            self.indexMode: str = "filenameAndContent"
        elif indexConf.isContentIndexed():
            self.indexMode = "content"
        else:
            self.indexMode = "filename"

class ContentMatch:
    """A single match within a file."""
    def __init__(self, file: str, line: int, matchText: str,
                 contextBefore: List[str], contextAfter: List[str], fullLine: str) -> None:
        self.file = file
        self.line = line
        self.matchText = matchText
        self.contextBefore = contextBefore
        self.contextAfter = contextAfter
        self.fullLine = fullLine

class ContentSearchResult:
    """Result of a content search."""
    def __init__(self, totalFiles: int, matches: List[ContentMatch],
                 pageOffset: Optional[Dict[str, int]] = None) -> None:
        self.totalFiles = totalFiles
        self.matches = matches
        self.pageOffset = pageOffset

class FileSearchResult:
    """Result of a file name search."""
    def __init__(self, totalFiles: int, files: List[str],
                 pageOffset: Optional[Dict[str, int]] = None) -> None:
        self.totalFiles = totalFiles
        self.files = files
        self.pageOffset = pageOffset
