import sys
from typing import override

from PySide6 import QtGui
from PySide6.QtCore import QByteArray, QLockFile, QSize, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
    QTabWidget,
)
from pytide6 import (
    HBoxPanel,
    Label,
    MainWindow,
    Splitter,
    VBoxPanel,
    W,
    set_geometry,
)
from sprats.config import AppPersistence

from i2cc.app import App
from i2cc.commands_panel import CommandsPanel
from i2cc.custom_commands.custom_commands_panel import CustomCommandsPanel
from i2cc.dongles.dongle_selector_dialog import select_dongle
from i2cc.dongles.dongles import SUPPORTED_DONGLES_DICT, mk_DummyI2CMaster
from i2cc.find_actions_dialog import FindActionDialog
from i2cc.i2c_log import LogLineLabel
from i2cc.i2c_op_thread import Quit
from i2cc.menus import MainMenuBar
from i2cc.project.opened_project_label import OpenedProjectLabel
from i2cc.project.project_nodes_panel import ProjectNotes
from i2cc.registers.reglist_panel import RegListPanel
from i2cc.results_panel import ResultsPanel


class InfoPanel(HBoxPanel):
    def __init__(self, app: App):
        super().__init__(background_color="#f1f1f1")

        i2c_master_container = app.i2c_master.value
        self.selected_dongle_label = Label(
            ""
            if i2c_master_container is None
            else (i2c_master_container.display_name + " :: " + i2c_master_container.port),
            css="border: 1px solid black;",
        )
        app.i2c_master.register_value_change_callback(
            lambda m: self.selected_dongle_label.setText(m.display_name + " :: " + m.port)
        )
        self.log_line = LogLineLabel()
        app.show_last_i2c_log_message = self.log_line.set_i2c_log_message

        self.layout().addWidgets(
            [
                OpenedProjectLabel(app),
                W(self.log_line, stretch=1),
                self.selected_dongle_label,
            ]
        )


class I2CDriverWindow(MainWindow):
    def __init__(self, screen_dim: tuple[int, int], app: App):
        super().__init__(
            objectName="MainWindow", windowTitle="I2C Commander", css="QMainWindow { background-color: #ffffff; }"
        )
        set_geometry(
            app_state=app.persistence.state,
            widget=self,
            screen_dim=screen_dim,
            win_size_fraction=0.7,
        )

        self.app = app
        self.info_panel = InfoPanel(app)

        self.res_table = ResultsPanel(self.app)
        left_panel = VBoxPanel(widgets=[self.res_table], background_color="gray", margins=1)

        self.cpanel = CommandsPanel(app)
        self.cpanel.setBackgroundColor("lightgreen")

        right_bottom_panel = QTabWidget()
        right_bottom_panel.setDocumentMode(True)
        self.reg_list_panel = RegListPanel(app)
        right_bottom_panel.addTab(self.reg_list_panel, "RegList")

        self.custom_commands_panel = CustomCommandsPanel(app)
        right_bottom_panel.addTab(self.custom_commands_panel, "User defined commands")
        right_bottom_panel.addTab(ProjectNotes(app), "Project notes")

        right_panel = VBoxPanel(
            widgets=[
                VBoxPanel([self.cpanel], background_color="black", margins=1),
                W(right_bottom_panel, stretch=2),
            ],
            margins=0,
        )
        self.hsplitter = Splitter(
            Qt.Orientation.Horizontal,
            childrenCollapsible=False,
            handleWidth=8,
            widgets=[left_panel, right_panel],
        )
        self.setCentralWidget(
            VBoxPanel(
                widgets=[W(self.hsplitter, stretch=2), self.info_panel],
                spacing=0,
                margins=0,
            )
        )

        app.connect_show_register_value(self.res_table.show_register_value)

        self.main_menu_bar = self.setMenuBar(MainMenuBar(self.app, dialogs_parent=self))
        self.app.exit_application[0] = self.exit_application

    def keyPressEvent(self, event: QtGui.QKeyEvent, /) -> None:
        if event.key() == Qt.Key.Key_A and event.modifiers() == (
            Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier
        ):
            FindActionDialog(self.app).exec()
        else:
            super().keyPressEvent(event)

    def exit_application(self):
        self.close()

    @override
    def closeEvent(self, event: QCloseEvent):
        self.app.op_thread.commands.put(Quit())
        self.app.persistence.state.save_geometry(self.objectName(), self.saveGeometry())

        self.app.persistence.state.set_value(
            "main_splitter_state",
            self.hsplitter.saveState().toBase64(QByteArray.Base64Option.Base64Encoding).data().decode("utf-8"),
        )

        self.app.persistence.state.set_value(
            "reg_list_splitter_state",
            self.reg_list_panel.splitter.saveState()
            .toBase64(QByteArray.Base64Option.Base64Encoding)
            .data()
            .decode("utf-8"),
        )

        self.custom_commands_panel.save_state()

        self.app.project.save()
        event.accept()

    def restore(self):
        spl_state = self.app.persistence.state.get_value("main_splitter_state")
        if spl_state is not None:
            self.hsplitter.restoreState(QByteArray.fromBase64(spl_state.encode("utf-8")))
        spl_state = self.app.persistence.state.get_value("reg_list_splitter_state")
        if spl_state is not None:
            self.reg_list_panel.splitter.restoreState(QByteArray.fromBase64(spl_state.encode("utf-8")))
        self.custom_commands_panel.restore()

        # following will trigger execution of __start__ command in the opened project if such command is present.
        self.app.request_commands_reload(False)

        last_selected_device = self.app.persistence.config.get_value("last_selected_device", dict)
        if last_selected_device == dict():
            QMessageBox.information(
                self,
                "Info",
                "<H3>Please select I2CDongle to use.</H3>"
                ""
                "Once selected you will <b>NOT</b> be prompted again on start up of "
                'this application unless connection to the dongle fails. You can, however, go to the menu "Dongle" '
                'and select option "Connect" to pick different dongle.',
            )
            if not select_dongle(self.app):
                QMessageBox.information(
                    self, "Info", "Dongle <em>DummyI2CDriver</em> used for demo purposes will be used"
                )
                self.app.i2c_master.value = mk_DummyI2CMaster("COM", None)
        else:
            try:
                saved_speed = self.app.persistence.config.get_by_xpath("/speed")
                self.app.i2c_master.value = SUPPORTED_DONGLES_DICT[last_selected_device["make_and_model"]].cons(
                    last_selected_device["port"], self.app.i2c_logger
                )
                self.cpanel.speed_selector.setCurrentText(saved_speed)
            except Exception:
                self.app.show_error(
                    "Failed to connected to last used dongle. Please select a new one or connect previously "
                    "used one and restart the application"
                )
                if not select_dongle(self.app):
                    QMessageBox.information(
                        self, "Info", "Dongle <em>DummyI2CDriver</em> used for demo purposes will be used"
                    )
                    self.app.i2c_master.value = mk_DummyI2CMaster("COM", None)
                    self.app.persistence.config.set_value(
                        "last_selected_device", {"make_and_model": "Demo :: DummyI2CDriver", "port": "COM"}
                    )


def main():
    app = QApplication(sys.argv)

    persistence = AppPersistence(
        app_name="i2cc",
        override_config_if_different_version=True,
        init_config_data={
            "speed": "100",
            "config_version": 2,
            "last_open_project": "default",
            "last_selected_device": {},
        },
    )

    # Only one instance of this application can be run at a time. Following code attains that by using POSIX lock file.
    lock_file_path = (persistence.config.app_name_config_dir / "lock").absolute()
    lock_file = QLockFile(f"{lock_file_path}")
    lock_file.setStaleLockTime(0)
    if not lock_file.tryLock(0):
        QMessageBox.critical(None, "Error", "Application i2cgui is already running.")
        sys.exit(1)

    # Will init main window size to be some fraction of the screen size unless defined elsewhere
    screen_dim: QSize = app.primaryScreen().size()
    screen_width, screen_height = screen_dim.width(), screen_dim.height()

    try:
        application = App(persistence, app)
        win = I2CDriverWindow(screen_dim=(screen_width, screen_height), app=application)
        application._main_window = win
        win.show()
        win.activateWindow()
        win.raise_()
        win.restore()
        application.init()

        sys.exit(app.exec())
    except Exception as ex:
        QMessageBox.critical(None, "Error", f"Error: {ex}")
        sys.exit(1)


if __name__ == "__main__":
    main()
