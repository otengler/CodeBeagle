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
import os.path
import abc
import re
import sqlite3
import time
import unittest
from tools.FileTools import fopen
from .IndexDatabase import IndexDatabase

reQueryToken = re.compile(r"[\w#*]+|<!.*!>")
reMatchWords = re.compile(r"(\*\*)([0-9]+)")
reMatchRegEx = re.compile(r"<!(.*)!>")

IndexPart = 1
ScanPart = 2
MatchWordsPart = 3
RegExPart = 4

def safeLen(obj):
    try:
        return len(obj)
    except:
        return 0

def intersectSortedLists(l1, l2):
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

# Return tokens which are in the index
def getTokens(text):
    parts = []
    pos = 0
    while True:
        result = reQueryToken.search(text, pos)
        if result:
            begin, pos = result.span()
            if result.group(0).replace("*", "") != "": # skip parts with asterisks only, they are not in the index
                parts.append((begin, pos))
        else:
            break
    return parts

# Returns the regular expression which matches a keyword
def kwExpr(kw):
    # If the keyword starts with '#' it is not matched if we search for word boundaries (\\b)
    if not kw.startswith("#"):
        return r"\b" + kw.replace("*", r"\w*") + r"\b"
    else:
        return kw.replace("*", r"\w*")

def trimScanPart(s):
    return s.replace(" ", "")

def splitSearchParts(strSearch: str):
    tokens = getTokens(strSearch)
    parts = []
    pos = 0
    for begin, end in tokens:
        if begin > pos:
            partScanPart = (ScanPart, trimScanPart(strSearch[pos:begin]))
            parts.append(partScanPart)
        token = strSearch[begin:end]
        result = reMatchWords.match(token) # special handling for **X syntax. It means to search for X unknown words
        if result and int(result.group(2)) > 0:
            matchWordsPart = (MatchWordsPart, int(result.group(2)))
            parts.append(matchWordsPart)
        elif token.startswith("<!"):
            r =  reMatchRegEx.match(token)
            if r:
                regExPart = (RegExPart, r.group(1))
            parts.append(regExPart)
        else:
            partIndexPart = (IndexPart, token)
            parts.append(partIndexPart)
        pos = end
    if pos < len(strSearch):
        end = len(strSearch)
        partScanPart = (ScanPart, trimScanPart(strSearch[pos:end]))
        parts.append(partScanPart)
    return parts

def createFolderFilter(strFilter):
    strFilter = strFilter.strip().lower()
    filterParts = []
    if not strFilter:
        return filter
    for item in (item.strip() for item in strFilter.split(",")):
        if item:
            if item.startswith("-"):
                filterParts.append((item[1:], False))
            else:
                filterParts.append((item, True))
    return filterParts

# Transform the comma separated list so that every extension looks like ".ext".
# Also remove '*' to support *.ext
def createExtensionFilter(strFilter):
    strFilter = strFilter.strip().lower()
    filterParts = []
    if not strFilter:
        return filterParts
    for item in (item.strip().replace("*", "") for item in strFilter.split(",")):
        if item:
            bPositiveFilter = True
            if item.startswith("-"):
                item = item[1:]
                bPositiveFilter = False
            if not item.startswith("."):
                item = "." + item
            if item == ".": # os.path.splitext returns an empty string if there is no extension
                item = ""
            filterParts.append((item, bPositiveFilter))
    return filterParts

class TestSearchParts(unittest.TestCase):
    def test(self):
        self.assertEqual(splitSearchParts(""), [])
        self.assertEqual(splitSearchParts("hallo"), [(IndexPart, "hallo")])
        self.assertEqual(splitSearchParts("hallo welt"), [(IndexPart, "hallo"), (ScanPart, ""), (IndexPart, "welt")])
        self.assertEqual(splitSearchParts("hallo      welt"), [(IndexPart, "hallo"), (ScanPart, ""), (IndexPart, "welt")])
        self.assertEqual(splitSearchParts("\"hallo < welt\""), [(ScanPart, '"'), (IndexPart, "hallo"), (ScanPart, "<"), (IndexPart, "welt"), (ScanPart, '"')])
        self.assertEqual(splitSearchParts("hallo* we*lt"), [(IndexPart, "hallo*"), (ScanPart, ""), (IndexPart, "we*lt")])
        self.assertEqual(splitSearchParts("linux *"), [(IndexPart, "linux"), (ScanPart, "*")])
        self.assertEqual(splitSearchParts("#if a"), [(IndexPart, "#if"), (ScanPart, ""), (IndexPart, "a")])
        self.assertEqual(splitSearchParts("a **2"), [(IndexPart, "a"), (ScanPart, ""), (MatchWordsPart, 2)])
        self.assertEqual(splitSearchParts("a ***"), [(IndexPart, "a"), (ScanPart, "***")])
        self.assertEqual(splitSearchParts("a <!abc!>"), [(IndexPart, "a"), (ScanPart, ""), (RegExPart, "abc")])

class QueryError(RuntimeError):
    pass

class Query(metaclass = abc.ABCMeta):
    def __init__(self, strSearch, strFolderFilter="", strExtensionFilter="", bCaseSensitive=False):
        self.folderFilter = createFolderFilter(strFolderFilter)
        self.extensionFilter = createExtensionFilter(strExtensionFilter)
        self.hasFilters = False
        if self.folderFilter or self.extensionFilter:
            self.hasFilters = True

        self.bCaseSensitive = bCaseSensitive
        self.reFlags = 0
        if not self.bCaseSensitive:
            self.reFlags = re.IGNORECASE
        self.parts = splitSearchParts(strSearch)
        # Check that the search contains at least one indexed part.
        if not self.hasPartTypeEqualTo(IndexPart):
            raise QueryError("Sorry, you can't search for that.")

    # All indexed parts
    def indexedPartsLower(self):
        return (part[1].lower() for part in self.parts if part[0] == IndexPart)

    def requiresRegex(self):
        """True if the query relies on a regex. That is e.g. true if you search for more than one keyword or case sensitive."""
        if self.partCount() > 1 and self.hasPartTypeUnequalTo(IndexPart):
            return True
        if self.bCaseSensitive:
            return True
        return False

    def hasPartTypeEqualTo(self, partType):
        for part in self.parts:
            if part[0] == partType:
                return True
        return False

    def hasPartTypeUnequalTo(self, partType):
        for part in self.parts:
            if part[0] != partType:
                return True
        return False

    def partCount(self):
        return len(self.parts)

    # Yields all matches in str. Each match is returned as the touple (position,length)
    def matches(self, data):
        reExpr = self.regExForMatches()
        if not reExpr:
            return
        cur = 0
        while True:
            result = reExpr.search(data, cur)
            if result:
                startPos, endPos = result.span()
                yield (startPos, endPos-startPos)
                cur = endPos
            else:
                return

    def matchFolderAndExtensionFilter(self, strFileName):
        if not self.hasFilters:
            return True
        strFileName = strFileName.lower()
        bHasPositiveFilter = False
        bPositiveFilterMatches = False
        for folder, bPositive in self.folderFilter:
            if bPositive:
                bHasPositiveFilter = True
            if strFileName.find(folder) != -1:
                if not bPositive:
                    return False
                else:
                    bPositiveFilterMatches = True
        if bHasPositiveFilter and not bPositiveFilterMatches:
            return False

        ext = os.path.splitext(strFileName)[1]
        bHasPositiveFilter = False
        bPositiveFilterMatches = False
        for extension, bPositive in self.extensionFilter:
            if bPositive:
                bHasPositiveFilter = True
            if ext == extension:
                if not bPositive:
                    return False
                else:
                    bPositiveFilterMatches = True
        if bHasPositiveFilter and not bPositiveFilterMatches:
            return False

        return True

    @abc.abstractmethod
    def regExForMatches(self):
        pass

class SearchQuery(Query):
    # Returns a list of regular expressions which match all found occurances in a document
    def regExForMatches(self):
        regParts = []
        for t, s in self.parts:
            if IndexPart == t:
                regParts.append(kwExpr(s))
            elif ScanPart == t:
                # Regex special characters [\^$.|?*+()
                for c in s:
                    if c in r"[\^$.|?*+()":
                        regParts.append("\\" + c)
                    else:
                        regParts.append(c)
            elif MatchWordsPart == t:
                regParts.append(r"(?:(?:\s+)?\S+){1,%u}?" % s)
            elif RegExPart == t:
                regParts.append("("+s+")")
        reExpr = re.compile(r"\s*".join(regParts), self.reFlags)
        return reExpr

class FindAllQuery(Query):
    def __init__(self, strSearch, strFolderFilter="", strExtensionFilter="", bCaseSensitive=False):
        super().__init__(strSearch, strFolderFilter, strExtensionFilter, bCaseSensitive)

        parts = []
        for i, s in self.parts:
            if i != IndexPart:
                if s != "":
                    raise QueryError("The element '%s' of the search string is not indexed! Remove it or search for the full phrase." % (s,))
            else:
                parts.append((i, s))

        self.parts = parts

    # Returns a list of regular expressions which match all found occurances in a document
    def regExForMatches(self):
        expr = "|".join("(" + kwExpr(kw) + ")" for kw in (part[1] for part in self.parts))
        reExpr = re.compile(expr, self.reFlags)
        return reExpr

class TestQuery(unittest.TestCase):
    def test(self):
        self.assertRaises(RuntimeError, SearchQuery, "!")
        self.assertRaises(RuntimeError, FindAllQuery, "a < b", "", "", False) # cannot search for < if we are not searching for full phrase
        s1 = SearchQuery("a < b")
        self.assertEqual(s1.parts, [(IndexPart, "a"), (ScanPart, "<"), (IndexPart, "b")])
        self.assertEqual(s1.bCaseSensitive, False)
        s2 = FindAllQuery("a b", "", "", True)
        self.assertEqual(s2.parts, [(IndexPart, "a"), (IndexPart, "b")])
        self.assertEqual(s2.bCaseSensitive, True)
        s3 = SearchQuery("linux *")
        self.assertEqual(s3.regExForMatches().pattern, "\\blinux\\b\\s*\\*")
        s4 = SearchQuery("createNode ( CComVariant")
        self.assertEqual(s4.regExForMatches().pattern, "\\bcreateNode\\b\\s*\\(\\s*\\bCComVariant\\b")

class ReportAction:
    def __init__(self, name):
        self.name = name
        self.data = []
        self.startTime = None
        self.duration = None

    def addData(self, text, *args):
        self.data.append(text % args)

    def __enter__(self):
        self.startTime = time.clock()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = time.clock() - self.startTime
        return False

    def __str__(self):
        s = self.name
        if self.duration:
            s += " (%3.2f s)" % (self.duration, )
        for d in self.data:
            s += "\n"
            s += d
        return s

class PerformanceReport:
    def __init__(self):
        self.actions = []
        self.current = None

    def newAction(self, name):
        self.current = ReportAction(name)
        self.actions.append(self.current)
        return self.current

    def __str__(self):
        s = ""
        for a in self.actions:
            if s:
                s += "\n\n"
            s += str(a)
        return s

class Keyword:
    def __init__(self, identifier, name):
        self.id = identifier
        self.name = name

    def __repr__(self):
        return "%s (%u)" % (self.name, self.id)

    def __eq__(self, other):
        return self.id == other.id and self.name == other.name

class FullTextIndex (IndexDatabase):
    # commonKeywordMap maps  keywords to numbers. A lower number means a worse keyword. Bad keywords are very common like "h" in cpp files.
    def search(self, query, perfReport=None, commonKeywordMap=None, manualIntersect=True, cancelEvent=None):
        commonKeywordMap = commonKeywordMap or {}
        try:
            return self.__search(query, perfReport, commonKeywordMap, manualIntersect, cancelEvent)
        except sqlite3.OperationalError as e:
            if str(e) == "interrupted":
                return []
            raise

    def __search(self, query, perfReport, commonKeywordMap, manualIntersect, cancelEvent):
        if not isinstance(query, Query):
            raise RuntimeError("query must be a Query derived object")

        query.parts = query.parts or []

        perfReport = perfReport or PerformanceReport()

        q = self.conn.cursor()

        # The result is a list of lists of Keyword objects
        kwList = []
        with perfReport.newAction("Finding keywords") as action:
            kwList = self.__getKeywords(q, query.indexedPartsLower(), reportAction=action)
            if not kwList:
                return []

        goodKeywords, badKeywords = self.__qualifyKeywords(kwList, commonKeywordMap)

        with perfReport.newAction("Finding documents") as action:
            if not manualIntersect:
                result = self.__findDocsByKeywords(q, goodKeywords, badKeywords)
            else:
                result = self.__findDocsByKeywordsManualIntersect(q, goodKeywords, badKeywords, action)
            action.addData("%u matches", safeLen(result))
            if not result:
                return []

        if query.requiresRegex():
            with perfReport.newAction("Filtering results"):
                return self.__filterDocsBySearchPhrase((r[0] for r in result), query, cancelEvent)
        else:
            with perfReport.newAction("Returning results"):
                if not query.folderFilter and not query.extensionFilter:
                    return [r[0] for r in result]
                else:
                    return [r[0] for r in result if query.matchFolderAndExtensionFilter(r[0])]

    def __findDocsByKeywords(self, q, goodKeywords, badKeywords):
        kwList = goodKeywords + badKeywords
        stmt = ""
        for keywords in kwList:
            if stmt:
                stmt += " INTERSECT "
            inString = ",".join((str(keyword.id) for keyword in keywords))
            stmt += "SELECT DISTINCT fullpath FROM kw2doc,documents WHERE docID=id AND kwID IN (%s)" % (inString, )
        q.execute(stmt + " ORDER BY fullpath")
        return q.fetchall()

    def __findDocsByKeywordsManualIntersect(self, q, goodKeywords, badKeywords, reportAction):
        result = None
        allKeywords = [(True, keywords) for keywords in goodKeywords] + [(False, keywords) for keywords in badKeywords]
        for isGood, keywords in allKeywords:
            # Stop if all good keywords have been used and the result is stripped down to less than 100 files
            if not isGood:
                kwNames = ",".join((keyword.name for keyword in keywords))
                if not result is None and len(result) < 100:
                    reportAction.addData("Search stopped with common keyword '%s'" % (kwNames, ))
                    break
                else:
                    if not result is None:
                        reportAction.addData("Common keyword '%s' used because %u matches are too much" % (kwNames, len(result)))
                    else:
                        reportAction.addData("Common keyword '%s' used as first keyword" % (kwNames, ))
            inString = ",".join((str(keyword.id) for keyword in keywords))
            stmt = "SELECT DISTINCT fullpath FROM kw2doc,documents WHERE docID=id AND kwID IN (%s) ORDER BY fullpath" % (inString, )
            q.execute(stmt)
            kwMatches = q.fetchall()
            if result is None:
                result = kwMatches
            else:
                result = intersectSortedLists(result, kwMatches)
            if not result:
                return []
        return result

    def __filterDocsBySearchPhrase(self, results, query, cancelEvent=None):
        finalResults = []
        reExpr = query.regExForMatches()
        bHasFilters = query.folderFilter or query.extensionFilter
        for fullpath in results:
            if bHasFilters:
                if not query.matchFolderAndExtensionFilter(fullpath):
                    continue
            try:
                with fopen(fullpath) as inputFile:
                    if reExpr.search(inputFile.read()):
                        finalResults.append(fullpath)
            except:
                pass

            if cancelEvent and cancelEvent.is_set():
                return []

        return finalResults

    # Receives a list of lists of Keywords and returns as two lists.
    # The first list contains the good keywords in input order. These are keywords which are not found if commonKeywordMap.
    # The second list contains the bad keywords which were found in commonKeywordMap ordered from the less worst to the worst.
    def __qualifyKeywords(self, kwList, commonKeywordMap):
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
    def __getKeywords(self, q, keywordList, reportAction=None):
        keys = []
        for kw in keywordList:
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
                    reportAction.addData("String '%s' was not found", kw)
                return []
            if reportAction:
                reportAction.addData("String '%s' results in %u keyword matches", kw, len(result))
            keys.append([Keyword(r[0], r[1]) for r in result])
        return keys



