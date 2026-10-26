from i2c_api import ExecResults, I2CMaster, I2CTransaction


class DummyI2CMaster(I2CMaster):
    def _exec(self, transaction: I2CTransaction, device_address: int = -1) -> ExecResults:
        pass

    def scan(self) -> list[int]:
        return []

    def list_pullups(self) -> list[str]:
        return ["disabled"]

    def set_pullup(self, pullup_value: str) -> None:
        pass

    def get_pullup(self) -> str:
        return "disabled"

    def list_clk_speeds(self) -> list[int]:
        return [100]

    def get_clk_speed(self) -> int:
        return 100

    def set_clk_speed(self, speed: int) -> None:
        pass

    def close(self):
        pass
