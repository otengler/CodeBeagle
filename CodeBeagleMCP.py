#! /usr/bin/python3
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

Standalone MCP server for CodeBeagle.

Provides the Model Context Protocol server over stdio so MCP-capable agents
(Claude Desktop, VS Code extensions, custom agents, ...) can search indexed
source code through the CodeBeagle search engine. See ai_agent/MCP-INTEGRATION.md.

This process is a pure adapter: it does NOT start its own HTTP server. It always
connects to the existing CodeBeagle agent HTTP API (run by the CodeBeagle GUI
with the AI agent enabled, or by CodeBeagleAgentServer.exe). This way API call
history is recorded in the server that the GUI can display.

All status output goes to stderr because stdout is the MCP wire.

Configure the agent in your MCP client:
    "codebeagle": { "command": "CodeBeagleMCP" }

When developing from a source tree you can use instead:
    "codebeagle": { "command": "python", "args": ["CodeBeagleMCP.py"] }
"""

import sys

from tools.SetupLogger import setupLogging
from tools import FileTools

def _serverReachable(baseUrl: str) -> bool:
    """Check whether a CodeBeagle agent HTTP server is already running."""
    from ai_agent.mcp_server.client import ApiError, CodeBeagleClient, ServerUnreachable
    try:
        health = CodeBeagleClient(baseUrl, timeoutSeconds=3).health()
        return bool(health.get("status") == "ok")
    except (ApiError, ServerUnreachable):
        return False

def main() -> None:
    setupLogging("codebeagle-mcp.log")
    
    from ai_agent.mcp_server.config import resolveBaseUrl
    baseUrl = resolveBaseUrl()

    if not _serverReachable(baseUrl):
        print(
            f"CodeBeagle agent HTTP server is not running at {baseUrl}. "
            "Enable the 'AI agent' server in the CodeBeagle settings (the 'AI agent' "
            "tab in the settings dialog) or start CodeBeagleAgentServer.",
            file=sys.stderr,
        )
        sys.exit(1)

    from ai_agent.mcp_server.server import main as runMCP
    print(f"CodeBeagle MCP server (stdio), HTTP API at {baseUrl}", file=sys.stderr)
    runMCP(baseUrl)

if __name__ == "__main__":
    # Switch to application directory to be able to load the configuration even
    # if we are executed from a different working directory.
    FileTools.switchToAppDir()
    main()