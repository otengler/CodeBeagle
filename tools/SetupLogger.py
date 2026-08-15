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
"""

import logging, os, sys
from logging.handlers import RotatingFileHandler
import AppConfig

def setupLogging(logname: str) -> None:
    try:
        userDir = os.path.join(AppConfig.userDataPath(), "log")
        if not os.path.isdir(userDir):
            os.makedirs(userDir)
        logName = os.path.join(userDir, logname)
        handler = RotatingFileHandler(logName, maxBytes=1024*1024, backupCount=10)
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
        root = logging.getLogger()
        root.addHandler(handler)
        root.setLevel(logging.INFO)
        logging.info("Starting")
    except Exception as e:
        print(f"Failed to setup logging: {e}", file=sys.stderr)