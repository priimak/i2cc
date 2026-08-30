import sys
from typing import override

import serial.tools.list_ports as slp
from PySide6 import QtGui
from PySide6.QtCore import QByteArray, QLockFile, QSize, Qt
from PySide6.QtGui import QCloseEvent, Qt
from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
    QTabWidget,
)
from pytide6 import (
    ComboBox,
    HBoxPanel,
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
from i2cc.find_actions_dialog import FindActionDialog
from i2cc.i2c_op_thread import Quit
from i2cc.log_line_label import LogLineLabel
from i2cc.menus import MainMenuBar
from i2cc.opened_project_label import OpenedProjectLabel
from i2cc.reglist_panel import RegListPanel
from i2cc.results_panel import ResultsPanel


def get_ports() -> list[str]:
    return [p.device for p in slp.comports() if p.product == "FT230X Basic UART"]


class COMPortSelector(ComboBox):
    def __init__(self, app: App):
        super().__init__(items=get_ports())
        self.app = app

        self.currentTextChanged.connect(self.app.set_port)
        self.currentTextChanged.emit(self.currentText())


class InfoPanel(HBoxPanel):
    def __init__(self, app: App):
        super().__init__(background_color="#f1f1f1")

        self.com_port_selector = COMPortSelector(app)
        self.log_line = LogLineLabel()
        app.show_last_i2c_log_message = self.log_line.set_i2c_log_message

        self.layout().addWidgets(
            [
                OpenedProjectLabel(app),
                W(self.log_line, stretch=1),
                self.com_port_selector,
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

        cpanel = CommandsPanel(app)
        cpanel.setBackgroundColor("lightgreen")

        right_bottom_panel = QTabWidget()
        right_bottom_panel.setDocumentMode(True)
        self.reg_list_panel = RegListPanel(app)
        right_bottom_panel.addTab(self.reg_list_panel, "RegList")

        self.custom_commands_panel = CustomCommandsPanel(app)
        right_bottom_panel.addTab(self.custom_commands_panel, "User defined commands")

        right_panel = VBoxPanel(
            widgets=[
                VBoxPanel([cpanel], background_color="black", margins=1),
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


def main():
    app = QApplication(sys.argv)

    persistence = AppPersistence(
        app_name="i2cdgui",
        override_config_if_different_version=True,
        init_config_data={
            "speed": "100",
            "config_version": 1,
            "last_open_project": "default",
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
        if win.info_panel.com_port_selector.count() == 0:
            win.app.show_error("I2C Master device not found. Connect device and restart application.")
        application.init()

        sys.exit(app.exec())
    except Exception as ex:
        QMessageBox.critical(None, "Error", f"Error: {ex}")
        sys.exit(1)


if __name__ == "__main__":
    main()
