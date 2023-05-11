from typing import List
from typing import Optional
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pymodbus.pdu import ModbusResponse

from unipi_control.config import Config, HardwareData, HardwareDefinition, HardwareType, LogPrefix, logger
from unipi_control.extensions.eastron import EastronSDM120M
from unipi_control.features import DigitalInput, DigitalOutput, FeatureMap, Led, Relay
from unipi_control.modbus import ModbusCacheData, ModbusClient, check_modbus_call


class Board:
    """Class to parse board features and register it to the ``FeatureMap``."""

    def __init__(self, neuron, versions: list, major_group: int) -> None:
        """Initialize board.

        Parameters
        ----------
        neuron: class
            The Neuron class for registering features.
        versions: list
            The modbus firmware version register (1000).
        major_group: int
            The board group number.
        """
        self.neuron: Neuron = neuron
        self.definition: HardwareDefinition = neuron.hardware["definitions"][0]
        self.major_group: int = major_group
        self.firmware = f"{(versions[0] & 0xff00) >> 8}.{(versions[0] & 0x00ff)}"

    def _parse_feature_ro(self, max_count: int, modbus_feature: dict) -> None:
        if modbus_feature["major_group"] == self.major_group:
            for index in range(0, max_count):
                ro: Relay = Relay(
                    neuron=self.neuron,
                    definition=self.definition,
                    index=index,
                    **modbus_feature,
                )

                self.neuron.features.register(ro)

    def _parse_feature_di(self, max_count: int, modbus_feature: dict) -> None:
        if modbus_feature["major_group"] == self.major_group:
            for index in range(0, max_count):
                di: DigitalInput = DigitalInput(
                    neuron=self.neuron,
                    definition=self.definition,
                    index=index,
                    **modbus_feature,
                )

                self.neuron.features.register(di)

    def _parse_feature_do(self, max_count: int, modbus_feature: dict) -> None:
        if modbus_feature["major_group"] == self.major_group:
            for index in range(0, max_count):
                do: DigitalOutput = DigitalOutput(
                    neuron=self.neuron,
                    definition=self.definition,
                    index=index,
                    **modbus_feature,
                )

                self.neuron.features.register(do)

    def _parse_feature_led(self, max_count: int, modbus_feature: dict) -> None:
        if modbus_feature["major_group"] == self.major_group:
            for index in range(0, max_count):
                led: Led = Led(
                    neuron=self.neuron,
                    definition=self.definition,
                    index=index,
                    **modbus_feature,
                )

                self.neuron.features.register(led)

    def _parse_feature(self, modbus_feature: dict) -> None:
        max_count: int = modbus_feature["count"]
        feature_type: str = modbus_feature["feature_type"].lower()

        if func := getattr(self, f"_parse_feature_{feature_type}", None):
            func(max_count, modbus_feature)

    def parse_features(self) -> None:
        """Parse features from hardware definition."""
        for modbus_feature in self.definition.modbus_features:
            self._parse_feature(modbus_feature)


class Neuron:
    """Class that reads all boards and scan modbus registers from an Unipi Neuron, extensions and third-party devices.

    The Unipi Neuron has one or more boards and each board has its features (e.g. Relay, Digital Input). This class
    reads out all boards and append it to the boards ``list``.

    Attributes
    ----------
    modbus_client: ModbusClient
        A modbus tcp client.
    hardware: HardwareData
        The Unipi Neuron hardware definitions.
    boards: list
        All available boards from the Unipi Neuron.
    features: FeatureMap
        All registered features (e.g. Relay, Digital Input, ...) from the
        Unipi Neuron.
    """

    def __init__(self, config: Config, modbus_client: ModbusClient) -> None:
        self.config: Config = config
        self.modbus_client: ModbusClient = modbus_client
        self.hardware: HardwareData = HardwareData(config=config)
        self.boards: List[Board] = []
        self.features = FeatureMap()

        self.modbus_cache_data: ModbusCacheData = ModbusCacheData(
            modbus_client=self.modbus_client,
            hardware=self.hardware,
        )

    async def init(self) -> None:
        """Initialize internal and external hardware."""
        await self.read_boards()
        await self.read_extensions()

    async def read_boards(self) -> None:
        """Scan Modbus TCP and initialize Unipi Neuron board."""
        logger.info("%s Reading SPI boards", LogPrefix.MODBUS)

        for index in (1, 2, 3):
            response: Optional[ModbusResponse] = await check_modbus_call(
                self.modbus_client.tcp.read_input_registers,
                data={
                    "address": 1000,
                    "count": 1,
                    "slave": index,
                },
            )

            if response:
                board = Board(neuron=self, versions=getattr(response, "registers", [0, 0]), major_group=index)
                board.parse_features()

                self.boards.append(board)
            else:
                logger.info("%s No board on SPI %s", LogPrefix.MODBUS, index)

        await self.modbus_cache_data.scan("tcp", hardware_types=[HardwareType.NEURON])

    async def read_extensions(self) -> None:
        """Scan Modbus RTU and initialize extension classes."""
        logger.info("%s Reading extensions", LogPrefix.MODBUS)

        for definition in self.hardware["definitions"][1:]:
            if definition.manufacturer.lower() == "eastron" and definition.model == "SDM120M":
                await EastronSDM120M(neuron=self, definition=definition).init()

        await self.modbus_cache_data.scan("serial", hardware_types=[HardwareType.EXTENSION])
