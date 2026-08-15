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

Entry point for the CodeBeagle MCP server.

Run with:
    python -m ai_agent.mcp_server

The server speaks MCP over stdio and forwards tool calls to the local
CodeBeagle agent HTTP API (see ai_agent/Server.py). The base URL is resolved
by config.resolveBaseUrl() (env var CODEBEAGLE_API_URL, codebeagle.json next
to this package or in the app directory, the 'agent' section of config.txt,
or the default http://127.0.0.1:8080).
"""

def main() -> None:
    from tools import FileTools
    # Switch to the application directory so config.txt / UserConfig.txt can be
    # loaded even if we are executed from a different working directory.
    FileTools.switchToAppDir()

    from ai_agent.mcp_server.config import resolveBaseUrl
    from ai_agent.mcp_server.server import main as runServer

    baseUrl = resolveBaseUrl()
    runServer(baseUrl)

if __name__ == "__main__":
    main()