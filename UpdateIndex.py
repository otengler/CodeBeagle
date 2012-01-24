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
import sys
import Config
import FullTextIndex
import time
import logging
import cProfile
import IndexConfiguration

def taketime (name,  func, *args):
    t1 = time.clock()
    result = func(*args)
    t2 = time.clock()
    logging.info (name + " %3.2f min" % ((t2-t1)/60.0,))
    return result

def setupLogging (conf):
    try:
        log = conf.updateIndexLog
        logging.basicConfig(filename=log,  format='%(asctime)s %(message)s',  level=logging.INFO)
    except KeyError:
        logging.basicConfig(format='%(asctime)s %(message)s',  level=logging.INFO)
    
def updateIndexes(indexes):
    for config in indexes:
        if config.updateIndex:
            fti=FullTextIndex.FullTextIndex(config.indexdb)
            statistics = FullTextIndex.UpdateStatistics()
            taketime("Updating index took ",  fti.updateIndex,   config.directories,  config.extensions,  statistics)
            logging.info (statistics)

# Switch to application directory to be able to load the configuration even if we are 
# executed from a different working directory.
os.chdir(os.path.dirname(sys.argv[0]))

conf = Config.Config("config.txt")
setupLogging (conf)

indexes = IndexConfiguration.readConfig(conf)

license = """
CodeBeagle Copyright (C) 2011 Oliver Tengler
This program comes with ABSOLUTELY NO WARRANTY; 
This is free software, and you are welcome to redistribute it under certain conditions; 
"""
print (license)

if conf.value("profileUpdate", 0) != 0:
    cProfile.run("updateIndexes(indexes)")
else:
    updateIndexes(indexes)

