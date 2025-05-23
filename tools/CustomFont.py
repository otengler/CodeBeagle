from typing import Optional
import os
from PyQt5.QtGui import QFontDatabase, QFont

customFont: Optional[QFont] = None

def installCustomFont():
    fontDir = os.path.join("resources", "font")
    try:
        global customFont
        customFont = None
        for name in os.listdir(fontDir):
            fullPath = os.path.join(fontDir, name)
            if os.path.isfile(fullPath) and fullPath.lower().endswith(".ttf"):
                QFontDatabase.addApplicationFont(fullPath)
                customFont = os.path.splitext(name[0])
                break
    except:
        pass

def customLFontList():
    return customFont