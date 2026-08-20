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

Tests for SearchIndexResolver.resolve and checkExtensionFilter.
"""

import unittest
from typing import List
from unittest import mock
from ..SearchProvider import SearchProvider
from ..SearchIndexResolver import SearchIndexResolver
from ..TtlCache import TTLCache
from fulltextindex import IndexConfiguration
from fulltextindex.IndexConfiguration import IndexMode, IndexType
from fulltextindex.SearchMethods import ResultSet


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

    def test_folderInSubdirectory(self) -> None:
        conf = self._conf("loc1", "C:/src/proj")
        provider = self._provider([conf])
        self.assertEqual(provider._indexResolver.resolve(folder="C:/src/proj/sub/dir"), conf)

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

    def test_excludedConfigSkippedInFavorOfCoveringConfig(self) -> None:
        excluded = self._conf("excluded", "C:/src/proj", dirExcludes="C:/src/proj/build")
        covering = self._conf("covering", "C:/src/proj")
        provider = self._provider([excluded, covering])
        self.assertEqual(provider._indexResolver.resolve(folder="C:/src/proj/build"), covering)

    def test_noConfigsAndNoFolder_raises(self) -> None:
        """When there are no index configs and no folder, we can't search."""
        provider = self._provider([])
        with self.assertRaises(ValueError):
            provider._indexResolver.resolve()

    def test_noIndexFallbackInContentSearch(self) -> None:
        """searchContent with an uncovered folder uses direct search (no error for unmatched extension)."""
        conf = self._confWithExtensions("loc1", ".py")
        provider = self._provider([conf])
        provider._fileListCache = mock.MagicMock()
        provider._fileListCache.get.return_value = None
        provider._commonKeywordMap = {}
        with mock.patch("ai_agent.SearchProvider.SearchMethods") as sm:
            sm.return_value.searchContent.return_value = ResultSet(matches=[])
            # Uncovered folder + unmatched extension should NOT raise because
            # we fall back to non-indexed search which skips extension filter validation
            result = provider.searchContent("foo", folder="C:/other/proj", extensionFilter="*.java")
            self.assertIsNotNone(result)

    def test_noIndexFallbackInFileNameSearch(self) -> None:
        """searchFileName with an uncovered folder uses direct search (no error for unmatched extension)."""
        conf = self._confWithExtensions("loc1", ".py")
        provider = self._provider([conf])
        provider._fileListCache = mock.MagicMock()
        provider._fileListCache.get.return_value = None
        with mock.patch("ai_agent.SearchProvider.SearchMethods") as sm:
            sm.return_value.searchFileName.return_value = ResultSet(matches=[])
            # Uncovered folder + unmatched extension should NOT raise
            result = provider.searchFileName("*.py", folder="C:/other/proj")
            self.assertIsNotNone(result)

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
            # *.java is not covered by the .py config, so checkExtensionFilter raises
            with self.assertRaises(ValueError):
                provider.searchContent("foo", location="loc1", extensionFilter="*.java")
            # Using location="loc1" matches the config, so extension filter is checked
            provider.searchContent("foo", location="loc1", extensionFilter="*.py")

    def test_extensionCheckRunsInFileNameSearch(self) -> None:
        conf = self._confWithExtensions("loc1", ".py")
        provider = self._provider([conf])
        provider._fileListCache = mock.MagicMock()
        provider._fileListCache.get.return_value = None
        with mock.patch("ai_agent.SearchProvider.SearchMethods") as sm:
            sm.return_value.searchFileName.return_value = ResultSet(matches=[])
            # Using location="loc1" matches the config, so extension filter is checked
            # "*.py" filter is covered by the .py config, so no ValueError should be raised
            provider.searchFileName("*.py", location="loc1")
            # An unmatched extension should raise
            with self.assertRaises(ValueError):
                provider.searchFileName("*.java", location="loc1")