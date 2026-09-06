from i2c_api.log import (
    ACK,
    DATA_MISO,
    DATA_MOSI,
    NACK,
    READ,
    RESTART,
    START,
    STOP,
    WRITE,
    I2CTransactionElement,
)
from pytide6 import RichTextLabel


def i2c_log_message_to_str(e: I2CTransactionElement) -> str:
    match e:
        case START():
            return "<span style='background-color: lightblue;'>S</span>"
        case STOP():
            return "<span style='background-color: lightblue;'>P</span>"
        case RESTART():
            return "<span style='background-color: lightblue;'>Sr</span>"
        case READ():
            return "<span style='background-color: lightblue;'>R</span>"
        case WRITE():
            return "<span style='background-color: lightblue;'>W</span>"
        case ACK():
            return "<span style='background-color: lightgreen;'>Ack</span>"
        case NACK():
            return "<span style='background-color: red; color: white;'>Nack</span>"
        case DATA_MOSI(payload):
            return f"<span style='background-color: yellow;'>{payload.bin}</span>"
        case DATA_MISO(payload):
            return f"<span style='background-color: pink;'>{payload.bin}</span>"
        case _:
            return ""


class LogLineLabel(RichTextLabel):
    def __init__(self):
        super().__init__("<em>Last I2C operation:</em>", css="border: 1px solid black;")

    def set_log_message(self, log_message: str):
        self.setText(log_message)

    def set_i2c_log_message(self, log_message: list[I2CTransactionElement]):
        join = " ".join([i2c_log_message_to_str(e) for e in log_message])
        self.setText(join)
