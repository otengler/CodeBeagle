#!/bin/bash

# 
# Update dependencies (for Sass) 
#
npm ci

#
# Set vars and Compile interface definitions
# 
. ./build-linux-vars.sh
./build-linux-ui.sh

#
# Run Cx_freeze
# 

rm -r -f build
$PYTHON setup.py build_exe 
echo Build done

BUILDDIR="build/"`ls build`
echo Build directory is $BUILDDIR
LIB=$BUILDDIR/lib

rm -r -f $LIB/qdarkstyle/qss
rm -r -f $LIB/qdarkstyle/rc
rm -r -f $LIB/qdarkstyle/svg
rm -f $LIB/qdarkstyle/style.qrc
rm -f $LIB/qdarkstyle/style.qss

mkdir -p $BUILDDIR/scripts
mkdir -p $BUILDDIR/config
cp config.txt $BUILDDIR
cp help.html $BUILDDIR
cp LICENSE $BUILDDIR
cp scripts/* $BUILDDIR/scripts/
cp config/* $BUILDDIR/config/

mv $BUILDDIR build/CodeBeagle
