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
import os
from typing import Any, Dict, Optional, cast

DEFAULT_BASE_URL = "http://127.0.0.1:8080"
ENV_VAR_NAME = "CODEBEAGLE_API_URL"
CONFIG_FILE_NAME = "codebeagle.json"

def _stripTrailingSlash(url: str) -> str:
    """Remove trailing slashes from a base URL."""
    return url.rstrip("/")

def _readJsonFile(path: str) -> Optional[Dict[str, Any]]:
    """Read a JSON file and return its content as a dict, or None on error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return cast(Dict[str, Any], data)

def resolveBaseUrl(appDir: Optional[str] = None) -> str:
    """
    Resolve the base URL of the CodeBeagle agent HTTP server.

    Precedence:
    1. CODEBEAGLE_API_URL environment variable.
    2. codebeagle.json next to this package or in the application directory,
       e.g. {"baseUrl": "http://127.0.0.1:8080"}.
    3. The 'agent' section of the CodeBeagle configuration (if the agent
       server is enabled there).
    4. http://127.0.0.1:8080 (default).
    """
    envUrl = os.environ.get(ENV_VAR_NAME)
    if envUrl:
        return _stripTrailingSlash(envUrl)

    candidates = [os.path.join(os.path.dirname(__file__), CONFIG_FILE_NAME)]
    if appDir:
        candidates.insert(0, os.path.join(appDir, CONFIG_FILE_NAME))
    for configPath in candidates:
        if not os.path.isfile(configPath):
            continue
        config = _readJsonFile(configPath)
        if config:
            baseUrl = config.get("baseUrl")
            if isinstance(baseUrl, str) and baseUrl:
                return _stripTrailingSlash(baseUrl)

    try:
        from AppConfig import appConfig
        agent = appConfig().agent
        if agent.enabled:
            return _stripTrailingSlash(f"http://{agent.bind}:{agent.port}")
    except Exception:
        # The config is optional; fall through to the default below.
        pass

    return DEFAULT_BASE_URL