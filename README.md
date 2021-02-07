# CodeBeagle
A tool to search source code based on a full text index.

CodeBeagle allows you to quickly find all occurrences of a search term inside source code files. It can handle large projects with thousands of files with a very good performance. To do so it creates a full text index of the desired source files. Because it is tolerant to whitespace its search syntax works great for searching source code. The search results are displayed in a source viewer with customizable syntax highlighting. It runs without installation and leaves you in full control when to update the index. Advanced features are the support of multiple search locations, extensible context menus and custom search scripts which allow to automate sequences of searches.

Version 1.3.5 is released. See ![CHANGES](/CHANGES) for details.

Visual Studio 2015 C++ runtime (x64) is a prerequisite. Fetch it from here if needed: https://www.microsoft.com/en-us/download/details.aspx?id=48145

Features:
- Indexes multiple directories, lets you choose file extensions to index
- Search indexed and not indexed locations
- Source viewer with customizable syntax highlighting
- Tabbed searching
- Custom search scripts allow to automate search tasks
- Supports ANSI,UTF8 and UTF16
- Dark theme

