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

import re
import types
from FileTools import fopen

class Config:
    def __init__ (self, name="", dataMap=None,  configLines=None):
        self.data = dataMap
        if not self.data:
            self.data = {}
        if name:
            self.loadFile(name)
        elif configLines:
            self.parseLines(configLines)
    
    def __getattr__ (self,  attr):
        attr = attr.lower()
        if attr in self.data:
            return self.data[attr]
        raise KeyError(attr + " does not exist in the configuration")

    def value (self, attr, default):
        attr = attr.lower()
        if attr in self.data:
            return self.data[attr]
        return default

    def __getitem__(self,a):
        return self.data[a.lower()]
        
    def __iter__(self):
        return self.data.__iter__()
    
    def __repr__ (self):
        return self.__dumpRec (self, 0)
        
    def __dumpRec (self,  config,  level):
        s = ""
        for k,v in config.data.items():
            if s:
                s += "\n"
            s = s + " " *2*level + k
            if type(v) is Config:
                s = s + " {\n"
                s = s + self.__dumpRec (v,  level+1)
                s = s + "\n" + " " *2*level + "}"
            else:
                s = s + " = " + v
        return s
        
    def setValue(self, key, value):
        if type(value) is Config:
            self.data[key.lower()] = value
        else:
            self.data[key.lower()] = str(value)
            
    def loadFile (self, name):
        with fopen(name) as file:
            self.parseLines ((line for line in file.readlines()))
            
    def parseLines(self, lines):
        if not type(lines) is types.GeneratorType:
            raise TypeError("lines must be a generator type")
        for line in lines:
            line = line.strip()
            try:
                if not line or line.startswith("#"): # ignore empty lines and comments
                    pass
                elif line.startswith("import"):
                    self.__handleImport(line)
                elif line.find("=") != -1:
                    key, value = line.split("=")
                    self.data[key.lower().strip()] = value.strip()
                elif line.startswith("}"):
                    return
                elif line.endswith("{"):
                    groupname = line.split("{")[0].strip().lower()
                    if groupname in self.data:
                        group = self.data[groupname]
                        group.parseLines (lines)
                    else:
                        self.data[groupname] = Config(configLines=lines)
            except:
                print ("Do not understand line: " + line)
                raise

    def __handleImport (self, line):
        # syntax: import file as groupname
        # This imports the file into the group 'groupname'. If the group already exists it is merged
        importTokens = re.match("import\\W+([\\w\\\\/\\.]+)\\W+as\\W+(\\w+)", line)
        if importTokens:
            groupname = importTokens.group(2).lower()
            filename = importTokens.group(1)
            try:
                if groupname in self.data:
                    group = self.data[groupname]
                    group.loadFile (filename)
                else:
                    self.data[groupname] = Config(filename)
            except IOError:
                pass
        else:
            # syntax: import file
            # This imports all properties of the file into the current config. 
            importTokens = re.match("import\\W+([\\w\\\\/\\.]+)", line)
            if not importTokens:
                raise RuntimeError("wrong import line")
            try:
                Config(importTokens.group(1), dataMap=self.data)
            except IOError:
                pass


    
    
    
