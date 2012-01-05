Binary distribution
===================

There is no installation as such. Just unzip to a location you like and launch "CodeBeagle.exe" to start up the UI. To get started read help.html which is opened  by default. If CodeBeagle fails to launch your system probably misses the correct Microsoft Visual C++ runtime. To fix this download and install the "Microsoft Visual C++ 2008 SP1 Redistributable Package (x86)" from Microsoft.

Running from source
===================

The latest version is available from "git://git.code.sf.net/p/codebeagle/code".
First the prerequisites (that's what I used to build the binary distribution):
- Python 3.2 (www.python.org)
- PyQt GPL v4.8.5 for Python v3.2 (x86) (http://www.riverbankcomputing.co.uk/software/pyqt/download)
- cx_Freeze 4.2.3 (http://cx-freeze.sourceforge.net/):
    Only needed if you want convert the python scripts into executables

Python is assumed to be installed in "C:\Python32". Compile the user interface and resource files by calling "build.bat". The user interface is launched via "CodeBeagle.pyw". The script to update the index is called "UpdateIndex.py".
To build the executables call "buildexe.bat" which calls "build.bat" itself.

Have fun
Oliver