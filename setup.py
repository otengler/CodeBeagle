import sys
from cx_Freeze import setup, Executable  # type: ignore[import-untyped]
import AppConfig

options = {
    "build_exe": {
        "includes": "unittest",
        "zip_include_packages": "logging,http,collections,encodings,sqlite3,urllib,asyncio,concurrent,dialogs"
    }
}

targetBase = None
codeBeagleScript = None
if sys.platform == "win32":
    print("Using Windows settings")
    codeBeagleScript = "CodeBeagle.pyw"
    targetBase = "gui"
    targetCodeBeagle = "CodeBeagle.exe"
    targetUpdateIndex = "UpdateIndex.exe"
    options["build_exe"]["excludes"] = "distutils,lib2to3,xml,test,tkinter,pydoc_data,pyreadline,curses,_pyrepl"
else:
    print("Using Linux/MacOS settings")
    codeBeagleScript = "CodeBeagle.py"
    targetBase = None
    targetCodeBeagle = "CodeBeagle"
    targetUpdateIndex = "UpdateIndex"
    #options["build_exe"]["bin_includes"] = ["libxcb-xinerama.so.0"]

CodeBeagle=Executable(
    script = codeBeagleScript,
    base = targetBase,
    target_name = targetCodeBeagle,
    icon = "resources.src/CodeBeagle.ico",
    manifest = "CodeBeagleManifest.xml"
)

UpdateIndex=Executable(
    script = "UpdateIndex.py",
    target_name = targetUpdateIndex
)

CodeBeagleAgentServer=Executable(
    script = "CodeBeagleAgentServer.py",
    target_name = "CodeBeagleAgentServer"
)

CodeBeagleMCP=Executable(
    script = "CodeBeagleMCP.py",
    target_name = "CodeBeagleMCP"
)

setup(
    options = options,
    name = AppConfig.appName,
    version = AppConfig.appVersion + ".0",
    description = "CodeBeagle - A tool to search source code based on a full text index",
    executables = [CodeBeagle, UpdateIndex, CodeBeagleAgentServer, CodeBeagleMCP]
)

