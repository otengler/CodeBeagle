import os
from PyQt5.QtGui import QFontDatabase

def installCustomFont():
    fontDir = os.path.join("resources", "font")
    try:
        for name in os.listdir(fontDir):
            fullPath = os.path.join(fontDir, name)
            if os.path.isfile(fullPath) and fullPath.lower().endswith(".ttf"):
                QFontDatabase.addApplicationFont(fullPath)
    except:
        pass