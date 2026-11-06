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

Tests for the generated PI extension (codebeagle.ts).
"""

import os
import unittest
from ..PiExtension import (PI_EXTENSION_VERSION, PI_EXTENSION_VERSION_MARKER,
                          resolvePiExtension)

_RESOURCE_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "resources", "ai_agent"))


class TestPiExtension(unittest.TestCase):
    def test_versionMarkerReplaced(self) -> None:
        content = resolvePiExtension(_RESOURCE_DIR)
        self.assertNotIn(PI_EXTENSION_VERSION_MARKER, content)
        self.assertIn(f'const PI_VERSION = "{PI_EXTENSION_VERSION}";', content)

    def test_sendsAgentHeader(self) -> None:
        content = resolvePiExtension(_RESOURCE_DIR)
        self.assertIn('const AGENT_NAME = "pi";', content)
        self.assertIn('"x-agent": AGENT_NAME', content)

    def test_healthSendsVersion(self) -> None:
        content = resolvePiExtension(_RESOURCE_DIR)
        self.assertIn("pi-version=${encodeURIComponent(PI_VERSION)}", content)
