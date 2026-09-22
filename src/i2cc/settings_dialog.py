from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication
from pytide6 import CheckBox, ComboBox, Dialog, HBoxPanel, Label, PushButton, VBoxLayout, W
from qppte import DEFAULT_STYLES
from sprats.collections import Variable

from i2cc.app import App


class SettingDialog(Dialog):
    def __init__(
        self,
        app: App,
    ):
        super().__init__(app.main_window, windowTitle="Settings", modal=True)

        font_families = QFontDatabase.families()
        fixed_font_families = [f for f in font_families if QFontDatabase.isFixedPitch(f)]

        from typing import Callable

        self.apply_functions: dict[str, Callable[[], None]] = dict()

        def mk_set_font_family(key: str) -> Callable[[str | None], None]:
            def set_font_family(font_name: str | None) -> None:
                def _set():
                    assert font_name is not None
                    app.persistence.config.set_by_xpath(key, font_name)
                    if key == "/global_appearance/font_family":
                        app.q_application.setFont(QFont(font_name, QApplication.font().pointSize()))
                    if key == "/code_appearance/font_family":
                        app.update_code_font()

                self.apply_functions[key] = _set

            return set_font_family

        def mk_set_font_size(key: str) -> Callable[[int | None], None]:
            def set_font_size(font_size: int | None) -> None:
                def _set():
                    assert font_size is not None
                    app.persistence.config.set_by_xpath(key, font_size)
                    if key == "/global_appearance/font_size":
                        font = app.q_application.font()
                        font.setPointSize(font_size)
                        app.q_application.setFont(font)
                    elif key == "/code_appearance/font_size":
                        app.update_code_font()

                self.apply_functions[key] = _set

            return set_font_size

        def set_syntax_highlight(value: bool | None) -> None:
            def _set():
                assert value is not None
                app.persistence.config.set_by_xpath("/code_appearance/syntax_highlight", value)
                app.toggle_syntax_highlighting(value)

            self.apply_functions["/code_appearance/syntax_highlight"] = _set

        def set_syntax_highlight_style(style: str | None) -> None:
            def _set():
                assert style is not None
                app.persistence.config.set_by_xpath("/code_appearance/syntax_highlight_style", style)
                app.set_syntax_highlighting_style(style)

            self.apply_functions["/code_appearance/syntax_highlight"] = _set

        application_font_family: Variable[str] = Variable(
            app.q_application.font().family(),
            valid_values=font_families,
            on_value_change=mk_set_font_family("/global_appearance/font_family"),
        )
        application_font_size = Variable(
            app.q_application.font().pointSize(),
            valid_values=list(range(9, 30)),
            on_value_change=mk_set_font_size("/global_appearance/font_size"),
        )

        code_font_family: Variable[str] = Variable(
            app.persistence.config.get_by_xpath("/code_appearance/font_family", str),
            valid_values=fixed_font_families,
            on_value_change=mk_set_font_family("/code_appearance/font_family"),
        )
        code_font_size = Variable(
            app.persistence.config.get_by_xpath("/code_appearance/font_size", int),
            valid_values=list(range(9, 30)),
            on_value_change=mk_set_font_size("/code_appearance/font_size"),
        )
        code_syntax_highlight = Variable(
            app.persistence.config.get_by_xpath("/code_appearance/syntax_highlight", bool),
            on_value_change=set_syntax_highlight,
        )

        code_syntax_highlight_style = Variable(
            app.persistence.config.get_by_xpath("/code_appearance/syntax_highlight_style", str),
            valid_values=list(DEFAULT_STYLES.keys()),
            on_value_change=set_syntax_highlight_style,
        )

        self.setLayout(
            VBoxLayout(
                [
                    HBoxPanel(
                        [
                            Label("Application font"),
                            ComboBox(reactive_variable=application_font_family),
                            ComboBox(reactive_variable=application_font_size),
                            W(stretch=1),
                        ]
                    ),
                    HBoxPanel(
                        [
                            Label("Code editor font"),
                            ComboBox(reactive_variable=code_font_family),
                            ComboBox(reactive_variable=code_font_size),
                            W(stretch=1),
                        ]
                    ),
                    HBoxPanel(
                        [
                            Label("Code syntax highlight"),
                            CheckBox(reactive_variable=code_syntax_highlight),
                            W(stretch=1),
                        ]
                    ),
                    HBoxPanel(
                        [
                            Label("Code highlight style"),
                            ComboBox(reactive_variable=code_syntax_highlight_style),
                            W(stretch=1),
                        ]
                    ),
                    HBoxPanel(
                        [
                            W(stretch=1),
                            PushButton("Ok", on_clicked=self.ok, auto_default=False),
                            PushButton("Cancel", on_clicked=self.close, auto_default=False),
                        ]
                    ),
                ]
            )
        )

    def ok(self):
        for f in self.apply_functions:
            self.apply_functions[f]()
        self.close()
