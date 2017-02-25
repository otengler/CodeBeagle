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

import os
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from FileTools import fopen
import HighlightingTextEdit
import HighlighterConfiguration
from AppConfig import appConfig

class RulesCache:
    """Provides a cache for HighlightingRules objects. It provides fast lookup by file name extension."""
    def __init__ (self):
        self.highlighterConfig = HighlighterConfiguration.highlighter(appConfig().SourceViewer)
        # A dict mapping a file extension to a HighlightingRules object
        self.highlightingRulesCache = {}
        self.extensionsToRulesFile = {}

    def getRulesByFileName(self,  name,  font):
        """Choose a set of highlighting rules depending on the file extension."""
        ext = os.path.splitext(name)[1].lower()
        if ext.startswith("."):
            ext = ext[1:]

        if ext in self.extensionsToRulesFile:
            rulesFile = self.extensionsToRulesFile[ext]
        else:
            rulesFile = self.highlighterConfig.lookup(ext)
            self.extensionsToRulesFile[ext] = rulesFile

        if rulesFile in self.highlightingRulesCache:
            highlightingRules = self.highlightingRulesCache[rulesFile]
        else:
            highlightingRules = self.rulesFromFile(rulesFile,  font)
            self.highlightingRulesCache[rulesFile] = highlightingRules

        return highlightingRules

    def rulesFromFile (self, rulesFile,  font):
        rules = HighlightingTextEdit.HighlightingRules(font)

        localsDict = { "Light" : QFont.Light,
                       "Normal" : QFont.Normal,
                       "DemiBold" : QFont.DemiBold,
                       "Bold" : QFont.Bold,
                       "Black" : QFont.Black,

                       "white" : Qt.white,
                       "black" : Qt.black,
                       "red" : Qt.red,
                       "darkRed" : Qt.darkRed,
                       "green" : Qt.green,
                       "darkGreen" : Qt.darkGreen,
                       "blue" : Qt.blue,
                       "darkBlue" : Qt.darkBlue,
                       "cyan" : Qt.cyan,
                       "darkCyan" : Qt.darkCyan,
                       "magenta" : Qt.magenta,
                       "darkMagenta" : Qt.darkMagenta,
                       "yellow" : Qt.yellow,
                       "darkYellow" : Qt.darkYellow,
                       "gray" : Qt.gray,
                       "darkGray" : Qt.darkGray,
                       "lightGray" : Qt.lightGray,

                       "addKeywords" : rules.addKeywords,
                       "addCommentRule" : rules.addCommentRule,
                       "addRule" : rules.addRule}

        with fopen(os.path.join("config", rulesFile)) as script:
            code = compile(script.read(), rulesFile, 'exec')
        exec(code,  globals(),  localsDict)

        return rules

_rulesCache = None

def rules():
    global _rulesCache
    if not _rulesCache:
        _rulesCache = RulesCache()
    return _rulesCache
