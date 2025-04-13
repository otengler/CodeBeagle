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

cp CodeBeagle.pyw CodeBeagle.py
$PYTHON setup.py build_exe 
echo Build done

BUILDDIR="build/"`ls build`
echo Build directory is $BUILDDIR
LIB=$BUILDDIR/lib

rm -r -f $LIB/themes/dark/qss
rm -r -f $LIB/themes/dark/svg

mkdir -p $BUILDDIR/scripts
mkdir -p $BUILDDIR/config
cp config.txt $BUILDDIR
cp help.html $BUILDDIR
cp LICENSE $BUILDDIR
cp scripts/* $BUILDDIR/scripts/
cp config/* $BUILDDIR/config/
cp resources/* $BUILDDIR/resources/

mv $BUILDDIR build/CodeBeagle
