from api.settings import logger
from config import HardwareDefinition
from devices import devices
from devices import RELAY


class Relay:
    name = "Relay"
    dev = "relay"
    dev_type = "physical"

    def __init__(self, circuit: str, coil: int, *args, **kwargs):
        self.circuit = circuit


class Board:
    def __init__(self, major_group: int):
        hw = HardwareDefinition()

        self.major_group: int = major_group
        self._modbus_features: list = hw["neuron_definition"]["modbus_features"]

    def parse_feature_ro(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                _relay = Relay(
                    circuit="%s_%s_%02d" % (modbus_feature["type"].lower(), major_group, index + 1),
                    coil=modbus_feature['val_coil'] + index,
                    **modbus_feature,
                )

                devices.register(RELAY, _relay)

    def parse_feature_do(self, max_count: int, modbus_feature: list) -> None:
        self.parse_feature_ro(max_count, modbus_feature)

    def parse_feature(self, modbus_feature: dict) -> None:
        max_count: int = modbus_feature["count"]
        feature_type: str = modbus_feature["type"].lower()
        func = getattr(self, f"parse_feature_{feature_type}", None)

        if func:
            func(max_count, modbus_feature)

    def parse_definition(self) -> None:
        for modbus_feature in self._modbus_features:
            self.parse_feature(modbus_feature)


class Neuron:
    def __init__(self, modbus_client):
        self._modbus_client = modbus_client
        self.boards: list = []

    async def read_boards(self) -> None:
        logger.info("Reading SPI boards")

        for index in (1, 2, 3):
            request_fw = await self._modbus_client.read_input_registers(1000, 1, unit=index)

            if request_fw.isError():
                logger.info(f"No board on SPI {index}")
            else:
                Board(major_group=index).parse_definition()
