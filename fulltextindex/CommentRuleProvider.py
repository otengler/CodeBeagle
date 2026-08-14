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
"""

import os
import re
from typing import Dict, List, Optional, Tuple
from fnmatch import fnmatch
from .CommentRule import CommentRule


def _parseSingleLineCommentPattern(ruleFilePath: str) -> Optional[str]:
    """
    Parse a highlighting rule file and extract the single-line comment pattern.

    Rule files contain calls like:
        addCommentRule ("//[^\n]*", "/\\*", "\\*/", Normal, darkGreen)
        addCommentRule ("#[^\n]*", None, None, Normal, darkGreen)

    Returns the single-line comment regex string, or None if not found.
    """
    try:
        with open(ruleFilePath, "r", encoding="utf-8") as f:
            content = f.read()
    except (FileNotFoundError, OSError):
        return None

    # Match addCommentRule("pattern", ...) — the first string argument
    match = re.search(r'addCommentRule\s*\(\s*"([^"]*)"', content)
    if match:
        return match.group(1)
    return None


class CommentRuleProvider:
    """
    Qt-free provider for single-line comment rules.

    Reads the SourceViewer config to map file extensions to highlighting rule
    files, then extracts the single-line comment pattern from each rule file.
    Multi-line comment patterns are NOT loaded — only single-line comments
    are filtered for performance reasons.

    Extension matching mirrors HighlighterConfiguration: patterns are matched
    with fnmatch and the pattern with the most non-wildcard characters
    (highest significance) wins. Results are cached after the first load.
    """

    def __init__(self, configDir: str = "config") -> None:
        self._configDir = configDir
        # List of (significance, extPattern, CommentRule)
        self._rules: List[Tuple[int, str, CommentRule]] = []
        # Simple extension cache: exact ext -> CommentRule
        self._cache: Dict[str, Optional[CommentRule]] = {}
        self._loaded = False

    def getCommentRule(self, filename: str) -> Optional[CommentRule]:
        """
        Return a CommentRule for the given filename, or None if no rule is known.

        Only the single-line comment pattern is populated (lineComment).
        Multi-line patterns are left as None for performance reasons.
        """
        if not filename:
            return None
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        if not ext:
            return None

        # Check exact cache first
        if ext in self._cache:
            return self._cache[ext]

        # Lazy load
        if not self._loaded:
            self._loadRules()
            self._loaded = True

        if ext in self._cache:
            return self._cache[ext]

        # Fnmatch fallback — pick the rule with the highest significance
        rule: Optional[CommentRule] = None
        bestSignificance = -1
        for significance, extPattern, candidate in self._rules:
            if significance > bestSignificance and fnmatch(ext, extPattern):
                rule = candidate
                bestSignificance = significance

        self._cache[ext] = rule
        return rule

    def _loadRules(self) -> None:
        """Read SourceViewer.txt and load comment rules for all extensions."""
        sourceViewerPath = os.path.join(self._configDir, "SourceViewer.txt")
        try:
            with open(sourceViewerPath, "r", encoding="utf-8") as f:
                content = f.read()
        except (FileNotFoundError, OSError):
            return

        self._parseSourceViewer(content)

    def _parseSourceViewer(self, content: str) -> None:
        """Parse Highlighter_XXX blocks to build extension -> rule mapping."""
        # Match blocks like:
        #   Highlighter_XXX {
        #       config = C++.txt
        #       extensions = c*,h*,inl
        #   }
        blockRe = re.compile(
            r'Highlighter_\w+\s*\{([^}]+)\}',
            re.IGNORECASE
        )
        for match in blockRe.finditer(content):
            block = match.group(1)
            configFile = self._extractValue(block, "config")
            extensions = self._extractValue(block, "extensions")
            if configFile and extensions:
                ruleFilePath = os.path.join(self._configDir, configFile)
                pattern = _parseSingleLineCommentPattern(ruleFilePath)
                if pattern:
                    compiled = re.compile(pattern)
                    rule = CommentRule(
                        lineComment=compiled,
                        multiCommentStart=None,
                        multiCommentStop=None,
                        hasTripleQuotes=False
                    )
                    for extPattern in (p.strip() for p in extensions.split(",")):
                        if extPattern:
                            significance = sum(1 for c in extPattern if c not in "*?")
                            self._rules.append((significance, extPattern, rule))
                            # Cache exact matches directly
                            if "*" not in extPattern and "?" not in extPattern:
                                self._cache[extPattern] = rule

    def _extractValue(self, block: str, key: str) -> Optional[str]:
        """Extract a config value like 'config = C++.txt' from a block."""
        match = re.search(
            rf'^\s*{re.escape(key)}\s*=\s*(.+?)\s*$',
            block,
            re.IGNORECASE | re.MULTILINE
        )
        if match:
            return match.group(1).strip()
        return None