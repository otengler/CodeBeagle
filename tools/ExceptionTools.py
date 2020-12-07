# -*- coding: utf-8 -*-
"""
Copyright (C) 2012 Oliver Tengler

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from typing import Optional

def exceptionAsString (limit: Optional[int]=5) -> str:
    """Prints the current exception into a string"""
    import sys
    import io
    import traceback
    exc_type, exc_value, exc_traceback = sys.exc_info()
    memFile = io.StringIO()
    traceback.print_exception(exc_type, exc_value, exc_traceback, limit=limit, file=memFile)
    return memFile.getvalue()
