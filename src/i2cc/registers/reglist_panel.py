from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock
from typing import Any

from PySide6 import QtGui
from PySide6.QtCore import QItemSelection, QModelIndex, QPersistentModelIndex, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QLabel, QMessageBox, QTextEdit
from pytide6 import HBoxPanel, Menu, Splitter, VBoxPanel, W
from rgscore import Register

from i2cc.app import App
from i2cc.gui_tools import (
    InTableSearchField,
    ListTableView,
    ModalMessageDialog,
    ReactiveActionLabelWithMenu,
    TableModelAllSelectableAndEnabled,
    TableModelWithFilterAction,
    TableModelWithThreeColumns,
    XButton,
    apply_filter_to_text,
)
from i2cc.registers.reg_def_editor import DefRegEditor, NewRegDefDialog, RegisterPrototype
from i2cc.registers.reg_write_dialog import RegisterWriteDialog


@dataclass
class RowAndRegisterName:
    row: int
    name: str


@dataclass
class RegisterDisplayData:
    address: str
    name: str
    fields: str
    pure_name: str


class RegListModel(
    TableModelWithThreeColumns,
    TableModelAllSelectableAndEnabled,
    TableModelWithFilterAction,
):
    def __init__(self, app: App):
        super().__init__()
        self.app = app
        self.registers_to_display = self.mk_registers_to_display()

    def mk_registers_to_display(self) -> list[RegisterDisplayData]:
        return [
            RegisterDisplayData(
                address=f"0x{register.address:0{register.address_bus_width_bytes * 2}X}",
                name=register.name,
                fields=", ".join(register.get_field_names()),
                pure_name=register.name,
            )
            for register in self.app.project.addr_map.registers
        ]

    def regenerate_registers_to_display(self):
        self.registers_to_display = self.mk_registers_to_display()

    def headerData(self, section, orientation, /, role=...) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            match section:
                case 0:
                    return "Address"
                case 1:
                    return "Register"
                case 2:
                    return "Fields"
                case _:
                    return ""
        elif orientation == Qt.Orientation.Vertical and role == Qt.ItemDataRole.DisplayRole:
            return None
        else:
            return super().headerData(section, orientation, role)

    def rowCount(self, /, parent: QModelIndex | QPersistentModelIndex = ...) -> int:
        return len(self.registers_to_display)

    def data(self, index: QModelIndex | QPersistentModelIndex, /, role: int = ...) -> Any:
        if index.isValid() and role == Qt.ItemDataRole.DisplayRole:
            register = self.registers_to_display[index.row()]
            match index.column():
                case 0:
                    return register.address
                case 1:
                    return register.name
                case 2:
                    return register.fields
                case _:
                    return None
        else:
            return None

    def apply_filter(self, filter_text: str, post_filter_action: Callable[[], Any]):
        char_filter = list(filter_text)
        try:
            self.beginResetModel()
            self.registers_to_display.clear()
            if char_filter == []:
                self.registers_to_display = self.mk_registers_to_display()
                self.endResetModel()
                post_filter_action()
                return

            registers_to_display_input = self.mk_registers_to_display()

            for register in registers_to_display_input:
                new_register_address = apply_filter_to_text(char_filter, register.address)
                new_register_name = apply_filter_to_text(char_filter, register.name)
                new_register_fields = apply_filter_to_text(char_filter, register.fields)

                fields_ = [new_register_address, new_register_name, new_register_fields]
                if len([a for a in fields_ if a is not None]) > 0:
                    # we have something to display
                    if new_register_address is None:
                        new_register_address = register.address

                    if new_register_name is None:
                        new_register_name = register.name

                    if new_register_fields is None:
                        new_register_fields = register.fields

                    # add to display
                    self.registers_to_display.append(
                        RegisterDisplayData(
                            address=new_register_address,
                            name=new_register_name,
                            fields=new_register_fields,
                            pure_name=register.name,
                        )
                    )
        finally:
            self.endResetModel()
            post_filter_action()


class RegInfoText(QTextEdit):
    def __init__(self, app: App):
        super().__init__()
        self.setReadOnly(True)
        self.app = app
        self.setStyleSheet(App.css.RegInfoText)
        self.register: Register | None = None
        self.__lock = Lock()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_A and event.modifiers() == (
            Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier
        ):
            super().keyPressEvent(event)

    def reload_register(self):
        if self.register is not None:
            self.show_register(self.register)

    def show_register(self, register: Register) -> None:
        with self.__lock:
            self.register = register
            raw_result = self.app.project.get_raw_result_for_address(register.address)
            if raw_result is not None:
                self.app.reload_results_table_from_memory()

            table_format = QtGui.QTextTableFormat()
            table_format.setWidth(QtGui.QTextLength(QtGui.QTextLength.Type.PercentageLength, 100))
            constraints = [
                QtGui.QTextLength(QtGui.QTextLength.Type.PercentageLength, 1),
                QtGui.QTextLength(QtGui.QTextLength.Type.PercentageLength, 1),
                QtGui.QTextLength(QtGui.QTextLength.Type.PercentageLength, 1),
                QtGui.QTextLength(QtGui.QTextLength.Type.PercentageLength, 1),
                QtGui.QTextLength(QtGui.QTextLength.Type.PercentageLength, 1),
                QtGui.QTextLength(QtGui.QTextLength.Type.PercentageLength, 1),
                QtGui.QTextLength(QtGui.QTextLength.Type.PercentageLength, 95),
            ]
            table_format.setColumnWidthConstraints(constraints)

            cursor = self.textCursor()
            cursor.beginEditBlock()
            cursor.select(QtGui.QTextCursor.SelectionType.Document)
            cursor.removeSelectedText()
            table = cursor.insertTable(1, 7, table_format)

            format = table.format()
            format.setBorder(0)
            table.setFormat(format)
            table.appendRows(6)

            c0 = table.cellAt(0, 0).firstCursorPosition()
            c0.insertText("Register:")
            c = table.cellAt(0, 1).firstCursorPosition()
            table.mergeCells(0, 1, 1, 6)
            char_format = QtGui.QTextCharFormat()
            char_format.setForeground(QtGui.QColorConstants.Blue)
            c.setCharFormat(char_format)
            assert register.name is not None
            c.insertText(register.name)

            table.cellAt(1, 0).firstCursorPosition().insertText("Description:")
            c = table.cellAt(1, 1).firstCursorPosition()
            table.mergeCells(1, 1, 1, 6)
            char_format = QtGui.QTextCharFormat()
            char_format.setForeground(QtGui.QColorConstants.DarkGreen)
            char_format.setFontItalic(True)
            c.setCharFormat(char_format)
            c.insertText(register.desc)

            table.cellAt(2, 0).firstCursorPosition().insertText("Address:")
            c = table.cellAt(2, 1).firstCursorPosition()
            char_format = QtGui.QTextCharFormat()
            char_format.setForeground(QtGui.QColorConstants.Blue)
            c.setCharFormat(char_format)
            assert register.address is not None
            c.insertText(f"0x{register.address:0{register.address_bus_width_bytes * 2}X}")

            c0 = table.cellAt(3, 0).firstCursorPosition()
            bf = QtGui.QTextBlockFormat()
            bf.setNonBreakableLines(True)
            c0.setBlockFormat(bf)
            c0.insertText("Width (bits):")
            c = table.cellAt(3, 1).firstCursorPosition()
            char_format = QtGui.QTextCharFormat()
            char_format.setForeground(QtGui.QColorConstants.Blue)
            c.setCharFormat(char_format)
            c.insertText(f"{register.width}")

            table.cellAt(4, 0).firstCursorPosition().insertText("Reset value:")
            c = table.cellAt(4, 1).firstCursorPosition()
            table.mergeCells(4, 1, 1, 6)
            char_format = QtGui.QTextCharFormat()
            char_format.setForeground(QtGui.QColorConstants.Blue)
            c.setCharFormat(char_format)
            c.insertText(register.reset_value.bin)

            table.cellAt(5, 0).firstCursorPosition().insertText("Raw data:")
            c = table.cellAt(5, 1).firstCursorPosition()
            table.mergeCells(5, 1, 1, 6)
            char_format = QtGui.QTextCharFormat()
            char_format.setForeground(QtGui.QColorConstants.Blue)
            c.setCharFormat(char_format)
            c.insertText(register.data.bin)

            table.cellAt(6, 0).firstCursorPosition().insertText("Fields:")
            row = 7
            for field_name in register.get_field_names():
                table.appendRows(1)
                field_def = register.get_field_definition(field_name)

                cell = table.cellAt(row, 1)
                c = cell.firstCursorPosition()
                char_format = QtGui.QTextCharFormat()
                char_format.setForeground(QtGui.QColorConstants.Blue)
                c.setCharFormat(char_format)
                bf = c.blockFormat()
                bf.setTopMargin(0)
                bf.setBottomMargin(0)
                bf.setNonBreakableLines(True)
                c.setBlockFormat(bf)
                c.insertText(f"{field_def.name}  ")

                c = table.cellAt(row, 2).firstCursorPosition()
                c.setBlockFormat(bf)
                c.insertText(f"[{field_def.end_offset()}:{field_def.offset}]  ")

                c = table.cellAt(row, 3).firstCursorPosition()
                c.setBlockFormat(bf)
                c.insertText(f"{field_def.number_format!r}  ")

                c = table.cellAt(row, 4).firstCursorPosition()
                c.setBlockFormat(bf)
                c.insertText("r/w  " if field_def.rw else "r/o")
                if raw_result is not None:
                    c = table.cellAt(row, 5).firstCursorPosition()
                    c.setBlockFormat(bf)
                    c.insertText("=> " + str(register.get_field_value(field_def.name)) + "  ")
                c = table.cellAt(row, 6).firstCursorPosition()
                char_format = QtGui.QTextCharFormat()
                char_format.setForeground(QtGui.QColorConstants.DarkGreen)
                char_format.setFontItalic(True)
                c.setCharFormat(char_format)
                c.insertText(field_def.desc)

                row += 1
                if field_def.enum_values is not None:
                    for e in field_def.enum_values:
                        table.appendRows(1)

                        c = table.cellAt(row, 1).firstCursorPosition()
                        char_format = QtGui.QTextCharFormat()
                        char_format.setForeground(QtGui.QColorConstants.Red)
                        c.setCharFormat(char_format)
                        c.setBlockFormat(bf)
                        c.insertText(f"  {e.name}")

                        c = table.cellAt(row, 3).firstCursorPosition()
                        table.mergeCells(row, 3, 1, 2)
                        c.setBlockFormat(bf)
                        c.insertText(f"{e.value}")

                        c = table.cellAt(row, 6).firstCursorPosition()
                        char_format = QtGui.QTextCharFormat()
                        char_format.setForeground(QtGui.QColorConstants.Gray)
                        char_format.setFontItalic(True)
                        c.setCharFormat(char_format)
                        c.insertText(f"{e.desc}")

                        row += 1
            c.endEditBlock()


class RegListPanel(VBoxPanel):
    def __init__(self, app: App):
        super().__init__(background_color=App.colors.background_common, margins=(7, 7, 7, 0))
        self.app = app
        self.reglist_table = ListTableView(
            table_model=RegListModel(app),
            pass_key_press_event=self.pass_key_press_event,
            on_double_clicked=self.on_actions_table_double_clicked,
        )
        app.request_reglist_reload = self.request_reglist_reload

        self.context_menu = Menu(
            parent=self,
            actions=[
                ("Read register", self.read_selected_register),
                ("Write register", self.write_selected_register),
                Menu.Separator,
                ("Edit register", self.edit_selected_register),
                ("Define new register", lambda: NewRegDefDialog(self.app).exec()),
                ("Delete register", self.delete_selected_register),
            ],
        )
        self.reglist_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.reglist_table.customContextMenuRequested.connect(
            lambda pos: self.context_menu.popup(self.reglist_table.viewport().mapToGlobal(pos))
        )

        self.search_field = InTableSearchField(
            table_view=self.reglist_table,
            on_key_enter=lambda _: self.read_selected_register(),
            close_action=lambda: None,
        )

        def select_register(register: Register) -> None:
            try:
                for row, rdd in enumerate(self.reglist_table.table_model.registers_to_display):
                    if rdd.pure_name == register.name:
                        self.reglist_table.selectRow(row)
                        return
            finally:
                self.search_field.setFocus()

        app.request_reglist_select_register = select_register

        self.register_text = RegInfoText(app)

        def selection_changed(selected_item: QItemSelection, _):
            selected_indexes = selected_item.indexes()
            if selected_indexes == []:
                self.register_text.setText("")
            else:
                register_name = self.reglist_table.table_model.registers_to_display[selected_indexes[0].row()].pure_name
                self.register_text.show_register(app.project.addr_map.get_register_by_name(register_name))

        self.reglist_table.selectionModel().selectionChanged.connect(selection_changed)

        self.splitter = Splitter(
            Qt.Orientation.Horizontal,
            childrenCollapsible=False,
            handleWidth=8,
            widgets=[self.reglist_table, self.register_text],
            margins=0,
        )

        button_new_register = XButton("New register", on_clicked=lambda: NewRegDefDialog(self.app).exec())
        button_edit = XButton("Edit", on_clicked=self.edit_selected_register)
        button_delete = XButton("Delete", on_clicked=self.delete_selected_register)
        button_read = XButton("Read", on_clicked=self.read_selected_register)
        button_write = XButton("Write", on_clicked=self.write_selected_register)

        def set_buttons_visible(visible: bool) -> None:
            button_new_register.setVisible(visible)
            button_edit.setVisible(visible)
            button_delete.setVisible(visible)
            button_read.setVisible(visible)
            button_write.setVisible(visible)

        show_registers_buttons = self.app.persistence.state.get_value("registers_buttons_show", True)
        set_buttons_visible(show_registers_buttons)

        config_label = ReactiveActionLabelWithMenu()
        show_action = config_label.addMenuAction("Show buttons")
        show_action.setCheckable(True)
        show_action.setChecked(show_registers_buttons)

        def action_show():
            is_checked = show_action.isChecked()
            self.app.persistence.state.set_value("registers_buttons_show", is_checked)
            set_buttons_visible(is_checked)

        show_action.triggered.connect(action_show)

        self.withWidgets(
            HBoxPanel(
                widgets=[
                    button_new_register,
                    button_edit,
                    button_delete,
                    QLabel("        "),
                    button_read,
                    button_write,
                    W(stretch=1),
                    config_label,
                ],
                margins=0,
            ),
            self.search_field,
            W(self.splitter, stretch=2),
        )

        self.app.registers_values_changed = self.registers_values_changed

    def registers_values_changed(self, address: int):
        if self.register_text.register is not None and self.register_text.register.address == address:
            self.register_text.reload_register()

    def request_reglist_reload(self):
        try:
            self.reglist_table.table_model.beginResetModel()
            self.reglist_table.table_model.regenerate_registers_to_display()
            self.register_text.clear()
            self.register_text.register = None
        finally:
            self.reglist_table.table_model.endResetModel()
            if self.reglist_table.model().rowCount() > 0:
                self.reglist_table.selectRow(0)

    def pass_key_press_event(self) -> Callable[[QKeyEvent], None]:
        def key_pressed(event: QKeyEvent) -> None:
            match event.key():
                case Qt.Key.Key_Return | Qt.Key.Key_Enter:
                    self.read_selected_register()
                case Qt.Key.Key_Delete:
                    self.delete_selected_register()
                case _:
                    self.search_field.keyPressEvent(event)

        return key_pressed

    def on_actions_table_double_clicked(self, index: QModelIndex):
        self.read_selected_register()

    def define_new_register(self):
        NewRegDefDialog(self.app).exec()

    def get_selected_register_name(self) -> RowAndRegisterName | None:
        selected_indexes = self.reglist_table.selectedIndexes()
        if selected_indexes is not None and len(selected_indexes) > 0:
            selected_row = selected_indexes[0].row()
            return RowAndRegisterName(
                row=selected_row,
                name=self.reglist_table.table_model.registers_to_display[selected_row].pure_name,
            )
        else:
            return None

    def edit_selected_register(self):
        row_and_name = self.get_selected_register_name()
        if row_and_name is not None:
            register = self.app.project.addr_map.get_register_by_name(row_and_name.name)
            DefRegEditor(
                app=self.app,
                windowTitle="Edit Register",
                is_new_register=False,
                register_proto=RegisterPrototype.from_register(
                    self.app.project.addr_map.get_register_by_name(register.name)
                ),
            ).exec()

    def delete_selected_register(self):
        register = self.get_selected_register_name()
        if register is not None:
            ret = ModalMessageDialog.question(
                self.app.main_window,
                "Delete register?",
                f"Please confirm that you want to delete register [{register.name}]?",
            )
            if ret == QMessageBox.StandardButton.Yes:
                self.app.project.addr_map.delete_register_by_name(register.name)
                self.app.request_reglist_reload()
                self.search_field.textChanged.emit(self.search_field.text())
                self.reglist_table.selectRow(min(self.reglist_table.table_model.rowCount() - 1, register.row))
                self.app.update_results_display_data()
                self.app.request_results_reload()

    def read_selected_register(self):
        register = self.get_selected_register_name()
        if register is not None:
            r = self.app.project.addr_map.get_register_by_name(register.name)
            self.app.read_register_address_str.set_value(f"0x{r.address:0{r.address_bus_width_bytes * 2}X}")
            self.app.read_register_num_bytes.set_value(int(r.width / 8))
            self.app.read_register()

    def write_selected_register(self):
        register = self.get_selected_register_name()
        if register is not None:
            RegisterWriteDialog(
                self.app,
                register=self.app.project.addr_map.get_register_by_name(register.name),
            ).exec()
