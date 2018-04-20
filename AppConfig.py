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
import tools.Config as Config
import tools.FileTools as FileTools

appName = "CodeBeagle"
appCompany = "OTE"
appVersion = "1.2.7.0"
configName = "config.txt"
_config = None
_lastUsedConfigName =  ""

def appConfig():
    """Read the global config.txt merged with a per user config.txt."""
    global _config
    if not _config:
        _config = globalConfig()
        __loadUserConfig (_config)
    return _config

def refreshConfig():
    """The next call to "appConfig" will read a fresh config."""
    global _config
    _config = None

def configFromFile (filename):
    """Reads the config from a file."""
    return Config.Config(filename, typeInfoFunc=configTypeInfo)

def globalConfig():
    """Returns the global config."""
    return configFromFile (configName)

def userConfig():
    """
    Returns the user config. The global config is loaded first to retrieve a possible override
    of the user config file location. The default is to use the user profile.
    """
    config = Config.Config(typeInfoFunc=configTypeInfo)
    return __loadUserConfig(config)

def userDataPath():
    """Points to the user profile."""
    return FileTools.getAppDataPath(appName)

def userConfigPath():
    if appConfig().managedConfig:
        name = appConfig().managedConfig
        return os.path.split(name)[0]
    else:
        return userDataPath()

def userConfigFileName():
    if appConfig().managedConfig:
        return appConfig().managedConfig
    else:
        return os.path.join(userDataPath(), configName)

def saveUserConfig (config):
    configPath = userConfigPath()
    name = userConfigFileName()

    for i in range(2):
        try:
            with open (name, "w",  -1,  "utf_8_sig") as output:
                output.write(str(config))
            return
        except IOError as e:
            if e.args[0] == 2: # Create path and try again
                os.makedirs(configPath)
            else:
                raise e

def __loadUserConfig (config):
    try:
        config.loadFile(userConfigFileName())
        return config
    except IOError as e:
        if e.args[0] == 2: # Ignore a file not found error
            return config
        raise e

def sourceViewerConfig():
    sourceviewer = Config.Config()
    sourceviewer.setType ("FontFamily",  Config.typeDefaultString("Consolas"))
    sourceviewer.setType ("FontSize",  Config.typeDefaultInt(10))
    sourceviewer.setType ("TabWidth",  Config.typeDefaultInt(4))
    return sourceviewer

def typeSourceViewerDefaults ():
    return (Config.identity, sourceViewerConfig, Config.identity)

def configTypeInfo (config):
    """Configurates the default values and types."""
    config.setType("profileUpdate",  Config.typeDefaultBool(False))
    config.setType("showCloseConfirmation",  Config.typeDefaultBool(False))
    config.setType("showMatchList", Config.typeDefaultBool(False))
    config.setType("previewLines",  Config.typeDefaultInt(5))
    config.setType("commonKeywords", Config.typeDefaultString(""))
    config.setType("updateCheckPeriod",  Config.typeDefaultInt(0))
    config.setType("matchOverFiles",  Config.typeDefaultBool(False))
    config.setType("activateFirstMatch", Config.typeDefaultBool(False))
    config.setType("showPerformanceButton",  Config.typeDefaultBool(False))
    config.setType("defaultLocation",  Config.typeDefaultString(""))
    config.setType("SourceViewer",  typeSourceViewerDefaults())
    config.setType("managedConfig", Config.typeDefaultString(""))

def lastUsedConfigName ():
    return _lastUsedConfigName

def setLastUsedConfigName (name):
    global _lastUsedConfigName
    _lastUsedConfigName = name




