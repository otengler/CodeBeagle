set PYDIR=C:\Python32
set PYTHON=%PYDIR%\python

set PYUIC=%PYDIR%\Lib\site-packages\PyQt4\uic\pyuic.py
set PYRCC4=%PYDIR%\Lib\site-packages\PyQt4\pyrcc4.exe

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

copy /Y resources\Crystal\*.* resources\

%PYRCC4% -o LeaveLastTabWidget_rc.py -py3 LeaveLastTabWidget.qrc
%PYRCC4% -o MainWindow_rc.py -py3 MainWindow.qrc
%PYRCC4% -o SearchPage_rc.py -py3 SearchPage.qrc
%PYRCC4% -o SettingsDialog_rc.py -py3 SettingsDialog.qrc

 
