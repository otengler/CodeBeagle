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
import json
import threading
import logging
import urllib.error
import urllib.request
from typing import Callable, List, Optional
from PySide6.QtCore import QObject, Signal
from AppConfig import appConfig
from .AgentHistory import AgentHistory, HistoryEntry
from .Server import AgentServer
from tools.ExceptionTools import exceptionAsString

_lock = threading.Lock()
_agentServer: Optional[AgentServer] = None
_exitHandlerRegistered = False
# Whether an external AI agent API server (e.g. the standalone
# CodeBeagleAgentServer.exe) was detected at startup. Set once, never updated.
_externalServerRunning = False


class AgentServerEvents(QObject):
    """Signal hub which notifies the UI about AI agent server state changes."""
    serverChanged = Signal()


# Module-level signal hub. Created before QApplication, which is safe for
# plain QObject instances (no widgets or event loop required).
agentServerEvents = AgentServerEvents()


def checkExternalAgentServer() -> bool:
    """Check whether an AI agent API server is already running externally.

    The standalone CodeBeagleAgentServer.exe does not use the "enable" setting,
    so it may be running even if agentic AI search is disabled in the UI. The
    check calls the health endpoint of the configured bind address and port.

    The result is stored in this module and is NOT updated afterwards: if a
    server was found running at startup the UI must not try to start its own
    instance (the port would be blocked anyway).

    Emits events.serverChanged when the check completes so the UI can update
    the AI agent history button visibility.
    """
    global _externalServerRunning
    agent = appConfig().agent
    # The excludeFromHistory parameter keeps the probe out of the API history.
    url = f"http://{agent.bind}:{int(agent.port)}/api/v1/health?excludeFromHistory=1"
    try:
        with urllib.request.urlopen(url, timeout=1.0) as response:
            _externalServerRunning = response.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        _externalServerRunning = False
    logging.debug("External AI agent server check on %s: %s", url, _externalServerRunning)
    agentServerEvents.serverChanged.emit()
    return _externalServerRunning


def checkExternalAgentServerAsync(onFinished: Optional[Callable[[bool], None]] = None) -> threading.Thread:
    """Run the external agent server check in a background daemon thread.

    The health check is a network call with a timeout; performing it on the
    main thread would delay the application startup. The callback is invoked
    from the worker thread after the check has finished.

    Emits agentServerEvents.serverChanged when the check completes so the UI can update
    the AI agent history button visibility.
    """
    def run() -> None:
        result = checkExternalAgentServer()
        if onFinished:
            try:
                onFinished(result)
            except Exception:
                logging.exception("Callback after external agent server check failed")
    thread = threading.Thread(target=run, name="AgentServerCheck", daemon=True)
    thread.start()
    return thread


def externalServerRunning() -> bool:
    """Return whether an external AI agent server was detected at startup."""
    return _externalServerRunning


def fetchExternalHistory() -> List[HistoryEntry]:
    """Fetch the API call history from an external AI agent server.

    Uses the internal /api/v1/history endpoint which is intentionally not
    documented in API.md. Returns an empty list if the server is not running
    externally or the history cannot be retrieved (e.g. an older server
    version without the endpoint).
    """
    if not _externalServerRunning:
        return []
    agent = appConfig().agent
    url = f"http://{agent.bind}:{int(agent.port)}/api/v1/history"
    try:
        with urllib.request.urlopen(url, timeout=2.0) as response:
            data = json.loads(response.read().decode("utf-8"))
        history: List[HistoryEntry] = []
        for entry in data.get("history", []):
            history.append(HistoryEntry(
                timestamp=float(entry["timestamp"]),
                method=str(entry["method"]),
                path=str(entry["path"]),
                params=str(entry["params"]),
                statusCode=int(entry["statusCode"]),
                durationSecs=float(entry.get("durationSecs", 0.0)),
                result=str(entry.get("result", "")),
            ))
        return history
    except Exception:
        logging.warning("Failed to fetch AI agent history from external server at %s", url)
        return []

def setAgentServer(server: Optional[AgentServer]) -> None:
    """Register the running AgentServer instance (or None if it was stopped).

    Emits agentServerEvents.serverChanged so the UI can update the AI agent history
    button visibility.
    """
    global _agentServer
    with _lock:
        _agentServer = server
    agentServerEvents.serverChanged.emit()

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

    If an external server was detected at startup no own instance is started
    because the port is already in use.

    Returns True if the server is running after the call, False on failure.
    """
    if _externalServerRunning or agentServer() is not None:
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
        if _externalServerRunning:
            # The API service is provided by an external process; the UI must
            # neither start nor stop it. Treat the change as applied.
            return True
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
