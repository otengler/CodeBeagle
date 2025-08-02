# -*- coding: utf-8 -*-
"""
Copyright (C) 2012 Oliver Tengler

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import re
from typing import Pattern, Iterator, Tuple, cast, Optional
from PyQt5.QtCore import QObject
from tools import AsynchronousTask
from tools.FileTools import fopen
from fulltextindex import FullTextIndex, IndexConfiguration
from fulltextindex.IStringMatcher import IStringMatcher, MatchPosition
from fulltextindex.SearchMethods import SearchMethods, ResultSet, removeDupsAndSort

class SearchParams:
    def __init__(self, search: str, folderFilter: str = "", extensionFilter: str = "", caseSensitive: bool = False):
        self.search = search
        self.folderFilter = folderFilter
        self.extensionFilter = extensionFilter
        self.caseSensitive = caseSensitive

def searchContent(parent: QObject, params: SearchParams, indexConf: IndexConfiguration.IndexConfiguration, commonKeywordMap: Optional[FullTextIndex.CommonKeywordMap] = None) -> ResultSet:
    """This executes an indexed or a direct search in the file content. This depends on the IndexConfiguration
       setting "indexUpdateMode" and "indexType"."""
    commonKeywordMap = commonKeywordMap or {}

    if not params.search:
        return ResultSet()

    searchData = FullTextIndex.ContentQuery(params.search, params.folderFilter, params.extensionFilter, params.caseSensitive)
    result: ResultSet

    ftiSearch = SearchMethods()
    result = AsynchronousTask.execute(parent, ftiSearch.searchContent, searchData, indexConf, commonKeywordMap, bEnableCancel=True, cancelAction=ftiSearch.cancel)
    result.label = params.search

    return result

def searchFileName(parent: QObject, params: SearchParams, indexConf: IndexConfiguration.IndexConfiguration) -> ResultSet:
    """This executes an indexed or a direct search for the file name. This depends on the IndexConfiguration
       setting "indexUpdateMode" and "indexType"."""

    if not params.search:
        return ResultSet()

    searchData = FullTextIndex.FileQuery(params.search, params.folderFilter, params.extensionFilter, params.caseSensitive)
    result: ResultSet

    ftiSearch = SearchMethods()
    result = AsynchronousTask.execute(parent, ftiSearch.searchFileName, searchData, indexConf, bEnableCancel=True, cancelAction=ftiSearch.cancel)
    result.label = params.search

    return result

def customSearch(parent: QObject, script: str, params: SearchParams, indexConf: IndexConfiguration.IndexConfiguration,
                 commonKeywordMap: Optional[FullTextIndex.CommonKeywordMap] = None) -> ResultSet:

    """
    Executes a custom search script from disk. The script receives a locals dictionary with all neccessary
    search parameters and returns its result in the variable "result". The variable "highlight" must be set
    to a regular expression which is used to highlight the matches in the result.
    """
    commonKeywordMap = commonKeywordMap or {}
    result: ResultSet = AsynchronousTask.execute(parent, __customSearchAsync, os.path.join("scripts", script), params, commonKeywordMap, indexConf)
    return result

class ScriptSearchData (IStringMatcher): 
    def __init__(self, reExpr: Pattern) -> None:
        self.reExpr = reExpr

    def matches(self, data: str) -> Iterator[MatchPosition]:
        """Yields all matches in str. Each match is returned as the touple (position,length)."""
        if not self.reExpr:
            return
        cur = 0
        while True:
            result = self.reExpr.search(data, cur)
            if result:
                startPos, endPos = result.span()
                yield MatchPosition(startPos, endPos-startPos)
                cur = endPos
            else:
                return

def __customSearchAsync(script: str, params: SearchParams, commonKeywordMap: FullTextIndex.CommonKeywordMap,
                        indexConf: IndexConfiguration.IndexConfiguration) -> ResultSet:

    query = params.search
    folders = params.folderFilter
    extensions = params.extensionFilter
    caseSensitive = params.caseSensitive

    def performSearch(strSearch: str, strFolderFilter: str="", strExtensionFilter:str="", bCaseSensitive: bool=False) -> FullTextIndex.SearchResult:
        if not strSearch:
            return []
        searchData = FullTextIndex.ContentQuery(strSearch, strFolderFilter, strExtensionFilter, bCaseSensitive)
        ftiSearch = SearchMethods()
        return ftiSearch.searchContent(searchData, indexConf, commonKeywordMap).matches

    def regexFromText(strQuery: str, bCaseSensitive: bool) -> Pattern:
        query = FullTextIndex.ContentQuery(strQuery, "", "", bCaseSensitive)
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
        searchData = FullTextIndex.ContentQuery(query, "", "", caseSensitive)

    return ResultSet(matches, searchData, label=label)
