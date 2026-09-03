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
 *  - codebeagle_update_file    -> POST /api/v1/index/update
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
  `Run the CodeBeagle GUI and enable the 'AI agent' or use the standalone CodeBeagleAgentServer.`;


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
    let bodyText: string;
    try {
      bodyText = await res.text();
    } catch {
      bodyText = "";
    }
    // Try to extract a server-side error message from JSON or use status text
    let msg: string;
    try {
      const err = JSON.parse(bodyText);
      msg = err.error || err.message || bodyText;
    } catch {
      msg = bodyText || res.statusText;
    }
    throw new Error(msg);
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
  fileIndex: Type.Optional(Type.Integer()),
  matchIndex: Type.Optional(Type.Integer()),
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
    description: "__TOOL_DESC_CONTENT_SEARCH__",
    promptSnippet: "__PROMPT_SNIPPET_CONTENT_SEARCH__",
    promptGuidelines: "__PROMPT_GUIDELINES_CONTENT_SEARCH__",
    parameters: Type.Object({
      query: Type.Union([
        Type.String({description: "__PARAM_DESC_CONTENT_SEARCH_QUERY__",}),
        Type.Array(Type.String(), {description: "__PARAM_DESC_CONTENT_SEARCH_QUERY__",})
      ]),
      location: Type.Union([
        Type.Object({
          folder: Type.String({ description: "__PARAM_DESC_CONTENT_SEARCH_FOLDER__", }),
          index: Type.Optional(Type.String({ description: "__PARAM_DESC_CONTENT_SEARCH_INDEX__", })),
        }),
        Type.Object({
          folder: Type.Optional(Type.String({ description: "__PARAM_DESC_CONTENT_SEARCH_FOLDER__", })),
          index: Type.String({ description: "__PARAM_DESC_CONTENT_SEARCH_INDEX__", }),
        })
      ]),
      pathFilter: Type.Optional(Type.String({ description: "__PARAM_DESC_CONTENT_SEARCH_PATHFILTER__" })),
      extensionFilter: Type.Optional(Type.String({ description: "__PARAM_DESC_CONTENT_SEARCH_EXTENSIONFILTER__" })),
      caseSensitive: Type.Optional(Type.Boolean({ description: "__PARAM_DESC_CONTENT_SEARCH_CASESENSITIVE__" })),
      excludeComments: Type.Optional(Type.Boolean({ description: "__PARAM_DESC_CONTENT_SEARCH_EXCLUDECOMMENTS__" })),
      contextLines: Type.Optional(Type.Integer({ description: "__PARAM_DESC_CONTENT_SEARCH_CONTEXTLINES__" })),
      limit: Type.Optional(Type.Integer({ description: "__PARAM_DESC_CONTENT_SEARCH_LIMIT__" })),
      pageOffset: Type.Optional(PageOffset, { description: "__PARAM_DESC_CONTENT_SEARCH_PAGEOFFSET__" }),
    }),
    async execute(_toolCallId: any, params: any, signal: any, _onUpdate: any) {
      const requestBody: any = {...params};
      requestBody.folder = params.location?.folder;
      requestBody.index = params.location?.index;
      delete requestBody.location;
      const result = await callApi("/api/v1/search/content", "POST", requestBody, signal);
      let body: string;
      if (params.contextLines === 0) {
        // Compact output: the server already returns pre-formatted strings (path:line: full matching line)
        body = (result.matches || []).join("\n");
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
    description: "__TOOL_DESC_FILE_SEARCH__",
    promptSnippet: "__PROMPT_SNIPPET_FILE_SEARCH__",
    promptGuidelines: "__PROMPT_GUIDELINES_FILE_SEARCH__",
    parameters: Type.Object({
      query: Type.Union([
        Type.String({ description: "__PARAM_DESC_FILE_SEARCH_QUERY__" }),
        Type.Array(Type.String(), { description: "__PARAM_DESC_FILE_SEARCH_QUERY__" }),
      ]),
      location: Type.Union([
        Type.Object({
          folder: Type.String({ description: "__PARAM_DESC_FILE_SEARCH_FOLDER__", }),
          index: Type.Optional(Type.String({ description: "__PARAM_DESC_FILE_SEARCH_INDEX__", })),
        }),
        Type.Object({
          folder: Type.Optional(Type.String({ description: "__PARAM_DESC_FILE_SEARCH_FOLDER__", })),
          index: Type.String({ description: "__PARAM_DESC_FILE_SEARCH_INDEX__", }),
        })
      ]),
      pathFilter: Type.Optional(Type.String({ description: "__PARAM_DESC_FILE_SEARCH_PATHFILTER__" })),
      caseSensitive: Type.Optional(Type.Boolean({ description: "__PARAM_DESC_FILE_SEARCH_CASESENSITIVE__" })),
      limit: Type.Optional(Type.Integer({ description: "__PARAM_DESC_FILE_SEARCH_LIMIT__" })),
      pageOffset: Type.Optional(PageOffset, { description: "__PARAM_DESC_FILE_SEARCH_PAGEOFFSET__" }),
    }),
    async execute(_toolCallId: any, params: any, signal: any) {
      const requestBody: any = {...params};
      requestBody.folder = params.location?.folder;
      requestBody.index = params.location?.index;
      delete requestBody.location;
      const result = await callApi("/api/v1/search/filename", "POST", requestBody, signal);
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
    description: "__TOOL_DESC_LIST_INDEXES__",
    promptSnippet: "__PROMPT_SNIPPET_LIST_INDEXES__",
    promptGuidelines: "__PROMPT_GUIDELINES_LIST_INDEXES__",
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
    description: "__TOOL_DESC_HEALTH__",
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

  pi.registerTool({
    name: "codebeagle_update_file",
    label: "CodeBeagle: Update Index for Single File",
    description: "__TOOL_DESC_UPDATE_FILE__",
    promptSnippet: "__PROMPT_SNIPPET_UPDATE_FILE__",
    promptGuidelines: "__PROMPT_GUIDELINES_UPDATE_FILE__",
    parameters: Type.Object({
      file: Type.String({ description: "Absolute file path to the file to update in the index. Example: 'C:\\src\\project\\main.cpp'" }),
    }),
    async execute(_toolCallId: any, params: any, signal: any) {
      const result = await callApi("/api/v1/index/update", "POST", { file: params.file }, signal);
      const body = JSON.stringify(result, null, 2);
      return {
        content: [{ type: "text", text: body }],
        details: result,
      };
    },
  });
}
