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

# No index wanted
NoIndexWanted = 0
# Only update index via CodeBeagle UI
ManualIndexUpdate = 1
# Update index when UpdateIndex.exe is run
TriggeredIndexUpdate = 2
# Keep index permanently up to date by watching the file system for changes
AutomaticIndexUpdate = 3

def indexUpdateModeToString(mode):
    if mode == 1:
        return "NoIndexWanted"
    elif mode == 2:
        return "ManualIndexUpdate"
    elif mode == 3:
        return "TriggeredIndexUpdate"
    elif mode == 4:
        return "AutomaticIndexUpdate"
    return "Unknown"

class IndexConfiguration:
    def __init__(self, indexName="", extensions="", directories="", dirExcludes="", indexdb="", indexUpdateMode=TriggeredIndexUpdate):
        self.indexName = indexName
        self.indexUpdateMode = indexUpdateMode
        self.indexdb = indexdb
        # Add the extensions into a set. This makes the lookup if an extension matches faster.
        self.extensions = set()
        for ext in (self.__makeExt(e) for e in extensions.split(",") if len(e) > 0):
            self.extensions.add(ext)
        # These list comprehensions split a string into a list making sure that an empty string returns an empty list
        self.directories = [d for d in (d.strip() for d in directories.split(",")) if len(d) > 0]
        self.dirExcludes = [d for d in (d.strip() for d in dirExcludes.split(",")) if len(d) > 0]

    def generatesIndex(self):
        return self.indexUpdateMode != NoIndexWanted

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

    def __makeExt(self, ext):
        ext = ext.strip()
        if ext and not ext.startswith("."):
            ext = "." + ext
        return ext.lower()

    def __str__(self):
        result = "Name       : " + self.indexName + "\n"
        result += "Index mode : " + indexUpdateModeToString(self.indexUpdateMode) + "\n"
        result += "IndexDB    : " + self.indexdb + "\n"
        result += "Directories: " + str(self.directories) + "\n"
        result += "Excludes   : " + str(self.dirExcludes) + "\n"
        result += "Extensions : " + str(self.extensions) + "\n"
        return result

    def __eq__(self, other):
        return self.indexName == other.indexName and \
            self.indexUpdateMode == other.indexUpdateMode and \
            self.indexdb == other.indexdb and \
            self.directories == other.directories and \
            self.dirExcludes == other.dirExcludes and \
            self.extensions == other.extensions

# Configurates the type information for the index configuration
def indexTypeInfo(config):
    config.setType("indexName", Config.typeDefaultString(""))
    config.setType("generateIndex", Config.typeDefaultBool(True)) # kept for compatibility
    config.setType("indexUpdateMode", Config.typeDefaultInt(TriggeredIndexUpdate))
    config.setType("dirExcludes", Config.typeDefaultString(""))

# Returns a list of Index objects from the config
def readConfig(conf):
    indexes = []
    for group in conf:
        if group.startswith("index"):
            indexes.append(group)
    indexes.sort()

    result = []
    for group in indexes:
        indexConf = conf[group]
        indexTypeInfo(indexConf)
        if "indexUpdateMode" in indexConf: # indexUpdateMode is newer, "generateIndex" was before
            indexUpdateMode = indexConf.indexUpdateMode
        elif indexConf.generateIndex:
            indexUpdateMode = TriggeredIndexUpdate
        else:
            indexUpdateMode = NoIndexWanted
        indexName = indexConf.indexName
        indexdb = indexConf.indexdb
        extensions = indexConf.extensions
        try:
            directories = indexConf.directories
        except AttributeError:
            directories = indexConf.directory
        dirExceptions = indexConf.dirExcludes
        result.append(IndexConfiguration(indexName, extensions, directories, dirExceptions, indexdb, indexUpdateMode))
    return result


