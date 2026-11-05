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

Resolve the PI extension template (codebeagle.ts) by replacing its
__...__ markers with the descriptions from tool_desc.json.
"""

import json
import os
from typing import Dict
from .ToolDescription import ToolDescription, loadToolDescriptions

# Tools registered by the PI extension. The marker names inside codebeagle.ts
# are derived from these names, e.g. codebeagle_content_search becomes
# __TOOL_DESC_CONTENT_SEARCH__ / __PARAM_DESC_CONTENT_SEARCH_QUERY__.
PI_TOOL_NAMES = [
    "codebeagle_content_search",
    "codebeagle_file_search",
    "codebeagle_list_indexes",
    "codebeagle_health",
    "codebeagle_update_file",
]

# Standard port of the CodeBeagle agent server (see AppConfig.agentConfig).
DEFAULT_PORT = 8080

# Default base URL baked into the versioned codebeagle.ts template.
TEMPLATE_BASE_URL = "http://127.0.0.1:8080"

def resolvePiExtension(resourceDir: str, port: int = DEFAULT_PORT) -> str:
    """Return codebeagle.ts with all __...__ markers replaced by real text.

    resourceDir must contain tool_desc.json and pi/extensions/codebeagle.ts.
    The standard port is used as the default base URL baked into the extension.
    """
    descriptions = loadToolDescriptions(os.path.join(resourceDir, "tool_desc.json"))
    templatePath = os.path.join(resourceDir, "pi", "extensions", "codebeagle.ts")
    with open(templatePath, "r", encoding="utf-8") as f:
        content = f.read()
    content = _replaceToolMarkers(content, descriptions)
    baseUrl = f"http://127.0.0.1:{port}"
    if baseUrl != TEMPLATE_BASE_URL:
        content = content.replace(TEMPLATE_BASE_URL, baseUrl)
    return content

def _replaceToolMarkers(content: str, descriptions: Dict[str, ToolDescription]) -> str:
    for toolName in PI_TOOL_NAMES:
        tool = descriptions[toolName]
        shortName = toolName.replace("codebeagle_", "").upper()
        content = content.replace(f"__TOOL_DESC_{shortName}__", tool.desc)
        content = content.replace(f"__PROMPT_SNIPPET_{shortName}__", tool.promptSnippet)
        content = content.replace(f'"__PROMPT_GUIDELINES_{shortName}__"', json.dumps(tool.promptGuidelines))
        for paramName, paramDesc in tool.params.items():
            content = content.replace(f"__PARAM_DESC_{shortName}_{paramName.upper()}__", paramDesc)
    return content