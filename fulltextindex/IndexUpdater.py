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
import os.path
import re
import time
import logging
import sqlite3
from fnmatch import fnmatch
from typing import List, Iterator, Set, cast, Tuple, Optional, Dict
from tools.FileTools import freadall
from .IndexDatabase import IndexDatabase
from .IndexConfiguration import IndexConfiguration, IndexType, indexTypeToString

reTokenize = re.compile(r"[\w#]+")

def __fixExtension(ext: str) -> str:
    """A single dot means no extension"""
    if ext != ".":
        return ext 
    return ""

def genFind(filepat: Set[str], strRootDir: str, dirExcludes: Optional[List[str]]=None, ignoredExts: Optional[Dict[str, int]]=None,
            fileExcludes: Optional[List[str]]=None) -> Iterator[Tuple[str,str]]:
    dirExcludes = dirExcludes or []
    fileExcludes = fileExcludes or []

    filepatFixed: Set[str] = set()
    for pat in (__fixExtension(pat) for pat in filepat):
        filepatFixed.add(pat)

    dirExcludes = [dir.lower() for dir in dirExcludes]
    fileExcludes = [f.lower() for f in fileExcludes]
    for path, dirnames, filelist in os.walk(strRootDir):
        if dirExcludes:
            pathLower = path.lower()
            found = False
            for exclude in dirExcludes:
                if fnmatch (pathLower, exclude):
                    found = True
                    break
            if found:
                # Prune the walk so os.walk does not descend into subdirectories of an excluded directory
                dirnames[:] = []
                continue
        for name in filelist:
            ext = os.path.splitext(name)[1].lower()
            if not filepatFixed or ext in filepatFixed:
                # Check file exclude patterns against full path
                if fileExcludes:
                    fullPath = os.path.join(path, name).lower()
                    skip = False
                    for fe in fileExcludes:
                        if fnmatch(fullPath, fe):
                            skip = True
                            break
                    if skip:
                        continue
                yield (path, name)
            elif ignoredExts is not None:
                ignoredExts[ext] = ignoredExts.get(ext, 0) + 1

def genTokens(text: str) -> Iterator[str]:
    for token in reTokenize.findall(text):
        yield token

class UpdateStatistics:
    def __init__(self) -> None:
        self.nNew: int = 0
        self.nUpdated: int = 0
        self.nUnchanged: int = 0

    def incNew(self) -> None:
        self.nNew += 1

    def incUpdated(self) -> None:
        self.nUpdated += 1

    def incUnchanged(self) -> None:
        self.nUnchanged += 1

    def __str__(self) -> str:
        s = "New docs: %u, Updated docs: %u, Unchanged: %u"  % (self.nNew, self.nUpdated, self.nUnchanged)
        return s

class IndexUpdater (IndexDatabase):
    def updateIndex(self, config: IndexConfiguration, statistics: Optional[UpdateStatistics]=None) -> None:
        kwCache: dict[str, int] = {}
        directories = config.directories
        extensions = config.extensions
        dirExcludes = config.dirExcludes or []
        fileExcludes = config.fileExcludes or []
        indexType = config.indexType

        c = self.conn.cursor()
        q = self.conn.cursor()

        with self.conn:
            # Generate the next index ID, old documents still have a lower number
            nextIndexID = self.__getNextIndexRun(c)

            for strRootDir in directories:
                logging.info("Updating index in %s. Indexing %s", strRootDir, indexTypeToString(indexType))
                ignoredExtCount: Dict[str, int] = {}
                for dirName, fileName in genFind(extensions, strRootDir, dirExcludes, ignoredExtCount, fileExcludes):
                    strFullPath = os.path.join(dirName, fileName)
                    mTime = os.stat(strFullPath).st_mtime
                    docIdAndTimestamp = self.__getDocumentId(c, q, strFullPath, mTime)
                    self.__handleSingleFile(c, q, strFullPath, fileName, docIdAndTimestamp, mTime, indexType, nextIndexID, statistics, kwCache)
                if ignoredExtCount:
                    logging.info("Ignored files with these extensions: %s", sorted(ignoredExtCount.keys()))
                    self.__saveExcludedExtensions(c, nextIndexID, ignoredExtCount)
                    logging.info("Saved %d excluded extension types", len(ignoredExtCount))
            self.__cleanup(c, nextIndexID)
        logging.info("Done")

    def __handleSingleFile(self, c: sqlite3.Cursor, q: sqlite3.Cursor, strFullPath: str, fileName: str, docIdAndTimestamp: Tuple[int, float | None], 
                           mTime: float, indexType: IndexType, nextIndexID: Optional[int],  
                           statistics: Optional[UpdateStatistics], kwCache: dict[str, int]) -> None:
        docID, timestamp = docIdAndTimestamp
        newFile = timestamp is None

        if indexType != IndexType.FileContent:
            self.__addFileName(c, q, docID, fileName)

        try:
            if indexType != IndexType.FileName:
                if timestamp != mTime:
                    self.__updateFile(c, q, docID, strFullPath, kwCache)
                    c.execute("UPDATE documents SET timestamp=:ts WHERE id=:id", {"ts":mTime, "id":docID})
                    if statistics and not newFile:
                        statistics.incUpdated()
                else:
                    if statistics:
                        statistics.incUnchanged()
        except Exception as e:
            logging.error("Failed to process file '%s'", strFullPath)
            logging.error(str(e))
            # Write an nextIndexID of -1 which makes sure the document is removed in the cleanup phase
            c.execute("INSERT OR REPLACE INTO documentInIndex (docID,indexID) VALUES (?,?)", (docID, -1))
        else:
            # We always write the next index ID. This is needed to find old files which still have lower indexID values.
            if nextIndexID is not None:
                c.execute("INSERT OR REPLACE INTO documentInIndex (docID,indexID) VALUES (?,?)", (docID, nextIndexID))
            if statistics and newFile:
                statistics.incNew()

    def __getDocumentId(self, c: sqlite3.Cursor, q: sqlite3.Cursor, strFullPath: str, mTime: float) -> Tuple[int, Optional[float]]: 
        c.execute("INSERT OR IGNORE INTO documents (id,timestamp,fullpath) VALUES (NULL,?,?)", (mTime, strFullPath))
        docID: int
        if c.rowcount == 1 and c.lastrowid != 0:
            # New document must always be processed
            docID = cast(int, c.lastrowid)
            if docID is None:
                raise RuntimeError("No document ID for new document returned")
            return (docID, None)
        else:
            q.execute("SELECT id,timestamp FROM documents WHERE fullpath=:fp", {"fp":strFullPath})
            row = q.fetchone()
            if row:
                return cast(Tuple[int, float], row)
            # Should never happen since INSERT OR IGNORE was executed above
            raise RuntimeError("No document ID for existing document returned")

    def __saveExcludedExtensions(self, c: sqlite3.Cursor, indexID: int, extCounts: Dict[str, int]) -> None:
        """Save excluded extension statistics to database."""
        for ext, count in extCounts.items():
            c.execute("INSERT INTO excludedExtensions (id,indexID,extension,fileCount) VALUES (NULL,?,?,?)",
                     (indexID, ext, count))

    def updateFile(self, config: IndexConfiguration, strFullPath: str, statistics: Optional[UpdateStatistics] = None) -> None:
        """
        Update the index for a single file.

        This is a lightweight alternative to updateIndex() which only processes
        the given file. It reuses the latest index run ID so that a subsequent
        full updateIndex() still works correctly.

        Args:
            config: The index configuration that covers this file.
            filePath: Full path to the file to update.

        Raises:
            FileNotFoundError: If filePath does not exist.
            ValueError: If the file's extension is not in the configuration.
        """
        if not os.path.isfile(strFullPath):
            raise FileNotFoundError(f"File not found: {strFullPath}")

        ext = os.path.splitext(strFullPath)[1].lower()
        if ext and ext not in config.extensions:
            raise ValueError(f"Extension '{ext}' is not indexed by this configuration")

        indexType = config.indexType
        kwCache: dict[str, int] = {}
        _, fileName = os.path.split(strFullPath)
        mTime = os.stat(strFullPath).st_mtime

        c = self.conn.cursor()
        q = self.conn.cursor()

        with self.conn:
            docIdAndTimestamp = self.__getDocumentId(c, q, strFullPath, mTime)
            # Rempve all document keyword associated and reset the timestamp. In case the __updateSingleFile
            # fails at least the next full index update will fix it.
            c.execute("DELETE FROM kw2doc WHERE docID = :docID", {"docID": docIdAndTimestamp[0]})
            c.execute("UPDATE documents SET timestamp=0 WHERE id=:id", {"id":docIdAndTimestamp[0]})
            self.__handleSingleFile(c, q, strFullPath, fileName, docIdAndTimestamp, mTime, indexType, None, statistics, kwCache)

    def __updateFile(self, c: sqlite3.Cursor, q: sqlite3.Cursor, docID: int, strFullPath: str, kwCache: dict[str, int]) -> None:
        # Delete old associations
        c.execute("DELETE FROM kw2doc WHERE docID=?", (docID,))
        # Associate document with all tokens
        lower = str.lower
        for token in genTokens(freadall(strFullPath)):
            keyword = lower(token)

            if keyword in kwCache:
                kwID = kwCache[keyword]
            else:
                c.execute("INSERT OR IGNORE INTO keywords (id,keyword) VALUES (NULL,?)", (keyword,))
                if c.rowcount == 1 and c.lastrowid != 0 and c.lastrowid != None:
                    kwID = c.lastrowid
                else:
                    q.execute("SELECT id FROM keywords WHERE keyword=:kw", {"kw":keyword})
                    kwID = q.fetchone()[0]
                kwCache[keyword] = kwID

            c.execute("INSERT OR IGNORE INTO kw2doc (kwID,docID) values (?,?)", (kwID, docID))

    def __addFileName(self, c: sqlite3.Cursor, q: sqlite3.Cursor, docID: int, fileName: str) -> None:
        name,ext = os.path.splitext(fileName.lower())

        c.execute("INSERT OR IGNORE INTO fileName (id,name,ext) VALUES (NULL,?,?)", (name, ext))
        if c.rowcount == 1 and c.lastrowid != 0:
            fileID = c.lastrowid
        else:
            q.execute("SELECT id from fileName WHERE name=:name AND ext=:ext", {"name":name, "ext":ext})
            fileID = q.fetchone()[0]

        c.execute("INSERT OR IGNORE INTO fileName2doc (fileNameID, docID) VALUES (?,?)", (fileID, docID))

    def __cleanup(self, c: sqlite3.Cursor, nextIndexID:int) -> None:
        logging.info("Cleaning associations")
        c.execute("DELETE FROM kw2doc WHERE docID IN (SELECT docID FROM documentInIndex WHERE indexID < :index)", {"index":nextIndexID})
        logging.info("Cleaning documents")
        c.execute("DELETE FROM documents WHERE id IN (SELECT docID FROM documentInIndex WHERE indexID < :index)", {"index":nextIndexID})
        logging.info("Cleaning document index")
        c.execute("DELETE FROM documentInIndex WHERE indexID < :index", {"index":nextIndexID})
        logging.info("Removing orphaned keywords")
        c.execute("DELETE FROM keywords WHERE id NOT IN (SELECT kwID FROM kw2doc)")
        logging.info("Cleaning file name associations")
        c.execute("DELETE FROM fileName2doc WHERE docID NOT IN (SELECT id FROM documents)")
        logging.info("Cleaning file names")
        c.execute("DELETE FROM fileName WHERE id NOT IN (SELECT fileNameID FROM fileName2doc)")
        logging.info("Removing old indexInfo entry")
        c.execute("DELETE FROM indexInfo WHERE id < :index", {"index":nextIndexID})
        logging.info("Cleaning excluded extensions")
        c.execute("DELETE FROM excludedExtensions WHERE indexID < :index", {"index":nextIndexID})

    def __getNextIndexRun(self, c: sqlite3.Cursor) -> int:
        c.execute("INSERT INTO indexInfo (id,timestamp) VALUES (NULL,?)", (int(time.time()),))
        return cast(int,c.lastrowid)

    def getExcludedExtensions(self) -> List[Tuple[str, int]]:
        """
        Read excluded extensions from the index database.

        Returns:
            List of tuples (extension, fileCount) sorted by count descending,
            or empty list if no data is available

        Raises:
            sqlite3.Error: If there's a database error
        """
        cursor = self.conn.cursor()

        # Get the most recent index run
        cursor.execute("SELECT MAX(id) FROM indexInfo")
        result = cursor.fetchone()
        if not result or result[0] is None:
            return []

        mostRecentIndexID = result[0]

        # Get excluded extensions for that run, sorted by count descending
        cursor.execute("""
            SELECT extension, SUM(fileCount) as totalCount
            FROM excludedExtensions
            WHERE indexID = ?
            GROUP BY extension
            ORDER BY totalCount DESC, extension ASC
        """, (mostRecentIndexID,))

        return cursor.fetchall() or []
