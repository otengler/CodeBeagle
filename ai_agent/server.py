# -*- coding: utf-8 -*-
"""
Copyright (C) 2025 Oliver Tengler

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

import json
import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from typing import Any, Dict, List, Optional, Tuple, cast
from AppConfig import appConfig
from ai_agent.search_provider import (
    SearchProvider, ContentSearchResult, FileSearchResult, ContentMatch
)

__all__ = ['AgentServer', 'TTLCache']

logger = logging.getLogger(__name__)

class HttpError(Exception):
    """HTTP-level error with a status code and message."""
    def __init__(self, statusCode: int, message: str) -> None:
        super().__init__(message)
        self.statusCode = statusCode
        self.message = message

class TTLCache:
    """Simple thread-safe TTL cache mapping keys to values."""

    def __init__(self, ttlSeconds: int = 300) -> None:
        self._ttl = ttlSeconds
        self._data: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expiresAt, value = item
            if time.time() > expiresAt:
                del self._data[key]
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = (time.time() + self._ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

class AgentHTTPServer(ThreadingMixIn, HTTPServer):
    """HTTP server for the AI agent API with thread-per-request handling."""
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, serverAddress: Tuple[str, int], RequestHandlerClass: Any,
                 provider: SearchProvider, contextLines: int, defaultLimit: int,
                 cacheTTL: int = 300) -> None:
        super().__init__(serverAddress, RequestHandlerClass)
        self.provider = provider
        self.contextLines = contextLines
        self.defaultLimit = defaultLimit
        # File list cache: keyed by (query, indexConf.displayName(), folderFilter, extensionFilter, caseSensitive, excludeComments)
        self.fileListCache = TTLCache(cacheTTL)
        # File matches cache: keyed by (query, caseSensitive, excludeComments, filePath)
        self.fileMatchesCache = TTLCache(cacheTTL)

class AgentRequestHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests for the AI agent API."""

    server: AgentHTTPServer

    # Silence per-request log output
    def log_message(self, format: str, *args: Any) -> None:  # pylint: disable=redefined-builtin
        logger.debug("HTTP %s %s", self.command, self.path)

    # ---- GET endpoints ----

    def do_GET(self) -> None:
        path = self.path.split("?")[0].rstrip("/")
        try:
            if path == "" or path == "/":
                self._serveApiDoc()
            elif path in ("/api/v1/health", "/health"):
                self._sendJson(200, {"status": "ok"})
            elif path in ("/api/v1/locations", "/locations"):
                self._handleLocations()
            else:
                self._sendError(404, f"Unknown endpoint: {path}")
        except HttpError as e:
            self._sendError(e.statusCode, e.message)
        except Exception as e:
            logger.exception("GET %s failed", path)
            self._sendError(500, str(e))

    # ---- POST endpoints ----

    def do_POST(self) -> None:
        path = self.path.split("?")[0].rstrip("/")
        try:
            if path in ("/api/v1/search/content", "/search/content"):
                self._handleContentSearch()
            elif path in ("/api/v1/search/filename", "/search/filename"):
                self._handleFileNameSearch()
            else:
                self._sendError(404, f"Unknown endpoint: {path}")
        except HttpError as e:
            self._sendError(e.statusCode, e.message)
        except Exception as e:
            logger.exception("POST %s failed", path)
            self._sendError(500, str(e))

    # ---- OPTIONS for CORS preflight ----

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._sendCorsHeaders()
        self.end_headers()

    # ---- Internal helpers ----

    def _sendJson(self, statusCode: int, data: object) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(statusCode)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._sendCorsHeaders()
        self.end_headers()
        self.wfile.write(body)

    def _sendError(self, statusCode: int, message: str) -> None:
        self._sendJson(statusCode, {"error": message})

    def _sendCorsHeaders(self) -> None:
        """Add CORS headers if configured via agent.allowOrigin."""
        allowOrigin = str(self._agentConfig().allowOrigin)
        if allowOrigin:
            self.send_header("Access-Control-Allow-Origin", allowOrigin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _agentConfig(self) -> Any:
        return appConfig().agent

    def _readJsonBody(self) -> Dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            raise HttpError(400, "Invalid Content-Length header")
        if length <= 0:
            raise HttpError(400, "Request body must not be empty")
        try:
            raw = self.rfile.read(length)
        except Exception:
            raise HttpError(400, "Failed to read request body")
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            raise HttpError(400, "Invalid JSON in request body")
        if not isinstance(data, dict):
            raise HttpError(400, "JSON request body must be an object")
        return data

    def _getString(self, data: Dict[str, Any], key: str,
                   default: str = "") -> str:
        value = data.get(key, default)
        if value is None:
            value = default
        if not isinstance(value, str):
            raise HttpError(400, f"Field '{key}' must be a string")
        return value

    def _getOptionalString(self, data: Dict[str, Any],
                           key: str) -> Optional[str]:
        value = data.get(key)
        if value is None:
            return None
        if not isinstance(value, str):
            raise HttpError(400, f"Field '{key}' must be a string")
        return value

    def _getBool(self, data: Dict[str, Any], key: str,
                 default: bool = False) -> bool:
        value = data.get(key, default)
        if not isinstance(value, bool):
            raise HttpError(400, f"Field '{key}' must be a boolean")
        return value

    def _getInt(self, data: Dict[str, Any], key: str,
                default: int) -> int:
        value = data.get(key, default)
        if isinstance(value, bool):
            raise HttpError(400, f"Field '{key}' must be an integer")
        if isinstance(value, int):
            return value
        raise HttpError(400, f"Field '{key}' must be an integer")

    def _getPageOffset(self, data: Dict[str, Any]) -> Optional[Dict[str, int]]:
        value = data.get("pageOffset")
        if value is None:
            return None
        if not isinstance(value, dict):
            raise HttpError(400, "Field 'pageOffset' must be an object")
        result: Dict[str, int] = {}
        for key in ("fileIndex", "matchIndex"):
            v = value.get(key)
            if v is not None:
                if isinstance(v, bool) or not isinstance(v, int):
                    raise HttpError(400, f"Field 'pageOffset.{key}' must be an integer")
                result[key] = v
        if "fileIndex" not in result:
            raise HttpError(400, "Field 'pageOffset.fileIndex' is required")
        return result

    # ---- Endpoint handlers ----

    def _serveApiDoc(self) -> None:
        """Serve the API documentation markdown file at the root URL."""
        docPath = os.path.join(os.path.dirname(__file__), "API.md")
        try:
            with open(docPath, "r", encoding="utf-8") as f:
                content = f.read()
            body = content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/markdown; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._sendCorsHeaders()
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self._sendError(500, "API documentation file not found")
        except Exception as e:
            logger.exception("Failed to serve API doc")
            self._sendError(500, str(e))

    def _handleLocations(self) -> None:
        locations = self.server.provider.getLocations()
        data = {
            "locations": [
                {
                    "name": loc.name,
                    "folders": loc.folders,
                    "extensions": loc.extensions,
                    "indexMode": loc.indexMode,
                }
                for loc in locations
            ]
        }
        self._sendJson(200, data)

    def _handleContentSearch(self) -> None:
        data = self._readJsonBody()
        location = self._getOptionalString(data, "location")
        folder = self._getOptionalString(data, "folder")
        query = self._getString(data, "query")
        if not query:
            raise HttpError(400, "Field 'query' must not be empty")
        folderFilter = self._getString(data, "folderFilter", "")
        extensionFilter = self._getString(data, "extensionFilter", "")
        caseSensitive = self._getBool(data, "caseSensitive", False)
        contextLines = self._getInt(data, "contextLines", self.server.contextLines)
        limit = self._getInt(data, "limit", self.server.defaultLimit)
        pageOffset = self._getPageOffset(data)

        if limit < 1:
            limit = self.server.defaultLimit

        try:
            result = self.server.provider.searchContent(
                query, location=location, folder=folder,
                folderFilter=folderFilter, extensionFilter=extensionFilter,
                caseSensitive=caseSensitive,
                contextLines=contextLines, limit=limit, pageOffset=pageOffset
            )
        except ValueError as e:
            raise HttpError(404, str(e))
        self._sendJson(200, _contentResultToJson(result))

    def _handleFileNameSearch(self) -> None:
        data = self._readJsonBody()
        location = self._getOptionalString(data, "location")
        folder = self._getOptionalString(data, "folder")
        query = self._getString(data, "query")
        if not query:
            raise HttpError(400, "Field 'query' must not be empty")
        folderFilter = self._getString(data, "folderFilter", "")
        extensionFilter = self._getString(data, "extensionFilter", "")
        caseSensitive = self._getBool(data, "caseSensitive", False)
        limit = self._getInt(data, "limit", self.server.defaultLimit)
        pageOffset = self._getPageOffset(data)

        if limit < 1:
            limit = self.server.defaultLimit

        try:
            result = self.server.provider.searchFileName(
                query, location=location, folder=folder,
                folderFilter=folderFilter, extensionFilter=extensionFilter,
                caseSensitive=caseSensitive, limit=limit, pageOffset=pageOffset
            )
        except ValueError as e:
            raise HttpError(404, str(e))
        self._sendJson(200, _fileNameResultToJson(result))

def _contentResultToJson(result: ContentSearchResult) -> Dict[str, object]:
    matches: List[Dict[str, object]] = []
    for m in result.matches:
        matches.append({
            "file": m.file,
            "line": m.line,
            "column": m.column,
            "matchText": m.matchText,
            "contextBefore": m.contextBefore,
            "contextAfter": m.contextAfter,
            "fullLine": m.fullLine,
        })
    jsonResult: Dict[str, object] = {
        "totalFiles": result.totalFiles,
        "matches": matches,
    }
    if result.pageOffset is not None:
        jsonResult["pageOffset"] = result.pageOffset
    return jsonResult

def _fileNameResultToJson(result: FileSearchResult) -> Dict[str, object]:
    jsonResult: Dict[str, object] = {
        "totalFiles": result.totalFiles,
        "files": result.files,
    }
    if result.pageOffset is not None:
        jsonResult["pageOffset"] = result.pageOffset
    return jsonResult

class AgentServer:
    """
    Wraps the AgentHTTPServer and manages its lifecycle.

    Reads configuration from the agent section of config.txt.
    """

    def __init__(self, provider: Optional[SearchProvider] = None) -> None:
        self.config = appConfig().agent
        self.provider = provider or SearchProvider()
        self.httpd: Optional[AgentHTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    @property
    def enabled(self) -> bool:
        return bool(self.config.enabled)

    def start(self) -> bool:
        """
        Start the server in a background daemon thread.

        Returns True if the server was started successfully, False otherwise.
        """
        if not self.enabled:
            logger.info("AI agent server is disabled in config")
            return False

        bind = str(self.config.bind)
        try:
            port = int(self.config.port)
        except (ValueError, TypeError):
            logger.error("Invalid port in config: %s", self.config.port)
            return False

        try:
            contextLines = int(self.config.contextLines)
        except (ValueError, TypeError):
            contextLines = 2
        try:
            defaultLimit = int(self.config.defaultLimit)
        except (ValueError, TypeError):
            defaultLimit = 100

        try:
            self.httpd = AgentHTTPServer(
                (bind, port), AgentRequestHandler,
                self.provider, contextLines, defaultLimit
            )
        except OSError as e:
            logger.error("Failed to start AI agent server on %s:%d: %s", bind, port, e)
            return False

        self.thread = threading.Thread(
            target=self.httpd.serve_forever,
            name="AgentServer",
            daemon=True
        )
        self.thread.start()
        logger.info("AI agent server started at http://%s:%d", bind, port)
        return True

    def stop(self) -> None:
        """Shut down the server gracefully."""
        if self.httpd:
            logger.info("Shutting down AI agent server...")
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
            self.thread = None