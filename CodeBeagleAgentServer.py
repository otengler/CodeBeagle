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

import argparse
import sys
import signal
import threading
import logging
from typing import Any, List, Optional
from tools.SetupLogger import setupLogging
from tools import FileTools
# Switch to application directory to be able to load the configuration even
# if we are executed from a different working directory.
FileTools.switchToAppDir()

import AppConfig
from ai_agent.Server import AgentServer


def _parseArguments(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse the command line. All settings default to the 'agent' section of
    config.txt and can be overridden via the command line."""
    parser = argparse.ArgumentParser(
        description="Standalone AI agent server for CodeBeagle. Runs the web API "
                    "server without a GUI. All settings default to the 'agent' "
                    "section of config.txt and can be overridden via the "
                    "command line.")
    parser.add_argument("--port", type=int,
                        help="Port to listen on (default: from config.txt)")
    parser.add_argument("--bind", type=str,
                        help="Address to bind to (default: from config.txt)")
    parser.add_argument("--context-lines", type=int,
                        help="Default context lines around search matches (default: from config.txt)")
    parser.add_argument("--default-limit", type=int,
                        help="Default maximum number of results (default: from config.txt)")
    parser.add_argument("--allow-origin", type=str,
                        help="CORS Access-Control-Allow-Origin header value (default: from config.txt)")
    return parser.parse_args(args)


def _applyArgumentOverrides(args: argparse.Namespace) -> None:
    """Apply command line overrides to the agent section of the configuration.
    Only arguments that were explicitly passed override the config values."""
    agent = AppConfig.appConfig().agent
    if args.port is not None:
        agent.port = args.port
    if args.bind is not None:
        agent.bind = args.bind
    if args.context_lines is not None:
        agent.contextLines = args.context_lines
    if args.default_limit is not None:
        agent.defaultLimit = args.default_limit
    if args.allow_origin is not None:
        agent.allowOrigin = args.allow_origin

def main() -> None:
    setupLogging("codebeagle-agentserver.log")

    args = _parseArguments()
    _applyArgumentOverrides(args)

    agent = AppConfig.appConfig().agent

    server = AgentServer()
    if not server.start(agent.port):
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
        while not stopEvent.wait(0.5):
            pass
    except KeyboardInterrupt:
        pass

    server.stop()
    sys.exit(0)

if __name__ == "__main__":
    main()