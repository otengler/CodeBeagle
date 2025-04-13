#!/bin/bash

. ./build-linux-vars.sh

#
# Compile interface definitions
# 

"$PYTHON" GenerateStylesheet.py

"$PYUIC" --from-imports -o widgets/Ui_LeaveLastTabWidget.py -x widgets/LeaveLastTabWidget.ui 
"$PYUIC" --from-imports -o widgets/Ui_InDocumentSearchWidget.py -x widgets/InDocumentSearchWidget.ui 
"$PYUIC" --from-imports -o dialogs/Ui_SettingsItem.py -x dialogs/SettingsItem.ui 
"$PYUIC" --from-imports -o dialogs/Ui_SettingsDialog.py -x dialogs/SettingsDialog.ui 
"$PYUIC" --from-imports -o dialogs/Ui_AboutDialog.py -x dialogs/AboutDialog.ui 
"$PYUIC" --from-imports -o dialogs/Ui_StackTraceMessageBox.py -x dialogs/StackTraceMessageBox.ui
"$PYUIC" --from-imports -o dialogs/Ui_ProgressBar.py -x dialogs/ProgressBar.ui 
"$PYUIC" --from-imports -o dialogs/Ui_CheckableItemsDialog.py -x dialogs/CheckableItemsDialog.ui 
"$PYUIC" --from-imports -o dialogs/Ui_UserHintDialog.py -x dialogs/UserHintDialog.ui 
"$PYUIC" --from-imports -o dialogs/Ui_GotoLineDialog.py -x dialogs/GotoLineDialog.ui
"$PYUIC" --from-imports -o dialogs/Ui_HelpViewerDialog.py -x dialogs/HelpViewerDialog.ui 
"$PYUIC" --from-imports -o dialogs/Ui_RegExTesterDlg.py -x dialogs/RegExTesterDlg.ui
"$PYUIC" -o Ui_MainWindow.py -x MainWindow.ui 
"$PYUIC" -o Ui_SearchPage.py -x SearchPage.ui 
"$PYUIC" -o Ui_SourceViewer.py -x SourceViewer.ui 
"$PYUIC" -o Ui_MatchesOverview.py -x MatchesOverview.ui 



