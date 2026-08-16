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
from .SearchProvider import ContentMatch, ContentSearchResult, FileSearchResult, SearchProvider
from .SearchIndexResolver import SearchIndexResolver
from .Server import HttpError, _contentResultToJson, _correctPathSeparator, _fileNameResultToJson, _hasExcludeFromHistory, _historyToJson
from .TtlCache import TTLCache
from .AgentHistory import AgentHistory, HistoryEntry, formatBodyParams
from fulltextindex import IndexConfiguration
from fulltextindex.IndexConfiguration import IndexMode, IndexType
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
        j: Dict[str, Any] = _contentResultToJson("query that differs", result)
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
        j: Dict[str, Any] = _contentResultToJson("", result)
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

    def test_historyToJson(self) -> None:
        history = AgentHistory()
        history.add(HistoryEntry(100.0, "GET", "/health", "", 200))
        history.add(HistoryEntry(200.0, "POST", "/search/content", "query: 'x'", 200, durationSecs=1.5))
        j = cast(Dict[str, Any], _historyToJson(history))
        entries = cast(List[Any], j["history"])
        # Newest first
        self.assertEqual(entries[0]["method"], "POST")
        self.assertEqual(entries[0]["durationSecs"], 1.5)
        self.assertEqual(entries[1]["path"], "/health")
        self.assertEqual(entries[1]["statusCode"], 200)

    def test_historyToJsonEmpty(self) -> None:
        j = cast(Dict[str, Any], _historyToJson(AgentHistory()))
        self.assertEqual(j["history"], [])

    def test_hasExcludeFromHistory(self) -> None:
        self.assertTrue(_hasExcludeFromHistory("/api/v1/health?excludeFromHistory=1"))
        self.assertTrue(_hasExcludeFromHistory("/api/v1/health?foo=1&excludeFromHistory"))
        self.assertFalse(_hasExcludeFromHistory("/api/v1/health"))
        self.assertFalse(_hasExcludeFromHistory("/api/v1/health?other=1"))
        self.assertFalse(_hasExcludeFromHistory(""))

class TestHttpError(unittest.TestCase):
    def test_httpError(self) -> None:
        err = HttpError(404, "Not found")
        self.assertEqual(err.statusCode, 404)
        self.assertEqual(err.message, "Not found")
        self.assertEqual(str(err), "Not found")

class TestPathSeparatorCorrection(unittest.TestCase):
    def test_windowsSeparator(self) -> None:
        if os.sep == '\\':
            self.assertEqual(_correctPathSeparator("C:/src/proj"), "C:\\src\\proj")
        else:
            self.assertEqual(_correctPathSeparator("C:/src/proj"), "C:/src/proj")

    def test_unixSeparator(self) -> None:
        if os.sep == '/':
            self.assertEqual(_correctPathSeparator("C:\\src\\proj"), "C:/src/proj")
        else:
            self.assertEqual(_correctPathSeparator("C:\\src\\proj"), "C:\\src\\proj")

    def test_mixedSeparators(self) -> None:
        expected = os.sep.join(["C:", "src", "proj"])
        self.assertEqual(_correctPathSeparator("C:/src\\proj"), expected)

    def test_emptyString(self) -> None:
        self.assertEqual(_correctPathSeparator(""), "")
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
        expected = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(3600.0))
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

class TestFileNameSearchPagination(unittest.TestCase):
    """Tests for the pagination logic of SearchProvider.searchFileName."""

    def setUp(self) -> None:
        # Create the provider without running __init__ to avoid loading the config.
        self.provider = object.__new__(SearchProvider)
        self.provider._fileListCache = TTLCache(60)
        self.provider._indexResolver = SearchIndexResolver(mock.MagicMock())
        self.indexConf = mock.MagicMock()
        self.indexConf.displayName.return_value = "loc1"
        self.allFiles = [f"C:/src/proj/file{i:02d}.py" for i in range(1, 11)]

    def _search(self, limit: int,
                pageOffset: Optional[Dict[str, int]] = None) -> Tuple[FileSearchResult, mock.MagicMock]:
        with mock.patch.object(self.provider._indexResolver, "resolve", return_value=self.indexConf), \
             mock.patch("ai_agent.SearchProvider.SearchMethods") as sm:
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

class TestResolveIndexConfig(unittest.TestCase):
    """Tests for SearchIndexResolver.resolve and checkExtensionFilter."""

    def _provider(self, configs: List[IndexConfiguration.IndexConfiguration]) -> SearchProvider:
        """Return a provider with readConfig patched to return the given configs."""
        provider = object.__new__(SearchProvider)
        provider._config = mock.MagicMock()
        provider._indexResolver = SearchIndexResolver(provider._config)
        patcher = mock.patch.object(IndexConfiguration, "readConfig", return_value=configs)
        patcher.start()
        self.addCleanup(patcher.stop)
        return provider

    def _conf(self, name: str, directories: str, dirExcludes: str = "",
              indexUpdateMode: IndexMode = IndexMode.TriggeredIndexUpdate,
              indexType: IndexType = IndexType.FileContentAndName) -> IndexConfiguration.IndexConfiguration:
        return IndexConfiguration.IndexConfiguration(
            indexName=name, extensions=".py", directories=directories,
            dirExcludes=dirExcludes, indexdb=f"C:/idx/{name}.idx",
            indexUpdateMode=indexUpdateMode, indexType=indexType)

    def test_locationMatch(self) -> None:
        conf = self._conf("loc1", "C:/src/proj")
        provider = self._provider([conf])
        self.assertEqual(provider._indexResolver.resolve(location="loc1"), conf)

    def test_locationNotFound(self) -> None:
        conf = self._conf("loc1", "C:/src/proj")
        provider = self._provider([conf])
        with self.assertRaises(ValueError):
            provider._indexResolver.resolve(location="nope")

    def test_neitherLocationNorFolderRaises(self) -> None:
        conf = self._conf("loc1", "C:/src/proj")
        provider = self._provider([conf])
        with self.assertRaises(ValueError):
            provider._indexResolver.resolve()

    def test_folderInSubdirectory(self) -> None:
        conf = self._conf("loc1", "C:/src/proj")
        provider = self._provider([conf])
        self.assertEqual(provider._indexResolver.resolve(folder="C:/src/proj/sub/dir"), conf)

    def test_folderNotCoveredRaises(self) -> None:
        conf = self._conf("loc1", "C:/src/proj")
        provider = self._provider([conf])
        with self.assertRaises(ValueError):
            provider._indexResolver.resolve(folder="C:/other/proj")

    def test_prefersContentIndexed(self) -> None:
        noIndex = self._conf("plain", "C:/src/proj", indexUpdateMode=IndexMode.NoIndexWanted)
        indexed = self._conf("idx", "C:/src/proj")
        provider = self._provider([noIndex, indexed])
        self.assertEqual(provider._indexResolver.resolve(folder="C:/src/proj", searchType="content"), indexed)

    def test_prefersFileNameIndexed(self) -> None:
        contentOnly = self._conf("content", "C:/src/proj", indexType=IndexType.FileContent)
        fileName = self._conf("fname", "C:/src/proj", indexType=IndexType.FileName)
        provider = self._provider([contentOnly, fileName])
        self.assertEqual(provider._indexResolver.resolve(folder="C:/src/proj", searchType="filename"), fileName)

    def test_contentSearchDoesNotCountFileNameOnlyIndex(self) -> None:
        contentOnly = self._conf("content", "C:/src/proj", indexType=IndexType.FileContent)
        fileName = self._conf("fname", "C:/src/proj", indexType=IndexType.FileName)
        provider = self._provider([contentOnly, fileName])
        self.assertEqual(provider._indexResolver.resolve(folder="C:/src/proj", searchType="content"), contentOnly)

    def test_folderExcludedByDirExcludes(self) -> None:
        conf = self._conf("loc1", "C:/src/proj", dirExcludes="C:/src/proj/build")
        provider = self._provider([conf])
        with self.assertRaises(ValueError):
            provider._indexResolver.resolve(folder="C:/src/proj/build")

    def test_folderNotExcluded(self) -> None:
        conf = self._conf("loc1", "C:/src/proj", dirExcludes="C:/src/proj/build")
        provider = self._provider([conf])
        self.assertEqual(provider._indexResolver.resolve(folder="C:/src/proj/src"), conf)

    def test_excludedParentDoesNotDisqualify(self) -> None:
        # os.walk descends into subdirectories even if a parent matches an
        # exclude (genFind only skips files directly in the excluded directory),
        # so a folder below an excluded parent is still covered.
        conf = self._conf("loc1", "C:/src/proj", dirExcludes="C:/src/proj/build")
        provider = self._provider([conf])
        self.assertEqual(provider._indexResolver.resolve(folder="C:/src/proj/build/sub/deep"), conf)

    def test_wildcardExclude(self) -> None:
        conf = self._conf("loc1", "C:/src/proj", dirExcludes="*/build")
        provider = self._provider([conf])
        with self.assertRaises(ValueError):
            provider._indexResolver.resolve(folder="C:/src/proj/build")

    def test_questionMarkExclude(self) -> None:
        conf = self._conf("loc1", "C:/src/proj", dirExcludes="C:/src/proj/buil?")
        provider = self._provider([conf])
        with self.assertRaises(ValueError):
            provider._indexResolver.resolve(folder="C:/src/proj/build")

    def test_excludeIsCaseInsensitive(self) -> None:
        conf = self._conf("loc1", "C:/src/proj", dirExcludes="C:/SRC/PROJ/BUILD")
        provider = self._provider([conf])
        with self.assertRaises(ValueError):
            provider._indexResolver.resolve(folder="C:/src/proj/build")

    def test_excludedConfigSkippedInFavorOfCoveringConfig(self) -> None:
        excluded = self._conf("excluded", "C:/src/proj", dirExcludes="C:/src/proj/build")
        covering = self._conf("covering", "C:/src/proj")
        provider = self._provider([excluded, covering])
        self.assertEqual(provider._indexResolver.resolve(folder="C:/src/proj/build"), covering)

    def _confExt(self, name: str, extensions: str,
                 indexType: IndexType = IndexType.FileContentAndName) -> IndexConfiguration.IndexConfiguration:
        return IndexConfiguration.IndexConfiguration(
            indexName=name, extensions=extensions, directories="C:/src/proj",
            indexdb=f"C:/idx/{name}.idx", indexType=indexType)

    def test_preferConfigMatchingExtensionFilter(self) -> None:
        pyConf = self._confExt("py", ".py")
        cppConf = self._confExt("cpp", ".cpp")
        provider = self._provider([pyConf, cppConf])
        self.assertEqual(provider._indexResolver.resolve(folder="C:/src/proj", extensionFilter="*.py"), pyConf)
        self.assertEqual(provider._indexResolver.resolve(folder="C:/src/proj", extensionFilter="*.cpp"), cppConf)

    def test_preferExtensionMatchOverFirstIndexed(self) -> None:
        noIndex = self._conf("noIdx", "C:/src/proj", indexUpdateMode=IndexMode.NoIndexWanted)
        pyConf = self._confExt("py", ".py")
        cppConf = self._confExt("cpp", ".cpp")
        provider = self._provider([noIndex, pyConf, cppConf])
        # pyConf is the first indexed config, but the *.cpp filter picks cppConf
        self.assertEqual(provider._indexResolver.resolve(folder="C:/src/proj", extensionFilter="*.cpp"), cppConf)

    def test_fallbackToFirstIndexedWhenNoConfExtMatches(self) -> None:
        pyConf = self._confExt("py", ".py")
        cppConf = self._confExt("cpp", ".cpp")
        provider = self._provider([pyConf, cppConf])
        # neither py nor cpp covers both .py and .cpp — falls back to first indexed
        self.assertEqual(provider._indexResolver.resolve(folder="C:/src/proj", extensionFilter="*.py,*.cpp"), pyConf)

    def test_negativeOnlyFilterDoesNotAffectSelection(self) -> None:
        pyConf = self._confExt("py", ".py")
        cppConf = self._confExt("cpp", ".cpp")
        # a negative-only filter has no positive parts to match: first indexed wins
        provider = self._provider([cppConf, pyConf])
        self.assertEqual(provider._indexResolver.resolve(folder="C:/src/proj", extensionFilter="-*.test"), cppConf)

    def test_extensionFitConsideredForContentSearch(self) -> None:
        pyConf = self._confExt("py", ".py", indexType=IndexType.FileContent)
        cppConf = self._confExt("cpp", ".cpp", indexType=IndexType.FileName)
        provider = self._provider([cppConf, pyConf])
        # content search with *.py filter prefers py even though cpp is first
        self.assertEqual(provider._indexResolver.resolve(
            folder="C:/src/proj", searchType="content", extensionFilter="*.py"), pyConf)

    def _confWithExtensions(self, name: str, extensions: str) -> IndexConfiguration.IndexConfiguration:
        return IndexConfiguration.IndexConfiguration(
            indexName=name, extensions=extensions, directories="C:/src/proj",
            indexdb=f"C:/idx/{name}.idx")

    def test_extensionCovered(self) -> None:
        conf = self._confWithExtensions("loc1", ".py")
        provider = self._provider([conf])
        provider._indexResolver.checkExtensionFilter("*.py", conf)

    def test_extensionNotCoveredRaises(self) -> None:
        conf = self._confWithExtensions("loc1", ".py")
        provider = self._provider([conf])
        with self.assertRaises(ValueError):
            provider._indexResolver.checkExtensionFilter("*.txt", conf)

    def test_emptyFilterIsFine(self) -> None:
        conf = self._confWithExtensions("loc1", ".py")
        provider = self._provider([conf])
        provider._indexResolver.checkExtensionFilter("", conf)

    def test_wildcardExtensionCovered(self) -> None:
        conf = self._confWithExtensions("loc1", ".py")
        provider = self._provider([conf])
        provider._indexResolver.checkExtensionFilter("*.p?", conf)

    def test_wildcardMatchingNothingRaises(self) -> None:
        # '.jsx?' matches '.jsxx' but not '.js': the pattern covers nothing
        # the config indexes, so it must raise.
        conf = self._confWithExtensions("loc1", ".js")
        provider = self._provider([conf])
        with self.assertRaises(ValueError):
            provider._indexResolver.checkExtensionFilter("*.jsx?", conf)

    def test_wildcardAllMatches(self) -> None:
        conf = self._confWithExtensions("loc1", ".py,.cpp")
        provider = self._provider([conf])
        provider._indexResolver.checkExtensionFilter("*", conf)
        provider._indexResolver.checkExtensionFilter(".*", conf)

    def test_negativeFilterPartsNotChecked(self) -> None:
        # A negative part only narrows results; it does not require the config
        # to index that extension.
        conf = self._confWithExtensions("loc1", ".py")
        provider = self._provider([conf])
        provider._indexResolver.checkExtensionFilter("*.py,-*.txt", conf)

    def test_negativeFilterOnly(self) -> None:
        conf = self._confWithExtensions("loc1", ".py")
        provider = self._provider([conf])
        provider._indexResolver.checkExtensionFilter("-*.txt", conf)

    def test_multiplePositiveOneMissingRaises(self) -> None:
        conf = self._confWithExtensions("loc1", ".py,.cpp")
        provider = self._provider([conf])
        with self.assertRaises(ValueError):
            provider._indexResolver.checkExtensionFilter("*.py,*.java", conf)

    def test_extensionCheckRunsInContentSearch(self) -> None:
        conf = self._confWithExtensions("loc1", ".py")
        provider = self._provider([conf])
        provider._fileListCache = mock.MagicMock()
        provider._fileListCache.get.return_value = None
        provider._commonKeywordMap = {}
        with mock.patch("ai_agent.SearchProvider.SearchMethods") as sm:
            sm.return_value.searchContent.return_value = ResultSet(matches=[])
            with self.assertRaises(ValueError):
                provider.searchContent("foo", folder="C:/src/proj", extensionFilter="*.java")
            provider.searchContent("foo", folder="C:/src/proj", extensionFilter="*.py")

    def test_extensionCheckRunsInFileNameSearch(self) -> None:
        conf = self._confWithExtensions("loc1", ".py")
        provider = self._provider([conf])
        provider._fileListCache = mock.MagicMock()
        provider._fileListCache.get.return_value = None
        with mock.patch("ai_agent.SearchProvider.SearchMethods") as sm:
            sm.return_value.searchFileName.return_value = ResultSet(matches=[])
            with self.assertRaises(ValueError):
                provider.searchFileName("*.py", folder="C:/src/proj", extensionFilter="*.java")
            provider.searchFileName("*.py", folder="C:/src/proj", extensionFilter="*.py")

class TestAgentState(unittest.TestCase):
    """Tests for the central agent server start/stop helpers."""

    def setUp(self) -> None:
        from . import AgentState
        self.AgentState = AgentState
        self.AgentState.setAgentServer(None)
        self.AgentState._externalServerRunning = False

    def tearDown(self) -> None:
        self.AgentState.setAgentServer(None)
        self.AgentState._externalServerRunning = False

    def _mockAppConfig(self) -> mock.MagicMock:
        """Return a mock appConfig whose agent section points at the default port."""
        appConfig = mock.MagicMock()
        appConfig.agent.bind = "127.0.0.1"
        appConfig.agent.port = 8080
        return appConfig

    def test_startStartsServerAndRegistersIt(self) -> None:
        with mock.patch("ai_agent.AgentState.AgentServer") as serverClass:
            serverClass.return_value.start.return_value = True
            self.assertTrue(self.AgentState.startAgentServer(8080))
            serverClass.return_value.start.assert_called_once()
            self.assertIs(self.AgentState.agentServer(), serverClass.return_value)

    def test_startFailureReturnsFalse(self) -> None:
        with mock.patch("ai_agent.AgentState.AgentServer") as serverClass:
            serverClass.return_value.start.return_value = False
            self.assertFalse(self.AgentState.startAgentServer(8080))
            self.assertIsNone(self.AgentState.agentServer())

    def test_startDoesNotRestartRunningServer(self) -> None:
        with mock.patch("ai_agent.AgentState.AgentServer") as serverClass:
            serverClass.return_value.start.return_value = True
            self.assertTrue(self.AgentState.startAgentServer(8080))
            self.assertTrue(self.AgentState.startAgentServer(8080))
            self.assertEqual(serverClass.return_value.start.call_count, 1)

    def test_stopStopsAndUnregistersServer(self) -> None:
        with mock.patch("ai_agent.AgentState.AgentServer") as serverClass:
            serverClass.return_value.start.return_value = True
            self.assertTrue(self.AgentState.startAgentServer(8080))
            self.AgentState.stopAgentServer()
            serverClass.return_value.stop.assert_called_once()
            self.assertIsNone(self.AgentState.agentServer())

    def test_stopWithoutServerIsNoOp(self) -> None:
        self.AgentState.stopAgentServer()
        self.assertIsNone(self.AgentState.agentServer())

    def test_startDoesNotStartWhenExternalServerRunning(self) -> None:
        with mock.patch("ai_agent.AgentState.AgentServer") as serverClass:
            self.AgentState._externalServerRunning = True
            try:
                self.assertTrue(self.AgentState.startAgentServer(8080))
                serverClass.return_value.start.assert_not_called()
                self.assertIsNone(self.AgentState.agentServer())
            finally:
                self.AgentState._externalServerRunning = False

    def test_applyChangesDoesNotTouchServerWhenExternalRunning(self) -> None:
        with mock.patch("ai_agent.AgentState.AgentServer") as serverClass:
            serverClass.return_value.start.return_value = True
            self.AgentState._externalServerRunning = True
            try:
                self.assertTrue(self.AgentState.applyAgentServerChanges(True, 8080))
                serverClass.return_value.start.assert_not_called()
                self.assertTrue(self.AgentState.applyAgentServerChanges(False, 8080))
                self.assertIsNone(self.AgentState.agentServer())
            finally:
                self.AgentState._externalServerRunning = False

    def test_checkExternalAgentServerDetectsHealthEndpoint(self) -> None:
        response = mock.MagicMock()
        response.status = 200
        response.__enter__.return_value = response  # context manager returns itself
        with mock.patch("ai_agent.AgentState.appConfig",
                        return_value=self._mockAppConfig()), \
             mock.patch("ai_agent.AgentState.urllib.request.urlopen",
                        return_value=response) as urlopen:
            self.assertTrue(self.AgentState.checkExternalAgentServer())
            urlopen.assert_called_once()
            # The probe must carry excludeFromHistory so that it is not recorded
            # in the API history of the external server.
            url = urlopen.call_args[0][0]
            self.assertIn("excludeFromHistory=1", url)
            self.assertTrue(self.AgentState.externalServerRunning())

    def test_checkExternalAgentServerNoServer(self) -> None:
        with mock.patch("ai_agent.AgentState.appConfig",
                        return_value=self._mockAppConfig()), \
             mock.patch("ai_agent.AgentState.urllib.request.urlopen",
                        side_effect=OSError("connection refused")):
            self.assertFalse(self.AgentState.checkExternalAgentServer())
            self.assertFalse(self.AgentState.externalServerRunning())

    def test_fetchExternalHistoryParsesEntries(self) -> None:
        body = (b'{"history": ['
                b'{"timestamp": 200.0, "method": "POST", "path": "/search/content", '
                b'"params": "query: \'x\'", "statusCode": 200, "durationSecs": 1.5}]}')
        response = mock.MagicMock()
        response.status = 200
        response.read.return_value = body
        response.__enter__.return_value = response
        self.AgentState._externalServerRunning = True
        try:
            with mock.patch("ai_agent.AgentState.appConfig",
                            return_value=self._mockAppConfig()), \
                 mock.patch("ai_agent.AgentState.urllib.request.urlopen",
                            return_value=response) as urlopen:
                entries = self.AgentState.fetchExternalHistory()
            urlopen.assert_called_once()
            self.assertEqual(len(entries), 1)
            entry = entries[0]
            self.assertEqual(entry.method, "POST")
            self.assertEqual(entry.path, "/search/content")
            self.assertEqual(entry.params, "query: 'x'")
            self.assertEqual(entry.statusCode, 200)
            self.assertEqual(entry.durationSecs, 1.5)
        finally:
            self.AgentState._externalServerRunning = False

    def test_fetchExternalHistoryNoExternalServer(self) -> None:
        self.AgentState._externalServerRunning = False
        with mock.patch("ai_agent.AgentState.urllib.request.urlopen") as urlopen:
            self.assertEqual(self.AgentState.fetchExternalHistory(), [])
            urlopen.assert_not_called()

    def test_fetchExternalHistoryFailureReturnsEmpty(self) -> None:
        self.AgentState._externalServerRunning = True
        try:
            with mock.patch("ai_agent.AgentState.appConfig",
                            return_value=self._mockAppConfig()), \
                 mock.patch("ai_agent.AgentState.urllib.request.urlopen",
                            side_effect=OSError("connection refused")):
                self.assertEqual(self.AgentState.fetchExternalHistory(), [])
        finally:
            self.AgentState._externalServerRunning = False

if __name__ == "__main__":
    unittest.main()