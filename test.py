import os, re
from fulltextindex.FullTextIndex import FullTextIndex, FileQuery
from typing import List, Tuple, Iterator, Iterable, Pattern, Any, Sized, Optional, Literal

# fti = FullTextIndex("C:\\Users\\oliver\\AppData\\Local\\CodeBeagle\\New location.dat")

# q = FullTextIndex.FileQuery("widget*", "opengl", "-.h")
# r = fti.searchFile(q)
# print(r)

cq = FileQuery("", "test", ".h,.c,.cpp")

def totime():
    cq.matchFolderAndExtensionFilter("test.cpp")

import timeit
print(timeit.timeit(totime))

# Orginal: 0.5057702