# -*- coding: utf-8 -*-
"""
Copyright (C) 2011 Oliver Tengler

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
from PyQt4.QtCore import * 
from PyQt4.QtGui import *
from Ui_SourceViewer import Ui_SourceViewer 
from FileTools import fopen
from AppConfig import appConfig
import HighlightingRulesCache

class SourceViewer (QWidget):
    # Triggered if a selection was finished while holding a modifier key down
    selectionFinishedWithKeyboardModifier = pyqtSignal('QString',  int)
    noPreviousMatch = pyqtSignal()
    noNextMatch = pyqtSignal()
    directoryDropped = pyqtSignal('QString')
    
    def __init__ (self, parent):
        super (SourceViewer, self).__init__(parent)
        self.ui = Ui_SourceViewer()
        self.ui.setupUi(self)
        self.ui.frameSearch.hide()
        
        self.sourceFont = None
        self.searchData = None
        self.__reset()
        self.__processConfig(None)
        
        self.actionReloadFile = QAction(self, shortcut=Qt.Key_F5, triggered= self.reloadFile)
        self.addAction(self.actionReloadFile)
        
        # Forward the signal
        self.ui.textEdit.selectionFinishedWithKeyboardModifier.connect(self.selectionFinishedWithKeyboardModifier)
        
        # Help the text edit to update the syntax highlighting. This works around an
        # update problem of the text edit used in a scroll area.
        self.ui.textEdit.updateNeeded.connect(self.textEditUpdateNeeded)
        
    @pyqtSlot()
    def textEditUpdateNeeded (self):
        self.ui.textEdit.viewport().update ()
        
    def reloadConfig (self,  font):
        self.__processConfig(font)
        
    def __processConfig (self,  font):
        if font:
            self.sourceFont = font
            self.ui.textEdit.setFont(self.sourceFont)
        
        self.bMatchOverFiles = appConfig().matchOverFiles

        config = appConfig().SourceViewer
        if self.ui.textEdit.tabStopWidth() != config.TabWidth*10:
            self.ui.textEdit.setTabStopWidth(config.TabWidth*10)
        
    def __reset (self):
        self.currentFile = None
        self.matches = [] # touples with position and length
        self.curMatch = -1
        self.ui.labelCursor.setText("")
        self.ui.labelFile.setText(self.trUtf8("No document loaded"))
        self.ui.textEdit.setPlainText("")
        self.__resetTextCursor()
        self.__setInfoLabel()
        self.ui.textEdit.setDynamicHighlight(None)
    
    def setSearchData (self,  searchData):
        self.__reset()
        self.searchData = searchData
        self.ui.textEdit.highlighter.setSearchData (searchData)
        
    def showFile (self,  name):
        self.__reset()
        self.ui.labelFile.setText(name)
        self.currentFile = name
        
        try:
            with fopen(name) as file:
                text = file.read()
        except:
            text = self.trUtf8("Failed to open file")
        
        rules = HighlightingRulesCache.rules().getRulesByFileName(name,  self.sourceFont)
        self.ui.textEdit.highlighter.setHighlightingRules (rules,  text)
        self.ui.textEdit.setPlainText(text)
            
        if self.searchData:
            self.matches = [match for match in self.searchData.matches (text)]
            self.nextMatch ()
        
    @pyqtSlot()
    def reloadFile(self):
        if self.currentFile:
            self.showFile(self.currentFile)
        
    @pyqtSlot()
    def nextMatch (self):
        if self.curMatch < len(self.matches)-1:
            self.curMatch += 1
            self.__scrollToMatch (self.curMatch)
            self.__setInfoLabel ()
            if not self.bMatchOverFiles:
                self.__enableNextPrevious()
        else:
            if self.bMatchOverFiles:
                self.noNextMatch.emit()
        
    @pyqtSlot()
    def previousMatch (self):
        if self.curMatch > 0:
            self.curMatch -= 1
            self.__scrollToMatch (self.curMatch)
            self.__setInfoLabel ()
            if not self.bMatchOverFiles:
                self.__enableNextPrevious()
        else:
            if self.bMatchOverFiles:
                self.noPreviousMatch.emit()
            
    @pyqtSlot()
    def nextSearch(self):
        search = self.ui.editSearch.text()
        if search:
            self.ui.textEdit.find(search)
            
    @pyqtSlot()
    def previousSearch(self):
        search = self.ui.editSearch.text()
        if search:
            self.ui.textEdit.find(search,  QTextDocument.FindBackward)

    @pyqtSlot()
    def updateCurrentLine (self):
        line = self.ui.textEdit.textCursor().blockNumber()+1
        self.ui.labelCursor.setText(self.trUtf8("Line") + " %u" % (line, ))
        
    @pyqtSlot()
    def showSearchFrame(self):
        self.ui.frameSearch.show()
        self.ui.editSearch.setFocus(Qt.MouseFocusReason)
        text = self.ui.textEdit.textCursor().selectedText().strip()
        if text:
            self.ui.editSearch.setText(text)
        self.ui.editSearch.selectAll()
        
    # Disable next/previous buttons if they don't make sense
    def __enableNextPrevious (self):          
        bEnablePrevious = self.curMatch > 0
        if self.ui.buttonMatchPrevious.isEnabled() != bEnablePrevious:
            self.ui.buttonMatchPrevious.setEnabled(bEnablePrevious)
        bEnableNext = self.curMatch < len(self.matches)-1
        if self.ui.buttonMatchNext.isEnabled() != bEnableNext:
            self.ui.buttonMatchNext.setEnabled(bEnableNext)
        
    def __resetTextCursor (self):
        cursor = self.ui.textEdit.textCursor()
        cursor.setPosition(0)
        self.ui.textEdit.setTextCursor(cursor)
        extra = QTextEdit.ExtraSelection ()
        extra.cursor = cursor
        self.ui.textEdit.setExtraSelections((extra,))
        
    def __setInfoLabel (self):
        str = ""
        if len(self.matches) and self.curMatch != -1:
            str = str + "%u/%u " % (self.curMatch+1, len(self.matches))
        self.ui.labelInfo.setText (str)
        
    def __scrollToMatch (self, num):
        if num < 0 or num >= len(self.matches):
            return
        index, length = self.matches[num]
        
        scrollDir = index - self.ui.textEdit.textCursor().position() # Determine if we need to scroll down or up

        extras = []
        extra1 = QTextEdit.ExtraSelection ()
        extra1.cursor = self.ui.textEdit.textCursor()
        extra1.cursor.setPosition (index)
        extra1.format.setProperty (QTextFormat.FullWidthSelection,  True)
        extra1.format.setBackground (QColor(170,255,127))
        extras.append(extra1)
       
        extra2 = QTextEdit.ExtraSelection ()
        extra2.cursor = self.ui.textEdit.textCursor()
        extra2.cursor.setPosition (index)
        extra2.cursor.setPosition (index+length,  QTextCursor.KeepAnchor)
        extra2.format.setBackground (Qt.yellow)
        extras.append(extra2)
        
        self.ui.textEdit.setExtraSelections (extras)
        
        cursor = self.ui.textEdit.textCursor()
        cursor.setPosition(index)
        if scrollDir > 0:
            cursor.movePosition(QTextCursor.Down, QTextCursor.MoveAnchor,  5)
        elif scrollDir < 0:
            cursor.movePosition(QTextCursor.Up, QTextCursor.MoveAnchor,  5)
        self.ui.textEdit.setTextCursor (cursor) # otherwise 'ensureCursorVisible' doesn't work
        self.ui.textEdit.ensureCursorVisible ()
        
        cursor.setPosition(index)
        self.ui.textEdit.setTextCursor(cursor) # jump back to match to make sure the line number of the match is correct
        
    def dragEnterEvent(self, event):
        # check if the data contains urls
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        
    def dropEvent(self, event):
        # check if the data contains urls
        if event.mimeData().hasUrls():
            name = event.mimeData().urls()[0].toLocalFile()
            if os.path.isfile(name):
                self.showFile(name)
            elif os.path.isdir(name):
                self.directoryDropped.emit(name)
    
def main():    
    import sys
    app = QApplication(sys.argv) 
    w = SourceViewer(None) 
    w.show() 
    #w.showFile(r"D:\C++\qt-everywhere-opensource-src-4.7.3\src\svg\qsvghandler.cpp")
    w.showFile(r"D:\test.cpp")
    sys.exit(app.exec_()) 

if __name__ == "__main__":
    main()
    


