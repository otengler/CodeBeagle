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

import os
from typing import Dict, List, Optional, cast
from AppConfig import appConfig
from tools.FileTools import freadall
from tools.ContextExtraction import LineMapping
from fulltextindex import IndexConfiguration
from fulltextindex.FullTextIndex import buildMapFromCommonKeywordFile, CommonKeywordMap
from fulltextindex.IStringMatcher import MatchPosition
from fulltextindex.Query import QueryParams, ContentQuery, FileQuery
from fulltextindex.SearchMethods import SearchMethods
from .DataModel import ContentMatch, ContentSearchResult, FileSearchResult, SearchLocation
from .SearchIndexResolver import SearchIndexResolver
from .TtlCache import TTLCache
from fulltextindex.CommentRuleProvider import CommentRuleProvider

__all__ = ['ContentMatch', 'ContentSearchResult', 'FileSearchResult', 'SearchLocation']

class SearchProvider:
    """Qt-free interface to CodeBeagle's search engine for the AI agent API."""

    def __init__(self, cacheTTLSeconds: int = 300) -> None:
        self._commonKeywordMap: Optional[CommonKeywordMap] = None
        self._config = appConfig()
        self._fileListCache = TTLCache(cacheTTLSeconds)
        self._fileMatchesCache = TTLCache(cacheTTLSeconds)
        self._indexResolver = SearchIndexResolver(self._config)
        self._loadCommonKeywords()

    # Lazily created comment rule provider (class attribute so instances created
    # via object.__new__ in tests work without running __init__).
    _commentRuleProviderCache: Optional[CommentRuleProvider] = None

    @property
    def _commentRuleProvider(self) -> CommentRuleProvider:
        if self._commentRuleProviderCache is None:
            self._commentRuleProviderCache = CommentRuleProvider()
        return self._commentRuleProviderCache

    def getLocations(self) -> List[SearchLocation]:
        """Return all configured search locations."""
        indexConfigs = IndexConfiguration.readConfig(self._config)
        return [SearchLocation(c) for c in indexConfigs]

    def searchContent(self, query: str, *,
                      location: Optional[str] = None,
                      folder: Optional[str] = None,
                      folderFilter: str = "",
                      extensionFilter: str = "",
                      caseSensitive: bool = False,
                      excludeComments: bool = True,
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
            excludeComments: If True (default), exclude matches inside single-line comments.
            contextLines: Number of context lines before/after each match.
            limit: Maximum number of matches to return.
            pageOffset: Cursor for pagination, from a previous response.

        Returns:
            ContentSearchResult with matches and pagination cursor.
        """

        indexConf = self._indexResolver.resolve(location, folder, "content", extensionFilter)
        self._indexResolver.checkExtensionFilter(extensionFilter, indexConf)

        # Build comment rule fetcher if comment exclusion is requested
        commentRuleFetcher = None
        if excludeComments:
            commentRuleFetcher = self._commentRuleProvider.getCommentRule

        params = QueryParams(
            strSearch=query,
            strFolderFilter=folderFilter,
            strExtensionFilter=extensionFilter,
            bCaseSensitive=caseSensitive,
            bExcludeComments=excludeComments,
            commentRuleFetcher=commentRuleFetcher
        )
        searchData = ContentQuery(params)
        # Check file list cache
        cacheKey = self._makeFileListCacheKey(searchData, indexConf, folderFilter, extensionFilter, excludeComments)
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
        indexConf = self._indexResolver.resolve(location, folder, "filename", extensionFilter)
        self._indexResolver.checkExtensionFilter(extensionFilter, indexConf)

        params = QueryParams(
            strSearch=query,
            strFolderFilter=folderFilter,
            strExtensionFilter=extensionFilter,
            bCaseSensitive=caseSensitive
        )
        searchData = FileQuery(params)

        # Check file list cache
        cacheKey = self._makeFileNameCacheKey(searchData, indexConf, folderFilter, extensionFilter)
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

        # Skip files before startFileIndex
        filesToProcess = matchingFiles[startFileIndex:]
        currentFileIndex = startFileIndex
        skip = startMatchIndex
        collected = 0

        for filePath in filesToProcess:
            try:
                text = freadall(filePath)
                lineIndex = LineMapping(text)
            except Exception:
                currentFileIndex += 1
                skip = 0
                continue

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
            for fileMatchIndex, (startPos, length) in enumerate(matchIterator):
                if skip > 0:
                    skip -= 1
                    continue

                if collected >= limit:
                    # We've collected enough; return with cursor pointing to next match
                    pageOffset = {
                        "fileIndex": currentFileIndex,
                        "matchIndex": fileMatchIndex
                    }
                    return ContentSearchResult(totalFiles, matches, pageOffset)

                lineNumber = lineIndex.findLineNumber(startPos)
                matchText = text[startPos:startPos + length]
                fullLine = lineIndex.getLine(lineNumber)

                contextBefore = self._extractContextLines(lineIndex, lineNumber, contextLines, before=True)
                contextAfter = self._extractContextLines(lineIndex, lineNumber, contextLines, before=False)

                matches.append(ContentMatch(
                    file=filePath,
                    line=lineNumber,
                    matchText=matchText,
                    contextBefore=contextBefore,
                    contextAfter=contextAfter,
                    fullLine=fullLine
                ))
                collected += 1

            currentFileIndex += 1
            skip = 0

        # No more matches
        return ContentSearchResult(totalFiles, matches, pageOffset=None)

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

    def _loadCommonKeywords(self) -> None:
            """Load the common keyword map from config if configured."""
            commonKeywordsFile = self._config.commonKeywords
            if commonKeywordsFile:
                self._commonKeywordMap = buildMapFromCommonKeywordFile(commonKeywordsFile)
            else:
                self._commonKeywordMap = {}
    
    def _makeFileListCacheKey(self, searchData: ContentQuery, indexConf: IndexConfiguration.IndexConfiguration,
                                   folderFilter: str, extensionFilter: str, excludeComments: bool = False) -> str:
            """Build a cache key for the file list of a content search."""
            return f"fl:{indexConf.displayName()}|{searchData.search}|{folderFilter}|{extensionFilter}|{searchData.bCaseSensitive}|{excludeComments}"
    
    def _makeFileMatchCacheKey(self, searchData: ContentQuery, filePath: str) -> str:
            """Build a cache key for the matches inside a single file."""
            return f"fm:{searchData.search}|{searchData.bCaseSensitive}|{searchData.bExcludeComments}|{filePath}"

    def _makeFileNameCacheKey(self, searchData: FileQuery, indexConf: IndexConfiguration.IndexConfiguration,
                               folderFilter: str, extensionFilter: str) -> str:
        """Build a cache key for the file list of a file name search."""
        return f"fn:{indexConf.displayName()}|{searchData.search}|{folderFilter}|{extensionFilter}|{searchData.bCaseSensitive}"