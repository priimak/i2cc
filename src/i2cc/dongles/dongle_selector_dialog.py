import sys

import serial.tools.list_ports as slp
from PySide6.QtGui import QPalette
from pytide6 import ComboBox, HBoxPanel, Label, Prompt, VBoxLayout, W
from pytide6.palette import Palette
from sprats.collections import Variable

from i2cc.app import App
from i2cc.dongles.dongles import SUPPORTED_DONGLES, SUPPORTED_DONGLES_DICT
from i2cc.gui_tools import XButton


class DongleSelectorDialog(Prompt[bool]):
    def __init__(self, app: App):
        super().__init__(app.main_window, windowTitle="Select dongle to connect to", default_value=False)
        self.setAutoFillBackground(True)
        self.setPalette(Palette(QPalette.ColorRole.Window, App.colors.background_common))

        ports = [p.device for p in slp.comports() if SUPPORTED_DONGLES[0].comp_port_filter[sys.platform](p)]
        if ports == []:
            ports = [""]

        com_ports = ComboBox(items=ports, current_selection=ports[0])
        label_and_ports_selector = HBoxPanel([Label("COM Port"), com_ports])

        def update_com_ports_combo_box(make_and_model: str | None):
            if not SUPPORTED_DONGLES_DICT[make_and_model].com_port_required:
                com_ports.clear()
                label_and_ports_selector.setVisible(False)
            else:
                label_and_ports_selector.setVisible(True)
                ports = [
                    p if isinstance(p, str) else p.device
                    for p in SUPPORTED_DONGLES_DICT[make_and_model].port_supplier[sys.platform]()
                    if SUPPORTED_DONGLES_DICT[make_and_model].comp_port_filter[sys.platform](p)
                ]
                if ports == []:
                    ports = [""]
                com_ports.clear()
                com_ports.addItems(ports)
                com_ports.setCurrentText(ports[0])

        self.dongle_id = Variable(
            SUPPORTED_DONGLES[0].make_and_model,
            valid_values=[a.make_and_model for a in SUPPORTED_DONGLES],
            on_value_change=update_com_ports_combo_box,
        )

        def ok():
            dongle_ref = SUPPORTED_DONGLES_DICT[self.dongle_id.value]
            com_port = com_ports.currentText()
            if com_port == "" and dongle_ref.com_port_required:
                app.show_error("You cannot select this dongle without COM port it is deemed to be connected")
            else:
                try:
                    app.i2c_master.value = dongle_ref.cons(com_port, app.i2c_logger)
                    app.persistence.config.set_value(
                        "last_selected_device", {"make_and_model": self.dongle_id.value, "port": com_port}
                    )
                    self.retval = True
                    self.close()
                except Exception as ex:
                    app.show_error(f"Failed to use selected dongle.\n\n{ex}")

        self.setLayout(
            VBoxLayout(
                [
                    HBoxPanel([Label("Make and Model"), ComboBox(reactive_variable=self.dongle_id)]),
                    label_and_ports_selector,
                    W(stretch=1),
                    HBoxPanel(
                        [
                            W(stretch=1),
                            XButton("Ok", on_clicked=ok, auto_default=True),
                            XButton("Cancel", on_clicked=self.close, auto_default=False),
                        ]
                    ),
                ]
            )
        )


def select_dongle(app: App) -> bool:
    return DongleSelectorDialog(app).prompt()
