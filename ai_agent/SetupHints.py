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

CodeBeagle supports agents that understand the Model Context Protocol (MCP),
for example Claude Code, ChatGPT, Cursor and similar tools.

To connect an MCP compatible agent to CodeBeagle:

1. Enable the AI agent web server in this settings page.
2. Add CodeBeagle as an MCP server to your agent configuration.
3. Restart the application so the server picks up the configured port.
4. The agent can then search source code through the CodeBeagle MCP tools.

(Mock text - real instructions will be added later.)
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