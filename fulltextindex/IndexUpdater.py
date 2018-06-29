# -*- coding: utf-8 -*-
"""
Copyright (C) 2018 Oliver Tengler

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
import re
import time
import logging
import sqlite3
from typing import List, Iterator, IO
from tools.FileTools import fopen
from .IndexDatabase import IndexDatabase

reTokenize = re.compile(r"[\w#]+")

def genFind(filepat: List[str], strRootDir: str, dirExcludes: List[str]=None) -> Iterator[str]:
    dirExcludes = dirExcludes or []
    def fixExtension(ext: str) -> str:
        if ext != ".":
            return ext
        return ""
    filepat = [fixExtension(pat) for pat in filepat]
    dirExcludes = [dir.lower() for dir in dirExcludes]
    for path, _, filelist in os.walk(strRootDir):
        if dirExcludes:
            pathLower = path.lower()
            found = False
            for exclude in dirExcludes:
                if pathLower.find(exclude) != -1:
                    found = True
                    break
            if found:
                continue
        for name in (name for name in filelist if os.path.splitext(name)[1].lower() in filepat):
            yield os.path.join(path, name)

def genTokens(file: IO) -> Iterator[str]:
    for token in reTokenize.findall(file.read()):
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
    def updateIndex(self, directories: List[str], extensions: List[str], dirExcludes: List[str]=None, statistics: UpdateStatistics=None) -> None:
        dirExcludes = dirExcludes or []
        c = self.conn.cursor()
        q = self.conn.cursor()

        #c.execute("PRAGMA synchronous = OFF")
        #c.execute("PRAGMA journal_mode = MEMORY")

        with self.conn:
            # Generate the next index ID, old documents still have a lower number
            nextIndexID = self.__getNextIndexRun(c)

            for strRootDir in directories:
                logging.info("Updating index in %s", strRootDir)
                for strFullPath in genFind(extensions, strRootDir, dirExcludes):
                    mTime = os.stat(strFullPath).st_mtime

                    c.execute("INSERT OR IGNORE INTO documents (id,timestamp,fullpath) VALUES (NULL,?,?)", (mTime, strFullPath))
                    if c.rowcount == 1 and c.lastrowid != 0:
                        # New document must always be processed
                        docID = c.lastrowid
                        timestamp = 0
                    else:
                        q.execute("SELECT id,timestamp FROM documents WHERE fullpath=:fp", {"fp":strFullPath})
                        docID, timestamp = q.fetchone()

                    try:
                        if timestamp != mTime:
                            self.__updateFile(c, q, docID, strFullPath)
                            c.execute("UPDATE documents SET timestamp=:ts WHERE id=:id", {"ts":mTime, "id":docID})
                            if statistics:
                                if timestamp != 0:
                                    statistics.incUpdated()
                                else:
                                    statistics.incNew()
                        else:
                            if statistics:
                                statistics.incUnchanged()
                    except Exception as e:
                        logging.error("Failed to process file '%s'", strFullPath)
                        logging.error(str(e))
                        # Write an nextIndexID of -1 which makes sure the document in removed in the cleanup phase
                        c.execute("INSERT OR REPLACE INTO documentInIndex (docID,indexID) VALUES (?,?)", (docID, -1))
                    else:
                        # We always write the next index ID. This is needed to find old files which still have lower indexID values.
                        c.execute("INSERT OR REPLACE INTO documentInIndex (docID,indexID) VALUES (?,?)", (docID, nextIndexID))

            # Now remove all documents with a lower indexID and their keyword associations
            logging.info("Cleaning associations")
            c.execute("DELETE FROM kw2doc WHERE docID IN (SELECT docID FROM documentInIndex WHERE indexID < :index)", {"index":nextIndexID})
            logging.info("Cleaning documents")
            c.execute("DELETE FROM documents WHERE id IN (SELECT docID FROM documentInIndex WHERE indexID < :index)", {"index":nextIndexID})
            logging.info("Cleaning document index")
            c.execute("DELETE FROM documentInIndex WHERE indexID < :index", {"index":nextIndexID})
            logging.info("Removing orphaned keywords")
            c.execute("DELETE FROM keywords WHERE id NOT IN (SELECT kwID FROM kw2doc)")
            logging.info("Removing old indexInfo entry")
            c.execute("DELETE FROM indexInfo WHERE id < :index", {"index":nextIndexID})
        logging.info("Done")

    def __updateFile(self, c: sqlite3.Cursor, q: sqlite3.Cursor, docID: int, strFullPath: str) -> None:
        # Delete old associations
        c.execute("DELETE FROM kw2doc WHERE docID=?", (docID,))
        # Associate document with all tokens
        lower = str.lower
        with fopen(strFullPath) as inputFile:
            for token in genTokens(inputFile):
                keyword = lower(token)

                c.execute("INSERT OR IGNORE INTO keywords (id,keyword) VALUES (NULL,?)", (keyword,))
                if c.rowcount == 1 and c.lastrowid != 0:
                    kwID = c.lastrowid
                else:
                    q.execute("SELECT id FROM keywords WHERE keyword=:kw", {"kw":keyword})
                    kwID = q.fetchone()[0]

                c.execute("INSERT OR IGNORE INTO kw2doc (kwID,docID) values (?,?)", (kwID, docID))

    def __getNextIndexRun(self, c: sqlite3.Cursor) -> int:
        c.execute("INSERT INTO indexInfo (id,timestamp) VALUES (NULL,?)", (int(time.time()),))
        return c.lastrowid



