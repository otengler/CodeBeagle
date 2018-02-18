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
import unittest
from tools.FileTools import fopen

def identity (a):
    return a

def boolParse (value):
    if type(value) == bool:
        return value
    if type(value) == str:
        value = value.lower()
        if value == "true" or value == "1" or value == "yes":
            return True
        if value == "false" or value == "0" or value == "no":
            return False
    if type(value) == int:
        return bool(value)
    raise RuntimeError("Unknown boolean value '" + value + "'")

def boolPersist (value):
    if type(value) == bool:
        return str(value)
    if type(value) == str:
        value = value.lower()
        if value == "true" or value == "1" or value == "yes":
            return "True"
        if value == "false" or value == "0" or value == "no":
            return "False"
    if type (value) == int:
        if value:
            return "True"
        return "False"
    raise RuntimeError("Cannot interpret '" + str(value) + "' as bool")

def plainTypeMapper(t):
    if bool == t:
        return (boolParse, lambda: None, boolPersist)
    if int == t:
        return (int, lambda: None, str)
    return (identity,  lambda: None,  str)

# A object which holds configuration data. The data is accessed like a property. It can contain objects of itself
# which allows to build deeper stacked configs.
# E.g.:
# c = Config()
# c.sub = Config()
# c.sub.a = "Text"
class Config:
    def __init__ (self, name="", dataMap=None,  configLines=None,  typeInfoFunc=None):
        self.__data = dataMap
        if not self.__data:
            self.__data = {}
        self.__typeMapper = {}
        if typeInfoFunc:
            typeInfoFunc(self)
        if name:
            self.loadFile(name)
        elif configLines:
            self.parseLines(configLines)

    def setPlainType(self, attr, type):
        self.__typeMapper[attr.lower()] = plainTypeMapper(type)

    def setType (self, attr, typeFuncs):
        self.__typeMapper[attr.lower()] = typeFuncs

    def __typeParse (self, attr):
        if attr in self.__typeMapper:
            return self.__typeMapper[attr][0]
        return lambda a: a

    def __typeNotFound (self, attr):
        if attr in self.__typeMapper:
            return self.__typeMapper[attr][1]
        return lambda:None

    def __typePersist (self, attr):
        if attr in self.__typeMapper:
            return self.__typeMapper[attr][2]
        return str

    def __getattr__ (self,  attr):
        attr = attr.lower()
        if attr in self.__data:
            return self.__typeParse(attr)(self.__data[attr])
        result = self.__typeNotFound(attr)()
        if result != None:
            if isinstance(result, Config):
                self.__data[attr] = result
            return result
        raise AttributeError(attr + " does not exist in the configuration")

    def __getitem__(self, attr):
        attr = attr.lower()
        return self.__data[attr]

    def __contains__(self,  attr):
        return attr.lower() in self.__data

    def __setattr__(self, attr,  value):
        if attr.startswith("_Config__"):
            return super(Config, self).__setattr__(attr, value)
        attr = attr.lower()
        if isinstance(value, Config):
            self.__data[attr] = value
        else:
            v = self.__typeParse(attr)(value)
            self.__data[attr] = v

    def __iter__(self):
        return self.__data.__iter__()

    def values(self):
        return self.__data.values()

    def __repr__ (self):
        return self.__dumpRec (self, 0)

    def __dumpRec (self,  config,  level):
        s = ""
        for k,v in config.__data.items():
            if s:
                s += "\n"
            s = s + " " *2*level + k
            if type(v) is Config:
                s += " {\n"
                s = s + self.__dumpRec (v,  level+1)
                s = s + "\n" + " " *2*level + "}"
            else:
                s = s + " = " + self.__typePersist(k)(v)
        return s

    def remove (self, key):
        key = key.lower()
        if key in self.__data:
            del self.__data[key]

    def loadFile (self, name):
        with fopen(name) as file:
            self.parseLines ((line for line in file.readlines()))

    def parseLines(self, lines):
        if type(lines) is not types.GeneratorType:
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
                    setattr(self, key.strip(),  value.strip())
                elif line.startswith("}"):
                    return
                elif line.endswith("{"):
                    groupname = line.split("{")[0].strip().lower()
                    if groupname in self.__data:
                        group = self.__data[groupname]
                        group.parseLines (lines)
                    else:
                        try:
                            group = getattr(self, groupname) # This allows to apply type information from __typeNotFound funcs
                        except AttributeError:
                            group = Config()
                        group.parseLines(lines)
                        setattr (self,  groupname,  group)
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
                group = getattr(self, groupname) # This allows to apply type information from __typeNotFound funcs
            except AttributeError:
                group = Config()

            try:
                group.loadFile (filename)
                setattr (self,  groupname,  group)
            except IOError:
                pass
        else:
            # syntax: import file
            # This imports all properties of the file into the current config.
            importTokens = re.match("import\\W+([\\w\\\\/\\.]+)", line)
            if not importTokens:
                raise RuntimeError("wrong import line")
            try:
                Config(importTokens.group(1), dataMap=self.__data)
            except IOError:
                pass

def typeDefaultBool (bDefault):
    return (boolParse, lambda: bDefault, boolPersist)

def typeDefaultInt (iDefault):
    return (int, lambda: iDefault, str)

def typeDefaultString (strDefault):
    return (identity, lambda: strDefault, str)

def typeDefaultConfig ():
    return (identity, lambda: Config(), identity)

class TestConfig(unittest.TestCase):
    def test(self):
        c = Config()
        c.setPlainType ("b1", bool)
        c.setType("b2",  typeDefaultBool(True))
        with self.assertRaises(AttributeError):
            c.b1
        self.assertEqual(c.b2, True)
        c.b1 = False
        self.assertEqual(c.b1, False)
        c.text = "Hallo"
        self.assertEqual(c.text, "Hallo")
        c.setType("di",  typeDefaultInt(42))
        self.assertEqual(c.di, 42)
        c.setType("ds",  typeDefaultString("Spam"))
        self.assertEqual(c.ds, "Spam")
        hasB1 = "b1" in c
        self.assertEqual(hasB1,  True)
        hasX1 = "x1" in c
        self.assertEqual(hasX1,  False)

if __name__ == "__main__":
    unittest.main()


