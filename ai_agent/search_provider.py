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

import os
import threading
import time
from typing import Any, Dict, List, Optional, Tuple, cast
from AppConfig import appConfig
from tools.FileTools import freadall
from tools.ContextExtraction import LineMapping
from fulltextindex import IndexConfiguration
from fulltextindex.FullTextIndex import buildMapFromCommonKeywordFile, CommonKeywordMap
from fulltextindex.IStringMatcher import MatchPosition
from fulltextindex.Query import QueryParams, ContentQuery, FileQuery
from fulltextindex.SearchMethods import SearchMethods, ResultSet

__all__ = ['SearchLocation', 'ContentMatch', 'ContentSearchResult', 'FileSearchResult',
           'SearchProvider', 'TTLCache']

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
    def __init__(self, file: str, line: int, column: int, matchText: str,
                 contextBefore: List[str], contextAfter: List[str], fullLine: str) -> None:
        self.file = file
        self.line = line
        self.column = column
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

class SearchProvider:
    """Qt-free interface to CodeBeagle's search engine for the AI agent API."""

    def __init__(self, cacheTTLSeconds: int = 300) -> None:
        self._commonKeywordMap: Optional[CommonKeywordMap] = None
        self._config = appConfig()
        self._fileListCache = TTLCache(cacheTTLSeconds)
        self._fileMatchesCache = TTLCache(cacheTTLSeconds)
        self._loadCommonKeywords()

    def _loadCommonKeywords(self) -> None:
        """Load the common keyword map from config if configured."""
        commonKeywordsFile = self._config.commonKeywords
        if commonKeywordsFile:
            self._commonKeywordMap = buildMapFromCommonKeywordFile(commonKeywordsFile)
        else:
            self._commonKeywordMap = {}

    def getLocations(self) -> List[SearchLocation]:
        """Return all configured search locations."""
        indexConfigs = IndexConfiguration.readConfig(self._config)
        return [SearchLocation(c) for c in indexConfigs]

    def _resolveIndexConfig(self, location: Optional[str] = None,
                            folder: Optional[str] = None) -> IndexConfiguration.IndexConfiguration:
        """
        Resolve an IndexConfiguration from either a location name or a folder path.

        If neither location nor folder is specified, the configured defaultLocation
        is used. If that is not configured, the first available location is returned.
        """
        if location and folder:
            raise ValueError("Only one of 'location' or 'folder' may be specified")

        indexConfigs = IndexConfiguration.readConfig(self._config)
        if not indexConfigs:
            raise ValueError("No search locations configured")

        if location:
            for conf in indexConfigs:
                if conf.displayName() == location:
                    return conf
            raise ValueError(f"Search location '{location}' not found")

        if folder:
            # Resolve by folder: find the first location whose source directory
            # equals or is a parent of the requested folder.
            normFolder = os.path.normpath(folder)
            for conf in indexConfigs:
                for srcDir in conf.directories:
                    normalizedSrc = os.path.normpath(srcDir)
                    if normalizedSrc == normFolder or normFolder.startswith(normalizedSrc + os.sep):
                        return conf
            raise ValueError(f"No search location found for folder '{folder}'")

        # Neither location nor folder provided: use defaultLocation or first config
        defaultName = str(self._config.defaultLocation)
        if defaultName:
            for conf in indexConfigs:
                if conf.displayName() == defaultName:
                    return conf
        return indexConfigs[0]

    def searchContent(self, query: str, *,
                      location: Optional[str] = None,
                      folder: Optional[str] = None,
                      folderFilter: str = "",
                      extensionFilter: str = "",
                      caseSensitive: bool = False,
                      excludeComments: bool = False,
                      contextLines: int = 2,
                      limit: int = 100,
                      pageOffset: Optional[Dict[str, int]] = None) -> ContentSearchResult:
        """
        Search file content.

        Args:
            query: Search string (same syntax as GUI search box, wildcards supported).
            location: Name of the search location (from getLocations()).
            folder: Root folder path to search in (alternative to location).
            folderFilter: Optional folder filter pattern.
            extensionFilter: Optional extension filter pattern.
            caseSensitive: Whether to search case-sensitively.
            excludeComments: Whether to exclude matches inside comments.
            contextLines: Number of context lines before/after each match.
            limit: Maximum number of matches to return.
            pageOffset: Cursor for pagination, from a previous response.

        Returns:
            ContentSearchResult with matches and pagination cursor.
        """
        # Note: excludeComments is not fully supported in the Qt-free provider
        # because comment rule detection requires PyQt. The parameter is accepted
        # but may not filter comments.
        indexConf = self._resolveIndexConfig(location, folder)

        params = QueryParams(
            strSearch=query,
            strFolderFilter=folderFilter,
            strExtensionFilter=extensionFilter,
            bCaseSensitive=caseSensitive,
            bExcludeComments=excludeComments
        )
        searchData = ContentQuery(params)
        # Check file list cache
        cacheKey = self._makeFileListCacheKey(query, indexConf, folderFilter, extensionFilter,
                                               caseSensitive, excludeComments)
        matchingFiles = cast(Optional[List[str]], self._fileListCache.get(cacheKey))
        if matchingFiles is None:
            ftiSearch = SearchMethods()
            resultSet = ftiSearch.searchContent(searchData, indexConf, self._commonKeywordMap or {})
            matchingFiles = resultSet.matches  # List of file paths
            self._fileListCache.set(cacheKey, matchingFiles)

        if not matchingFiles:
            return ContentSearchResult(totalFiles=0, matches=[], pageOffset=None)

        # Build paginated matches from the matching files
        return self._buildContentResults(
            matchingFiles, searchData, contextLines, limit, pageOffset
        )

    def _buildContentResults(self, matchingFiles: List[str], searchData: ContentQuery,
                              contextLines: int, limit: int,
                              pageOffset: Optional[Dict[str, int]]) -> ContentSearchResult:
        """
        Scan matching files for individual matches, apply pagination, and return results.
        """
        # Determine starting point from pageOffset
        startFileIndex = 0
        startMatchIndex = 0
        if pageOffset:
            startFileIndex = pageOffset.get("fileIndex", 0)
            startMatchIndex = pageOffset.get("matchIndex", 0)

        totalFiles = len(matchingFiles)
        matches: List[ContentMatch] = []
        fileLineCache: Dict[str, Tuple[str, LineMapping]] = {}

        # Skip files before startFileIndex
        filesToProcess = matchingFiles[startFileIndex:]
        currentFileIndex = startFileIndex
        skip = startMatchIndex
        collected = 0

        for filePath in filesToProcess:
            # Read and cache file content
            if filePath not in fileLineCache:
                try:
                    text = freadall(filePath)
                    lineIndex = LineMapping(text)
                    fileLineCache[filePath] = (text, lineIndex)
                except Exception:
                    currentFileIndex += 1
                    skip = 0
                    continue

            text, lineIndex = fileLineCache[filePath]

            # Try to get cached matches for this file
            fileMatchCacheKey = self._makeFileMatchCacheKey(searchData, filePath)
            cachedMatches = cast(Optional[List[MatchPosition]], self._fileMatchesCache.get(fileMatchCacheKey))

            if cachedMatches is not None:
                matchIterator: List[MatchPosition] = cachedMatches
            else:
                # Compute and cache matches for this file
                freshMatches = list(searchData.matches(text, filePath))
                self._fileMatchesCache.set(fileMatchCacheKey, freshMatches)
                matchIterator = freshMatches

            # Iterate over matches in this file
            fileMatchIndex = 0
            for startPos, length in matchIterator:
                if skip > 0:
                    skip -= 1
                    fileMatchIndex += 1
                    continue

                if collected >= limit:
                    # We've collected enough; return with cursor pointing to next match
                    pageOffset = {
                        "fileIndex": currentFileIndex,
                        "matchIndex": fileMatchIndex
                    }
                    return ContentSearchResult(totalFiles, matches, pageOffset)

                lineNumber = lineIndex.findLineNumber(startPos)
                column = self._calcColumn(lineIndex, lineNumber, startPos)
                matchText = text[startPos:startPos + length]
                fullLine = lineIndex.getLine(lineNumber)

                contextBefore = self._extractContextLines(lineIndex, lineNumber, contextLines, before=True)
                contextAfter = self._extractContextLines(lineIndex, lineNumber, contextLines, before=False)

                matches.append(ContentMatch(
                    file=filePath,
                    line=lineNumber,
                    column=column,
                    matchText=matchText,
                    contextBefore=contextBefore,
                    contextAfter=contextAfter,
                    fullLine=fullLine
                ))
                collected += 1
                fileMatchIndex += 1

            currentFileIndex += 1
            skip = 0

        # No more matches
        return ContentSearchResult(totalFiles, matches, pageOffset=None)

    def _makeFileListCacheKey(self, query: str, indexConf: IndexConfiguration.IndexConfiguration,
                               folderFilter: str, extensionFilter: str,
                               caseSensitive: bool, excludeComments: bool) -> str:
        """Build a cache key for the file list of a content search."""
        return f"fl:{indexConf.displayName()}|{query}|{folderFilter}|{extensionFilter}|{caseSensitive}|{excludeComments}"

    def _makeFileMatchCacheKey(self, searchData: ContentQuery, filePath: str) -> str:
        """Build a cache key for the matches inside a single file."""
        return f"fm:{searchData.search}|{searchData.bCaseSensitive}|{searchData.bExcludeComments}|{filePath}"

    def _calcColumn(self, lineIndex: LineMapping, lineNumber: int, charPos: int) -> int:
        """Calculate 1-based column number from character position."""
        lineStart = lineIndex.numberMap.get(lineNumber, 0)
        return charPos - lineStart + 1

    def _extractContextLines(self, lineIndex: LineMapping, lineNumber: int,
                              contextLines: int, before: bool) -> List[str]:
        """Extract context lines before or after the match line."""
        lines: List[str] = []
        if before:
            start = lineNumber - contextLines
            if start < 1:
                start = 1
            for i in range(start, lineNumber):
                lines.append(lineIndex.getLine(i))
        else:
            end = lineNumber + contextLines
            if end > lineIndex.lineCount():
                end = lineIndex.lineCount()
            for i in range(lineNumber + 1, end + 1):
                lines.append(lineIndex.getLine(i))
        return lines

    def searchFileName(self, query: str, *,
                       location: Optional[str] = None,
                       folder: Optional[str] = None,
                       folderFilter: str = "",
                       extensionFilter: str = "",
                       caseSensitive: bool = False,
                       limit: int = 100,
                       pageOffset: Optional[Dict[str, int]] = None) -> FileSearchResult:
        """
        Search file names.

        Args:
            query: File name pattern (supports * and ? wildcards).
            location: Name of the search location (from getLocations()).
            folder: Root folder path to search in (alternative to location).
            folderFilter: Optional folder filter pattern.
            extensionFilter: Optional extension filter pattern.
            caseSensitive: Whether to search case-sensitively.
            limit: Maximum number of files to return.
            pageOffset: Cursor for pagination, from a previous response.

        Returns:
            FileSearchResult with matching files and pagination cursor.
        """
        indexConf = self._resolveIndexConfig(location, folder)

        params = QueryParams(
            strSearch=query,
            strFolderFilter=folderFilter,
            strExtensionFilter=extensionFilter,
            bCaseSensitive=caseSensitive
        )
        searchData = FileQuery(params)

        # Check file list cache
        cacheKey = self._makeFileNameCacheKey(query, indexConf, folderFilter, extensionFilter, caseSensitive)
        allFiles = cast(Optional[List[str]], self._fileListCache.get(cacheKey))

        if allFiles is None:
            ftiSearch = SearchMethods()
            resultSet = ftiSearch.searchFileName(searchData, indexConf)
            allFiles = resultSet.matches  # List of file paths
            self._fileListCache.set(cacheKey, allFiles)

        totalFiles = len(allFiles)

        # Apply pagination
        startIndex = 0
        if pageOffset:
            startIndex = pageOffset.get("fileIndex", 0)

        pageFiles = allFiles[startIndex:startIndex + limit]
        nextOffset: Optional[Dict[str, int]] = None
        if startIndex + limit < totalFiles:
            nextOffset = {"fileIndex": startIndex + limit}

        return FileSearchResult(totalFiles, pageFiles, nextOffset)

    def _makeFileNameCacheKey(self, query: str, indexConf: IndexConfiguration.IndexConfiguration,
                               folderFilter: str, extensionFilter: str,
                               caseSensitive: bool) -> str:
        """Build a cache key for the file list of a file name search."""
        return f"fn:{indexConf.displayName()}|{query}|{folderFilter}|{extensionFilter}|{caseSensitive}"