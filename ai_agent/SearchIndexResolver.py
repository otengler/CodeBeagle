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
from fnmatch import fnmatch
from typing import List, Optional
from tools import Config
from fulltextindex import IndexConfiguration
from fulltextindex.Query import createExtensionFilter

class SearchIndexResolver:
    """
    Resolves an IndexConfiguration for a search request.

    A search request either names a location explicitly or passes a folder.
    If several configurations qualify (e.g. multiple configurations cover the
    same folder), one with a matching index type is preferred over one without,
    and among those one whose indexed extensions cover the extension filter.
    """

    def __init__(self, config: Config.Config) -> None:
        self._config = config

    def resolve(self, location: Optional[str] = None,
                folder: Optional[str] = None,
                searchType: str = "content",
                extensionFilter: str = "") -> Optional[IndexConfiguration.IndexConfiguration]:
        """
        Resolve an IndexConfiguration from either a location name or a folder path.

        searchType is "content" or "filename" and controls which configurations
        are considered indexed: isContentIndexed() or isFileNameIndexed().
        If an extensionFilter is given, configurations whose indexed extensions
        cover the filter are preferred over configurations that do not.

        If neither location nor folder is specified, a ValueError is raised:
        the caller must explicitly choose a search location.
        If several configurations qualify, one that has a matching index is preferred
        over one without a matching index.
        """
        if location and folder:
            raise ValueError("Only one of 'location' or 'folder' may be specified")

        indexConfigs = IndexConfiguration.readConfig(self._config) or []

        if location:
            for conf in indexConfigs:
                if conf.displayName() == location:
                    return conf

            raise ValueError(f"Search location '{location}' not found")

        if folder:
            # Resolve by folder: find all locations whose source directory
            # equals or is a parent of the requested folder and that do not
            # exclude the folder (or any directory on the path to it).
            candidates = [
                conf for conf in indexConfigs
                if self._folderCovered(conf, folder)
            ]
            if candidates:
                return self._preferIndexed(candidates, searchType, extensionFilter)

            return None
        
        raise ValueError("Either 'location' or 'folder' must be specified")       

    def checkExtensionFilter(self, extensionFilter: str,
                             indexConf: IndexConfiguration.IndexConfiguration) -> None:
        """
        Verify that all positive extensions in the filter are covered by the config.

        Raises ValueError if an extension pattern in the filter does not match
        any extension indexed by the config. Negative (excluded) extensions are
        not checked since they only narrow results.
        """
        if self._extensionsCovered(indexConf, extensionFilter):
            return
        parts = createExtensionFilter(extensionFilter)
        uncovered = [ext for ext, isPositive in parts
                     if isPositive and not any(fnmatch(confExt, ext) for confExt in indexConf.extensions)]
        raise ValueError(
            f"Extension(s) {', '.join(uncovered)} from filter '{extensionFilter}' are not indexed "
            f"in search location '{indexConf.displayName()}' "
            f"(indexed extensions: {', '.join(sorted(indexConf.extensions))})")

    def _folderCovered(self, conf: IndexConfiguration.IndexConfiguration, folder: str) -> bool:
        """
        True if a walk from one of the config's source directories would reach folder.

        Mirrors IndexUpdater.genFind: only the final folder itself is checked
        against dirExcludes (os.walk descends into subdirectories even if a
        parent is excluded). Matching uses fnmatch, case-insensitively, and
        supports wildcards (*, ?).
        """
        normFolder = os.path.normpath(folder).lower()
        excludes = [e.lower() for e in conf.dirExcludes]
        if any(fnmatch(normFolder, ex) for ex in excludes):
            return False
        for srcDir in conf.directories:
            normalizedSrc = os.path.normpath(srcDir)
            if normFolder == normalizedSrc.lower() or normFolder.startswith(normalizedSrc.lower() + os.sep):
                return True
        return False

    def _extensionsCovered(self, indexConf: IndexConfiguration.IndexConfiguration,
                           extensionFilter: str) -> bool:
        """True if all positive extension patterns of the filter are indexed by the config."""
        if not extensionFilter:
            return True
        parts = createExtensionFilter(extensionFilter)
        for ext, isPositive in parts:
            if not isPositive:
                continue
            if not any(fnmatch(confExt, ext) for confExt in indexConf.extensions):
                return False
        return True

    def _preferIndexed(self, configs: List[IndexConfiguration.IndexConfiguration],
                       searchType: str = "content",
                       extensionFilter: str = "") -> IndexConfiguration.IndexConfiguration:
        """
        Prefer a config with a matching index for the given search type.

        Among configs with a matching index type, prefer one whose indexed
        extensions cover the extensionFilter. Falls back to the first config
        if no config matches.
        """
        if searchType == "filename":
            indexed = [c for c in configs if c.isFileNameIndexed()]
        else:
            indexed = [c for c in configs if c.isContentIndexed()]
        for conf in indexed:
            if self._extensionsCovered(conf, extensionFilter):
                return conf
        return indexed[0] if indexed else configs[0]
