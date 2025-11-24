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

from typing import Optional, Pattern
from dataclasses import dataclass


@dataclass
class CommentRule:
    """
    Defines comment patterns for a file type.
    Contains compiled regex patterns for detecting comments.
    """
    lineComment: Optional[Pattern]
    multiCommentStart: Optional[Pattern]
    multiCommentStop: Optional[Pattern]
