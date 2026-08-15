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

MCP server that exposes the CodeBeagle search engine as MCP tools.

Implemented with the official Python MCP SDK (mcp >= 2.0). The server talks
to the local CodeBeagle HTTP API (ai_agent/Server.py) through
CodeBeagleClient and registers three tools:

  - list_locations        -> GET  /api/v1/locations
  - search_content        -> POST /api/v1/search/content
  - search_filename       -> POST /api/v1/search/filename

Run via stdio with:  python CodeBeagleMCP.py
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

import mcp_types as types
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp_types import ServerCapabilities, ToolsCapability
from pydantic import BaseModel, ValidationError

from .client import ApiError, CodeBeagleClient, ServerUnreachable
from .types import ContentSearchInput, FileNameSearchInput

logger = logging.getLogger(__name__)

SERVER_NAME = "codebeagle"
SERVER_VERSION = "1.0.0"

# A tool definition: (inputModel, description, handler)
#   inputModel = None for parameter-less tools (list_locations)
#   inputModel = a pydantic BaseModel subclass for tools with parameters
#   handler receives the validated model (or None for parameter-less tools)
ToolDef = Tuple[
    Optional[Type[BaseModel]],
    str,
    Callable[..., Dict[str, Any]],
]

# ---- Tool descriptions ----

_DESC_LIST_LOCATIONS = (
    "List all configured CodeBeagle search locations (indexes): name, folders, "
    "extensions and index mode. Call this first to discover what is searchable, "
    "then pass the location name to search_content / search_filename."
)
_DESC_SEARCH_CONTENT = (
    "Full-text search across CodeBeagle-indexed source code. Query syntax: "
    "keywords ('createNode ( CComVariant'), trailing wildcards ('Fact*'), "
    "unknown-word gaps ('error **2 network'), regex ('code <!\\d+!>'). "
    "Specify either 'location' (name from list_locations) or 'folder' (root path; "
    "the server resolves the best matching index). Returns matching lines with "
    "surrounding context and a pageOffset if more results exist. "
    "Set format='json' (default) for the full JSON response or format='compact' "
    "for 'path:line: full matching line' output (no context lines)."
)
_DESC_SEARCH_FILENAME = (
    "Search for files by name across CodeBeagle-indexed source code. "
    "The query supports * and ? wildcards ('Factory*', '*test*.py', 'Makefile'). "
    "If the query contains a dot, the part after the last dot is used as an "
    "extension filter. Returns full file paths and a pageOffset if more "
    "results exist. Set format='json' (default) for the full JSON response or "
    "format='compact' for one file path per line."
)

_EMPTY_SCHEMA: Dict[str, Any] = {"type": "object", "properties": {}, "required": []}

class CodeBeagleMCPServer:
    """
    Wraps the MCP server instance and registers the CodeBeagle tools.

    The tool registry is the single source of truth: each entry carries the
    input model (used for both schema generation and argument validation) and
    the handler. The dispatch validates arguments against the registered model
    and passes the validated instance to the handler.
    """

    def __init__(self, baseUrl: str) -> None:
        self.client = CodeBeagleClient(baseUrl)
        self._tools: Dict[str, ToolDef] = {
            "list_locations": (None, _DESC_LIST_LOCATIONS, self._listLocations),
            "search_content": (ContentSearchInput, _DESC_SEARCH_CONTENT, self._searchContent),
            "search_filename": (FileNameSearchInput, _DESC_SEARCH_FILENAME, self._searchFileName),
        }
        self._server = Server(
            SERVER_NAME,
            version=SERVER_VERSION,
            description="Search source code with the CodeBeagle full-text index engine.",
            on_list_tools=self._handleListTools,
            on_call_tool=self._handleCallTool,
        )

    @property
    def server(self) -> Server[Any]:
        """The underlying MCP Server instance (for transports and capabilities)."""
        return self._server

    # ---- MCP request handlers ----

    async def _handleListTools(self, ctx: Any, params: Any) -> types.ListToolsResult:
        tools: List[types.Tool] = []
        for name, (inputModel, description, _) in self._tools.items():
            inputSchema = _EMPTY_SCHEMA if inputModel is None else inputModel.model_json_schema()
            tools.append(types.Tool(name=name, description=description, input_schema=inputSchema))
        return types.ListToolsResult(tools=tools)

    async def _handleCallTool(self, ctx: Any, params: types.CallToolRequestParams) -> types.CallToolResult:
        name = params.name
        arguments = params.arguments or {}
        entry = self._tools.get(name)
        if entry is None:
            return _toolError(f"Unknown tool: {name}")
        inputModel, _, handler = entry
        try:
            if inputModel is None:
                validated: Any = None
            else:
                validated = inputModel.model_validate(arguments)
            data = handler(validated)
        except ValidationError as e:
            return _toolError(f"Invalid parameters: {_formatValidationError(e)}")
        except ApiError as e:
            return _toolError(_apiErrorText(e))
        except Exception as e:
            logger.exception("Tool %s failed", name)
            return _toolError(f"Internal error: {e}")
        text = _formatResult(name, data, arguments.get("format"))
        return types.CallToolResult(content=[types.TextContent(type="text", text=text)])

    # ---- Tool implementations ----

    def _listLocations(self, _unused: Any) -> Dict[str, Any]:
        return self.client.getLocations()

    def _searchContent(self, input_: ContentSearchInput) -> Dict[str, Any]:
        return self.client.searchContent(input_.toHttpParams())

    def _searchFileName(self, input_: FileNameSearchInput) -> Dict[str, Any]:
        return self.client.searchFileName(input_.toHttpParams())

# ---- Result formatting helpers ----

def _formatResult(name: str, data: Dict[str, Any], outputFormat: Any) -> str:
    """Format a tool result: JSON (default) or compact path:line lines."""
    if outputFormat == "compact":
        if name == "search_content":
            matches = data.get("matches")
            if isinstance(matches, list):
                return "\n".join(
                    f"{m.get('file')}:{m.get('line')}: {m.get('fullLine')}"
                    for m in matches
                    if isinstance(m, dict)
                )
        if name == "search_filename":
            files = data.get("files")
            if isinstance(files, list):
                return "\n".join(str(f) for f in files)
    return json.dumps(data, ensure_ascii=False, indent=2)

def _toolError(message: str) -> types.CallToolResult:
    """Return a CallToolResult that reports an error to the agent."""
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=message)],
        is_error=True,
    )

def _apiErrorText(error: ApiError) -> str:
    """Map an HTTP API error to agent guidance."""
    if isinstance(error, ServerUnreachable):
        return (
            f"{error.message}. "
            "Start the CodeBeagle GUI with the 'AI agent' server enabled or run "
            "CodeBeagleAgentServer.py to make CodeBeagle searchable."
        )
    if error.statusCode == 400:
        return f"Invalid parameters: {error.message}"
    if error.statusCode == 404:
        return (
            f"Location or folder not indexed: {error.message}. "
            "Call list_locations to discover the available search locations."
        )
    return f"CodeBeagle API error {error.statusCode}: {error.message}"

def _formatValidationError(error: ValidationError) -> str:
    """Format a pydantic validation error into a short, readable message."""
    parts: List[str] = []
    for item in error.errors():
        loc = ".".join(str(part) for part in item["loc"])
        parts.append(f"{loc}: {item['msg']}")
    return "; ".join(parts)

# ---- Transport ----

def _buildCapabilities() -> ServerCapabilities:
    """Build capabilities without the (empty) `experimental` dict.

    `Server.create_initialization_options()` always sets
    `experimental={}`, which the MCP Inspector shows as ✓ Experimental
    even though no experimental capabilities are offered.  Building the
    options manually leaves `experimental` unset so it is dropped from
    the wire by `exclude_unset=True` in the stdio transport.
    """
    return ServerCapabilities(tools=ToolsCapability(list_changed=False))


async def runStdioServer(baseUrl: str) -> None:
    """Serve MCP over stdio until the client closes the connection."""
    mcpServer = CodeBeagleMCPServer(baseUrl)
    initializationOptions = InitializationOptions(
        server_name=mcpServer.server.name,
        server_version=mcpServer.server.version,
        description=mcpServer.server.description,
        capabilities=_buildCapabilities(),
    )
    async with stdio_server() as (readStream, writeStream):
        await mcpServer.server.run(readStream, writeStream, initializationOptions)

def main(baseUrl: str) -> None:
    """Entry point for the stdio server (blocking)."""
    asyncio.run(runStdioServer(baseUrl))