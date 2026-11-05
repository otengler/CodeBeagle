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

from typing import Any, List, Dict
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

TOOL_DATA: Dict[str, ToolDescription] = {}

def loadToolDescriptions(path: str) -> Dict[str, ToolDescription]:
    """Load all tool descriptions from a tool_desc.json file."""
    with open(path, "r", encoding="utf-8") as _f:
        data = json.load(_f)
    return {tool_key: ToolDescription.fromJson(tool_data) for tool_key, tool_data in data.items()}

def tool_desc(tool_key: str) -> ToolDescription:
    """Build tool scription"""
    global TOOL_DATA   
    if not TOOL_DATA:
        _loadToolDescription()
    return TOOL_DATA[tool_key]

def _loadToolDescription() -> None:
    global TOOL_DATA
    toolDescPath = os.path.join("resources", "ai_agent", "tool_desc.json")
    try:
        TOOL_DATA = loadToolDescriptions(toolDescPath)
    except Exception as e:
        raise RuntimeError("Could not load tool_desc.json from %s: %s", toolDescPath, e)

