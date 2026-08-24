from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QModelIndex, QPersistentModelIndex, Qt
from PySide6.QtGui import QKeyEvent
from pytide6 import Dialog, VBoxLayout

from i2cc.app import App
from i2cc.gui_tools import (
    InTableSearchField,
    ListTableView,
    TableModelAllSelectableAndEnabled,
    TableModelWithFilterAction,
    TableModelWithOneColumn,
    apply_filter_to_text,
)


@dataclass
class RegisterDisplayData:
    name_and_field: str
    name: str
    field: str


class RegistersModel(
    TableModelWithOneColumn,
    TableModelAllSelectableAndEnabled,
    TableModelWithFilterAction,
):
    def __init__(self, app: App):
        super().__init__()
        self.app = app
        self.registers_to_display = self.mk_registers_to_display()

    def mk_registers_to_display(self) -> list[RegisterDisplayData]:
        return [
            RegisterDisplayData(register.name + field, register.name, field)
            for register in self.app.project.reg_list.registers
            for field in [""] + [f".{f}" for f in register.get_field_names()]
        ]

    def rowCount(self, /, parent: QModelIndex | QPersistentModelIndex = ...) -> int:
        return len(self.registers_to_display)

    def data(self, index: QModelIndex | QPersistentModelIndex, /, role: int = ...) -> Any:
        if index.isValid() and role == Qt.ItemDataRole.DisplayRole and index.column() == 0:
            return self.registers_to_display[index.row()].name_and_field
        else:
            return None

    def headerData(self, section, orientation, /, role=...) -> Any:
        return None

    def apply_filter(self, filter_text: str, post_filter_action: Callable[[], Any]):
        char_filter = list(filter_text)
        self.beginResetModel()
        self.registers_to_display.clear()
        if char_filter == []:
            self.registers_to_display = self.mk_registers_to_display()
            self.endResetModel()
            post_filter_action()
            return

        registers_to_display_input = self.mk_registers_to_display()
        for register in registers_to_display_input:
            new_register_name_and_field = apply_filter_to_text(char_filter, register.name_and_field)
            if new_register_name_and_field is not None:
                self.registers_to_display.append(
                    RegisterDisplayData(new_register_name_and_field, register.name, register.field)
                )

        self.endResetModel()
        post_filter_action()


class FindRegisterDialog(Dialog):
    def __init__(self, parent, app: App, insert_text_callback: Callable[[str], None]):
        super().__init__(
            parent,
            windowTitle="Find Register",
            modal=True,
            css="QDialog { background-color: #DDDDFF; border: 1px solid black; }",
        )
        self.insert_text_callback = insert_text_callback
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.registers_table = ListTableView(
            table_model=RegistersModel(app),
            pass_key_press_event=self.pass_key_press_event,
            on_double_clicked=self.on_actions_table_double_clicked,
        )
        self.registers_table.horizontalHeader().hide()
        self.registers_table.horizontalHeader().hide()

        self.search_field = InTableSearchField(
            table_view=self.registers_table,
            on_key_enter=lambda _: self.insert_selected_register_and_field(),
            close_action=lambda: None,
        )

        self.setLayout(VBoxLayout([self.search_field, self.registers_table], margins=3))

    def pass_key_press_event(self) -> Callable[[QKeyEvent], None]:
        def key_pressed(event: QKeyEvent) -> None:
            print(f"key_pressed {event}")
            match event.key():
                case Qt.Key.Key_Return | Qt.Key.Key_Enter:
                    self.insert_selected_register_and_field()
                case _:
                    self.search_field.keyPressEvent(event)

        return key_pressed

    def on_actions_table_double_clicked(self, index: QModelIndex):
        self.insert_selected_register_and_field()

    def insert_selected_register_and_field(self):
        selected_indexes = self.registers_table.selectedIndexes()
        if selected_indexes is not None and len(selected_indexes) > 0:
            selected_row = selected_indexes[0].row()
            selected_register = self.registers_table.table_model.registers_to_display[selected_row]

            if selected_register.field != "":
                self.insert_text_callback(selected_register.name + selected_register.field)
            else:
                self.insert_text_callback(selected_register.name)
            self.close()
