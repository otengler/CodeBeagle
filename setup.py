import os
from cx_Freeze import setup, Executable
import AppConfig

options = {
    "build_exe": {
        "zip_include_packages": "logging,http,collections,encodings,sqlite3,unittest,urllib,asyncio,concurrent,dialogs,email,importlib"
    }
}

targetBase = None
codeBeagleScript = None
if os.name == "nt":
    print("Using Windows settings")
    codeBeagleScript = "CodeBeagle.pyw"
    targetBase = "Win32GUI"
    targetCodeBeagle = "CodeBeagle.exe"
    targetUpdateIndex = "UpdateIndex.exe"
    options["build_exe"]["excludes"] = "distutils,html,multiprocessing,lib2to3,xml,test,tkinter,pydoc_data,bz2,queue,lzma,ssl,pyreadline,decimal,curses,zipfile,sysconfig"
else:
    print("Using Linux/MacOS settings")
    codeBeagleScript = "CodeBeagle.py"
    targetBase = None
    targetCodeBeagle = "CodeBeagle"
    targetUpdateIndex = "UpdateIndex"

CodeBeagle=Executable(
    script = codeBeagleScript,
    base = targetBase,
    target_name = targetCodeBeagle,
    icon = "resources.src/CodeBeagle.ico"
)

UpdateIndex=Executable(
    script = "UpdateIndex.py",
    target_name = targetUpdateIndex
)

setup(
    options=options,
    name = AppConfig.appName,
    version = AppConfig.appVersion + ".0",
    description = "CodeBeagle - A tool to search source code based on a full text index",
    executables = [CodeBeagle, UpdateIndex]
)

