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
    def __init__(self,  indexName=None,  extensions=None,  directories=None,  indexdb=None,  updateIndex=True):
        self.indexName = indexName
        self.updateIndex = updateIndex
        self.indexdb = indexdb
        self.extensions = [self.__makeExt(ext) for ext in extensions.split(",")]
        self.directories = [d.strip() for d in directories.split(",")]
        
    # Return a display name. Either it is explicitely defined or the file part of the index database is used
    def displayName(self):
        if self.indexName:
            return self.indexName
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
    for group in conf:
        if group.startswith("index"):
            indexes.append(group)
    indexes.sort()
    
    result = []
    for group in indexes:
        indexConf= conf[group]
        indexdb = indexConf.indexdb
        extensions = indexConf.extensions
        try:
            directories = indexConf.directories
        except KeyError:
            directories = indexConf.directory
        result.append(IndexConfiguration(indexdb=indexdb, extensions=extensions, directories=directories))
    return result
    

