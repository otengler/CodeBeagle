#!/bin/bash

. ./build-unix-vars.sh

#
# Compile interface definitions
# 

"$PYTHON" GenerateStylesheet.py

function compile_ui {
    output=$1
    uiFile=$2
    "$PYUIC" -o "$output" "$uiFile" 2>/dev/null
}

compile_ui widgets/Ui_LeaveLastTabWidget.py widgets/LeaveLastTabWidget.ui
compile_ui widgets/Ui_InDocumentSearchWidget.py widgets/InDocumentSearchWidget.ui
compile_ui dialogs/Ui_SettingsItem.py dialogs/SettingsItem.ui
compile_ui dialogs/Ui_SettingsDialog.py dialogs/SettingsDialog.ui
compile_ui dialogs/Ui_AboutDialog.py dialogs/AboutDialog.ui
compile_ui dialogs/Ui_StackTraceMessageBox.py dialogs/StackTraceMessageBox.ui
compile_ui dialogs/Ui_ProgressBar.py dialogs/ProgressBar.ui
compile_ui dialogs/Ui_CheckableItemsDialog.py dialogs/CheckableItemsDialog.ui
compile_ui dialogs/Ui_ExcludedExtensionsDialog.py dialogs/ExcludedExtensionsDialog.ui
compile_ui dialogs/Ui_UserHintDialog.py dialogs/UserHintDialog.ui
compile_ui dialogs/Ui_GotoLineDialog.py dialogs/GotoLineDialog.ui
compile_ui dialogs/Ui_HelpViewerDialog.py dialogs/HelpViewerDialog.ui
compile_ui dialogs/Ui_RegExTesterDlg.py dialogs/RegExTesterDlg.ui
compile_ui Ui_MainWindow.py MainWindow.ui
compile_ui Ui_SearchPage.py SearchPage.ui
compile_ui Ui_SourceViewer.py SourceViewer.ui
compile_ui Ui_MatchesOverview.py MatchesOverview.ui
compile_ui Ui_MatchesOverviewLabel.py MatchesOverviewLabel.ui
# ai-agent
compile_ui "ai_agent/dialogs/Ui_AgentInstructionsDialog.py" "ai_agent/dialogs/AgentInstructionsDialog.ui"