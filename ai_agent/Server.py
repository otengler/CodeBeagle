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

import json
import logging
import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import parse_qsl
from AppConfig import appConfig
from .AgentHistory import AgentHistory, HistoryEntry, formatBodyParams
from .SearchProvider import SearchProvider, ContentSearchResult, FileSearchResult
from .TtlCache import TTLCache
from .ToolDescription import tool_desc

logger = logging.getLogger(__name__)

class HttpError(Exception):
    """HTTP-level error with a status code and message."""
    def __init__(self, statusCode: int, message: str) -> None:
        super().__init__(message)
        self.statusCode = statusCode
        self.message = message
        
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
        # History of API calls (thread-safe, capped at 500 entries)
        self.history = AgentHistory()
        # File list cache: keyed by (query, indexConf.displayName(), pathFilter, extensionFilter, caseSensitive, excludeComments)
        self.fileListCache = TTLCache(cacheTTL)
        # File matches cache: keyed by (query, caseSensitive, excludeComments, filePath)
        self.fileMatchesCache = TTLCache(cacheTTL)

class AgentRequestHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests for the AI agent API."""

    server: AgentHTTPServer

    def __init__(self, request: socket.socket, clientAddress: Tuple[str, int],
                 server: "AgentHTTPServer") -> None:
        self._statusCode = 200
        self._lastBody: Optional[Dict[str, Any]] = None
        self._lastResult: str = ""
        self._currentEntry: Optional[HistoryEntry] = None
        self._bodyReadAttempted: bool = False
        self._bodyParseError: HttpError
        super().__init__(request, clientAddress, server)

    # Silence per-request log output
    def log_message(self, format: str, *args: Any) -> None:  # pylint: disable=redefined-builtin
        logger.debug("HTTP %s %s", self.command, self.path)

    # ---- GET endpoints ----

    def do_GET(self) -> None:
        path = self.path.split("?")[0].rstrip("/")
        try:
            # Create a "Running" history entry immediately when the request
            # is received (except for the history endpoint itself and requests
            # flagged with excludeFromHistory, e.g. the startup health probe).
            if _shouldRecordHistory(self.path, path):
                self._currentEntry = self._createRunningEntry()

            if path == "" or path == "/":
                self._serveApiDoc()
            elif path in ("/api/v1/docs", "/docs"):
                self._serveApiDoc()
            elif path in ("/api/v1/pi-extension", "/pi-extension"):
                self._servePiExtension()
            elif path in ("/api/v1/health", "/health"):
                self._sendJson(200, {"status": "ok"})
            elif path in ("/api/v1/history", "/history"):
                self._handleHistory()
            elif path in ("/api/v1/locations", "/locations"):
                self._handleLocations()
            else:
                self._sendError(404, f"Unknown endpoint: {path}")
        except HttpError as e:
            self._sendError(e.statusCode, e.message)
        except Exception as e:
            logger.exception("GET %s failed", path)
            self._sendError(500, str(e))
        finally:
            if self._currentEntry is not None:
                self._currentEntry.finish(self._statusCode, self._lastResult)

    # ---- POST endpoints ----

    def do_POST(self) -> None:
        path = self.path.split("?")[0].rstrip("/")
        try:
            # Pre-read the request body now so that the params are available
            # in the history entry from the very start.
            try:
                self._readJsonBody()
            except HttpError:
                pass  # Will surface again from the endpoint handler below

            if _shouldRecordHistory(self.path, path):
                self._currentEntry = self._createRunningEntry()

            if path in ("/api/v1/search/content", "/search/content"):
                self._handleContentSearch()
            elif path in ("/api/v1/search/filename", "/search/filename"):
                self._handleFileNameSearch()
            elif path in ("/api/v1/index/update", "/index/update"):
                self._handleIndexUpdate()
            else:
                self._sendError(404, f"Unknown endpoint: {path}")
        except HttpError as e:
            self._sendError(e.statusCode, e.message)
        except Exception as e:
            logger.exception("POST %s failed", path)
            self._sendError(500, str(e))
        finally:
            if self._currentEntry is not None:
                self._currentEntry.finish(self._statusCode, self._lastResult)

    # ---- OPTIONS for CORS preflight ----

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._sendCorsHeaders()
        self.end_headers()

    # ---- Internal helpers ----

    def _sendJson(self, statusCode: int, data: object) -> None:
        self._statusCode = statusCode
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

    def _createRunningEntry(self) -> HistoryEntry:
        """Create a "Running" history entry for the current request and add it
        to the shared history immediately. The entry will be updated by
        finish() when the request completes.

        Parameters are populated straight away so they are visible in the
        history from the moment the request is received.
        """
        path = self.path.split("?")[0]
        if path != "/":
            path = path.rstrip("/")
        # Params available immediately for GET (query string) and for POST
        # (the body was pre-read in do_POST before this method is called).
        if self.command == "POST" and self._lastBody:
            params = formatBodyParams(self._lastBody)
        else:
            params = self._formatQueryParams()
        entry = HistoryEntry(
            timestamp=time.time(),
            method=str(self.command),
            path=path,
            params=params,
            result="Running",
            isRunning=True
        )
        self.server.history.add(entry)
        return entry

    def _formatQueryParams(self) -> str:
        """Format the query string of the request into a human-readable string."""
        query = self.path.split("?", 1)[1] if "?" in self.path else ""
        if not query:
            return ""
        parts = [f"{key}: '{value}'" for key, value in parse_qsl(query)]
        return ", ".join(parts)

    def _agentConfig(self) -> Any:
        return appConfig().agent

    def _readJsonBody(self) -> Dict[str, Any]:
        if self._lastBody is not None:
            return self._lastBody
        if self._bodyReadAttempted:
            raise self._bodyParseError
        self._bodyReadAttempted = True
        try:
            length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            self._bodyParseError = HttpError(400, "Invalid Content-Length header")
            raise self._bodyParseError
        if length <= 0:
            self._bodyParseError = HttpError(400, "Request body must not be empty")
            raise self._bodyParseError
        try:
            raw = self.rfile.read(length)
        except Exception:
            self._bodyParseError = HttpError(400, "Failed to read request body")
            raise self._bodyParseError
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            self._bodyParseError = HttpError(400, "Invalid JSON in request body")
            raise self._bodyParseError
        if not isinstance(data, dict):
            self._bodyParseError = HttpError(400, "JSON request body must be an object")
            raise self._bodyParseError
        self._lastBody = data
        return data

    def _getStringOrList(self, data: Dict[str, Any], key: str) -> Union[str,List[str]]:
        value = data.get(key)
        if value is None:
            raise HttpError(400, f"Field '{key}' is mandatory")    
        if isinstance(value, str):
            if not value:
                raise HttpError(400, f"Field '{key}' must not be empty")
            return value
        if isinstance(value, list):
            if not value or any(not q for q in value):
                raise HttpError(400, f"Field '{key}' must not be empty and must not contain empty strings")
            return value
        raise HttpError(400, f"Field '{key}' contains invalid data")        

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
        # Prefer the distribution copy under resources/ai_agent/, fall back to
        # the source tree location for development without a build.
        docPath = os.path.join("resources", "ai_agent", "API.md")
        if not os.path.isfile(docPath):
            docPath = os.path.join(os.path.dirname(__file__), "API.md")
        try:
            with open(docPath, "r", encoding="utf-8") as f:
                content = f.read()
            body = content.encode("utf-8")
            self._statusCode = 200
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

    def _servePiExtension(self) -> None:
        """Serve the PI extension TypeScript file for download.
        Replaces __TOOL_DESC_*__ markers with actual tool descriptions from tool_desc.json.
        """
        tool_names = ["codebeagle_content_search", "codebeagle_file_search", "codebeagle_list_indexes", "codebeagle_health", "codebeagle_update_file"]
        try:
            extensionPath = os.path.join("resources", "ai_agent", "pi", "extensions", "codebeagle.ts")
            with open(extensionPath, "r", encoding="utf-8") as f:
                content = f.read()

            for tool_name in tool_names:
                tool = tool_desc(tool_name)
                shortName = tool_name.replace("codebeagle_","").upper()
                content = content.replace(f"__TOOL_DESC_{shortName}__", tool.desc)
                content = content.replace(f"__PROMPT_SNIPPET_{shortName}__", tool.desc)
                content = content.replace(f"\"__PROMPT_GUIDELINES_{shortName}__\"", json.dumps(tool.promptGuidelines))
                for param_name, param_desc in tool.params.items():
                    content = content.replace(f"__PARAM_DESC_{shortName}_{param_name.upper()}__", param_desc)
                
            body = content.encode("utf-8")
            self._statusCode = 200
            self.send_response(200)
            self.send_header("Content-Type", "text/typescript; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Disposition", 'attachment; filename="codebeagle.ts"')
            self._sendCorsHeaders()
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self._sendError(404, f"Resource not found: {extensionPath}")
        except Exception as e:
            logger.exception("Failed to serve PI extension")
            self._sendError(500, str(e))

    def _serveResourceFile(self, relPath: str, contentType: str, downloadName: str) -> None:
        """
        Serve a static file from the application directory.

        Args:
            relPath: Path relative to the app directory.
            contentType: MIME type for the response.
            downloadName: Filename hint for the Content-Disposition header.
        """
        try:
            with open(relPath, "r", encoding="utf-8") as f:
                content = f.read()
            body = content.encode("utf-8")
            self._statusCode = 200
            self.send_response(200)
            self.send_header("Content-Type", f"{contentType}; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Disposition", f'attachment; filename="{downloadName}"')
            self._sendCorsHeaders()
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self._sendError(404, f"Resource not found: {relPath}")
        except Exception as e:
            logger.exception("Failed to serve resource %s", relPath)
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

    def _handleHistory(self) -> None:
        """Serve the API call history.

        Internal endpoint, intentionally NOT documented in API.md so that AI
        agents do not discover it. It is used by the AgentHistory dialog of a
        second CodeBeagle instance when the API server runs externally
        (CodeBeagleAgentServer.exe).
        """
        self._sendJson(200, _historyToJson(self.server.history))

    def _handleContentSearch(self) -> None:
        data = self._readJsonBody()
        location = self._getOptionalString(data, "location")
        folder = self._getOptionalString(data, "folder")
        if folder is not None:
            folder = _correctPathSeparator(folder)
        query =self._getStringOrList(data, "query")
        pathFilter = _correctPathSeparator(self._getString(data, "pathFilter", ""))
        extensionFilter = self._getString(data, "extensionFilter", "")
        caseSensitive = self._getBool(data, "caseSensitive", False)
        excludeComments = self._getBool(data, "excludeComments", True)
        contextLines = self._getInt(data, "contextLines", self.server.contextLines)
        limit = self._getInt(data, "limit", self.server.defaultLimit)
        pageOffset = self._getPageOffset(data)

        if limit < 1:
            limit = self.server.defaultLimit

        try:
            result = self.server.provider.searchContent(
                query, location=location, folder=folder,
                pathFilter=pathFilter, extensionFilter=extensionFilter,
                caseSensitive=caseSensitive, excludeComments=excludeComments,
                contextLines=contextLines, limit=limit, pageOffset=pageOffset
            )
        except ValueError as e:
            raise HttpError(404, str(e))
        except TimeoutError as e:
            self._lastResult = str(e)
            raise HttpError(504, str(e))
        self._lastResult = f"{len(result.matches)} matches, {result.totalFiles} files"
        self._sendJson(200, _contentResultToJson(query, contextLines, result))

    def _handleFileNameSearch(self) -> None:
        data = self._readJsonBody()
        location = self._getOptionalString(data, "location")
        folder = self._getOptionalString(data, "folder")
        if folder is not None:
            folder = _correctPathSeparator(folder)
        query = self._getStringOrList(data, "query")
        pathFilter = _correctPathSeparator(self._getString(data, "pathFilter", ""))
        caseSensitive = self._getBool(data, "caseSensitive", False)
        limit = self._getInt(data, "limit", self.server.defaultLimit)
        pageOffset = self._getPageOffset(data)

        if limit < 1:
            limit = self.server.defaultLimit

        try:
            result = self.server.provider.searchFileName(
                query, location=location, folder=folder,
                pathFilter=pathFilter, caseSensitive=caseSensitive, limit=limit, pageOffset=pageOffset
            )
        except ValueError as e:
            raise HttpError(404, str(e))
        except TimeoutError as e:
            self._lastResult = str(e)
            raise HttpError(504, str(e))
        self._lastResult = f"{result.totalFiles} files"
        self._sendJson(200, _fileNameResultToJson(query, result))

    def _handleIndexUpdate(self) -> None:
        """Handle POST /api/v1/index/update - update index for a single file."""
        data = self._readJsonBody()
        filePath = self._getString(data, "file")
        if not filePath:
            raise HttpError(400, "Field 'file' must not be empty")
        filePath = _correctPathSeparator(filePath)

        try:
            result = self.server.provider.updateFile(filePath)
        except FileNotFoundError as e:
            raise HttpError(404, str(e))
        except ValueError as e:
            raise HttpError(400, str(e))
        self._lastResult = str(result.get("status", str(result)))
        self._sendJson(200, result)

def _correctPathSeparator(path: str) -> str:
    """Normalise path separators to the local OS convention."""
    if not path:
        return path
    if os.sep == '\\':
        return path.replace("/", "\\")
    else:
        return path.replace("\\", "/")


def _shouldRecordHistory(rawPath: str, normalisedPath: str) -> bool:
    """True if the request should appear in the API call history.

    The history endpoint itself and requests carrying an
    ``excludeFromHistory`` query parameter (used by internal probes such as
    the startup health check) must not pollute the history.
    """
    return (not _hasExcludeFromHistory(rawPath)
            and normalisedPath not in ("/api/v1/history", "/history"))


def _hasExcludeFromHistory(path: str) -> bool:
    """True if the request path carries the excludeFromHistory query parameter.

    Used by internal probes (e.g. the startup health check) so that they do not
    show up in the API call history.
    """
    query = path.split("?", 1)[1] if "?" in path else ""
    return any(key == "excludeFromHistory" for key, _ in parse_qsl(query, keep_blank_values=True))


def _contentResultToJson(query: Union[str, List[str]], contextLines: int, result: ContentSearchResult) -> Dict[str, object]:
    matches: List[Union[str, Dict[str, object]]] = []
    if contextLines == 0:
        # Compact format: return matches as strings
        matches = [
            f"{m.file}:{m.line}: {m.fullLine}"
            for m in result.matches
        ]
    else:
        # Full format: return matches as objects
        for m in result.matches:
            match: Dict[str, object] = {
                "file": m.file,
                "line": m.line,
                "fullLine": m.fullLine
            }
            if isinstance(query, str):
                if query != m.matchText:
                    match["matchText"] = m.matchText
            else:
                match["matchText"] = m.matchText # or requires the matchText, otherwise we don't know what has matched
            if m.contextBefore:
                match["contextBefore"] = m.contextBefore
            if m.contextAfter:
                match["contextAfter"] = m.contextAfter
            matches.append(match)
    jsonResult: Dict[str, object] = {
        "totalFiles": result.totalFiles,
        "matches": matches,
    }
    if result.pageOffset is not None:
        jsonResult["pageOffset"] = result.pageOffset
    return jsonResult

def _fileNameResultToJson(query: Union[str, List[str]], result: FileSearchResult) -> Dict[str, object]:
    jsonResult: Dict[str, object] = {
        "totalFiles": result.totalFiles,
        "files": result.files,
    }
    if result.pageOffset is not None:
        jsonResult["pageOffset"] = result.pageOffset
    return jsonResult


def _historyToJson(history: AgentHistory) -> Dict[str, object]:
    """Serialize the API history for the internal (undocumented) history endpoint."""
    entries: List[Dict[str, object]] = []
    for entry in history.entries():
        entries.append({
            "timestamp": entry.timestamp,
            "method": entry.method,
            "path": entry.path,
            "params": entry.params,
            "statusCode": entry.statusCode,
            "durationSecs": entry.durationSecs,
            "result": entry.result,
            "isRunning": entry.isRunning,
        })
    return {"history": entries}

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

    def start(self, port: int) -> bool:
        """
        Start the server in a background daemon thread.

        Returns True if the server was started successfully, False otherwise.
        """
        bind = str(self.config.bind)

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
        return True

    def stop(self) -> None:
        """Shut down the server gracefully."""
        if self.httpd:
            logger.info("Shutting down AI agent server...")
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
            self.thread = None