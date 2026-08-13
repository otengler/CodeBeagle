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
import unittest
from typing import Any, Dict, List, Optional, Tuple, cast
from unittest import mock
from .search_provider import ContentMatch, ContentSearchResult, FileSearchResult, SearchProvider
from .server import HttpError, _contentResultToJson, _fileNameResultToJson
from .ttl_cache import TTLCache
from .AgentHistory import AgentHistory, HistoryEntry, formatBodyParams
from fulltextindex.IStringMatcher import MatchPosition
from fulltextindex.Query import ContentQuery, QueryParams
from fulltextindex.SearchMethods import ResultSet

class TestTTLCache(unittest.TestCase):
    def test_getSet(self) -> None:
        cache = TTLCache(ttlSeconds=60)
        cache.set("key1", "value1")
        self.assertEqual(cache.get("key1"), "value1")
        self.assertIsNone(cache.get("nonexistent"))

    def test_clear(self) -> None:
        cache = TTLCache(ttlSeconds=60)
        cache.set("key1", "value1")
        cache.clear()
        self.assertIsNone(cache.get("key1"))

    def test_ttl(self) -> None:
        cache = TTLCache(ttlSeconds=0)  # 0 second TTL = instant expiry
        cache.set("key1", "value1")
        import time
        time.sleep(0.01)
        self.assertIsNone(cache.get("key1"))

class TestJsonConversion(unittest.TestCase):
    def test_contentResultToJson(self) -> None:
        matches = [
            ContentMatch(
                file="C:/test/main.py",
                line=10,
                matchText="def main",
                contextBefore=["import sys", ""],
                contextAfter=["    print('hello')", "    return 0"],
                fullLine="def main():"
            )
        ]
        result = ContentSearchResult(totalFiles=1, matches=matches)
        j: Dict[str, Any] = _contentResultToJson(result)
        self.assertEqual(j["totalFiles"], 1)
        self.assertEqual(len(cast(List[Any], j["matches"])), 1)
        self.assertNotIn("pageOffset", j)
        m = cast(Dict[str, Any], j["matches"][0])
        self.assertEqual(m["file"], "C:/test/main.py")
        self.assertEqual(m["line"], 10)
        self.assertEqual(m["matchText"], "def main")
        self.assertEqual(m["fullLine"], "def main():")

    def test_contentResultWithPageOffset(self) -> None:
        result = ContentSearchResult(
            totalFiles=10, matches=[],
            pageOffset={"fileIndex": 2, "matchIndex": 1}
        )
        j: Dict[str, Any] = _contentResultToJson(result)
        self.assertIn("pageOffset", j)
        self.assertEqual(j["pageOffset"], {"fileIndex": 2, "matchIndex": 1})

    def test_fileNameResultToJson(self) -> None:
        result = FileSearchResult(
            totalFiles=5, files=["a.py", "b.py"],
            pageOffset={"fileIndex": 2}
        )
        j: Dict[str, Any] = _fileNameResultToJson(result)
        self.assertEqual(j["totalFiles"], 5)
        self.assertEqual(j["files"], ["a.py", "b.py"])
        self.assertEqual(j["pageOffset"], {"fileIndex": 2})

    def test_fileNameResultNoPageOffset(self) -> None:
        result = FileSearchResult(totalFiles=3, files=["x.py"])
        j: Dict[str, Any] = _fileNameResultToJson(result)
        self.assertNotIn("pageOffset", j)

class TestHttpError(unittest.TestCase):
    def test_httpError(self) -> None:
        err = HttpError(404, "Not found")
        self.assertEqual(err.statusCode, 404)
        self.assertEqual(err.message, "Not found")
        self.assertEqual(str(err), "Not found")

class TestAgentHistory(unittest.TestCase):
    def test_addAndEntries(self) -> None:
        history = AgentHistory(maxEntries=5)
        history.add(HistoryEntry(100.0, "GET", "/health", "", 200))
        history.add(HistoryEntry(200.0, "POST", "/search/content", "query: 'test'", 200))
        entries = history.entries()
        self.assertEqual(len(entries), 2)
        # Newest first
        self.assertEqual(entries[0].method, "POST")
        self.assertEqual(entries[0].path, "/search/content")
        self.assertEqual(entries[1].method, "GET")
        self.assertEqual(entries[1].path, "/health")

    def test_maxEntries(self) -> None:
        history = AgentHistory(maxEntries=3)
        for i in range(5):
            history.add(HistoryEntry(float(i), "GET", "/health", "", 200))
        entries = history.entries()
        self.assertEqual(len(entries), 3)
        # Oldest entries should have been evicted (timestamps 0, 1)
        self.assertEqual(entries[2].timestamp, 2.0)

    def test_timeStr(self) -> None:
        import time
        # Expected string is timezone dependent, so compute it the same way
        entry = HistoryEntry(3600.0, "GET", "/health", "", 200)
        expected = time.strftime("%H:%M:%S", time.localtime(3600.0))
        self.assertEqual(entry.timeStr(), expected)

    def test_durationStr(self) -> None:
        entry = HistoryEntry(100.0, "GET", "/health", "", 200, durationSecs=2.34)
        self.assertEqual(entry.durationStr(), "2.3s")
        self.assertEqual(entry.durationSecs, 2.34)

    def test_durationDefaultZero(self) -> None:
        entry = HistoryEntry(100.0, "GET", "/health", "", 200)
        self.assertEqual(entry.durationSecs, 0.0)
        self.assertEqual(entry.durationStr(), "0.0s")

    def test_clear(self) -> None:
        history = AgentHistory(maxEntries=10)
        history.add(HistoryEntry(1.0, "GET", "/health", "", 200))
        history.clear()
        self.assertEqual(history.entries(), [])

    def test_formatBodyParams(self) -> None:
        params = {
            "query": "hello world",
            "caseSensitive": True,
            "limit": 50,
            "pageOffset": {"fileIndex": 10}
        }
        result = formatBodyParams(params)
        self.assertIn("query: 'hello world'", result)
        self.assertIn("caseSensitive: yes", result)
        self.assertIn("limit: 50", result)
        self.assertIn("pageOffset", result)

    def test_formatBodyParams_empty(self) -> None:
        self.assertEqual(formatBodyParams({}), "")

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

        with mock.patch("ai_agent.search_provider.freadall", side_effect=read):
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

        with mock.patch.object(provider, "_resolveIndexConfig", return_value=indexConf), \
             mock.patch("ai_agent.search_provider.SearchMethods") as sm, \
             mock.patch("ai_agent.search_provider.freadall", side_effect=read):
            sm.return_value.searchContent.return_value = ResultSet(matches=list(content))
            page1 = provider.searchContent("target", limit=2)
            page2 = provider.searchContent("target", limit=2, pageOffset=page1.pageOffset)
            # The file list is cached: the second page must not re-run the index search.
            self.assertEqual(sm.return_value.searchContent.call_count, 1)

        self.assertEqual([(os.path.basename(m.file), m.line) for m in page1.matches],
                         [("f1.py", 1), ("f1.py", 2)])
        self.assertEqual(page1.pageOffset, {"fileIndex": 1, "matchIndex": 0})
        self.assertEqual([(os.path.basename(m.file), m.line) for m in page2.matches],
                         [("f2.py", 1), ("f2.py", 2)])
        self.assertIsNone(page2.pageOffset)

class TestFileNameSearchPagination(unittest.TestCase):
    """Tests for the pagination logic of SearchProvider.searchFileName."""

    def setUp(self) -> None:
        # Create the provider without running __init__ to avoid loading the config.
        self.provider = object.__new__(SearchProvider)
        self.provider._fileListCache = TTLCache(60)
        self.indexConf = mock.MagicMock()
        self.indexConf.displayName.return_value = "loc1"
        self.allFiles = [f"C:/src/proj/file{i:02d}.py" for i in range(1, 11)]

    def _search(self, limit: int,
                pageOffset: Optional[Dict[str, int]] = None) -> Tuple[FileSearchResult, mock.MagicMock]:
        with mock.patch.object(self.provider, "_resolveIndexConfig", return_value=self.indexConf), \
             mock.patch("ai_agent.search_provider.SearchMethods") as sm:
            sm.return_value.searchFileName.return_value = ResultSet(matches=list(self.allFiles))
            result = self.provider.searchFileName("*.py", limit=limit, pageOffset=pageOffset)
            return result, sm

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

if __name__ == "__main__":
    unittest.main()