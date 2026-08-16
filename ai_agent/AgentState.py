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

import atexit
import threading
import logging
from typing import Optional
from .AgentHistory import AgentHistory
from .Server import AgentServer
from tools.ExceptionTools import exceptionAsString

_lock = threading.Lock()
_agentServer: Optional[AgentServer] = None
_exitHandlerRegistered = False

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

def stopAgentServer() -> None:
    """Stop the running agent server, if any."""
    server = agentServer()
    if server is not None:
        server.stop()
        setAgentServer(None)

def _stopAtExit() -> None:
    stopAgentServer()

def _registerStopAtExit() -> None:
    global _exitHandlerRegistered
    if not _exitHandlerRegistered:
        _exitHandlerRegistered = True
        atexit.register(_stopAtExit)

def startAgentServer(port: int) -> bool:
    """Start the agent server from the current configuration if it is not already running.

    Returns True if the server is running after the call, False on failure.
    """
    if agentServer() is not None:
        return True
    server = AgentServer()
    if server.start(port):
        setAgentServer(server)
        _registerStopAtExit()
        return True
    return False

def applyAgentServerChanges(enabled: bool, port: int) -> bool:
    """Start or stop the AI agent server according to the new settings.

    If the server is already running but the port changed it is restarted so
    that the new settings take effect immediately.
    """
    try:
        running = agentServer()
        if enabled:
            if running is not None and int(running.config.port) != port:
                stopAgentServer()
                running = None
            if running is None and not startAgentServer(port):
                return False
        else:
            stopAgentServer()
        return True
    except Exception as e:
        logging.error("Failed to start or stop the agent server %s" % exceptionAsString(None))
        return False
