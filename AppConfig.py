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

import os, json
from typing import Optional, Tuple, Callable, cast
from tools import Config, FileTools

def readVersion():
    if os.path.isfile("VERSION"):
        return json.load(open("VERSION", "r"))["version"]
    return "1.0.0"

appName = "CodeBeagle"
appCompany = "OTE"
appVersion = readVersion()
configName = "config.txt"
darkTheme = "dark"

class ConfigCache:
    config: Optional[Config.Config] = None
    lastUsedConfigName: str = ""
    theme = "" # default theme

def appConfig() -> Config.Config:
    """Read the global config.txt merged with a per user config.txt."""
    if not ConfigCache.config:
        ConfigCache.config = globalConfig()
        __loadUserConfig (ConfigCache.config)
    return ConfigCache.config

def refreshConfig() -> None:
    """The next call to "appConfig" will read a fresh config."""
    ConfigCache.config = None

def configFromFile (filename: str) -> Config.Config:
    """Reads the config from a file."""
    return Config.Config(filename, typeInfoFunc=configTypeInfo)

def globalConfig() -> Config.Config:
    """Returns the global config."""
    return configFromFile (configName)

def userConfig() -> Config.Config:
    """
    Returns the user config. The global config is loaded first to retrieve a possible override
    of the user config file location. The default is to use the user profile.
    """
    config = Config.Config(typeInfoFunc=configTypeInfo)
    return __loadUserConfig(config)

def userDataPath() -> str:
    """Points to the user profile."""
    return FileTools.getAppDataPath(appName)

def userConfigPath() -> str:
    if appConfig().managedConfig:
        name = cast(str,appConfig().managedConfig)
        return os.path.split(name)[0]

    return userDataPath()

def userConfigFileName() -> str:
    if appConfig().managedConfig:
        return cast(str,appConfig().managedConfig)

    return os.path.join(userDataPath(), configName)

def saveUserConfig (config: Config.Config) -> None:
    configPath = userConfigPath()
    name = userConfigFileName()

    for _ in range(2):
        try:
            with open (name, "w",  -1,  "utf_8_sig") as output:
                output.write(str(config))
            return
        except IOError as e:
            if e.args[0] == 2: # Create path and try again
                os.makedirs(configPath)
            else:
                raise e

def __loadUserConfig (config: Config.Config) -> Config.Config:
    try:
        config.loadFile(userConfigFileName())
        return config
    except IOError as e:
        if e.args[0] == 2: # Ignore a file not found error
            return config
        raise e

def sourceViewerConfig() -> Config.Config:
    sourceviewer = Config.Config()
    sourceviewer.setType ("FontFamily",  Config.typeDefaultString("Cascadia Mono"))
    sourceviewer.setType ("FontSize",  Config.typeDefaultInt(10))
    sourceviewer.setType ("TabWidth",  Config.typeDefaultInt(4))
    sourceviewer.setType ("showLineNumbers", Config.typeDefaultBool(True))
    return sourceviewer

def typeSourceViewerDefaults () -> Tuple[Callable, Callable, Callable]:
    return (Config.identity, sourceViewerConfig, Config.identity)

def configTypeInfo (config: Config.Config) -> None:
    """Configurates the default values and types."""
    config.setType("profileUpdate",  Config.typeDefaultBool(False))
    config.setType("showCloseConfirmation",  Config.typeDefaultBool(False))
    config.setType("showRegexDialog", Config.typeDefaultBool(False))
    config.setType("showMatchList", Config.typeDefaultBool(False))
    config.setType("previewLines",  Config.typeDefaultInt(5))
    config.setType("commonKeywords", Config.typeDefaultString(""))
    config.setType("updateCheckPeriod",  Config.typeDefaultInt(0))
    config.setType("matchOverFiles",  Config.typeDefaultBool(False))
    config.setType("activateFirstMatch", Config.typeDefaultBool(False))
    config.setType("theme", Config.typeDefaultString(""))
    config.setType("showPerformanceButton",  Config.typeDefaultBool(False))
    config.setType("defaultLocation",  Config.typeDefaultString(""))
    config.setType("SourceViewer",  typeSourceViewerDefaults())
    config.setType("managedConfig", Config.typeDefaultString(""))

def lastUsedConfigName () -> str:
    return ConfigCache.lastUsedConfigName

def setLastUsedConfigName (name: str) -> None:
    ConfigCache.lastUsedConfigName = name
