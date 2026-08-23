.\build-windows-vars.ps1

#
# Compile interface definitions
# 

if (-not $?) { throw "GenerateStylesheet failed" }

function Compile-Ui($output, $uiFile) {
    $outputPath = $output -replace '\\', '/'
    $inputPath = $uiFile -replace '\\', '/'
    Write-Host "  Compiling $uiFile -> $output"
    & $env:PYUIC -o $outputPath $inputPath
    if ($LASTEXITCODE -ne 0) { throw "pyside2-uic failed for $uiFile" }
    python fix_uic_imports.py $outputPath
    if (-not $?) { throw "fix_uic_imports.py failed for $output" }
}

Compile-Ui "widgets\Ui_LeaveLastTabWidget.py" "widgets\LeaveLastTabWidget.ui"
Compile-Ui "widgets\Ui_InDocumentSearchWidget.py" "widgets\InDocumentSearchWidget.ui"
Compile-Ui "dialogs\Ui_SettingsItem.py" "dialogs\SettingsItem.ui"
Compile-Ui "dialogs\Ui_SettingsDialog.py" "dialogs\SettingsDialog.ui"
Compile-Ui "dialogs\Ui_AboutDialog.py" "dialogs\AboutDialog.ui"
Compile-Ui "dialogs\Ui_StackTraceMessageBox.py" "dialogs\StackTraceMessageBox.ui"
Compile-Ui "dialogs\Ui_ProgressBar.py" "dialogs\ProgressBar.ui"
Compile-Ui "dialogs\Ui_CheckableItemsDialog.py" "dialogs\CheckableItemsDialog.ui"
Compile-Ui "dialogs\Ui_ExcludedExtensionsDialog.py" "dialogs\ExcludedExtensionsDialog.ui"
Compile-Ui "dialogs\Ui_UserHintDialog.py" "dialogs\UserHintDialog.ui"
Compile-Ui "dialogs\Ui_GotoLineDialog.py" "dialogs\GotoLineDialog.ui"
Compile-Ui "dialogs\Ui_HelpViewerDialog.py" "dialogs\HelpViewerDialog.ui"
Compile-Ui "dialogs\Ui_RegExTesterDlg.py" "dialogs\RegExTesterDlg.ui"
Compile-Ui "Ui_MainWindow.py" "MainWindow.ui"
Compile-Ui "Ui_SearchPage.py" "SearchPage.ui"
Compile-Ui "Ui_SourceViewer.py" "SourceViewer.ui"
Compile-Ui "Ui_MatchesOverview.py" "MatchesOverview.ui"
Compile-Ui "Ui_MatchesOverviewLabel.py" "MatchesOverviewLabel.ui"
# ai-agent
Compile-Ui "ai_agent\dialogs\Ui_AgentInstructionsDialog.py" "ai_agent\dialogs\AgentInstructionsDialog.ui"