# -*- coding: utf-8 -*-
"""
Copyright (C) 2011 Oliver Tengler

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
from enum import IntEnum
from typing import Set,List,cast
from tools import Config
from tools.FileTools import correctPath

class IndexMode(IntEnum):
    # No index wanted
    NoIndexWanted = 0
    # Only update index via CodeBeagle UI
    ManualIndexUpdate = 1
    # Update index when UpdateIndex.exe is run
    TriggeredIndexUpdate = 2
    # Keep index permanently up to date by watching the file system for changes
    AutomaticIndexUpdate = 3

class IndexType(IntEnum):
    # Index file content
    FileContent = 0
    # Index file names
    FileName = 1
    # Both file content and file names
    FileContentAndName = 2

def indexTypeToString(indexType: IndexType) -> str:
    if indexType == IndexType.FileContent:
        return "file content"
    if indexType == IndexType.FileContentAndName:
        return "file content and name"
    if indexType == IndexType.FileName:
        return "file name"
    return "Unknown"

class IndexConfiguration:
    def __init__(self, indexName:str="", extensions:str="", directories:str="", dirExcludes:str="", indexdb:str="", 
                 indexUpdateMode:IndexMode=IndexMode.TriggeredIndexUpdate, indexType:IndexType=IndexType.FileContentAndName) -> None:
        self.indexName = indexName
        self.indexUpdateMode = IndexMode(indexUpdateMode)
        self.indexType = IndexType(indexType)
        self.indexdb = correctPath(indexdb)
        # Add the extensions into a set. This makes the lookup if an extension matches faster.
        self.extensions: Set[str] = set()
        for ext in (self.__makeExt(e) for e in extensions.split(",") if len(e) > 0):
            self.extensions.add(ext)
        # These list comprehensions split a string into a list making sure that an empty string returns an empty list
        self.directories = [correctPath(d) for d in (d.strip() for d in directories.split(",")) if len(d) > 0]
        self.dirExcludes = [correctPath(d) for d in (d.strip() for d in dirExcludes.split(",")) if len(d) > 0]

    def generatesIndex(self) -> bool:
        return self.indexUpdateMode != IndexMode.NoIndexWanted
    def isContentIndexed(self) -> bool:
        if not self.generatesIndex():
            return False
        return self.indexType == IndexType.FileContent or self.indexType == IndexType.FileContentAndName
    def isFileNameIndexed(self) -> bool:
        if not self.generatesIndex():
            return False
        return self.indexType == IndexType.FileName or self.indexType == IndexType.FileContentAndName

    def extensionsAsString(self) -> str:
        return ",".join(sorted(self.extensions))

    def directoriesAsString(self) -> str:
        return ",".join(self.directories)

    def dirExcludesAsString(self) -> str:
        return ",".join(self.dirExcludes)

    # Return a display name. Either it is explicitely defined or the file part of the index database is used
    def displayName(self) -> str:
        if self.indexName:
            return self.indexName
        filename = os.path.split(self.indexdb)[1]
        return os.path.splitext(filename)[0]

    def __makeExt(self, ext:str) -> str:
        ext = ext.strip()
        if ext:
            if ext.startswith("*."):
                ext = ext[2:]
            elif not ext.startswith("."):
                ext = "." + ext
        return ext.lower()

    def __str__(self) -> str:
        result = "Name       : " + self.indexName + "\n"
        result += "Index mode : " + self.indexUpdateMode.name + "\n"
        result += "Index type: " + self.indexType.name + "\n"
        result += "IndexDB    : " + self.indexdb + "\n"
        result += "Directories: " + str(self.directories) + "\n"
        result += "Excludes   : " + str(self.dirExcludes) + "\n"
        result += "Extensions : " + str(self.extensions) + "\n"
        return result

    def __eq__(self, other: object) -> bool:
        if not type(other) is IndexConfiguration:
            return False

        other = cast(IndexConfiguration, other)

        return self.indexName == other.indexName and \
               self.indexUpdateMode == other.indexUpdateMode and \
               self.indexType == other.indexType and \
               self.indexdb == other.indexdb and \
               self.directories == other.directories and \
               self.dirExcludes == other.dirExcludes and \
               self.extensions == other.extensions

# Configurates the type information for the index configuration
def indexTypeInfo(config: Config.Config) -> None:
    config.setType("indexName", Config.typeDefaultString(""))
    config.setType("generateIndex", Config.typeDefaultBool(True)) # kept for compatibility
    config.setType("indexUpdateMode", Config.typeDefaultInt(IndexMode.TriggeredIndexUpdate))
    config.setType("indexType", Config.typeDefaultInt(IndexType.FileContent))
    config.setType("dirExcludes", Config.typeDefaultString(""))

# Returns a list of Index objects from the config
def readConfig(conf: Config.Config) -> List[IndexConfiguration]:
    indexes = []
    for group in conf:
        if group.startswith("index"):
            indexes.append(group)
    indexes.sort()

    result: List[IndexConfiguration] = []
    for group in indexes:
        indexConf = conf[group]
        indexTypeInfo(indexConf)
        if "indexUpdateMode" in indexConf: # indexUpdateMode is newer, "generateIndex" was before
            indexUpdateMode = indexConf.indexUpdateMode
        elif indexConf.generateIndex:
            indexUpdateMode = IndexMode.TriggeredIndexUpdate
        else:
            indexUpdateMode = IndexMode.NoIndexWanted
        indexType = indexConf.indexType
        indexName = indexConf.indexName
        indexdb = indexConf.indexdb
        extensions = indexConf.extensions
        try:
            directories = indexConf.directories
        except AttributeError:
            directories = indexConf.directory
        dirExceptions = indexConf.dirExcludes
        result.append(IndexConfiguration(indexName, extensions, directories, dirExceptions, indexdb, indexUpdateMode, indexType))
    return result