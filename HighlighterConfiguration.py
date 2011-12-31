# -*- coding: utf-8 -*-
"""
Copyright (C) 2011 Oliver Tengler

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

from fnmatch  import fnmatch
import Config
import unittest

class ExtensionMapping:
    def __init__(self,  extPattern,  configFile):
        # The significance is the number of none wildcard chars. E.g. CPP has a significance of 3, C* has only 1.
        self.significance = sum ((lambda c: c!="*" and c!="?")(c) for c in extPattern)
        # A pattern which matches the extension
        self.extPattern = extPattern
        self.configFile = configFile
       
    # Returns the significance if the configuration matches the pattern , -1 otherwise
    def match (self, ext):
        if ext.startswith("."):
            ext = ext[1:]
        if fnmatch (ext,  self.extPattern):
            return self.significance
        return -1
    
# Contains a list of ExtensionMapping objects. Its main function is to lookup the right ExtensionMapping for 
#  a given extension.
class Highlighter:    
    def __init__(self, conf):
        self.mappings = self.readConfig (conf)
        
    #Highlighter_Default {
    #    config = C++.txt
    #    extensions = *
    #}
    def readConfig (self,  conf):
        mappings = []
        for c in conf:
            if c.startswith("highlighter"):
                settings = conf[c]
                extensions = settings.extensions
                configFile = settings.config
                for pattern in extensions.split(","):
                    mappings.append(ExtensionMapping(pattern,  configFile))
        return mappings
        
    # Lookup highlighter by extension
    def lookup (self, ext):
        matches = []
        for mapping in self.mappings:
            significance = mapping.match(ext)
            if significance != -1:
                matches.append((significance, mapping))
        # Sort by significance
        matches.sort(key=lambda i: i[0], reverse=True)
        if len(matches):
            return matches[0][1].configFile
        return None

_highlighter = None

def highlighter(conf):
    global _highlighter
    if not _highlighter:
        _highlighter = Highlighter(conf)
    return _highlighter

#Highlighter_Default {
#    config = default.txt
#    extensions = *
#}
#
#Highlighter_C {
#    config = C.txt
#    extensions = c*,h*,inl
#}
#
#Highlighter_CPP {
#    config = C++.txt
#    extensions = cpp
#}

class TestHighlighterConfig(unittest.TestCase):
    def test(self):
        h = highlighter(Config.Config("tests\\SourceViewer.txt"))
        self.assertEqual (h.lookup("py"),  "default.txt")
        self.assertEqual (h.lookup("cpp"),  "C++.txt")
        self.assertEqual (h.lookup("CPP"),  "C++.txt")
        self.assertEqual (h.lookup("c"),  "C.txt")
        self.assertEqual (h.lookup("c"),  "C.txt")

if __name__ == "__main__":
    unittest.main()
    
    