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
import unittest
import shutil
import stat
from typing import cast, Callable
from .FullTextIndex import FullTextIndex, Keyword, buildMapFromCommonKeywordFile
from .Query import ContentQuery, FileQuery
from .IndexUpdater import IndexUpdater, UpdateStatistics
from .IndexConfiguration import IndexConfiguration, IndexType

def delFile (name: str) -> None:
    try:
        os.unlink (name)
    except Exception as e:
        print (str(e))

def delDir (name: str) -> None:
    try:
        removeReadOnly (name)
        shutil.rmtree(name)
    except WindowsError as e:
        if e.winerror != 3:
            raise

def removeReadOnly (path: str) -> None:
    for path, _, filelist in os.walk (path):
        for name in filelist:
            fullpath = os.path.join(path, name)
            fileAtt = os.stat(fullpath).st_mode
            if not fileAtt & stat.S_IWRITE:
                # File is read-only, so make it writeable
                os.chmod(fullpath, stat.S_IWRITE)

# Change modified timestamp of a file one year back in time
def modifyTimestamp (name: str) -> None:
    st = os.stat(name)
    atime = st.st_atime #access time
    mtime = st.st_mtime #modification time
    new_mtime = mtime - (365*24*3600) # one year in the past
    os.utime(name,(atime,new_mtime))

def setModifyTimestamp(name: str, seconds: float) -> None:
    os.utime(name,(seconds,seconds))

def getModulePath () -> str:
    import __main__
    return cast(str, os.path.split(__main__.__file__)[0])

def forAllFiles(name: str, doAction: Callable) -> None:
    for root, _, files in os.walk(name):
        for file in files:
            doAction(os.path.join(root,file))

class TestFullTextIndex(unittest.TestCase):
    def test(self) -> None:
        testPath = os.path.join(getModulePath (), "tests")
        os.chdir(testPath)

        aNiceTime = 1586099163.8849764  # Set all test files to a defined time
        def setTime(name: str) -> None:
            setModifyTimestamp(name, aNiceTime)
        forAllFiles("data1", setTime)
        forAllFiles("data2", setTime)

        delFile ("test.dat")

        updater = IndexUpdater("test.dat")

        # Copy initial data
        # Data1
        # ebcdic.c: "conversion table"
        # utf8.txt: "äöüß"
        # utf16.txt: "äöüß"
        # test1.c: "Dschungelbuch"
        # test2.c: "Dschungelbuch Bambi"
        # test3.c: "Tom & Cherry"

        delDir("data")
        shutil.copytree ("data1", "data")
        updateStats = UpdateStatistics()
        config = IndexConfiguration("test", ".c,.cpp,.cxx,.txt", os.path.join(testPath,"data"))
        updater.updateIndex (config, updateStats)
        self.assertEqual(updateStats.nNew,  6)
        self.assertEqual(updateStats.nUpdated,  0)
        self.assertEqual(updateStats.nUnchanged,  0)
        stats = updater.queryStats()
        self.assertEqual (stats[0], 6)
        self.assertEqual (stats[1], 6)

        fti = FullTextIndex("test.dat")

        q = ContentQuery ("conversion table")
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\latin_1\ebcdic.c")]
        self.assertEqual (result, exp)

        q = ContentQuery ("äöüß")
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\utf16\utf16.txt"), os.path.join(testPath, r"data\utf8\utf8.txt")]
        self.assertEqual (result, exp)

        q = ContentQuery ("dschungelbuch")
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\test1.cpp"), os.path.join(testPath, r"data\test2.cxx")]
        self.assertEqual (result, exp)

        q = ContentQuery ("BamBi")
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\test2.cxx")]
        self.assertEqual (result, exp)

        q = ContentQuery ("Tom & cherry")
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\test3.c")]
        self.assertEqual (result, exp)

        # Update data
        # Data2
        # ebcdic.c: "conversion table"
        # utf8.txt: "äöüß"
        # utf16.txt: "äöüß", "Dschungelbuch"
        # corrupt_utf8.c: Corrupt BOM (file should be ignored)
        # test1.c:  "Dschungelbuch Neuer Text"
        # test2.c: "Dschungelbuch"
        # test3.c: Gelöscht
        # test4.c: Neu: "Speedy Gonzales"
        # test5.c: Neu: "Just to have another file"

        delDir("data")
        shutil.copytree ("data2", "data")
        # Make sure these three files have a modified timestamp:
        modifyTimestamp ("data\\utf16\\utf16.txt")
        modifyTimestamp ("data\\test1.cpp")
        modifyTimestamp ("data\\test2.cxx")

        updateStats = UpdateStatistics()
        updater.updateIndex (config, updateStats)
        self.assertEqual(updateStats.nNew,  2)
        self.assertEqual(updateStats.nUpdated,  3)
        self.assertEqual(updateStats.nUnchanged,  2)
        stats = fti.queryStats()
        self.assertEqual (stats[0], 7)
        self.assertEqual (stats[1], 7)

        q = ContentQuery ("conversion table")
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\latin_1\ebcdic.c")]
        self.assertEqual (result, exp)

        q = ContentQuery ("äöüß")
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\utf16\utf16.txt"), os.path.join(testPath, r"data\utf8\utf8.txt")]
        self.assertEqual (result, exp)

        q = ContentQuery ("DschungelbUch")
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\test1.cpp"), os.path.join(testPath, r"data\test2.cxx"), os.path.join(testPath, r"data\utf16\utf16.txt")]
        self.assertEqual (result, exp)

        q = ContentQuery ("Neuer Text")
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\test1.cpp")]
        self.assertEqual (result, exp)

        q = ContentQuery ("Bambi")
        result = fti.searchContent(q)
        exp = []
        self.assertEqual (result, exp)

        q = ContentQuery ("Tom & Cherry")
        result = fti.searchContent(q)
        exp = []
        self.assertEqual (result, exp)

        q = ContentQuery ("speedy gonzales")
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\test4.c")]
        self.assertEqual (result, exp)

        # Test folder filter
        q = ContentQuery ("Dschungelbuch",  "utf16")
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\utf16\utf16.txt")]
        self.assertEqual (result, exp)

        # Test extension filter
        q = ContentQuery ("Dschungelbuch",  "", "*.c*")
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\test1.cpp"), os.path.join(testPath, r"data\test2.cxx")]
        self.assertEqual (result, exp)

        # Test case sensitivity
        q = ContentQuery ("speedy gonzales",  "", "",  True)
        result = fti.searchContent(q,)
        exp = []
        self.assertEqual (result, exp)

        # Update index again to check that no updated file will be found
        updateStats = UpdateStatistics()
        config.indexType = IndexType.FileContentAndName
        updater.updateIndex (config, updateStats)
        self.assertEqual(updateStats.nNew,  0)
        self.assertEqual(updateStats.nUpdated,  0)
        self.assertEqual(updateStats.nUnchanged,  7)
        stats = fti.queryStats()
        self.assertEqual (stats[0], 7)
        self.assertEqual (stats[1], 7)

        # Test file search
        q2 = FileQuery("utf8.txt") # test search specific file
        result = fti.searchFile(q2)
        exp = [os.path.join(testPath, r"data\utf8\utf8.txt")]
        self.assertEqual(exp, result)

        q2 = FileQuery("test*", "", "c??") # test extension filter
        result = fti.searchFile(q2)
        exp = [os.path.join(testPath, r"data\test1.cpp"), os.path.join(testPath, r"data\test2.cxx")]
        self.assertEqual (result, exp)

        q2 = FileQuery("*", "latin_?", "c") # test folder filter
        result = fti.searchFile(q2)
        exp = [os.path.join(testPath, r"data\latin_1\ebcdic.c")]
        self.assertEqual (result, exp)

        # Now remove everything, documents and keyword associations must be empty
        delDir("data")
        os.mkdir("data")
        updater.updateIndex (config, updateStats)

        stats = fti.queryStats()
        self.assertEqual (stats[0], 0)
        self.assertEqual (stats[1], 0)
        self.assertEqual (stats[2], 0)
        self.assertEqual (stats[3], 0)

    def testCommonKeywords(self) -> None:
        testPath = os.path.join(getModulePath (), "tests")
        os.chdir(testPath)
        delFile ("test.dat")

        fti = FullTextIndex("test.dat")
        commonKeywords = buildMapFromCommonKeywordFile("CommonKeywords.txt")
        # h
        # if
        # for
        # while

        good, bad = fti._FullTextIndex__qualifyKeywords ([[Keyword(100, "wichtiger")], [Keyword(101, "hinweis")]], commonKeywords) # type: ignore
        print (good, bad)
        self.assertEqual(len(good), 2)
        self.assertEqual(len(bad), 0)
        self.assertEqual(good[0], [Keyword(100, "wichtiger")])
        self.assertEqual(good[1], [Keyword(101, "hinweis")])

        good, bad = fti._FullTextIndex__qualifyKeywords ([[Keyword(100, "iostream")], [Keyword(101, "h")]], commonKeywords) # type: ignore
        print (good, bad)
        self.assertEqual(len(good), 1)
        self.assertEqual(len(bad), 1)
        self.assertEqual(good[0], [Keyword(100, "iostream")])
        self.assertEqual(bad[0], [Keyword(101, "h")])

        good, bad = fti._FullTextIndex__qualifyKeywords ([[Keyword(50, "func")], [Keyword(100, "whi"), Keyword(101, "while")], [Keyword(102, "true")]], commonKeywords) # type: ignore
        print (good, bad)
        self.assertEqual(len(good), 2)
        self.assertEqual(len(bad), 1)
        self.assertEqual(good[0], [Keyword(50, "func")])
        self.assertEqual(good[1], [Keyword(102, "true")])
        self.assertEqual(bad[0], [Keyword(100, "whi"), Keyword(101, "while")])

if __name__ == "__main__":
    unittest.main()
