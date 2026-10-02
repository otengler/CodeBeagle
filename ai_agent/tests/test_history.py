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

Tests for AgentHistory.
"""

import time
import unittest
from ..AgentHistory import AgentHistory, HistoryEntry, formatBodyParams


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

    def test_isRunning_default(self) -> None:
        entry = HistoryEntry(100.0, "GET", "/health", "", 200)
        self.assertFalse(entry.isRunning)

    def test_isRunning_flag(self) -> None:
        entry = HistoryEntry(200.0, "POST", "/search/content", "", isRunning=True)
        self.assertTrue(entry.isRunning)
        self.assertEqual(entry.result, "")

    def test_isRunning_durationStr(self) -> None:
        """A running entry should compute its own duration live."""
        start = time.time() - 1.5  # 1.5 seconds ago
        entry = HistoryEntry(start, "GET", "/search", "", isRunning=True)
        dur = entry.durationStr()
        # The computed duration should be close to 1.5s (but not exact due to
        # the time elapsed since we constructed the entry).
        self.assertTrue(dur.endswith("s"))
        val = float(dur[:-1])
        self.assertGreaterEqual(val, 1.4)
        self.assertLess(val, 5.0)

    def test_finish(self) -> None:
        """finish() should set result/statusCode and compute duration."""
        start = time.time()
        entry = HistoryEntry(start, "POST", "/search/content", "", isRunning=True)
        entry.finish(200, "10 matches, 3 files")
        self.assertEqual(entry.statusCode, 200)
        self.assertEqual(entry.result, "10 matches, 3 files")
        self.assertFalse(entry.isRunning)
        # Duration should be very small (near zero since we just created it)
        self.assertLess(entry.durationSecs, 1.0)
        self.assertGreaterEqual(entry.durationSecs, 0.0)

    def test_finish_with_params(self) -> None:
        """finish() accepts optional params to replace the initial placeholder."""
        entry = HistoryEntry(time.time(), "POST", "/search/content", "", isRunning=True)
        entry.finish(200, "ok", params="query: 'test'")
        self.assertEqual(entry.params, "query: 'test'")

    def test_finish_updates_durationStr(self) -> None:
        """After finish() the durationStr should use the stored durationSecs,
        and isRunning must be cleared."""
        start = time.time()
        entry = HistoryEntry(start, "GET", "/health", "", isRunning=True)
        entry.finish(200, "ok")
        self.assertFalse(entry.isRunning)
        # Duration should be a small positive value (the actual wall-clock
        # time elapsed between construction and finish()).
        self.assertLess(entry.durationSecs, 5.0)
        self.assertGreaterEqual(entry.durationSecs, 0.0)
        # durationStr() now uses the stored value, not the live clock
        self.assertTrue(entry.durationStr().endswith("s"))