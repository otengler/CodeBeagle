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

from typing import Any, List, Dict, Optional
import os, json

class ToolDescription:
    desc: str = ""
    promptSnippet: str = ""
    promptGuidelines: List[str] = []
    params: Dict[str, str] = {}

    def param(self, name: str) -> str:
        return self.params[name]

    def mcpDesc(self) -> str:
        """Join desc and append promptGuidelines (if any) for MCP tool description."""
        desc = self.desc
        if self.promptGuidelines:
            desc = desc + " " + " ".join(self.promptGuidelines)
        return desc

    @staticmethod
    def fromJson(json: Any) -> ToolDescription:
        td = ToolDescription()
        desc= json["desc"]
        if not isinstance(desc, list):
            desc = [desc]
        td.desc = " ".join(desc)
        if "promptSnippet" in json:
            td.promptSnippet = json["promptSnippet"]
        if "promptGuidelines" in json:
            td.promptGuidelines = json["promptGuidelines"]
        if "params" in json:
            td.params = json["params"]
        return td

class AgenticTools:
    """Tool descriptions and the PI extension version read from tool_desc.json."""

    def __init__(self, version: int, tools: Dict[str, ToolDescription]) -> None:
        self.version = version
        self.tools = tools

_CACHED_TOOLS: Optional[AgenticTools] = None

def toolDesc(tool_key: str) -> ToolDescription:
    """Return the description of a single tool from the default resource file."""
    return _cachedTools().tools[tool_key]

def loadAgenticTools(path: str = "") -> AgenticTools:
    """Load all tool descriptions and the extension version from tool_desc.json.

    If path is empty the default resource location is used. The data is always
    read from disk; no cached or global state is used or modified. A missing
    'version' entry defaults to 1.
    """
    toolDescPath = path or os.path.join("resources", "ai_agent", "tool_desc.json")
    try:
        with open(toolDescPath, "r", encoding="utf-8") as _f:
            data = json.load(_f)
    except Exception as e:
        raise RuntimeError(f"Could not load tool_desc.json from {toolDescPath}: {e}")
    tools = {tool_key: ToolDescription.fromJson(tool_data) for tool_key, tool_data in data["tools"].items()}
    return AgenticTools(int(data.get("version", 1)), tools)

def toolVersion() -> int:
    """Version of the PI extension (codebeagle.ts) read from tool_desc.json.

    Bump the 'version' entry in tool_desc.json whenever the extension changes so
    that the server can tell a PI agent when its installed extension is
    outdated. The extension reports its version via the 'pi-version' query
    parameter when it calls the health endpoint.
    """
    return _cachedTools().version

def _cachedTools() -> AgenticTools:
    """Load and cache the default tool descriptions on first use."""
    global _CACHED_TOOLS
    if _CACHED_TOOLS is None:
        _CACHED_TOOLS = loadAgenticTools()
    return _CACHED_TOOLS

