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
    def __init__(self,  indexName=None,  extensions="",  directories="",  indexdb=None,  generateIndex=True):
        self.indexName = indexName
        self.generateIndex = generateIndex
        self.indexdb = indexdb
        # These list comprehensions split a string into a list making sure that an empty string returns an empty list
        self.extensions = [e for e in (self.__makeExt(e) for e in extensions.split(",")) if len(e)>0]
        self.directories = [d for d in (d.strip() for d in directories.split(",")) if len(d)>0]
        
    def extensionsAsString(self):
        return ",".join(self.extensions)
        
    def directoriesAsString(self):
        return ",".join(self.directories)
        
    # Return a display name. Either it is explicitely defined or the file part of the index database is used
    def displayName(self):
        if self.indexName:
            return self.indexName
        filename = os.path.split(self.indexdb)[1]
        return os.path.splitext(filename)[0]
        
    def __makeExt (self, ext):
        ext = ext.strip()
        if ext and not ext.startswith("."):
            ext = "." + ext
        return ext
        
    def __str__(self):
        s    = "Name       : " + self.indexName + "\n"
        s += "Indexed    : " + str(self.generateIndex) + "\n"
        s += "IndexDB    : " + self.indexdb + "\n"
        s += "Directories: " + str(self.directories) + "\n"
        s += "Extensions : " + str(self.extensions) + "\n"
        return s
        
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
        indexName = indexConf.value("indexName", None)
        generateIndex = (indexConf.value("generateIndex", "True") == "True")
        indexdb = indexConf.indexdb
        extensions = indexConf.extensions
        try:
            directories = indexConf.directories
        except KeyError:
            directories = indexConf.directory
        result.append(IndexConfiguration(indexName, extensions, directories,  indexdb,  generateIndex))
    return result
    

