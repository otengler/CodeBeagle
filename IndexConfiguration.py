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
import Config

class IndexConfiguration:
    def __init__(self,  indexName="",  extensions="",  directories="",  dirExcludes="",  indexdb="",  generateIndex=True):
        self.indexName = indexName
        self.generateIndex = generateIndex
        self.indexdb = indexdb
        # Add the extensions into a set. This makes the lookup if an extension matches faster.
        self.extensions = set()
        for ext in (self.__makeExt(e) for e in extensions.split(",") if len(e)>0):
            self.extensions.add(self.__makeExt(ext))
        # These list comprehensions split a string into a list making sure that an empty string returns an empty list
        self.directories = [d for d in (d.strip() for d in directories.split(",")) if len(d)>0]
        self.dirExcludes = [d for d in (d.strip() for d in dirExcludes.split(",")) if len(d)>0]
        
    def extensionsAsString(self):
        return ",".join(self.extensions)
        
    def directoriesAsString(self):
        return ",".join(self.directories)
        
    def dirExcludesAsString(self):
        return ",".join(self.dirExcludes)
        
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
        s += "Excludes   : " + str(self.dirExcludes) + "\n"
        s += "Extensions : " + str(self.extensions) + "\n"
        return s
        
# Configurates the type information for the index configuration
def indexTypeInfo (config):
    config.setType("indexName", Config.typeDefaultString(""))
    config.setType("generateIndex", Config.typeDefaultBool(True))
    config.setType("dirExcludes", Config.typeDefaultString(""))
        
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
        indexTypeInfo (indexConf)
        
        indexName = indexConf.indexName
        generateIndex = indexConf.generateIndex
        indexdb = indexConf.indexdb
        extensions = indexConf.extensions
        try:
            directories = indexConf.directories
        except AttributeError:
            directories = indexConf.directory
        dirExceptions = indexConf.dirExcludes
        result.append(IndexConfiguration(indexName, extensions, directories,  dirExceptions,  indexdb,  generateIndex))
    return result
    

