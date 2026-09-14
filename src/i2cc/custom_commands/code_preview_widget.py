from qppte import QPythonPlainTextEdit


class CodePreviewWidget(QPythonPlainTextEdit):
    def __init__(self, style="default"):
        super().__init__(style=style)
        self.setStyleSheet("QTextEdit { font-family: 'Monospace'; }")
        self.setReadOnly(True)
