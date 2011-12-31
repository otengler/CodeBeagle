from cx_Freeze import setup, Executable
	
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

setup(  
    name = "CodeBeagle",
    version = "1.0.24.0",
    description = "CodeBeagle - A tool to search source code based on a full text index",
    executables = [CodeBeagle,  UpdateIndex]
)

