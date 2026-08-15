# Mock instructions for connecting AI agents to CodeBeagle. Replace with real setup
# instructions once the agent connections are implemented.
piAgentInstructions = """\
The user wants you to install the "CodeBeagle" extension. The setup steps are: 
1. Download the CodeBeagle PI extension from http://localhost:{port}/pi-extension and store the downloaded file as codebeagle.ts in the PI user extension
   folder (e.g. ~/.pi/agent/extensions/).
2. Create a JSON config file named codebeagle.json in the same folder as codebeagle.ts. It contains the base URL of the CodeBeagle agent server:
   {{
     "baseUrl": "http://127.0.0.1:{port}"
   }}
3. Restart PI (or use /reload) so the extension is loaded.
"""

mcpAgentInstructions = """\
MCP compatible agents
======================

CodeBeagle ships a Model Context Protocol (MCP) server so MCP-capable agents
(for example Claude Desktop, Claude Code, Cursor) can search indexed source
code directly.

To connect an MCP compatible agent to CodeBeagle:

1. Enable the AI agent web server in this settings page (the MCP server
   connects to it).
2. Add CodeBeagle as an MCP server to your agent's configuration, e.g. for
   Claude Desktop in claude_desktop_config.json:

   {{
     "mcpServers": {{
       "codebeagle": {{
         "command": "CodeBeagleMCP"
       }}
     }}
   }}

   When running from a source tree instead of the distribution use:
   "command": "python", "args": ["CodeBeagleMCP.py"]
3. Restart the agent so the MCP server starts. It reads the configured port
   from the CodeBeagle settings, so no port needs to be configured here.
4. The agent can then use the CodeBeagle MCP tools (list_locations,
   search_content, search_filename) to search your code.

See ai_agent/MCP-INTEGRATION.md for the full protocol documentation.
"""

otherAgentInstructions = """\
Other agents
============

Any agent that can issue HTTP requests can search code through the
CodeBeagle REST API.

To connect your agent:

1. Enable the AI agent web server in this settings page.
2. Check the listen port and make sure the server can be reached.
3. Point your agent at the CodeBeagle API endpoints, e.g.
   POST /api/v1/search/content
4. Restart the application so the server picks up the configured port.

See the documentation in ai_agent/API.md for the full API description.

(Mock text - real instructions will be added later.)
"""