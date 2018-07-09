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
from .FullTextIndex import FullTextIndex, SearchQuery, Keyword, buildMapFromCommonKeywordFile
from .IndexUpdater import IndexUpdater, UpdateStatistics

def delFile (name):
    try:
        os.unlink (name)
    except Exception as e:
        print (str(e))

def delDir (name):
    try:
        removeReadOnly (name)
        shutil.rmtree(name)
    except WindowsError as e:
        if e.winerror != 3:
            raise

def removeReadOnly (path):
    for path, dirlist, filelist in os.walk (path):
        for name in filelist:
            fullpath = os.path.join(path, name)
            fileAtt = os.stat(fullpath)[0]
            if not fileAtt & stat.S_IWRITE:
                # File is read-only, so make it writeable
                os.chmod(fullpath, stat.S_IWRITE)

# Change modified timestamp of a file one year back in time
def modifyTimestamp (name):
    st = os.stat(name)
    atime = st[stat.ST_ATIME] #access time
    mtime = st[stat.ST_MTIME] #modification time
    new_mtime = mtime - (365*24*3600) # one year in the past
    os.utime(name,(atime,new_mtime))

def getModulePath ():
    import __main__
    return os.path.split(__main__.__file__)[0]

class TestFullTextIndex(unittest.TestCase):
    def test(self):
        testPath = os.path.join(getModulePath (), "tests")
        os.chdir(testPath)
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
        updater.updateIndex ([os.path.join(testPath,"data")], [".c",".txt"], [], updateStats)
        self.assertEqual(updateStats.nNew,  6)
        self.assertEqual(updateStats.nUpdated,  0)
        self.assertEqual(updateStats.nUnchanged,  0)
        stats = updater.queryStats()
        self.assertEqual (stats[0], 6)
        self.assertEqual (stats[1], 6)

        fti = FullTextIndex("test.dat")

        q = SearchQuery ("conversion table")
        result = fti.search(q)
        exp = [os.path.join(testPath, r"data\latin_1\ebcdic.c")]
        self.assertEqual (result, exp)

        q = SearchQuery ("äöüß")
        result = fti.search(q)
        exp = [os.path.join(testPath, r"data\utf16\utf16.txt"), os.path.join(testPath, r"data\utf8\utf8.txt")]
        self.assertEqual (result, exp)

        q = SearchQuery ("dschungelbuch")
        result = fti.search(q)
        exp = [os.path.join(testPath, r"data\test1.c"), os.path.join(testPath, r"data\test2.c")]
        self.assertEqual (result, exp)

        q = SearchQuery ("BamBi")
        result = fti.search(q)
        exp = [os.path.join(testPath, r"data\test2.c")]
        self.assertEqual (result, exp)

        q = SearchQuery ("Tom & cherry")
        result = fti.search(q)
        exp = [os.path.join(testPath, r"data\test3.c")]
        self.assertEqual (result, exp)

        # Update data
        # Data2
        # ebcdic.c: "conversion table"
        # utf8.txt: "äöüß"
        # utf16.txt: "äöüß", "Dschungelbuch"
        # test1.c:  "Dschungelbuch Neuer Text"
        # test2.c: "Dschungelbuch"
        # test3.c: Gelöscht
        # test4.c: Neu: "Speedy Gonzales"
        # test5.c: Neu: "Just to have another file"

        delDir("data")
        shutil.copytree ("data2", "data")
        # Make sure these three files have a modified timestamp:
        modifyTimestamp ("data\\utf16\\utf16.txt")
        modifyTimestamp ("data\\test1.c")
        modifyTimestamp ("data\\test2.c")

        updateStats = UpdateStatistics()
        updater.updateIndex ([os.path.join(testPath,"data")], [".c",".txt"],  [], updateStats)
        self.assertEqual(updateStats.nNew,  2)
        self.assertEqual(updateStats.nUpdated,  3)
        self.assertEqual(updateStats.nUnchanged,  2)
        stats = fti.queryStats()
        self.assertEqual (stats[0], 7)
        self.assertEqual (stats[1], 7)

        q = SearchQuery ("conversion table")
        result = fti.search(q)
        exp = [os.path.join(testPath, r"data\latin_1\ebcdic.c")]
        self.assertEqual (result, exp)

        q = SearchQuery ("äöüß")
        result = fti.search(q)
        exp = [os.path.join(testPath, r"data\utf16\utf16.txt"), os.path.join(testPath, r"data\utf8\utf8.txt")]
        self.assertEqual (result, exp)

        q = SearchQuery ("DschungelbUch")
        result = fti.search(q)
        exp = [os.path.join(testPath, r"data\test1.c"), os.path.join(testPath, r"data\test2.c"), os.path.join(testPath, r"data\utf16\utf16.txt")]
        self.assertEqual (result, exp)

        q = SearchQuery ("Neuer Text")
        result = fti.search(q)
        exp = [os.path.join(testPath, r"data\test1.c")]
        self.assertEqual (result, exp)

        q = SearchQuery ("Bambi")
        result = fti.search(q)
        exp = []
        self.assertEqual (result, exp)

        q = SearchQuery ("Tom & Cherry")
        result = fti.search(q)
        exp = []
        self.assertEqual (result, exp)

        q = SearchQuery ("speedy gonzales")
        result = fti.search(q)
        exp = [os.path.join(testPath, r"data\test4.c")]
        self.assertEqual (result, exp)

        # Test folder filter
        q = SearchQuery ("Dschungelbuch",  "utf16")
        result = fti.search(q)
        exp = [os.path.join(testPath, r"data\utf16\utf16.txt")]
        self.assertEqual (result, exp)

        # Test extension filter
        q = SearchQuery ("Dschungelbuch",  "", "*.c")
        result = fti.search(q)
        exp = [os.path.join(testPath, r"data\test1.c"), os.path.join(testPath, r"data\test2.c")]
        self.assertEqual (result, exp)

        # Test case sensitivity
        q = SearchQuery ("speedy gonzales",  "", "",  True)
        result = fti.search(q,)
        exp = []
        self.assertEqual (result, exp)

        # Update index again to check that no updated file will be found
        updateStats = UpdateStatistics()
        updater.updateIndex ([os.path.join(testPath,"data")], [".c",".txt"],  [],  updateStats)
        self.assertEqual(updateStats.nNew,  0)
        self.assertEqual(updateStats.nUpdated,  0)
        self.assertEqual(updateStats.nUnchanged,  7)
        stats = fti.queryStats()
        self.assertEqual (stats[0], 7)
        self.assertEqual (stats[1], 7)

        # Now remove everything, documents and keyword associations must be empty
        delDir("data")
        os.mkdir("data")
        updater.updateIndex ([os.path.join(testPath,"data")], [".c",".txt"])

        stats = fti.queryStats()
        self.assertEqual (stats[0], 0)
        self.assertEqual (stats[1], 0)
        self.assertEqual (stats[2], 0)
        self.assertEqual (stats[3], 0)

    def testCommonKeywords(self):
        testPath = os.path.join(getModulePath (), "tests")
        os.chdir(testPath)
        delFile ("test.dat")

        fti = FullTextIndex("test.dat")
        commonKeywords = buildMapFromCommonKeywordFile("CommonKeywords.txt")
        # h
        # if
        # for
        # while

        good, bad = fti._FullTextIndex__qualifyKeywords ([[Keyword(100, "wichtiger")], [Keyword(101, "hinweis")]], commonKeywords)
        print (good, bad)
        self.assertEqual(len(good), 2)
        self.assertEqual(len(bad), 0)
        self.assertEqual(good[0], [Keyword(100, "wichtiger")])
        self.assertEqual(good[1], [Keyword(101, "hinweis")])

        good, bad = fti._FullTextIndex__qualifyKeywords ([[Keyword(100, "iostream")], [Keyword(101, "h")]], commonKeywords)
        print (good, bad)
        self.assertEqual(len(good), 1)
        self.assertEqual(len(bad), 1)
        self.assertEqual(good[0], [Keyword(100, "iostream")])
        self.assertEqual(bad[0], [Keyword(101, "h")])

        good, bad = fti._FullTextIndex__qualifyKeywords ([[Keyword(50, "func")], [Keyword(100, "whi"), Keyword(101, "while")], [Keyword(102, "true")]], commonKeywords)
        print (good, bad)
        self.assertEqual(len(good), 2)
        self.assertEqual(len(bad), 1)
        self.assertEqual(good[0], [Keyword(50, "func")])
        self.assertEqual(good[1], [Keyword(102, "true")])
        self.assertEqual(bad[0], [Keyword(100, "whi"), Keyword(101, "while")])

if __name__ == "__main__":
    unittest.main()
