from typing import Any

from pytide6 import Dialog, HBoxPanel, Label, VBoxLayout, W

from i2cc.app import App
from i2cc.gui_tools import XButton


class ShowDialog(Dialog):
    def __init__(self, values: list[Any]):
        super().__init__(None, windowTitle="Show", modal=True, css=App.css.UserPromptDialog)
        self.setLayout(
            VBoxLayout(
                [Label(str(v)) for v in values]
                + [
                    HBoxPanel(
                        [
                            W(stretch=1),
                            XButton("Ok", parent=self, on_clicked=self.close, auto_default=True),
                        ]
                    ),
                ]
            )
        )


def mk_show_func():
    def show_func(*vs: Any) -> None:
        ShowDialog(list(vs)).exec()

    return show_func
