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

Tests for FileNameSearch pagination logic.
"""

import unittest
from typing import Dict, List, Optional, Tuple
from unittest import mock
from ..SearchProvider import FileSearchResult, SearchProvider
from ..SearchIndexResolver import SearchIndexResolver
from ..TtlCache import TTLCache
from fulltextindex.SearchMethods import ResultSet


class TestFileNameSearchPagination(unittest.TestCase):
    """Tests for the pagination logic of SearchProvider.searchFileName."""

    def setUp(self) -> None:
        # Create the provider without running __init__ to avoid loading the config.
        self.provider = object.__new__(SearchProvider)
        self.provider._fileListCache = TTLCache(60)
        self.provider._indexResolver = SearchIndexResolver(mock.MagicMock())
        self.indexConf = mock.MagicMock()
        self.indexConf.displayName.return_value = "loc1"
        self.indexConf.extensions = [".py"]
        self.allFiles = [f"C:/src/proj/file{i:02d}.py" for i in range(1, 11)]

    def _search(self, limit: int,
                pageOffset: Optional[Dict[str, int]] = None) -> Tuple[FileSearchResult, mock.MagicMock]:
        with mock.patch.object(self.provider._indexResolver, "resolve", return_value=self.indexConf), \
             mock.patch("ai_agent.SearchProvider.SearchMethods") as sm:
            sm.return_value.searchFileName.return_value = ResultSet(matches=list(self.allFiles))
            result = self.provider.searchFileName("*.py", limit=limit, pageOffset=pageOffset)
            return result, sm

    def test_emptyQueryListReturnsEmpty(self) -> None:
        """An empty list of queries should return an empty result."""
        provider = object.__new__(SearchProvider)
        provider._fileListCache = TTLCache(60)
        provider._fileMatchesCache = TTLCache(60)
        provider._commonKeywordMap = {}
        provider._indexResolver = SearchIndexResolver(mock.MagicMock())
        indexConf = mock.MagicMock()
        indexConf.displayName.return_value = "loc1"
        with mock.patch.object(provider._indexResolver, "resolve", return_value=indexConf):
            result = provider.searchContent([], limit=10, excludeComments=False)
            self.assertEqual(result.totalFiles, 0)
            self.assertEqual(result.matches, [])

    def test_firstPage(self) -> None:
        result, _ = self._search(limit=3)
        self.assertEqual(result.totalFiles, 10)
        self.assertEqual(result.files, self.allFiles[:3])
        self.assertEqual(result.pageOffset, {"fileIndex": 3})

    def test_middlePage(self) -> None:
        result, _ = self._search(limit=3, pageOffset={"fileIndex": 6})
        self.assertEqual(result.files, self.allFiles[6:9])
        self.assertEqual(result.pageOffset, {"fileIndex": 9})

    def test_lastPage(self) -> None:
        result, _ = self._search(limit=3, pageOffset={"fileIndex": 9})
        self.assertEqual(result.files, self.allFiles[9:])
        self.assertIsNone(result.pageOffset)

    def test_exactMultiplePages(self) -> None:
        r1, _ = self._search(limit=5)
        self.assertEqual(r1.files, self.allFiles[:5])
        self.assertEqual(r1.pageOffset, {"fileIndex": 5})

        r2, _ = self._search(limit=5, pageOffset=r1.pageOffset)
        self.assertEqual(r2.files, self.allFiles[5:])
        self.assertIsNone(r2.pageOffset)

    def test_limitLargerThanTotal(self) -> None:
        result, _ = self._search(limit=100)
        self.assertEqual(result.files, self.allFiles)
        self.assertIsNone(result.pageOffset)

    def test_fileListIsCached(self) -> None:
        _, sm = self._search(limit=3)
        result2, _ = self._search(limit=3, pageOffset={"fileIndex": 3})
        # The second page must come from the cached file list, not a new search.
        self.assertEqual(sm.return_value.searchFileName.call_count, 1)
        self.assertEqual(result2.files, self.allFiles[3:6])