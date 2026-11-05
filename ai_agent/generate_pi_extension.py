# -*- coding: utf-8 -*-
"""
Copyright (C) 2026 Oliver Tengler

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Helper script: print the PI extension (codebeagle.ts) with all __...__ markers
resolved from tool_desc.json using the standard agent server port.

Usage (from the repository root):
    python ai_agent/generate_pi_extension.py > codebeagle.ts

The script reads the tracked resources under ai_agent/resources/ai_agent.
"""

import argparse
import os
import sys
from typing import List, Optional

# Allow running this file directly (python ai_agent/generate_pi_extension.py).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from ai_agent.PiExtension import DEFAULT_PORT, resolvePiExtension

# Tracked source resources bundled into resources/ai_agent during the build.
_SOURCE_RESOURCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "ai_agent")

def _findResourceDir(requested: str) -> str:
    if requested:
        return requested
    candidates = [
        _SOURCE_RESOURCE_DIR,
        os.path.join(_REPO_ROOT, "resources", "ai_agent"),
    ]
    for candidate in candidates:
        if os.path.isfile(os.path.join(candidate, "tool_desc.json")):
            return candidate
    return candidates[0]

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Print codebeagle.ts with all tool/parameter markers resolved.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"Agent server port baked into the extension (default: {DEFAULT_PORT}).")
    parser.add_argument("--resource-dir", default="",
                        help="Directory containing tool_desc.json and pi/extensions/codebeagle.ts.")
    parser.add_argument("-o", "--output", default="",
                        help="Write to this file instead of stdout.")
    args = parser.parse_args(argv)

    resourceDir = _findResourceDir(args.resource_dir)
    try:
        content = resolvePiExtension(resourceDir, args.port)
    except Exception as e:
        print(f"error: could not resolve PI extension: {e}", file=sys.stderr)
        return 1

    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
    else:
        sys.stdout.write(content)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
