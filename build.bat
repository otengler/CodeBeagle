call buildvars.bat

set PYUIC=%PYDIR%\scripts\pyuic5.exe
set PYRCC5=%PYDIR%\scripts\pyrcc5.exe

%PYTHON% %PYUIC% -o Ui_MainWindow.py -x MainWindow.ui 
%PYTHON% %PYUIC% -o Ui_LeaveLastTabWidget.py -x LeaveLastTabWidget.ui 
%PYTHON% %PYUIC% -o Ui_ProgressBar.py -x ProgressBar.ui 
%PYTHON% %PYUIC% -o Ui_SearchPage.py -x SearchPage.ui 
%PYTHON% %PYUIC% -o Ui_SourceViewer.py -x SourceViewer.ui 
%PYTHON% %PYUIC% -o Ui_SettingsItem.py -x SettingsItem.ui 
%PYTHON% %PYUIC% -o Ui_SettingsDialog.py -x SettingsDialog.ui 
%PYTHON% %PYUIC% -o Ui_CheckableItemsDialog.py -x CheckableItemsDialog.ui 
%PYTHON% %PYUIC% -o Ui_HelpViewerDialog.py -x HelpViewerDialog.ui 
%PYTHON% %PYUIC% -o Ui_UserHintDialog.py -x UserHintDialog.ui 
%PYTHON% %PYUIC% -o Ui_AboutDialog.py -x AboutDialog.ui 
%PYTHON% %PYUIC% -o Ui_MatchesOverview.py -x MatchesOverview.ui 
%PYTHON% %PYUIC% -o Ui_GotoLineDialog.py -x GotoLineDialog.ui
%PYTHON% %PYUIC% -o Ui_StackTraceMessageBox.py -x StackTraceMessageBox.ui

copy /Y resources\Crystal\*.* resources\

%PYRCC5% -o LeaveLastTabWidget_rc.py LeaveLastTabWidget.qrc
%PYRCC5% -o MainWindow_rc.py MainWindow.qrc
%PYRCC5% -o SearchPage_rc.py SearchPage.qrc
%PYRCC5% -o SettingsDialog_rc.py SettingsDialog.qrc
%PYRCC5% -o StackTraceMessageBox_rc.py StackTraceMessageBox.qrc
%PYRCC5% -o darkorange_resources_rc.py style/darkorange/resources.qrc
 
