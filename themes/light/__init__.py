from typing import cast, TYPE_CHECKING
import pathlib, os

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QFile, QTextStream

def apply_stylesheet(app: 'QApplication') -> None:
    from PySide6.QtCore import QFile, QTextStream
    scriptDir = pathlib.Path(__file__).parent.resolve()
    qss_file = QFile(os.path.join(scriptDir, "style.qss"))
    qss_file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text)
    text_stream = QTextStream(qss_file)
    result = ""
    result = text_stream.readAll()
    
    app.setStyleSheet(result)