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

set BUILDDIR=build/exe.win-amd64-3.8
set LIB=$BUILDDIR/lib
[ -d "build" ] rm -r build
# build with cx_freeze 6.4 to avoid false positives with VirusTotal
$PYTHON setup.py build_exe 

del /q $LIB/unicodedata.pyd

mkdir $LIB/PyQt5.new/Qt5/bin
mkdir $LIB/PyQt5.new/Qt5/plugins/imageformats
mkdir $LIB/PyQt5.new/Qt5/plugins/platforms
mkdir $LIB/PyQt5.new/Qt5/plugins/styles

copy $LIB/PyQt5/__init__.pyc $LIB/PyQt5.new 
copy $LIB/PyQt5/QtCore.pyd $LIB/PyQt5.new
copy $LIB/PyQt5/QtWidgets.pyd $LIB/PyQt5.new
copy $LIB/PyQt5/QtGui.pyd $LIB/PyQt5.new
copy $LIB/PyQt5/sip.cp38-win_amd64.pyd $LIB/PyQt5.new
copy $LIB/PyQt5/Qt5/bin/Qt5Core.dll $LIB/PyQt5.new/Qt5/bin/
copy $LIB/PyQt5/Qt5/bin/Qt5Widgets.dll $LIB/PyQt5.new/Qt5/bin/
copy $LIB/PyQt5/Qt5/bin/Qt5Gui.dll $LIB/PyQt5.new/Qt5/bin/
copy $LIB/PyQt5/Qt5/plugins/imageformats/qgif.dll $LIB/PyQt5.new/Qt5/plugins/imageformats/
copy $LIB/PyQt5/Qt5/plugins/platforms/qwindows.dll $LIB/PyQt5.new/Qt5/plugins/platforms/
copy $LIB/PyQt5/Qt5/plugins/styles/qwindowsvistastyle.dll $LIB/PyQt5.new/Qt5/plugins/styles/

rm -r /q /s $LIB/PyQt5
mv $LIB/PyQt5.new $LIB/PyQt5

rm -r /q /s $LIB/qdarkstyle/qss
rm -r /q /s $LIB/qdarkstyle/rc
rm -r /q /s $LIB/qdarkstyle/svg
rm /q $LIB/qdarkstyle/style.qrc
rm /q $LIB/qdarkstyle/style.qss

cp config.txt $BUILDDIR
cp help.html $BUILDDIR
cp LICENSE $BUILDDIR
cp scripts/* $BUILDDIR/scripts/
cp config/* $BUILDDIR/config/

mv $BUILDDIR build/CodeBeagle
