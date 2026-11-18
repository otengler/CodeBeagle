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

Tests for the extended timeout messages of SearchProvider.
"""

import unittest
from typing import Any, List
from unittest import mock
from ..SearchProvider import SearchProvider
from ..SearchIndexResolver import SearchIndexResolver
from fulltextindex import IndexConfiguration
from fulltextindex.IndexConfiguration import IndexMode, IndexType
from fulltextindex.SearchMethods import ResultSet


class TestTimeoutMessage(unittest.TestCase):
    """Tests for SearchProvider._timeoutMessage."""

    def _provider(self, configs: List[IndexConfiguration.IndexConfiguration]) -> SearchProvider:
        """Return a provider with readConfig patched to return the given configs."""
        provider = object.__new__(SearchProvider)
        provider._config = mock.MagicMock()
        provider._indexResolver = SearchIndexResolver(provider._config)
        patcher = mock.patch.object(IndexConfiguration, "readConfig", return_value=configs)
        patcher.start()
        self.addCleanup(patcher.stop)
        provider._fileListCache = mock.MagicMock()
        provider._fileListCache.get.return_value = None
        provider._fileMatchesCache = mock.MagicMock()
        provider._commonKeywordMap = {}
        return provider

    def _conf(self, name: str, extensions: str = ".py",
              directories: str = "C:/src/proj",
              indexUpdateMode: IndexMode = IndexMode.TriggeredIndexUpdate,
              indexType: IndexType = IndexType.FileContentAndName) -> IndexConfiguration.IndexConfiguration:
        return IndexConfiguration.IndexConfiguration(
            indexName=name, extensions=extensions, directories=directories,
            indexdb=f"C:/idx/{name}.idx", indexUpdateMode=indexUpdateMode,
            indexType=indexType, apiAccess=True)

    def _contentTimeout(self, provider: SearchProvider, **kwargs: Any) -> str:
        with mock.patch("ai_agent.SearchProvider.SearchMethods") as sm, \
                mock.patch("ai_agent.SearchProvider.TimeoutEvent") as te:
            sm.return_value.searchContent.return_value = ResultSet(matches=[])
            te.return_value.happened.return_value = True
            with self.assertRaises(TimeoutError) as ctx:
                provider.searchContent("foo", **kwargs)
        return str(ctx.exception)

    def _fileNameTimeout(self, provider: SearchProvider, query: str, **kwargs: Any) -> str:
        with mock.patch("ai_agent.SearchProvider.SearchMethods") as sm, \
                mock.patch("ai_agent.SearchProvider.TimeoutEvent") as te:
            sm.return_value.searchFileName.return_value = ResultSet(matches=[])
            te.return_value.happened.return_value = True
            with self.assertRaises(TimeoutError) as ctx:
                provider.searchFileName(query, **kwargs)
        return str(ctx.exception)

    # ── Content search ────────────────────────────────────────────────────

    def test_content_unindexedLocation(self) -> None:
        """No config covers the folder: suggest creating an index for it."""
        provider = self._provider([])
        message = self._contentTimeout(provider, folder="C:/other/proj")
        self.assertIn("Timeout while searching for content", message)
        self.assertIn("not indexed location", message)
        self.assertIn("C:/other/proj", message)

    def test_content_missingExtensions(self) -> None:
        """Indexed location but the extension filter is not covered: name the missing extensions."""
        provider = self._provider([self._conf("loc1", extensions=".py")])
        message = self._contentTimeout(provider, folder="C:/src/proj",
                                       extensionFilter="*.xml,*.py")
        self.assertIn("Timeout while searching for content", message)
        self.assertIn("extensions are not included", message)
        self.assertIn("'.xml'", message)
        self.assertNotIn("'.py'", message)

    def test_content_locationMissingExtensions(self) -> None:
        """Same extension hint when a location is named explicitly."""
        provider = self._provider([self._conf("loc1", extensions=".py")])
        message = self._contentTimeout(provider, location="loc1", extensionFilter="*.xml")
        self.assertIn("extensions are not included", message)
        self.assertIn("'.xml'", message)

    def test_content_unindexedConfig(self) -> None:
        """A covering config without an index is reported as not indexed."""
        provider = self._provider([self._conf("loc1", indexUpdateMode=IndexMode.NoIndexWanted)])
        message = self._contentTimeout(provider, folder="C:/src/proj")
        self.assertIn("not indexed location", message)
        self.assertIn("C:/src/proj", message)

    # ── File name search ──────────────────────────────────────────────────

    def test_fileName_unindexedLocation(self) -> None:
        """No config covers the folder for a file name search."""
        provider = self._provider([])
        message = self._fileNameTimeout(provider, "*.py", folder="C:/other/proj")
        self.assertIn("Timeout while searching for files", message)
        self.assertIn("not indexed location", message)
        self.assertIn("C:/other/proj", message)

    def test_fileName_missingExtensions(self) -> None:
        """Indexed location but the query extension is not covered."""
        provider = self._provider([self._conf("loc1", extensions=".py")])
        message = self._fileNameTimeout(provider, "*.xml", location="loc1")
        self.assertIn("Timeout while searching for files", message)
        self.assertIn("extensions are not included", message)
        self.assertIn("'.xml'", message)
