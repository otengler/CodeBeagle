# -*- coding: utf-8 -*-
"""
Copyright (C) 2021 Oliver Tengler

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
import threading
from typing import Optional, List
from tools.FileTools import fopen, freadall
from  . import FullTextIndex, IndexConfiguration, Query, IndexUpdater

emptyPattern = re.compile("") # make mypy happy

class ResultSet:
    def __init__(self, matches: Optional[FullTextIndex.SearchResult] = None, searchData: Optional[Query.Query] = None,
                 perfReport: Optional[FullTextIndex.PerformanceReport] = None, label: Optional[str] = None) -> None:

        self.matches = matches or []
        self.perfReport = perfReport
        self.searchData = searchData
        self.label = label

class SearchMethods:
    """
    Holds an instance of FullTextIndex. Setting the instance is secured by a lock because
    the call to 'cancel' may happen any time - also during construction and assignment of FullTextIndex
    """
    def __init__(self) -> None:
        self.fti: Optional[FullTextIndex.FullTextIndex] = None
        self.lock = threading.Lock()

    def searchContent(self, searchData: FullTextIndex.ContentQuery, indexConf: IndexConfiguration.IndexConfiguration, 
                      commonKeywordMap:FullTextIndex.CommonKeywordMap, cancelEvent: Optional[threading.Event]=None) -> ResultSet:

        try:
            if indexConf.isContentIndexed():
                return self.__searchContentIndexed(searchData, indexConf, commonKeywordMap, cancelEvent)
            return self.__searchContentDirect(searchData, indexConf, cancelEvent)
        finally:
            with self.lock:
                del self.fti
                self.fti = None

    def __searchContentIndexed(self, searchData: FullTextIndex.ContentQuery, indexConf: IndexConfiguration.IndexConfiguration,
                               commonKeywordMap:FullTextIndex.CommonKeywordMap, cancelEvent: Optional[threading.Event]=None) -> ResultSet:
        perfReport = FullTextIndex.PerformanceReport()
        with perfReport.newAction("Init database"):
            with self.lock:
                self.fti = FullTextIndex.FullTextIndex(indexConf.indexdb)
            result = ResultSet(self.fti.searchContent(searchData, perfReport, commonKeywordMap, cancelEvent=cancelEvent), searchData, perfReport)
        return result

    def __searchContentDirect(self, searchData: FullTextIndex.ContentQuery, indexConf: IndexConfiguration.IndexConfiguration, cancelEvent: Optional[threading.Event]=None) -> ResultSet:
        matches: List[str] = []
        for directory in indexConf.directories:
            for dirName, fileName in IndexUpdater.genFind(indexConf.extensions, directory, indexConf.dirExcludes):
                file = os.path.join(dirName, fileName)
                if searchData.matchFolderAndExtensionFilter(file):
                    try:
                        for _ in searchData.matches(freadall(file)):
                            matches.append(file)
                            break
                    except:
                        pass
                if cancelEvent and cancelEvent.is_set():
                    return ResultSet([], searchData)
        matches = removeDupsAndSort(matches)
        return ResultSet(matches, searchData)

    def searchFileName(self, searchData: FullTextIndex.FileQuery, indexConf: IndexConfiguration.IndexConfiguration, cancelEvent: Optional[threading.Event]=None) -> ResultSet:
        try:
            if indexConf.isFileNameIndexed():
                return self.__searchFileNameIndexed(searchData, indexConf, cancelEvent)
            return self.__searchFileNameDirect(searchData, indexConf, cancelEvent)
        finally:
            with self.lock:
                del self.fti
                self.fti = None

    def __searchFileNameIndexed(self, searchData: FullTextIndex.FileQuery, indexConf: IndexConfiguration.IndexConfiguration, cancelEvent: Optional[threading.Event]=None) -> ResultSet:
        perfReport = FullTextIndex.PerformanceReport()
        with perfReport.newAction("Init database"):
            with self.lock:
                self.fti = FullTextIndex.FullTextIndex(indexConf.indexdb)
            result = ResultSet(self.fti.searchFile(searchData, perfReport, cancelEvent=cancelEvent), searchData, perfReport)
        return result

    def __searchFileNameDirect(self, searchData: FullTextIndex.FileQuery, indexConf: IndexConfiguration.IndexConfiguration, cancelEvent: Optional[threading.Event]=None) -> ResultSet:
        search = searchData.search
        searchLower = search.lower()

        hasWildcards = Query.hasFileNameWildcard(search)
        bCaseSensitive = searchData.bCaseSensitive

        searchPattern = emptyPattern
        if hasWildcards:
            reFlags = 0
            if not bCaseSensitive:
                reFlags = re.IGNORECASE
            searchPattern = re.compile(Query.createPathMatchPattern(search, True), reFlags)

        matches: List[str] = []
        for directory in indexConf.directories:
            for dirName, fileName in IndexUpdater.genFind(indexConf.extensions, directory, indexConf.dirExcludes):
                fullPath = os.path.join(dirName, fileName)
                name,_ = os.path.splitext(fileName)
                if not hasWildcards:
                    if bCaseSensitive:
                        if name != search:
                            continue
                    else:
                        if name.lower() != searchLower:
                            continue
                elif not searchPattern.match(name):
                    continue
                if searchData.matchFolderAndExtensionFilter(fullPath): # TODO: splits file name again
                    matches.append(fullPath)
                if cancelEvent and cancelEvent.is_set():
                    return ResultSet([], searchData)
        matches.sort()
        return ResultSet(matches, searchData)

    def cancel(self) -> None:
        with self.lock:
            if self.fti:
                self.fti.interrupt()

def removeDupsAndSort(matches: FullTextIndex.SearchResult) -> FullTextIndex.SearchResult:
    """Remove duplicates and sort"""
    uniqueMatches = set()
    for match in matches:
        uniqueMatches.add(match)
    matches = [match for match in uniqueMatches] # make list from set
    matches.sort()
    return matches
