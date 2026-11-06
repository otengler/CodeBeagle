"""Extract the CHANGES section for a given release version.

Usage: python tools/ReleaseNotes.py <version> [changes-file]

Prints the body (bullet lines) of the first matching version section, or
nothing when the version has no entry.
"""

from __future__ import annotations

import re
import sys

_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def extractSection(changesText: str, version: str) -> str:
    lines: list[str] = []
    collecting = False
    for rawLine in changesText.splitlines():
        line = rawLine.rstrip()
        if not collecting:
            if line == version and _VERSION_PATTERN.match(line):
                collecting = True
            continue
        if _VERSION_PATTERN.match(line):
            break
        lines.append(rawLine)

    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: ReleaseNotes.py <version> [changes-file]", file=sys.stderr)
        return 2
    version = sys.argv[1]
    changesFile = sys.argv[2] if len(sys.argv) > 2 else "CHANGES"
    with open(changesFile, encoding="utf-8") as handle:
        changesText = handle.read()
    section = extractSection(changesText, version)
    if section:
        print(section)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
