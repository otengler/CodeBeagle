# -*- coding: utf-8 -*-
"""
Copyright (C) 2025 Oliver Tengler

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

import threading
import os
from typing import Dict, Tuple, List, Optional, cast

class Keyword:
    def __init__(self, identifier: int, name: str) -> None:
        self.id = identifier
        self.name = name

    def __repr__(self) -> str:
        return "%s (%u)" % (self.name, self.id)

    def __eq__(self, other: object) -> bool:
        if not type(other) is Keyword:
            return False

        other = cast(Keyword, other)
        return self.id == other.id and self.name == other.name

# Module-level cache for keyword lookups, shared across all FullTextIndex instances
# Cache key: (database_location, keyword) -> List[Keyword]
_keywordCache: Dict[Tuple[str, str], List[Keyword]] = {}
# Track database modification times for cache invalidation
_dbModTimes: Dict[str, float] = {}
_keywordCacheLock = threading.Lock()

def checkAndInvalidateKeywordsCache(dbLocation: str) -> None:
    """Check if database has been modified and invalidate cache if needed."""
    try:
        currentModTime = os.path.getmtime(dbLocation)
        with _keywordCacheLock:
            lastModTime = _dbModTimes.get(dbLocation)
            if lastModTime is None or currentModTime > lastModTime:
                # Database modified or first access - clear cache entries for this database
                keysToRemove = [key for key in _keywordCache.keys() if key[0] == dbLocation]
                for key in keysToRemove:
                    del _keywordCache[key]
                _dbModTimes[dbLocation] = currentModTime
    except OSError:
        # Database file doesn't exist or can't be accessed - ignore
        pass

def getCachedKeywords(dbLocation: str, keyword: str) -> Optional[List[Keyword]]:
    """Get cached keywords for a given database and keyword string."""
    with _keywordCacheLock:
        return _keywordCache.get((dbLocation, keyword))

def setCachedKeywords(dbLocation: str, keyword: str, keywords: List[Keyword]) -> None:
    """Cache keywords for a given database and keyword string."""
    with _keywordCacheLock:
        _keywordCache[(dbLocation, keyword)] = keywords
