.\build-windows-vars.ps1

#
# Compile interface definitions
# 

python GenerateStylesheet.py
& $env:PYRCC5 -o qdarkstyle/style_rc.py qdarkstyle\style.qrc
& $env:PYRCC5 -o qlightstyle/style_rc.py qlightstyle\style.qrc

& $env:PYUIC --from-imports -o widgets\Ui_LeaveLastTabWidget.py -x widgets\LeaveLastTabWidget.ui 
& $env:PYUIC --from-imports -o widgets\Ui_InDocumentSearchWidget.py -x widgets\InDocumentSearchWidget.ui 
& $env:PYUIC --from-imports -o dialogs\Ui_SettingsItem.py -x dialogs\SettingsItem.ui 
& $env:PYUIC --from-imports -o dialogs\Ui_SettingsDialog.py -x dialogs\SettingsDialog.ui 
& $env:PYUIC --from-imports -o dialogs\Ui_AboutDialog.py -x dialogs\AboutDialog.ui 
& $env:PYUIC --from-imports -o dialogs\Ui_StackTraceMessageBox.py -x dialogs\StackTraceMessageBox.ui
& $env:PYUIC --from-imports -o dialogs\Ui_ProgressBar.py -x dialogs\ProgressBar.ui 
& $env:PYUIC --from-imports -o dialogs\Ui_CheckableItemsDialog.py -x dialogs\CheckableItemsDialog.ui 
& $env:PYUIC --from-imports -o dialogs\Ui_UserHintDialog.py -x dialogs\UserHintDialog.ui 
& $env:PYUIC --from-imports -o dialogs\Ui_GotoLineDialog.py -x dialogs\GotoLineDialog.ui
& $env:PYUIC --from-imports -o dialogs\Ui_HelpViewerDialog.py -x dialogs\HelpViewerDialog.ui 
& $env:PYUIC --from-imports -o dialogs\Ui_RegExTesterDlg.py -x dialogs\RegExTesterDlg.ui
& $env:PYUIC -o Ui_MainWindow.py -x MainWindow.ui 
& $env:PYUIC -o Ui_SearchPage.py -x SearchPage.ui 
& $env:PYUIC -o Ui_SourceViewer.py -x SourceViewer.ui 
& $env:PYUIC -o Ui_MatchesOverview.py -x MatchesOverview.ui 

& $env:PYRCC5 -o widgets\LeaveLastTabWidget_rc.py widgets\LeaveLastTabWidget.qrc
& $env:PYRCC5 -o widgets\InDocumentSearchWidget_rc.py widgets\InDocumentSearchWidget.qrc
& $env:PYRCC5 -o dialogs\SettingsDialog_rc.py dialogs\SettingsDialog.qrc
& $env:PYRCC5 -o dialogs\StackTraceMessageBox_rc.py dialogs\StackTraceMessageBox.qrc 
& $env:PYRCC5 -o SearchPage_rc.py SearchPage.qrc
& $env:PYRCC5 -o MainWindow_rc.py MainWindow.qrc


