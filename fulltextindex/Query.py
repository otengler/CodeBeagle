# -*- coding: utf-8 -*-
"""
Copyright (C) 2020 Oliver Tengler

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
import time
import re
import unittest
from enum import Enum
from .IStringMatcher import IStringMatcher, MatchPosition
from typing import List, Tuple, Iterator, Iterable, Pattern, Any, Sized, Optional, Literal, Dict, Callable
from .CommentRule import CommentRule
from .CommentDetection import isInsideTextSpan, analyzeText

reQueryToken = re.compile(r"[\w#*]+|<!.*?!>")
reMatchWords = re.compile(r"(\*\*)([0-9]+)")
reMatchRegEx = re.compile(r"<!(.*)!>")

regexEscape = r"[\^$.|?*+()"

SearchResult = List[str] # List of matching files

# Return tokens which are in the index
def getTokens(text: str) -> List[Tuple[int,int]]:
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

def trimScanPart(s: str) -> str:
    return s.replace(" ", "")

class TokenType (Enum):
    IndexPart = 1
    ScanPart = 2
    MatchWordsPart = 3
    RegExPart = 4

SearchPartList = List[Tuple[TokenType,str]]

def splitSearchParts(strSearch: str) -> SearchPartList:
    tokens = getTokens(strSearch)
    parts: SearchPartList = []
    pos = 0
    for begin, end in tokens:
        if begin > pos:
            partScanPart = (TokenType.ScanPart, trimScanPart(strSearch[pos:begin]))
            parts.append(partScanPart)
        token = strSearch[begin:end]
        result = reMatchWords.match(token) # special handling for **X syntax. It means to search for X unknown words
        if result and int(result.group(2)) > 0:
            matchWordsPart = (TokenType.MatchWordsPart, result.group(2))
            parts.append(matchWordsPart)
        elif token.startswith("<!"):
            r =  reMatchRegEx.match(token)
            if r:
                regExPart = (TokenType.RegExPart, r.group(1))
                parts.append(regExPart)
        else:
            partIndexPart = (TokenType.IndexPart, token)
            parts.append(partIndexPart)
        pos = end
    if pos < len(strSearch):
        end = len(strSearch)
        partScanPart = (TokenType.ScanPart, trimScanPart(strSearch[pos:end]))
        parts.append(partScanPart)
    return parts

class TestSearchParts(unittest.TestCase):
    def test(self) -> None:
        self.assertEqual(splitSearchParts(""), [])
        self.assertEqual(splitSearchParts("hallo"), [(TokenType.IndexPart, "hallo")])
        self.assertEqual(splitSearchParts("hallo welt"), [(TokenType.IndexPart, "hallo"), (TokenType.ScanPart, ""), (TokenType.IndexPart, "welt")])
        self.assertEqual(splitSearchParts("hallo      welt"), [(TokenType.IndexPart, "hallo"), (TokenType.ScanPart, ""), (TokenType.IndexPart, "welt")])
        self.assertEqual(splitSearchParts("\"hallo < welt\""), [(TokenType.ScanPart, '"'), (TokenType.IndexPart, "hallo"), (TokenType.ScanPart, "<"), (TokenType.IndexPart, "welt"), (TokenType.ScanPart, '"')])
        self.assertEqual(splitSearchParts("hallo* we*lt"), [(TokenType.IndexPart, "hallo*"), (TokenType.ScanPart, ""), (TokenType.IndexPart, "we*lt")])
        self.assertEqual(splitSearchParts("linux *"), [(TokenType.IndexPart, "linux"), (TokenType.ScanPart, "*")])
        self.assertEqual(splitSearchParts("#if a"), [(TokenType.IndexPart, "#if"), (TokenType.ScanPart, ""), (TokenType.IndexPart, "a")])
        self.assertEqual(splitSearchParts("a **2"), [(TokenType.IndexPart, "a"), (TokenType.ScanPart, ""), (TokenType.MatchWordsPart, "2")])
        self.assertEqual(splitSearchParts("a ***"), [(TokenType.IndexPart, "a"), (TokenType.ScanPart, "***")])
        self.assertEqual(splitSearchParts("a <!abc!>"), [(TokenType.IndexPart, "a"), (TokenType.ScanPart, ""), (TokenType.RegExPart, "abc")])

def hasFileNameWildcard(name: str) -> bool:
    if name.find("*") != -1:
        return True
    if name.find("?") != -1:
        return True
    return False

def createPathMatchPattern(pathMatch: str, fullMatch: bool) -> str:
    pattern = ""
    for c in pathMatch:
        if c == '*':
            pattern += ".*"
        elif c == '?':
            pattern += "."
        elif c in regexEscape:
            pattern += f"\\{c}"
        else:
            pattern += c
    if fullMatch:
        pattern += "$"
    return pattern

class IncludeExcludePattern:
    def __init__(self, filterParts: List[Tuple[str,bool]], matchAll: bool = False) -> None:
        self.includeParts = []
        self.excludeParts = []
        self.positivePattern: Optional[Pattern] = None
        self.negativePattern: Optional[Pattern] = None
        self.matchAll = matchAll # If true all characters from the text must be used by the pattern

        if filterParts:
            for part,positive in filterParts:
                if positive:
                    self.includeParts.append(part)
                else:
                    self.excludeParts.append(part)

        if self.includeParts:
            positiveFilter = [createPathMatchPattern(part, matchAll) for part in self.includeParts]
            self.positivePattern = re.compile("|".join(positiveFilter), re.IGNORECASE)

        if self.excludeParts:
            negativeFilter = [createPathMatchPattern(part, matchAll) for part in self.excludeParts]
            self.negativePattern = re.compile("|".join(negativeFilter), re.IGNORECASE)

    def isEmpty(self) -> bool:
        return not self.positivePattern and not self.negativePattern

    def match(self, text: str) -> bool:
        if self.negativePattern:
            if self.negativePattern.pattern: # Empty pattern matches always but should only match empty string
                if not self.matchAll:
                    if self.negativePattern.search(text):
                        return False
                elif m:= self.negativePattern.match(text):
                    return False
            elif text:
                return False
        if self.positivePattern:
            if self.positivePattern.pattern: # Empty pattern matches always but should only match empty string
                if not self.matchAll:
                    return bool(self.positivePattern.search(text))
                m = self.positivePattern.match(text)
                return bool(m)
            return not bool(text)
        return True

class TestIncludeExcludePattern(unittest.TestCase):
    def test(self) -> None:
        ie = IncludeExcludePattern([("test*", True), ("black*", False) ])
        self.assertTrue(ie.match("test123"))
        self.assertTrue(ie.match("test_abc.txt"))
        self.assertFalse(ie.match("test_blacklist.txt"))

# Transform the comma separated list so that every extension looks like ".ext".
# Also remove '*' to support *.ext
def createExtensionFilter(strFilter: str) -> List[Tuple[str,bool]]:
    filterParts: List[Tuple[str,bool]] = []
    if not strFilter:
        return filterParts
    for item in (item.strip() for item in strFilter.lower().split(",")):
        if item:
            if item.startswith("*."):
                item = item[2:]    
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

def createFolderFilter(strFilter: str) -> List[Tuple[str,bool]]:
    strFilter = strFilter.strip().lower()
    filterParts: List[Tuple[str,bool]] = []
    if not strFilter:
        return filterParts
    for item in (item.strip() for item in strFilter.split(",")):
        if item:
            if item.startswith("-"):
                filterParts.append((item[1:], False))
            else:
                filterParts.append((item, True))
    return filterParts

class QueryError(RuntimeError):
    pass

CommentRuleFetcher = Callable[[str], Optional[CommentRule]]

class QueryParams:
    def __init__(self, strSearch: str, strFolderFilter: str = "", strExtensionFilter: str = "", bCaseSensitive: bool = False, bExcludeComments: bool = False, commentRuleFetcher: Optional[CommentRuleFetcher] = None) -> None:
        self.strSearch = strSearch
        self.strFolderFilter = strFolderFilter
        self.strExtensionFilter = strExtensionFilter
        self.bCaseSensitive = bCaseSensitive
        self.bExcludeComments = bExcludeComments
        self.commentRuleFetcher = commentRuleFetcher

class Query (IStringMatcher):
    def __init__(self, params: QueryParams) -> None:
        self.search = params.strSearch
        self.folderFilterString = params.strFolderFilter
        self.extensionFilterString = params.strExtensionFilter
        self.folderFilter = createFolderFilter(params.strFolderFilter)
        self.extensionFilter = createExtensionFilter(params.strExtensionFilter)
        self.__folderFilterExpression = IncludeExcludePattern(self.folderFilter)
        self.__extensionFilterExpression = IncludeExcludePattern(self.extensionFilter, matchAll=True)
        self.__hasFilters = False
        if self.folderFilter or self.extensionFilter:
            self.__hasFilters = True

        self.bCaseSensitive = params.bCaseSensitive
        self.bExcludeComments = params.bExcludeComments
        self.commentRuleFetcher = params.commentRuleFetcher

    def getFolderFilterExpression(self) -> IncludeExcludePattern:
        return self.__folderFilterExpression
    def getExtensionFilterExpression(self) -> IncludeExcludePattern:
        return self.__extensionFilterExpression

    def matchFolderAndExtensionFilter(self, strFileName: str, runFolderFilter: bool=True, runExtensionFilter: bool=True, ext: Optional[str]=None) -> bool:
        if not self.__hasFilters:
            return True

        if runFolderFilter:
            if not self.__folderFilterExpression.match(strFileName):
                return False

        if runExtensionFilter:
            if ext is None:
                ext = os.path.splitext(strFileName)[1]
            if not self.__extensionFilterExpression.match(ext):
                return False

        return True

# Returns the regular expression which matches a keyword
def kwExpr(kw: str) -> str:
    # If the keyword starts with '#' it is not matched if we search for word boundaries (\\b)
    if not kw.startswith("#"):
        return r"\b" + kw.replace("*", r"\w*") + r"\b"
    return kw.replace("*", r"\w*")

class ContentQuery(Query):
    def __init__(self, params: QueryParams) -> None:
        super().__init__(params)

        self.reFlags = 0
        if not self.bCaseSensitive:
            self.reFlags = re.IGNORECASE
        self.parts = splitSearchParts(self.search)
        # Check that the search contains at least one indexed part.
        if not self.hasPartTypeEqualTo(TokenType.IndexPart):
            raise QueryError("Sorry, you can't search for that.")

    # Returns a list of regular expressions which match all found occurances in a document
    def regExForMatches(self) -> Pattern:
        regParts = []
        for t, s in self.parts:
            if TokenType.IndexPart == t:
                regParts.append(kwExpr(s))
            elif TokenType.ScanPart == t:
                # Regex special characters [\^$.|?*+()
                for c in s:
                    if c in regexEscape:
                        regParts.append("\\" + c)
                    else:
                        regParts.append(c)
            elif TokenType.MatchWordsPart == t:
                wordCount = int(s)
                if wordCount:
                    part = r"\S+"
                    if wordCount > 1:
                        part += r"(?:\s+\S+){0,%u}" % (wordCount-1)
                    regParts.append(part)
            elif TokenType.RegExPart == t:
                regParts.append("(?:"+s+")")
        reExpr = re.compile(r"\s*".join(regParts), self.reFlags)
        return reExpr

    # Yields all matches in str. Each match is returned as the touple (position,length)
    def matches(self, data: str, filename: str = "") -> Iterable[MatchPosition]:
        reExpr = self.regExForMatches()
        if not reExpr:
            return

        # Determine if we should filter comments
        commentRule: Optional[CommentRule] = None
        if self.commentRuleFetcher:
            commentRule = self.commentRuleFetcher(filename)
        
        commentRanges = None
        if self.bExcludeComments and commentRule is not None and filename:
            # Find all comments in the data
            _, commentRanges = analyzeText(data,
                commentRule.lineComment,
                commentRule.multiCommentStart,
                commentRule.multiCommentStop,
                commentRule.hasTripleQuotes)

        cur = 0
        while True:
            result = reExpr.search(data, cur)
            if result:
                startPos, endPos = result.span()
                # Check if match is inside a comment
                if commentRanges:
                    # Check if the start of the match is inside a comment
                    if not isInsideTextSpan(startPos, commentRanges):
                        yield MatchPosition(startPos, endPos-startPos)
                else:
                    yield MatchPosition(startPos, endPos-startPos)

                cur = endPos
            else:
                return

    # All indexed parts
    def indexedPartsLower(self) -> Iterator[str]:
        return (part[1].lower() for part in self.parts if part[0] == TokenType.IndexPart)

    def requiresReadingFile(self) -> bool:
        """True if the query relies on a regex. That is e.g. true if you search for more than one keyword or case sensitive."""
        if self.partCount() > 1 and self.hasPartTypeUnequalTo(TokenType.IndexPart):
            return True
        if self.bCaseSensitive or self.bExcludeComments:
            return True
        return False

    def hasPartTypeEqualTo(self, partType: TokenType) -> bool:
        for part in self.parts:
            if part[0] == partType:
                return True
        return False

    def hasPartTypeUnequalTo(self, partType: TokenType) -> bool:
        for part in self.parts:
            if part[0] != partType:
                return True
        return False

    def partCount(self) -> int:
        return len(self.parts)

class TestQuery(unittest.TestCase):
    def test(self) -> None:
        self.assertRaises(RuntimeError, ContentQuery, QueryParams("!"))
        s1 = ContentQuery(QueryParams("a < b"))
        self.assertEqual(s1.parts, [(TokenType.IndexPart, "a"), (TokenType.ScanPart, "<"), (TokenType.IndexPart, "b")])
        self.assertEqual(s1.bCaseSensitive, False)
        s3 = ContentQuery(QueryParams("linux *"))
        self.assertEqual(s3.regExForMatches().pattern, r"\blinux\b\s*\*")
        s4 = ContentQuery(QueryParams("createNode ( CComVariant"))
        self.assertEqual(s4.regExForMatches().pattern, r"\bcreateNode\b\s*\(\s*\bCComVariant\b")
        s5 = ContentQuery(QueryParams("unknown **4"))
        self.assertEqual(s5.regExForMatches().pattern, r"\bunknown\b\s*\S+(?:\s+\S+){0,3}")
        s6 = ContentQuery(QueryParams("regex <!abc!>"))
        self.assertEqual(s6.regExForMatches().pattern, r"\bregex\b\s*(?:abc)")

class FileQuery(Query):
    def __init__(self, params: QueryParams) -> None:
        # If the search term contains a "." we use the part after that as the extension. But only if the extension filter is
        # not specified as that takes precedance.
        if params.strSearch.find('.') != -1 and not params.strExtensionFilter:
            search, extensionFilter = os.path.splitext(params.strSearch)
            if extensionFilter == ".*":
                extensionFilter = ""
            params = QueryParams(search, params.strFolderFilter, extensionFilter, params.bCaseSensitive)
        super().__init__(params)

    def matches(self, data: str, filename: str = "") -> Iterable[MatchPosition]:
        return []

class ReportAction:
    def __init__(self, name: str) -> None:
        self.name = name
        self.data: List[str] = []
        self.startTime: float = 0
        self.duration: float = 0

    def addData(self, text: str, *args: Any) -> None:
        self.data.append(text % args)

    def __enter__(self) -> 'ReportAction':
        self.startTime = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Literal[False]:
        self.duration = time.perf_counter() - self.startTime
        return False

    def __str__(self) -> str:
        s = self.name
        if self.duration:
            s += " (%3.2f s)" % (self.duration, )
        for d in self.data:
            s += "\n"
            s += d
        return s

class PerformanceReport:
    def __init__(self) -> None:
        self.actions: List[ReportAction] = []
        self.current: Optional[ReportAction] = None

    def newAction(self, name: str) -> ReportAction:
        self.current = ReportAction(name)
        self.actions.append(self.current)
        return self.current

    def __str__(self) -> str:
        s = ""
        for a in self.actions:
            if s:
                s += "\n\n"
            s += str(a)
        return s

def safeLen(obj: Sized) -> int:
    try:
        return len(obj)
    except:
        return 0

