from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QFile, QTextStream

from qlightstyle import style_rc

def apply_stylesheet(app: QApplication) -> None:
    qss_file = QFile(":qlightstyle/style.qss")
    qss_file.open(QFile.ReadOnly | QFile.Text)
    text_stream = QTextStream(qss_file)
    result = ""
    result = text_stream.readAll()
    
    app.setStyleSheet(result)