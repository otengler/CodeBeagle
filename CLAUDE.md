# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CodeBeagle is a PyQt5-based desktop application for searching source code using full-text indexing. It creates SQLite-based indexes of code files for fast searching, supports multiple search locations, syntax highlighting, bookmarks, and custom search scripts.

## Build and Development Commands

### Running the Application

**Development mode:**
```bash
# On Linux/Mac
python3 CodeBeagle.pyw

# On Windows
python CodeBeagle.pyw
```

### Building the Application

**Windows:**
```powershell
.\build-windows-freeze.ps1
```
This compiles UI files, generates stylesheets from SASS, and uses cx_Freeze to create a standalone executable.

**Linux:**
```bash
./build-unix-freeze.sh linux
```

**macOS:**
```bash
./build-unix-freeze.sh mac
```

Build outputs go to `build/CodeBeagle/` directory.

### Compiling UI Files

UI files (`.ui`) must be compiled to Python after changes:

**Windows:**
```powershell
.\build-windows-ui.ps1
```

**Linux/Mac:**
```bash
./build-unix-ui.sh
```

This generates `Ui_*.py` files from Qt Designer `.ui` files.

### Testing

Run unit tests:
```bash
python UnitTests.py
```

Test modules include: SyntaxHighlighter, HighlighterConfiguration, MatchesOverview, Config, FileTools, Query, fulltextindex testsuite, and BookmarkStorage.

### Verification

mypy should be run after changes to see that the code has no problems:
```
check.ps1
```

The project uses strict mypy settings configured in `mypy.ini`:
- `disallow_untyped_defs`: All functions must have type annotations
- `warn_return_any`: Warns when returning Any from typed functions
- Auto-generated files (`Ui_*.py`) are excluded from type checking

### Dependencies

The application uses a virtual environemt under .venv.

Install Python dependencies:
```bash
pip install PyQt5 cx_Freeze sass
```

Install Node dependencies (for SASS compilation):
```bash
npm ci
```

## Architecture

### Application Entry Point

- **CodeBeagle.pyw**: Main entry point. Initializes QApplication, configures theme (light/dark), sets up MainWindow, and starts update checker.
- **AppConfig.py**: Global configuration management. Reads from `config.txt` and user-specific `UserConfig.txt`. Stores version from `VERSION` file.

### UI Structure

- **MainWindow (Ui_MainWindow)**: Top-level window containing the tabbed search interface
- **SearchPageTabWidget**: Manages multiple search tabs, each containing a SearchPage
- **SearchPage**: Main search UI with:
  - Search input controls
  - Results list view with custom PathVisualizerDelegate for file paths
  - SourceViewer for displaying file contents
  - Support for both content search and filename search
- **SourceViewer**: Text viewer with syntax highlighting, line numbers (LineNumberArea), and in-document search (InDocumentSearchWidget)

### Full-Text Index Architecture

The `fulltextindex/` package contains the core search engine. It is indepedent of any UI classes and does not use PyQt:

- **IndexDatabase.py**: SQLite database schema and operations. Tables: `keywords`, `documents`, `kw2doc` (keyword-to-document mapping), `documentInIndex`, `fileName`, `fileName2doc`
- **FullTextIndex.py**: High-level search interface. Implements `searchContent()` for full-text search and `searchFile()` for filename search. Uses keyword intersection for multi-term queries.
- **IndexUpdater.py**: Builds/updates indexes by scanning directories, extracting keywords from files
- **IndexConfiguration.py**: Configuration for each search location (index database path, source directories, file extensions, index mode)
- **Query.py**: Query objects (ContentQuery, FileQuery) and result types
- **SearchMethods.py**: String matching implementations (exact, wildcard, regex)
- **FileSearch.py**: File name search logic

Search flow:
1. User enters search terms in SearchPage
2. SearchAsync executes search asynchronously (uses AsynchronousTask framework)
3. FullTextIndex queries SQLite database to find documents containing keywords
4. Results sorted and displayed in SearchPage's results list
5. User selects file → SourceViewer displays content with highlighted matches

### Widgets

Custom widgets in `widgets/`:
- **SourceHighlightingTextEdit**: QPlainTextEdit with syntax highlighting
- **SyntaxHighlighter**: Implements PyQt5 syntax highlighting with configurable rules
- **HighlightingTextEdit**: Base text editor with search term highlighting
- **LineNumberArea**: Line number display for editors
- **LeaveLastTabWidget**: Tab widget that keeps at least one tab open
- **InDocumentSearchWidget**: In-file search UI
- **AnimatedProgressWidget**: Animated progress indicator
- **RecyclingVerticalScrollArea**: Performance-optimized scroll area

### Dialogs

Located in `dialogs/`:
- **SettingsDialog**: Configure search locations, index settings, extensions
- **RegExTesterDlg**: Test regex patterns
- **HelpViewerDialog**: Display help.html
- **ProgressBar**: Index update progress
- **StackTraceMessageBox**: Enhanced error reporting with stack traces

### Theming

Two themes in `themes/`:
- **light/**: Default light theme
- **dark/**: Dark theme with custom palette

Theme generation uses SASS. Source files in `themes/dark/` are compiled to stylesheets. Theme is selected via `AppConfig.appConfig().theme`.

### Configuration System

- **tools/Config.py**: Generic configuration parser supporting nested blocks and type validation
- **config.txt**: Global defaults (predefined extensions, update check period, source viewer settings)
- **UserConfig.txt**: User-specific index definitions and overrides (stored in user profile)
- Index configurations define: database path, file extensions, source directories, whether to index content/filenames

### Asynchronous Operations

- **tools/AsynchronousTask.py**: Framework for running tasks in background threads
- **SearchAsync.py**: Asynchronous search execution with progress reporting and cancellation
- **UpdateCheck.py**: Background update checker using GitHub API

### Custom Features

- **BookmarkStorage.py**: Persist bookmarks (file locations) across sessions
- **CustomContextMenu.py**: Extensible context menu system with custom actions
- **SearchPageBookmarks.py**: Search page bookmark integration
- **scripts/**: Custom search scripts (`.script` files) for automating search sequences

### File Organization

```
CodeBeagle.pyw              # Main entry point
AppConfig.py                # Global configuration
SearchPage.py               # Main search interface
SourceViewer.py             # File viewer
MainWindow.ui               # Main window UI definition
SearchPage.ui               # Search page UI definition
fulltextindex/              # Search engine core
  ├── IndexDatabase.py
  ├── FullTextIndex.py
  ├── IndexUpdater.py
  └── Query.py
dialogs/                    # UI dialogs
widgets/                    # Custom widgets
tools/                      # Utilities (Config, FileTools, etc.)
themes/                     # Light/dark themes
config.txt                  # Global config
help.html                   # User documentation
setup.py                    # cx_Freeze build configuration
```

## Development Notes

### Notes before changing code

1. Do not copy and paste code. Try to reuse existing code.
2. Think carefully if a change is efficient with large documents. Documents can have 500k lines or more.
3. Code interfacing with SqLite must be in the "fulltextindex" directory. The UI can then use this code.

### UI Development

1. Edit `.ui` files in Qt Designer
2. Run build UI script to regenerate `Ui_*.py` files
3. Never manually edit `Ui_*.py` files - they are auto-generated
4. Keyboard shortcuts must be documented in help.html

### Adding a New Dialog

1. Create `dialogs/MyDialog.ui` in Qt Designer
2. Run UI build script to generate `dialogs/Ui_MyDialog.py`
3. Create `dialogs/MyDialog.py` with class inheriting from QDialog and using `Ui_MyDialog`

### Modifying Search Logic

Search logic is in `fulltextindex/FullTextIndex.py`. The search uses a keyword-based approach:
- Text split into keywords (alphanumeric sequences)
- Each keyword stored in `keywords` table
- `kw2doc` table maps keywords to documents
- Multi-term search uses set intersection of document lists

### Theme Modifications

1. Edit SASS files in `themes/dark/` or `themes/light/`
2. Run build script (which calls `npm ci` and compiles SASS)
3. Theme applied in `CodeBeagle.pyw` `configureTheme()` function

### Platform-Specific Code

Check `os.name`:
- `"nt"` for Windows
- `"posix"` for Linux/Mac

Example: Windows uses `.pyw` extension and `Win32GUI` base for cx_Freeze, Linux/Mac use `.py` and no base.

### Index Update Tool

`UpdateIndex.py` is a separate executable for updating indexes from command line or scheduled tasks. It can be run independently of the main GUI.
