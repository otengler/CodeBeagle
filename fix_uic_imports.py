#!/usr/bin/env python3
"""Post-process a pyside2-uic generated file to use module-qualified imports."""
from __future__ import annotations
import re
import sys

# Symbols that come from QtCore
qtcore_symbols = {"Qt", "QMetaObject", "QCoreApplication", "QSize", "QPoint",
                  "QRect", "QUrl", "QString", "QVariant", "QEvent", "QByteArray",
                  "QDir", "QFile", "QFileInfo", "QIODevice", "QTextStream",
                  "QDateTime", "QDate", "QTimer", "QObject", "QThread"}

# Symbols that come from QtGui
qtgui_symbols = {"QIcon", "QPixmap", "QFont", "QKeySequence", "QColor",
                 "QBrush", "QRegExp", "QValidator", "QTextCursor",
                 "QTextCharFormat", "QTextFormat", "QMovie", "QPainter",
                 "QPalette", "QCursor", "QRegion", "QStandardItem",
                 "QStandardItemModel"}

def fix_file(path: str) -> None:
    with open(path, encoding="utf-8") as f:
        content = f.read()

    # Replace star imports with module imports
    content = re.sub(r"from PySide2\.QtCore import \*", "from PySide2 import QtCore, QtGui, QtWidgets", content)
    content = content.replace("from PySide2.QtGui import *", "")
    content = content.replace("from PySide2.QtWidgets import *", "")

    lines = content.split("\n")
    new_lines = []
    for line in lines:
        # Find word-like tokens that are Qt class names and prefix them
        # Only apply to lines inside methods (not import lines)
        if line.strip().startswith("from ") or line.strip().startswith("import "):
            new_lines.append(line)
            continue
        # Replace Qt.X -> QtCore.Qt.X (only whole words)
        line = re.sub(r'(?<![a-zA-Z_])Qt\.(?=[A-Za-z])', 'QtCore.Qt.', line)
        # Replace QtCore signal/string references - these may be dotted
        line = re.sub(r'(?<![a-zA-Z_])Signal\(', 'QtCore.Signal(', line)
        line = re.sub(r'(?<![a-zA-Z_])Slot\(', 'QtCore.Slot(', line)
        # For known QtGui classes, prefix with QtGui.
        for sym in qtgui_symbols:
            # Word boundary match
            line = re.sub(r'(?<![a-zA-Z_])' + re.escape(sym) + r'(?=\s*[\(\.])', 'QtGui.' + sym, line)
        # For known QtCore classes (except Qt which is already done), prefix with QtCore.
        for sym in qtcore_symbols - {"Qt"}:
            line = re.sub(r'(?<![a-zA-Z_])' + re.escape(sym) + r'(?=\s*[\(\.])', 'QtCore.' + sym, line)
        # For remaining capitalized words that look like Qt classes (matching Q[A-Z]), apply general logic
        # These are likely QtWidgets classes since QtCore/QtGui are covered
        def replace_qclass(m: re.Match[str]) -> str:
            word = m.group(0)
            if word.startswith("Q") and word not in qtcore_symbols and word not in qtgui_symbols and word not in {"QLine", "QStringList", "QRectF", "QPointF", "QSizeF"}:
                # Not matched by core/gui -> assume QtWidgets
                return "QtWidgets." + word
            return word
        line = re.sub(r'(?<![a-zA-Z_\.])(Q[A-Z][a-zA-Z0-9_]+)(?=\s*[\(\.])', replace_qclass, line)
        new_lines.append(line)

    content = "\n".join(new_lines)
    # Clean up multiple blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    for p in sys.argv[1:]:
        fix_file(p)
        print(f"Fixed: {p}")