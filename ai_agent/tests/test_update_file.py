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

Tests for the updateFile functionality: IndexUpdater.updateFile,
SearchProvider.updateFile, and the HTTP API endpoint.
"""

import os
import sqlite3
import tempfile
import unittest
from typing import cast
from unittest import mock

from ..Server import HttpError, _correctPathSeparator
from ..SearchProvider import SearchProvider
from ..TtlCache import TTLCache
from fulltextindex.IndexUpdater import IndexUpdater, UpdateStatistics
from fulltextindex.IndexConfiguration import IndexConfiguration, IndexMode, IndexType


class TestIndexUpdaterUpdateFile(unittest.TestCase):
    """Tests for IndexUpdater.updateFile()."""

    def setUp(self) -> None:
        self.tmpDir = tempfile.mkdtemp()
        self.dbPath = os.path.join(self.tmpDir, "test_index.db")
        self.filePath = os.path.join(self.tmpDir, "test_file.py")
        # Create a test file
        with open(self.filePath, "w", encoding="utf-8") as f:
            f.write("def hello():\n    print('world')\n")

    def tearDown(self) -> None:
        # Clean up temp files
        for f in [self.filePath, self.dbPath]:
            try:
                if os.path.isfile(f):
                    os.unlink(f)
            except OSError:
                pass
        try:
            os.rmdir(self.tmpDir)
        except OSError:
            pass

    def _makeConfig(self, indexType: IndexType = IndexType.FileContentAndName) -> IndexConfiguration:
        return IndexConfiguration(
            indexName="test_index",
            extensions=".py",
            directories=self.tmpDir,
            indexdb=self.dbPath,
            indexUpdateMode=IndexMode.TriggeredIndexUpdate,
            indexType=indexType
        )

    def test_updateFile_new_file(self) -> None:
        """A new file should be added to the index."""
        config = self._makeConfig()
        updater = IndexUpdater(self.dbPath)
        stats = UpdateStatistics()
        updater.updateFile(config, self.filePath, stats)
        self.assertEqual(stats.nNew, 1)
        self.assertEqual(stats.nUpdated, 0)
        self.assertEqual(stats.nUnchanged, 0)

        # Verify the document is in the database
        conn = sqlite3.connect(self.dbPath)
        try:
            cur = conn.cursor()
            cur.execute("SELECT fullpath FROM documents WHERE fullpath=?", (self.filePath,))
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], self.filePath)
        finally:
            conn.close()

    def test_updateFile_existing_file(self) -> None:
        """An existing file should be updated."""
        config = self._makeConfig()
        updater = IndexUpdater(self.dbPath)
        stats = UpdateStatistics()
        updater.updateFile(config, self.filePath, stats)
        self.assertEqual(stats.nNew, 1)

        # Update the file content
        with open(self.filePath, "w", encoding="utf-8") as f:
            f.write("def updated():\n    pass\n")

        stats2 = UpdateStatistics()
        updater.updateFile(config, self.filePath, stats2)
        self.assertEqual(stats2.nNew, 0)
        self.assertEqual(stats2.nUpdated, 1)

    def test_updateFile_unchanged_file(self) -> None:
        """An unchanged file should report unchanged."""
        config = self._makeConfig()
        updater = IndexUpdater(self.dbPath)
        stats = UpdateStatistics()
        updater.updateFile(config, self.filePath, stats)
        self.assertEqual(stats.nNew, 1)

        # Same content, no changes
        stats2 = UpdateStatistics()
        updater.updateFile(config, self.filePath, stats2)
        self.assertEqual(stats2.nNew, 0)
        self.assertEqual(stats2.nUpdated, 0)
        self.assertEqual(stats2.nUnchanged, 1)

    def test_updateFile_file_not_found(self) -> None:
        """A missing file should raise FileNotFoundError."""
        config = self._makeConfig()
        updater = IndexUpdater(self.dbPath)
        with self.assertRaises(FileNotFoundError):
            updater.updateFile(config, os.path.join(self.tmpDir, "nonexistent.py"))

    def test_updateFile_wrong_extension(self) -> None:
        """A file with an extension not in the config should raise ValueError."""
        config = self._makeConfig()
        # Create a .txt file
        txtPath = os.path.join(self.tmpDir, "test.txt")
        try:
            with open(txtPath, "w", encoding="utf-8") as f:
                f.write("test")
            updater = IndexUpdater(self.dbPath)
            with self.assertRaises(ValueError):
                updater.updateFile(config, txtPath)
        finally:
            try:
                os.unlink(txtPath)
            except OSError:
                pass

    def test_updateFile_content_indexing(self) -> None:
        """Verify that tokens are stored in the database."""
        config = self._makeConfig(IndexType.FileContent)
        updater = IndexUpdater(self.dbPath)
        updater.updateFile(config, self.filePath)

        # Verify tokens exist in keywords table
        conn = sqlite3.connect(self.dbPath)
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT k.keyword FROM keywords k
                JOIN kw2doc d ON k.id = d.kwID
                JOIN documents doc ON doc.id = d.docID
                WHERE doc.fullpath = ?
            """, (self.filePath,))
            keywords = [row[0] for row in cur.fetchall()]
            self.assertIn("hello", keywords)
            self.assertIn("print", keywords)
            self.assertIn("world", keywords)
        finally:
            conn.close()

    def test_updateFile_filename_indexing(self) -> None:
        """Verify that the file name is indexed."""
        config = self._makeConfig(IndexType.FileName)
        updater = IndexUpdater(self.dbPath)
        updater.updateFile(config, self.filePath)

        conn = sqlite3.connect(self.dbPath)
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT fn.name, fn.ext FROM fileName fn
                JOIN fileName2doc f2d ON fn.id = f2d.fileNameID
                JOIN documents doc ON doc.id = f2d.docID
                WHERE doc.fullpath = ?
            """, (self.filePath,))
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "test_file")
            self.assertEqual(row[1], ".py")
        finally:
            conn.close()


class TestSearchProviderUpdateFile(unittest.TestCase):
    """Tests for SearchProvider.updateFile()."""

    def setUp(self) -> None:
        self.tmpDir = tempfile.mkdtemp()
        self.dbPath = os.path.join(self.tmpDir, "test_provider.db")
        self.filePath = os.path.join(self.tmpDir, "test_provider.py")
        with open(self.filePath, "w", encoding="utf-8") as f:
            f.write("def provider_test():\n    pass\n")

        # Create a minimal config-like mock
        self.configPatcher = mock.patch("ai_agent.SearchProvider.appConfig")
        self.mockConfig = self.configPatcher.start()

        # Set up config mock to return something that looks like agent config
        configInstance = mock.MagicMock()
        configInstance.agent = mock.MagicMock()
        configInstance.agent.defaultExcludeDirs = ""
        configInstance.commonKeywords = ""

        self.mockConfig.return_value = configInstance

        # Mock IndexConfiguration.readConfig to return our test config
        self.readConfigPatcher = mock.patch("ai_agent.SearchProvider.IndexConfiguration.readConfig")
        self.mockReadConfig = self.readConfigPatcher.start()

        self.testConfig = IndexConfiguration(
            indexName="test_index",
            extensions=".py",
            directories=self.tmpDir,
            indexdb=self.dbPath,
            indexUpdateMode=IndexMode.TriggeredIndexUpdate,
            indexType=IndexType.FileContentAndName
        )
        self.mockReadConfig.return_value = [self.testConfig]

        # Create the provider
        self.provider = object.__new__(SearchProvider)
        self.provider._config = configInstance
        self.provider._commonKeywordMap = {}
        self.provider._fileListCache = TTLCache(60)
        self.provider._fileMatchesCache = TTLCache(60)
        self.provider._indexResolver = mock.MagicMock()

    def tearDown(self) -> None:
        self.configPatcher.stop()
        self.readConfigPatcher.stop()
        for f in [self.filePath, self.dbPath]:
            try:
                if os.path.isfile(f):
                    os.unlink(f)
            except OSError:
                pass
        try:
            os.rmdir(self.tmpDir)
        except OSError:
            pass

    def test_updateFile_success(self) -> None:
        """A valid file should be updated successfully."""
        result = self.provider.updateFile(self.filePath)
        self.assertTrue(result["updated"])
        self.assertEqual(result["file"], self.filePath)
        self.assertEqual(result["index"], "test_index")
        self.assertIn("detail", result)

    def test_updateFile_file_not_found(self) -> None:
        """A missing file should raise FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            self.provider.updateFile(os.path.join(self.tmpDir, "nonexistent.py"))

    def test_updateFile_no_matching_index(self) -> None:
        """A file not covered by any index should raise ValueError."""
        # Create a file outside the tmpDir
        otherDir = tempfile.mkdtemp()
        try:
            otherFile = os.path.join(otherDir, "other.py")
            with open(otherFile, "w", encoding="utf-8") as f:
                f.write("test")
            with self.assertRaises(ValueError):
                self.provider.updateFile(otherFile)
        finally:
            try:
                os.unlink(otherFile)
            except OSError:
                pass
            try:
                os.rmdir(otherDir)
            except OSError:
                pass


class TestIndexUpdateEndpoint(unittest.TestCase):
    """Tests for the HTTP API endpoint _handleIndexUpdate."""

    def setUp(self) -> None:
        self.tmpDir = tempfile.mkdtemp()
        self.dbPath = os.path.join(self.tmpDir, "test_endpoint.db")
        self.filePath = os.path.join(self.tmpDir, "test_endpoint.py")
        with open(self.filePath, "w", encoding="utf-8") as f:
            f.write("def endpoint_test():\n    pass\n")

    def tearDown(self) -> None:
        for f in [self.filePath, self.dbPath]:
            try:
                if os.path.isfile(f):
                    os.unlink(f)
            except OSError:
                pass
        try:
            os.rmdir(self.tmpDir)
        except OSError:
            pass

    def test_path_separator_correction(self) -> None:
        """Path separator correction should work for the file path."""
        if os.sep == '\\':
            result = _correctPathSeparator("C:/test/file.py")
            self.assertEqual(result, "C:\\test\\file.py")
        else:
            result = _correctPathSeparator("C:\\test\\file.py")
            self.assertEqual(result, "C:/test/file.py")

    def test_http_error(self) -> None:
        """HttpError should carry status code and message."""
        err = HttpError(400, "Bad request")
        self.assertEqual(err.statusCode, 400)
        self.assertEqual(err.message, "Bad request")


# Run tests if executed directly
if __name__ == "__main__":
    unittest.main()