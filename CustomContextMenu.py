# -*- coding: utf-8 -*-
"""
Copyright (C) 2012 Oliver Tengler

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
from PyQt4.QtCore import *
import Config
from FileTools import fopen
from ExceptionTools import exceptionAsString

# Launches an executable for each of the files passed via context menu
class ExecuteProgramTask:
    def __init__(self, program,  args,  bShowWindow):
        super(ExecuteProgramTask, self).__init__()
        self.program = os.path.expandvars(program)
        self.args =args
        self.bShowWindow = bShowWindow
        
    def execute (self,  contextMenu,  files):
        import subprocess
        import shlex
        
        failedFiles = []
        for file in files:
            os.environ["file"] = file
            args = os.path.expandvars(self.args)
            args = shlex.split(args)
            si = subprocess.STARTUPINFO()
            if not self.bShowWindow:
                si.dwFlags = subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE
            try:
                subprocess.Popen ([self.program] + args,  startupinfo=si)
            except:
                failedFiles.append (file)
            
        if failedFiles:
            contextMenu.executionFailed.emit (ContextMenuError(self.program,  failedFiles))
        
# Executes an python script with all of the files passed via context menu
class CustomScriptTask:
    def __init__(self,  script):
        self.script = script
        
    def execute(self, contextMenu,  files):
        localsDict = { "files":  files }
        try:
            # The actual script is wrapped in the function "contextMenu". It is needed to 
            # establish a proper scope which enables access to local variables from sub functions 
            # analog to globals. Example what caused problems:
            # import time
            # def foo(files):
            #    time.sleep(5)
            # foo(files)
            # This failed in previous versions with "global 'time' not found". 
            scriptCode=""
            with fopen(self.script) as file:
                scriptCode="def contextMenu(files):\n"
                for line in file:
                    scriptCode += "\t"
                    scriptCode += line
                scriptCode += "\ncontextMenu(files)\n"
                    
            code = compile(scriptCode, self.script, 'exec')
            exec(code,  globals(),  localsDict)
        except:
            contextMenu.executionFailed.emit (ContextMenuError(self.script,  files,  exceptionAsString()))

class ContextMenuError:
    def __init__(self,  program,  failedFiles,  exception=None):
        self.program = program
        self.failedFiles = failedFiles
        self.exception = exception

class CustomContextMenu (QObject):
    executionFailed = pyqtSignal(ContextMenuError)  
    
    def __init__(self, title, task):
        super(CustomContextMenu, self).__init__()
        self.title = title
        self.task = task
        
    def execute (self,  files):
        self.task.execute(self,  files)

_customMenuEntries = None

# Returns a list of CustomContextMenu objects 
def customMenuEntries (conf):
    global _customMenuEntries
    if _customMenuEntries is None:
        try:
            _customMenuEntries = __readConfig(conf)
        except:
            _customMenuEntries = []
    return _customMenuEntries 
    
# Configurates the type information for the context menu configuration
def contextMenuTypeInfo (config):
    config.setType("title", Config.typeDefaultString("Custom context menu"))
    config.setType("executable", Config.typeDefaultString(""))
    config.setType("args",  Config.typeDefaultString(""))
    config.setType("showWindow",  Config.typeDefaultBool(True))
    config.setType("script", Config.typeDefaultString(""))
        
# Returns a list of Index objects from the config
# ContextMenu1 {
# title = Notepad
# executable = %windir%\notepad.exe %file%
# script = filename relative to program root
#}
def __readConfig (conf):
    menus = []
    for group in conf:
        if group.startswith("contextmenu"):
            menus.append(group)
    menus.sort()
    
    entries = []
    for group in menus:
        menuConf= conf[group]
        contextMenuTypeInfo (menuConf)
        
        title = menuConf.title
        executable = menuConf.executable
        script = menuConf.script
        
        if executable:
            entries.append(CustomContextMenu(title,  ExecuteProgramTask(executable,  menuConf.args,  menuConf.showWindow)))
        elif script:
            entries.append(CustomContextMenu(title,  CustomScriptTask(script)))
        
    return entries
    

