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
import FileTools

appName = "CodeBeagle"
appCompany = "OTE"
appVersion = "1.2.1.0"
configName = "config.txt"
_config = None
_lastUsedConfigName =  ""

# Read the global config.txt merged with a per user config.txt.
def appConfig():
    global _config
    if not _config:
        _config = globalConfig()
        __loadUserConfig (_config)
    return _config

# The next call to "appConfig" will read a fresh config
def refreshConfig():
    global _config
    _config = None
    
# Reads the config from a file
def configFromFile (filename):
    return Config.Config(filename, typeInfoFunc=configTypeInfo)
    
# Returns the global config
def globalConfig():
    return configFromFile (configName)
    
# Returns the user config. The global config is loaded first to retrieve a possible override
# of the user config file location. The default is to use the user profile.
def userConfig():
    userConfig = Config.Config(typeInfoFunc=configTypeInfo)
    return __loadUserConfig(userConfig)
    
# Points to the user profile
def userDataPath():
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
                os.mkdir(configPath)
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
      
# Configurates the default values and types
def configTypeInfo (config):
    config.setType("profileUpdate",  Config.typeDefaultBool(False))
    config.setType("showCloseConfirmation",  Config.typeDefaultBool(False)) 
    config.setType("previewLines",  Config.typeDefaultInt(5))
    config.setType("commonKeywords", Config.typeDefaultString(""))
    config.setType("updateCheckPeriod",  Config.typeDefaultInt(0))
    config.setType("matchOverFiles",  Config.typeDefaultBool(False)) 
    config.setType("showPerformanceButton",  Config.typeDefaultBool(False))
    config.setType("defaultLocation",  Config.typeDefaultString(""))
    config.setType("SourceViewer",  typeSourceViewerDefaults())
    config.setType("managedConfig", Config.typeDefaultString(""))

def lastUsedConfigName ():
    return _lastUsedConfigName

def setLastUsedConfigName (name):
    global _lastUsedConfigName
    _lastUsedConfigName = name
 
 
 
 
