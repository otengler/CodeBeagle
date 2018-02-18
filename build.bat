call buildvars.bat

set PYUIC=%PYDIR%\scripts\pyuic5.exe
set PYRCC5=%PYDIR%\scripts\pyrcc5.exe

%PYTHON% %PYUIC% --from-imports -o widgets/Ui_LeaveLastTabWidget.py -x widgets/LeaveLastTabWidget.ui 
%PYTHON% %PYUIC% --from-imports -o dialogs/Ui_SettingsItem.py -x dialogs/SettingsItem.ui 
%PYTHON% %PYUIC% --from-imports -o dialogs/Ui_SettingsDialog.py -x dialogs/SettingsDialog.ui 
%PYTHON% %PYUIC% --from-imports -o dialogs/Ui_AboutDialog.py -x dialogs/AboutDialog.ui 
%PYTHON% %PYUIC% --from-imports -o dialogs/Ui_StackTraceMessageBox.py -x dialogs/StackTraceMessageBox.ui
%PYTHON% %PYUIC% --from-imports -o dialogs/Ui_ProgressBar.py -x dialogs/ProgressBar.ui 
%PYTHON% %PYUIC% --from-imports -o dialogs/Ui_CheckableItemsDialog.py -x dialogs/CheckableItemsDialog.ui 
%PYTHON% %PYUIC% --from-imports -o dialogs/Ui_UserHintDialog.py -x dialogs/UserHintDialog.ui 
%PYTHON% %PYUIC% --from-imports -o dialogs/Ui_GotoLineDialog.py -x dialogs/GotoLineDialog.ui
%PYTHON% %PYUIC% --from-imports -o dialogs/Ui_HelpViewerDialog.py -x dialogs/HelpViewerDialog.ui 
%PYTHON% %PYUIC% --from-imports -o dialogs/Ui_RegExTesterDlg.py -x dialogs/RegExTesterDlg.ui
%PYTHON% %PYUIC% -o Ui_MainWindow.py -x MainWindow.ui 
%PYTHON% %PYUIC% -o Ui_SearchPage.py -x SearchPage.ui 
%PYTHON% %PYUIC% -o Ui_SourceViewer.py -x SourceViewer.ui 
%PYTHON% %PYUIC% -o Ui_MatchesOverview.py -x MatchesOverview.ui 

copy /Y resources\Crystal\*.* resources\

%PYRCC5% -o widgets/LeaveLastTabWidget_rc.py widgets/LeaveLastTabWidget.qrc
%PYRCC5% -o dialogs/SettingsDialog_rc.py dialogs/SettingsDialog.qrc
%PYRCC5% -o dialogs/StackTraceMessageBox_rc.py dialogs/StackTraceMessageBox.qrc 
%PYRCC5% -o SearchPage_rc.py SearchPage.qrc
%PYRCC5% -o MainWindow_rc.py MainWindow.qrc
