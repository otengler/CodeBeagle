/**
 * CodeBeagle PI Extension
 *
 * Registers custom tools that let the LLM search source code through
 * CodeBeagle's local HTTP web API (ai_agent/Server.py, 127.0.0.1:8080 by default).
 *
 * Tools:
 *  - codebeagle_health         -> GET  /api/v1/health
 *  - codebeagle_content_search -> POST /api/v1/search/content
 *  - codebeagle_file_search    -> POST /api/v1/search/filename
 *  - codebeagle_list_indexes   -> GET  /api/v1/locations
 *
 * Base URL resolution:
 *  - CODEBEAGLE_API_URL env var (highest precedence)
 *  - codebeagle.json in the same directory as this file, e.g.
 *      {
 *        "baseUrl": "http://127.0.0.1:8080"
 *      }
 *  - http://127.0.0.1:8080 default
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import {
  truncateHead,
  DEFAULT_MAX_BYTES,
  DEFAULT_MAX_LINES,
} from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { dirname, join } from "node:path";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

// Directory of this extension file (codebeagle.json is expected next to it).
const EXTENSION_DIR = dirname(fileURLToPath(import.meta.url));

interface ExtensionConfig {
  baseUrl?: string;
}

function readConfig(): ExtensionConfig {
  const configPath = join(EXTENSION_DIR, "codebeagle.json");
  try {
    if (!existsSync(configPath)) {
      return {};
    }
    const raw = readFileSync(configPath, "utf-8");
    const config = JSON.parse(raw) as ExtensionConfig;
    return typeof config === "object" && config !== null ? config : {};
  } catch (err) {
    console.warn(`CodeBeagle extension: could not read ${configPath}`, err);
    return {};
  }
}

/**
 * Resolve the CodeBeagle agent server base URL.
 * Precedence: CODEBEAGLE_API_URL env var > codebeagle.json (next to this file) > 8080 default.
 */
function resolveBaseUrl(): string {
  if (process.env.CODEBEAGLE_API_URL) {
    return process.env.CODEBEAGLE_API_URL.replace(/\/+$/, "");
  }
  const config = readConfig();
  if (config.baseUrl) {
    return config.baseUrl.replace(/\/+$/, "");
  }
  return "http://127.0.0.1:8080";
}

const BASE_URL = resolveBaseUrl();

const SERVER_DOWN_HINT =
  `The CodeBeagle agent server is not reachable at ${BASE_URL}. ` +
  `Run the CodeBeagle GUI and enable the 'AI agent' or use the standalone CodeBeagleAgentServer).`;

const NOT_INDEXED_HINT =
  `The requested path is not indexed. Fallback to searching without codebeagle_content_search or codebeagle_file_search.`

// ---- HTTP client -----------------------------------------------------------

async function callApi(
  path: string,
  method: "GET" | "POST",
  body?: object,
  signal?: AbortSignal,
): Promise<any> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (err) {
    if (signal?.aborted) throw err;
    const wrapped = new Error(SERVER_DOWN_HINT);
    (wrapped as any).cause = err;
    throw wrapped;
  }
  if (!res.ok) {
    if (res.status === 404) {
      throw new Error(NOT_INDEXED_HINT)
    }
    throw new Error(`HTTP ${res.status} from ${path}`);
  }
  try {
    return await res.json();
  } catch (err) {
    throw new Error(`Reading data failed: ${err}`);
  }
}

// ---- Result formatting ------------------------------------------------------

/** Opaque server-side pagination cursor ({fileIndex} / {fileIndex, matchIndex}). */
const PageOffset = Type.Object({
  fileIndex: Type.Optional(Type.Integer({ description: "File index cursor" })),
  matchIndex: Type.Optional(Type.Integer({ description: "Match index within the file" })),
});

function truncate(text: string): string {
  const t = truncateHead(text, { maxLines: DEFAULT_MAX_LINES, maxBytes: DEFAULT_MAX_BYTES });
  let out = t.content;
  if (t.truncated) {
    out +=
      `\n\n[Output truncated: showing ${t.outputLines} of ${t.totalLines} lines. ` +
      `Call the tool again with a smaller limit or pass pageOffset to fetch the next page.]`;
  }
  return out;
}

// ---- Tools -----------------------------------------------------------------

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "codebeagle_content_search",
    label: "CodeBeagle: Search Content",
    description:
      "Full-text search across CodeBeagle-indexed source code. " +
      "Query syntax: keywords ('createNode ( CComVariant'), trailing wildcards ('Fact*'), " +
      "unknown-word gaps ('error **2 network', regex ('code <!\\d+!>'). " +
      "Specify either 'location' (name from codebeagle_list_indexes) or 'folder' (root path; " +
      "the server resolves the best matching index). Returns matching lines with surrounding context. " +
      "Set contextLines=0 for compact output (path:line: full matching line, no context lines). " +
      "Keep contextLines low (2-3) to bound token usage. " +
      "Pagination: pass pageOffset from a previous response to fetch the next page.",
    promptSnippet: "Search CodeBeagle-indexed location for content (keywords, wildcards, regex, context lines)",
    promptGuidelines: [
      "Use codebeagle_content_search when the user asks to find content inside files. It replaces calls to `grep`. " +
      "Use codebeagle_health before any other tool use to make sure CodeBeagle services are available. "
    ],
    parameters: Type.Object({
      query: Type.Union([
        Type.String({
          description: "Search query. Examples: 'malloc', 'createNode ( CComVariant', 'error **5 <!\\d+!>'",
        }),
        Type.Array(Type.String(), {
          description: "List of search queries (OR logic). Files matching ANY query are returned.",
        }),
      ]),
      location: Type.Optional(
        Type.String({
          description: "Search location name from codebeagle_list_indexes. Mutually exclusive with folder.",
        }),
      ),
      folder: Type.Optional(
        Type.String({
          description: "Root folder path; the server resolves the best matching index. Mutually exclusive with location.",
        }),
      ),
      pathFilter: Type.Optional(Type.String({ description: "Path filter. Can be a full file path to select a single file, e.g. 'src/main.cpp'" })),
      extensionFilter: Type.Optional(
        Type.String({ description: "Extension filter, e.g. '.cpp,.h,-.hpp'" }),
      ),
      caseSensitive: Type.Optional(Type.Boolean({ description: "Case-sensitive search (default: false)" })),
      excludeComments: Type.Optional(Type.Boolean({ description: "Exclude matches inside comments (default: true)" })),
      contextLines: Type.Optional(
        Type.Integer({ description: "Context lines before/after each match (default 2). Set to 0 for compact output (no context lines)." }),
      ),
      limit: Type.Optional(Type.Integer({ description: "Max matches per page (default 100)" })),
      pageOffset: Type.Optional(PageOffset),
    }),
    async execute(_toolCallId: any, params: any, signal: any, _onUpdate: any) {
      const result = await callApi("/api/v1/search/content", "POST", params, signal);
      let body: string;
      if (params.contextLines === 0) {
        // Compact output: path:line: full matching line
        body = (result.matches || []).map((m: any) => `${m.file}:${m.line}: ${m.fullLine}`).join("\n");
      } else {
        body = JSON.stringify(result, null, 2);
      }
      const more = result.pageOffset
        ? `\n\nMore results available. Call codebeagle_content_search again with the same parameters plus pageOffset=${JSON.stringify(result.pageOffset)}.`
        : "";
      return {
        content: [{ type: "text", text: truncate(body + more) }],
        details: result,
      };
    },
  });

  pi.registerTool({
    name: "codebeagle_file_search",
    label: "CodeBeagle: Search File Names",
    description:
      "Search for files by name across CodeBeagle-indexed source code. " +
      "This replaces the 'find' command for indexed locations. " +
      "The query supports * and ? wildcards ('Factory*', '*test*.py', 'Makefile'). " +
      "Pass a list of queries for OR logic: files matching ANY pattern are returned. " +
      "If the query contains a dot, the part after the last dot is used as an extension filter. " +
      "Specify either 'location' or 'folder'. " +
      "Pagination: pass pageOffset from a previous response to fetch the next page.",
    promptSnippet: "Search CodeBeagle-indexed location for file names.",
    promptGuidelines: [
      "Use codebeagle_file_search when the user asks to find files by name. It replaces calls to `find`. " +
      "Pass multiple queries as an array for OR matching. " +
      "Use codebeagle_health before any other tool use to make sure CodeBeagle services are available. "
    ],
    parameters: Type.Object({
      query: Type.Union([
        Type.String({ description: "File name pattern, e.g. 'main*', '*test*.py', 'Makefile'" }),
        Type.Array(Type.String(), { description: "List of file name patterns (OR logic). Files matching ANY pattern are returned." }),
      ]),
      location: Type.Optional(Type.String({ description: "Search location name from codebeagle_list_indexes" })),
      folder: Type.Optional(Type.String({ description: "Root folder path" })),
      pathFilter: Type.Optional(Type.String({ description: "Path filter. Can be a full file path to select a single file, e.g. 'src/main.cpp'" })),
      extensionFilter: Type.Optional(Type.String({ description: "Extension filter, e.g. '.py,.js'" })),
      caseSensitive: Type.Optional(Type.Boolean({ description: "Case-sensitive search (default: false)" })),
      limit: Type.Optional(Type.Integer({ description: "Max files per page (default 100)" })),
      pageOffset: Type.Optional(PageOffset),
    }),
    async execute(_toolCallId: any, params: any, signal: any) {
      const result = await callApi("/api/v1/search/filename", "POST", params, signal);
      const body = JSON.stringify(result, null, 2);
      const more = result.pageOffset
        ? `\n\nMore results available. Call codebeagle_file_search again with the same parameters plus pageOffset=${JSON.stringify(result.pageOffset)}.`
        : "";
      return {
        content: [{ type: "text", text: truncate(body + more) }],
        details: result,
      };
    },
  });

  pi.registerTool({
    name: "codebeagle_list_indexes",
    label: "CodeBeagle: List Search Locations",
    description:
      "List all available CodeBeagle search locations (indexes): name, folders, extensions, index mode. " +
      "Call this first to discover what is searchable, then pass the location name to codebeagle_content_search / codebeagle_file_search.",
    promptSnippet: "List CodeBeagle search locations (indexes)",
    promptGuidelines: [
      "Call codebeagle_list_indexes when the user wants to find files or search inside files (like grep), to discover available search locations. " +
      "Use codebeagle_health before any other tool use to make sure CodeBeagle services are available. "
    ],
    parameters: Type.Object({}),
    async execute(_toolCallId: any, _params: any, signal: any) {
      const result = await callApi("/api/v1/locations", "GET", undefined, signal);
      const text =
        result.locations.length === 0
          ? "No search locations configured."
          : result.locations
              .map(
                (loc: any) =>
                  `- ${loc.name}: ${loc.folders.join(", ")} [${loc.extensions.join(", ")}] (${loc.indexMode})`,
              )
              .join("\n");
      return {
        content: [{ type: "text", text: `Available CodeBeagle search locations:\n${text}` }],
        details: result,
      };
    },
  });

  pi.registerTool({
    name: "codebeagle_health",
    label: "CodeBeagle: Server Health",
    description:
      "Check whether the CodeBeagle agent server is running and reachable. " +
      "Use this when a codebeagle_* tool reports that the server is down.",
    parameters: Type.Object({}),
    async execute() {
      const result = await callApi("/api/v1/health", "GET");
      return {
        content: [
          { type: "text", text: `CodeBeagle agent server at ${BASE_URL}: ${JSON.stringify(result)}` },
        ],
        details: result,
      };
    },
  });
}
