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

import sqlite3
from typing import Tuple

strSetup = """
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

strTablesForFileNames = """
CREATE TABLE IF NOT EXISTS fileName(
  id INTEGER PRIMARY KEY,
  name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS fileName2doc(
  fileNameID INTEGER,
  docID INTEGER,
  UNIQUE(fileNameID, docID)
);
CREATE INDEX IF NOT EXISTS i_fileName2doc_fileNameID ON fileName2doc (fileNameID);
CREATE INDEX IF NOT EXISTS i_fileName2doc_docID ON fileName2doc (docID);
"""

class IndexDatabase:
    def __init__(self, strDbLocation: str) -> None:
        self.strDbLocation = strDbLocation
        self.conn = sqlite3.connect(strDbLocation)
        self.__setupDatabase()

    def __del__(self) -> None:
        self.conn.close()

    def queryStats(self) -> Tuple[int,int,int,int]:
        q = self.conn.cursor()
        q.execute("SELECT COUNT(*) FROM documents")
        documents = int(q.fetchone()[0])
        print("Documents: " + str(documents))
        q.execute("SELECT COUNT(*) FROM documentInIndex")
        documentsInIndex = int(q.fetchone()[0])
        print("Documents in index: " + str(documentsInIndex))
        q.execute("SELECT COUNT(*) FROM keywords")
        keywords = int(q.fetchone()[0])
        print("Keywords: " + str(keywords))
        q.execute("SELECT COUNT(*) FROM kw2doc")
        associations = int(q.fetchone()[0])
        print("Associations: " + str(associations))
        return (documents, documentsInIndex, keywords, associations)

    def interrupt(self) -> None:
        self.conn.interrupt()

    def __setupDatabase(self) -> None:
        with self.conn:
            c = self.conn.cursor()
            c.executescript(strSetup)