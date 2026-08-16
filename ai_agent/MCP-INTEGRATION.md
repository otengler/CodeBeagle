# MCP Integration Plan for CodeBeagle

This document describes how an MCP (Model Context Protocol) capable AI agent can discover,
consume, and integrate CodeBeagle's search API. It covers the MCP server wrapper, tool/resource
definitions, client consumption patterns, and implementation guidance.

**Status:** The MCP server (Phase 1 and the pagination part of Phase 2) is implemented and
tested. Sections marked *Planned* describe functionality that is designed but not yet built.

---

## Table of Contents

1. [Overview](#overview)
2. [MCP Concepts Applied to CodeBeagle](#mcp-concepts-applied-to-codebeagle)
3. [Architecture](#architecture)
4. [MCP Server Implementation](#mcp-server-implementation)
5. [Tool Definitions](#tool-definitions)
6. [Resource Definitions](#resource-definitions) *(Planned)*
7. [Prompt Templates](#prompt-templates) *(Planned)*
8. [Client Consumption Patterns](#client-consumption-patterns)
9. [Authentication & Security](#authentication--security)
10. [Error Handling & Edge Cases](#error-handling--edge-cases)
11. [Performance Considerations](#performance-considerations)
12. [Implementation Status](#implementation-status)

---

## Overview

CodeBeagle exposes a local HTTP API (`ai_agent/Server.py`) for content and filename
search. The MCP server (`ai_agent/mcp_server/`) wraps this API into the **Model Context
Protocol** so any MCP-compatible agent client (Claude Desktop, VS Code extensions,
custom agents, etc.) can use CodeBeagle as a tool without writing HTTP-level code.

### What MCP Provides

- **Tool discovery** – The client asks "what can you do?" and gets typed schemas.
- **Resource access** – The client reads files or search result sets via URI addressing. *(Planned)*
- **Prompt templates** – Pre-crafted prompt snippets for common search workflows. *(Planned)*
- **Structured I/O** – JSON Schema typed inputs/outputs enforced by the protocol.
- **Transports** – Stdio (implemented) or SSE (planned, for remote).

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
               │  MCP Protocol (JSON-RPC over stdio)
               ▼
┌──────────────────────────────────────────────────────┐
│              CodeBeagle MCP Server                   │
│  ┌───────────────────────────────────────────────┐   │
│  │  MCP Transport Layer (stdio)                  │   │
│  │  - ListTools, CallTool                        │   │
│  └──────────────┬────────────────────────────────┘   │
│                 │  HTTP client (localhost:8080)      │
│  ┌──────────────▼────────────────────────────────┐   │
│  │  CodeBeagle HTTP API (ai_agent/Server.py)     │   │
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

---

## MCP Server Implementation

### Approach: Python MCP SDK

Implemented with the official [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk)
(`mcp >= 2.0`, installed in `.venv`). The server talks to the local CodeBeagle HTTP API
(`ai_agent/Server.py`) through `CodeBeagleClient` and registers three tools.

**File structure (as implemented):**

```
mcp_server/
├── __init__.py              # Public API re-exports (CodeBeagleMCPServer, resolveBaseUrl, ...)
├── server.py                # MCP server creation, tool registry, transport
├── client.py                # HTTP client to CodeBeagle's local API (urllib-based)
├── types.py                 # Pydantic input models; double as JSON Schemas for tools
├── config.py                # Base URL resolution (env var, JSON file, AppConfig, default)
└── tests.py                 # Unit tests for config, client, input types, and the server

CodeBeagleMCP.py             # Standalone stdio entry point (repo root)
```

Notes on the implementation:

- **Tool registration** uses the low-level handler API (`on_list_tools` / `on_call_tool`
  constructor parameters) with a `ToolDef` registry instead of the `@server.tool()`
  decorator. Each registry entry carries the pydantic input model, the description, and
  the handler; the dispatch validates arguments against the model and passes the
  validated instance to the handler.
- **`InitializationOptions` is built manually** (`_buildCapabilities()`) rather than via
  `create_initialization_options()`. The SDK always sets `experimental={}` there, which
  makes the MCP Inspector show *"Experimental"* as a capability even though nothing
  experimental is offered. Leaving the field unset drops it from the wire.
- **`types.py` input models** use snake_case field names; `toHttpParams()` translates them
  to the camelCase names expected by the HTTP API and drops `None` values.

### Server Skeleton (as implemented)

```python
# ai_agent/mcp_server/server.py
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp_types import ServerCapabilities, ToolsCapability

class CodeBeagleMCPServer:
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

def _buildCapabilities() -> ServerCapabilities:
    """Capabilities without the empty `experimental` dict (see note above)."""
    return ServerCapabilities(tools=ToolsCapability(list_changed=False))

async def runStdioServer(baseUrl: str) -> None:
    mcpServer = CodeBeagleMCPServer(baseUrl)
    initializationOptions = InitializationOptions(
        server_name=mcpServer.server.name,
        server_version=mcpServer.server.version,
        description=mcpServer.server.description,
        capabilities=_buildCapabilities(),
    )
    async with stdio_server() as (readStream, writeStream):
        await mcpServer.server.run(readStream, writeStream, initializationOptions)
```

### Base URL Resolution (`config.py`)

`resolveBaseUrl()` resolves the HTTP API endpoint with this precedence:

1. `CODEBEAGLE_API_URL` environment variable.
2. `codebeagle.json` next to the package or in the application directory
   (`{"baseUrl": "http://127.0.0.1:8080"}`).
3. The `agent` section of the CodeBeagle configuration, if the agent server is enabled
   there (bind host + port).
4. `http://127.0.0.1:8080` (default).

---

## Tool Definitions

Each tool maps to one or more HTTP API calls. All tools expose **typed JSON Schema inputs**
so the AI agent knows exactly what parameters are valid.

### Tool 1: `search_content`

Searches file contents and returns matches with context lines.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | – (required) | Search expression: keywords (`createNode ( CComVariant`), trailing wildcards (`Fact*`), unknown-word gaps (`error **2 network`), regex (`code <!\d+!>`). |
| `folder` | string | – | Root folder path to search in. Server resolves the best matching index. Mutually exclusive with `location`. |
| `location` | string | – | Named search location (from `list_locations`). Mutually exclusive with `folder`. |
| `folder_filter` | string | – | Comma-separated folder patterns, `-` prefix excludes (`test, -test/mock`). |
| `extension_filter` | string | – | Comma-separated extensions, `-` prefix excludes (`.py, .js, -test.py`). |
| `case_sensitive` | boolean | false | Case-sensitive matching. |
| `exclude_comments` | boolean | true | Exclude matches inside comments. |
| `context_lines` | integer | 2 | Context lines before/after each match (0–20). |
| `limit` | integer | 100 | Maximum number of matches (1–10000). |
| `page_offset` | object | – | Pagination cursor from a previous response (`{"fileIndex": int, "matchIndex": int?}`). |
| `format` | string | json | `json` (full response) or `compact` (`path:line: full matching line`, no context). |

**Return value** — JSON object with `totalFiles`, `matches` (file, line, fullLine, optional
matchText/contextBefore/contextAfter), and a `pageOffset` cursor when more results exist.

### Tool 2: `search_filename`

Searches file names with wildcard support.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | – (required) | File name pattern with `*` and `?` wildcards (`Factory*`, `*test*.py`). A trailing dot-part becomes an extension filter. |
| `folder` / `location` | string | – | As for `search_content`. |
| `folder_filter` / `extension_filter` | string | – | As for `search_content`. |
| `case_sensitive` | boolean | false | Case-sensitive matching. |
| `limit` | integer | 100 | Maximum number of files (1–10000). |
| `page_offset` | object | – | Pagination cursor (`{"fileIndex": int}`). |
| `format` | string | json | `json` (full response) or `compact` (one file path per line). |

**Return value** — JSON object with `totalFiles`, `files` (full paths), and a `pageOffset`
cursor when more results exist.

### Tool 3: `list_locations`

Discovers available search locations. No parameters.

**Return value:**

```json
{
  "locations": [
    {
      "name": "myproject",
      "folders": ["C:/src/myproject"],
      "extensions": [".py", ".js", ".ts", ".cpp"],
      "indexMode": "filenameAndContent"
    }
  ]
}
```

### Pagination Design

The plan originally proposed two tools per search endpoint (`search_content` +
`search_content_paginate`). **The single-tool alternative was implemented instead:**
`search_content` / `search_filename` take an optional `page_offset` parameter.

The agent client decides when to paginate: it calls `search_content`, inspects the result
for a `pageOffset`, and passes that cursor back as `page_offset` on a subsequent call.

```
page 1 → search_content(query=..., limit=100)
         returns { ..., "pageOffset": {"fileIndex": 1, "matchIndex": 0} }
page 2 → search_content(query=..., limit=100,
                        page_offset={"fileIndex": 1, "matchIndex": 0})
```

Rationale for the single-tool design:

- Keeps the tool list small; no duplication of every search option across two tools.
- The cursor is opaque — the agent just echoes back the `pageOffset` object it received.
- `CallTool` stays stateless; the cursor is passed explicitly, never stored server-side.

The two-tools-per-endpoint variant remains valid and can be added later if agent clients
benefit from the clearer intent in conversation history.

---

## Resource Definitions *(Planned — not yet implemented)*

MCP resources let the agent read data via URI — useful for fetching file contents or
pre-computed search result sets without re-running searches. When implemented, the MCP
server must advertise the `resources` capability (`ServerCapabilities(resources=...)`) and
serve the following URIs:

### Resource `codebeagle://locations`

Returns the list of all configured search locations.

### Resource `codebeagle://file/{path}`

Returns the full text content of a file. The path is URL-encoded.

**Usage by agent:**

```
Read file: codebeagle://file/C%3A/src/myproject/main.py
```

### Resource Template `codebeagle://search/{query}`

Exposes top search results as a resource. The agent can reference this URI to get a
snapshot of search results without an explicit tool call.

### Resource `codebeagle://api-docs`

Returns the full API.md documentation as a resource the agent can reference.

---

## Prompt Templates *(Planned — not yet implemented)*

MCP prompts are pre-crafted message templates that guide the AI agent on how to use the
tools effectively. When implemented, the MCP server must advertise the `prompts`
capability and serve the following templates:

### Prompt `search_codebase`

Guides the agent through a structured code search workflow. Workflow sketch:

1. **Discover** — Call `list_locations` to see which code indexes are available,
   or use the `folder` parameter directly with your project root.
2. **Search broadly** — Use `search_content` with broad keywords.
3. **Refine** — Use `folder_filter` / `extension_filter` to narrow.
4. **Read context** — Read interesting files in full (future `codebeagle://file/{path}`).
5. **Paginate** — If the response includes a `pageOffset`, pass it back as `page_offset`.

### Prompt `find_references`

Specialized for finding all references to a symbol. Sketch:

1. `search_content(query="<symbol>", context_lines=1, limit=200)`.
2. Paginate with `page_offset` if there are many results.
3. Group results by file; optionally search imports (`import **2 <symbol>`).
4. Read key files via `codebeagle://file/{path}` (future resource).

The `totalFiles` field in the response tells you how many files contain the symbol.

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
5. If a match looks interesting, read the file (future `codebeagle://file/C%3A/...`).
6. Synthesize answer.
```

**MCP conversation:**

```
Client:  Initialize (capabilities request)
Server:  Responds with tools: [list_locations, search_content, search_filename]

Client:  tools/call { name: "search_content",
                      arguments: { query: "def calculate_risk", folder: "C:/src/myproject",
                                   context_lines: 5, limit: 10 } }
Server:  { content: [{ type: "text", text: "{\"totalFiles\": ..., \"matches\": [...]}" }] }
```

### Pattern 2: Iterative Exploration with Pagination

```
1. Broad search: `search_content(query="class Handler", limit=5)`
2. Refined search: `search_content(query="class Handler *Factory", folder_filter="src/patterns")`
3. If the response contains a pageOffset, fetch the next page:
   `search_content(query="class Handler *Factory", folder_filter="src/patterns",
                   page_offset={"fileIndex": 2, "matchIndex": 0})`
4. Repeat until no pageOffset is returned (or totalFiles reached).
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

    while "pageOffset" in page:
        page = await mcp.call_tool("search_filename", {
            "query": "*.py",
            "location": loc["name"],
            "page_offset": page["pageOffset"]
        })
        all_py_files.extend(page["files"])
```

### Pattern 4: Natural Language Integration (via Claude Desktop / VS Code)

The user asks in natural language:

> "Find all places where we handle authentication and show me the relevant code."

The LLM agent:

1. Calls `list_locations` to discover the available indexes.
2. Calls `search_content(query="authenticate * login", context_lines=5, limit=20)`.
3. Paginates with `page_offset` if needed.
4. Reads promising files (future `codebeagle://file/...`).
5. Summarizes findings to the user.

---

## Authentication & Security

### Default Binding

The CodeBeagle HTTP API binds to `127.0.0.1:8080` by default. The MCP server connects to
this local endpoint. No network exposure.

### Token-Based Access *(Planned)*

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

### HTTP API Errors → MCP Tool Errors (as implemented)

The MCP server catches HTTP API errors and returns them as MCP tool errors with guidance:

| HTTP Status | MCP Error | Agent Guidance |
|-------------|-----------|---------------|
| 400 Bad Request | Tool error (`is_error: true`) | "Invalid parameters: ..." — wrong field types or missing required fields. |
| 404 Not Found | Tool error (`is_error: true`) | "Location or folder not indexed: ... Call list_locations to discover the available search locations." |
| Server unreachable | Tool error (`is_error: true`) | "CodeBeagle agent server not reachable ... Start the CodeBeagle GUI with the 'AI agent' server enabled or run CodeBeagleAgentServer." |
| 500 Internal Error | Tool error (`is_error: true`) | "CodeBeagle API error 500: ..." |

Parameter validation errors (pydantic) are mapped to "Invalid parameters: <field>: <msg>".

### Common Edge Cases

| Edge Case | Behaviour | Agent Handling |
|-----------|-----------|---------------|
| Empty query | 400 error | Always provide a non-empty `query`. |
| Query with no matches | Empty matches array, `totalFiles: 0` | Try broader terms or different location. |
| Query too broad (many matches) | `totalFiles` is capped, pagination cursor returned | Paginate with `page_offset` or add more specific terms. |
| Invalid pageOffset | Server re-starts from beginning | The cursor is opaque; pass it exactly as received. |
| File deleted between search and read | 404 on resource read *(future)* | Catch and report file not found. |
| Index out of date | Search misses new/changed files | Run `UpdateIndex.py` to refresh indexes. |
| Concurrent index updates | SQLite handles this safely | No special handling needed. |
| Very large file (>100k lines) | Reading may be slow | Use `search_content` with context_lines=0 for pinpointing, then read specific sections. |

---

## Performance Considerations

### Caching

The CodeBeagle HTTP API already caches:
- **File lists** per query → avoids re-running index search for paginated requests (5 min TTL).
- **File matches** per file → avoids re-scanning the same file for the same query (5 min TTL).

An optional **result cache** in the MCP server to avoid duplicate tool calls with identical
parameters is still possible but not implemented (the HTTP layer cache usually suffices):

```python
class CodeBeagleMCPServer:
    def __init__(self):
        self._result_cache = {}  # key: (tool_name, frozenset(params.items()))
        self._cache_ttl = 60    # 60 seconds
```

### Rate Limiting

The MCP server should not rate-limit — it talks to a local server. But if deployed with SSE
*(planned)*, consider a simple per-client rate limit to prevent abuse.

### Large Result Sets

- Content search default `limit` = 100 matches. This keeps response size manageable.
- For bulk analysis, the agent can paginate by passing `page_offset` back.
- Filename search default `limit` = 100 files, max 10 000.

### Streaming

MCP supports `TextContent` with arbitrary text. For very large result sets (>1000 matches),
consider returning a summary + pagination cursor rather than all matches at once.

---

## Implementation Status

### Phase 1: MCP Server Skeleton — **Done**

- [x] `mcp_server/` package with `__init__.py`, `server.py`, `client.py`, `types.py`, `config.py`.
- [x] `CodeBeagleClient` — thin HTTP client (urllib) wrapping the `ai_agent/Server.py` endpoints.
- [x] `CodeBeagleMCPServer` with `list_locations`, `search_content`, `search_filename` tools.
- [x] Stdio transport (`runStdioServer`, `CodeBeagleMCP.py` entry point).
- [x] Tested with `npx @modelcontextprotocol/inspector` and unit tests.
- [x] `InitializationOptions` built manually — no spurious `experimental` capability.

### Phase 2: Pagination + Resources — **Partially done**

- [x] Pagination via `page_offset` parameter on `search_content` / `search_filename`
      (single-tool design; see [Pagination Design](#pagination-design)).
- [ ] `codebeagle://locations`, `codebeagle://file/{path}`, `codebeagle://search/{query}` resources.
- [ ] `codebeagle://api-docs` resource.

### MVP Scope (recommendation)

The MCP part should be **usable but not bloated**. Analysis of what is worth building
for an MVP (current state: three tools + pagination are implemented and tested):

**Recommended scope: tools-only — no resources, no prompts.**

| Planned item | Build for MVP? | Rationale |
|--------------|----------------|-----------|
| `codebeagle://file/{path}` | Optional | Coding agents (Claude, Cursor, VS Code extensions) read files natively, so this competes with a capability the client already has. Would require a new HTTP endpoint with location-boundary validation (medium effort) for limited unique value. Reconsider only if real client testing shows `context_lines` is not enough. |
| `codebeagle://locations` | No | Duplicates the `list_locations` tool. |
| `codebeagle://search/{query}` | No | A non-paginatable result snapshot; `search_content` does it better and supports pagination. |
| `codebeagle://api-docs` | No | Documents the *HTTP* API, which MCP clients never call directly; the tools are the interface. |
| Prompt templates | No | Tool descriptions already embed the search workflow guidance. Advertises an extra capability (`prompts`) for marginal benefit. If only one is ever wanted, `search_codebase` suffices. |

**On "prompts as resources"**: MCP prompts are their own capability (and newer protocol
revisions model prompt templates as resources with a prompt content type). Neither is
needed for the MVP — the LLM learns the workflow from the tool descriptions
(`list_locations` → `search_content` → paginate via `page_offset`) without server-side
prompts. Skip; revisit only if a specific client does not surface tool descriptions well.

**Kept because they are cheap and already paid off:** the `format=compact` output
(`path:line: full matching line`) which keeps token usage low for large result sets.

If the scope later grows, `codebeagle://file/{path}` is the single most valuable
addition (needs a new `GET /api/v1/file?path=...` HTTP endpoint that validates the
path against the configured search locations before the MCP resource is added).

### Phase 3: Prompt Templates — **Not started**

- [ ] `search_codebase` and `find_references` prompt templates.
- [ ] A `debug_issue` prompt for tracing bugs across files.

### Phase 4: SSE Transport (Currently out of scope) — **Not started**

- [ ] `--sse` flag to start the server with SSE transport.
- [ ] Optional API key authentication for SSE mode.
- [ ] `AgentMCPServer` class (analogous to `AgentServer`) for lifecycle management.

### Phase 5: Integration & Packaging — **Done**

- [x] Standalone `CodeBeagleMCP.py` script (analogous to `CodeBeagleAgentServer.py`).
- [x] `CodeBeagleMCP` executable target in `setup.py` (built by the freeze scripts).
- [x] `mcp_server/tests.py` with unit tests for the MCP layer (mocking the HTTP client).
- [ ] Document MCP usage in `help.html` and `README.md`.

### Phase 6: Client-side Testing — **Not started**

- [ ] Test with Claude Desktop: add `"codebeagle": { "command": "CodeBeagleMCP" }`
      to `claude_desktop_config.json`.
- [ ] Test with VS Code Cline extension.
- [ ] Test pagination with a large codebase to verify cursor handling.

---

## Appendices

### A. Sample Client Configuration

#### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "codebeagle": {
      "command": "CodeBeagleMCP"
    }
  }
}
```

When running from a source tree instead of the distribution use:

```json
{
  "mcpServers": {
    "codebeagle": {
      "command": "python",
      "args": ["CodeBeagleMCP.py"],
      "env": {
        "CODEBEAGLE_API_URL": "http://127.0.0.1:8080"
      }
    }
  }
}
```

`CODEBEAGLE_API_URL` is optional — without it the server falls back to the CodeBeagle
settings or the default port (see [Base URL Resolution](#base-url-resolution-configpy)).

#### VS Code (Cline / Continue extension)

```json
{
  "mcpServers": {
    "codebeagle": {
      "command": "CodeBeagleMCP"
    }
  }
}
```

### B. Full MCP Tool Schema (Quick Reference, as implemented)

The `search_content` / `search_filename` input schemas are generated from the pydantic
models in `types.py`; `page_offset` serialises as `object` with integer
`additionalProperties` (plus `null`, since it is optional).

```json
{
  "tools": [
    {
      "name": "list_locations",
      "description": "List all configured CodeBeagle search locations (indexes): name, folders, extensions and index mode. Call this first to discover what is searchable, then pass the location name to search_content / search_filename.",
      "inputSchema": { "type": "object", "properties": {}, "required": [] }
    },
    {
      "name": "search_content",
      "description": "Full-text search across CodeBeagle-indexed source code. Query syntax: keywords ('createNode ( CComVariant'), trailing wildcards ('Fact*'), unknown-word gaps ('error **2 network'), regex ('code <!\\d+!>'). Specify either 'location' (name from list_locations) or 'folder' (root path; the server resolves the best matching index). Returns matching lines with surrounding context and a pageOffset if more results exist; pass that pageOffset back as the page_offset parameter to fetch the next page. Set format='json' (default) for the full JSON response or format='compact' for 'path:line: full matching line' output (no context lines).",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": { "type": "string" },
          "folder": { "type": "string" },
          "location": { "type": "string" },
          "folder_filter": { "type": "string" },
          "extension_filter": { "type": "string" },
          "case_sensitive": { "type": "boolean", "default": false },
          "exclude_comments": { "type": "boolean", "default": true },
          "context_lines": { "type": "integer", "default": 2, "minimum": 0, "maximum": 20 },
          "limit": { "type": "integer", "default": 100, "minimum": 1, "maximum": 10000 },
          "page_offset": { "type": "object", "additionalProperties": { "type": "integer" } },
          "format": { "enum": ["json", "compact"] }
        },
        "required": ["query"]
      }
    },
    {
      "name": "search_filename",
      "description": "Search for files by name across CodeBeagle-indexed source code. The query supports * and ? wildcards ('Factory*', '*test*.py', 'Makefile'). If the query contains a dot, the part after the last dot is used as an extension filter. Returns full file paths and a pageOffset if more results exist; pass that pageOffset back as the page_offset parameter to fetch the next page. Set format='json' (default) for the full JSON response or format='compact' for one file path per line.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": { "type": "string" },
          "folder": { "type": "string" },
          "location": { "type": "string" },
          "folder_filter": { "type": "string" },
          "extension_filter": { "type": "string" },
          "case_sensitive": { "type": "boolean", "default": false },
          "limit": { "type": "integer", "default": 100, "minimum": 1, "maximum": 10000 },
          "page_offset": { "type": "object", "additionalProperties": { "type": "integer" } },
          "format": { "enum": ["json", "compact"] }
        },
        "required": ["query"]
      }
    }
  ]
}
```

Resources and prompts (see [Resource Definitions](#resource-definitions) and
[Prompt Templates](#prompt-templates)) are not yet advertised.

### C. Relation to Existing Code

| Existing Module | Role | MCP Server Usage |
|-----------------|------|-----------------|
| `ai_agent/Server.py` | HTTP API (port 8080) | MCP server calls this via HTTP (`CodeBeagleClient`). |
| `ai_agent/SearchProvider.py` | Qt-free search engine wrapper | Called by `Server.py`. Not directly used by MCP server. |
| `ai_agent/DataModel.py` | Data classes (ContentMatch, ContentSearchResult, ...) | MCP server reuses the same JSON structure. |
| `ai_agent/API.md` | API documentation | Candidate for `codebeagle://api-docs` resource *(planned)*. |
| `ai_agent/AgentHistory.py` | API call history | MCP server could add its own history layer *(planned)*. |
| `ai_agent/TtlCache.py` | TTL cache | Used by `Server.py` for file list / match caches; MCP server could reuse for result caching *(planned)*. |
| `fulltextindex/` | Search engine | Accessed indirectly through the HTTP API. |
| `tools/ContextExtraction.py` | Line/context extraction | Already used by `SearchProvider.py`. |
| `AppConfig.py` | Configuration | `config.py` reads the `agent` section for port/host fallback. |
| `CodeBeagleAgentServer.py` | Standalone HTTP server | MCP server requires it (or the GUI's agent server) to be running. |

---

*This plan is a living document. As the MCP protocol evolves and new patterns emerge,
update the tool definitions and prompts accordingly.*
