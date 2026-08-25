# -*- coding: utf-8 -*-
"""
Copyright (C) 2021 Oliver Tengler

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

import unittest
import os, shutil

testmodules = [
    'widgets.SyntaxHighlighter',
    'widgets.SourceHighlightingTextEdit',
    'HighlighterConfiguration',
    'MatchesOverview',
    'tools.Config',
    'tools.FileTools',
    'fulltextindex.Query',
    'fulltextindex.CommentDetection',
    'fulltextindex.testsuite',
    'BookmarkStorage'
    ]

agentTestmodules = [
    'ai_agent.tests',
    'ai_agent.mcp_server.tests'
    ]

def getModulePath() -> str:
    import __main__
    return os.path.split(__main__.__file__)[0]

if __name__ == "__main__":
    root = getModulePath ()
    os.chdir(root)
    shutil.copytree(os.path.join("ai_agent", "resources"), "resources", dirs_exist_ok=True)

    testPath = os.path.join(root, "tests")
    os.chdir(testPath)

    suite = unittest.TestSuite()

    for t in testmodules:
        suite.addTest(unittest.defaultTestLoader.loadTestsFromName(t))

    for t in agentTestmodules:
        suite.addTest(unittest.defaultTestLoader.loadTestsFromName(t))

    unittest.TextTestRunner().run(suite)

