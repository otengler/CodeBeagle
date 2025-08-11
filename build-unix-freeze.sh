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
  rm $BUILDDIR/lib/liblzma-004595ca.so.5.2.2
  rm $BUILDDIR/lib/libreadline-2c5f7b8d.so.6.2
  rm $BUILDDIR/lib/libffi-af4ed708.so.6.0.1
  rm $BUILDDIR/lib/libbz2-a273e504.so.1.0.6
  rm $BUILDDIR/lib/_bz2.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_codecs_kr.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_codecs_tw.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_posixshmem.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_codecs_jp.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_codecs_hk.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/fcntl.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/pyexpat.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_codecs_cn.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/grp.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_queue.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_heapq.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_blake2.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_ctypes.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_json.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_csv.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/readline.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_pickle.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_statistics.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_contextvars.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_multiprocessing.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_hashlib.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_decimal.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_bisect.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/termios.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/mmap.cpython-$PYVER-x86_64-linux-gnu.so
  rm $BUILDDIR/lib/_codecs_iso2022.cpython-$PYVER-x86_64-linux-gnu.so
  rm -r $BUILDDIR/lib/ctypes
  rm -r $BUILDDIR/lib/multiprocessing
  rm -r $BUILDDIR/lib/xml
  rm -r $BUILDDIR/lib/xmlrpc
  # PyQt
  rm -r $BUILDDIR/lib/PyQt5/Qt5/translations
  # Clean all files in lib from the other directories. They are duplicates
  SOURCE_LIB_DIR="$BUILDDIR/lib/PyQt5/Qt5/lib"
  PLUGIN_DIR="$BUILDDIR/lib/PyQt5/Qt5/plugins"
  # Ensure both directories exist
  if [[ ! -d "$SOURCE_LIB_DIR" || ! -d "$PLUGIN_DIR" ]]; then
    echo "Error: lib or plugins directory does not exist"
    exit 1
  fi
  # Get unique filenames from SOURCE_DIR
  find "$SOURCE_LIB_DIR" -type f -printf "%f\n" | sort -u | while read -r filename; do
    # Find and delete all matching filenames in TARGET_DIR
    find "$PLUGIN_DIR" -type f -name "$filename" -exec rm -f {} \;
  done  
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

mv $BUILDDIR build/CodeBeagle

chmod +x ./build/CodeBeagle/CodeBeagle
chmod +x ./build/CodeBeagle/UpdateIndex
