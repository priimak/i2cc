import dataclasses
import re
import sys
import traceback
from collections.abc import Callable
from typing import Any, override

from PySide6 import QtCore
from PySide6.QtCore import QModelIndex, QPersistentModelIndex
from PySide6.QtGui import QCloseEvent, QFont, QKeyEvent, Qt
from pytide6 import Dialog, HBoxPanel, Label, PushButton, VBoxLayout, W
from pytide6.frame import HorizonalLine
from pytide6.inputs import LineEdit
from qppte import QPythonPlainTextEdit
from sprats.collections import Variable

from i2cc.app import App
from i2cc.custom_commands.find_register_dialog import FindRegisterDialog
from i2cc.gui_tools import (
    ListTableView,
    TableModelAllSelectableAndEnabled,
    TableModelWithFilterAction,
    TableModelWithOneColumn,
)
from i2cc.project.project import CustomCommand

COMMENT_REGEX = re.compile(r"^(\s*)#\s?")
NO_COMMENT_REGEX = re.compile(r"^(\s*)")


class CodeEditor(QPythonPlainTextEdit):
    space_key_event = QKeyEvent(QtCore.QEvent.Type.KeyPress, Qt.Key.Key_A, QtCore.Qt.KeyboardModifier.NoModifier, " ")

    def __init__(self, app: App, save_command: Callable[[], None]):
        super().__init__(
            enableSyntaxHighlighting=app.persistence.config.get_by_xpath("/code_appearance/syntax_highlight", bool),
            highlightStyle=app.persistence.config.get_by_xpath("/code_appearance/syntax_highlight_style", str),
            font=QFont(
                app.persistence.config.get_by_xpath("/code_appearance/font_family", str),
                app.persistence.config.get_by_xpath("/code_appearance/font_size", int),
            ),
        )

        self.app = app
        self.save_command = save_command
        char_width = self.fontMetrics().height()
        self.setMinimumHeight(char_width * 25)

    @override
    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if event.type() == QtCore.QEvent.Type.KeyPress:
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


class HistoryTableModel(TableModelWithOneColumn, TableModelAllSelectableAndEnabled, TableModelWithFilterAction):
    def __init__(self, app: App, points_in_time: list[str]):
        super().__init__()
        self.app = app
        self.points_in_time = points_in_time

    def headerData(self, section, orientation, /, role=...) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            return None
        else:
            return super().headerData(section, orientation, role)

    def rowCount(self, /, parent: QModelIndex | QPersistentModelIndex = ...) -> int:
        return len(self.points_in_time)

    def data(self, index: QModelIndex | QPersistentModelIndex, /, role: int = ...) -> Any:
        if index.isValid() and role == Qt.ItemDataRole.DisplayRole:
            return self.points_in_time[index.row()]
        else:
            return None


class HistoryDialog(Dialog):
    def __init__(self, parent, app: App, command_name: str, history: list[tuple[int, str]]):
        super().__init__(parent, windowTitle=f"History for [{command_name}]", modal=True)

        self.cce: CustomCommandsEditor = parent
        self.saved_code = self.cce.code_editor.toPlainText()

        def preview_historical_code(timestamp: str):
            if timestamp == "current":
                self.cce.code_editor.setPlainText(self.saved_code)
            else:
                id = [p[0] for p in history if p[1] == timestamp]
                if len(id) == 1:
                    name_and_code = app.project.commands_history.get_command(command_name, id[0])
                    if name_and_code is not None:
                        self.cce.code_editor.setPlainText(name_and_code[1])

        model = HistoryTableModel(app, [p[1] for p in history])

        def set_to_historical_record():
            selected_indexes = self.history_table.selectedIndexes()
            if selected_indexes != []:
                point_in_time = model.points_in_time[selected_indexes[0].row()]
                if point_in_time == "current":
                    self.cce.update_old_historical_records = lambda: None
                else:
                    id = [p[0] for p in history if p[1] == point_in_time]
                    if len(id) == 1:
                        record_id = id[0]
                        app.project.commands_history.get_command(command_name, record_id)
                        self.saved_code = None

                        self.cce.update_old_historical_records = lambda: app.project.commands_history.get_command(
                            command_name, record_id, revert_to_requested_id=True
                        )
                self.close()

        def on_selection_changed(selected: QtCore.QItemSelection):
            if selected.length() != 0:
                selected_indexes = selected.data().indexes()
                if selected_indexes != []:
                    selected_indexes[0].row()
                    point_in_time = model.points_in_time[selected_indexes[0].row()]
                    preview_historical_code(point_in_time)

        self.history_table = ListTableView(
            table_model=model,
            pass_key_press_event=None,
            on_double_clicked=lambda _: set_to_historical_record(),
            hide_horizontal_header=True,
            on_selection_change=on_selection_changed,
        )

        self.history_table.selectRow(model.rowCount(QModelIndex()) - 1)

        self.setLayout(
            VBoxLayout(
                [
                    Label("Code saved at time"),
                    self.history_table,
                    W(stretch=1),
                    HBoxPanel(
                        [
                            W(stretch=1),
                            PushButton("Ok", on_clicked=set_to_historical_record, auto_default=True),
                            PushButton("Cancel", on_clicked=self.close, auto_default=False),
                        ]
                    ),
                ]
            )
        )

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent, /) -> None:
        if self.saved_code is not None:
            self.cce.code_editor.setPlainText(self.saved_code)
        super().closeEvent(event)


class CustomCommandsEditor(Dialog):
    def __init__(self, app: App, cmd: CustomCommand | None):
        super().__init__(
            app.main_window, windowTitle="Create Custom Command" if cmd is None else "Edit Custom Command", modal=True
        )
        self.app = app
        self.original_cmd = None if cmd is None else dataclasses.replace(cmd)
        self.update_old_historical_records: Callable[[], None] = lambda: None

        self.command_label = Variable("" if cmd is None else cmd.label)
        self.code_editor = CodeEditor(app, self.save_command)
        if cmd is not None:
            self.code_editor.setPlainText(cmd.source_code)

        def show_history_selector():
            history = app.project.commands_history.get_history_for_command(self.command_label.value) + [
                (sys.maxsize, "current")
            ]
            HistoryDialog(self, app, command_name=self.command_label.value, history=history).show()

        history_button = (
            [] if cmd is None else [PushButton("History", on_clicked=show_history_selector, auto_default=False)]
        )

        self.setLayout(
            VBoxLayout(
                [
                    LineEdit(
                        reactive_variable=self.command_label,
                        with_min_width_for_text=(" " * 200),
                        on_key_enter=lambda _: self.code_editor.setFocus(),
                        suppress_keys=[Qt.Key.Key_Escape],
                    ),
                    W(self.code_editor, stretch=1),
                    HorizonalLine(),
                    HBoxPanel(
                        history_button
                        + [
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
                self.update_old_historical_records()
                self.app.project.update_custom_command(self.original_cmd, new_cmd)

            self.close()
            self.app.request_commands_reload(True)  # True requests to keep current selection
        except Exception as ex:
            tb_lines = traceback.format_exception(type(ex), ex, ex.__traceback__)
            x = "".join(tb_lines[2:])
            self.app.show_error(str(x))
