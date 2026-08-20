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

Tests for ContentSearch pagination logic.
"""

import os
import unittest
from typing import Dict, List, Optional, cast
from unittest import mock
from ..SearchProvider import ContentMatch, ContentSearchResult, FileSearchResult, SearchProvider
from ..SearchIndexResolver import SearchIndexResolver
from ..TtlCache import TTLCache
from fulltextindex.IStringMatcher import MatchPosition
from fulltextindex.Query import ContentQuery, QueryParams
from fulltextindex.SearchMethods import ResultSet


class TestContentSearchPagination(unittest.TestCase):
    """
    Tests for the pagination logic of SearchProvider._buildContentResults.

    Each test file below contains exactly two matches of the search term "target"
    (one per line) unless noted otherwise.
    """

    CONTENT: Dict[str, Optional[str]] = {
        "C:/test/f1.py": "alpha target\nbeta target\n",
        "C:/test/f2.py": "gamma target\ndelta target\n",
        "C:/test/f3.py": "epsilon target\nzeta target\n",
    }

    def setUp(self) -> None:
        # Create the provider without running __init__ to avoid loading the config.
        self.provider = object.__new__(SearchProvider)
        self.provider._fileMatchesCache = TTLCache(60)
        self.query = ContentQuery(QueryParams("target"))

    def _buildResults(self, files: List[str], limit: int,
                      pageOffset: Optional[Dict[str, int]] = None,
                      contextLines: int = 2,
                      content: Optional[Dict[str, Optional[str]]] = None) -> ContentSearchResult:
        filesContent = content if content is not None else self.CONTENT

        def read(filePath: str) -> str:
            if filePath not in filesContent:
                raise FileNotFoundError(filePath)
            value = filesContent[filePath]
            if value is None:
                raise OSError(f"Cannot read {filePath}")
            return value

        with mock.patch("ai_agent.SearchProvider.freadall", side_effect=read):
            return self.provider._buildContentResults(files, self.query, contextLines, limit, pageOffset)

    def test_firstPage(self) -> None:
        result = self._buildResults(list(self.CONTENT), limit=2)
        self.assertEqual(result.totalFiles, 3)
        self.assertEqual([(os.path.basename(m.file), m.line) for m in result.matches],
                         [("f1.py", 1), ("f1.py", 2)])
        # The cursor points at the first match of the next file.
        self.assertEqual(result.pageOffset, {"fileIndex": 1, "matchIndex": 0})

    def test_fullPaginationSequence(self) -> None:
        files = list(self.CONTENT)
        page1 = self._buildResults(files, limit=2)
        self.assertEqual(page1.pageOffset, {"fileIndex": 1, "matchIndex": 0})

        page2 = self._buildResults(files, limit=2, pageOffset=page1.pageOffset)
        self.assertEqual([(os.path.basename(m.file), m.line) for m in page2.matches],
                         [("f2.py", 1), ("f2.py", 2)])
        self.assertEqual(page2.pageOffset, {"fileIndex": 2, "matchIndex": 0})

        page3 = self._buildResults(files, limit=2, pageOffset=page2.pageOffset)
        self.assertEqual([(os.path.basename(m.file), m.line) for m in page3.matches],
                         [("f3.py", 1), ("f3.py", 2)])
        # No more data: the cursor is omitted.
        self.assertIsNone(page3.pageOffset)

    def test_resumeMidFile(self) -> None:
        # Skip the first match of f2.py: the page must start with its second match.
        result = self._buildResults(list(self.CONTENT), limit=3,
                                    pageOffset={"fileIndex": 1, "matchIndex": 1})
        self.assertEqual([(os.path.basename(m.file), m.line) for m in result.matches],
                         [("f2.py", 2), ("f3.py", 1), ("f3.py", 2)])
        self.assertIsNone(result.pageOffset)

    def test_limitLargerThanTotal(self) -> None:
        result = self._buildResults(list(self.CONTENT), limit=100)
        self.assertEqual(len(result.matches), 6)
        self.assertIsNone(result.pageOffset)

    def test_noMatchingFiles(self) -> None:
        result = self._buildResults([], limit=10)
        self.assertEqual(result.totalFiles, 0)
        self.assertEqual(result.matches, [])
        self.assertIsNone(result.pageOffset)

    def test_pageBoundaryAtFileEnd(self) -> None:
        # f1.py has 3 matches, f2.py has 2. The first page must end exactly at
        # the last match of f1.py, not mid-file.
        content: Dict[str, Optional[str]] = {
            "C:/test/f1.py": "a target\nb target\nc target\n",
            "C:/test/f2.py": "d target\ne target\n",
        }
        page1 = self._buildResults(list(content), limit=3, content=content)
        self.assertEqual([(os.path.basename(m.file), m.line) for m in page1.matches],
                         [("f1.py", 1), ("f1.py", 2), ("f1.py", 3)])
        self.assertEqual(page1.pageOffset, {"fileIndex": 1, "matchIndex": 0})

        page2 = self._buildResults(list(content), limit=3, pageOffset=page1.pageOffset, content=content)
        self.assertEqual([(os.path.basename(m.file), m.line) for m in page2.matches],
                         [("f2.py", 1), ("f2.py", 2)])
        self.assertIsNone(page2.pageOffset)

    def test_unreadableFileIsSkipped(self) -> None:
        # The unreadable file still occupies its slot in the file index: the
        # cursor after the first page must point past it.
        content: Dict[str, Optional[str]] = {
            "C:/test/f1.py": "alpha target\n",
            "C:/test/bad.py": None,
            "C:/test/f3.py": "beta target\n",
        }
        page1 = self._buildResults(list(content), limit=1, content=content)
        self.assertEqual([os.path.basename(m.file) for m in page1.matches], ["f1.py"])
        self.assertEqual(page1.pageOffset, {"fileIndex": 2, "matchIndex": 0})

        page2 = self._buildResults(list(content), limit=1, pageOffset=page1.pageOffset, content=content)
        self.assertEqual([os.path.basename(m.file) for m in page2.matches], ["f3.py"])
        self.assertIsNone(page2.pageOffset)

    def test_pageOffsetBeyondEnd(self) -> None:
        result = self._buildResults(list(self.CONTENT), limit=10,
                                    pageOffset={"fileIndex": 99, "matchIndex": 0})
        self.assertEqual(result.matches, [])
        self.assertIsNone(result.pageOffset)
        self.assertEqual(result.totalFiles, 3)

    def test_contextLines(self) -> None:
        content: Dict[str, Optional[str]] = {
            "C:/test/f1.py": "line one\ntarget here\nline three\n",
        }
        noContext = self._buildResults(list(content), limit=10, contextLines=0, content=content)
        self.assertEqual(noContext.matches[0].contextBefore, [])
        self.assertEqual(noContext.matches[0].contextAfter, [])

        # Requesting more context than available must be clamped to the file bounds.
        # The trailing newline produces an empty last line, so after-context ends there.
        clamped = self._buildResults(list(content), limit=10, contextLines=5, content=content)
        self.assertEqual(clamped.matches[0].contextBefore, ["line one"])
        self.assertEqual(clamped.matches[0].contextAfter, ["line three", ""])

    def test_matchFields(self) -> None:
        content: Dict[str, Optional[str]] = {
            "C:/test/f1.py": "line one\nalpha target here\n",
        }
        result = self._buildResults(list(content), limit=10, content=content)
        m = result.matches[0]
        self.assertEqual(m.line, 2)
        self.assertEqual(m.matchText, "target")
        self.assertEqual(m.fullLine, "alpha target here")

    def test_cachedMatchesAreUsed(self) -> None:
        content: Dict[str, Optional[str]] = {
            "C:/test/f1.py": "hello world\n",
            "C:/test/f2.py": "hello world\n",
        }
        # Pre-populate the match cache with positions a real "target" search
        # could never produce. If the results contain them, the cached path
        # was used instead of re-scanning the file.
        for filePath in content:
            key = self.provider._makeFileMatchCacheKey(self.query, filePath)
            self.provider._fileMatchesCache.set(key, [MatchPosition(0, 5)])

        result = self._buildResults(list(content), limit=10, content=content)
        self.assertEqual([m.matchText for m in result.matches], ["hello", "hello"])
        self.assertEqual([m.line for m in result.matches], [1, 1])

    def test_searchContentPublicApi(self) -> None:
        # Exercise the public searchContent() end to end: mocked index search
        # returns the file list, pagination is done by _buildContentResults.
        provider = object.__new__(SearchProvider)
        provider._fileListCache = TTLCache(60)
        provider._fileMatchesCache = TTLCache(60)
        provider._commonKeywordMap = {}
        provider._indexResolver = SearchIndexResolver(mock.MagicMock())
        indexConf = mock.MagicMock()
        indexConf.displayName.return_value = "loc1"
        content: Dict[str, Optional[str]] = {
            "C:/test/f1.py": "alpha target\nbeta target\n",
            "C:/test/f2.py": "gamma target\ndelta target\n",
        }

        def read(filePath: str) -> str:
            value = content[filePath]
            if value is None:
                raise OSError(filePath)
            return value

        with mock.patch.object(provider._indexResolver, "resolve", return_value=indexConf), \
             mock.patch("ai_agent.SearchProvider.SearchMethods") as sm, \
             mock.patch("ai_agent.SearchProvider.freadall", side_effect=read):
            sm.return_value.searchContent.return_value = ResultSet(matches=list(content))
            # Comment exclusion would load the highlighting rules and with them
            # the global config, which this test deliberately avoids (see setUp).
            page1 = provider.searchContent("target", limit=2, excludeComments=False)
            page2 = provider.searchContent("target", limit=2, pageOffset=page1.pageOffset, excludeComments=False)
            # The file list is cached: the second page must not re-run the index search.
            self.assertEqual(sm.return_value.searchContent.call_count, 1)

        self.assertEqual([(os.path.basename(m.file), m.line) for m in page1.matches],
                         [("f1.py", 1), ("f1.py", 2)])
        self.assertEqual(page1.pageOffset, {"fileIndex": 1, "matchIndex": 0})
        self.assertEqual([(os.path.basename(m.file), m.line) for m in page2.matches],
                         [("f2.py", 1), ("f2.py", 2)])
        self.assertIsNone(page2.pageOffset)

    def test_searchContentWithMultipleQueries_union(self) -> None:
        """OR logic: files matching ANY query are returned, even if each file only
        matches one of the alternatives. This proves the combined regex works."""
        provider = object.__new__(SearchProvider)
        provider._fileListCache = TTLCache(60)
        provider._fileMatchesCache = TTLCache(60)
        provider._commonKeywordMap = {}
        provider._indexResolver = SearchIndexResolver(mock.MagicMock())
        indexConf = mock.MagicMock()
        indexConf.displayName.return_value = "loc1"
        # Each file matches only ONE of the two queries
        content: Dict[str, Optional[str]] = {
            "C:/test/f1.py": "alpha target only here\n",
            "C:/test/f2.py": "gamma different only here\n",
        }

        def read(filePath: str) -> str:
            value = content[filePath]
            if value is None:
                raise OSError(filePath)
            return value

        with mock.patch.object(provider._indexResolver, "resolve", return_value=indexConf), \
             mock.patch("ai_agent.SearchProvider.SearchMethods") as sm, \
             mock.patch("ai_agent.SearchProvider.freadall", side_effect=read):
            sm.return_value.searchContent.return_value = ResultSet(matches=list(content))

            result = provider.searchContent(["target", "different"], limit=10, excludeComments=False)
            # Both files should be returned (OR: f1 matches "target", f2 matches "different")
            self.assertEqual(result.totalFiles, 2)
            self.assertEqual(len(result.matches), 2)
            # Verify the match text shows each file matched the correct alternative
            self.assertEqual(result.matches[0].file, "C:/test/f1.py")
            self.assertEqual(result.matches[0].matchText, "target")
            self.assertEqual(result.matches[1].file, "C:/test/f2.py")
            self.assertEqual(result.matches[1].matchText, "different")
            # Only a single search call (orSearchFor is passed in QueryParams)
            self.assertEqual(sm.return_value.searchContent.call_count, 1)
            # Verify orSearchFor was passed through
            callArgs = sm.return_value.searchContent.call_args[0]
            self.assertEqual(callArgs[0].orSearchFor, ["different"])

    def test_searchContentMultipleQueries_areOrNotAnd(self) -> None:
        """Prove OR vs AND: a file with 'target' but NOT 'different' is still
        returned when searching for ['target', 'different']. With AND it would
        be excluded."""
        provider = object.__new__(SearchProvider)
        provider._fileListCache = TTLCache(60)
        provider._fileMatchesCache = TTLCache(60)
        provider._commonKeywordMap = {}
        provider._indexResolver = SearchIndexResolver(mock.MagicMock())
        indexConf = mock.MagicMock()
        indexConf.displayName.return_value = "loc1"
        # f1 has only "target", f2 has only "different"
        content: Dict[str, Optional[str]] = {
            "C:/test/f1.py": "only target here\n",
            "C:/test/f2.py": "only different here\n",
        }

        def read(filePath: str) -> str:
            value = content[filePath]
            if value is None:
                raise OSError(filePath)
            return value

        with mock.patch.object(provider._indexResolver, "resolve", return_value=indexConf), \
             mock.patch("ai_agent.SearchProvider.SearchMethods") as sm, \
             mock.patch("ai_agent.SearchProvider.freadall", side_effect=read):
            sm.return_value.searchContent.return_value = ResultSet(matches=list(content))

            result = provider.searchContent(["target", "different"], limit=10, excludeComments=False)
            # Both files must be present (OR)
            self.assertEqual(result.totalFiles, 2)
            self.assertEqual(len(result.matches), 2)

            # Single query "target" would only find f1
            result2 = provider.searchContent("target", limit=10, excludeComments=False)
            self.assertEqual(len(result2.matches), 1)
            self.assertEqual(os.path.basename(result2.matches[0].file), "f1.py")