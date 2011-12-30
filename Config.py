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

class Config:
    def __init__ (self, name="", dataMap=None,  configLines=None):
        self.name = name
        self.data = dataMap
        if not self.data:
            self.data = {}
        if self.name:
            self.__load()
        elif configLines:
            self.__parseConfig(configLines)
    
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
        return self.data[a]
        
    def __iter__(self):
        return self.data.__iter__()
    
    def __repr__ (self):
        s = ""
        for k,v in self.data.items():
            if s:
                s += "\n"
            s += "%s -> %s" % (k,v)
        return s

    def __load (self):
        with open(self.name) as file:
            self.__parseConfig ((line for line in file.readlines()))
            
    def __parseConfig(self, lines):
        for line in lines:
            line = line.strip()
            try:
                if not line or line.startswith("#"): # ignore empty lines and comments
                    pass
                elif line.startswith("import"):
                    self.handleImport(line)
                elif line.find("=") != -1:
                    key, value = line.split("=")
                    self.data[key.lower().strip()] = value.strip()
                elif line.startswith("}"):
                    return
                elif line.endswith("{"):
                    group = line.split("{")[0].strip()
                    self.data[group.lower()] = Config(configLines=lines)
            except:
                print ("Do not understand line: " + line)
                raise

    def handleImport (self, line):
        # syntax: import file as token
        # This import the file into the property 'token'.
        importTokens = re.match("import\\W+([\\w\\\\/\\.]+)\\W+as\\W+(\\w+)", line)
        if importTokens:
            try:
                self.data[importTokens.group(2).lower()] = Config(importTokens.group(1))
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

