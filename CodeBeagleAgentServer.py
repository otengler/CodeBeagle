#! /usr/bin/python3
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

Standalone AI agent server for CodeBeagle.

Runs the web API server without a GUI. Indexes can be updated using the
existing UpdateIndex.py tool. The server reads configuration from config.txt
(and UserConfig.txt) and respects the agent section.
"""

import sys
import signal
import threading
import logging
from typing import Any
from tools.SetupLogger import setupLogging
from tools import FileTools
# Switch to application directory to be able to load the configuration even
# if we are executed from a different working directory.
FileTools.switchToAppDir()

import AppConfig
from ai_agent.Server import AgentServer

def main() -> None:
    setupLogging("codebeagle-agentserver.log")

    agent = AppConfig.appConfig().agent
    server = AgentServer()
    if not server.start():
        logging.error("Failed to start AI agent server. See log for details.")
        sys.exit(1)
    from ai_agent.AgentState import setAgentServer
    setAgentServer(server)

    print(f"CodeBeagle AI agent server listening on http://{agent.bind}:{agent.port}")
    print("Press Ctrl+C to stop.")

    # Set up signal handling for graceful shutdown
    stopEvent = threading.Event()

    def handleSignal(signum: int, frame: Any) -> None:
        print("\nShutting down...")
        stopEvent.set()

    signal.signal(signal.SIGINT, handleSignal)
    signal.signal(signal.SIGTERM, handleSignal)

    try:
        stopEvent.wait()
    except KeyboardInterrupt:
        pass

    server.stop()
    sys.exit(0)

if __name__ == "__main__":
    main()