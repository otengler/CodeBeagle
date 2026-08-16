# Mock instructions for connecting AI agents to CodeBeagle. Replace with real setup
# instructions once the agent connections are implemented.
piAgentInstructions = """\
The user wants you to install the "CodeBeagle" extension. The setup steps are: 
1. Download the CodeBeagle PI extension from http://localhost:{port}/api/v1/pi-extension and store the downloaded file as codebeagle.ts in the PI user extension
   folder (e.g. ~/.pi/agent/extensions/).
2. Create a JSON config file named codebeagle.json in the same folder as codebeagle.ts. It contains the base URL of the CodeBeagle agent server:
   {{
     "baseUrl": "http://localhost:{port}"
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
<p><b>ChatGPT Codex</b></p>
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
<p><b>Other MCP capable agent</b></p>
Ask your agent how to setup a stdio based MCP server that is contained in an executable. When asked provide the path to the server as:
<pre style="font-family: 'Courier New', monospace; background-color: #1E1E1E; color: #F0F0F0; padding: 8px; border: 1px solid #383838; border-radius: 4px;">
"{mcp_executable}"
</pre>
"""

otherAgentInstructions = """\
Download the CodeBeagle API documentation from here http://localhost:{port}/api/v1/docs.
The base URL to access the API is http://localhost:{port}
"""