from PySide6.QtWidgets import QMessageBox
from pytide6 import ComboBox, Dialog, HBoxPanel, Label, PushButton, VBoxLayout, VBoxPanel, W
from pytide6.inputs import LineEdit
from sprats.collections import Variable

from i2cc.app import App
from i2cc.dongles.dongles import I2CMasterContainer
from i2cc.i2c_op_thread import I2CBusScan


class SelectDeviceDialog(Dialog):
    def __init__(self, app: App, addresses: list[int]):
        super().__init__(app.main_window, windowTitle="Select device", modal=True)
        addrs = [f"0x{a:X}" for a in addresses]
        available_addresses = Variable(addrs[0], valid_values=addrs)

        def ok():
            app.select_device_address(available_addresses.value)
            self.close()

        self.setLayout(
            VBoxLayout(
                [
                    HBoxPanel([Label("Select i2c device to use"), ComboBox(reactive_variable=available_addresses)]),
                    W(stretch=1),
                    HBoxPanel(
                        [W(stretch=1), PushButton("Ok", on_clicked=ok), PushButton("Cancel", on_clicked=self.close)]
                    ),
                ]
            )
        )


class AddrSelector(ComboBox):
    def __init__(self, app: App):
        super().__init__(items=[], on_text_change=app.device_address_changed)
        self.app = app
        self.available_addresses = []
        app.op_thread.set_available_addresses.connect(self.set_addresses)
        self.app.select_device_address = self.setCurrentText

    def set_addresses(self, addresses: list[int]) -> None:
        if self.available_addresses != addresses:
            self.available_addresses.clear()
            self.available_addresses.extend(addresses)
            self.clear()
            self.addItems([f"0x{a:X}" for a in addresses])
            self.app.device_address_changed(self.currentText())


class SpeedSelector(ComboBox):
    def __init__(self, app: App):
        super().__init__(
            items=[f"{s} KHz" for s in app.i2c.list_clk_speeds()],
            current_selection=app.persistence.config.get_by_xpath("/speed"),
        )
        self.app = app
        self.app.i2c.set_clk_speed(int(app.persistence.config.get_by_xpath("/speed")[0:3]))

        def change_speed(new_speed: str) -> None:
            if new_speed != "":
                self.app.i2c.set_clk_speed(int(new_speed[0:3]))
                self.setCurrentText(f"{self.app.i2c.get_clk_speed()} KHz")
                self.app.persistence.config.set_by_xpath("/speed", self.currentText())

        self.currentTextChanged.connect(change_speed)


class PullUpResistorSelector(ComboBox):
    def __init__(self, app: App):
        super().__init__(
            items=app.i2c.list_pullups(),
            current_selection=app.persistence.config.get_by_xpath("/pullup"),
        )
        self.app = app
        self.setCurrentText(self.app.i2c.get_pullup())

        def change_pullup_value(new_resistance: str) -> None:
            if new_resistance != "":
                self.app.i2c.set_pullup(new_resistance)

        self.currentTextChanged.connect(change_pullup_value)


class CommandsPanel(VBoxPanel):
    def __init__(self, app: App):
        super().__init__(margins=1, background_color="gray")
        self.app = app
        self.addr_selector = AddrSelector(app)
        self.speed_selector = SpeedSelector(app)
        self.pullup_selector = PullUpResistorSelector(app)
        app.i2c_master_changed.append(self.i2c_master_changed)
        app.scan_and_show_select_device_dialog = self.scan_and_show_select_device_dialog

        self.addWidget(
            HBoxPanel(
                [
                    W(Label(""), stretch=1),
                    Label("I2C Device Address"),
                    self.addr_selector,
                    PushButton("Scan", on_clicked=self.do_i2c_bus_scan),
                    Label("  |  "),
                    Label("Speed"),
                    self.speed_selector,
                    Label("  |  "),
                    Label("Pullup"),
                    self.pullup_selector,
                    W(Label(""), stretch=1),
                ]
            )
        )

        reg_addres_input = []

        def do_read_register(_: str):
            app.read_register()
            reg_addres_input[0].selectAll()

        reg_addres_input.append(
            LineEdit(
                reactive_variable=app.read_register_address_str,
                on_key_enter=do_read_register,
            )
        )

        panel = VBoxPanel(
            [
                HBoxPanel(
                    [
                        PushButton("Read Register", on_clicked=app.read_register),
                        Label(" Addr:"),
                        reg_addres_input[0],
                        Label(" Num Bytes:"),
                        ComboBox(reactive_variable=app.read_register_num_bytes),
                        W(Label(""), stretch=1),
                    ]
                ),
                HBoxPanel(
                    [
                        PushButton("Write Register", on_clicked=app.write_register),
                        Label(" Addr:"),
                        LineEdit(reactive_variable=app.write_register_address_str),
                        Label(" Value:"),
                        LineEdit(reactive_variable=app.write_register_value_str),
                        Label(" Num Bytes:"),
                        ComboBox(reactive_variable=app.write_register_num_bytes),
                        W(Label(""), stretch=1),
                    ]
                ),
            ],
            margins=0,
        )
        self.addWidget(HBoxPanel([W(Label(""), stretch=1), panel, W(Label(""), stretch=1)]))

    def do_i2c_bus_scan(self) -> None:
        scan_dialog = QMessageBox(self.app.main_window)
        scan_dialog.setStandardButtons(QMessageBox.StandardButton.Cancel)
        connection = []

        def close():
            scan_dialog.close()
            self.app.op_thread.dismiss_scan_dialog.disconnect(connection[0])

        connection.append(self.app.op_thread.dismiss_scan_dialog.connect(close))
        scan_dialog.setIcon(QMessageBox.Icon.Information)
        scan_dialog.setText("Performing I2C bus scan ...")
        scan_dialog.setModal(True)
        self.app.op_thread.commands.put(I2CBusScan())
        scan_dialog.exec()

    def scan_and_show_select_device_dialog(self) -> None:
        self.do_i2c_bus_scan()
        SelectDeviceDialog(self.app, self.addr_selector.available_addresses).show()

    def i2c_master_changed(self, i2c: I2CMasterContainer) -> None:
        self.pullup_selector.clear()
        pullup_value_to_set = i2c.driver.get_pullup()
        self.pullup_selector.addItems(i2c.driver.list_pullups())
        self.pullup_selector.setCurrentText(pullup_value_to_set)

        self.speed_selector.clear()
        clock_speed_to_set = f"{i2c.driver.get_clk_speed()} KHz"
        self.speed_selector.addItems([f"{s} KHz" for s in i2c.driver.list_clk_speeds()])
        self.speed_selector.setCurrentText(clock_speed_to_set)
