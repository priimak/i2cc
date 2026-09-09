from PySide6.QtWidgets import QTextEdit


class CodePreviewWidget(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("QTextEdit { font-family: 'Monospace'; }")
        self.setReadOnly(True)
