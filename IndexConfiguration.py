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

import os

class IndexConfiguration:
    def __init__(self,  indexGroup):
        self.indexdb =indexGroup.indexdb
        self.extensions = [self.__makeExt(ext) for ext in indexGroup.extensions.split(",")]
        self.directories = self.indexDirectories(indexGroup)
        
    def indexDirectories(self, indexGroup):
        try:
            directories = indexGroup.directories
        except KeyError:
            directories = indexGroup.directory
        return [d.strip() for d in directories.split(",")]
        
    # Return a friendly name. Currently this returns just the file name of the db without extension
    def name(self):
        filename = os.path.split(self.indexdb)[1]
        return os.path.splitext(filename)[0]
        
    def __makeExt (self, ext):
        ext = ext.strip()
        if not ext.startswith("."):
            ext = "." + ext
        return ext
        
# Returns a list of Index objects from the config
def readConfig (conf):
    indexes = []
    for c in conf:
        if c.startswith("index"):
            indexes.append(c)
    indexes.sort()
    return [IndexConfiguration(conf[c]) for c in indexes]
    

