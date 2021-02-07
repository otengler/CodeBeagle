# -*- coding: utf-8 -*-
"""
Copyright (C) 2012 Oliver Tengler

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

import os
from typing import Optional, Dict
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from tools.FileTools import fopen
from widgets.SyntaxHighlighter import HighlightingRules
import HighlighterConfiguration
import AppConfig

def themeDependedRuleFile(ruleFile: str) -> str:
    """
    Returns the rule file with the name of the theme appended. For "dark" and "c++.txt" that is
    "c++-dark.txt"
    """
    name, ext = os.path.splitext(ruleFile)
    return  name + "-" + str(AppConfig.appConfig().theme) + ext

def ruleFilePath(rulesFile: str) -> str:
    return os.path.join("config", rulesFile)

def rgb(r: int, g: int, b: int) -> QColor:
    return QColor(r,g,b)

def rgba(r: int, g: int, b: int, a: int) -> QColor:
    return QColor(r,g,b,a)

class RulesCache:
    """Provides a cache for HighlightingRules objects. It provides fast lookup by file name extension."""
    def __init__ (self) -> None:
        self.highlighterConfig = HighlighterConfiguration.highlighter(AppConfig.appConfig().SourceViewer)
        # A dict mapping a file extension to a HighlightingRules object
        self.highlightingRulesCache: Dict[str, HighlightingRules] = {}
        self.extensionsToRulesFile: Dict[str, str] = {}

    def getRulesByFileName(self,  name: str,  font: QFont) -> Optional[HighlightingRules]:
        """Choose a set of highlighting rules depending on the file extension."""
        ext = os.path.splitext(name)[1].lower()
        if ext.startswith("."):
            ext = ext[1:]

        if ext in self.extensionsToRulesFile:
            rulesFile = self.extensionsToRulesFile[ext]
        else:
            possibleRulesFile = self.highlighterConfig.lookup(ext)
            if not possibleRulesFile:
                return None
            themeRuleFile = themeDependedRuleFile(possibleRulesFile)
            if os.path.isfile(ruleFilePath(themeRuleFile)):
                possibleRulesFile = themeRuleFile
            rulesFile = possibleRulesFile
            self.extensionsToRulesFile[ext] = rulesFile

        if rulesFile in self.highlightingRulesCache:
            highlightingRules = self.highlightingRulesCache[rulesFile]
        else:
            highlightingRules = self.__rulesFromFile(rulesFile, font)
            self.highlightingRulesCache[rulesFile] = highlightingRules

        return highlightingRules

    def __rulesFromFile (self, rulesFile: str,  font: QFont) -> HighlightingRules:
        newRules = HighlightingRules(font)

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

                       "QColor": QColor,
                       "rgb": rgb,
                       "rgba": rgba,

                       "setColor": newRules.setColor,
                       "addKeywords" : newRules.addKeywords,
                       "addCommentRule" : newRules.addCommentRule,
                       "addRule" : newRules.addRule}

        with fopen(ruleFilePath(rulesFile)) as script:
            code = compile(script.read(), rulesFile, 'exec')
        exec(code,  globals(),  localsDict)

        return newRules

class RulesCacheStorage:
    rulesCache: Optional[RulesCache] = None

def rules() -> RulesCache:
    if not RulesCacheStorage.rulesCache:
        RulesCacheStorage.rulesCache = RulesCache()
    return RulesCacheStorage.rulesCache
