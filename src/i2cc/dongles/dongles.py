from dataclasses import dataclass
from typing import Callable, NamedTuple

from i2c_api import I2CLogger, I2CMaster
from i2capi_i2cdriver import I2CMasterI2CDriver
from i2capi_mcp2221.mcp2221_api import I2CMasterMCP2221
from i2cdriver import I2CDriver
from serial.tools.list_ports_common import ListPortInfo

from i2cc.dongles.dummy_i2cmaster import DummyI2CMaster


@dataclass(frozen=True)
class I2CMasterContainer:
    driver: I2CMaster
    port: str
    display_name: str


class DongleRef(NamedTuple):
    make_and_model: str
    cons: Callable[[str, I2CLogger], I2CMasterContainer]
    comp_port_filter: dict[str, Callable[[ListPortInfo], bool]]
    com_port_required: bool


def mk_I2CMasterI2CDriver(port: str, logger: I2CLogger) -> I2CMasterContainer:
    return I2CMasterContainer(
        driver=I2CMasterI2CDriver(I2CDriver(port), logger=logger), port=port, display_name="I2CDriver"
    )


def mk_I2CMasterMCP2221(port: str, logger: I2CLogger) -> I2CMasterContainer:
    return I2CMasterContainer(driver=I2CMasterMCP2221(logger=logger), port=port, display_name="MCP2221")


def mk_DummyI2CMaster(port: str, logger: I2CLogger) -> I2CMasterContainer:
    return I2CMasterContainer(driver=DummyI2CMaster(), port=port, display_name="DummyI2CDriver")


SUPPORTED_DONGLES = [
    DongleRef(
        make_and_model="Demo :: DummyI2CDriver",
        cons=mk_DummyI2CMaster,
        comp_port_filter={
            "win32": lambda _: True,
            "cygwin": lambda _: True,
            "linux": lambda _: True,
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
        com_port_required=True,
    ),
    DongleRef(
        make_and_model="Microchip :: MCP2221", cons=mk_I2CMasterMCP2221, comp_port_filter={}, com_port_required=False
    ),
]

SUPPORTED_DONGLES_DICT = {a.make_and_model: a for a in SUPPORTED_DONGLES}
