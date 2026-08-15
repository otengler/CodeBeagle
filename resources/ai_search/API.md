# CodeBeagle AI Agent API

This document describes the HTTP API for AI agents to search source code using CodeBeagle's full-text indexing engine.
Humans are welcome too :-)

## Quick Start

```bash
# Check if the server is running
curl http://localhost:8080/api/v1/health

# Search file content
curl -X POST http://localhost:8080/api/v1/search/content \
  -H "Content-Type: application/json" \
  -d '{"query": "class Factory", "folder": "c:\\src\\project", "contextLines": 3}'

# Search file names - 404 means the folder is not covered by an index
curl -X POST http://localhost:8080/api/v1/search/filename \
  -H "Content-Type: application/json" \
  -d '{"query": "Factory*", "folder": "c:\\src\\project"}'

# List available search locations
curl http://localhost:8080/api/v1/locations
```

## Base URL

All API endpoints are served under `http://{host}:{port}/api/v1/`. The root path `/` returns this documentation.

Default port is `8080`, bound to `127.0.0.1` (localhost only).

---

## Endpoints

### `GET /health`

Returns a simple status check. Use this to verify the server is running.

**Response:**
```json
{
  "status": "ok"
}
```

---

### `GET /api/v1/locations`

Returns all configured search locations. The recommended way is to skip this and specify the `folder` parameter with the desired root folder
in the content or file name search.

**Response:**
```json
{
  "locations": [
    {
      "name": "myproject",
      "folders": ["C:/src/myproject"],
      "extensions": [".py", ".js", ".ts", ".cpp", ".h", ".java", ".md"],
      "indexMode": "filenameAndContent"
    }
  ]
}
```

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Identifier for the search location. Use in the `location` field of search requests. |
| `folders` | string[] | One or more source directories indexed under this location. |
| `extensions` | string[] | File extensions included in the index. |
| `indexMode` | string | `"filenameAndContent"` — both content and filename search available. `"content"` — content search only. `"filename"` — filename search only. |

---

### `POST /api/v1/search/content`

Search within file contents. Returns matching lines with surrounding context.

**Request body:**

```json
{
  "query": "class MyClass*",
  "location": null,
  "folder": "C:\\src\\project",
  "folderFilter": "",
  "extensionFilter": "",
  "caseSensitive": false,
  "excludeComments": true,
  "contextLines": 2,
  "limit": 100,
  "pageOffset": null
}
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | **yes** | — | Search expression. See [Search Syntax](#search-syntax) below. |
| `location` | string | no* | — | Name of a search location from `GET /locations`. |
| `folder` | string | no* | — | Root folder path to search in. The server resolves this to the best matching location. |
| `folderFilter` | string | no | `""` | Filter results by folder path. See [Folder Filter](#folder-and-extension-filters). |
| `extensionFilter` | string | no | `""` | Filter results by file extension. See [Extension Filter](#folder-and-extension-filters). |
| `caseSensitive` | bool | no | `false` | If `true`, search is case-sensitive. |
| `excludeComments` | bool | no | `true` | If `true`, matches inside comments are excluded (e.g. `//` in C/C++, `#` in Python). |
| `contextLines` | int | no | `2` | Number of lines of context before and after each match. Set to `0` to omit context lines entirely (the `contextBefore`/`contextAfter` fields are then not included in the response). |
| `limit` | int | no | `100` | Maximum number of matches per page. |
| `pageOffset` | object | no | `null` | Pagination cursor from a previous response. See [Pagination](#pagination). |

\* Either `location` or `folder` must be specified. If both are omitted, the configured default location is used.

**Matching logic:**
- The query is matched against the full text of each file using regex.
- Only files whose extensions match the index configuration are searched.
- Each match's position, line number, and surrounding context are returned.
- Matches are returned in file order (sorted alphabetically by file path), then by position within each file.
- When `excludeComments` is `true` (the default), matches that start inside a comment (e.g. `//` in C/C++, `#` in Python) are dropped. Set `"excludeComments": false` to include matches in comments.

**Response:**

```json
{
  "totalFiles": 42,
  "pageOffset": {
    "fileIndex": 4,
    "matchIndex": 3
  },
  "matches": [
    {
      "file": "C:/src/myproject/src/main.py",
      "line": 45,
      "matchText": "class MyClassA",
      "contextBefore": ["# My awesome class", ""],
      "contextAfter": ["    def __init__(self):", "        pass"],
      "fullLine": "class MyClassA (Superclass)"
    }
  ]
}
```

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `totalFiles` | int | Total number of files with at least one match (not total matches). |
| `pageOffset` | object or null | Present if there are more results. Pass this back in the next request. Omitted when no more data. |
| `matches` | object[] | Array of match objects. |

**Match object fields:**

| Field | Type | Description |
|-------|------|-------------|
| `file` | string | Full path to the file. |
| `line` | int | 1-based line number. |
| `matchText` | string | The exact text that matched the search. |
| `fullLine` | string | The complete source line containing the match. |
| `contextBefore` | string[] | Lines before the match (up to `contextLines`). |
| `contextAfter` | string[] | Lines after the match (up to `contextLines`). |

---

### `POST /api/v1/search/filename`

Search for file names. Wildcard matching with `*` and `?` is always enabled.

**Request body:**

```json
{
  "query": "Factory*",
  "location": null,
  "folder": "C:\\src\\project",
  "folderFilter": "",
  "extensionFilter": "",
  "caseSensitive": false,
  "limit": 100,
  "pageOffset": null
}
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | **yes** | — | File name pattern. Supports `*` and `?` wildcards. See [Search Syntax](#search-syntax). |
| `location` | string | no* | — | Name of a search location from `GET /locations`. |
| `folder` | string | no* | — | Root folder path to search in. |
| `folderFilter` | string | no | `""` | Filter results by folder path. |
| `extensionFilter` | string | no | `""` | Filter results by file extension. |
| `caseSensitive` | bool | no | `false` | If `true`, search is case-sensitive. |
| `limit` | int | no | `100` | Maximum number of files per page. |
| `pageOffset` | object | no | `null` | Pagination cursor from a previous response. |

\* Either `location` or `folder` must be specified, or the default location is used.

**Matching logic:**
- The query is matched against the **file name only** (not the full path).
- The extension part of the query is automatically used as an extension filter. For example, `*.py` matches files with `.py` extension.
- `*` matches any sequence of characters.
- `?` matches any single character.
- Results are sorted alphabetically by file path.

**Response:**

```json
{
  "totalFiles": 5000,
  "pageOffset": {
    "fileIndex": 100
  },
  "files": [
    "C:/src/myproject/src/Factory.py",
    "C:/src/myproject/src/subdir/FactoryConfig.cs"
  ]
}
```

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `totalFiles` | int | Total number of matching files. |
| `pageOffset` | object or null | Present if there are more results. Omitted when no more data. |
| `files` | string[] | Array of full file paths matching the query. |

---

## Search Syntax

### Content Search

The search syntax is the same as CodeBeagle's GUI search box. It supports:

**Basic keywords:**
```
class Factory
```
Searches for files containing both `class` and `Factory` (in order, with optional whitespace between them).

**Wildcards inside keywords:**
```
class Fact*
```
The `*` wildcard matches any sequence of word characters (`\w*`). Available in content search.

```
class Fact?ry
```
`?` is not supported in content search — use `*` instead.

**Phrase / proximity search:**
```
class **2 Factory
```
`**N` matches exactly `N` unknown words between the preceding and following keyword. For example, `class **2 Factory` matches `class MyAbstract Factory`.

**Regular expression:**
```
<!\bclass\s+\w+Factory!>
```
Wrap a regex in `<!` and `!>` to use it as a search term. The regex is matched as a sub-expression and combined with other terms.

**Case sensitivity:**
By default, searches are case-insensitive. Set `"caseSensitive": true` in the request body to enable case-sensitive matching.

### Filename Search

Filename search supports `*` and `?` wildcards:

| Pattern | Matches | Does not match |
|---------|---------|---------------|
| `Factory*` | `Factory.py`, `FactoryConfig.cs` | `factory.py` (case-insensitive by default) |
| `*test*` | `test_main.py`, `mytest.js` | `data.txt` |
| `test?.py` | `test1.py`, `testA.py` | `test.py`, `test10.py` |
| `*.py` | `main.py`, `util.py` | `main.js` |

When the query contains a `.`, the part after the last `.` is treated as an extension filter. For example, `*.py` searches for files with any name and `.py` extension. Search for `Factory` to find files named exactly `Factory` (with any extension).

### Folder and Extension Filters

Both content and filename search support optional filters.

**Folder filter** (`folderFilter`):
- Comma-separated list of folder name patterns.
- `*` matches any characters, `?` matches any single character.
- Prefix with `-` to exclude. Example: `test, -test/mock` matches folders containing "test" but not "test/mock".
- Applied to the full file path (case-insensitive).

**Extension filter** (`extensionFilter`):
- Comma-separated list of extensions.
- Prefix with `-` to exclude. Example: `.py, .js, -test.py` includes `.py` and `.js` but excludes `test.py`.
- Without a leading dot, one is added automatically: `py` → `.py`.

---

## Pagination

Both search endpoints return a `pageOffset` object when there are more results available. Pass this object back in the next request to get the next page.

**Content search pagination:**
```json
{
  "pageOffset": {
    "fileIndex": 4,
    "matchIndex": 3
  }
}
```
- `fileIndex`: Zero-based index into the list of matching files. The next page starts from this file.
- `matchIndex`: Zero-based index of the match inside that file. The next page starts from this match.

**Filename search pagination:**
```json
{
  "pageOffset": {
    "fileIndex": 100
  }
}
```
- `fileIndex`: Zero-based index into the list of matching files. The next page starts from this file.

**End of data:**
When there are no more results, `pageOffset` is omitted from the response. No special handling is needed — just stop paginating when `pageOffset` is absent.

**Example pagination loop (curl):**
```bash
# Get first page
curl -X POST http://localhost:8080/api/v1/search/content \
  -H "Content-Type: application/json" \
  -d '{"query": "class Factory", "location": "myproject", "limit": 10}' | jq .

# Use the pageOffset from the response to get the next page
curl -X POST http://localhost:8080/api/v1/search/content \
  -H "Content-Type: application/json" \
  -d '{"query": "class Factory", "location": "myproject", "limit": 10, "pageOffset": {"fileIndex": 4, "matchIndex": 3}}' | jq .
```

---

## Error Handling

The API returns standard HTTP status codes and a JSON error body.

**400 Bad Request** — Invalid input (missing fields, bad JSON, invalid values):
```json
{
  "error": "Field 'query' must not be empty"
}
```

**404 Not Found** — Unknown search location or folder:
```json
{
  "error": "Search location 'unknown' not found"
}
```

**500 Internal Server Error** — Search engine error (corrupted index, etc.):
```json
{
  "error": "Database error: no such table: keywords"
}
```

**Common errors:**

| Error | Cause |
|-------|-------|
| `"Field 'query' must not be empty"` | Missing or empty `query` field. |
| `"Field 'query' must be a string"` | `query` is not a string. |
| `"Search location 'X' not found"` | The `location` name doesn't match any configured location. |
| `"No search location found for folder 'X'"` | The `folder` path doesn't belong to any configured location. |
| `"Only one of 'location' or 'folder' may be specified"` | Both `location` and `folder` were provided. |
| `"Invalid JSON in request body"` | The request body is not valid JSON. |
| `"Field 'pageOffset.fileIndex' is required"` | `pageOffset` is present but missing the `fileIndex` field. |

---

## Configuration

The server is configured in `config.txt` (or `UserConfig.txt`) under the `agent` section:

```ini
agent {
    enabled = true
    port = 8080
    bind = 127.0.0.1
    contextLines = 2
    defaultLimit = 100
    allowOrigin = http://localhost:3000
}
```

| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | `false` | Set to `true` to enable the server. |
| `port` | `8080` | TCP port to listen on. |
| `bind` | `127.0.0.1` | IP address to bind to. Use `0.0.0.0` to allow network access (not recommended). |
| `contextLines` | `2` | Default number of context lines if not specified in the request. |
| `defaultLimit` | `100` | Default page size if not specified in the request. |
| `allowOrigin` | (empty) | If set, enables CORS with this origin. Useful for browser-based AI tools. |

---

## Notes for AI Agents

1. **Start with `GET /api/v1/locations`** to discover which indexes are available. The response tells you the `name` to use in the `location` field and what `indexMode` is supported (content vs. filename).

2. **Use the `folder` parameter** instead of `location` if you don't know the location name. The server will find the best matching index for the folder path you provide.

3. **Pagination is sequential.** Each response includes a `pageOffset` that you pass back as-is. Do not modify the `pageOffset` values — they are opaque cursors.

4. **Context lines help with understanding.** Request 2-5 context lines to give the AI model enough context around each match. More lines = more tokens consumed.

5. **Wildcards are powerful for filename search.** Use `*` to match any part of a filename: `*test*` finds all files containing "test" in the name.

6. **Wildcards for content search cost performance.** Especially if not at the end. If you know the exact pattern omit wildcards.

7. **For regex searches in content**, wrap the regex in `<!...!>`. Example: `code <!\\d+!>` matches `code` followed by a number.

8. **The server binds to localhost only** by default (127.0.0.1). This is intentional for security. Do not change the bind address to 0.0.0.0 unless you are in a controlled network environment.

9. **Use `excludeComments` (default `true`) to filter out trivial matches** in comments (e.g. TODO notes, documentation). Set `"excludeComments": false` if you want matches in comments too.

10. **For compact output set `"contextLines": 0`** — the response then contains no `contextBefore`/`contextAfter` lines, only `file`, `line`, `matchText` and `fullLine` per match. This reduces response size and is what the PI extension's compact format does.

11. **Performance:** Searches are typically fast (milliseconds to seconds). The server uses caching to avoid re-scanning files for paginated requests. The cache has a 5-minute TTL.