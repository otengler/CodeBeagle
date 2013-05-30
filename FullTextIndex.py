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
import logging
from FileTools import fopen

reTokenize = re.compile(r"[\w#]+")
reQueryToken = re.compile(r"[\w#*]+")
reMatchWords = re.compile(r"(\*\*)([0-9]+)")

strSetup="""
CREATE TABLE IF NOT EXISTS keywords(
  id INTEGER PRIMARY KEY,
  keyword TEXT UNIQUE  
);
CREATE INDEX IF NOT EXISTS i_keywords_keyword ON keywords (keyword);

CREATE TABLE IF NOT EXISTS documents(
  id INTEGER PRIMARY KEY,
  timestamp INTEGER,
  fullpath TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS documentInIndex(
  docID INTEGER UNIQUE,
  indexID INTEGER
);
CREATE INDEX IF NOT EXISTS i_documentInIndex_indexID ON documentInIndex (indexID);

CREATE TABLE IF NOT EXISTS kw2doc(
  kwID INTEGER,
  docID INTEGER,
  UNIQUE (kwID,docID)
);
CREATE INDEX IF NOT EXISTS i_kw2doc_kwID ON kw2doc (kwID);
CREATE INDEX IF NOT EXISTS i_kw2doc_docID ON kw2doc (docID);

CREATE TABLE IF NOT EXISTS indexInfo(
  id INTEGER PRIMARY KEY,
  timestamp INTEGER
);
"""

IndexPart = 1
ScanPart= 2
MatchWordsPart = 3

def genFind (filepat, strRootDir,  dirExcludes=[]):
    dirExcludes = [dir.lower() for dir in dirExcludes]
    for path, dirlist, filelist in os.walk (strRootDir):
        if dirExcludes:
            pathLower = path.lower()
            found=False
            for exclude in dirExcludes:
                if pathLower.find(exclude) != -1:
                    found=True
                    break
            if found:
                continue
        for name in (name for name in filelist if os.path.splitext(name)[1].lower() in filepat):
            yield os.path.join(path,name) 
     
def genTokens (file):
        for token in reTokenize.findall(file.read()):
            yield token
            
def safeLen (obj):
    try:
        return len(obj)
    except:
        return 0
        
def intersectSortedLists(l1,l2):
    l = 0
    r = 0   
    l3 = []
    try:
        itemL = l1[l]
        itemR = l2[r]
        while (True):
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
def getTokens (str):
    parts = []
    pos=0
    while True:
        result = reQueryToken.search(str,pos)
        if result:
            begin,pos = result.span()
            if result.group(0).replace("*", "") != "": # skip parts with asterisks only, they are not in the index
                parts.append((begin, pos))
        else:
            break
    return parts

# Returns the regular expression which matches a keyword
def kwExpr (kw):
    # If the keyword starts with '#' it is not matched if we search for word boundaries (\\b)
    if not kw.startswith("#"): 
        return r"\b" + kw.replace("*",  r"\w*") + r"\b"
    else:
        return kw.replace("*",  r"\w*")

def trimScanPart (s):
    return s.replace(" ", "")

def splitSearchParts (str):
    tokens = getTokens  (str)
    parts = []
    pos=0
    for begin, end in tokens:
        if begin > pos:
            partScanPart = (ScanPart, trimScanPart(str[pos:begin]))
            parts.append(partScanPart)
        token = str[begin:end]
        result = reMatchWords.match(token) # special handling for **X syntax. It means to search for X unknown words
        if result and int(result.group(2))>0:
            matchWordsPart = (MatchWordsPart, int(result.group(2)))
            parts.append(matchWordsPart)
        else:
            partIndexPart = (IndexPart, token)
            parts.append(partIndexPart)
        pos = end
    if pos < len(str):
        end = len(str)
        partScanPart = (ScanPart, trimScanPart(str[pos:end]))
        parts.append(partScanPart)
    return parts
    
def createFolderFilter (strFilter):
    strFilter = strFilter.strip().lower()
    filter = []
    if not strFilter:
        return filter
    for item in (item.strip() for item in strFilter.split(",")):
        if item.startswith("-"):
            filter.append((item[1:], False))
        else:
            filter.append((item, True))
    return filter

# Transform the comma seperated list so that every extension looks like ".ext".
# Also remove '*' to support *.ext
def createExtensionFilter (strFilter):
    strFilter = strFilter.strip().lower()
    filter = []
    if not strFilter:
        return filter
    for item in strFilter.split(","):
        item = item.strip().replace("*", "")
        bPositiveFilter = True
        if item.startswith("-"):
            item = item[1:]
            bPositiveFilter = False
        if not item.startswith("."):
            item = "." + item
        filter.append((item, bPositiveFilter))
    return filter

class TestSearchParts(unittest.TestCase):
    def test(self):
        self.assertEqual (splitSearchParts(""), [])
        self.assertEqual (splitSearchParts("hallo"), [(IndexPart,"hallo")])
        self.assertEqual (splitSearchParts("hallo welt"), [(IndexPart,"hallo"),(ScanPart,""),(IndexPart,"welt")])
        self.assertEqual (splitSearchParts("hallo      welt"), [(IndexPart,"hallo"),(ScanPart,""),(IndexPart,"welt")])
        self.assertEqual (splitSearchParts("\"hallo < welt\""), [(ScanPart,'"'),(IndexPart,"hallo"),(ScanPart,"<"),(IndexPart,"welt"),(ScanPart,'"')])
        self.assertEqual (splitSearchParts("hallo* we*lt"), [(IndexPart,"hallo*"),(ScanPart,""),(IndexPart,"we*lt")])
        self.assertEqual (splitSearchParts("linux *"), [(IndexPart,"linux"),(ScanPart,"*")])
        self.assertEqual (splitSearchParts("#if a"), [(IndexPart,"#if"),(ScanPart,""),(IndexPart,"a")])
        self.assertEqual (splitSearchParts("a **2"), [(IndexPart,"a"),(ScanPart,""),(MatchWordsPart, 2)])
        self.assertEqual (splitSearchParts("a ***"), [(IndexPart,"a"),(ScanPart,"***")])

class QueryError (RuntimeError):
    def __init__(self, strReason):
        super(QueryError, self).__init__(strReason)

class Query (metaclass = abc.ABCMeta):
    def __init__(self,  strSearch, strFolderFilter="",  strExtensionFilter="",  bCaseSensitive=False):
        self.folderFilter = createFolderFilter(strFolderFilter)
        self.extensionFilter = createExtensionFilter(strExtensionFilter)
        self.hasFilters = False
        if self.folderFilter or self.extensionFilter:
            self.hasFilters = True
            
        self.bCaseSensitive = bCaseSensitive
        self.reFlags = 0
        if not self.bCaseSensitive:
            self.reFlags = re.IGNORECASE
        self.parts = splitSearchParts (strSearch)
        # Check that the search contains at least one indexed part. 
        if not self.hasPartTypeEqualTo(IndexPart):
            raise QueryError("Sorry, you can't search for that.")
    
    # All indexed parts
    def indexedPartsLower(self):
        return (part[1].lower() for part in self.parts if part[0] == IndexPart)
    
    def hasPartTypeEqualTo (self,  partType):
        for part in self.parts:
            if part[0] == partType:
                return True
        return False
        
    def hasPartTypeUnequalTo (self,  partType):
        for part in self.parts:
            if part[0] != partType:
                return True
        return False
        
    def partCount (self):
        return len(self.parts)
        
    # Yields all matches in str. Each match is returned as the touple (position,length)
    def matches (self,  str):
        reExpr = self.regExForMatches ()
        if not reExpr:
            return
        cur = 0
        while True:
            result = reExpr.search(str, cur)
            if result:
                startPos, endPos = result.span()
                yield (startPos,  endPos-startPos)
                cur = endPos
            else:
                return
        
    def matchFolderAndExtensionFilter (self, strFileName):
        if not self.hasFilters:
            return True
        strFileName = strFileName.lower()
        bHasPositiveFilter = False
        bPositiveFilterMatches = False
        for filter, bPositive in self.folderFilter:
            if bPositive:
                bHasPositiveFilter = True
            if strFileName.find(filter) != -1:
                if not bPositive:
                    return False
                else:
                    bPositiveFilterMatches = True
        if bHasPositiveFilter and not bPositiveFilterMatches:
            return False

        ext = os.path.splitext(strFileName)[1]
        bHasPositiveFilter = False
        bPositiveFilterMatches = False
        for filter, bPositive in self.extensionFilter:
            if bPositive:
                bHasPositiveFilter = True
            if ext == filter:
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
        
class SearchQuery (Query):
    def __init__(self,  strSearch, strFolderFilter="",  strExtensionFilter="",  bCaseSensitive=False):
        super(SearchQuery, self).__init__(strSearch, strFolderFilter,  strExtensionFilter,  bCaseSensitive)
        
    # Returns a list of regular expressions which match all found occurances in a document
    def regExForMatches (self):
        regParts=[]
        for t, s in self.parts:
            if IndexPart == t:
                regParts.append (kwExpr (s))
            elif ScanPart == t:
                # Regex special characters [\^$.|?*+()
                for c in s:
                    if c in r"[\^$.|?*+()":
                        regParts.append("\\" + c)
                    else:
                        regParts.append(c)
            elif MatchWordsPart:
                regParts.append(r"(?:(?:\s+)?\S+){1,%u}?" % s) 
        reExpr = re.compile(r"\s*".join(regParts), self.reFlags)
        return reExpr
        
class FindAllQuery (Query):
    def __init__(self,  strSearch, strFolderFilter="",  strExtensionFilter="",  bCaseSensitive=False):
        super(FindAllQuery, self).__init__(strSearch, strFolderFilter,  strExtensionFilter,  bCaseSensitive)
    
        parts = []
        for i,s in self.parts:
            if i == ScanPart:
                if s != "":
                    raise QueryError("The element '%s' of the search string is not indexed! Remove it or search for the full phrase." % (s,))
            else:
                parts.append ((i,s))

        self.parts = parts
            
    # Returns a list of regular expressions which match all found occurances in a document
    def regExForMatches (self):
        expr = "|".join("(" + kwExpr(kw) + ")" for kw in (part[1] for part in self.parts))
        reExpr = re.compile(expr, self.reFlags)
        return reExpr

class TestQuery(unittest.TestCase):
    def test(self):
        self.assertRaises(RuntimeError, SearchQuery, "!")
        self.assertRaises(RuntimeError, FindAllQuery, "a < b", "",  "",  False) # cannot search for < if we are not searching for full phrase
        s1 = SearchQuery ("a < b")
        self.assertEqual (s1.parts, [(IndexPart,"a"),(ScanPart,"<"),(IndexPart,"b")])
        self.assertEqual (s1.bCaseSensitive,  False)
        s2 = FindAllQuery ("a b", "",  "",  True)
        self.assertEqual (s2.parts, [(IndexPart,"a"),(IndexPart,"b")])
        self.assertEqual (s2.bCaseSensitive,  True)
        s3 = SearchQuery("linux *")
        self.assertEqual (s3.regExForMatches().pattern, "\\blinux\\b\\s*\\*") 
        s4 = SearchQuery ("createNode ( CComVariant")
        self.assertEqual (s4.regExForMatches().pattern, "\\bcreateNode\\b\\s*\\(\\s*\\bCComVariant\\b") 

class ReportAction:
    def __init__(self, name):
        self.name = name
        self.data = []
        self.startTime = None
        self.duration = None
        
    def addData (self, text,  *args):
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
            s = s + " (%3.2f s)" % (self.duration, )
        for d in self.data:
            s += "\n"
            s += d
        return s

class PerformanceReport:
    def __init__(self):
        self.actions = []
        self.current = None
        
    def newAction (self, name):
        self.current = ReportAction(name)
        self.actions.append(self.current)
        return self.current
        
    def __str__(self):
        s = ""
        for a in self.actions:
            if s:
                s += "\n\n"
            s = s + str(a)
        return s

class UpdateStatistics:
    def __init__(self):
        self.nNew = 0
        self.nUpdated = 0
        self.nUnchanged = 0
    
    def incNew(self):
        self.nNew += 1
    
    def incUpdated(self):
        self.nUpdated += 1
        
    def incUnchanged(self):
        self.nUnchanged += 1
        
    def __str__(self):
        s = "New docs: %u, Updated docs: %u, Unchanged: %u"  % (self.nNew,  self.nUpdated,  self.nUnchanged)
        return s

class Keyword:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        
    def __repr__(self):
        return "%s (%u)" % (self.name, self.id)
        
    def __eq__(self,other):
        return self.id==other.id and self.name==other.name

class FullTextIndex:
    def __init__(self,  strDbLocation):
        self.strDbLocation = strDbLocation
        self.conn = sqlite3.connect(strDbLocation)
        self.__setupDatabase ()
        
    def __del__(self):
        self.conn.close()
       
    def queryStats (self):
        q = self.conn.cursor()
        q.execute("SELECT COUNT(*) FROM documents")
        documents = int(q.fetchone()[0])
        print ("Documents: " + str(documents))
        q.execute("SELECT COUNT(*) FROM documentInIndex")
        documentsInIndex = int(q.fetchone()[0])
        print ("Documents in index: " + str(documentsInIndex))
        q.execute("SELECT COUNT(*) FROM keywords")
        keywords = int(q.fetchone()[0])
        print ("Keywords: " + str(keywords))
        q.execute("SELECT COUNT(*) FROM kw2doc")
        associations = int(q.fetchone()[0])
        print ("Associations: " + str(associations))
        return (documents, documentsInIndex,  keywords, associations)
        
    def interrupt (self):
        self.conn.interrupt()

    # commonKeywordMap maps  keywords to numbers. A lower number means a worse keyword. Bad keywords are very common like "h" in cpp files.
    def search (self, query,  perfReport = None,  commonKeywordMap={},  manualIntersect=True,  cancelEvent=None):
        try:
            return self.__search (query,  perfReport,  commonKeywordMap,  manualIntersect,  cancelEvent)
        except sqlite3.OperationalError as e:
            if str(e) == "interrupted":
                return []
            raise
        
    def __search (self,  query,  perfReport,  commonKeywordMap,  manualIntersect,  cancelEvent):
        if not isinstance (query,Query):
            raise RuntimeError("query must be a Query derived object")
        
        if not query.parts:
            return []
            
        if not perfReport:
            perfReport = PerformanceReport()
        
        q = self.conn.cursor()
        
        # The result is a list of lists of Keyword objects
        kwList = []
        with perfReport.newAction ("Finding keywords") as action:
            kwList = self.__getKeywords (q, query.indexedPartsLower(),  reportAction=action)
            if not kwList:
                return []
        
        goodKeywords, badKeywords = self.__qualifyKeywords (kwList, commonKeywordMap)
        
        with perfReport.newAction ("Finding documents") as action:
            if not manualIntersect:
                result = self.__findDocsByKeywords (q,  goodKeywords,  badKeywords)
            else:
                result = self.__findDocsByKeywordsManualIntersect (q,  goodKeywords,  badKeywords,  action)
            action.addData ("%u matches",  safeLen(result))
            if not result:
                return []
            
        if (query.partCount() > 1 and query.hasPartTypeUnequalTo(IndexPart)) or query.bCaseSensitive:
            with perfReport.newAction("Filtering results"):
                return self.__filterDocsBySearchPhrase ((r[0] for r in result), query, cancelEvent)
        else:
            with perfReport.newAction("Returning results"):
                if not query.folderFilter and not query.extensionFilter:
                    return [r[0] for r in result]
                else:
                    return [r[0] for r in result if query.matchFolderAndExtensionFilter(r[0])]
            
    def __findDocsByKeywords (self,  q,  goodKeywords, badKeywords):
        kwList = goodKeywords + badKeywords
        stmt = ""
        for keywords in kwList:
            if stmt:
                stmt += " INTERSECT "
            inString = ",".join((str(keyword.id) for keyword in keywords))
            stmt += "SELECT DISTINCT fullpath FROM kw2doc,documents WHERE docID=id AND kwID IN (%s)" % (inString, )
        q.execute (stmt + " ORDER BY fullpath")
        return q.fetchall()
        
    def __findDocsByKeywordsManualIntersect (self, q,  goodKeywords, badKeywords,  reportAction):
        result= None
        allKeywords = [(True, keywords) for keywords in goodKeywords] + [(False, keywords) for keywords in badKeywords]
        for isGood, keywords in allKeywords:
            # Stop if all good keywords have been used and the result is stripped down to less than 100 files
            if not isGood:
                kwNames = ",".join((keyword.name for keyword in keywords))
                if not result is None and len(result) < 100:
                    reportAction.addData ("Search stopped with common keyword '%s'" % (kwNames, ))
                    break
                else:
                    if not result is None:
                        reportAction.addData ("Common keyword '%s' used because %u matches are too much" % (kwNames, len(result)))
                    else:
                        reportAction.addData ("Common keyword '%s' used as first keyword" % (kwNames, ))
            inString = ",".join((str(keyword.id) for keyword in keywords))
            stmt = "SELECT DISTINCT fullpath FROM kw2doc,documents WHERE docID=id AND kwID IN (%s) ORDER BY fullpath" % (inString, )
            q.execute (stmt)
            kwMatches = q.fetchall()
            if result is None:
                result = kwMatches
            else:
                result = intersectSortedLists (result,  kwMatches)
            if not result:
                return []
        return result

    def __filterDocsBySearchPhrase (self,  results,  query,  cancelEvent=None):
        finalResults = []
        reExpr = query.regExForMatches()
        bHasFilters = query.folderFilter or query.extensionFilter
        for fullpath in results:
            if bHasFilters:
                 if not query.matchFolderAndExtensionFilter(fullpath):
                    continue
            try:
                with fopen(fullpath) as input:
                    if reExpr.search(input.read()):
                        finalResults.append (fullpath)
            except:
                pass
                
            if cancelEvent and cancelEvent.is_set():
                return []
                
        return finalResults
        
    # Receives a list of lists of Keywords and returns a two lists.
    # The first list contains the good keywords in input order. These are keywords which are not found if commonKeywordMap.
    # The second list contains the bad keywords which were found in commonKeywordMap ordered from the less worst to the worst.
    def __qualifyKeywords (self, kwList,  commonKeywordMap):
        goodKeywords = []
        badKeywordsTemp = [] # contains touples (quality,keywords) in order to sort by quality
        for keywords in kwList:
            # Check if one of the keywords is found in mapCommonKeywords
            quality = None
            for keyword in keywords:
                if keyword.name in commonKeywordMap:
                    q= commonKeywordMap[keyword.name]
                    if not quality or q < quality:
                        quality = q
            if quality is None:
                # Not in the common keyword map
                goodKeywords.append(keywords)
            else:
                # In the common keyword map
                badKeywordsTemp.append((quality, keywords))
        badKeywords = [keywords for quality, keywords in sorted(badKeywordsTemp, reverse=True)]
        return goodKeywords, badKeywords
    
    # Receives a list of keywords which might contain wildcards. For every passed keyword a list of Keyword objects
    # is returned. If a keyword is not found an empty list is returned.
    def __getKeywords (self,  q,  keywordList,  reportAction=None):
        keys = []
        for kw in keywordList:
            query = "SELECT id,keyword FROM keywords WHERE"
            if kw.find("*")!=-1:
                query = query + " keyword LIKE ? ESCAPE '!'"
                kw = kw.replace("_", "!_")
                kw = kw.replace("*", "%")
            else:
                query = query + " keyword=?"
            q.execute(query, (kw, ))
            result = q.fetchall()
            if not result:
                if reportAction: reportAction.addData ("String '%s' was not found",  kw)
                return []
            if reportAction: reportAction.addData ("String '%s' results in %u keyword matches",  kw,  len(result))
            keys.append([Keyword(r[0], r[1]) for r in result])
        return keys
                    
    def updateIndex (self, directories,  extensions,  dirExcludes=[],  statistics=None):
        c = self.conn.cursor ()
        q = self.conn.cursor ()
        
        #c.execute("PRAGMA synchronous = OFF")
        #c.execute("PRAGMA journal_mode = MEMORY")

        with self.conn:
            # Generate the next index ID, old documents still have a lower number
            nextIndexID = self.__getNextIndexRun (c)
            
            for strRootDir in directories:
                logging.info ("-"*80)
                logging.info ("Updating index in " + strRootDir)
                for strFullPath in genFind(extensions, strRootDir,  dirExcludes):
                    mTime = os.stat(strFullPath)[8]
                 
                    c.execute ("INSERT OR IGNORE INTO documents (id,timestamp,fullpath) VALUES (NULL,?,?)", (mTime,strFullPath))
                    if c.rowcount == 1 and c.lastrowid != 0:
                        # New document must always be processed
                        docID = c.lastrowid
                        timestamp = 0
                    else:
                        q.execute("SELECT id,timestamp FROM documents WHERE fullpath=:fp", {"fp":strFullPath})
                        docID,timestamp = q.fetchone()
                        
                    try:
                        if timestamp != mTime:
                            self.__updateFile (c, q, docID, strFullPath, mTime)
                            if statistics:
                                if timestamp != 0: 
                                    c.execute ("UPDATE documents SET timestamp=:ts WHERE id=:id", {"ts":mTime, "id":docID})
                                    statistics.incUpdated()
                                else: 
                                    statistics.incNew()
                        else:
                            if statistics: statistics.incUnchanged()
                    except Exception as e:
                        print ("Failed to process file '%s'" % (strFullPath, ))
                        print (e)
                        # Write an nextIndexID of -1 which makes sure the document in removed in the cleanup phase
                        c.execute ("INSERT OR REPLACE INTO documentInIndex (docID,indexID) VALUES (?,?)", (docID, -1))
                    else:
                        # We always write the next index ID. This is needed to find old files which still have lower indexID values.
                        c.execute ("INSERT OR REPLACE INTO documentInIndex (docID,indexID) VALUES (?,?)", (docID, nextIndexID))

            # Now remove all documents with a lower indexID and their keyword associations
            logging.info ("Cleaning associations")
            c.execute ("DELETE FROM kw2doc WHERE docID IN (SELECT docID FROM documentInIndex WHERE indexID < :index)", {"index":nextIndexID})
            logging.info ("Cleaning documents")
            c.execute ("DELETE FROM documents WHERE id IN (SELECT docID FROM documentInIndex WHERE indexID < :index)", {"index":nextIndexID})
            logging.info ("Cleaning document index")
            c.execute("DELETE FROM documentInIndex WHERE indexID < :index",  {"index":nextIndexID})
            logging.info ("Removing orphaned keywords")
            c.execute("DELETE FROM keywords WHERE id NOT IN (SELECT kwID FROM kw2doc)")
        logging.info("Done")

    def __updateFile (self, c, q, docID, strFullPath, mTime):
        # Delete old associations
        c.execute ("DELETE FROM kw2doc WHERE docID=?", (docID,))
        # Associate document with all tokens
        lower = str.lower
        with fopen(strFullPath) as input:
            for token in genTokens (input):
                keyword = lower(token)
                     
                c.execute ("INSERT OR IGNORE INTO keywords (id,keyword) VALUES (NULL,?)", (keyword,))
                if c.rowcount == 1 and c.lastrowid != 0:
                    kwID = c.lastrowid
                else:
                    q.execute("SELECT id FROM keywords WHERE keyword=:kw", {"kw":keyword})
                    kwID = q.fetchone()[0]
                    
                c.execute ("INSERT OR IGNORE INTO kw2doc (kwID,docID) values (?,?)", (kwID,docID))
            
    def __setupDatabase (self):
        with self.conn:
            c = self.conn.cursor ()
            c.executescript (strSetup) 

    def __getNextIndexRun (self, c):
       c.execute ("INSERT INTO indexInfo (id,timestamp) VALUES (NULL,?)", (int(time.time()),))
       return c.lastrowid
    
def buildMapFromCommonKeywordFile (name):
    mapCommonKeywords = {}
    if name:
        with fopen(name, "r") as input:
            for number, keyword in ((number, keyword.strip().lower()) for number, keyword in enumerate(input)):
                if keyword:
                    mapCommonKeywords[keyword] = number
    return mapCommonKeywords

def resolveKeywordId (q, i):
    q.execute("SELECT keyword FROM keywords WHERE id=:kw", {"kw":i})
    return q.fetchone()[0]

def getDocumentId (q, fullpath):
    q.execute("SELECT id FROM documents WHERE fullpath=:fp", {"fp":fullpath})
    return q.fetchone()[0]

def hasDocumentKeyword (q, docID, kwID):
    q.execute ("SELECT docID from kw2doc where docID=:d and kwID=:k", {"d":docID,"k":kwID})
    if q.fetchone():
        return True
    return False

if __name__ == "__main__":
    unittest.main()

