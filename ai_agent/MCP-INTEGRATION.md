# MCP Integration Plan for CodeBeagle

This document describes how an MCP (Model Context Protocol) capable AI agent can discover,
consume, and integrate CodeBeagle's search API. It covers the MCP server wrapper, tool/resource
definitions, client consumption patterns, and implementation guidance.

---

## Table of Contents

1. [Overview](#overview)
2. [MCP Concepts Applied to CodeBeagle](#mcp-concepts-applied-to-codebeagle)
3. [Architecture](#architecture)
4. [MCP Server Implementation](#mcp-server-implementation)
5. [Tool Definitions](#tool-definitions)
6. [Resource Definitions](#resource-definitions)
7. [Prompt Templates](#prompt-templates)
8. [Client Consumption Patterns](#client-consumption-patterns)
9. [Authentication & Security](#authentication--security)
10. [Error Handling & Edge Cases](#error-handling--edge-cases)
11. [Performance Considerations](#performance-considerations)
12. [Implementation Steps](#implementation-steps)

---

## Overview

CodeBeagle already exposes a local HTTP API (`ai_agent/server.py`) for content and filename
search. An MCP server wraps this API into the **Model Context Protocol** so any MCP-compatible
agent client (Claude Desktop, VS Code extensions, custom agents, etc.) can use CodeBeagle as a
tool without writing HTTP-level code.

### What MCP Provides

- **Tool discovery** – The client asks "what can you do?" and gets typed schemas.
- **Resource access** – The client reads files or search result sets via URI addressing.
- **Prompt templates** – Pre-crafted prompt snippets for common search workflows.
- **Structured I/O** – JSON Schema typed inputs/outputs enforced by the protocol.
- **Transports** – Stdio (for local subprocess) or SSE (for remote).

### What the CodeBeagle HTTP API Provides

- Content search with context lines, pagination, caching.
- Filename search with wildcards.
- Location discovery.
- All backed by SQLite full-text indexes.

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                AI Agent Client                       │
│  (Claude Desktop, VS Code extension, custom host)    │
└──────────────┬───────────────────────────────────────┘
               │  MCP Protocol (JSON-RPC over stdio/SSE)
               ▼
┌──────────────────────────────────────────────────────┐
│              CodeBeagle MCP Server                   │
│  ┌───────────────────────────────────────────────┐   │
│  │  MCP Transport Layer (stdio / SSE)            │   │
│  │  - ListTools, CallTool, ListResources,        │   │
│  │    ReadResource, GetPrompt                    │   │
│  └──────────────┬────────────────────────────────┘   │
│                 │  HTTP client (localhost:8080)      │
│  ┌──────────────▼────────────────────────────────┐   │
│  │  CodeBeagle HTTP API (ai_agent/server.py)     │   │
│  │  /api/v1/search/content                       │   │
│  │  /api/v1/search/filename                      │   │
│  │  /api/v1/locations                            │   │
│  │  /api/v1/health                               │   │
│  └──────────────┬────────────────────────────────┘   │
│                 │  SQLite / filesystem               │
│  ┌──────────────▼────────────────────────────────┐   │
│  │  Full-Text Indexes (fulltextindex/*)          │   │
│  └───────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

## MCP Server Implementation

### Recommended Approach: Python MCP SDK

Use the official [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk) to
implement the MCP server. The SDK provides:

- `mcp.server.Server` base class.
- `@server.tool()` decorator for tool registration.
- `@server.resource()` decorator for resource registration.
- `@server.prompt()` decorator for prompt templates.
- Built-in `stdio` and `sse` transports.

**File structure:**

```
mcp_server/
├── __init__.py
├── __main__.py            # Entry point for `python -m mcp_server`
├── server.py              # MCP server creation and tool registration
├── client.py              # HTTP client to CodeBeagle's local API
├── resources.py           # MCP resource handlers
├── prompts.py             # Prompt templates
├── types.py               # Shared type definitions
└── config.py              # Configuration (port, host, etc.)
```

### Minimal Server Skeleton

```python
# mcp_server/server.py
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, Resource, ResourceTemplate, Prompt
import mcp.server.stdio
import httpx  # or urllib.request

from .client import CodeBeagleClient
from .types import (
    ContentSearchInput, ContentSearchResult,
    FileNameSearchInput, FileNameSearchResult,
    LocationList, PaginationCursor
)

class CodeBeagleMCPServer:
    def __init__(self, base_url: str = "http://127.0.0.1:8080"):
        self.client = CodeBeagleClient(base_url)
        self.server = Server("codebeagle")

        # Register tools
        self.server.tool()(self.search_content)
        self.server.tool()(self.search_filename)
        self.server.tool()(self.list_locations)
        self.server.tool()(self.search_content_paginate)
        self.server.tool()(self.search_filename_paginate)

        # Register resources
        self.server.resource("codebeagle://locations")(self.resource_locations)
        self.server.resource("codebeagle://file/{path:path}")(self.resource_file_content)
        self.server.resource("codebeagle://search/{query}")(self.resource_search_results)

        # Register prompts
        self.server.prompt()(self.prompt_search_code)

    async def run_stdio(self):
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, write_stream,
                InitializationOptions(
                    server_name="codebeagle",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
```

---

## Tool Definitions

Each tool maps to one or more HTTP API calls. All tools expose **typed JSON Schema inputs**
so the AI agent knows exactly what parameters are valid.

### Tool 1: `search_content`

Searches file contents and returns matches with context lines.

```python
@server.tool()
async def search_content(
    query: str = Field(description="Search expression. Supports keywords, wildcard (*), phrase proximity (**N), and regex (<!...!>). Example: 'class Factory*' or '<!\\\\b[A-Z]\\\\w+Factory!>'"),
    folder: str = Field(default="", description="Root folder path to search in. The server resolves this to the best matching index. Mutually exclusive with 'location'."),
    location: str = Field(default="", description="Named search location (from list_locations). Mutually exclusive with 'folder'."),
    folder_filter: str = Field(default="", description="Comma-separated folder patterns. Prefix with '-' to exclude. Example: 'test, -test/mock'"),
    extension_filter: str = Field(default="", description="Comma-separated extensions. Prefix with '-' to exclude. Example: '.py, .js, -test.py'"),
    case_sensitive: bool = Field(default=False, description="Enable case-sensitive matching"),
    exclude_comments: bool = Field(default=False, description="Exclude matches inside comments (may not work for all file types)"),
    context_lines: int = Field(default=2, ge=0, le=20, description="Number of lines of context before and after each match"),
    limit: int = Field(default=100, ge=1, le=10000, description="Maximum number of matches to return"),
) -> list[dict]:
    """Search within file contents. Returns matching lines with surrounding context."""
    ...
```

**MCP tool schema** (what the agent sees):

```json
{
  "name": "search_content",
  "description": "Search within file contents. Returns matching lines with surrounding context.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search expression. Supports keywords, wildcards, phrase proximity, and regex."
      },
      "folder": { "type": "string", "description": "Root folder path to search in." },
      "location": { "type": "string", "description": "Named search location." },
      "folder_filter": { "type": "string" },
      "extension_filter": { "type": "string" },
      "case_sensitive": { "type": "boolean", "default": false },
      "exclude_comments": { "type": "boolean", "default": false },
      "context_lines": { "type": "integer", "default": 2, "minimum": 0, "maximum": 20 },
      "limit": { "type": "integer", "default": 100, "minimum": 1, "maximum": 1000 }
    },
    "required": ["query"]
  }
}
```

**Return value** — a list of match objects with file, line, matchText, fullLine, contextBefore, contextAfter.

If there are more results than `limit`, the tool returns a **pagination cursor** as part of the
response metadata. The agent can then call `search_content_paginate` to get the next page.

### Tool 2: `search_content_paginate`

Continues a paginated content search from where the previous call left off.

```python
@server.tool()
async def search_content_paginate(
    query: str,
    page_offset: dict = Field(description="Pagination cursor from a previous search_content or search_content_paginate response. Must contain 'fileIndex' and optionally 'matchIndex'."),
    folder: str = Field(default=""),
    location: str = Field(default=""),
    folder_filter: str = Field(default=""),
    extension_filter: str = Field(default=""),
    case_sensitive: bool = Field(default=False),
    exclude_comments: bool = Field(default=False),
    context_lines: int = Field(default=2),
    limit: int = Field(default=100),
) -> list[dict]:
    """Continue a paginated content search. Pass the pageOffset from a previous response."""
    ...
```

### Tool 3: `search_filename`

Searches file names with wildcard support.

```python
@server.tool()
async def search_filename(
    query: str = Field(description="File name pattern. Supports * and ? wildcards. Example: 'Factory*', '*test*.py', 'test?.py'"),
    folder: str = Field(default=""),
    location: str = Field(default=""),
    folder_filter: str = Field(default=""),
    extension_filter: str = Field(default=""),
    case_sensitive: bool = Field(default=False),
    limit: int = Field(default=100, ge=1, le=10000),
) -> list[str]:
    """Search for file names. Returns full file paths matching the query."""
    ...
```

### Tool 4: `search_filename_paginate`

Paginated variant of `search_filename`.

```python
@server.tool()
async def search_filename_paginate(
    query: str,
    page_offset: dict = Field(description="Pagination cursor with 'fileIndex' field."),
    folder: str = Field(default=""),
    location: str = Field(default=""),
    folder_filter: str = Field(default=""),
    extension_filter: str = Field(default=""),
    case_sensitive: bool = Field(default=False),
    limit: int = Field(default=100),
) -> list[str]:
    """Continue a paginated filename search."""
    ...
```

### Tool 5: `list_locations`

Discovers available search locations. Returns an array of location objects.

```python
@server.tool()
async def list_locations() -> list[dict]:
    """List all configured search locations with their folders, extensions, and index mode."""
    ...
```

**Return value:**

```json
[
  {
    "name": "myproject",
    "folders": ["C:/src/myproject"],
    "extensions": [".py", ".js", ".ts", ".cpp"],
    "indexMode": "filenameAndContent"
  }
]
```

### Rationale: Two Tools per Search Endpoint

The MCP protocol expects `CallTool` to be stateless wherever possible. Rather than exposing
pagination as an opaque side-effect, CodeBeagle's API already uses explicit `pageOffset`
cursors. This maps naturally to two MCP tools:

| Tool | Purpose |
|------|---------|
| `search_content` | First page. Always returns fresh results. |
| `search_content_paginate` | Subsequent pages. Requires a `pageOffset` from a previous call. |

The agent client decides when to paginate: it calls `search_content`, inspects the result for
a `pageOffset`, and calls `search_content_paginate` if it wants more.

**Alternative design** (one tool with an optional `page_offset` parameter) is also valid,
but two tools make the agent's intent clearer in the conversation history.

---

## Resource Definitions

MCP resources let the agent read data via URI — useful for fetching file contents or
pre-computed search result sets without re-running searches.

### Resource `codebeagle://locations`

Returns the list of all configured search locations.

```python
@server.resource("codebeagle://locations")
async def resource_locations() -> list[dict]:
    return await self.client.get_locations()
```

### Resource `codebeagle://file/{path}`

Returns the full text content of a file. The path is URL-encoded.

```python
@server.resource("codebeagle://file/{path:path}")
async def resource_file_content(path: str) -> str:
    """Read the complete content of a source file."""
    file_path = urllib.parse.unquote(path)
    return await self.client.read_file(file_path)
```

**Usage by agent:**

```
Read file: codebeagle://file/C%3A/src/myproject/main.py
```

### Resource Template `codebeagle://search/{query}`

Exposes top search results as a resource. The agent can reference this URI to get a
snapshot of search results without an explicit tool call.

```python
@server.resource("codebeagle://search/{query:path}")
async def resource_search_results(query: str) -> str:
    """Top 10 matches for a search query, formatted as plain text."""
    decoded = urllib.parse.unquote(query)
    results = await self.client.search_content(decoded, limit=10)
    return format_search_as_text(results)
```

### Resource `codebeagle://api-docs`

Returns the full API.md documentation as a resource the agent can reference.

```python
@server.resource("codebeagle://api-docs")
async def resource_api_docs() -> str:
    """The full CodeBeagle HTTP API documentation."""
    return await self.client.get_api_docs()
```

---

## Prompt Templates

MCP prompts are pre-crafted message templates that guide the AI agent on how to use the
tools effectively. The agent can load these to get task-specific instructions.

### Prompt `search_codebase`

Guides the agent through a structured code search workflow.

```python
@server.prompt()
async def prompt_search_codebase(goal: str = "") -> list[Message]:
    """
    Search the codebase to understand a code area or find relevant files.

    Args:
        goal: What the agent should look for (e.g., "Find the factory pattern implementation").
    """
    return [
        Message(
            role="user",
            content=TextContent(
                type="text",
                text=f"""You have access to the CodeBeagle code search engine.
Your goal is: {goal}

Follow this workflow:

1. **Discover** — Call `list_locations` to see which code indexes are available,
   or use the `folder` parameter directly with your project root.

2. **Search broadly** — Use `search_content` with broad keywords to find
   relevant files. Example queries:
   - `"class Factory"` — find class definitions
   - `"def handle_*"` — find methods starting with "handle"
   - `"TODO\\|FIXME"` — find todos (regex)
   - `"import **2 os"` — find imports with up to 2 unknown words

3. **Refine** — Use `folder_filter` to narrow to a specific directory, or
   `extension_filter` to focus on a file type.

4. **Read context** — Use `resource("codebeagle://file/{{path}}")` to read
   interesting files in full.

5. **Paginate** — If `search_content` returns fewer results than expected,
   the response may include a `page_offset`. Pass it to `search_content_paginate`.

Tips:
- Start with 2-3 context lines to understand matches.
- Use wildcards (*) sparingly in content search as they are slower.
- For filename search, use `*` and `?` freely — they are fast.
- When query contains a `.`, the part after the last `.` is treated as
  extension filter for filename search.
"""
            )
        )
    ]
```

### Prompt `find_references`

Specialized for finding all references to a symbol.

```python
@server.prompt()
async def prompt_find_references(symbol: str = "") -> list[Message]:
    """
    Find all references to a symbol in the codebase.

    Args:
        symbol: The symbol name to find references for.
    """
    return [
        Message(
            role="user",
            content=TextContent(
                type="text",
                text=f"""Find all references to `{symbol}` in the codebase.

1. Search content for the symbol: `search_content(query="{symbol}", context_lines=1, limit=200)`
2. If there are many results, paginate using `search_content_paginate`.
3. Group results by file to show which files reference the symbol.
4. If the symbol is a class, also search for imports: `search_content(query="import **2 {symbol}")`
5. Optionally read key files via `codebeagle://file/{{path}}`.

The `totalFiles` field in the response tells you how many files contain the symbol.
"""
        )
    ]
```

---

## Client Consumption Patterns

This section describes how an MCP client interacts with the CodeBeagle MCP server.

### Pattern 1: Simple Q&A ("What does this function do?")

```
Agent host workflow:
1. Connect to MCP server via stdio.
2. Call `list_locations` → learns available indexes.
3. Call `search_content(query="def calculate_risk", folder="C:/src/myproject", context_lines=5)`
4. Receives matches with context.
5. If a match looks interesting, read full file via `codebeagle://file/C%3A/...`
6. Synthesize answer.
```

**MCP conversation:**

```
Client:  Initialize (capabilities request)
Server:  Responds with tools: [search_content, search_filename, list_locations, ...]
         resources: [codebeagle://locations, codebeagle://file/{path}, ...]

Client:  tools/call { name: "search_content",
                      arguments: { query: "def calculate_risk", folder: "C:/src/myproject",
                                   context_lines: 5, limit: 10 } }
Server:  { content: [{ type: "text", text: "[{file: ..., line: 42, ...}]" }] }
```

### Pattern 2: Iterative Exploration

```
1. Broad search: `search_content(query="class Handler", limit=5)`
2. Read found files: `resource("codebeagle://file/C%3A/.../handler.py")`
3. Refined search: `search_content(query="class Handler *Factory", folder_filter="src/patterns")`
4. Paginate: `search_content_paginate(query=..., pageOffset={"fileIndex": 2, "matchIndex": 0})`
5. Read more files...
```

### Pattern 3: Batch Analysis (Agent Script)

An agent can pre-compute a map of the codebase by:

```python
# Pseudo-code
locations = await mcp.call_tool("list_locations")
all_py_files = []

for loc in locations:
    page = await mcp.call_tool("search_filename", {"query": "*.py", "location": loc["name"]})
    all_py_files.extend(page["files"])

    while "pageOffset" in page["meta"]:
        page = await mcp.call_tool("search_filename_paginate", {
            "query": "*.py",
            "location": loc["name"],
            "pageOffset": page["meta"]["pageOffset"]
        })
        all_py_files.extend(page["files"])
```

### Pattern 4: Natural Language Integration (via Claude Desktop / VS Code)

The user asks in natural language:

> "Find all places where we handle authentication and show me the relevant code."

The LLM agent:

1. Calls `get_prompt("search_codebase", {"goal": "Find authentication handling code"})`
   to load the search strategy.
2. Calls `search_content(query="authenticate * login", context_lines=5, limit=20)`.
3. Reads promising files via `codebeagle://file/...`.
4. Summarizes findings to the user.

---

## Authentication & Security

### Default Binding

The CodeBeagle HTTP API binds to `127.0.0.1:8080` by default. The MCP server connects to
this local endpoint. No network exposure.

### Token-Based Access (Optional)

If the MCP server is deployed with SSE transport (remote access), add a simple token:

```python
# In MCP server config
MCP_API_KEY = os.environ.get("CODEBEAGLE_MCP_KEY", "")

# The MCP server passes this as a header to the HTTP API:
headers = {"X-API-Key": MCP_API_KEY}
```

The CodeBeagle HTTP API would need to be extended to check this header (optional enhancement).

### Filesystem Access Control

The CodeBeagle HTTP API already respects index boundaries — it only searches within
configured locations. The MCP server inherits this restriction. No additional filesystem
filtering is needed.

---

## Error Handling & Edge Cases

### HTTP API Errors → MCP Tool Errors

| HTTP Status | MCP Error | Agent Guidance |
|-------------|-----------|---------------|
| 400 Bad Request | `InvalidParams` | Wrong field types or missing required fields. Check tool input schema. |
| 404 Not Found | `InvalidParams` with detail | Location or folder not indexed. Use `list_locations` to discover available locations. |
| 500 Internal Error | `InternalError` | Index corruption or database error. Suggest reindexing or check server logs. |

### Common Edge Cases

| Edge Case | Behaviour | Agent Handling |
|-----------|-----------|---------------|
| Empty query | 400 error | Always provide a non-empty `query`. |
| Query with no matches | Empty matches array, `totalFiles: 0` | Try broader terms or different location. |
| Query too broad (many matches) | `totalFiles` is capped, pagination cursor returned | Paginate or add more specific terms. |
| Invalid pageOffset | Server re-starts from beginning | The cursor is opaque; pass it exactly as received. |
| File deleted between search and read | 404 on resource read | Catch and report file not found. |
| Index out of date | Search misses new/changed files | Run `UpdateIndex.py` to refresh indexes. |
| Concurrent index updates | SQLite handles this safely | No special handling needed. |
| Very large file (>100k lines) | Reading may be slow | Use `search_content` with context_lines=0 for pinpointing, then read specific sections. |

---

## Performance Considerations

### Caching

The CodeBeagle HTTP API already caches:
- **File lists** per query → avoids re-running index search for paginated requests (5 min TTL).
- **File matches** per file → avoids re-scanning the same file for the same query (5 min TTL).

The MCP server adds an optional **result cache** to avoid duplicate tool calls with identical
parameters:

```python
class CodeBeagleMCPServer:
    def __init__(self):
        self._result_cache = {}  # key: (tool_name, frozenset(params.items()))
        self._cache_ttl = 60    # 60 seconds

    def _cached_or_call(self, key, fn):
        now = time.time()
        if key in self._result_cache:
            expires, result = self._result_cache[key]
            if now < expires:
                return result
        result = fn()
        self._result_cache[key] = (now + self._cache_ttl, result)
        return result
```

### Rate Limiting

The MCP server should not rate-limit — it talks to a local server. But if deployed with SSE,
consider a simple per-client rate limit to prevent abuse.

### Large Result Sets

- Content search default `limit` = 100 matches. This keeps response size manageable.
- For bulk analysis, the agent can paginate with `search_content_paginate`.
- Filename search default `limit` = 100 files, max 10 000.

### Streaming

MCP supports `TextContent` with arbitrary text. For very large result sets (>1000 matches),
consider returning a summary + pagination cursor rather than all matches at once.

---

## Implementation Steps

### Phase 1: MCP Server Skeleton

1. Create `mcp_server/` package with `__init__.py`, `__main__.py`, `server.py`.
2. Implement `CodeBeagleClient` — a thin HTTP client wrapping the existing `ai_agent/server.py` endpoints.
3. Implement `CodeBeagleMCPServer` with `list_locations`, `search_content`, `search_filename` tools.
4. Wire up stdio transport.
5. Test with `npx @modelcontextprotocol/inspector` or direct JSON-RPC calls.

### Phase 2: Pagination + Resources

6. Add `search_content_paginate` and `search_filename_paginate` tools.
7. Add `codebeagle://locations`, `codebeagle://file/{path}`, `codebeagle://search/{query}` resources.
8. Add `codebeagle://api-docs` resource.

### Phase 3: Prompt Templates

9. Add `search_codebase` and `find_references` prompt templates.
10. Write a `debug_issue` prompt for tracing bugs across files.

### Phase 4: SSE Transport (Optional)

11. Add `--sse` flag to start the server with SSE transport.
12. Implement optional API key authentication for SSE mode.
13. Add `AgentMCPServer` class (analogous to `AgentServer`) for lifecycle management.

### Phase 5: Integration & Packaging

14. Add `CodeBeagleMCP.pyw` entry point that starts both the HTTP API and the MCP server.
15. Create `setup.py` entry points for `codebeagle-mcp` console command.
16. Add standalone `CodeBeagleMCP.py` script (analogous to `CodeBeagleAgentServer.py`).
17. Document MCP usage in `help.html` and `README.md`.
18. Add `mcp_server/tests.py` with unit tests for the MCP layer (mocking the HTTP client).

### Phase 6: Client-side Testing

19. Test with Claude Desktop: add `"codebeagle": { "command": "python", "args": ["-m", "mcp_server"] }`
    to `claude_desktop_config.json`.
20. Test with VS Code Cline extension.
21. Test pagination with a large codebase to verify cursor handling.

---

## Appendices

### A. Sample Client Configuration

#### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "codebeagle": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "env": {
        "CODEBEAGLE_API_URL": "http://127.0.0.1:8080"
      }
    }
  }
}
```

#### VS Code (Cline / Continue extension)

```json
{
  "mcpServers": {
    "codebeagle": {
      "command": "python",
      "args": ["-m", "mcp_server"]
    }
  }
}
```

### B. Full MCP Tool Schema (Quick Reference)

```json
{
  "tools": [
    {
      "name": "list_locations",
      "description": "List configured search locations with folders and extensions.",
      "inputSchema": { "type": "object", "properties": {}, "required": [] }
    },
    {
      "name": "search_content",
      "description": "Search file contents with context lines.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": { "type": "string" },
          "folder": { "type": "string" },
          "location": { "type": "string" },
          "folder_filter": { "type": "string" },
          "extension_filter": { "type": "string" },
          "case_sensitive": { "type": "boolean" },
          "exclude_comments": { "type": "boolean" },
          "context_lines": { "type": "integer" },
          "limit": { "type": "integer" }
        },
        "required": ["query"]
      }
    },
    {
      "name": "search_content_paginate",
      "description": "Continue a paginated content search.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": { "type": "string" },
          "page_offset": { "type": "object" },
          "limit": { "type": "integer" }
        },
        "required": ["query", "page_offset"]
      }
    },
    {
      "name": "search_filename",
      "description": "Search file names with wildcard support.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": { "type": "string" },
          "folder": { "type": "string" },
          "location": { "type": "string" },
          "folder_filter": { "type": "string" },
          "extension_filter": { "type": "string" },
          "case_sensitive": { "type": "boolean" },
          "limit": { "type": "integer" }
        },
        "required": ["query"]
      }
    },
    {
      "name": "search_filename_paginate",
      "description": "Continue a paginated filename search.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": { "type": "string" },
          "page_offset": { "type": "object" },
          "limit": { "type": "integer" }
        },
        "required": ["query", "page_offset"]
      }
    }
  ],
  "resources": [
    {
      "uri": "codebeagle://locations",
      "name": "Search Locations",
      "mimeType": "application/json"
    },
    {
      "uri": "codebeagle://file/{path}",
      "name": "File Content",
      "mimeType": "text/plain"
    },
    {
      "uri": "codebeagle://search/{query}",
      "name": "Search Results Snapshot",
      "mimeType": "text/plain"
    },
    {
      "uri": "codebeagle://api-docs",
      "name": "API Documentation",
      "mimeType": "text/markdown"
    }
  ],
  "prompts": [
    {
      "name": "search_codebase",
      "description": "Guide the agent through a structured code search.",
      "arguments": [
        { "name": "goal", "description": "What to search for", "required": false }
      ]
    },
    {
      "name": "find_references",
      "description": "Find all references to a symbol.",
      "arguments": [
        { "name": "symbol", "description": "Symbol name", "required": true }
      ]
    }
  ]
}
```

### C. Relation to Existing Code

| Existing Module | Role | MCP Server Usage |
|-----------------|------|-----------------|
| `ai_agent/server.py` | HTTP API (port 8080) | MCP server calls this via HTTP. |
| `ai_agent/search_provider.py` | Qt-free search engine wrapper | Called by `server.py`. Not directly used by MCP server. |
| `ai_agent/data_model.py` | Data classes (ContentMatch, etc.) | MCP server reuses same JSON structure. |
| `ai_agent/API.md` | API documentation | Exposed as `codebeagle://api-docs` resource. |
| `ai_agent/AgentHistory.py` | API call history | MCP server could add its own history layer. |
| `ai_agent/ttl_cache.py` | TTL cache | MCP server can reuse for result caching. |
| `fulltextindex/` | Search engine | Accessed indirectly through the HTTP API. |
| `tools/ContextExtraction.py` | Line/context extraction | Already used by `search_provider.py`. |
| `AppConfig.py` | Configuration | MCP server reads `agent` config section for port/host. |
| `CodeBeagleAgentServer.py` | Standalone HTTP server | MCP server runs alongside or wraps this. |

---

*This plan is a living document. As the MCP protocol evolves and new patterns emerge,
update the tool definitions and prompts accordingly.*