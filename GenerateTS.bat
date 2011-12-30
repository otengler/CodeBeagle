set SOURCES1=AppConfig.py Config.py FullTextIndex.py IndexConfiguration.py LeaveLastTabWidget.py 
set SOURCES2=LeaveLastTabWidget_rc.py MainWindow_rc.py PathDragListView.py PathVisualizerDelegate.py ProgressBar.py
set SOURCES3=SearchPage.py SearchPageTabWidget.py SearchPage_rc.py setup.py SourceViewer.py
set SOURCES4=testsuite.py Ui_LeaveLastTabWidget.py Ui_MainWindow.py Ui_ProgressBar.py Ui_SearchPage.py
set SOURCES5=Ui_SourceViewer.py UpdateIndex.py

pylupdate4 %SOURCES1% %SOURCES2% %SOURCES3% %SOURCES4% %SOURCES5% -ts CodeBeagle.ts
