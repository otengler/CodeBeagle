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

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ContentSearchInput(BaseModel):
    """Parameters for a full-text content search (search_content tool)."""

    query: Union[str, List[str]] = Field(
        description=(
            "Search expression or list of expressions (OR logic). "
            "Supports keywords ('createNode ( CComVariant'), "
            "trailing wildcards ('Fact*'), unknown-word gaps ('error **2 network') "
            "and regex ('code <!\\d+!>'). "
            "When a list is provided, files matching ANY expression are returned."
        )
    )
    folder: Optional[str] = Field(
        default=None,
        description=(
            "Root folder path to search in. The server resolves the best matching "
            "index. Mutually exclusive with 'location'."
        ),
    )
    location: Optional[str] = Field(
        default=None,
        description=(
            "Named search location (from list_locations). Mutually exclusive with 'folder'."
        ),
    )
    path_filter: Optional[str] = Field(
        default=None,
        description=(
            "Path filter pattern. Can be a full file path to select a single file. "
            "Prefix with '-' to exclude. Example: 'src/, -test/mock'"
        ),
    )
    extension_filter: Optional[str] = Field(
        default=None,
        description=(
            "Comma-separated extensions. Prefix with '-' to exclude. "
            "Example: '.py, .js, -test.py'"
        ),
    )
    case_sensitive: bool = Field(
        default=False,
        description="Enable case-sensitive matching (default: false).",
    )
    exclude_comments: bool = Field(
        default=True,
        description="Exclude matches inside comments (default: true).",
    )
    context_lines: int = Field(
        default=2,
        ge=0,
        le=20,
        description="Number of context lines before and after each match (default: 2). Set to 0 for compact output (no context lines).",
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Maximum number of matches to return (default: 100).",
    )
    page_offset: Optional[Dict[str, int]] = Field(
        default=None,
        description=(
            "Pagination cursor from a previous response. Pass the 'pageOffset' "
            "object exactly as returned by the server. Must contain 'fileIndex' "
            "(integer) and optionally 'matchIndex' (integer)."
        ),
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

    query: str = Field(
        description=(
            "File name pattern. Supports * and ? wildcards. "
            "Example: 'Factory*', '*test*.py', 'test?.py'. If the query contains "
            "a dot, the part after the last dot is used as an extension filter."
        )
    )
    folder: Optional[str] = Field(
        default=None,
        description=(
            "Root folder path to search in. The server resolves the best matching "
            "index. Mutually exclusive with 'location'."
        ),
    )
    location: Optional[str] = Field(
        default=None,
        description=(
            "Named search location (from list_locations). Mutually exclusive with 'folder'."
        ),
    )
    path_filter: Optional[str] = Field(
        default=None,
        description=(
            "Path filter pattern. Can be a full file path to select a single file. "
            "Prefix with '-' to exclude. Example: 'src, -test'"
        ),
    )
    extension_filter: Optional[str] = Field(
        default=None,
        description="Comma-separated extensions. Prefix with '-' to exclude. Example: '.py, .js'.",
    )
    case_sensitive: bool = Field(
        default=False,
        description="Enable case-sensitive matching (default: false).",
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Maximum number of files to return (default: 100).",
    )
    page_offset: Optional[Dict[str, int]] = Field(
        default=None,
        description=(
            "Pagination cursor from a previous response. Pass the 'pageOffset' "
            "object exactly as returned by the server. Must contain 'fileIndex' "
            "(integer) and optionally 'matchIndex' (integer)."
        ),
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
            "limit": self.limit,
            "pageOffset": self.page_offset,
        })


def _dropNone(data: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the dict without entries whose value is None."""
    return {key: value for key, value in data.items() if value is not None}