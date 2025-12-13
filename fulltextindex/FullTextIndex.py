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

import sqlite3
import threading
from typing import List, Tuple, Iterable, Any, Dict, Callable, Optional
from tools.FileTools import fopen, freadall
from .IndexDatabase import IndexDatabase
from .FileSearch import searchFile
from .Query import Query, ContentQuery, FileQuery, PerformanceReport, ReportAction, safeLen, SearchResult
from .KeywordCaching import Keyword, getCachedKeywords, setCachedKeywords, checkAndInvalidateKeywordsCache

__all__ = ['ContentQuery', 'FileQuery', 'Query', 'PerformanceReport', 'SearchResult', 'Keyword', 'buildMapFromCommonKeywordFile', 'FullTextIndex']

ProgressFunction = Callable[[int], None]

def intersectSortedLists(l1: List[str], l2: List[str]) -> List[str]:
    l = 0
    r = 0
    l3 = []
    try:
        itemL = l1[l]
        itemR = l2[r]
        while True:
            if itemL < itemR:
                l += 1
                itemL = l1[l]
            elif itemL > itemR:
                r += 1
                itemR = l2[r]
            else:
                l3.append(itemL)
                l += 1
                r += 1
                itemL = l1[l]
                itemR = l2[r]
    except IndexError:
        pass
    return l3

KeywordList = List[List[Keyword]]

CommonKeywordMap = Dict[str,int]

def buildMapFromCommonKeywordFile(name:str) -> CommonKeywordMap:
    mapCommonKeywords = {}
    if name:
        with fopen(name, "r") as inputFile:
            for number, keyword in ((number, keyword.strip().lower()) for number, keyword in enumerate(inputFile)):
                if keyword:
                    mapCommonKeywords[keyword] = number
    return mapCommonKeywords

def cancelableSearch(func: Callable[..., SearchResult], *args: Any) -> SearchResult:
    try:
        return func(*args)
    except sqlite3.OperationalError as e:
        if str(e) == "interrupted":
            return []
        raise

class FullTextIndex (IndexDatabase):
    def __init__(self, strDbLocation: str) -> None:
        super().__init__(strDbLocation)

    def searchFile(self, query: FileQuery, perfReport: Optional[PerformanceReport]=None, cancelEvent:Optional[threading.Event]=None) -> SearchResult:
        return cancelableSearch(self.__searchFile, query, perfReport)

    def __searchFile(self, query: FileQuery, perfReport: Optional[PerformanceReport]=None) -> SearchResult:
        q = self.conn.cursor()
        return searchFile(q, query, perfReport)

    # commonKeywordMap maps  keywords to numbers. A lower number means a worse keyword. Bad keywords are very common like "h" in cpp files.
    def searchContent(self, query: ContentQuery, perfReport: Optional[PerformanceReport]=None, commonKeywordMap: Optional[CommonKeywordMap]=None,
                      cancelEvent: Optional[threading.Event]=None, reportProgress: Optional[ProgressFunction]=None) -> SearchResult:
        return cancelableSearch(self.__searchContent, query, perfReport, commonKeywordMap, cancelEvent, reportProgress)

    def __searchContent(self, query: ContentQuery, perfReport: Optional[PerformanceReport]=None, commonKeywordMap: Optional[CommonKeywordMap]=None, 
                        cancelEvent: Optional[threading.Event]=None, reportProgress: Optional[ProgressFunction]=None) -> SearchResult:
        if not isinstance(query, ContentQuery):
            raise RuntimeError("query must be a ContentQuery derived object")

        perfReport = perfReport or PerformanceReport()

        commonKeywordMap = commonKeywordMap or {}

        q = self.conn.cursor()

        # The result is a list of lists of Keyword objects
        kwList: KeywordList = []
        with perfReport.newAction("Finding keywords") as action:
            kwList = self.__getKeywords(q, query.indexedPartsLower(), reportAction=action)
            if not kwList:
                return []

        goodKeywords, badKeywords = self.__qualifyKeywords(kwList, commonKeywordMap)

        with perfReport.newAction("Finding documents") as action:
            result = self.__findDocsByKeywordsManualIntersect(q, goodKeywords, badKeywords, action)
            action.addData("%u matches", safeLen(result))
            if not result:
                return []

        if query.requiresReadingFile():
            with perfReport.newAction("Filtering results") as action:
                return self.__filterDocsBySearchPhrase(action, (r[0] for r in result), query, cancelEvent, reportProgress, len(result))
        else:
            with perfReport.newAction("Returning results"):
                if not query.folderFilter and not query.extensionFilter:
                    return [r[0] for r in result]
                return [r[0] for r in result if query.matchFolderAndExtensionFilter(r[0])]
        return []

    def __findDocsByKeywordsManualIntersect(self, q: sqlite3.Cursor, goodKeywords: KeywordList, badKeywords: KeywordList, reportAction: ReportAction) -> SearchResult:
        result: SearchResult = []
        allKeywords = [(True, keywords) for keywords in goodKeywords] + [(False, keywords) for keywords in badKeywords]
        for isGood, keywords in allKeywords:
            # Stop if all good keywords have been used and the result is stripped down to less than 100 files
            if not isGood:
                kwNames = ",".join((keyword.name for keyword in keywords))
                if result and len(result) < 100:
                    reportAction.addData("Search stopped with common keyword '%s'", kwNames)
                    break
                else:
                    if result:
                        reportAction.addData("Common keyword '%s' used because %u matches are too much", kwNames, len(result))
                    else:
                        reportAction.addData("Common keyword '%s' used as first keyword", kwNames)
            keywordIds = [keyword.id for keyword in keywords]
            placeholders = ",".join("?" * len(keywordIds))
            stmt = f"SELECT DISTINCT fullpath FROM kw2doc,documents WHERE docID=id AND kwID IN ({placeholders}) ORDER BY fullpath"
            q.execute(stmt, keywordIds)
            kwMatches = q.fetchall()
            if not result:
                result = kwMatches
            else:
                result = intersectSortedLists(result, kwMatches)
            if not result:
                return []
        return result

    def __filterDocsBySearchPhrase(self, action: ReportAction, results: Iterable[str], query: ContentQuery,
                                   cancelEvent: Optional[threading.Event]=None,
                                   reportProgress: Optional[ProgressFunction]=None, lenResults: int = 0) -> SearchResult:
        finalResults = []
        reExpr = query.regExForMatches()
        action.addData("RegEx: %s", reExpr.pattern)
        bHasFilters = query.folderFilter or query.extensionFilter
        lastProgress = None
        idx = 1
        for fullpath in results:
            if bHasFilters:
                if not query.matchFolderAndExtensionFilter(fullpath):
                    continue
            try:
                # Use query.matches() to support comment filtering
                fileContent = freadall(fullpath)
                for _ in query.matches(fileContent, fullpath):
                    finalResults.append(fullpath)
                    break
            except:
                pass

            if cancelEvent and cancelEvent.is_set():
                return []
            
            if reportProgress:
                progress = (int((idx*100)/lenResults))
                idx += 1
                if lastProgress != progress:
                    lastProgress = progress
                    reportProgress(progress)

        return finalResults

    # Receives a list of lists of Keywords and returns as two lists.
    # The first list contains the good keywords in input order. These are keywords which are not found if commonKeywordMap.
    # The second list contains the bad keywords which were found in commonKeywordMap ordered from the less worst to the worst.
    def __qualifyKeywords(self, kwList: KeywordList, commonKeywordMap: CommonKeywordMap) -> Tuple[KeywordList,KeywordList]:
        goodKeywords = []
        badKeywordsTemp = [] # contains touples (quality,keywords) in order to sort by quality
        for keywords in kwList:
            # Check if one of the keywords is found in mapCommonKeywords
            quality = None
            for keyword in keywords:
                if keyword.name in commonKeywordMap:
                    q = commonKeywordMap[keyword.name]
                    if not quality or q < quality:
                        quality = q
            if quality is None:
                # Not in the common keyword map
                goodKeywords.append(keywords)
            else:
                # In the common keyword map
                badKeywordsTemp.append((quality, keywords))
        badKeywords = [keywords for unusedQuality, keywords in sorted(badKeywordsTemp, reverse=True)]

        # Sort good keywords by length descending, the hope is that longer keywords are more unique
        return sorted(goodKeywords,reverse=True,key=len), badKeywords

    # Receives a list of keywords which might contain wildcards. For every passed keyword a list of Keyword objects
    # is returned. If a keyword is not found an empty list is returned.
    def __getKeywords(self, q: sqlite3.Cursor, keywordList: Iterable[str], reportAction: Optional[ReportAction]=None) -> KeywordList:
        # Check if database has been modified and invalidate cache if needed
        checkAndInvalidateKeywordsCache(self.strDbLocation)

        keys = []
        for originalKw in keywordList:
            keywordMatches: Optional[List[Keyword]] = None

            # Check cache first
            cachedResult = getCachedKeywords(self.strDbLocation, originalKw)
            if cachedResult is not None:
                keywordMatches = cachedResult

            if keywordMatches is None:
                # Not in cache - query database
                kw = originalKw
                query = "SELECT id,keyword FROM keywords WHERE"
                if kw.find("*") != -1:
                    query += " keyword LIKE ? ESCAPE '!'"
                    kw = kw.replace("_", "!_")
                    kw = kw.replace("*", "%")
                else:
                    query += " keyword=?"
                q.execute(query, (kw, ))
                result = q.fetchall()
                if not result:
                    if reportAction:
                        reportAction.addData("String '%s' was not found", originalKw)
                    return []
                keywordMatches = [Keyword(r[0], r[1]) for r in result]

                # Add to cache
                setCachedKeywords(self.strDbLocation, originalKw, keywordMatches)

            if reportAction:
                reportAction.addData("String '%s' results in %u keyword matches", originalKw, len(keywordMatches))
            keys.append(keywordMatches)
        return keys
