import dataclasses
import traceback
from collections.abc import Callable

from PySide6 import QtCore
from PySide6.QtGui import QKeyEvent, Qt
from PySide6.QtWidgets import QTextEdit
from pytide6 import Dialog, HBoxPanel, PushButton, VBoxLayout, W
from pytide6.frame import HorizonalLine
from pytide6.inputs import LineEdit
from sprats.collections import Variable

from i2cc.app import App
from i2cc.custom_commands.find_register_dialog import FindRegisterDialog
from i2cc.project.project import CustomCommand


class CodeEditor(QTextEdit):
    space_key_event = QKeyEvent(QtCore.QEvent.Type.KeyPress, Qt.Key.Key_A, QtCore.Qt.KeyboardModifier.NoModifier, " ")

    def __init__(self, app: App, save_command: Callable[[], None]):
        super().__init__()
        self.app = app
        self.save_command = save_command
        self.setStyleSheet("QTextEdit { font-family: 'Monospace'; }")
        char_width = self.fontMetrics().height()
        self.setMinimumHeight(char_width * 25)

    def keyPressEvent(self, event: QKeyEvent, /) -> None:
        key = event.key()
        if event.type() == QtCore.QEvent.Type.KeyPress:
            if key == Qt.Key.Key_Tab:
                super().keyPressEvent(CodeEditor.space_key_event)
                super().keyPressEvent(CodeEditor.space_key_event)
                super().keyPressEvent(CodeEditor.space_key_event)
                super().keyPressEvent(CodeEditor.space_key_event)
                return

            if (
                key in [Qt.Key.Key_Enter, Qt.Key.Key_Return]
                and event.modifiers() == Qt.KeyboardModifier.ControlModifier
            ):
                self.save_command()
                return

        super().keyPressEvent(event)

        if key == Qt.Key.Key_Period and self.textCursor().block().text()[0 : self.textCursor().columnNumber()].endswith(
            "dut."
        ):
            # show popup selector for registers and fields
            pos = self.cursorRect().topLeft()
            pos = self.viewport().mapToGlobal(pos)
            dialog = FindRegisterDialog(self, self.app, self.insertPlainText)
            dialog.move(pos)
            dialog.exec()


class CustomCommandsEditor(Dialog):
    def __init__(self, app: App, cmd: CustomCommand | None):
        super().__init__(app.main_window, windowTitle="Edit/Create Custom Command", modal=True)
        self.app = app
        self.original_cmd = None if cmd is None else dataclasses.replace(cmd)

        self.command_label = Variable("" if cmd is None else cmd.label)
        self.code_editor = CodeEditor(app, self.save_command)
        if cmd is not None:
            self.code_editor.append(cmd.source_code)

        self.setLayout(
            VBoxLayout(
                [
                    LineEdit(
                        reactive_variable=self.command_label,
                        with_min_width_for_text=(" " * 200),
                        on_key_enter=lambda _: self.code_editor.setFocus(),
                    ),
                    W(self.code_editor, stretch=1),
                    HorizonalLine(),
                    HBoxPanel(
                        [
                            W(stretch=1),
                            PushButton("Ok", on_clicked=self.save_command, auto_default=False),
                            PushButton("Cancel", on_clicked=self.close, auto_default=False),
                        ],
                        margins=0,
                    ),
                ]
            )
        )

    def save_command(self):
        code = self.code_editor.toPlainText()
        try:
            command_label = self.command_label.value.strip()
            if command_label == "":
                self.app.show_error("Command must have a label.")
                return

            if (
                self.original_cmd is None
                or (self.original_cmd is not None and command_label != self.original_cmd.label)
            ) and command_label in self.app.project.commands_by_label:
                self.app.show_error("Command with this name already exist. Please pick another name.")
                return

            new_cmd = CustomCommand(
                label=command_label,
                source_code=code,
                compiled_code=compile(code, "<str>", "exec"),
            )
            if self.original_cmd is None:
                self.app.project.add_custom_command(new_cmd)
            else:
                self.app.project.update_custom_command(self.original_cmd, new_cmd)

            self.close()
            self.app.request_commands_reload(True)  # True requests to keep current selection
        except Exception as ex:
            tb_lines = traceback.format_exception(type(ex), ex, ex.__traceback__)
            x = "".join(tb_lines[2:])
            self.app.show_error(str(x))
