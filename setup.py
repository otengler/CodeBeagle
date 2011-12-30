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
    version = "1.0.0.24",
    description = "A database based full text search for source code",
    executables = [CodeBeagle,  UpdateIndex]
)

