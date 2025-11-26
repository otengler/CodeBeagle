# -*- coding: utf-8 -*-
"""
Copyright (C) 2020 Oliver Tengler

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

from abc import ABC,abstractmethod
from typing import Iterable, List
import bisect

class MatchPosition:
    def __init__(self, index: int, length: int=0) -> None:
        self.index = index
        self.length = length

    def __lt__ (self, other: 'MatchPosition') -> bool:
        return self.index < other.index
    
    def __iter__(self):
        # return values in order you want to unpack
        yield self.index
        yield self.length

class IStringMatcher(ABC):
    # Yields all matches in data. Each match is returned as the touple (position,length)
    @abstractmethod
    def matches(self, data: str, filename: str = "") -> Iterable[MatchPosition]:
        pass
