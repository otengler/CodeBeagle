/**
 * CodeBeagle PI Extension
 *
 * Registers custom tools that let the LLM search source code through
 * CodeBeagle's local HTTP web API (ai_agent/Server.py, 127.0.0.1:8080 by default).
 *
 * Tools:
 *  - codebeagle_list_indexes  -> GET  /api/v1/locations
 *  - codebeagle_search        -> POST /api/v1/search/content
 *  - codebeagle_search_files  -> POST /api/v1/search/filename
 *  - codebeagle_health        -> GET  /api/v1/health
 *
 * Command:
 *  - /codebeagle-start  spawns CodeBeagleAgentServer.py for the current session
 *
 * Base URL override: CODEBEAGLE_API_URL env var.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import {
  truncateHead,
  DEFAULT_MAX_BYTES,
  DEFAULT_MAX_LINES,
} from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { spawn, type ChildProcess } from "node:child_process";
import { join } from "node:path";
import { readFileSync } from "node:fs";

/**
 * Resolve the CodeBeagle agent server base URL.
 * Precedence: CODEBEAGLE_API_URL env var > 8080 default.
 */
function resolveBaseUrl(): string {
  if (process.env.CODEBEAGLE_API_URL) {
    return process.env.CODEBEAGLE_API_URL.replace(/\/+$/, "");
  }
  return "http://127.0.0.1:8080";
}

const BASE_URL = resolveBaseUrl();

const SERVER_DOWN_HINT =
  `The CodeBeagle agent server is not reachable at ${BASE_URL}. ` +
  `Run the CodeBeagle GUI and enable the 'AI agent' or use the standalone CodeBeagleAgentServer).`;

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
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error ?? `HTTP ${res.status} from ${path}`);
  }
  return data;
}

// ---- Result formatting ------------------------------------------------------

/** Opaque server-side pagination cursor ({fileIndex} / {fileIndex, matchIndex}). */
const PageOffset = Type.Object({
  fileIndex: Type.Optional(Type.Integer({ description: "File index cursor" })),
  matchIndex: Type.Optional(Type.Integer({ description: "Match index within the file" })),
});

/** Output format: json (default) returns full JSON response; compact returns path:line: text (no context lines). */
const OutputFormat = Type.Optional(
  Type.Union([
    Type.Literal("json", { description: "Full JSON result" }),
    Type.Literal("compact", { description: "path:line: full matching line (no context lines)" }),
  ], { description: "Output format (default: json). Compact mode sets contextLines=0 automatically, so no context lines are returned." }),
);

function formatCompactMatches(matches: any[]): string {
  return matches.map((m) => `${m.file}:${m.line}: ${m.fullLine}`).join("\n");
}

/** Human-readable match listing with context (used by the legacy default view). */
function formatMatches(matches: any[]): string {
  return matches
    .map((m) => {
      const before = (m.contextBefore ?? []).map((l: string) => `  ${l}`).join("\n");
      const after = (m.contextAfter ?? []).map((l: string) => `  ${l}`).join("\n");
      const parts = [`${m.file}:${m.line}`];
      if (before) parts.push(before);
      parts.push(`> ${m.fullLine}`);
      if (after) parts.push(after);
      return parts.join("\n");
    })
    .join("\n\n");
}

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
    name: "codebeagle_search",
    label: "CodeBeagle: Search Content",
    description:
      "Full-text search across CodeBeagle-indexed source code. " +
      "Query syntax: keywords ('createNode ( CComVariant'), trailing wildcards ('Fact*'), " +
      "unknown-word gaps ('error **2 network', regex ('code <!\\d+!>'). " +
      "Specify either 'location' (name from codebeagle_list_indexes) or 'folder' (root path; " +
      "the server resolves the best matching index). Returns matching lines with surrounding context. " +
      "Set format='json' (default) for JSON output, format='compact' for path:line: text " +
      "(compact mode returns no context lines). " +
      "Keep contextLines low (2-3) to bound token usage. " +
      "Pagination: pass pageOffset from a previous response to fetch the next page.",
    promptSnippet: "Search indexed source code with CodeBeagle (keywords, wildcards, regex, context lines)",
    promptGuidelines: [
      "Use codebeagle_search to find code usages, definitions, or patterns across indexed source code instead of ad-hoc grep.",
      "Call codebeagle_list_indexes to discover available search locations.",
    ],
    parameters: Type.Object({
      query: Type.String({
        description:
          "Search query. Examples: 'malloc', 'createNode ( CComVariant', 'error **5 <!\\d+!>'",
      }),
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
      folderFilter: Type.Optional(Type.String({ description: "Folder filter, e.g. 'src/, -test/'" })),
      extensionFilter: Type.Optional(
        Type.String({ description: "Extension filter, e.g. '.cpp,.h,-.hpp'" }),
      ),
      caseSensitive: Type.Optional(Type.Boolean({ description: "Case-sensitive search (default: false)" })),
      excludeComments: Type.Optional(Type.Boolean({ description: "Exclude matches inside single-line comments (default: true)" })),
      contextLines: Type.Optional(
        Type.Integer({ description: "Context lines before/after each match (default 2)" }),
      ),
      limit: Type.Optional(Type.Integer({ description: "Max matches per page (default 100)" })),
      pageOffset: Type.Optional(PageOffset),
      format: OutputFormat,
    }),
    async execute(_toolCallId: any, params: any, signal: any, _onUpdate: any) {
      const { format: outputFormat, ...apiParams } = params;
      if (outputFormat === "compact") {
        apiParams.contextLines = 0; // no context lines in compact mode
      }
      const result = await callApi("/api/v1/search/content", "POST", apiParams, signal);
      let body: string;
      if (outputFormat === "compact") {
        // path:line: full matching line
        body = formatCompactMatches(result.matches);
      } else if (outputFormat === "json") {
        // Default: raw JSON for programmatic consumption
        body = JSON.stringify(result, null, 2);
      } else {
        // Legacy human-readable view
        body =
          `Found ${result.totalFiles} files with matches (showing ${result.matches.length}):\n\n` +
          formatMatches(result.matches);
      }
      const more = result.pageOffset
        ? `\n\nMore results available. Call codebeagle_search again with the same parameters plus pageOffset=${JSON.stringify(result.pageOffset)}.`
        : "";
      return {
        content: [{ type: "text", text: truncate(body + more) }],
        details: result,
      };
    },
  });

  pi.registerTool({
    name: "codebeagle_search_files",
    label: "CodeBeagle: Search File Names",
    description:
      "Search for files by name across CodeBeagle-indexed source code. " +
      "The query supports * and ? wildcards ('Factory*', '*test*.py', 'Makefile'). " +
      "If the query contains a dot, the part after the last dot is used as an extension filter. " +
      "Specify either 'location' or 'folder'. " +
      "Set format='json' (default) for JSON output, format='compact' for file paths. " +
      "Pagination: pass pageOffset from a previous response to fetch the next page.",
    promptSnippet: "Search CodeBeagle-indexed file names with wildcards",
    promptGuidelines: [
      "Use codebeagle_search_files when the user asks to find files by name across indexed source code.",
    ],
    parameters: Type.Object({
      query: Type.String({ description: "File name pattern, e.g. 'main*', '*test*.py', 'Makefile'" }),
      location: Type.Optional(Type.String({ description: "Search location name from codebeagle_list_indexes" })),
      folder: Type.Optional(Type.String({ description: "Root folder path" })),
      folderFilter: Type.Optional(Type.String({ description: "Folder filter, e.g. 'src/, -test/'" })),
      extensionFilter: Type.Optional(Type.String({ description: "Extension filter, e.g. '.py,.js'" })),
      caseSensitive: Type.Optional(Type.Boolean({ description: "Case-sensitive search (default: false)" })),
      limit: Type.Optional(Type.Integer({ description: "Max files per page (default 100)" })),
      pageOffset: Type.Optional(PageOffset),
      format: OutputFormat,
    }),
    async execute(_toolCallId: any, params: any, signal: any) {
      const { format: outputFormat, ...apiParams } = params;
      const result = await callApi("/api/v1/search/filename", "POST", apiParams, signal);
      let body: string;
      if (outputFormat === "compact") {
        body = result.files.join("\n");
      } else if (outputFormat === "json") {
        body = JSON.stringify(result, null, 2);
      } else {
        body =
          `Found ${result.totalFiles} matching files (showing ${result.files.length}):\n\n` +
          result.files.join("\n");
      }
      const more = result.pageOffset
        ? `\n\nMore results available. Call codebeagle_search_files again with the same parameters plus pageOffset=${JSON.stringify(result.pageOffset)}.`
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
      "Call this first to discover what is searchable, then pass the location name to codebeagle_search / codebeagle_search_files.",
    promptSnippet: "List CodeBeagle search locations (indexes)",
    promptGuidelines: [
      "Call codebeagle_list_indexes first when the user wants to search code, to discover available search locations.",
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
