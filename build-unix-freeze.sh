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
  PYVER=`python3 build-GetPyVer.py`
  # Keep the following modules: they are imported by the MCP server
  # (CodeBeagleMCP) via pydantic/mcp: decimal, queue, multiprocessing, bz2, lzma
  rm $BUILDDIR/lib/libreadline-2c5f7b8d.so.6.2
  rm $BUILDDIR/lib/libffi-af4ed708.so.6.0.1
  rm $BUILDDIR/lib/_codecs_iso2022.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_posixshmem.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/fcntl.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/pyexpat.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/grp.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_heapq.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_ctypes.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_json.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_csv.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/readline.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_pickle.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_statistics.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_bisect.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/termios.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/mmap.cpython-$PYVER-x86_64-linux-gnu.so
  # PySide6/Qt parts not needed for the Linux distribution
  rm -r $BUILDDIR/share \
    $BUILDDIR/lib/PySide6/QtNetwork.abi3.so \
    $BUILDDIR/lib/PySide6/Qt/translations \
    $BUILDDIR/lib/PySide6/Qt/plugins/{iconengines,tls,egldeviceintegrations,networkinformation,platforminputcontexts} \
    $BUILDDIR/lib/PySide6/Qt/lib/libQt6{EglFSDeviceIntegration,QmlWorkerScript,OpenGL,Quick,VirtualKeyboard,EglFsKmsSupport}.so.6 \
    $BUILDDIR/lib/PySide6/Qt/lib/libQt6{QmlMeta,WaylandEglCompositorHwIntegration,VirtualKeyboardQml,Qml,Pdf,QmlModels,Network}.so.6 \
    $BUILDDIR/lib/PySide6/Qt/plugins/platforms/libq{minimal,linuxfb,vkkhrdisplay,minimalegl,eglfs,vnc}.so \
    $BUILDDIR/lib/PySide6/Qt/plugins/imageformats/libq{icns,pdf,wbmp,tiff,jpeg,ico,tga,svg,webp}.so
    
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
mkdir -p $BUILDDIR/scripts && cp scripts/* $BUILDDIR/scripts/
mkdir -p $BUILDDIR/config && cp config/* $BUILDDIR/config/
mkdir -p $BUILDDIR/resources && cp -r resources/* $BUILDDIR/resources/
# ai_agent start
mkdir -p $BUILDDIR/resources/ai_agent && cp -r ai_agent/resources/* $BUILDDIR/resources/

mv $BUILDDIR build/CodeBeagle

chmod +x ./build/CodeBeagle/CodeBeagle
chmod +x ./build/CodeBeagle/UpdateIndex
