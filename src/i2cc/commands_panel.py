from pytide6 import ComboBox, HBoxPanel, Label, PushButton, VBoxPanel, W
from pytide6.inputs import LineEdit

from i2cc.app import App
from i2cc.dongles.dongles import I2CMasterContainer


class AddrSelector(ComboBox):
    def __init__(self, app: App):
        super().__init__(on_text_change=app.device_address_changed)
        self.app = app

    def scan(self) -> None:
        addrs = [f"0x{a:X}" for a in self.app.scan()]
        self.clear()
        self.addItems(addrs)
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
        self.addWidget(
            HBoxPanel(
                [
                    W(Label(""), stretch=1),
                    Label("I2C Device Address"),
                    self.addr_selector,
                    PushButton("Scan", on_clicked=self.addr_selector.scan),
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

    def i2c_master_changed(self, i2c: I2CMasterContainer) -> None:
        self.pullup_selector.clear()
        pullup_value_to_set = i2c.driver.get_pullup()
        self.pullup_selector.addItems(i2c.driver.list_pullups())
        self.pullup_selector.setCurrentText(pullup_value_to_set)

        self.speed_selector.clear()
        clock_speed_to_set = f"{i2c.driver.get_clk_speed()} KHz"
        self.speed_selector.addItems([f"{s} KHz" for s in i2c.driver.list_clk_speeds()])
        self.speed_selector.setCurrentText(clock_speed_to_set)
