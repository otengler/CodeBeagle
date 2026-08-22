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

Shared type definitions for the CodeBeagle MCP server.

The input models double as JSON Schemas for the MCP tool definitions
(pydantic model_json_schema()) and as validators for tool arguments.
Field names use snake_case; toHttpParams() translates them to the
camelCase field names expected by the CodeBeagle HTTP API.
"""

import json
import os
from typing import Any, Dict, List, Optional, Union, cast

from pydantic import BaseModel, Field


# ---- Load parameter descriptions from tool_desc.json ----

_TOOL_DESC_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "resources", "ai_agent", "tool_desc.json",
)
try:
    with open(_TOOL_DESC_PATH, "r", encoding="utf-8") as _f:
        _TOOL_DESC_DATA = json.load(_f)
except Exception as e:
    raise RuntimeError("Could not load tool_desc.json from %s: %s", _TOOL_DESC_PATH, e)


def _param_desc(tool_key: str, param_key: str) -> str:
    """Look up a parameter description from tool_desc.json."""
    return cast(str, _TOOL_DESC_DATA.get(tool_key, {}).get("params", {}).get(param_key, ""))


class ContentSearchInput(BaseModel):
    """Parameters for a full-text content search (search_content tool)."""

    query: Union[str, List[str]] = Field(
        description=_param_desc("codebeagle_content_search", "query")
    )
    folder: Optional[str] = Field(
        default=None,
        description=_param_desc("codebeagle_content_search", "folder"),
    )
    location: Optional[str] = Field(
        default=None,
        description=_param_desc("codebeagle_content_search", "location"),
    )
    path_filter: Optional[str] = Field(
        default=None,
        description=_param_desc("codebeagle_content_search", "pathFilter"),
    )
    extension_filter: Optional[str] = Field(
        default=None,
        description=_param_desc("codebeagle_content_search", "extensionFilter"),
    )
    case_sensitive: bool = Field(
        default=False,
        description=_param_desc("codebeagle_content_search", "caseSensitive"),
    )
    exclude_comments: bool = Field(
        default=True,
        description=_param_desc("codebeagle_content_search", "excludeComments"),
    )
    context_lines: int = Field(
        default=2,
        ge=0,
        le=20,
        description=_param_desc("codebeagle_content_search", "contextLines"),
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=10000,
        description=_param_desc("codebeagle_content_search", "limit"),
    )
    page_offset: Optional[Dict[str, int]] = Field(
        default=None,
        description=_param_desc("codebeagle_content_search", "pageOffset"),
    )

    def toHttpParams(self) -> Dict[str, Any]:
        """Translate to the field names used by the HTTP API, dropping None values."""
        return _dropNone({
            "query": self.query,
            "folder": self.folder,
            "location": self.location,
            "pathFilter": self.path_filter,
            "extensionFilter": self.extension_filter,
            "caseSensitive": self.case_sensitive,
            "excludeComments": self.exclude_comments,
            "contextLines": self.context_lines,
            "limit": self.limit,
            "pageOffset": self.page_offset,
        })


class FileNameSearchInput(BaseModel):
    """Parameters for a file name search (search_filename tool)."""

    query: Union[str, List[str]] = Field(
        description=_param_desc("codebeagle_file_search", "query")
    )
    folder: Optional[str] = Field(
        default=None,
        description=_param_desc("codebeagle_file_search", "folder"),
    )
    location: Optional[str] = Field(
        default=None,
        description=_param_desc("codebeagle_file_search", "location"),
    )
    path_filter: Optional[str] = Field(
        default=None,
        description=_param_desc("codebeagle_file_search", "pathFilter"),
    )
    case_sensitive: bool = Field(
        default=False,
        description=_param_desc("codebeagle_file_search", "caseSensitive"),
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=10000,
        description=_param_desc("codebeagle_file_search", "limit"),
    )
    page_offset: Optional[Dict[str, int]] = Field(
        default=None,
        description=_param_desc("codebeagle_file_search", "pageOffset"),
    )

    def toHttpParams(self) -> Dict[str, Any]:
        """Translate to the field names used by the HTTP API, dropping None values."""
        return _dropNone({
            "query": self.query,
            "folder": self.folder,
            "location": self.location,
            "pathFilter": self.path_filter,
            "caseSensitive": self.case_sensitive,
            "limit": self.limit,
            "pageOffset": self.page_offset,
        })


def _dropNone(data: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the dict without entries whose value is None."""
    return {key: value for key, value in data.items() if value is not None}