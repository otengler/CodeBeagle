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

import unittest
from typing import Any, Dict, List, cast
from .search_provider import ContentMatch, ContentSearchResult, FileSearchResult, TTLCache
from .server import HttpError, _contentResultToJson, _fileNameResultToJson

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

if __name__ == "__main__":
    unittest.main()