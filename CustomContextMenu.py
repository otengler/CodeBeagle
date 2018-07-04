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
from abc import ABC, abstractmethod
from typing import List, Optional
from PyQt5.QtCore import QObject, pyqtSignal
import tools.Config as Config
from tools.FileTools import fopen
from tools.ExceptionTools import exceptionAsString

class ContextMenuError:
    def __init__(self,  program: str,  failedFiles: List[str],  exception: str=None) -> None:
        self.program = program
        self.failedFiles = failedFiles
        self.exception = exception

class ContextMenuTask(ABC):
    @abstractmethod
    def execute (self, files: List[str]) -> Optional[ContextMenuError]:
        pass

class CustomContextMenu (QObject):
    executionFailed = pyqtSignal(ContextMenuError)

    def __init__(self, title: str, task: ContextMenuTask) -> None:
        super().__init__()
        self.title = title
        self.task = task

    def execute (self, files: List[str]) -> None:
        error = self.task.execute(files)
        if error:
            self.executionFailed.emit (error)

class ExecuteProgramTask (ContextMenuTask):
    """Launches an executable for each of the files passed via context menu"""
    def __init__(self, program: str,  args: str,  bShowWindow: bool) -> None:
        super().__init__()
        self.program = os.path.expandvars(program)
        self.args = args
        self.bShowWindow = bShowWindow

    def execute (self, files: List[str]) -> Optional[ContextMenuError]:
        import subprocess
        import shlex

        failedFiles: List[str] = []
        for file in files:
            os.environ["file"] = file
            args = os.path.expandvars(self.args)
            argList = shlex.split(args)
            si = subprocess.STARTUPINFO()
            if not self.bShowWindow:
                si.dwFlags = subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE
            try:
                subprocess.Popen ([self.program] + argList,  startupinfo=si)
            except:
                failedFiles.append (file)

        if failedFiles:
            return ContextMenuError(self.program,  failedFiles)
        return None

class CustomScriptTask (ContextMenuTask):
    """Executes an python script with all of the files passed via context menu"""
    def __init__(self,  script: str) -> None:
        self.script = script

    def execute (self, files: List[str]) -> Optional[ContextMenuError]:
        """
        The actual script is wrapped in the function "contextMenu". It is needed to
        establish a proper scope which enables access to local variables from sub functions
        analog to globals. Example what caused problems:
        import time
        def foo(files):
            time.sleep(5)
            foo(files)
        This failed in previous versions with "global 'time' not found".
        """
        localsDict = { "files":  files }
        try:
            scriptCode=""
            with fopen(self.script) as file:
                scriptCode="def contextMenu(files):\n"
                for line in file:
                    scriptCode += "\t"
                    scriptCode += line
                scriptCode += "\ncontextMenu(files)\n"

            code = compile(scriptCode, self.script, 'exec')
            exec(code, globals(), localsDict)
        except:
            return ContextMenuError(self.script,  files,  exceptionAsString())
        return None

class CustomContextMenuCache:
    customMenuEntries: List[CustomContextMenu] = []

def customMenuEntries (conf: Config.Config) -> List[CustomContextMenu]:
    """Returns a list of CustomContextMenu objects"""
    if not CustomContextMenuCache.customMenuEntries:
        try:
            CustomContextMenuCache.customMenuEntries = __readConfig(conf)
        except:
            CustomContextMenuCache.customMenuEntries = []
    return CustomContextMenuCache.customMenuEntries

def contextMenuTypeInfo (config: Config.Config) -> None:
    """Configurates the type information for the context menu configuration"""
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
def __readConfig (conf: Config.Config) -> List[CustomContextMenu]:
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


