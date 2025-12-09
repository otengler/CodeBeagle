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

import re
import types
import unittest
from typing import TypeVar, Any, Dict, Callable, Tuple, Iterator, cast, Optional
from tools.FileTools import fopen

T = TypeVar('T')

def identity (a: T) -> T:
    return a

def boolParse (value: Any) -> bool:
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

def boolPersist (value: Any) -> str:
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

def plainTypeMapper(t: Any) -> Tuple[Callable[[Any], Any], Callable[[], Any], Callable[[Any], str]]:
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
    def __init__ (self, name: str="", dataMap: Optional[Dict[str,Any]]=None,  configLines:Optional[Iterator[str]]=None,  typeInfoFunc: Optional[Callable[[Any], None]]=None) -> None:
        self.__data = dataMap or {}
        self.__typeMapper: Dict[str,Tuple[Callable[[Any], Any],Callable[[], Any],Callable[[Any], str]]] = {}
        if typeInfoFunc:
            typeInfoFunc(self)
        if name:
            self.loadFile(name)
        elif configLines:
            self.parseLines(configLines)

    def setPlainType(self, attr: str, attrType: Any) -> None:
        self.__typeMapper[attr.lower()] = plainTypeMapper(attrType)

    def setType (self, attr: str, typeFuncs: Tuple[Callable[[Any], Any], Callable[[], Any], Callable[[Any], str]]) -> None:
        self.__typeMapper[attr.lower()] = typeFuncs

    def __typeParse (self, attr: str) -> Callable[[Any], Any]:
        if attr in self.__typeMapper:
            return self.__typeMapper[attr][0]
        return lambda a: a

    def __typeNotFound (self, attr: str) -> Callable[[], Any]:
        if attr in self.__typeMapper:
            return self.__typeMapper[attr][1]
        return lambda:None

    def __typePersist (self, attr: str) -> Callable[[Any], str]:
        if attr in self.__typeMapper:
            return self.__typeMapper[attr][2]
        return str

    def __getattr__ (self,  attr: str) -> Any:
        attr = attr.lower()
        if attr in self.__data:
            return self.__typeParse(attr)(self.__data[attr])
        result = self.__typeNotFound(attr)()
        if result is not None:
            if isinstance(result, Config):
                self.__data[attr] = result
            return result
        raise AttributeError(attr + " does not exist in the configuration")

    def __getitem__(self, attr: str) -> Any:
        attr = attr.lower()
        return self.__data[attr]

    def __contains__(self,  attr: str) -> bool:
        return attr.lower() in self.__data

    def __setattr__(self, attr: str, value: Any) -> None:
        if attr.startswith("_Config__"):
            super().__setattr__(attr, value)
            return 
        attr = attr.lower()
        if isinstance(value, Config):
            self.__data[attr] = value
        else:
            v = self.__typeParse(attr)(value)
            self.__data[attr] = v

    def __iter__(self) -> Any:
        return self.__data.__iter__()

    def values(self) -> Any:
        return self.__data.values()

    def __repr__ (self) -> str:
        return self.__dumpRec (self, 0)

    def __dumpRec (self, config: 'Config',  level: int) -> str:
        s = ""
        for k,v in config.__data.items(): # access of protected member pylint: disable=W0212
            if s:
                s += "\n"
            s = s + " " *2*level + k
            if type(v) is Config:
                s += " {\n"
                s = s + self.__dumpRec (v,  level+1)
                s = s + "\n" + " " *2*level + "}"
            else:
                s = s + " = " + config.__typePersist(k)(v) # access of protected member pylint: disable=W0212
        return s

    def remove (self, key: str) -> None:
        key = key.lower()
        if key in self.__data:
            del self.__data[key]

    def loadFile (self, name: str) -> None:
        with fopen(name) as file:
            self.parseLines ((line for line in file.readlines()))

    def parseLines(self, lines: Iterator[str]) -> None:
        if type(lines) is not types.GeneratorType:
            raise TypeError("lines must be a generator type")
        for line in lines:
            line = line.strip()
            try:
                if not line or line.startswith("#"): # ignore empty lines and comments
                    continue
                equalSign = line.find("=")
                if equalSign != -1:
                    key = line[:equalSign]
                    value = line[equalSign+1:]
                    setattr(self, key.strip(),  value.strip())
                elif line.startswith("import"):
                    self.__handleImport(line)
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

    def __handleImport (self, line: str) -> None:
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

def typeDefaultBool (bDefault: bool) -> Tuple[Callable[[Any], Any], Callable[[], Any], Callable[[Any], str]]:
    return (boolParse, lambda: bDefault, boolPersist)

def typeDefaultInt (iDefault: int) -> Tuple[Callable[[Any], Any], Callable[[], Any], Callable[[Any], str]]:
    return (int, lambda: iDefault, str)

def typeDefaultString (strDefault: str) -> Tuple[Callable[[Any], Any], Callable[[], Any], Callable[[Any], str]]:
    return (identity, lambda: strDefault, str)

def typeDefaultConfig () -> Tuple[Callable[[Any], Any], Callable[[], Any], Callable[[Any], str]]:
    return (identity, lambda: Config(), identity) # Lambda may not be neccessary pylint: disable=W0108
class TestConfig(unittest.TestCase):
    def test(self) -> None:
        c = Config()
        c.setPlainType ("b1", bool)
        c.setType("b2",  typeDefaultBool(True))
        with self.assertRaises(AttributeError):
            c.b1 # pylint: disable=W0104
        self.assertEqual(c.b2, True)
        c.b1 = False # pylint: disable=W0201
        self.assertEqual(c.b1, False)
        c.text = "Hallo" # pylint: disable=W0201
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