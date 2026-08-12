# AI Agent Integration Plan for CodeBeagle

This document outlines a plan to expose CodeBeagle's search capabilities to AI agents via a local web API, allowing automated search and retrieval of code search results.

## Vision

AI agents (such as LLM-powered coding assistants) need to query codebases efficiently. CodeBeagle's fast full-text indexing and flexible search syntax make it an ideal backend for such tasks. By providing a locally accessible HTTP interface, AI agents can perform searches without requiring a GUI, enabling integration into automated workflows, AI‑driven code analysis, and agentic tool‑use scenarios.

## Goals

1. **Expose search functionality** via a simple, well‑defined HTTP API.
2. **Return results with configurable context** (e.g., two lines before/after each match).
3. **Support pagination** to handle large result sets.
4. **Minimal impact** on the existing GUI application; the service should be optional and run alongside the GUI or as a standalone daemon.
5. **Keep dependencies light** – use Python’s standard library where possible, avoid heavy web frameworks if not needed.

## Architecture

### Component Overview

```
┌──────────────────────────────────────────────────────────┐
│                   AI Agent (Client)                       │
│  (e.g., Claude, GPT, custom script)                       │
└──────────────────────────────────────────────────────────┘
                                   │ HTTP (localhost:PORT)
                                   ▼
┌──────────────────────────────────────────────────────────┐
│            CodeBeagle Web API Server                      │
│  ┌───────────────┐   ┌──────────────────────────────┐    │
│  │ HTTP Listener │   │ Search Engine Integration    │    │
│  │ (TCP port)    │──▶│ (reuse FullTextIndex,        │    │
│  └───────────────┘   │  Query, SearchAsync)         │    │
│                      └──────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────────────────────────────┐
│        Existing CodeBeagle Indexes & Configuration        │
│  (config.txt, UserConfig.txt, index *.db files)          │
└──────────────────────────────────────────────────────────┘
```

### Server Options

1. **Integrated Mode** – The web server runs as a background thread within the existing CodeBeagle GUI process. The GUI can be hidden or minimized; the server starts automatically when the GUI starts (configurable).
2. **Standalone Mode** – A separate script (`CodeBeagleAgentServer.py`) launches the web server independently, using the same configuration files. This allows headless operation on servers or dedicated machines.

Both modes share the same API implementation.

### Technology Choices

- **HTTP server**: Use Python’s `http.server` extended with JSON handling,
- **Concurrency**: The server will be single‑threaded but can handle multiple requests sequentially. Since searches are fast and AI agents likely issue few concurrent requests, this is acceptable. If needed, `socketserver.ThreadingMixIn` can be used.
- **JSON**: Input and output will be JSON‑encoded.

## API Design

### Base URL

`http://localhost:PORT/api/v1`

### Endpoints

#### `GET /locations`

Returns the list of configured search locations (index configurations) with their display names, IDs, source directories, file extensions, and index mode. This is the first endpoint an AI agent should call to discover which search locations are available, so it can reference them in subsequent `POST /search/content` or `POST /search/filename` requests.

No request body or query parameters are required.

**Response (JSON):**

```json
{
  "locations": [
    {
      "name": "default",
      "folders": [
        "C:/src/CodeBeagle",
        "C:/src/CodeBeagle/fulltextindex"
      ],
      "extensions": [".py", ".pyw", ".js", ".ts", ".cs", ".cpp", ".h", ".java", ".md"],
      "indexMode": "filenameAndContent"
    },
    {
      "name": "docs",
      "folders": [
        "D:/docs/reference"
      ],
      "extensions": [".md", ".rst", ".txt"],
      "indexMode": "filename"
    }
  ]
}
```

**Field descriptions:**
- `name` – Machine-readable identifier for the location. Use this in the `location` field of search requests.
- `folders` – One or more directories that are indexed under this location.
- `extensions` – File extensions included in the index.
- `indexMode` – Either `"content"` (full-text search within files) or `"filename"` (file name search only) or `"filenameAndContent"` (content and filename search is possible).

**Example usage:**

```bash
curl http://localhost:8080/api/v1/locations
```

**Response snippet:**

```json
{
  "locations": [
    {
      "name": "default",
      "folders": ["C:/src/CodeBeagle"],
      "extensions": [".py", ".js"],
      "indexMode": "filenameAndContent"
    }
  ]
}
```

#### `POST /search/content`

Search within file content.

**Request Body (JSON):**
```json
{
  "location": "default",           // index configuration name
  "folder": "root folder for search",  // root folder where to search
  "query": "class MyClass*",        // search string (same syntax as GUI search box); wildcards like * are always supported
  "folderFilter": "",              // optional folder filter
  "extensionFilter": "",           // optional extension filter
  "caseSensitive": false,          // optional
  "excludeComments": false,        // optional
  "contextLines": 2,               // optional, number of lines before/after each match to include (default 2)
  "limit": 10,                    // max results per page (default 100)
  "pageOffset":  {"fileIndex": number, "matchIndex": number}, // returned by /search/content
}
```

`location` and `folder` are mutually exlusive. Either you can pass the name of the search index.
Or you can pass the root folder where to search. In the latter case the server has to determine which search location to use. It needs to inspect the existing locations and use the first matching location which has a folder which equals or is a parent folder of the desired `folder`.
This allows an AI agent to run a query without first querying the search locations.

Edge cases for `folder`:
- If the root folder matches multiple search indexes the first one is used
- If the root folder does not match any search index the web call fails with 404.
- If a location has multiple source directories and only one matches: This does not matter, the index contains all files from both directories and can be used.
- If a `folderFilter` is specified this allows to refine the search. E.g. the root folder is "C:\\src" and the `folderFilter` is "interface". The all files under C:\\src" which are in a directory called "interface" are returned. This can also be used to exclude directories using a minus sign. E.g. "-header".

**Response (JSON):**
```json
{
  "totalFiles": 42,
  "pageOffset": {"fileIndex": 4, "matchIndex": 3},
  "matches": [
    {
      "file": "C:/src/project/main.py",
      "line": 45,
      "column": 10,
      "matchText": "class MyClassA",
      "contextBefore": ["# My awesome class", ""],
      "contextAfter": ["    def __init__(self):", "        pass"],
      "fullLine": "class MyClassA (Superclass)"
    },
    ...9 more results
  ]
}
```

Each match includes the exact line number (1‑based), column (1‑based), the matched text, and the requested number of lines before/after (as arrays of strings). The `fullLine` field contains the complete line where the match occurred.
`totalFiles` is the total number of files where the search matches. It is not the number of total matches because there are potentially more than one matches per file.

#### `POST /search/filename`

Search for file names. Wildcard matching (`*`, `?`) is always enabled — no separate `wildcard` parameter is needed. The `*` matches any sequence of characters, `?` matches a single character.

**Request Body (JSON):**
Same fields as content search, except `excludeComments` and `contextLines` are not applicable:
- `location` / `folder` — mutually exclusive (same rules as content search)
- `query` — file name pattern (supports `*` and `?` wildcards)
- `folderFilter` — optional
- `extensionFilter` — optional
- `caseSensitive` — optional
- `limit` — optional (default 100)
- `pageOffset` — optional, returned by a previous response

**Response (JSON):**
```json
{
  "totalFiles": 5000,
  "pageOffset":  {"fileIndex": 100 },
  "files": [
    "C:/src/project/MyClass.py",
    "C:/src/project/subdir/MyClass.cs",
    ..and 98 more (because 100 are default)
  ]
}
```

`totalFiles` is the total number of files where the search matches. 

#### `GET /health`

Simple endpoint returning `{"status": "ok"}` to verify the server is running.

### Error Handling

- **400 Bad Request** – Invalid JSON, missing required fields, or malformed query.
- **404 Not Found** – Requested location not found.
- **500 Internal Server Error** – Search engine error (e.g., corrupted index). The response body may contain an error message.

### Example Usage

Using `curl` to search for `"def main"` in the default location:

```bash
curl -X POST http://localhost:8080/api/v1/search/content \
  -H "Content-Type: application/json" \
  -d '{"query": "def main", "contextLines": 2}'
```

Response snippet:

```json
{
  "totalFiles": 3,
  "matches": [
    {
      "file": "/home/user/project/script.py",
      "line": 5,
      "column": 1,
      "matchText": "def main",
      "contextBefore": ["import sys", ""],
      "contextAfter": ["    print(\"Hello\")", "    return 0"],
      "fullLine": "def main():"
    }
  ]
}
```

## Context Extraction

To provide context lines around each match, the server must:

1. Read the file (with proper encoding detection, reuse `tools.FileTools.freadall`).
2. Split the content into lines.
3. For each match position (already available from `query.matches()`), compute line and column using `tools.FileTools.lineColFromPos`.
4. Extract `contextLines` lines before and after the match line, ensuring array boundaries.
5. Return the arrays together with the match line.

Because reading the same file multiple times (if many matches in one file) could be inefficient, we can cache the lines per file for the duration of the search. The existing `MatchesOverview` module already does similar line extraction; its logic can be adapted.

## Pagination

The calls to `/search/content` and `/search/filename` returns a `pageOffset` which can be feed into the calls again to return the next page.
In general the search engine always returns flat list of files. For file name search this is all it needs. For content search the files in the list must be checked for matches.

### Pagination for 'content'
The `pageOffset` contains:
```json
{
  "fileIndex": 4, 
  "matchIndex": 3
}
  ```
This  describes where the next match can be found. `fileIndex` is a zero based number indicating which file match is returned next. The `matchIndex` is a zero based index of the match inside the file.

### Pagination for 'filename'
The `pageOffset` contains:
```json
{
  "fileIndex": 4, 
}
```
`fileIndex` is a zero based number indicating which file match is returned next.

### Signalling end of data
When the `pageOffset`is omitted there is no more data.

### Performance
The server should perform caching based on query parameters to improve performance.
The file of file matches and the list of matches inside a file should be cached. It is enough to cache the matches inside a single file (which only affects performance if there a lots of matches inside a single file).
The cache should have a TTL with a reasonable time. E.g. 5 minutes. 

## Configuration

### Server Configuration

The web server should be configurable via `config.txt`:

```
[agent]
port = 8080
bind = 127.0.0.1
enabled = true
contextLines = 2
defaultLimit = 100
```

If `enabled` is false, the server does not start (integrated mode) or exits immediately (standalone mode).

### Security Considerations

- Bind only to `127.0.0.1` (localhost) by default, preventing network access.
- Optionally support CORS headers for local web apps (`Access‑Control‑Allow‑Origin: http://localhost:3000`).
- No authentication – assumed to be running in a trusted local environment.

## Deployment

### Integrated Mode
When CodeBeagle GUI is started and the `[agent] enabled` setting is `true`, the web server starts in a background thread. The GUI operates normally; the server runs until the GUI closes. The UI should show an icon which allows to view a history of the command the AI agent(s) executed (limited to 500).

### Standalone Mode
Run `python CodeBeagleAgentServer.py` (or the packaged executable `CodeBeagleAgentServer.exe`). This script loads the same configuration files as the GUI but runs only the web server, without any Qt window. It is suitable for headless environments (e.g., development servers, CI pipelines).

### Index Updates
In standalone mode, indexes can be updated using the existing `UpdateIndex.py` tool (or its packaged counterpart). The web server does not automatically update indexes; this remains a manual or scheduled task.

## Implementation Steps

### Phase 1: Core Search Abstraction

1. Create a new module `ai_agent/search_provider.py` that provides a Qt‑free interface to CodeBeagle’s search engine. This module will:
   - Load configuration via `AppConfig.appConfig()` (without Qt).
   - Use `fulltextindex.SearchMethods` directly (no `QObject` parent).
   - Convert `QueryParams` and execute searches synchronously (cancellation not needed for simple API).
   - Return results as plain Python objects.

2. Adapt the existing `MatchesOverview.MatchesInFile` logic to extract matches with context lines. This code must not be copied. It must be used from a shared location. E.g. move it to "tools".

### Phase 2: HTTP Server

3. Create `ai_agent/server.py` using `http.server.HTTPServer` and a custom `RequestHandler` that:
   - Parses JSON request bodies.
   - Routes requests to the appropriate search provider.
   - Converts results to JSON.
   - Handles errors and returns proper HTTP status codes.
   - Serves only the API endpoints described above.

4. Add a command‑line argument `--agent‑server` to `CodeBeagle.pyw` that starts the server in a background thread (integrated mode). Also provide a standalone script `CodeBeagleAgentServer.py` that loads configuration and runs the server indefinitely.

### Phase 3: Configuration Integration

5. Extend `config.txt` with an `[agent]` section as described.
6. Ensure the server reads the configuration and respects the `enabled` flag.

### Phase 4: Testing

7. Write unit tests for the search provider and context extraction.
8. Create a simple integration test that starts the server, sends HTTP requests, and validates responses.
9. Update `UnitTests.py` to include the new tests.

## Potential Challenges & Solutions

- **Qt Dependency**: The existing `SearchAsync` requires a `QObject` parent. We can bypass it by using `SearchMethods` directly (already designed to be independent). However, `SearchMethods` uses `FullTextIndex` which uses SQLite – this is fine without Qt.
- **Thread Safety**: If the server runs in a separate thread while the GUI is also using the same index databases, SQLite connections must be managed carefully. Each search should open its own connection (already done by `FullTextIndex`).
- **Performance**: Extracting context lines for many matches may be slow for huge files. We can limit the number of matches per file (e.g., first 10 matches per file) or cap the total matches returned.
- **Memory**: Caching file contents for repeated matches in the same file is beneficial; we can use an LRU cache with a reasonable size limit.

## Future Enhancements

- **Streaming Results**: Support `Transfer‑Encoding: chunked` to stream matches as they are found.
- **WebSocket API**: For real‑time search progress and cancellation.
- **Additional Endpoints**: 
  - `/index/status` – show index update status.
  - `/index/update` – trigger an index update.
  - `/files/content` – retrieve the entire content of a file (with syntax highlighting as HTML).
- **Plugin System**: Allow AI agents to register custom search scripts via the API.
- **UI enhancements**: Show button with AI search history.

## Deliverables

1. `ai‑agents.md` (this plan).
2. New directory `ai_agent/` containing:
   - `search_provider.py`
   - `server.py`
3. `CodeBeagleAgentServer.py` (standalone entry point).
4. Updates to `config.txt` schema documentation.
5. Integration with existing build scripts (include new module in `setup.py`).

## Timeline

- **Week 1**: Implement search provider and context extraction (Phase 1).
- **Week 2**: Implement HTTP server and integrate configuration (Phases 2‑3).
- **Week 3**: Testing and documentation.

---

*This plan is a living document; feedback and adjustments are welcome.*