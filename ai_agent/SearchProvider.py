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
from fnmatch import fnmatch
from typing import Dict, List, Optional, Set, Union, Tuple, cast
from PySide6.QtGui import QFont
from AppConfig import appConfig
from tools.FileTools import freadall
from tools.ContextExtraction import LineMapping
from fulltextindex import IndexConfiguration
from fulltextindex.IndexUpdater import IndexUpdater, UpdateStatistics
from fulltextindex.FullTextIndex import buildMapFromCommonKeywordFile, CommonKeywordMap
from fulltextindex.IStringMatcher import MatchPosition
from fulltextindex.Query import QueryParams, ContentQuery, FileQuery
from fulltextindex.SearchMethods import SearchMethods
from fulltextindex.CommentRule import CommentRule
from HighlightingRulesCache import rules as highlightingRules
from .DataModel import ContentMatch, ContentSearchResult, FileSearchResult, SearchLocation
from .SearchIndexResolver import SearchIndexResolver
from .TtlCache import TTLCache

__all__ = ['ContentMatch', 'ContentSearchResult', 'FileSearchResult', 'SearchLocation']

def splitQueries(query: Union[str, List[str]]) -> Tuple[str, List[str]]: 
    if isinstance(query, list):
        orSearchFor = list(query[1:])
        search = query[0]
    else:
        orSearchFor = []
        search = query
    return (search, orSearchFor) 

class SearchProvider:
    """Interface to CodeBeagle's search engine for the AI agent API."""

    def __init__(self, cacheTTLSeconds: int = 300) -> None:
        self._commonKeywordMap: Optional[CommonKeywordMap] = None
        self._config = appConfig()
        self._fileListCache = TTLCache(cacheTTLSeconds)
        self._fileMatchesCache = TTLCache(cacheTTLSeconds)
        self._indexResolver = SearchIndexResolver(self._config)
        self._loadCommonKeywords()

    def __commentRuleForFile(self, filename: str) -> Optional[CommentRule]:
        """
        Return the comment rule for a file, taken from the existing
        highlighting rules cache (same source as the GUI).
        """
        rule = highlightingRules().getRulesByFileName(filename, QFont())
        if not rule or not rule.lineComment:
            return None
        return CommentRule(rule.lineComment, rule.multiCommentStart, rule.multiCommentStop, rule.hasTripleQuotes)

    def getLocations(self) -> List[SearchLocation]:
        """Return all configured search locations."""
        indexConfigs = IndexConfiguration.readConfig(self._config)
        return [SearchLocation(c) for c in indexConfigs]

    def searchContent(self, query: Union[str, List[str]], *,
                      location: Optional[str] = None,
                      folder: Optional[str] = None,
                      pathFilter: str = "",
                      extensionFilter: str = "",
                      caseSensitive: bool = False,
                      excludeComments: bool = True,
                      contextLines: int = 2,
                      limit: int = 100,
                      pageOffset: Optional[Dict[str, int]] = None) -> ContentSearchResult:
        """
        Search file content.

        Args:
            query: Search string or list of strings (same syntax as GUI search box, wildcards supported).
                   When a list is provided, files matching ANY of the queries are returned (OR logic).
            location: Name of the search location (from getLocations()).
            folder: Root folder path to search in (alternative to location).
            pathFilter: Optional path filter pattern. Can be a full file path to select a single file.
            extensionFilter: Optional extension filter pattern.
            caseSensitive: Whether to search case-sensitively.
            excludeComments: If True (default), exclude matches inside comments.
            contextLines: Number of context lines before/after each match. Set to 0 for compact output (no context lines).
            limit: Maximum number of matches to return.
            pageOffset: Cursor for pagination, from a previous response.

        Returns:
            ContentSearchResult with matches and pagination cursor.
        """
        if isinstance(query, list) and not query:
            return ContentSearchResult(totalFiles=0, matches=[], pageOffset=None)

        indexConf = self._indexResolver.resolve(location, folder, "content", extensionFilter)

        # Use orSearchFor to combine multiple queries into a single index + regex scan
        search, orSearchFor = splitQueries(query)

        params = QueryParams(
            strSearch=search,
            orSearchFor=orSearchFor,
            strFolderFilter=pathFilter,
            strExtensionFilter=extensionFilter,
            bCaseSensitive=caseSensitive
        )
        searchData = ContentQuery(params)

        # Check file list cache
        cacheKey = self._makeFileListCacheKey(searchData, indexConf)
        matchingFiles = cast(Optional[List[str]], self._fileListCache.get(cacheKey))
        if matchingFiles is None:
            ftiSearch = SearchMethods()
            resultSet = ftiSearch.searchContent(searchData, indexConf, self._commonKeywordMap or {})
            matchingFiles = resultSet.matches  # List of file paths
            self._fileListCache.set(cacheKey, matchingFiles)

        if not matchingFiles:
            return ContentSearchResult(totalFiles=0, matches=[], pageOffset=None)

        # Set comment rule fetcher if comment exclusion is requested
        if excludeComments:
            searchData.bExcludeComments = True
            searchData.commentRuleFetcher = self.__commentRuleForFile

        # Build paginated matches from the matching files
        return self._buildContentResults(
            matchingFiles, searchData, contextLines, limit, pageOffset
        )

    def searchFileName(self, query: Union[str, List[str]], *,
                           location: Optional[str] = None,
                           folder: Optional[str] = None,
                           pathFilter: str = "",
                           caseSensitive: bool = False,
                           limit: int = 100,
                           pageOffset: Optional[Dict[str, int]] = None) -> FileSearchResult:
        """
        Search file names.

        Args:
            query: File name pattern or list of patterns (OR logic).
                   Each pattern supports * and ? wildcards.
                   When a list is provided, files matching ANY pattern are returned.
            location: Name of the search location (from getLocations()).
            folder: Root folder path to search in (alternative to location).
            pathFilter: Optional path filter pattern. Can be a full file path to select a single file.
            caseSensitive: Whether to search case-sensitively.
            limit: Maximum number of files to return.
            pageOffset: Cursor for pagination, from a previous response.

        Returns:
            FileSearchResult with matching files and pagination cursor.
        """
        if isinstance(query, list) and not query:
            return FileSearchResult(totalFiles=0, files=[], pageOffset=None)

        queries = query if isinstance(query, list) else [query]
        exts = set()
        for name in queries:
            _, ext = FileQuery.correctSearchAndExt(name)
            exts.add(ext)
        extensionFilter = ",".join(exts)

        indexConf = self._indexResolver.resolve(location, folder, "filename", extensionFilter)

        allFiles: List[str] = []

        if indexConf.generatesIndex():
            # via DB: or is not supported, does not fit into the system
            seen: Set[str] = set()

            for q in queries:
                params = QueryParams(
                    strSearch=q,
                    strFolderFilter=pathFilter,
                    bCaseSensitive=caseSensitive
                )
                searchData = FileQuery(params)

                # Check file list cache
                cacheKey = self._makeFileNameCacheKey(searchData, indexConf)
                files = cast(Optional[List[str]], self._fileListCache.get(cacheKey))

                if files is None:
                    ftiSearch = SearchMethods()
                    resultSet = ftiSearch.searchFileName(searchData, indexConf)
                    files = resultSet.matches  # List of file paths
                    self._fileListCache.set(cacheKey, files)

                for f in files:
                    if f not in seen:
                        seen.add(f)
                        allFiles.append(f)
        else:
            search, orSearchFor = splitQueries(query)
            params = QueryParams(
                                strSearch=search,
                                orSearchFor=orSearchFor,
                                strFolderFilter=pathFilter,
                                bCaseSensitive=caseSensitive
                            )
            searchData = FileQuery(params)

            # Check file list cache
            cacheKey = self._makeFileNameCacheKey(searchData, indexConf)
            files = cast(Optional[List[str]], self._fileListCache.get(cacheKey))

            if files is None:
                ftiSearch = SearchMethods()
                resultSet = ftiSearch.searchFileName(searchData, indexConf)
                files = resultSet.matches  # List of file paths
                self._fileListCache.set(cacheKey, files)

            allFiles = files

        allFiles.sort()
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

    def updateFile(self, filePath: str) -> Dict[str, object]:
        """
        Update the index for a single file.

        This re-indexes the given file in-place without running a full index
        update. Only the index configuration whose source directories cover
        the file path and whose extensions match the file is updated.

        Args:
            filePath: Full path to the file to update.

        Returns:
            Dict with keys:
              - "updated": True if the file was updated, False if unchanged.
              - "detail": Description of the update result.
              - "file": The file path that was updated.
              - "index": The name of the index configuration used.

        Raises:
            FileNotFoundError: If filePath does not exist.
            ValueError: If no index configuration covers the file path.
        """
        if not os.path.isfile(filePath):
            raise FileNotFoundError(f"File not found: {filePath}")

        # Find the index configuration that covers this file
        indexConfigs = IndexConfiguration.readConfig(self._config)
        extension = os.path.splitext(filePath)[1].lower()

        matchingConf = None
        for conf in indexConfigs:
            if not conf.generatesIndex():
                continue
            # Check if the file is under one of the source directories
            fileDir = os.path.normpath(os.path.dirname(filePath)).lower()
            for srcDir in conf.directories:
                normSrc = os.path.normpath(srcDir).lower()
                if fileDir == normSrc or fileDir.startswith(normSrc + os.sep):
                    # Check extension match
                    if extension and extension not in conf.extensions:
                        continue
                    # Check directory exclude patterns
                    excluded = False
                    for exclude in conf.dirExcludes:
                        if fnmatch(fileDir, exclude.lower()):
                            excluded = True
                            break
                    if excluded:
                        continue
                    matchingConf = conf
                    break
            if matchingConf:
                break

        if matchingConf is None:
            raise ValueError(
                f"No indexed search location covers the file path '{filePath}'. "
                "Add the file's directory to an index in CodeBeagle settings."
            )

        updater = IndexUpdater(matchingConf.indexdb)
        stats = UpdateStatistics()
        updater.updateFile(matchingConf, filePath, stats)

        detail = str(stats)
        updated = stats.nUpdated > 0 or stats.nNew > 0

        return {
            "updated": updated,
            "detail": detail,
            "file": filePath,
            "index": matchingConf.displayName(),
        }

    def _loadCommonKeywords(self) -> None:
            """Load the common keyword map from config if configured."""
            commonKeywordsFile = self._config.commonKeywords
            if commonKeywordsFile:
                self._commonKeywordMap = buildMapFromCommonKeywordFile(commonKeywordsFile)
            else:
                self._commonKeywordMap = {}
    
    def _makeFileListCacheKey(self, searchData: ContentQuery, indexConf: IndexConfiguration.IndexConfiguration) -> str:
        """Build a cache key for the file list of a content search."""
        orPart = "|".join(searchData.orSearchFor) if searchData.orSearchFor else ""
        return f"fl:{indexConf.displayName()}|{searchData.search}|{orPart}|{searchData.folderFilter}|{searchData.extensionFilter}|{searchData.bCaseSensitive}"
    
    def _makeFileMatchCacheKey(self, searchData: ContentQuery, filePath: str) -> str:
        """Build a cache key for the matches inside a single file."""
        orPart = "|".join(searchData.orSearchFor) if searchData.orSearchFor else ""
        return f"fm:{searchData.search}|{orPart}|{searchData.bCaseSensitive}|{searchData.bExcludeComments}|{filePath}"

    def _makeFileNameCacheKey(self, searchData: FileQuery, indexConf: IndexConfiguration.IndexConfiguration) -> str:
        """Build a cache key for the file list of a file name search."""
        orPart = "|".join(searchData.orSearchFor) if searchData.orSearchFor else ""
        return f"fn:{indexConf.displayName()}|{searchData.search}|{orPart}|{searchData.folderFilter}|{searchData.extensionFilter}|{searchData.bCaseSensitive}"