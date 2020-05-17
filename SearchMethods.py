# -*- coding: utf-8 -*-
"""
Copyright (C) 2012 Oliver Tengler

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
from typing import List, Pattern, Iterator, Tuple, Optional, cast
import threading
from PyQt5.QtCore import QObject
from tools import AsynchronousTask
from tools.FileTools import fopen
from fulltextindex import FullTextIndex, IndexUpdater, IndexConfiguration

class ResultSet:
    def __init__(self, matches: FullTextIndex.SearchResult = None, searchData: FullTextIndex.Query = None,
                 perfReport: FullTextIndex.PerformanceReport = None, label: str = None) -> None:

        self.matches = matches or []
        self.perfReport = perfReport
        self.searchData = searchData
        self.label = label

class ScriptSearchData:
    def __init__(self, reExpr: Pattern) -> None:
        self.reExpr = reExpr

    def matches(self, data: str) -> Iterator[Tuple[int,int]]:
        """Yields all matches in str. Each match is returned as the touple (position,length)."""
        if not self.reExpr:
            return
        cur = 0
        while True:
            result = self.reExpr.search(data, cur)
            if result:
                startPos, endPos = result.span()
                yield (startPos, endPos-startPos)
                cur = endPos
            else:
                return

SearchParams = Tuple[str, str, str, bool] # Search query, folders, extensions, case sensitive

def search(parent: QObject, params: SearchParams, indexConf: IndexConfiguration.IndexConfiguration, commonKeywordMap: FullTextIndex.CommonKeywordMap=None) -> ResultSet:
    """This executes an indexed or a direct search. This depends on the IndexConfiguration setting "indexUpdateMode"."""
    commonKeywordMap = commonKeywordMap or {}
    strSearch, strFolderFilter, strExtensionFilter, bCaseSensitive = params
    if not strSearch:
        return ResultSet()
    searchData = FullTextIndex.SearchQuery(strSearch, strFolderFilter, strExtensionFilter, bCaseSensitive)
    result: ResultSet
    if indexConf.generatesIndex():
        ftiSearch = FullTextIndexSearch()
        result = AsynchronousTask.execute(parent, ftiSearch, searchData, commonKeywordMap, indexConf, bEnableCancel=True, cancelAction=ftiSearch.cancel)
    else:
        result = AsynchronousTask.execute(parent, directSearchAsync, searchData, indexConf, bEnableCancel=True)

    result.label = strSearch
    return result

class FullTextIndexSearch:
    """
    Holds an instance of FullTextIndex. Setting the instance is secured by a lock because
    the call to 'cancel' may happen any time - also during construction and assignment of FullTextIndex
    """
    def __init__(self) -> None:
        self.fti: Optional[FullTextIndex.FullTextIndex] = None
        self.lock = threading.Lock()

    def __call__(self, searchData: FullTextIndex.Query, commonKeywordMap:FullTextIndex.CommonKeywordMap,
                 indexConf: IndexConfiguration.IndexConfiguration, cancelEvent: threading.Event=None) -> ResultSet:

        perfReport = FullTextIndex.PerformanceReport()
        with perfReport.newAction("Init database"):
            with self.lock:
                self.fti = FullTextIndex.FullTextIndex(indexConf.indexdb)
            result = ResultSet(self.fti.search(searchData, perfReport, commonKeywordMap, cancelEvent=cancelEvent), searchData, perfReport)
        with self.lock:
            del self.fti
            self.fti = None
        return result

    def cancel(self) -> None:
        with self.lock:
            if self.fti:
                self.fti.interrupt()

def directSearchAsync(searchData: FullTextIndex.Query, indexConf: IndexConfiguration.IndexConfiguration, cancelEvent: threading.Event=None) -> ResultSet:
    matches: List[str] = []
    for directory in indexConf.directories:
        for dirName, fileName in IndexUpdater.genFind(indexConf.extensions, directory, indexConf.dirExcludes):
            file = os.path.join(dirName, fileName)
            if searchData.matchFolderAndExtensionFilter(file):
                with fopen(file) as inputFile:
                    for _ in searchData.matches(inputFile.read()):
                        matches.append(file)
                        break
            if cancelEvent and cancelEvent.is_set():
                return ResultSet([], searchData)
    matches = removeDupsAndSort(matches)
    return ResultSet(matches, searchData)

def customSearch(parent: QObject, script: str, params: SearchParams, indexConf: IndexConfiguration.IndexConfiguration,
                 commonKeywordMap: FullTextIndex.CommonKeywordMap=None) -> ResultSet:

    """
    Executes a custom search script from disk. The script receives a locals dictionary with all neccessary
    search parameters and returns its result in the variable "result". The variable "highlight" must be set
    to a regular expression which is used to highlight the matches in the result.
    """
    commonKeywordMap = commonKeywordMap or {}
    result: ResultSet = AsynchronousTask.execute(parent, customSearchAsync, os.path.join("scripts", script), params, commonKeywordMap, indexConf)
    return result

def customSearchAsync(script: str, params: SearchParams, commonKeywordMap: FullTextIndex.CommonKeywordMap,
                      indexConf: IndexConfiguration.IndexConfiguration) -> ResultSet:

    import re
    query, folders, extensions, caseSensitive = params

    def performSearch(strSearch: str, strFolderFilter: str="", strExtensionFilter:str="", bCaseSensitive: bool=False) -> FullTextIndex.SearchResult:
        if not strSearch:
            return []
        searchData = FullTextIndex.SearchQuery(strSearch, strFolderFilter, strExtensionFilter, bCaseSensitive)
        if indexConf.generatesIndex():
            ftiSearch = FullTextIndexSearch()
            return ftiSearch(searchData, commonKeywordMap, indexConf).matches
        return directSearchAsync(searchData, indexConf).matches

    def regexFromText(strQuery: str, bCaseSensitive: bool) -> Pattern:
        query = FullTextIndex.SearchQuery(strQuery, "", "", bCaseSensitive)
        return query.regExForMatches()

    class Result:
        def __init__(self) -> None:
            self.matches: FullTextIndex.SearchResult = []
            self.highlight = None
            self.label = "Custom script"

    localsDict = {"re": re,
                  "performSearch" : performSearch,
                  "regexFromText" : regexFromText,
                  "query" : query,
                  "folders" : folders,
                  "extensions" : extensions,
                  "caseSensitive" : caseSensitive,
                  "result" : Result()}

    # The actual script is wrapped in the function "customSearch". It is needed to
    # establish a proper scope which enables access to local variables from sub functions
    # analog to globals. Example what caused problems:
    # import time
    # def foo(files):
    #    time.sleep(5)
    # foo(files)
    # This failed in previous versions with "global 'time' not found".
    scriptCode = ""
    with fopen(script) as file:
        scriptCode = "def customSearch(re,performSearch,regexFromText,query,folders,extensions,caseSensitive,result):\n"
        for line in file:
            scriptCode += "\t"
            scriptCode += line
        scriptCode += "\ncustomSearch(re,performSearch,regexFromText,query,folders,extensions,caseSensitive,result)\n"

    code = compile(scriptCode, script, 'exec')
    exec(code, globals(), localsDict)

    result = cast(Result,localsDict["result"])

    matches = result.matches
    highlight = result.highlight
    label = result.label

    matches = removeDupsAndSort(matches)
    if highlight:
        searchData = ScriptSearchData(highlight)
    else:
        # Highlight by default the query
        searchData = FullTextIndex.SearchQuery(query, "", "", caseSensitive)

    return ResultSet(matches, searchData, label=label)

def removeDupsAndSort(matches: FullTextIndex.SearchResult) -> FullTextIndex.SearchResult:
    """Remove duplicates and sort"""
    uniqueMatches = set()
    for match in matches:
        uniqueMatches.add(match)
    matches = [match for match in uniqueMatches]
    matches.sort()
    return matches
