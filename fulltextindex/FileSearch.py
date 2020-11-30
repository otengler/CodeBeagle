# -*- coding: utf-8 -*-
"""
Copyright (C) 2020 Oliver Tengler

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

import re
import os
import sqlite3
from .Query import FileQuery, PerformanceReport, SearchResult, safeLen, hasFileNameWildcard, createPathMatchPattern

emptyPattern = re.compile("") # make mypy happy

def escapeFileName(name: str) -> str:
    name = name.replace("_", "!_")
    name = name.replace("?", "_") # one char wild card
    return name.replace("*", "%") # any number char wild card

def searchFile(q: sqlite3.Cursor, query: FileQuery, perfReport: PerformanceReport=None) -> SearchResult:
    if not isinstance(query, FileQuery):
        raise RuntimeError("query must be a FileQuery derived object")

    perfReport = perfReport or PerformanceReport()

    search = query.search.lower()
    positiveExtFilter = query.getExtensionFilterExpression().includeParts
    negativeExtFilter = query.getExtensionFilterExpression().excludeParts

    params = {}

    queryStmt = "SELECT DISTINCT fullpath FROM fileName fn,fileName2doc fn2d,documents d WHERE fn2d.docID=d.id AND fn2d.fileNameID=fn.id AND "

    fileNameHasWildcards = hasFileNameWildcard(search)

    if fileNameHasWildcards:
        queryStmt += "fn.name LIKE :searchTerm ESCAPE '!'"
        params["searchTerm"] = escapeFileName(search)
    else:
        queryStmt += "fn.name = :searchTerm"
        params["searchTerm"] = search

    if positiveExtFilter or negativeExtFilter:
        positiveWildcard = False
        negatedWildcard = False
        positiveParams = []
        negativeParams = []
        iPos = 1
        iNeg = 1
        for ext in positiveExtFilter:
            positiveWildcard |= hasFileNameWildcard(ext)
            p = f"p{iPos}"
            iPos+=1
            positiveParams.append(":" + p)
            params[p] = escapeFileName(ext)
        for ext in negativeExtFilter:
            negatedWildcard |= hasFileNameWildcard(ext)
            p = f"n{iNeg}"
            iNeg+=1
            negativeParams.append(":" + p)
            params[p] = escapeFileName(ext)

        # If no wildcard is used the in list approach is more efficient. For wildcards we need 'like'. Both are shown here
        # fn.ext in ('.h','.cpp') and not (fn.ext like '.a%' or fn.ext like '.b')) 
        if positiveExtFilter:
            queryStmt += " AND "
            if not positiveWildcard:
                queryStmt += "fn.ext IN ({})".format(",".join(positiveParams)) # IN (p1,p2,p3)
            else:
                queryStmt += "("
                queryStmt += " OR ".join((f"fn.ext LIKE {p}" for p in positiveParams))
                queryStmt += ")"
        if negativeExtFilter:
            queryStmt += " AND NOT "
            if not negatedWildcard:
                queryStmt += "fn.ext IN ({})".format(",".join(negativeParams)) # IN (n1,n2,n3)
            else:
                queryStmt += "("
                queryStmt += " OR ".join((f"fn.ext LIKE {p}" for p in negativeParams))
                queryStmt += ")"

    with perfReport.newAction("Finding documents") as action:
        q.execute(queryStmt + " ORDER BY d.fullpath", params)
        result = q.fetchall()
        action.addData("%u matches", safeLen(result))


    if query.folderFilter:
        result = [r[0] for r in result if query.matchFolderAndExtensionFilter(r[0], True, False)]
    else:
        result = [r[0] for r in result]

    if not query.bCaseSensitive:
        return result

    # Case sensitive search requested. The DB is always case insensitive so filter out unwanted results
    searchPattern = emptyPattern
    searchName = os.path.splitext(query.search)[0]
    if fileNameHasWildcards:
        searchPattern = re.compile(createPathMatchPattern(searchName), 0)

    filtered = []
    for r in result:
        name,_ = os.path.splitext(r)
        name = os.path.basename(name)
        if not fileNameHasWildcards:
            if name == searchName:
                filtered.append(r)
        elif searchPattern.match(name):
            filtered.append(r)

    return filtered
