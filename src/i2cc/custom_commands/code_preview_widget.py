from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QTextEdit


class CodePreviewWidget(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("QTextEdit { font-family: 'Monospace'; }")

    def keyPressEvent(self, event: QKeyEvent, /) -> None:
        # suppress all keys
        pass
