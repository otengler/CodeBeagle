# PI Agent — CodeBeagle API Integration Plan

## 1. Overview

The PI coding agent can consume CodeBeagle's search engine via a **PI extension** (TypeScript) that registers **custom tools** callable by the LLM.

**No Python bridge is needed.** CodeBeagle already ships a local HTTP web API in `ai_agent/server.py` (`AgentHTTPServer` → `SearchProvider` → `fulltextindex`). The PI extension simply calls these existing HTTP endpoints from TypeScript using `fetch()`. This removes the need for a stdin/stdout subprocess bridge entirely.

---

## 2. Architecture

```
User prompt: "Find all usages of createNode with CComVariant"
  │
  ▼
PI Agent (LLM decides to call codebeagle_search tool)
  │
  ▼
PI Extension (TypeScript) ─── codebeagle.ts
  │  ┌───────────────────────────────────┐
  │  │ pi.registerTool("codebeagle_..")  │
  │  │ fetch() → http://127.0.0.1:8080   │
  │  │ AbortSignal for cancellation      │
  │  └───────────────────────────────────┘
  │
  ▼
CodeBeagle HTTP Web API (ai_agent/server.py) — already exists
  │  ┌───────────────────────────────────┐
  │  │ GET  /api/v1/health               │
  │  │ GET  /api/v1/locations            │
  │  │ POST /api/v1/search/content       │
  │  │ POST /api/v1/search/filename      │
  │  └───────────────────────────────────┘
  │
  ▼
SearchProvider (ai_agent/search_provider.py) — Qt-free wrapper
  │  caching, pagination, context lines
  ▼
fulltextindex/ — SQLite-based full-text engine (no PyQt)
```

---

## 3. Existing HTTP API (no new server code required)

Server config lives in `config.txt` / `UserConfig.txt` under the `agent` section
(`enabled`, `port` = 8080, `bind` = 127.0.0.1). Full docs in `ai_agent/API.md`.

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/health` | GET | Liveness check |
| `/api/v1/locations` | GET | List configured search locations (name, folders, extensions, indexMode) |
| `/api/v1/search/content` | POST | Full-text content search with context lines |
| `/api/v1/search/filename` | POST | File name search with `*`/`?` wildcards |

Both search endpoints support `location` **or** `folder`, `folderFilter`, `extensionFilter`,
`caseSensitive`, `limit` (default 100) and return a `pageOffset` cursor for pagination.

**Key request fields:**

```json
{
  "query": "createNode ( CComVariant",
  "folder": "C:\\src\\project",
  "contextLines": 2,
  "limit": 100
}
```

**Key response fields:**

```json
{
  "totalFiles": 42,
  "pageOffset": {"fileIndex": 4, "matchIndex": 3},
  "matches": [
    {
      "file": "C:/src/project/src/main.cpp",
      "line": 45,
      "matchText": "createNode ( CComVariant",
      "fullLine": "CComVariant v = createNode ( CComVariant ...",
      "contextBefore": ["..."],
      "contextAfter": ["..."]
    }
  ]
}
```

---

## 4. Tools to Register

Each tool maps 1:1 to an existing HTTP endpoint.

### 4.1 `codebeagle_search` — Full-text content search → `POST /api/v1/search/content`

| Parameter | Type | Required | Description |
|---|---|---|---|
| `query` | string or string[] | yes | CodeBeagle query syntax: `keyword`, `keyword*` (wildcard), `<!regex!>` (regex), `**N` (N unknown words), `#ifdef`. Pass a list for OR logic: files matching ANY expression are returned. |
| `location` | string | no | Search location name (from `codebeagle_list_indexes`). Mutually exclusive with `folder`. |
| `folder` | string | no | Root folder to search in; server resolves best matching index |
| `folderFilter` | string | no | Folder include/exclude, e.g. `"src/, -test/"` |
| `extensionFilter` | string | no | Extension filter, e.g. `".cpp,.h,-.hpp"` |
| `caseSensitive` | boolean | no | Default: false |
| `contextLines` | integer | no | Context lines around each match (default 2). Set to 0 for compact output (matches returned as `"path:line: full matching line"` strings) |
| `limit` | integer | no | Max matches per page (default 100) |
| `pageOffset` | object | no | Opaque cursor from a previous response |

**Returns:** Matches with file path, line number, match text, full line, context. Plus `pageOffset` if more results exist.

### 4.2 `codebeagle_search_files` — File name search → `POST /api/v1/search/filename`

| Parameter | Type | Required | Description |
|---|---|---|---|
| `query` | string or string[] | yes | File name pattern or list of patterns (OR logic), supports `*` and `?` |
| `location` | string | no | Search location name |
| `folder` | string | no | Root folder |
| `folderFilter` | string | no | Folder filter |
| `extensionFilter` | string | no | Extension filter |
| `caseSensitive` | boolean | no | Default: false |
| `limit` | integer | no | Max files per page (default 100) |
| `pageOffset` | object | no | Opaque cursor |

**Returns:** List of matching file paths + `pageOffset`.

### 4.3 `codebeagle_list_indexes` — List search locations → `GET /api/v1/locations`

| Parameter | Type | Required | Description |
|---|---|---|---|
| *(none)* | | | |

**Returns:** Location name, folders, extensions, index mode. The LLM should call this first to discover what's searchable.

### 4.4 `codebeagle_health` — Check server availability → `GET /health`

| Parameter | Type | Required | Description |
|---|---|---|---|
| *(none)* | | | |

**Returns:** `{ "status": "ok" }` or a clear error telling the user the CodeBeagle agent server is not running.

---

## 5. PI Extension Skeleton (TypeScript)

Location: `.pi/extensions/codebeagle.ts` (project-local) or `~/.pi/agent/extensions/` (global)

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

const BASE_URL = process.env.CODEBEAGLE_API_URL ?? "http://127.0.0.1:8080";

// Thin HTTP client for the existing CodeBeagle web API
async function callApi(
  path: string,
  method: "GET" | "POST",
  body?: object,
  signal?: AbortSignal
): Promise<any> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
    signal,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error ?? `HTTP ${res.status} from ${path}`);
  }
  return data;
}

export default function (pi: ExtensionAPI) {
  // Register tool: codebeagle_search (maps to POST /api/v1/search/content)
  pi.registerTool({
    name: "codebeagle_search",
    label: "CodeBeagle: Search Content",
    description:
      "Full-text search across indexed source code. " +
      "Supports keywords, wildcards (key*), regex (<!re!>), unknown word gaps (**N), " +
      "folder/extension filters, and returns lines with surrounding context. " +
      "Uses CodeBeagle's SQLite-based full-text index engine.",
    parameters: Type.Object({
      query: Type.String({
        description: "Search query. Examples: 'malloc', 'createNode ( CComVariant', 'error **5 <!\\d+!>'",
      }),
      location: Type.Optional(Type.String({ description: "Search location name (see codebeagle_list_indexes). Mutually exclusive with folder." })),
      folder: Type.Optional(Type.String({ description: "Root folder path; server resolves the best matching index. Mutually exclusive with location." })),
      folderFilter: Type.Optional(Type.String({ description: "Folder filter: 'src/, -test/'" })),
      extensionFilter: Type.Optional(Type.String({ description: "Extension filter: '.cpp,.h,-.hpp'" })),
      caseSensitive: Type.Optional(Type.Boolean({ description: "Case sensitive search (default: false)" })),
      contextLines: Type.Optional(Type.Integer({ description: "Context lines before/after each match (default 2)" })),
      limit: Type.Optional(Type.Integer({ description: "Max matches per page (default 100)" })),
      pageOffset: Type.Optional(Type.Object({}, { description: "Opaque pagination cursor from a previous response" })),
    }),
    async execute(_toolCallId, params, signal, _onUpdate, ctx) {
      const result = await callApi("/api/v1/search/content", "POST", params, signal);
      const text = result.matches
        .map((m: any) => `${m.file}:${m.line}: ${m.fullLine}`)
        .join("\n");
      return {
        content: [
          {
            type: "text",
            text:
              `Found ${result.totalFiles} files with matches (showing ${result.matches.length}):\n\n` +
              text +
              (result.pageOffset ? `\n\nMore results available. Pass pageOffset=${JSON.stringify(result.pageOffset)} to codebeagle_search for the next page.` : ""),
          },
        ],
        details: result,
      };
    },
  });

  // Register tool: codebeagle_search_files (maps to POST /api/v1/search/filename)
  pi.registerTool({
    name: "codebeagle_search_files",
    label: "CodeBeagle: Search File Names",
    description: "Search for files by name across indexed source code. Supports * and ? wildcards.",
    parameters: Type.Object({
      query: Type.String({ description: "File name pattern, e.g. 'main*', '*test*.py', 'Makefile'" }),
      location: Type.Optional(Type.String({ description: "Search location name" })),
      folder: Type.Optional(Type.String({ description: "Root folder path" })),
      folderFilter: Type.Optional(Type.String({ description: "Folder filter" })),
      extensionFilter: Type.Optional(Type.String({ description: "Extension filter" })),
      caseSensitive: Type.Optional(Type.Boolean({ description: "Case sensitive (default: false)" })),
      limit: Type.Optional(Type.Integer({ description: "Max files per page (default 100)" })),
      pageOffset: Type.Optional(Type.Object({}, { description: "Opaque pagination cursor" })),
    }),
    async execute(_toolCallId, params, signal) {
      const result = await callApi("/api/v1/search/filename", "POST", params, signal);
      return {
        content: [
          {
            type: "text",
            text:
              `Found ${result.totalFiles} matching files (showing ${result.files.length}):\n\n` +
              result.files.join("\n") +
              (result.pageOffset ? `\n\nMore results available. Pass pageOffset=${JSON.stringify(result.pageOffset)} to codebeagle_search_files for the next page.` : ""),
          },
        ],
        details: result,
      };
    },
  });

  // Register tool: codebeagle_list_indexes (maps to GET /api/v1/locations)
  pi.registerTool({
    name: "codebeagle_list_indexes",
    label: "CodeBeagle: List Search Locations",
    description: "List all available CodeBeagle search locations (indexes). Call this first to discover what is searchable.",
    parameters: Type.Object({}),
    async execute() {
      const result = await callApi("/api/v1/locations", "GET");
      const text = result.locations
        .map((loc: any) => `- ${loc.name}: ${loc.folders.join(", ")} [${loc.extensions.join(", ")}] (${loc.indexMode})`)
        .join("\n");
      return {
        content: [{ type: "text", text: `Available search locations:\n${text}` }],
        details: result,
      };
    },
  });

  // Register tool: codebeagle_health (maps to GET /health)
  pi.registerTool({
    name: "codebeagle_health",
    label: "CodeBeagle: Server Health",
    description: "Check whether the CodeBeagle agent server is running and reachable.",
    parameters: Type.Object({}),
    async execute() {
      const result = await callApi("/health", "GET");
      return {
        content: [{ type: "text", text: `CodeBeagle agent server: ${JSON.stringify(result)}` }],
        details: result,
      };
    },
  });
}
```

**Cancellation:** pass `signal` (from `ctx.signal`) to `fetch()` — PI's Esc/abort propagates to the HTTP request automatically.

---

## 6. Server Lifecycle

The HTTP server is **not** spawned by the extension — it is owned by CodeBeagle:

- **Inside the CodeBeagle GUI** — `AgentServer.start()` runs the HTTP server in a daemon thread when `agent.enabled = true` in config.
- **Standalone** — `CodeBeagleAgentServer.py` starts the server without the GUI (mentioned in `MCP-INTEGRATION.md` appendix).

The extension must therefore:

1. On first tool call, hit `/health` (or let the first request fail with a clear message).
2. If unreachable, return a tool error telling the user: *"Start the CodeBeagle agent server (enable `agent` in config or run CodeBeagleAgentServer.py)."*

---

## 7. Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| **Transport** | Plain HTTP via `fetch()` | The web API in `ai_agent/server.py` already exists; no bridge to build/maintain |
| **Server lifecycle** | Managed by CodeBeagle, checked by extension | Extension only verifies `/health` and reports a clear error if down |
| **Cancellation** | `ctx.signal` → `AbortSignal` on `fetch()` | Maps to PI's built-in abort mechanism |
| **Pagination** | `pageOffset` passed through verbatim | Server-side cursors, opaque to the client |
| **Result limiting** | `limit` (default 100) + pagination | Keeps LLM context usage bounded |
| **Caching** | Server-side TTL caches (5 min) | No client-side cache needed |
| **Error handling** | Structured `{ "error": ... }` responses | PI surfaces them as tool errors |

---

## 8. Implementation Order

### Phase 1 — PI Extension (`codebeagle.ts`)
- [x] HTTP client helper using `fetch()` + `AbortSignal`
- [x] `codebeagle_list_indexes` tool
- [x] `codebeagle_search` tool
- [x] `codebeagle_search_files` tool
- [x] `codebeagle_health` tool
- [x] Server-down error message

### Phase 2 — Polish
- [x] Pagination loop guidance in tool results (show `pageOffset` hint)
- [x] Config override via env var `CODEBEAGLE_API_URL`, and config file codebeagle.json

---

## 9. Constraints & Notes

- **No new server code required** for the core tools — the web API already implements search,
  pagination, caching, context lines, and location discovery.
- **`fulltextindex/` is independent of PySide6** — the server uses it via the Qt-free `SearchProvider`.
- **Indexes must exist and be up to date** — the API searches existing indexes; refresh via
  `UpdateIndex.py` if results are stale.
- **Localhost-only by default** — server binds to `127.0.0.1:8080`; the extension should
  default to that URL (overridable via `CODEBEAGLE_API_URL`).
- **Query syntax** — CodeBeagle's rich query syntax (`*`, `**N`, `<!regex!>`, `#ifdef`) is a
  unique strength; tool descriptions should document it.
- **Context budget** — each match can carry up to `2*contextLines` extra lines; keep
  `contextLines` low (2–3) to limit token consumption.
- **Existing sibling doc** — `ai_agent/MCP-INTEGRATION.md` covers the same HTTP API for MCP
  agents; this plan is the PI-specific counterpart.