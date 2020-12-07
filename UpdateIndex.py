#! /usr/bin/python3
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
from typing import List, Callable, Any, Optional, Tuple
import argparse
import time
import logging
import cProfile
from tools import FileTools
from tools.Config import Config
from tools.ExceptionTools import exceptionAsString
from fulltextindex import IndexConfiguration
from fulltextindex.IndexUpdater import IndexUpdater, UpdateStatistics
import AppConfig

codebeagleLicense = """
CodeBeagle Copyright (C) 2011-2017 Oliver Tengler;
This program comes with ABSOLUTELY NO WARRANTY; 
This is free software, and you are welcome to redistribute it under certain conditions; 
"""

updateIndexDescription = """Utility to update indexes for CodeBeagle. By default those indexes defined in config.txt are updated"""
helpJobMode = """This mode is used by CodeBeagle to update indexes in the background. It reads job files from the given directory"""
helpConfig = """Full path to config file. This parameter allows to specify an additional config file beside the default config.txt. Can be specified more than once."""

parser = argparse.ArgumentParser(description=updateIndexDescription, epilog=codebeagleLicense)
parser.add_argument("-v", "--version", action='version', version="UpdateIndex " + AppConfig.appVersion)
parser.add_argument("--jobmode", metavar='DIR', type=str, help=helpJobMode)
parser.add_argument("-c", "--config", action="append", default=[AppConfig.configName], type=str, help=helpConfig)

def taketime(name: str, func: Callable, *args: Any) -> Any:
    t1 = time.perf_counter()
    result = func(*args)
    t2 = time.perf_counter()
    logging.info("%s %3.2f min", name, (t2-t1)/60.0)
    return result

def setupLogging(conf: Config) -> None:
    try:
        log = conf.updateIndexLog
        logging.basicConfig(filename=log, format='%(asctime)s %(message)s', level=logging.INFO)
    except AttributeError:
        logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

def updateIndex(config: IndexConfiguration.IndexConfiguration) -> None:
    logging.info("-"*80)
    logging.info("Updating index '%s'", config.indexName)
    try:
        fti = IndexUpdater(config.indexdb)
        statistics = UpdateStatistics()
        taketime("Updating index took ", fti.updateIndex, config, statistics)
        logging.info("%s", statistics)
    except:
        logging.error("Exception caught while updating index:\n%s", exceptionAsString(None))

def updateIndexes(indexes: List[IndexConfiguration.IndexConfiguration]) -> None:
    for config in indexes:
        if config.indexUpdateMode == IndexConfiguration.IndexMode.TriggeredIndexUpdate:
            updateIndex(config)

def loadConfigFiles(args: Any) -> Config:
    configFiles = args.config
    if not configFiles:
        configFiles = [AppConfig.configName]
    conf = AppConfig.configFromFile(configFiles[0])
    configFiles = configFiles[1:]
    for name in configFiles:
        print("Load config " + name)
        conf.loadFile(name)
    # managedConfig is an override for the config file maintained by
    # CodeBeagle. Normally this file is stored in the user profile.
    # Because UpdateIndex.exe runs with a high probability from a
    # scheduled task we cannot pull in files from the user profile because
    # we don't know the user. But if there is an override it makes
    # sense to include the managed config.
    if conf.managedConfig:
        print("Load config " + conf.managedConfig)
        conf.loadFile(conf.managedConfig)
    return conf

def handleUpdateJobs(indexes: List[IndexConfiguration.IndexConfiguration], jobDir: str) -> None:
    configByName = {}
    for conf in indexes:
        configByName[FileTools.removeInvalidFileChars(conf.displayName().lower())] = conf

    while True:
        jobData = nextJob(jobDir)
        if not jobData:
            break
        index, jobFile = jobData
        logging.info("Handle job '%s'", index)
        try:
            conf = configByName[index.lower()]
            updateIndex(conf)
        except KeyError:
            logging.warning("No index for this job found")
        finally:
            os.unlink(jobFile)

def nextJob(jobDir: str) -> Optional[Tuple[str, str]]:
    files = os.listdir(jobDir)
    if not files:
        return None
    for file in files:
        if not file.endswith(".running"):
            jobFile = os.path.join(jobDir, file)
            jobFileRunning = jobFile + ".running"
            os.rename(jobFile, jobFileRunning)
            return (file, jobFileRunning)
    return None

def handleUncleanShutdown(jobDir: str, removeTriggerFiles: bool) -> None:
    pidfile, bStaleFileWasRemoved = getPidFile()
    if bStaleFileWasRemoved:
        # This writes the current PID and make sure the file is removed at the end
        with pidfile:
            cleanupCrash(jobDir, removeTriggerFiles)

def removeFile(name: str) -> None:
    try:
        os.unlink(name)
    except:
        pass

# Cleans up stuff left behind from a crash
def cleanupCrash(jobDir: str, removeTriggerFiles: bool = False) -> None:
    guarddir = os.path.join(FileTools.getTempPath(), "UpdateIndex_running")
    if os.path.isdir(guarddir):
        try:
            os.rmdir(guarddir)
        except:
            pass

    if jobDir:
        files = os.listdir(jobDir)
        for file in files:        
            if file.endswith(".running"):
                jobFile = os.path.join(jobDir, file)            
                removeFile(jobFile)
            # This is the branch when UpdateIndex is not started in job mode. We want to get rid of job files then.
            elif removeTriggerFiles:
                triggerFile = os.path.join(jobDir, file)            
                removeFile(triggerFile)

# Returns touple (pidfile, bStaleFileWasRemoved)
def getPidFile() -> Tuple[FileTools.PidFile, bool]:
    pidname = os.path.join(FileTools.getTempPath(), "codebeagle.pid")
    pidfile = FileTools.PidFile(pidname)
    bStaleFileWasRemoved = False

    if pidfile.exists():
        pid = pidfile.read()
        if pid and FileTools.isProcessAlive(pid):
            print("Update index process with PID %u is already running" % pid)
        else:
            print("Found a stale PID file for process %u - cleaning up data" % pid)
            pidfile.remove()
            bStaleFileWasRemoved = True

    return (pidfile, bStaleFileWasRemoved)

def main() -> None:
    # Parse command line
    args = parser.parse_args()

    pidfile, _ = getPidFile()

    # This writes the current PID and make sure the file is removed at the end
    with pidfile:
        cleanupCrash(args.jobmode)

        # Switch to application directory to be able to load the configuration even if we are
        # executed from a different working directory.
        FileTools.switchToAppDir()

        conf = loadConfigFiles(args)
        indexes = IndexConfiguration.readConfig(conf)

        if args.jobmode:
            runGuardDir = os.path.join(FileTools.getTempPath(), "UpdateIndex_running")
            while True:
                with FileTools.LockDir(runGuardDir):
                    setupLogging(conf)
                    logging.info("UpdateIndex watches directory '%s'", args.jobmode)
                    handleUpdateJobs(indexes, args.jobmode)
                if not nextJob(args.jobmode):
                    logging.info("No more jobs found")
                    break
        else:
            setupLogging(conf)
            if conf.profileUpdate:
                cProfile.run("updateIndexes(indexes)")
            else:
                updateIndexes(indexes)

if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except:
        print("Exception caught while updating index:\n%s" % exceptionAsString(None))
        sys.exit(1)

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
# This should guarantee that every job is processed by UpdateIndex without the
# UI caring much if there is already an UpdateIndex running and in which state
# it currently is.
