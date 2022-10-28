from typing import Dict
from typing import List

from unipi_control.config import Config
from unipi_control.config import HardwareData
from unipi_control.config import HardwareType
from unipi_control.config import LogPrefix
from unipi_control.config import logger
from unipi_control.features import DigitalInput
from unipi_control.features import DigitalOutput
from unipi_control.features import FeatureMap
from unipi_control.features import Led
from unipi_control.features import Relay
from unipi_control.modbus.cache import ModbusCacheData
from unipi_control.modbus.cache import ModbusClient


class Board:
    """Class to parse board features and register it to the ``FeatureMap``."""

    def __init__(self, neuron, versions: list, major_group: int):
        """Initialize board.

        Parameters
        ----------
        neuron : class
            The Neuron class for registering features.
        versions : list
            The modbus firmware version register (1000).
        major_group : int
            The board group number.
        """
        self.neuron: Neuron = neuron
        self.major_group: int = major_group
        self.firmware = f"{(versions[0] & 0xff00) >> 8}.{(versions[0] & 0x00ff)}"

    def _parse_feature_ro(self, max_count: int, modbus_feature: dict):
        major_group: str = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                circuit: str = f"{feature_type.lower()}_{major_group}_{index + 1:02d}"

                ro = Relay(
                    board=self,
                    short_name=modbus_feature["type"],
                    circuit=circuit,
                    major_group=modbus_feature["major_group"],
                    mask=(0x1 << (index % 16)),
                    reg=modbus_feature["val_reg"],
                    coil=modbus_feature["val_coil"] + index,
                )

                self.neuron.features.register(ro)

    def _parse_feature_di(self, max_count: int, modbus_feature: dict):
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                circuit: str = f"{feature_type.lower()}_{major_group}_{index + 1:02d}"

                di = DigitalInput(
                    board=self,
                    short_name=modbus_feature["type"],
                    circuit=circuit,
                    major_group=modbus_feature["major_group"],
                    reg=modbus_feature["val_reg"],
                    mask=(0x1 << (index % 16)),
                )

                self.neuron.features.register(di)

    def _parse_feature_do(self, max_count: int, modbus_feature: dict):
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                circuit: str = f"{feature_type.lower()}_{major_group}_{index + 1:02d}"

                do = DigitalOutput(
                    board=self,
                    short_name=modbus_feature["type"],
                    circuit=circuit,
                    major_group=modbus_feature["major_group"],
                    mask=(0x1 << (index % 16)),
                    reg=modbus_feature["val_reg"],
                    coil=modbus_feature["val_coil"] + index,
                )

                self.neuron.features.register(do)

    def _parse_feature_led(self, max_count: int, modbus_feature: dict):
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                circuit: str = f"{feature_type.lower()}_{major_group}_{index + 1:02d}"

                led = Led(
                    board=self,
                    short_name=modbus_feature["type"],
                    circuit=circuit,
                    major_group=modbus_feature["major_group"],
                    mask=(0x1 << (index % 16)),
                    reg=modbus_feature["val_reg"],
                    coil=modbus_feature["val_coil"] + index,
                )

                self.neuron.features.register(led)

    def _parse_feature(self, modbus_feature: dict):
        max_count: int = modbus_feature["count"]
        feature_type: str = modbus_feature["type"].lower()

        if func := getattr(self, f"_parse_feature_{feature_type}", None):
            func(max_count, modbus_feature)

    def parse_features(self):
        neuron_definition: Dict[str, dict] = self.neuron.hardware["definitions"]["neuron"]
        modbus_features: dict = neuron_definition["modbus_features"]

        for modbus_feature in modbus_features:
            self._parse_feature(modbus_feature)


class Neuron:
    """Class that reads all boards and scan modbus registers from an Unipi Neuron, extensions and third-party devices.

    The Unipi Neuron has one or more boards and each board has its features (e.g. Relay, Digital Input). This class
    reads out all boards and append it to the boards ``list``.

    Attributes
    ----------
    modbus_client : ModbusClient
        A modbus tcp client.
    hardware : HardwareData
        The Unipi Neuron hardware definitions.
    boards : list
        All available boards from the Unipi Neuron.
    features : FeatureMap
        All registered features (e.g. Relay, Digital Input, ...) from the
        Unipi Neuron.
    """

    def __init__(self, config: Config, modbus_client: ModbusClient):
        self.config: Config = config
        self.modbus_client: ModbusClient = modbus_client
        self.hardware: HardwareData = HardwareData(config=config)
        self.boards: List[Board] = []
        self.features = FeatureMap()

        self.modbus_cache_data: ModbusCacheData = ModbusCacheData(
            self.modbus_client,
            hardware_definitions=self.hardware["definitions"],
        )

    async def read_boards(self):
        logger.info("%s Reading SPI boards", LogPrefix.MODBUS)
        await self.modbus_cache_data.scan([HardwareType.NEURON, HardwareType.THIRD_PARTY])

        for index in (1, 2, 3):
            response = await self.modbus_client.tcp.read_input_registers(address=1000, count=1, slave=index)

            if response.isError():
                logger.info("%s No board on SPI %s", LogPrefix.MODBUS, index)
            else:
                board = Board(self, versions=response.registers, major_group=index)
                board.parse_features()

                self.boards.append(board)
