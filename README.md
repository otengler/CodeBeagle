# CodeBeagle
A tool to search source code based on a full text index.

CodeBeagle allows you to quickly find all occurrences of a search term inside source code files. It can handle large projects with thousands of files with a very good performance. To do so it creates a full text index of the desired source files. Because it is tolerant to whitespace its search syntax works great for searching source code. The search results are displayed in a source viewer with customizable syntax highlighting. It runs without installation and leaves you in full control when to update the index. Advanced features are the support of multiple search locations, extensible context menus and custom search scripts which allow to automate sequences of searches.

Change log can be found here: ![CHANGES](/CHANGES)

Download here: https://github.com/otengler/CodeBeagle/releases/latest

Visual Studio 2015 C++ runtime (x64) is a prerequisite. Fetch it from here if needed: https://www.microsoft.com/en-us/download/details.aspx?id=48145

# Features
- Indexes multiple directories, lets you choose file extensions to index
- Search in file content or for file name
- Search indexed and not indexed locations
- Source viewer with customizable syntax highlighting
- Tabbed searching
- Custom search scripts allow to automate search tasks
- Supports ANSI,UTF8 and UTF16
- Dark theme

# Screenshots

![main-light](/../screenshots/screenshots/main-light.png?raw=true "Main windows (light theme)")

![settings](/../screenshots/screenshots/settings.png?raw=true "Settings")

![options](/../screenshots/screenshots/options.png?raw=true "Options")

![main-dark](/../screenshots/screenshots/main-dark.png?raw=true "Main windows (dark theme)")

# Building

First the prerequisites (that's what I used to build the binary distribution):
- NodeJs to be able to use npm
- Python 3.10.5 (www.python.org)
- PyQt GPL v5.15.2 (install with "pip install PyQt5")
- Cx_Freeze (install with "pip install Cx_freeze==6.11"):
    Only needed if you want convert the python scripts into executables

Compile the user interface and resource files by calling "build-windows-ui.bat". The user interface is launched via "CodeBeagle.pyw". The script to update the index is called "UpdateIndex.py".
To build the executables call "build-windows-freeze.bat". To be able to compile the dark theme style sheet you need the sass compiler in your path.
