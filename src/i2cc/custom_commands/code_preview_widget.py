from PySide6.QtGui import QFont
from qppte import QPythonPlainTextEdit

from i2cc.app import App


class CodePreviewWidget(QPythonPlainTextEdit):
    def __init__(self, app: App):
        super().__init__(
            enableSyntaxHighlighting=app.persistence.config.get_by_xpath("/code_appearance/syntax_highlight", bool),
            highlightStyle=app.persistence.config.get_by_xpath("/code_appearance/syntax_highlight_style", str),
            font=QFont(
                app.persistence.config.get_by_xpath("/code_appearance/font_family", str),
                app.persistence.config.get_by_xpath("/code_appearance/font_size", int),
            ),
        )
        self.setReadOnly(True)

        app.update_code_font = lambda: self.setFont(
            QFont(
                app.persistence.config.get_by_xpath("/code_appearance/font_family", str),
                app.persistence.config.get_by_xpath("/code_appearance/font_size", int),
            )
        )
        app.set_syntax_highlighting_style = self.setHighlightStyle
        app.toggle_syntax_highlighting = self.setEnableSyntaxHighlighting
