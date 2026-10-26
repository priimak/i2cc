from dataclasses import dataclass
from typing import Callable, NamedTuple

import serial.tools.list_ports as slp
from i2c_api import I2CLogger, I2CMaster
from i2c_drivers import I2CMasterFT232H, I2CMasterI2CDriver, I2CMasterMCP2221
from pyftdi.ftdi import Ftdi
from pyftdi.usbtools import UsbTools
from serial.tools.list_ports_common import ListPortInfo

from i2cc.dongles.dummy_i2cmaster import DummyI2CMaster


@dataclass(frozen=True)
class I2CMasterContainer:
    driver: I2CMaster
    port: str
    display_name: str


type DonglePort = ListPortInfo | str


class DongleRef(NamedTuple):
    make_and_model: str
    cons: Callable[[str, I2CLogger], I2CMasterContainer]
    comp_port_filter: dict[str, Callable[[DonglePort], bool]]
    com_port_required: bool
    port_supplier: dict[str, Callable[[], list[DonglePort]]] | None


def mk_I2CMasterI2CDriver(port: str, logger: I2CLogger) -> I2CMasterContainer:
    return I2CMasterContainer(driver=I2CMasterI2CDriver(port, logger=logger), port=port, display_name="I2CDriver")


def mk_I2CMasterMCP2221(port: str, logger: I2CLogger) -> I2CMasterContainer:
    return I2CMasterContainer(driver=I2CMasterMCP2221(logger=logger), port=port, display_name="MCP2221")


def mk_I2CMasterFT232H(port: str, logger: I2CLogger) -> I2CMasterContainer:
    return I2CMasterContainer(driver=I2CMasterFT232H(logger=logger), port=port, display_name="FTH232H")


def mk_DummyI2CMaster(port: str, logger: I2CLogger) -> I2CMasterContainer:
    return I2CMasterContainer(driver=DummyI2CMaster(), port=port, display_name="DummyI2CDriver")


def ft232h_ports() -> list[str]:
    return [
        d[0]
        for d in UsbTools.build_dev_strings("ftdi", Ftdi.VENDOR_IDS, Ftdi.PRODUCT_IDS, Ftdi.list_devices())
        if "232h" in d[0]
    ]


SUPPORTED_DONGLES = [
    DongleRef(
        make_and_model="Demo :: DummyI2CDriver",
        cons=mk_DummyI2CMaster,
        comp_port_filter={
            "win32": lambda _: True,
            "cygwin": lambda _: True,
            "linux": lambda _: True,
        },
        port_supplier={
            "win32": lambda: slp.comports(),
            "cygwin": lambda: slp.comports(),
            "linux": lambda: slp.comports(),
        },
        com_port_required=True,
    ),
    DongleRef(
        make_and_model="Excamera Labs :: I2CDriver",
        cons=mk_I2CMasterI2CDriver,
        comp_port_filter={
            "win32": lambda _: True,
            "cygwin": lambda _: True,
            "linux": lambda p: p.product == "FT230X Basic UART",
        },
        port_supplier={
            "win32": lambda: slp.comports(),
            "cygwin": lambda: slp.comports(),
            "linux": lambda: slp.comports(),
        },
        com_port_required=True,
    ),
    DongleRef(
        make_and_model="Microchip :: MCP2221",
        cons=mk_I2CMasterMCP2221,
        comp_port_filter={},
        com_port_required=False,
        port_supplier={
            "win32": lambda: "",
            "cygwin": lambda: "",
            "linux": lambda: "",
        },
    ),
    DongleRef(
        make_and_model="FTDI :: FT232H",
        cons=mk_I2CMasterFT232H,
        comp_port_filter={
            "win32": lambda _: True,
            "cygwin": lambda _: True,
            "linux": lambda _: True,
        },
        com_port_required=True,
        port_supplier={
            "win32": lambda: ft232h_ports(),
            "cygwin": lambda: ft232h_ports(),
            "linux": lambda: ft232h_ports(),
        },
    ),
]

SUPPORTED_DONGLES_DICT = {a.make_and_model: a for a in SUPPORTED_DONGLES}
