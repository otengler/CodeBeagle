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
from PyQt4.QtCore import * 
from PyQt4.QtGui import *
import AsynchronousTask
import FullTextIndex

class ResultSet:
    def __init__(self, matches=[], searchData=None, perfReport=None, label=None):
        self.matches = matches
        self.perfReport = perfReport
        self.searchData = searchData
        self.label = label
        
class ScriptSearchData:
    def __init__(self,  reExpr):
        self.reExpr = reExpr
        
    # Yields all matches in str. Each match is returned as the touple (position,length)
    def matches (self,  str):
        if not self.reExpr:
            return
        cur = 0
        while True:
            result = self.reExpr.search(str, cur)
            if result:
                startPos, endPos = result.span()
                yield (startPos,  endPos-startPos)
                cur = endPos
            else:
                return

# This executes the regular search
def search (parent,  params,  indexConf):
    strSearch, strFolderFilter,  strExtensionFilter, bCaseSensitive = params
    if not len(strSearch):
        return ResultSet()
    searchData = FullTextIndex.SearchQuery (strSearch,  strFolderFilter,  strExtensionFilter,  bCaseSensitive)
    result = AsynchronousTask.execute (parent,  searchAsync,  searchData, indexConf)
    result.label = strSearch
    return result
    
def searchAsync(searchData, indexConf):
    perfReport = FullTextIndex.PerformanceReport()
    with perfReport.newAction("Init database"):
        fti = FullTextIndex.FullTextIndex(indexConf.indexdb)
    return ResultSet (fti.search (searchData,  perfReport),  searchData,  perfReport)
    
# Executes a custom search script from disk. The script receives a locals dictionary with all neccessary
# search parameters and returns its result in the variable "result". The variable "highlight" must be set
# to a regular expression which is used to highlight the matches in the result.
def customSearch (parent, script,  params, indexConf):
    strSearch, strFolderFilter,  strExtensionFilter, bCaseSensitive = params
    if not len(strSearch):
        return ResultSet()
    return AsynchronousTask.execute (parent,  customSearchAsync, os.path.join("scripts", script), params, indexConf)
    
def customSearchAsync (script,  params, indexConf):
    import re
    query, folders, extensions, caseSensitive = params
    def performSearch (strSearch,  strFolderFilter="",  strExtensionFilter="",  bCaseSensitive=False):
        searchData = FullTextIndex.SearchQuery (strSearch,  strFolderFilter,  strExtensionFilter,  bCaseSensitive)
        return searchAsync(searchData,  indexConf).matches
    localsDict = { "re":  re, 
                        "performSearch" : performSearch, 
                       "query" : query,  
                       "folders" : folders,  
                       "extensions" : extensions,  
                       "caseSensitive" : caseSensitive,  
                       "results" : [],  
                       "highlight" : None,  
                       "label" : "Custom script"}
    with open(script) as file: 
        code = compile(file.read(), script, 'exec')
    exec(code,  globals(),  localsDict)
    
    matches = localsDict["results"]
    highlight =  localsDict["highlight"]
    label = localsDict["label"]
    
    matches = removeDupsAndSort(matches)
    if highlight:
        searchData = ScriptSearchData (highlight)
    else:
        # Highlight  by default the query
        searchData = FullTextIndex.SearchQuery (query, "",  "",  caseSensitive)
    
    return ResultSet (matches,  searchData,  label=label)
    
# Remove duplicates and sort
def removeDupsAndSort(matches):
    uniqueMatches = set()
    for m in matches:
        uniqueMatches.add(m)
    matches = [m for m in uniqueMatches]
    matches.sort()
    return matches
