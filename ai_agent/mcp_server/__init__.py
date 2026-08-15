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

MCP (Model Context Protocol) server for CodeBeagle.

Exposes CodeBeagle's local HTTP search API (ai_agent/Server.py) as MCP tools
so MCP-capable agents (Claude Desktop, VS Code extensions, custom agents, ...)
can search indexed source code. See ai_agent/MCP-INTEGRATION.md for the
full integration plan.

Run the stdio server with:
    python -m ai_agent.mcp_server
"""

from .client import ApiError, CodeBeagleClient, ServerUnreachable
from .config import DEFAULT_BASE_URL, resolveBaseUrl
from .server import CodeBeagleMCPServer, runStdioServer

__all__ = [
    "ApiError",
    "CodeBeagleClient",
    "CodeBeagleMCPServer",
    "DEFAULT_BASE_URL",
    "ServerUnreachable",
    "resolveBaseUrl",
    "runStdioServer",
]
