from fulltextindex.FullTextIndex import FullTextIndex, FileQuery

fti = FullTextIndex("C:\\Users\\oliver\\AppData\\Local\\CodeBeagle\\New location.dat")

q = FileQuery("widget*", "opengl", "-.h")
r = fti.searchFile(q)
print(r)