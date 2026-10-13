from dataclasses import asdict
from typing import Any

from PySide6.QtCore import QItemSelectionModel, QModelIndex, QPersistentModelIndex
from PySide6.QtGui import QFont, QFontDatabase, QFontMetrics, Qt
from PySide6.QtWidgets import QFrame, QPlainTextEdit
from pytide6 import ComboBox, Dialog, HBoxLayout, HBoxPanel, Label, VBoxPanel, W
from qppte import QPythonPlainTextSettings, Settings
from sprats.collections import Variable

from i2cc.app import App
from i2cc.gui_tools import (
    ListTableView,
    TableModelAllSelectableAndEnabled,
    TableModelWithFilterAction,
    TableModelWithOneColumn,
    TableModelWithoutHeader,
)


class GroupsModel(
    TableModelWithoutHeader, TableModelWithOneColumn, TableModelAllSelectableAndEnabled, TableModelWithFilterAction
):
    def __init__(self, groups: list[str]):
        super().__init__()
        self.groups = groups

    def rowCount(self, /, parent: QModelIndex | QPersistentModelIndex = ...) -> int:
        return len(self.groups)

    def data(self, index: QModelIndex | QPersistentModelIndex, /, role: int = ...) -> Any:
        return self.groups[index.row()] if index.isValid() and role == Qt.ItemDataRole.DisplayRole else None


class SettingDialog2(Dialog):
    def __init__(
        self,
        app: App,
    ):
        super().__init__(app.main_window, windowTitle="Settings", modal=True)
        group_names = ["General", "Code Editor"]
        settings_groups = ListTableView(
            table_model=GroupsModel(group_names),
            pass_key_press_event=None,
            on_double_clicked=None,
            hide_horizontal_header=True,
        )
        width = QFontMetrics(self.font()).horizontalAdvance("Code Editor   ")
        settings_groups.setMaximumWidth(width)
        settings_groups.setMinimumWidth(width)
        settings_groups.setFrameShape(QFrame.Shape.NoFrame)
        settings_groups.setShowGrid(False)
        settings_groups.selectionModel().select(
            settings_groups.model().index(0, 0), QItemSelectionModel.SelectionFlag.ClearAndSelect
        )
        example_general_text = QPlainTextEdit(
            """“I love those who can smile in trouble, who can gather strength
from distress, and grow brave by reflection. 'Tis the business
of little minds to shrink, but they whose heart is firm, and
whose conscience approves their conduct, will pursue their
principles unto death”

    ― Leonardo da Vinci""",
            self,
        )
        example_general_text.setReadOnly(True)
        application_font_family: Variable[str] = Variable(
            app.q_application.font().family(),
            valid_values=QFontDatabase.families(),
            on_value_change=lambda f: example_general_text.setFont(QFont(f, example_general_text.font().pointSize())),
        )
        current_font_point_size = app.q_application.font().pointSize()
        application_font_size = Variable[int](
            current_font_point_size,
            valid_values=list(range(min(9, current_font_point_size), max(30, current_font_point_size + 1))),
            on_value_change=lambda s: example_general_text.setFont(QFont(example_general_text.font().family(), s)),
        )

        general_settings = VBoxPanel(
            [
                HBoxPanel(
                    [
                        Label("Application font"),
                        ComboBox(reactive_variable=application_font_family),
                        ComboBox(reactive_variable=application_font_size),
                        W(stretch=1),
                    ],
                    margins=0,
                ),
                example_general_text,
                W(stretch=1),
            ],
        )
        code_editor_settings = QPythonPlainTextSettings(self, app.get_code_editor_settings(), displayButtons=False)
        general_settings.setMinimumWidth(QFontMetrics(self.font()).horizontalAdvance("9") * 70)
        code_editor_settings.setVisible(False)
        ok_button = code_editor_settings.ok_button()
        ok_button.setStyleSheet(App.css.PushButton)
        cancel_button = code_editor_settings.cancel_button()
        cancel_button.setStyleSheet(App.css.PushButton)

        def apply_new_settings(settings: Settings):
            app.set_code_settings(settings)
            app.persistence.config.set_value("code_settings", asdict(settings))

        def ok():
            app.q_application.setFont(QFont(application_font_family.value, application_font_size.value))
            app.persistence.config.set_by_xpath("/global_appearance/font_family", application_font_family.value)
            app.persistence.config.set_by_xpath("/global_appearance/font_size", application_font_size.value)
            self.close()

        code_editor_settings.settings_changed.connect(apply_new_settings)
        code_editor_settings.ok_called.connect(ok)
        code_editor_settings.cancel_called.connect(self.close)

        settings_container = VBoxPanel(
            widgets=[
                W(general_settings, stretch=1),
                W(code_editor_settings, stretch=1),
                HBoxPanel([W(stretch=1), ok_button, cancel_button]),
            ],
            margins=0,
        )

        def show_group(a, b):
            group = group_names[settings_groups.currentIndex().row()]
            match group:
                case "General":
                    general_settings.setVisible(True)
                    code_editor_settings.setVisible(False)
                case "Code Editor":
                    general_settings.setVisible(False)
                    code_editor_settings.setVisible(True)

        settings_groups.selectionModel().selectionChanged.connect(show_group)
        self.setLayout(HBoxLayout([settings_groups, W(settings_container, stretch=2)]))
