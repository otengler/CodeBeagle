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

Tests for JSON serialization, HTTP errors, and path separator correction.
"""

import os
import unittest
from typing import Any, Dict, List, cast
from ..Server import HttpError, _contentResultToJson, _fileNameResultToJson, _hasExcludeFromHistory, _historyToJson
from ..SearchProvider import ContentMatch, ContentSearchResult, FileSearchResult
from ..AgentHistory import AgentHistory, HistoryEntry
from tools.FileTools import correctPath


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
        j: Dict[str, Any] = _contentResultToJson("query that differs", 2, result)
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
        j: Dict[str, Any] = _contentResultToJson("", 2, result)
        self.assertIn("pageOffset", j)
        self.assertEqual(j["pageOffset"], {"fileIndex": 2, "matchIndex": 1})

    def test_contentResultToJsonWithListQuery(self) -> None:
        matches = [
            ContentMatch(
                file="C:/test/main.py",
                line=10,
                matchText="def main",
                contextBefore=[], contextAfter=[],
                fullLine="def main():"
            )
        ]
        result = ContentSearchResult(totalFiles=1, matches=matches)
        # With list queries, matchText is always included (OR queries make it ambiguous)
        j: Dict[str, Any] = _contentResultToJson(["def main", "other"], 2, result)
        self.assertIn("matchText", cast(Dict[str, Any], j["matches"][0]))

        # When matchText is not in the query list, it should still be included
        j2: Dict[str, Any] = _contentResultToJson(["other"], 2, result)
        self.assertIn("matchText", cast(Dict[str, Any], j2["matches"][0]))

    def test_contentResultToJsonWithListQueryOmitsMatchTextWhenMatchesQuery(self) -> None:
        """With string queries, matchText is omitted when it matches the query."""
        matches = [
            ContentMatch(
                file="C:/test/main.py",
                line=10,
                matchText="def main",
                contextBefore=[], contextAfter=[],
                fullLine="def main():"
            )
        ]
        result = ContentSearchResult(totalFiles=1, matches=matches)
        # String query equal to matchText omits matchText
        j: Dict[str, Any] = _contentResultToJson("def main", 2, result)
        self.assertNotIn("matchText", cast(Dict[str, Any], j["matches"][0]))

    def test_fileNameResultToJson(self) -> None:
        result = FileSearchResult(
            totalFiles=5, files=["a.py", "b.py"],
            pageOffset={"fileIndex": 2}
        )
        j: Dict[str, Any] = _fileNameResultToJson("", result)
        self.assertEqual(j["totalFiles"], 5)
        self.assertEqual(j["files"], ["a.py", "b.py"])
        self.assertEqual(j["pageOffset"], {"fileIndex": 2})

    def test_fileNameResultNoPageOffset(self) -> None:
        result = FileSearchResult(totalFiles=3, files=["x.py"])
        j: Dict[str, Any] = _fileNameResultToJson("", result)
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
            self.assertEqual(correctPath("C:/src/proj"), "C:\\src\\proj")
        else:
            self.assertEqual(correctPath("C:/src/proj"), "C:/src/proj")

    def test_unixSeparator(self) -> None:
        if os.sep == '/':
            self.assertEqual(correctPath("C:\\src\\proj"), "C:/src/proj")
        else:
            self.assertEqual(correctPath("C:\\src\\proj"), "C:\\src\\proj")

    def test_mixedSeparators(self) -> None:
        expected = os.sep.join(["C:", "src", "proj"])
        self.assertEqual(correctPath("C:/src\\proj"), expected)

    def test_emptyString(self) -> None:
        self.assertEqual(correctPath(""), "")