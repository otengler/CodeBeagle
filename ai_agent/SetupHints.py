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
<p><b>Claude Code</b></p>
Enter this on the command line (not inside the chat windows):
<pre style="font-family: 'Courier New', monospace; background-color: #1E1E1E; color: #F0F0F0; padding: 8px; border: 1px solid #383838; border-radius: 4px;">
claude mcp add CodeBeagle -- "{mcp_executable}"
</pre>
<p/>
<p><b>ChatGPT</b></p>
CodeBeagle needs to be integrated as a local MCP server using the 
<a href="https://github.com/openai/tunnel-client/">tunnel-client</a>.
The setup requires several steps and is not described here in details. At some point you need to start the tunnel-client:
<pre style="font-family: 'Courier New', monospace; background-color: #1E1E1E; color: #F0F0F0; padding: 8px; border: 1px solid #383838; border-radius: 4px;">
tunnel-client.exe run --mcp.command "{mcp_executable}"
</pre>
<p><b>Cursor</b></p>
<p>
Add a "mcp.json" under your project folder:
</p>
<pre>
MyProject/
└── .cursor/
    └── mcp.json
</pre>
<p>
Place the following content in it:
</p>
<pre>
{{
  "mcpServers": {{
    "CodeBeagle": {{
      "command": "{mcp_executable}"
    }}
  }}
}}
</pre>
<p>
Restart cursor.
</p>
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