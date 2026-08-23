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
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

class ApiError(Exception):
    """An error returned by the CodeBeagle HTTP API."""

    def __init__(self, statusCode: int, message: str) -> None:
        super().__init__(message)
        self.statusCode = statusCode
        self.message = message

class ServerUnreachable(ApiError):
    """The CodeBeagle agent server could not be reached at all."""

    def __init__(self, baseUrl: str, reason: str) -> None:
        super().__init__(0, f"CodeBeagle agent server not reachable at {baseUrl}: {reason}")
        self.baseUrl = baseUrl
        self.reason = reason

class CodeBeagleClient:
    """
    Thin HTTP client for the local CodeBeagle agent API (ai_agent/Server.py).

    Endpoints used:
      GET  /api/v1/health
      GET  /api/v1/locations
      POST /api/v1/search/content
      POST /api/v1/search/filename
    """

    def __init__(self, baseUrl: str = "http://127.0.0.1:8080", timeoutSeconds: float = 60.0) -> None:
        self.baseUrl = baseUrl.rstrip("/")
        self.timeoutSeconds = timeoutSeconds

    def get(self, path: str) -> Dict[str, Any]:
        """Send a GET request and return the parsed JSON body."""
        return self._request("GET", path)

    def post(self, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a POST request with a JSON body and return the parsed JSON body."""
        return self._request("POST", path, body)

    # ---- API endpoints ----

    def health(self) -> Dict[str, Any]:
        """Check whether the agent server is up."""
        return self.get("/api/v1/health")

    def getLocations(self) -> Dict[str, Any]:
        """Return the configured search locations (name, folders, extensions, indexMode)."""
        return self.get("/api/v1/locations")

    def searchContent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run a content search; see the HTTP API for the accepted fields."""
        return self.post("/api/v1/search/content", params)

    def searchFileName(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run a file name search; see the HTTP API for the accepted fields."""
        return self.post("/api/v1/search/filename", params)

    def updateFile(self, filePath: str) -> Dict[str, Any]:
        """Update the CodeBeagle index for a single file."""
        return self.post("/api/v1/index/update", {"file": filePath})

    # ---- Internals ----

    def _request(self, method: str, path: str,
                 body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = self.baseUrl + path
        data: Optional[bytes] = None
        headers: Dict[str, str] = {}
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeoutSeconds) as response:  # noqa: S310
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            message = self._errorMessage(e)
            raise ApiError(e.code, message) from e
        except urllib.error.URLError as e:
            reason = str(e.reason) if e.reason else str(e)
            raise ServerUnreachable(self.baseUrl, reason) from e
        except OSError as e:
            raise ServerUnreachable(self.baseUrl, str(e)) from e
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ApiError(500, f"Invalid JSON response from {path}: {e}") from e
        if not isinstance(data, dict):
            raise ApiError(500, f"Unexpected response from {path}: expected a JSON object")
        return data

    @staticmethod
    def _errorMessage(error: urllib.error.HTTPError) -> str:
        """Extract the 'error' field from an error response body."""
        try:
            raw = error.read().decode("utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                message = data.get("error")
                if isinstance(message, str) and message:
                    return message
        except Exception:
            pass
        return error.reason if error.reason else f"HTTP {error.code}"
