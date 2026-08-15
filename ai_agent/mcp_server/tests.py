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

import asyncio
import email.message
import io
import os
import sys
import types as pytypes
import unittest
import urllib.error
from typing import Any, Dict, Optional, cast
from unittest import mock

import mcp_types as types

from .client import ApiError, CodeBeagleClient, ServerUnreachable
from .config import DEFAULT_BASE_URL, resolveBaseUrl
from .server import CodeBeagleMCPServer
from .types import ContentSearchInput, FileNameSearchInput

class _FakeResponse:
    """Minimal stand-in for urllib response objects."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: Any) -> None:
        return None

def _fakeAgentConfig(enabled: bool) -> Any:
    """Build a fake AppConfig module whose agent section has the given state."""

    class FakeAgent:
        def __init__(self) -> None:
            self.enabled = enabled
            self.bind = "127.0.0.1"
            self.port = 8080

    class FakeAppConfig:
        def appConfig(self) -> Any:
            class Cfg:
                agent = FakeAgent()
            return Cfg()

    module = pytypes.ModuleType("AppConfig")
    module.appConfig = FakeAppConfig().appConfig  # type: ignore[attr-defined]
    return module

class TestConfigResolution(unittest.TestCase):
    def test_envVarWins(self) -> None:
        with mock.patch.dict(os.environ, {"CODEBEAGLE_API_URL": "http://example:1234"}, clear=True), \
             mock.patch("os.path.isfile", return_value=False):
            self.assertEqual(resolveBaseUrl(), "http://example:1234")

    def test_envVarWinsOverConfigFile(self) -> None:
        with mock.patch.dict(os.environ, {"CODEBEAGLE_API_URL": "http://example:1234"}, clear=True), \
             mock.patch("os.path.isfile", return_value=True), \
             mock.patch("ai_agent.mcp_server.config._readJsonFile",
                        return_value={"baseUrl": "http://json-host:4321"}):
            self.assertEqual(resolveBaseUrl(), "http://example:1234")

    def test_configFileUsedWithoutEnvVar(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch("os.path.isfile", return_value=True), \
             mock.patch("ai_agent.mcp_server.config._readJsonFile",
                        return_value={"baseUrl": "http://json-host:4321"}):
            self.assertEqual(resolveBaseUrl(), "http://json-host:4321")

    def test_appConfigWhenEnabled(self) -> None:
        fake = _fakeAgentConfig(enabled=True)
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch("os.path.isfile", return_value=False), \
             mock.patch.dict(sys.modules, {"AppConfig": fake}):
            self.assertEqual(resolveBaseUrl(), "http://127.0.0.1:8080")

    def test_defaultWhenDisabled(self) -> None:
        fake = _fakeAgentConfig(enabled=False)
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch("os.path.isfile", return_value=False), \
             mock.patch.dict(sys.modules, {"AppConfig": fake}):
            self.assertEqual(resolveBaseUrl(), DEFAULT_BASE_URL)

    def test_defaultOnConfigError(self) -> None:
        # A broken AppConfig import must not crash the resolver.
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch("os.path.isfile", return_value=False), \
             mock.patch.dict(sys.modules, {"AppConfig": None}):
            self.assertEqual(resolveBaseUrl(), DEFAULT_BASE_URL)

    def test_trailingSlashStripped(self) -> None:
        with mock.patch.dict(os.environ, {"CODEBEAGLE_API_URL": "http://example:1234//"}, clear=True):
            self.assertEqual(resolveBaseUrl(), "http://example:1234")

class TestCodeBeagleClient(unittest.TestCase):
    def setUp(self) -> None:
        self.client = CodeBeagleClient("http://127.0.0.1:8080")

    def test_get(self) -> None:
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(b'{"status": "ok"}')) as urlopen:
            result = self.client.health()
        self.assertEqual(result, {"status": "ok"})
        request = urlopen.call_args[0][0]
        self.assertEqual(request.get_full_url(), "http://127.0.0.1:8080/api/v1/health")
        self.assertEqual(request.get_method(), "GET")
        self.assertIsNone(request.data)

    def test_post(self) -> None:
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(b'{"totalFiles": 0, "matches": []}')) as urlopen:
            result = self.client.searchContent({"query": "target", "contextLines": 0})
        self.assertEqual(result["totalFiles"], 0)
        request = urlopen.call_args[0][0]
        self.assertEqual(request.get_full_url(), "http://127.0.0.1:8080/api/v1/search/content")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Content-type"), "application/json")
        import json
        self.assertEqual(json.loads(cast(bytes, request.data)), {"query": "target", "contextLines": 0})

    def test_trailingSlashInBaseUrl(self) -> None:
        client = CodeBeagleClient("http://127.0.0.1:8080/")
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(b'{}')) as urlopen:
            client.getLocations()
        request = urlopen.call_args[0][0]
        self.assertEqual(request.get_full_url(), "http://127.0.0.1:8080/api/v1/locations")

    def test_httpErrorRaisesApiError(self) -> None:
        headers = email.message.Message()
        error = urllib.error.HTTPError("http://x", 404, "Not Found", headers,
                                       io.BytesIO(b'{"error": "no such index"}'))
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(ApiError) as cm:
                self.client.searchFileName({"query": "*.py"})
        self.assertEqual(cm.exception.statusCode, 404)
        self.assertEqual(cm.exception.message, "no such index")

    def test_httpErrorWithoutJsonBody(self) -> None:
        headers = email.message.Message()
        error = urllib.error.HTTPError("http://x", 500, "boom", headers, io.BytesIO(b"plain text"))
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(ApiError) as cm:
                self.client.searchContent({"query": "x"})
        self.assertEqual(cm.exception.statusCode, 500)
        self.assertNotEqual(cm.exception.message, "")

    def test_connectionRefusedRaisesServerUnreachable(self) -> None:
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
            with self.assertRaises(ServerUnreachable):
                self.client.getLocations()

    def test_invalidJsonResponse(self) -> None:
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(b"not json")):
            with self.assertRaises(ApiError):
                self.client.getLocations()

class TestInputTypes(unittest.TestCase):
    def test_contentSearchToHttpParams(self) -> None:
        params = ContentSearchInput(
            query="target",
            folder="C:/src/proj",
            context_lines=3,
            case_sensitive=True,
            limit=5,
        ).toHttpParams()
        self.assertEqual(params, {
            "query": "target",
            "folder": "C:/src/proj",
            "caseSensitive": True,
            "excludeComments": True,
            "contextLines": 3,
            "limit": 5,
        })
        # None values must not be sent to the HTTP API.
        self.assertNotIn("location", params)
        self.assertNotIn("folderFilter", params)
        self.assertNotIn("extensionFilter", params)

    def test_compactContentSearchForcesNoContext(self) -> None:
        params = ContentSearchInput(query="target", context_lines=5, format="compact").toHttpParams()
        self.assertEqual(params["contextLines"], 0)
        self.assertNotIn("format", params)

    def test_jsonContentSearchKeepsContext(self) -> None:
        params = ContentSearchInput(query="target", context_lines=5, format="json").toHttpParams()
        self.assertEqual(params["contextLines"], 5)
        self.assertNotIn("format", params)

    def test_fileNameSearchToHttpParams(self) -> None:
        params = FileNameSearchInput(query="*.py").toHttpParams()
        self.assertEqual(params, {"query": "*.py", "caseSensitive": False, "limit": 100})

    def test_limitBounds(self) -> None:
        with self.assertRaises(Exception):
            ContentSearchInput(query="x", limit=0)
        with self.assertRaises(Exception):
            ContentSearchInput(query="x", limit=10001)
        with self.assertRaises(Exception):
            ContentSearchInput(query="x", context_lines=21)

class TestMCPServer(unittest.TestCase):
    def setUp(self) -> None:
        self.mcp = CodeBeagleMCPServer("http://127.0.0.1:8080")
        self.client = mock.MagicMock()
        self.mcp.client = self.client

    def _call(self, name: str, arguments: Optional[Dict[str, Any]]) -> types.CallToolResult:
        params = types.CallToolRequestParams(name=name, arguments=arguments)
        return asyncio.run(self.mcp._handleCallTool(None, params))

    def _text(self, result: types.CallToolResult) -> str:
        return cast(types.TextContent, result.content[0]).text

    def test_toolList(self) -> None:
        result = asyncio.run(self.mcp._handleListTools(None, None))
        names = [t.name for t in result.tools]
        self.assertEqual(names, ["list_locations", "search_content", "search_filename"])
        schemas = {t.name: t.input_schema for t in result.tools}
        self.assertIn("query", schemas["search_content"]["required"])
        self.assertIn("query", schemas["search_filename"]["required"])
        self.assertEqual(schemas["list_locations"]["properties"], {})
        for tool in result.tools:
            self.assertTrue(tool.description)

    def test_listLocations(self) -> None:
        self.client.getLocations.return_value = {
            "locations": [{
                "name": "loc1",
                "folders": ["C:/src/proj"],
                "extensions": [".py"],
                "indexMode": "filenameAndContent",
            }]
        }
        result = self._call("list_locations", {})
        self.assertFalse(result.is_error)
        self.assertIn("loc1", self._text(result))

    def test_searchContentTranslatesParams(self) -> None:
        self.client.searchContent.return_value = {"totalFiles": 1, "matches": [
            {"file": "C:/src/proj/a.py", "line": 3, "fullLine": "def target():", "matchText": "target"}
        ]}
        result = self._call("search_content", {
            "query": "target", "folder": "C:/src/proj", "context_lines": 3, "limit": 5,
        })
        self.assertFalse(result.is_error)
        self.client.searchContent.assert_called_once_with({
            "query": "target",
            "folder": "C:/src/proj",
            "caseSensitive": False,
            "excludeComments": True,
            "contextLines": 3,
            "limit": 5,
        })
        self.assertIn("C:/src/proj/a.py", self._text(result))

    def test_searchContentCompact(self) -> None:
        self.client.searchContent.return_value = {"totalFiles": 2, "matches": [
            {"file": "C:/src/proj/a.py", "line": 3, "fullLine": "def target():"},
            {"file": "C:/src/proj/b.py", "line": 7, "fullLine": "target = 1"},
        ]}
        result = self._call("search_content", {"query": "target", "context_lines": 5, "format": "compact"})
        self.assertFalse(result.is_error)
        # Compact mode must not request context lines from the HTTP API.
        self.client.searchContent.assert_called_once_with({
            "query": "target", "excludeComments": True, "contextLines": 0,
            "caseSensitive": False, "limit": 100,
        })
        self.assertEqual(
            self._text(result),
            "C:/src/proj/a.py:3: def target():\nC:/src/proj/b.py:7: target = 1",
        )

    def test_searchContentCompactEmpty(self) -> None:
        self.client.searchContent.return_value = {"totalFiles": 0, "matches": []}
        result = self._call("search_content", {"query": "zzz", "format": "compact"})
        self.assertFalse(result.is_error)
        self.assertEqual(self._text(result), "")

    def test_searchFileNameCompact(self) -> None:
        self.client.searchFileName.return_value = {"totalFiles": 2, "files": ["a.py", "b.py"]}
        result = self._call("search_filename", {"query": "*.py", "format": "compact"})
        self.assertFalse(result.is_error)
        self.assertEqual(self._text(result), "a.py\nb.py")

    def test_invalidFormatRejected(self) -> None:
        result = self._call("search_content", {"query": "x", "format": "yaml"})
        self.assertTrue(result.is_error)
        self.assertIn("format", self._text(result))
        self.client.searchContent.assert_not_called()

    def test_searchContentValidationError(self) -> None:
        result = self._call("search_content", {"context_lines": 50})
        self.assertTrue(result.is_error)
        self.assertIn("query", self._text(result))
        self.client.searchContent.assert_not_called()

    def test_searchContentValidationErrorOnType(self) -> None:
        result = self._call("search_content", {"query": 42})
        self.assertTrue(result.is_error)
        self.client.searchContent.assert_not_called()

    def test_searchFileName(self) -> None:
        self.client.searchFileName.return_value = {"totalFiles": 2, "files": ["a.py", "b.py"]}
        result = self._call("search_filename", {"query": "*.py", "case_sensitive": True})
        self.assertFalse(result.is_error)
        self.client.searchFileName.assert_called_once_with({
            "query": "*.py", "caseSensitive": True, "limit": 100,
        })
        self.assertIn("a.py", self._text(result))

    def test_unknownTool(self) -> None:
        result = self._call("nope", {})
        self.assertTrue(result.is_error)
        self.assertIn("Unknown tool", self._text(result))

    def test_http404MapsToGuidance(self) -> None:
        self.client.searchContent.side_effect = ApiError(404, "No index covers C:/src/other")
        result = self._call("search_content", {"query": "x", "folder": "C:/src/other"})
        self.assertTrue(result.is_error)
        text = self._text(result)
        self.assertIn("not indexed", text)
        self.assertIn("list_locations", text)

    def test_http400MapsToInvalidParams(self) -> None:
        self.client.searchContent.side_effect = ApiError(400, "Field 'query' must not be empty")
        result = self._call("search_content", {"query": ""})
        self.assertTrue(result.is_error)
        self.assertIn("Invalid parameters", self._text(result))

    def test_serverUnreachableMapsToGuidance(self) -> None:
        self.client.searchContent.side_effect = ServerUnreachable("http://127.0.0.1:8080", "refused")
        result = self._call("search_content", {"query": "x"})
        self.assertTrue(result.is_error)
        text = self._text(result)
        self.assertIn("not reachable", text)
        self.assertIn("CodeBeagleAgentServer", text)

    def test_internalError(self) -> None:
        self.client.searchContent.side_effect = RuntimeError("boom")
        result = self._call("search_content", {"query": "x"})
        self.assertTrue(result.is_error)
        self.assertIn("Internal error", self._text(result))

if __name__ == "__main__":
    unittest.main()
