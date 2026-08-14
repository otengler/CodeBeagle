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

import threading
from typing import Optional
from .AgentHistory import AgentHistory
from .Server import AgentServer

_lock = threading.Lock()
_agentServer: Optional[AgentServer] = None

def setAgentServer(server: Optional[AgentServer]) -> None:
    """Register the running AgentServer instance (or None if it was stopped)."""
    global _agentServer
    with _lock:
        _agentServer = server


def agentServer() -> Optional[AgentServer]:
    """Return the registered AgentServer instance, or None if it is not running."""
    with _lock:
        return _agentServer


def agentHistory() -> Optional[AgentHistory]:
    """Return the API history of the running agent server, or None if it is not running."""
    server = agentServer()
    if server and server.httpd:
        return server.httpd.history
    return None
