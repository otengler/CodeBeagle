from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QComboBox, QCompleter

class CaseSensitiveComboBox (QComboBox):
    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        completer = QCompleter()
        completer.setCaseSensitivity(Qt.CaseSensitive)
        self.setEditable(True)
        self.setCompleter(completer)
        