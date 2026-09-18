from qppte import QPythonPlainTextEdit


class CodePreviewWidget(QPythonPlainTextEdit):
    def __init__(self, style="light_bold"):
        super().__init__(highlightStyle=style)
        self.setStyleSheet("QTextEdit { font-family: 'Monospace'; }")
        self.setReadOnly(True)
