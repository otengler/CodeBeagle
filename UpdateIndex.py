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
import argparse
import time
import logging
import cProfile
import FileTools
import IndexConfiguration
import AppConfig
import FullTextIndex

license = """
CodeBeagle Copyright (C) 2011-2012 Oliver Tengler;
This program comes with ABSOLUTELY NO WARRANTY; 
This is free software, and you are welcome to redistribute it under certain conditions; 
"""

updateIndexDescription ="""Utility to update indexes for CodeBeagle. By default those indexes defined in config.txt are updated"""
helpJobMode = """This mode is used by CodeBeagle to update indexes in the background. It reads job files from the given directory"""
helpConfig="""Full path to config file. This parameter allows to specify an additional config file beside the default config.txt. Can be specified more than once."""

parser = argparse.ArgumentParser(description=updateIndexDescription,  epilog=license)
parser.add_argument("-v", "--version", action='version', version="UpdateIndex " + AppConfig.appVersion)
parser.add_argument("--jobmode",  metavar='DIR', type=str, help=helpJobMode)
parser.add_argument("-c", "--config",  action="append",  default=[AppConfig.configName],  type=str,  help=helpConfig)

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
    except AttributeError:
        logging.basicConfig(format='%(asctime)s %(message)s',  level=logging.INFO)
    
def updateIndex (config):
    fti=FullTextIndex.FullTextIndex(config.indexdb)
    statistics = FullTextIndex.UpdateStatistics()
    taketime("Updating index took ",  fti.updateIndex,   config.directories,  config.extensions,  config.dirExcludes, statistics)
    logging.info (statistics)
    
def updateIndexes(indexes):
    for config in indexes:
        if config.generateIndex:
            updateIndex (config)

def loadConfigFiles (args):
    configFiles = args.config
    if not configFiles:
        configFiles = [AppConfig.configName]
    conf = AppConfig.configFromFile (configFiles[0])
    configFiles = configFiles[1:]
    for name in configFiles:
        print ("Load config " + name)
        conf.loadFile(name)
    return conf

def handleUpdateJobs (indexes,  jobDir):
    configByName = {}
    for conf in indexes:
        configByName[conf.displayName().lower()] = conf
        
    while True:
        jobData = nextJob(jobDir)
        if not jobData:
            break
        index, jobFile = jobData
        logging.info ("Handle job '" + index + "'")
        try:
            conf = configByName[index.lower()]
            updateIndex (conf)
        except KeyError:
            logging.warning("No index for this job found")
        finally:
            os.unlink(jobFile)
    
def nextJob (jobDir):
    files = os.listdir(jobDir)
    if not files:
        return None
    for file in files:
        if not file.endswith(".running"):
            jobFile = os.path.join(jobDir, files[0])
            jobFileRunning = jobFile + ".running"
            os.rename(jobFile,  jobFileRunning)
            return (file,  jobFileRunning)
    return None

# Parse command line
args = parser.parse_args()

# Switch to application directory to be able to load the configuration even if we are 
# executed from a different working directory.
FileTools.switchToAppDir()

conf = loadConfigFiles (args)
indexes = IndexConfiguration.readConfig(conf)

if args.jobmode:
    runGuardDir = os.path.join(FileTools.getTempPath (), "UpdateIndex_running")
    while True:
        with FileTools.lockDir(runGuardDir):
            setupLogging (conf)
            logging.info ("UpdateIndex watches directory '" + args.jobmode + "'")
            handleUpdateJobs (indexes,  args.jobmode)
        if not nextJob (args.jobmode):
            logging.info ("No more jobs found")
            break
else:
    setupLogging (conf)
    if conf.profileUpdate:
        cProfile.run("updateIndexes(indexes)")
    else:
        updateIndexes(indexes)

# Synchronization in slave mode between UI and UpdateIndex:
#
# UI: 
# Write job file
# Launch UpdateIndex process
#
# UpdateIndex:
# Write run guard (1)
#    If it already exists bailout
# For each job file:
#    read job
#    update index
#    delete job file
# Delete run guard
# New jobs available?
#    If yes jump to (1)
#
# This should guarantee that every job is processed by UpdateIndex without the UI caring much if there is already an UpdateIndex running and
# in which state it currently is.

