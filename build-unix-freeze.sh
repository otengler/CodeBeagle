#!/bin/bash

# 
# Update dependencies (for Sass) 
#
npm ci

#
# Set vars and Compile interface definitions
# 
. ./build-unix-vars.sh
./build-unix-ui.sh

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

if [ "$1" == "linux" ]; then
  echo "Cleanup Linux"
fi
if [ "$1" == "mac" ]; then
  echo "Cleanup MAC"
fi

rm -r -f $LIB/themes/dark/qss
rm -r -f $LIB/themes/dark/svg

cp config.txt $BUILDDIR
cp help.html $BUILDDIR
cp LICENSE $BUILDDIR
cp VERSION $BUILDDIR
cp install.sh $BUILDDIR
mkdir -p $BUILDDIR/scripts && cp scripts/* $BUILDDIR/scripts/
mkdir -p $BUILDDIR/config && cp config/* $BUILDDIR/config/
mkdir -p $BUILDDIR/resources && cp -r resources/* $BUILDDIR/resources/

chmod +x $BUILDDIR/CodeBeagle
chmod +x $BUILDDIR/UpdateIndex
chmod +x $BUILDDIR/install.sh

mv $BUILDDIR build/CodeBeagle
