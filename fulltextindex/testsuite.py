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
import unittest
import shutil
import stat
from typing import Callable, List
from .FullTextIndex import FullTextIndex, Keyword, buildMapFromCommonKeywordFile
from .Query import ContentQuery, FileQuery, QueryParams
from .IndexUpdater import IndexUpdater, UpdateStatistics
from .IndexConfiguration import IndexConfiguration, IndexType, IndexMode
from .SearchMethods import SearchMethods

def delFile (name: str) -> None:
    try:
        if os.path.isfile(name):
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

def forAllFiles(name: str, doAction: Callable[[str], None]) -> None:
    for root, _, files in os.walk(name):
        for file in files:
            doAction(os.path.join(root,file))

def setTime(name: str) -> None:
    aNiceTime = 1586099163.8849764  # Set all test files to a defined time
    setModifyTimestamp(name, aNiceTime)

class TestFullTextIndex(unittest.TestCase):
    def testNameSearch(self) -> None:
        testPath = os.getcwd()

        forAllFiles("data_names", setTime)

        testDb = "test-names.dat"
        extPattern = ".c,.cp,.cpp,.cxx,.txt,."
        dirName = os.path.join(testPath,"data")

        delFile (testDb)
        delDir("data")
        shutil.copytree ("data_names", "data")

        configDirect = IndexConfiguration("test", extPattern, dirName, indexUpdateMode = IndexMode.NoIndexWanted)

        updateStats = UpdateStatistics()
        configDB = IndexConfiguration("test", extPattern, dirName, indexdb=testDb, indexType = IndexType.FileContentAndName)
        updater = IndexUpdater(testDb)
        updater.updateIndex (configDB, updateStats)

        # Run the same tests directly agains the file system and against a full text index DB
        for config in [configDirect, configDB]:
            self.__testNameSearch(testPath, config)
            self.__testNameSearchCaseSensitive(testPath, config)

    def __assertStringArray(self, expected: List[str], actual: List[str]) -> None:
        self.assertEqual(len(expected), len(actual))
        for a,b in zip(expected,actual):
            self.assertEqual(a.lower(),b.lower())

    def __assertTestFiles(self, testPath: str, result: List[str], expectedFiles: List[str]) -> None:
        exp = [os.path.join(testPath,x) for x in expectedFiles]
        self.__assertStringArray(exp, result)

    def __testNameSearch(self, testPath: str, config: IndexConfiguration) -> None:
        search = SearchMethods()

        print("\n================== NameSearch Test1 ==================")
        q = FileQuery (QueryParams("test.cpp"))
        result = search.searchFileName(q, config).matches
        self.__assertTestFiles(testPath, result, ["data\\test.cpp"])

        print("\n================== NameSearch Test2 ==================")
        q = FileQuery (QueryParams("test"))
        result = search.searchFileName(q, config).matches
        exp = ["data\\Test.cpp", "data\\test"]
        self.__assertTestFiles(testPath, result, exp)

        print("\n================== NameSearch Test3 ==================")
        q = FileQuery (QueryParams("test*.*"))
        result = search.searchFileName(q, config).matches
        exp = ["data\\TEst2.c", "data\\Test.cpp", "data\\test", "data\\test1.c", "data\\tester.CP", "data\\tester3.c"]
        self.__assertTestFiles(testPath, result, exp)

        print("\n================== NameSearch Test4 ==================")
        q = FileQuery (QueryParams("test", "", ".")) # no extension
        result = search.searchFileName(q, config).matches
        exp = ["data\\test"]
        self.__assertTestFiles(testPath, result, exp)

        print("\n================== NameSearch Test5 ==================")
        q = FileQuery (QueryParams("tes")) # no match
        result = search.searchFileName(q, config).matches
        exp = []
        self.__assertTestFiles(testPath, result, exp)

        print("\n================== NameSearch Test6 ==================")
        q = FileQuery (QueryParams("*est?"))
        result = search.searchFileName(q, config).matches
        exp = ["data\\TEst2.c", "data\\test1.c"]
        self.__assertTestFiles(testPath, result, exp)

        print("\n================== NameSearch Test7 ==================")
        q = FileQuery (QueryParams("test*"))
        result = search.searchFileName(q, config).matches
        exp = ["data\\TEst2.c", "data\\Test.cpp", "data\\test", "data\\test1.c", "data\\tester.cp", "data\\tester3.c"]
        self.__assertTestFiles(testPath, result, exp)

        print("\n================== NameSearch Test8 ==================")
        q = FileQuery (QueryParams("test*", "", ".c*,-.cpp")) # .c* but no files with .cpp extension
        result = search.searchFileName(q, config).matches
        exp = ["data\\TEst2.c", "data\\test1.c", "data\\tester.cp", "data\\tester3.c"]
        self.__assertTestFiles(testPath, result, exp)

        print("\n================== NameSearch Test9 ==================")
        q = FileQuery (QueryParams("test*", "", ".cp*,-.c")) # .cp* but no files with .c extension / useless but most work
        result = search.searchFileName(q, config).matches
        exp = ["data\\Test.cpp", "data\\tester.cp"]
        self.__assertTestFiles(testPath, result, exp)

        print("\n================== NameSearch Test10 ==================")
        q = FileQuery (QueryParams("test*", "-test2,-tester?", ".c"))
        result = search.searchFileName(q, config).matches
        exp = ["data\\test1.c"]
        self.__assertTestFiles(testPath, result, exp)

        print("\n================== NameSearch Test11 ==================")
        q = FileQuery (QueryParams("test*", "er*,-e?3", ".c,.cp"))
        result = search.searchFileName(q, config).matches
        exp = ["data\\tester.cp"]
        self.__assertTestFiles(testPath, result, exp)

    def __testNameSearchCaseSensitive(self, testPath: str, config: IndexConfiguration) -> None:
        search = SearchMethods()

        print("\n================== NameSearch case insensitive Test1 ==================")
        q = FileQuery (QueryParams("TEst.cpp", bCaseSensitive=True))
        result = search.searchFileName(q, config).matches
        self.__assertTestFiles(testPath, result, [])

        print("\n================== NameSearch case insensitive Test2 ==================")
        q = FileQuery (QueryParams("Test.cpp", bCaseSensitive=True))
        result = search.searchFileName(q, config).matches
        self.__assertTestFiles(testPath, result, ["data\\Test.cpp"])

        print("\n================== NameSearch case insensitive Test3 ==================")
        q = FileQuery (QueryParams("T*", bCaseSensitive=True))
        result = search.searchFileName(q, config).matches
        self.__assertTestFiles(testPath, result, ["data\\TEst2.c", "data\\Test.cpp"])

        print("\n================== NameSearch case insensitive Test4 ==================")
        q = FileQuery (QueryParams("tester.cP", bCaseSensitive=True)) # extensions are not treated case sensitive
        result = search.searchFileName(q, config).matches
        self.__assertTestFiles(testPath, result, ["data\\tester.CP"])

        print("\n================== NameSearch case insensitive Test5 ==================")
        q = FileQuery (QueryParams("tester", ".cp", bCaseSensitive=True)) # extensions are not treated case sensitive
        result = search.searchFileName(q, config).matches
        self.__assertTestFiles(testPath, result, ["data\\tester.CP"])

        print("\n================== NameSearch case insensitive Test6 ==================")
        q = FileQuery (QueryParams("tester", ".cP", bCaseSensitive=True)) # extensions are not treated case sensitive
        result = search.searchFileName(q, config).matches
        self.__assertTestFiles(testPath, result, ["data\\tester.CP"])

        print("\n================== NameSearch case insensitive Test7 ==================")
        q = FileQuery (QueryParams("tester", "CP", bCaseSensitive=True)) # extensions are not treated case sensitive
        result = search.searchFileName(q, config).matches
        self.__assertTestFiles(testPath, result, ["data\\tester.CP"])

    def testContentSearch(self) -> None:
        testPath = os.getcwd()

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

        print("\n================== ContentSearch Test1 ==================")
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

        print("\n================== ContentSearch Test2 ==================")
        q = ContentQuery (QueryParams("conversion table"))
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\latin_1\ebcdic.c")]
        self.assertEqual (result, exp)

        print("\n================== ContentSearch Test3 ==================")
        q = ContentQuery (QueryParams("äöüß"))
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\utf16\utf16.txt"), os.path.join(testPath, r"data\utf8\utf8.txt")]
        self.assertEqual (result, exp)

        print("\n================== ContentSearch Test4 ==================")
        q = ContentQuery (QueryParams("dschungelbuch"))
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\test1.cpp"), os.path.join(testPath, r"data\test2.cxx")]
        self.assertEqual (result, exp)

        print("\n================== ContentSearch Test5 ==================")
        q = ContentQuery (QueryParams("BamBi"))
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\test2.cxx")]
        self.assertEqual (result, exp)

        print("\n================== ContentSearch Test6 ==================")
        q = ContentQuery (QueryParams("Tom & cherry"))
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\test3.c")]
        self.assertEqual (result, exp)

        print("\n================== ContentSearch Test6.1 ==================")
        q = ContentQuery (QueryParams("Whatever#"))
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\test1.cpp")]
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

        print("\n================== ContentSearch Test7 ==================")
        updateStats = UpdateStatistics()
        updater.updateIndex (config, updateStats)
        self.assertEqual(updateStats.nNew,  2)
        self.assertEqual(updateStats.nUpdated,  3)
        self.assertEqual(updateStats.nUnchanged,  2)
        stats = fti.queryStats()
        self.assertEqual (stats[0], 7)
        self.assertEqual (stats[1], 7)

        print("\n================== ContentSearch Test8 ==================")
        q = ContentQuery (QueryParams("conversion table"))
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\latin_1\ebcdic.c")]
        self.assertEqual (result, exp)

        print("\n================== ContentSearch Test9 ==================")
        q = ContentQuery (QueryParams("äöüß"))
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\utf16\utf16.txt"), os.path.join(testPath, r"data\utf8\utf8.txt")]
        self.assertEqual (result, exp)

        print("\n================== ContentSearch Test10 ==================")
        q = ContentQuery (QueryParams("DschungelbUch"))
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\test1.cpp"), os.path.join(testPath, r"data\test2.cxx"), os.path.join(testPath, r"data\utf16\utf16.txt")]
        self.assertEqual (result, exp)

        print("\n================== ContentSearch Test11 ==================")
        q = ContentQuery (QueryParams("Neuer Text"))
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\test1.cpp")]
        self.assertEqual (result, exp)

        print("\n================== ContentSearch Test12 ==================")
        q = ContentQuery (QueryParams("Bambi"))
        result = fti.searchContent(q)
        exp = []
        self.assertEqual (result, exp)

        print("\n================== ContentSearch Test13 ==================")
        q = ContentQuery (QueryParams("Tom & Cherry"))
        result = fti.searchContent(q)
        exp = []
        self.assertEqual (result, exp)

        print("\n================== ContentSearch Test14 ==================")
        q = ContentQuery (QueryParams("speedy gonzales"))
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\test4.c")]
        self.assertEqual (result, exp)

        print("\n================== ContentSearch Test15 ==================")
        # Test folder filter
        q = ContentQuery (QueryParams("Dschungelbuch",  "utf16"))
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\utf16\utf16.txt")]
        self.assertEqual (result, exp)

        print("\n================== ContentSearch Test16 ==================")
        # Test extension filter
        q = ContentQuery (QueryParams("Dschungelbuch",  "", "*.c*"))
        result = fti.searchContent(q)
        exp = [os.path.join(testPath, r"data\test1.cpp"), os.path.join(testPath, r"data\test2.cxx")]
        self.assertEqual (result, exp)

        print("\n================== ContentSearch Test17 ==================")
        # Test case sensitivity
        q = ContentQuery (QueryParams("speedy gonzales",  "", "",  True))
        result = fti.searchContent(q,)
        exp = []
        self.assertEqual (result, exp)

        print("\n================== ContentSearch Test18 ==================")
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

        print("\n================== ContentSearch Test19 ==================")
        # Test file search
        q2 = FileQuery(QueryParams("utf8.txt")) # test search specific file
        result = fti.searchFile(q2)
        exp = [os.path.join(testPath, r"data\utf8\utf8.txt")]
        self.assertEqual(exp, result)

        print("\n================== ContentSearch Test20 ==================")
        q2 = FileQuery(QueryParams("test*", "", "c??")) # test extension filter
        result = fti.searchFile(q2)
        exp = [os.path.join(testPath, r"data\test1.cpp"), os.path.join(testPath, r"data\test2.cxx")]
        self.assertEqual (result, exp)

        print("\n================== ContentSearch Test21 ==================")
        q2 = FileQuery(QueryParams("*", "latin_?", "c")) # test folder filter
        result = fti.searchFile(q2)
        exp = [os.path.join(testPath, r"data\latin_1\ebcdic.c")]
        self.assertEqual (result, exp)

        print("\n================== ContentSearch Test22 ==================")
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

    def testExcludedExtensions(self) -> None:
        """Test that excluded file extensions are correctly tracked in the database."""
        testPath = os.getcwd()
        testDb = "test-excluded.dat"
        testDir = "data_excluded"

        # Clean up from previous runs
        delFile(testDb)
        if os.path.exists(testDir):
            delDir(testDir)

        # Create test directory structure with various file types
        os.mkdir(testDir)

        # Create files with included extensions (.c, .cpp, .txt)
        with open(os.path.join(testDir, "source1.c"), "w") as f:
            f.write("int main() { return 0; }")
        with open(os.path.join(testDir, "source2.cpp"), "w") as f:
            f.write("int main() { return 0; }")
        with open(os.path.join(testDir, "readme.txt"), "w") as f:
            f.write("This is a readme file.")

        # Create files with excluded extensions
        # 3 .jpg files
        for i in range(1, 4):
            with open(os.path.join(testDir, f"image{i}.jpg"), "w") as f:
                f.write(f"fake image {i}")

        # 2 .png files
        for i in range(1, 3):
            with open(os.path.join(testDir, f"picture{i}.png"), "w") as f:
                f.write(f"fake picture {i}")

        # 1 .log file
        with open(os.path.join(testDir, "debug.log"), "w") as f:
            f.write("log data")

        # 1 file with no extension
        with open(os.path.join(testDir, "Makefile"), "w") as f:
            f.write("all: build")

        # 4 .xml files
        for i in range(1, 5):
            with open(os.path.join(testDir, f"config{i}.xml"), "w") as f:
                f.write(f"<config>{i}</config>")

        forAllFiles(testDir, setTime)

        print("\n================== Excluded Extensions Test1 ==================")
        # Create index configuration that only indexes .c, .cpp, .txt files
        config = IndexConfiguration("test", ".c,.cpp,.txt", os.path.join(testPath, testDir), indexdb=testDb)

        # Create updater and run index update
        updateStats = UpdateStatistics()
        updater = IndexUpdater(testDb)
        updater.updateIndex(config, updateStats)

        # Verify that 3 files were indexed (source1.c, source2.cpp, readme.txt)
        self.assertEqual(updateStats.nNew, 3)
        self.assertEqual(updateStats.nUpdated, 0)
        self.assertEqual(updateStats.nUnchanged, 0)

        print("\n================== Excluded Extensions Test2 ==================")
        # Use getExcludedExtensions to retrieve the data
        results = updater.getExcludedExtensions()

        # Convert to dictionary for easier verification
        excludedExts: dict[str, int] = {ext: count for ext, count in results}

        # Verify excluded extensions and counts
        self.assertEqual(len(excludedExts), 5)  # .jpg, .png, .log, .xml, and no extension
        self.assertEqual(excludedExts.get(""), 1)       # Makefile (no extension)
        self.assertEqual(excludedExts.get(".jpg"), 3)   # 3 jpg files
        self.assertEqual(excludedExts.get(".log"), 1)   # 1 log file
        self.assertEqual(excludedExts.get(".png"), 2)   # 2 png files
        self.assertEqual(excludedExts.get(".xml"), 4)   # 4 xml files

        print(f"Excluded extensions found: {excludedExts}")

        print("\n================== Excluded Extensions Test3 ==================")
        # Test that updating the index again doesn't duplicate excluded extensions
        # Add one more .jpg file
        with open(os.path.join(testDir, "image4.jpg"), "w") as f:
            f.write("fake image 4")
        setTime(os.path.join(testDir, "image4.jpg"))

        # Run update again
        updateStats2 = UpdateStatistics()
        updater.updateIndex(config, updateStats2)

        # Should have no new indexed files (only excluded files added)
        self.assertEqual(updateStats2.nNew, 0)
        self.assertEqual(updateStats2.nUpdated, 0)
        self.assertEqual(updateStats2.nUnchanged, 3)

        # Use getExcludedExtensions to retrieve the data from the new index run
        newResults = updater.getExcludedExtensions()
        newExcludedExts: dict[str, int] = {ext: count for ext, count in newResults}

        # Verify .jpg count increased to 4
        self.assertEqual(newExcludedExts.get(".jpg"), 4)
        self.assertEqual(newExcludedExts.get(".png"), 2)
        self.assertEqual(newExcludedExts.get(".log"), 1)
        self.assertEqual(newExcludedExts.get(".xml"), 4)
        self.assertEqual(newExcludedExts.get(""), 1)

        print(f"New excluded extensions found: {newExcludedExts}")

        print("\n================== Excluded Extensions Test4 ==================")
        # Test with no excluded files
        delDir(testDir)
        os.mkdir(testDir)

        # Create only files with included extensions
        with open(os.path.join(testDir, "test.c"), "w") as f:
            f.write("int x;")
        with open(os.path.join(testDir, "test.cpp"), "w") as f:
            f.write("int y;")

        forAllFiles(testDir, setTime)

        updateStats3 = UpdateStatistics()
        updater.updateIndex(config, updateStats3)

        # Verify files were indexed
        self.assertEqual(updateStats3.nNew, 2)

        # Use getExcludedExtensions - should return empty list
        finalResults = updater.getExcludedExtensions()
        self.assertEqual(len(finalResults), 0)  # No excluded extensions

        # Clean up
        delDir(testDir)
        delFile(testDb)

        print("All excluded extensions tests passed!")

if __name__ == "__main__":
    unittest.main()
