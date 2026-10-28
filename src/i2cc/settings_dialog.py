from dataclasses import asdict
from typing import Any

from PySide6.QtCore import QModelIndex, QPersistentModelIndex
from PySide6.QtGui import QFont, QFontDatabase, QFontMetrics, Qt
from PySide6.QtWidgets import QPlainTextEdit
from pytide6 import ComboBox, Dialog, HBoxLayout, HBoxPanel, Label, VBoxPanel, W
from qppte import QPythonPlainTextSettings, Settings
from sprats.collections import Variable

from i2cc.app import App
from i2cc.gui_tools import (
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


class SettingDialog(Dialog):
    def __init__(
        self,
        app: App,
    ):
        super().__init__(app.main_window, windowTitle="Settings", modal=True, css=App.css.SettingsDialog)

        group_labels = [
            Label(" General ", css=App.css.ReactiveLabelOn),
            Label(" Code Editor ", css=App.css.ReactiveLabelOff),
        ]

        groups_panel = VBoxPanel(group_labels + [W(stretch=1)], spacing=0, margins=0)
        groups_panel.setStyleSheet(App.css.SettingGroupsPanel)

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

        def show_general(_):
            general_settings.setVisible(True)
            code_editor_settings.setVisible(False)
            group_labels[0].setStyleSheet(App.css.ReactiveLabelOn)
            group_labels[1].setStyleSheet(App.css.ReactiveLabelOff)

        def show_code_editor(_):
            general_settings.setVisible(False)
            code_editor_settings.setVisible(True)
            group_labels[0].setStyleSheet(App.css.ReactiveLabelOff)
            group_labels[1].setStyleSheet(App.css.ReactiveLabelOn)

        group_labels[0].mousePressEvent = show_general
        group_labels[1].mousePressEvent = show_code_editor

        self.setLayout(HBoxLayout([groups_panel, W(settings_container, stretch=2)]))
