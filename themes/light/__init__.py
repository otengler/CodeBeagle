from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QFile, QTextStream
import pathlib, os

def apply_stylesheet(app: QApplication) -> None:
    scriptDir = pathlib.Path(__file__).parent.resolve()
    qss_file = QFile(os.path.join(scriptDir, "style.qss"))
    qss_file.open(QFile.ReadOnly | QFile.Text)
    text_stream = QTextStream(qss_file)
    result = ""
    result = text_stream.readAll()
    
    app.setStyleSheet(result)