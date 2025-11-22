# -*- coding: utf-8 -*-

import AppConfig
from tools import FileTools
from fulltextindex import IndexConfiguration, FullTextIndex

# TODO: installations pfad aus _reg_clsid_\PythonCOMPath lesen und als Pfad für config.txt verwenden
#       bei installation pythoncom33.dll ins windows verzeichnis kopieren
#       als moegliche Server Typen nur inprocess angeben? Oder testen ob es mit der cx_freeze exe funktioniert

class CodeBeagleAutomation:
    _public_methods_ = ['search']
    _reg_clsid_ = "{DB31CA26-655B-4C5E-BE82-0D5D78A604F7}"
    _reg_desc_ = "CodeBeagle COM Automation"
    _reg_progid_ = "CodeBeagle.Search"

    # indexName = Name of configuration from global or user local config
    # The rest of the parameters are similar to the UI parameters.
    def search(self, indexName, searchPhrase, filterDirectories, filterExtensions, caseSensitive):

        indexName = indexName.lower()

        # Switch to application directory to be able to load the configuration even if we are
        # executed from a different working directory.
        FileTools.switchToAppDir()

        conf = AppConfig.appConfig()

        indexes = IndexConfiguration.readConfig(conf)
        # Build a map from index name to index database for those configuration which actually generate an index
        indexMap = dict((conf.indexName.lower(), conf.indexdb) for conf in indexes if conf.isContentIndexed())

        if not indexName in indexMap:
            return []

        queryParams = FullTextIndex.QueryParams(searchPhrase, filterDirectories, filterExtensions, caseSensitive)
        query = FullTextIndex.ContentQuery(queryParams)

        fti = FullTextIndex.FullTextIndex(indexMap[indexName])

        return fti.searchContent(query)

if __name__== '__main__':
    import win32com.server.register
    win32com.server.register.UseCommandLine(CodeBeagleAutomation)

#import pythoncom
#print (pythoncom.CreateGuid())
#o = win32com.client.Dispatch("Python.ComServerTest")
