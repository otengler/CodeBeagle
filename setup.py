from cx_Freeze import setup, Executable
import AppConfig

CodeBeagle=Executable(
    script = "CodeBeagle.pyw",
    base = "Win32GUI",
    targetName = "CodeBeagle.exe",
    icon = "resources/CodeBeagle.ico"
)

UpdateIndex=Executable(
    script = "UpdateIndex.py",
    targetName = "UpdateIndex.exe"
)

options = {
    "build_exe": {
        "zip_include_packages": "logging,http,collections,encodings,sqlite3,unittest,urllib,asyncio,concurrent,dialogs,email,importlib",
        "excludes": "distutils,html,multiprocessing,lib2to3,xml,test,tkinter,pydoc_data,bz2,queue,lzma,ssl"
    }
}

setup(
    options=options,
    name = AppConfig.appName,
    version = AppConfig.appVersion,
    description = "CodeBeagle - A tool to search source code based on a full text index",
    executables = [CodeBeagle,  UpdateIndex]
)

