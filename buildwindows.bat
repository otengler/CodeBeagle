REM
REM Build variables
REM

set PYTHON=python
set PYUIC=pyuic5.exe
set PYRCC5=pyrcc5.exe
set SASS=node_modules\.bin\sass.cmd

REM
REM Compile interface definitions
REM 

"%PYTHON%" GenerateStylesheet.py
"%PYRCC5%" -o qdarkstyle/style_rc.py qdarkstyle\style.qrc
"%PYRCC5%" -o qlightstyle/style_rc.py qlightstyle\style.qrc

"%PYUIC%" --from-imports -o widgets\Ui_LeaveLastTabWidget.py -x widgets\LeaveLastTabWidget.ui 
"%PYUIC%" --from-imports -o widgets\Ui_InDocumentSearchWidget.py -x widgets\InDocumentSearchWidget.ui 
"%PYUIC%" --from-imports -o dialogs\Ui_SettingsItem.py -x dialogs\SettingsItem.ui 
"%PYUIC%" --from-imports -o dialogs\Ui_SettingsDialog.py -x dialogs\SettingsDialog.ui 
"%PYUIC%" --from-imports -o dialogs\Ui_AboutDialog.py -x dialogs\AboutDialog.ui 
"%PYUIC%" --from-imports -o dialogs\Ui_StackTraceMessageBox.py -x dialogs\StackTraceMessageBox.ui
"%PYUIC%" --from-imports -o dialogs\Ui_ProgressBar.py -x dialogs\ProgressBar.ui 
"%PYUIC%" --from-imports -o dialogs\Ui_CheckableItemsDialog.py -x dialogs\CheckableItemsDialog.ui 
"%PYUIC%" --from-imports -o dialogs\Ui_UserHintDialog.py -x dialogs\UserHintDialog.ui 
"%PYUIC%" --from-imports -o dialogs\Ui_GotoLineDialog.py -x dialogs\GotoLineDialog.ui
"%PYUIC%" --from-imports -o dialogs\Ui_HelpViewerDialog.py -x dialogs\HelpViewerDialog.ui 
"%PYUIC%" --from-imports -o dialogs\Ui_RegExTesterDlg.py -x dialogs\RegExTesterDlg.ui
"%PYUIC%" -o Ui_MainWindow.py -x MainWindow.ui 
"%PYUIC%" -o Ui_SearchPage.py -x SearchPage.ui 
"%PYUIC%" -o Ui_SourceViewer.py -x SourceViewer.ui 
"%PYUIC%" -o Ui_MatchesOverview.py -x MatchesOverview.ui 

"%PYRCC5%" -o widgets\LeaveLastTabWidget_rc.py widgets\LeaveLastTabWidget.qrc
"%PYRCC5%" -o widgets\InDocumentSearchWidget_rc.py widgets\InDocumentSearchWidget.qrc
"%PYRCC5%" -o dialogs\SettingsDialog_rc.py dialogs\SettingsDialog.qrc
"%PYRCC5%" -o dialogs\StackTraceMessageBox_rc.py dialogs\StackTraceMessageBox.qrc 
"%PYRCC5%" -o SearchPage_rc.py SearchPage.qrc
"%PYRCC5%" -o MainWindow_rc.py MainWindow.qrc

REM
REM Run Cx_freeze
REM 

set BUILDDIR=build\exe.win-amd64-3.8
set LIB=%BUILDDIR%\lib
if exist build rmdir /s /q build
REM build with cx_freeze 6.4 to avoid false positives with VirusTotal
%PYTHON% setup.py build_exe 

del /q %LIB%\unicodedata.pyd

mkdir %LIB%\PyQt5.new\Qt\bin
mkdir %LIB%\PyQt5.new\Qt\plugins\imageformats
mkdir %LIB%\PyQt5.new\Qt\plugins\platforms
mkdir %LIB%\PyQt5.new\Qt\plugins\styles
copy %LIB%\PyQt5\__init__.pyc %LIB%\PyQt5.new 
copy %LIB%\PyQt5\QtCore.pyd %LIB%\PyQt5.new
copy %LIB%\PyQt5\QtWidgets.pyd %LIB%\PyQt5.new
copy %LIB%\PyQt5\QtGui.pyd %LIB%\PyQt5.new
copy %LIB%\PyQt5\sip.cp38-win_amd64.pyd %LIB%\PyQt5.new
copy %LIB%\PyQt5\Qt\bin\Qt5Core.dll %LIB%\PyQt5.new\Qt\bin\
copy %LIB%\PyQt5\Qt\bin\Qt5Widgets.dll %LIB%\PyQt5.new\Qt\bin\
copy %LIB%\PyQt5\Qt\bin\Qt5Gui.dll %LIB%\PyQt5.new\Qt\bin\
copy %LIB%\PyQt5\Qt\plugins\imageformats\qgif.dll %LIB%\PyQt5.new\Qt\plugins\imageformats\
copy %LIB%\PyQt5\Qt\plugins\platforms\qwindows.dll %LIB%\PyQt5.new\Qt\plugins\platforms\
copy %LIB%\PyQt5\Qt\plugins\styles\qwindowsvistastyle.dll %LIB%\PyQt5.new\Qt\plugins\styles\

rmdir /q /s %LIB%\PyQt5
move %LIB%\PyQt5.new %LIB%\PyQt5

rmdir /q /s %LIB%\qdarkstyle\qss
rmdir /q /s %LIB%\qdarkstyle\rc
rmdir /q /s %LIB%\qdarkstyle\svg
del /q %LIB%\qdarkstyle\style.qrc
del /q %LIB%\qdarkstyle\style.qss

xcopy config.txt %BUILDDIR%
xcopy help.html %BUILDDIR%
xcopy LICENSE %BUILDDIR%
xcopy scripts\* %BUILDDIR%\scripts\
xcopy config\* %BUILDDIR%\config\

REM %mt% -manifest CodeBeagleManifest.xml "-outputresource:%BUILDDIR%\CodeBeagle.exe;#1"
REM %mt% -manifest UpdateIndexManifest.xml "-outputresource:%BUILDDIR%\UpdateIndex.exe;#1"

move %BUILDDIR% build\CodeBeagle
