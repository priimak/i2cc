import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from functools import reduce

from PySide6 import QtGui
from PySide6.QtCore import Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QGridLayout, QLayoutItem, QScrollArea, QWidget
from pytide6 import (
    CheckBox,
    ComboBox,
    Dialog,
    HBoxPanel,
    Label,
    PushButton,
    VBoxLayout,
    VBoxPanel,
    W,
)
from pytide6.frame import HorizonalLine
from pytide6.inputs import LineEdit
from rgscore import BinaryCodedDecimal, EnumValue, FieldDef, FixedPointNumber, Register
from rgscore.model.register import enum_value_name_re
from sprats.collections import Variable

from i2cc.app import App
from i2cc.gui_tools import ModalLineTextInputDialog, XButton


class FractionalInput(LineEdit):
    def __init__(self, value: str, on_text_change: Callable[[str], None]):
        super().__init__(
            text=value,
            with_fixed_width_for_text="00",
            validator=QRegularExpressionValidator("^[0-9]{0,2}$"),
            on_text_change=on_text_change,
        )
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def reformat_input_text(self):
        if self.text() == "":
            self.setText("0")

    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
        self.reformat_input_text()
        super().focusOutEvent(event)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Return:
            self.reformat_input_text()

        super().keyPressEvent(event)


class FieldNameInput(LineEdit):
    def __init__(self, value: str, on_text_change: Callable[[str], None], tooltip: str | None = None):
        super().__init__(
            text=value,
            with_fixed_width_for_text="Very Long Field Name",
            validator=QRegularExpressionValidator("^[a-zA-Z_]?[a-zA-Z0-9_]*$"),
            on_text_change=on_text_change,
            tooltip=tooltip,
        )


@dataclass
class FieldDefGUIElements:
    field_name_input_field: FieldNameInput
    checkboxes: list[CheckBox]
    width_label: Label
    rw_selector: ComboBox
    signed_selector: ComboBox
    fractional_input_field: FractionalInput


@dataclass
class RegisterPrototype:
    name: str
    address: int | None
    address_bus_width_bytes: int
    width: int
    model: list[FieldDef]
    gui_model: list[FieldDefGUIElements]
    desc: str

    __address_str: str = ""

    def __post_init__(self):
        self.__address_str = "" if self.address is None else f"0x{self.address:02X}"

    def set_name(self, name: str):
        self.name = name

    def set_desc(self, desc: str):
        self.desc = desc

    def set_address(self, address: str) -> None:
        self.__address_str = address
        self.address = 0 if address in ["", "0x"] else int(address, 16)
        self.address_bus_width_bytes = App.get_address_width(address.removeprefix("0x"))

    def to_register(self) -> Register:
        if self.name is None or self.name.strip() == "":
            raise ValueError("Register must have a name")
        elif not Register.register_name_re.match(self.name):
            raise ValueError("Register name must not be empty and contain only numbers, letters and (_) underscores.")
        elif self.__address_str in ["", "0x"]:
            raise ValueError("Register must have an address")
        elif self.model == []:
            raise ValueError("Register must have at least one field")
        elif len([fd for fd in self.model if fd.width == 0]) > 0:
            raise ValueError("Every field must have bits that it is picking from the register")
        elif len([fd for fd in self.model if fd.name.strip() == ""]) > 0:
            raise ValueError("Every field must have a name")
        else:
            return Register(
                bit_len=self.width,
                address=self.address,
                address_bus_width_bytes=self.address_bus_width_bytes,
                name=self.name,
                model=self.model,
                desc=self.desc,
            )

    @staticmethod
    def from_register(register: Register) -> "RegisterPrototype":
        return RegisterPrototype(
            name="" if register.name is None else register.name,
            address=register.address,
            address_bus_width_bytes=register.address_bus_width_bytes,
            width=register.width,
            model=[fd.copy() for fd in register._model],
            gui_model=[],
            desc=register.desc,
        )


class AddressInput(LineEdit):
    valid_address_re = re.compile("^(0x)?[0-9a-fA-F]+$")

    def __init__(self, register: RegisterPrototype):
        super().__init__(
            text="" if register.address is None else f"0x{register.address:0{register.address_bus_width_bytes * 2}X}",
            with_fixed_width_for_text="0xFFFF",
            validator=QRegularExpressionValidator("^(0x)?[0-9a-fA-F]{0,4}$"),
            on_text_change=register.set_address,
        )
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def reformat_input_text(self):
        entered_address = self.text().strip().removeprefix("0x")
        if re.match("^(0x)?[0-9a-fA-F]+$", entered_address):
            address = int(entered_address, 16)
            address_width = App.get_address_width(entered_address)
            self.setText(f"0x{address:0{address_width * 2}X}")

    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
        self.reformat_input_text()
        super().focusOutEvent(event)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Return:
            self.reformat_input_text()

        super().keyPressEvent(event)


@dataclass
class EnumVars:
    name: str
    value: str
    desc: str


class EnumEditDialog(Dialog):
    def __init__(self, parent, *, enums: list[EnumValue] | None):
        super().__init__(parent)
        self.is_success = False
        self.app: App = parent.app
        self.enums = [] if enums is None else enums
        self.vs = [EnumVars(e.name, str(e.value), e.desc) for e in self.enums]
        self.ins = []

        self.enums_layout = QGridLayout()

        self.build_ins()

        enum_panel = QWidget()
        enum_panel.setLayout(self.enums_layout)
        enum_area = QScrollArea()
        enum_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        enum_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        enum_area.setWidgetResizable(True)
        enum_area.setWidget(VBoxPanel([enum_panel, W(stretch=1)]))
        self.enums_layout.addWidget(
            XButton("Add New Enum Value", on_clicked=self.add_new_enum, auto_default=False), 0, 0, 1, 2
        )
        self.enums_layout.addWidget(Label("Enum Name"), 1, 0)
        self.enums_layout.addWidget(Label("Value"), 1, 1)
        self.enums_layout.addWidget(Label("Description"), 1, 2)
        self.build_rows()

        self.setLayout(
            VBoxLayout(
                [
                    W(enum_area, stretch=1),
                    HBoxPanel(
                        [
                            W(stretch=1),
                            XButton("Ok", auto_default=False, on_clicked=self.save_enums_and_close),
                            XButton("Cancel", on_clicked=self.close, auto_default=False),
                        ]
                    ),
                ]
            )
        )
        enum_panel.adjustSize()
        hint = enum_panel.sizeHint()
        vbar = enum_area.verticalScrollBar().sizeHint().width() if enum_area.verticalScrollBar().isVisible() else 0
        hbar = enum_area.horizontalScrollBar().sizeHint().height() if enum_area.horizontalScrollBar().isVisible() else 0
        enum_area.resize(
            hint.width() + vbar,
            hint.height() + hbar,
        )

    def build_ins(self):
        for i, v in enumerate(self.vs):
            self.ins.append(
                [
                    LineEdit(text=v.name, with_fixed_width_for_text="_" * 20),
                    LineEdit(text=v.value, with_fixed_width_for_text="0.1234567"),
                    LineEdit(text=v.desc, with_min_width_for_text="_" * 50),
                    XButton("Del", props={"row": i}, x_clicked=self.del_button_pressed, auto_default=False),
                ]
            )

    def remove_all_enums_gui_elements(self):
        enums_layout_items = self.enums_layout.layout()
        for _ in range(enums_layout_items.count()):
            w: QLayoutItem = enums_layout_items.takeAt(0)
            w.widget().setParent(None)
            enums_layout_items.removeItem(w)

        enums_layout_items.update()

    def del_button_pressed(self, b: PushButton):
        for i, v in enumerate(self.vs):
            v.name = self.ins[i][0].text()
            v.value = self.ins[i][1].text()
            v.desc = self.ins[i][2].text()

        self.remove_all_enums_gui_elements()
        idx: int = b.property("row")
        del self.vs[idx]
        self.ins.clear()
        self.build_ins()
        self.enums_layout.addWidget(
            XButton("Add New Enum Value", on_clicked=self.add_new_enum, auto_default=False), 0, 0, 1, 2
        )
        self.enums_layout.addWidget(Label("Enum Name"), 1, 0)
        self.enums_layout.addWidget(Label("Value"), 1, 1)
        self.enums_layout.addWidget(Label("Description"), 1, 2)
        self.build_rows()

    def add_new_enum(self):
        self.vs.append(EnumVars("", "0", ""))
        self.ins.append(
            [
                LineEdit(text=self.vs[-1].name, with_fixed_width_for_text="_" * 20),
                LineEdit(text=self.vs[-1].value, with_fixed_width_for_text="0.1234567"),
                LineEdit(text=self.vs[-1].desc, with_min_width_for_text="_" * 50),
                XButton("Del", props={"row": len(self.ins)}, x_clicked=self.del_button_pressed, auto_default=False),
            ]
        )
        row = len(self.ins) + 2
        for c in range(4):
            self.enums_layout.addWidget(self.ins[-1][c], row, c)

    def build_rows(self):
        row = 2
        for le in self.ins:
            self.enums_layout.addWidget(le[0], row, 0)
            self.enums_layout.addWidget(le[1], row, 1)
            self.enums_layout.addWidget(le[2], row, 2)
            self.enums_layout.addWidget(le[3], row, 3)
            row += 1

    def save_enums_and_close(self):
        for i, v in enumerate(self.vs):
            v.name = self.ins[i][0].text()
            v.value = self.ins[i][1].text()
            v.desc = self.ins[i][2].text()
            name = v.name.strip()
            if name == "":
                self.app.show_error("Every enum must have a non empty name")
                return
            elif not enum_value_name_re.match(name):
                self.app.show_error(
                    f"Invalid enum name [{v.name}]. Enum names must start with letter and "
                    "contain only letters, numbers and underscores."
                )
                return
            try:
                float(v.value)
            except:
                self.app.show_error(f"Invalid enum value [{v.value}]")
                return

        if len({v.name for v in self.vs}) != len(self.vs):
            self.app.show_error("Enum names must be unique")
            return

        if len({float(v.value) for v in self.vs}) != len(self.vs):
            self.app.show_error("Enum values must be unique")
            return

        self.enums = [EnumValue(name=v.name, value=float(v.value), desc=v.desc) for v in self.vs]
        self.is_success = True
        self.close()


class DefRegEditor(Dialog):
    def __init__(
        self,
        app: App,
        *,
        is_new_register: bool,
        register_proto: RegisterPrototype,
        windowTitle: str | None = None,
    ):
        super().__init__(app.main_window, windowTitle=windowTitle, modal=True)
        self.app = app
        self.is_new_register = is_new_register
        self.cb_toggle_enabled = True
        self.register_proto = register_proto
        self.original_register_name = self.register_proto.name
        name = "" if self.register_proto.name is None else self.register_proto.name
        self.register_proto.width = 8 * (self.register_proto.width // 8) + (
            8 if (self.register_proto.width % 8) > 0 else 0
        )
        self.new_register_address = ""

        self.fields_panel = self.build_fields_panel(VBoxPanel(margins=0))

        def add_new_field():
            self.remove_all_fields_gui_elements()
            self.register_proto.model.append(
                FieldDef(
                    name="",
                    offset=0,
                    number_format=FixedPointNumber(signed="U", integer_bits=0, fractional_bits=0),
                    width=0,
                    rw=True,
                )
            )
            self.register_proto.gui_model.clear()
            self.build_fields_panel(self.fields_panel)

        self.setLayout(
            VBoxLayout(
                [
                    HBoxPanel(
                        [
                            Label("Name"),
                            LineEdit(
                                name,
                                on_text_change=self.register_proto.set_name,
                                with_fixed_width_for_text="Very Long Register Name",
                            ),
                            Label("  Addr"),
                            AddressInput(self.register_proto),
                            Label(f"  This register is {self.register_proto.width} bits wide"),
                            W(stretch=1),
                        ],
                        margins=0,
                    ),
                    HBoxPanel(
                        [
                            Label("Description"),
                            LineEdit(self.register_proto.desc, on_text_change=self.register_proto.set_desc),
                        ],
                        margins=0,
                    ),
                    HorizonalLine(),
                    HBoxPanel(
                        [
                            Label("Fields"),
                            XButton(
                                "Add New Field",
                                on_clicked=add_new_field,
                                auto_default=False,
                            ),
                            W(stretch=1),
                        ],
                        margins=0,
                    ),
                    self.fields_panel,
                    W(stretch=1),
                    HorizonalLine(),
                    HBoxPanel(
                        [
                            W(stretch=1),
                            XButton("Ok", on_clicked=self.save_register, auto_default=False),
                            XButton("Cancel", on_clicked=self.close, auto_default=False),
                        ],
                        margins=0,
                    ),
                ]
            )
        )

    def remove_all_fields_gui_elements(self):
        fields_panel_layout = self.fields_panel.layout()
        for _ in range(fields_panel_layout.count()):
            w: QLayoutItem = fields_panel_layout.takeAt(0)
            w.widget().setParent(None)
            fields_panel_layout.removeItem(w)

        fields_panel_layout.update()

    def save_register(self):
        try:
            new_register = self.register_proto.to_register()
            if self.is_new_register:
                self.app.project.addr_map.add(new_register)
            else:
                # we are editing register
                original_register = self.app.project.addr_map.get_register_by_name(self.original_register_name)
                self.app.project.addr_map.update_register_def(original_register, new_register)

            self.app.request_reglist_reload()
            self.app.request_reglist_select_register(new_register)
            self.app.update_results_display_data()
            self.app.request_results_reload()
            self.close()
        except Exception as ex:
            self.app.show_error(f"{ex}")

    def build_fields_panel(self, fields_panel: VBoxPanel) -> VBoxPanel:
        wgs = []

        def other_used_bits(but_fd: FieldDef) -> set[int]:
            other_fields = [fd for fd in self.register_proto.model if fd is not but_fd]
            used_register_bits = [set(range(fd.offset, fd.offset + fd.width)) for fd in other_fields]
            return reduce(lambda acc, v: acc | v, used_register_bits, set())

        def mk_bare_cb(field_idx: int, offset: int) -> CheckBox:
            cb = CheckBox(css="QCheckBox:disabled {background-color: black;}")
            cb.setProperty("field_idx", field_idx)
            cb.setProperty("offset", offset)
            return cb

        for field_idx, field_def in enumerate(self.register_proto.model):

            def mk_rw_setter(fd: FieldDef):
                def set_rw(value: str):
                    fd.rw = value == "rw"

                return set_rw

            def mk_fractional_setter(fd: FieldDef):
                def set_fractional(value: str):
                    if isinstance(fd.number_format, FixedPointNumber):
                        fd.number_format = replace(fd.number_format, fractional_bits=(0 if value == "" else int(value)))

                return set_fractional

            def mk_field_name_setter(fd: FieldDef):
                def set_name(value: str):
                    fd.name = value

                return set_name

            def get_current_selector_for_signed_combo_box(fd: FieldDef) -> int:
                if isinstance(fd.number_format, BinaryCodedDecimal):
                    return 2
                elif fd.number_format.signed == "U":
                    return 0
                else:
                    return 1

            def get_fractional_input_value(fd: FieldDef) -> str:
                if isinstance(fd.number_format, FixedPointNumber):
                    return f"{fd.number_format.fractional_bits}"
                else:
                    return "0"

            fractional_input_field = FractionalInput(
                get_fractional_input_value(field_def),
                on_text_change=mk_fractional_setter(field_def),
            )

            def mk_signed_setter(fd: FieldDef, fif: FractionalInput):
                def set_signed(value: str):
                    if value == "BCD":
                        fd.number_format = BinaryCodedDecimal()
                        fif.setVisible(False)
                    else:
                        if isinstance(fd.number_format, BinaryCodedDecimal):
                            fd.number_format = FixedPointNumber(
                                signed=("S" if value == "Signed" else "U"), integer_bits=fd.width, fractional_bits=0
                            )
                            fif.setText("0")
                        else:
                            fd.number_format = replace(fd.number_format, signed=("S" if value == "Signed" else "U"))
                        fif.setVisible(True)

                return set_signed

            self.register_proto.gui_model.append(
                FieldDefGUIElements(
                    field_name_input_field=FieldNameInput(
                        field_def.name, on_text_change=mk_field_name_setter(field_def), tooltip=field_def.desc
                    ),
                    checkboxes=[mk_bare_cb(field_idx, offset) for offset in range(self.register_proto.width)],
                    width_label=Label(f"{field_def.width}."),
                    rw_selector=ComboBox(
                        items=["rw", "ro"],
                        current_selection="rw" if field_def.rw else "ro",
                        on_text_change=mk_rw_setter(field_def),
                    ),
                    signed_selector=ComboBox(
                        items=["Unsinged", "Signed", "BCD"],
                        current_selection=get_current_selector_for_signed_combo_box(field_def),
                        on_text_change=mk_signed_setter(field_def, fractional_input_field),
                    ),
                    fractional_input_field=fractional_input_field,
                )
            )
        for field_idx, field_def in enumerate(self.register_proto.model):
            bits_to_disable: set[int] = other_used_bits(field_def)

            def mk_cb(i: int, bits_to_disable: set[int], field_def: FieldDef):
                cb: CheckBox = self.register_proto.gui_model[field_idx].checkboxes[i]
                cb.setChecked(field_def.offset <= i <= field_def.end_offset())
                cb.setEnabled(i not in bits_to_disable)

                def mk_cb_toggled(cbb: CheckBox):
                    def cb_toggled(on: bool):
                        if not self.cb_toggle_enabled:
                            return

                        field_idx: int = cbb.property("field_idx")
                        offset: int = cbb.property("offset")
                        field_def: FieldDef = self.register_proto.model[field_idx]
                        if offset == (field_def.end_offset() + 1):
                            field_def.width += 1
                        elif offset == field_def.offset - 1:
                            field_def.offset -= 1
                            field_def.width += 1
                        elif field_def.offset < offset <= field_def.end_offset():
                            field_def.width = offset - field_def.offset
                        elif field_def.offset == offset:
                            field_def.offset += 1
                            field_def.width -= 1
                        else:
                            field_def.offset = offset
                            field_def.width = 1 if on else 0

                        if isinstance(field_def.number_format, FixedPointNumber):
                            field_def.number_format = replace(field_def.number_format, integer_bits=field_def.width)

                        # update numerical type width label
                        self.register_proto.gui_model[field_idx].width_label.setText(f"{field_def.width}.")

                        # now update gui checkboxes
                        ids_checked = set(range(field_def.offset, field_def.end_offset() + 1))
                        try:
                            self.cb_toggle_enabled = False
                            for cb in self.register_proto.gui_model[field_idx].checkboxes:
                                idx: int = cb.property("offset")
                                cb.setChecked(idx in ids_checked)
                        finally:
                            self.cb_toggle_enabled = True

                        # now update other fields disabling checkboxes
                        for j, other_field_def in enumerate(self.register_proto.model):
                            if j != field_idx:
                                bits_to_disable: set[int] = other_used_bits(other_field_def)
                                for cb in self.register_proto.gui_model[j].checkboxes:
                                    cb.setEnabled(cb.property("offset") not in bits_to_disable)

                    return cb_toggled

                cb.toggled.connect(mk_cb_toggled(cb))

                return cb

            cbs = [mk_cb(i, bits_to_disable, field_def) for i in range(self.register_proto.width)[::-1]]

            def mk_delete_action(idx: int) -> Callable[[], None]:
                def delete_action():
                    self.remove_all_fields_gui_elements()
                    del self.register_proto.model[idx]
                    self.register_proto.gui_model.clear()
                    self.build_fields_panel(fields_panel)

                return delete_action

            desc_tooltip = Variable(self.register_proto.model[field_idx].desc)

            def mk_desc_field_updater(f: FieldDef, desc_tooltip: Variable[str]):
                def desc_field_updater():
                    desc_dialog = ModalLineTextInputDialog(self, text=f.desc, windowTitle="Field Description")
                    desc_dialog.exec()
                    f.desc = desc_dialog.new_value
                    desc_tooltip.value = f.desc

                return desc_field_updater

            field_name_input_field = self.register_proto.gui_model[field_idx].field_name_input_field
            desc_tooltip.register_value_change_callback(field_name_input_field.setToolTip)

            def mk_edit_enums(idx: int):
                def edit_enums():
                    enum_dialog = EnumEditDialog(self, enums=self.register_proto.model[idx].enum_values)
                    enum_dialog.exec()
                    if enum_dialog.is_success:
                        self.register_proto.model[idx].enum_values = (
                            None if enum_dialog.enums == [] else enum_dialog.enums
                        )

                return edit_enums

            wgs.append(
                HBoxPanel(
                    cbs
                    + [
                        Label(" "),
                        field_name_input_field,
                        self.register_proto.gui_model[field_idx].rw_selector,
                        self.register_proto.gui_model[field_idx].signed_selector,
                        self.register_proto.gui_model[field_idx].width_label,
                        self.register_proto.gui_model[field_idx].fractional_input_field,
                        W(stretch=1),
                        XButton(
                            "Desc",
                            auto_default=False,
                            on_clicked=mk_desc_field_updater(self.register_proto.model[field_idx], desc_tooltip),
                            tool_tip=self.register_proto.model[field_idx].desc,
                            reactive_tooltip=desc_tooltip,
                        ),
                        XButton(
                            "Enums",
                            auto_default=False,
                            on_clicked=mk_edit_enums(field_idx),
                        ),
                        Label("  "),
                        XButton("Del", on_clicked=mk_delete_action(field_idx), auto_default=False),
                    ],
                    margins=0,
                )
            )
        fields_panel.layout().addWidgets(wgs)
        return fields_panel


class NewRegDefDialog(Dialog):
    def __init__(self, app: App):
        super().__init__(app.main_window, windowTitle="Create new register", modal=True, css=App.css.NewRegDefDialog)
        self.app = app
        self.bit_width: Variable[int] = Variable(8, valid_values=[8, 16, 24, 32])

        def open_edit_dialog():
            self.close()
            DefRegEditor(
                app,
                windowTitle="Create new register",
                is_new_register=True,
                register_proto=RegisterPrototype(
                    name="",
                    address=None,
                    address_bus_width_bytes=1,
                    width=self.bit_width.value,
                    model=[
                        FieldDef(
                            name="",
                            offset=0,
                            number_format=FixedPointNumber(signed="U", integer_bits=0, fractional_bits=0),
                            width=0,
                            rw=True,
                        )
                    ],
                    gui_model=[],
                    desc="",
                ),
            ).exec()

        self.setLayout(
            VBoxLayout(
                [
                    HBoxPanel(
                        [
                            Label("How wide (in number of bits) do you want this register to be?"),
                            ComboBox(reactive_variable=self.bit_width),
                        ]
                    ),
                    HBoxPanel(
                        [
                            W(stretch=1),
                            XButton("Ok", on_clicked=open_edit_dialog, auto_default=True),
                            XButton("Cancel", on_clicked=self.close, auto_default=False),
                        ]
                    ),
                ]
            )
        )


def open_create_or_edit_register_from_template(
    app: App, register_address: int, address_bus_width_bytes: int, width_bits: int
):
    register = app.project.addr_map.get_register_by_address(register_address)
    if register is None:
        return DefRegEditor(
            app,
            windowTitle="Create new register",
            is_new_register=True,
            register_proto=RegisterPrototype(
                name="",
                address=register_address,
                address_bus_width_bytes=address_bus_width_bytes,
                width=width_bits,
                model=[
                    FieldDef(
                        name="",
                        offset=0,
                        number_format=FixedPointNumber(signed="U", integer_bits=0, fractional_bits=0),
                        width=0,
                        rw=True,
                    )
                ],
                gui_model=[],
                desc="",
            ),
        ).exec()
    else:
        DefRegEditor(
            app=app,
            windowTitle="Edit Register",
            is_new_register=False,
            register_proto=RegisterPrototype.from_register(register),
        ).exec()
