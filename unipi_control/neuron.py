from typing import List
from typing import Optional

from pymodbus.pdu import ModbusResponse

from unipi_control.config import BoardConfig
from unipi_control.config import Config
from unipi_control.config import HardwareData
from unipi_control.config import HardwareType
from unipi_control.config import LogPrefix
from unipi_control.config import NeuronHardware
from unipi_control.config import logger
from unipi_control.extensions.eastron import EastronSDM120M
from unipi_control.features.map import DigitalInput
from unipi_control.features.map import DigitalOutput
from unipi_control.features.map import FeatureMap
from unipi_control.features.map import Led
from unipi_control.features.map import Relay
from unipi_control.features.neuron import Hardware
from unipi_control.features.neuron import Modbus
from unipi_control.features.utils import FeatureType
from unipi_control.modbus import ModbusCacheData
from unipi_control.modbus import ModbusClient
from unipi_control.modbus import check_modbus_call


class Board:
    """Class to parse board features and register it to the ``FeatureMap``."""

    def __init__(self, config: Config, board_config: BoardConfig, neuron_hardware: NeuronHardware) -> None:
        """Initialize board.

        Parameters
        ----------
        firmware: str
            The board firmware.
        major_group: int
            The board group number.
        """
        self.config: Config = config
        self.board_config: BoardConfig = board_config
        self.neuron_hardware: NeuronHardware = neuron_hardware

    def _parse_feature_ro(self, max_count: int, modbus_feature: dict) -> None:
        if modbus_feature["major_group"] == self.board_config.major_group:
            for index in range(0, max_count):
                ro: Relay = Relay(
                    config=self.config,
                    modbus=Modbus(
                        client=self.board_config.modbus_client,
                        cache=self.neuron_hardware.modbus_cache_data,
                        val_reg=modbus_feature["val_reg"],
                        val_coil=modbus_feature["val_coil"],
                    ),
                    hardware=Hardware(
                        major_group=self.board_config.major_group,
                        feature_type=FeatureType[modbus_feature["feature_type"]],
                        feature_index=index,
                        definition=self.neuron_hardware.definition,
                        firmware=self.board_config.firmware,
                    ),
                )

                self.neuron_hardware.features.register(ro)

    def _parse_feature_di(self, max_count: int, modbus_feature: dict) -> None:
        if modbus_feature["major_group"] == self.board_config.major_group:
            for index in range(0, max_count):
                di: DigitalInput = DigitalInput(
                    config=self.config,
                    modbus=Modbus(
                        client=self.board_config.modbus_client,
                        cache=self.neuron_hardware.modbus_cache_data,
                        val_reg=modbus_feature["val_reg"],
                    ),
                    hardware=Hardware(
                        major_group=self.board_config.major_group,
                        feature_type=FeatureType[modbus_feature["feature_type"]],
                        feature_index=index,
                        definition=self.neuron_hardware.definition,
                        firmware=self.board_config.firmware,
                    ),
                )

                self.neuron_hardware.features.register(di)

    def _parse_feature_do(self, max_count: int, modbus_feature: dict) -> None:
        if modbus_feature["major_group"] == self.board_config.major_group:
            for index in range(0, max_count):
                do: DigitalOutput = DigitalOutput(
                    config=self.config,
                    modbus=Modbus(
                        client=self.board_config.modbus_client,
                        cache=self.neuron_hardware.modbus_cache_data,
                        val_reg=modbus_feature["val_reg"],
                        val_coil=modbus_feature["val_coil"],
                    ),
                    hardware=Hardware(
                        major_group=self.board_config.major_group,
                        feature_type=FeatureType[modbus_feature["feature_type"]],
                        feature_index=index,
                        definition=self.neuron_hardware.definition,
                        firmware=self.board_config.firmware,
                    ),
                )

                self.neuron_hardware.features.register(do)

    def _parse_feature_led(self, max_count: int, modbus_feature: dict) -> None:
        if modbus_feature["major_group"] == self.board_config.major_group:
            for index in range(0, max_count):
                led: Led = Led(
                    config=self.config,
                    modbus=Modbus(
                        client=self.board_config.modbus_client,
                        cache=self.neuron_hardware.modbus_cache_data,
                        val_reg=modbus_feature["val_reg"],
                        val_coil=modbus_feature["val_coil"],
                    ),
                    hardware=Hardware(
                        major_group=self.board_config.major_group,
                        feature_type=FeatureType[modbus_feature["feature_type"]],
                        feature_index=index,
                        definition=self.neuron_hardware.definition,
                        firmware=self.board_config.firmware,
                    ),
                )

                self.neuron_hardware.features.register(led)

    def _parse_feature(self, modbus_feature: dict) -> None:
        max_count: int = modbus_feature["count"]
        feature_type: str = modbus_feature["feature_type"].lower()

        if func := getattr(self, f"_parse_feature_{feature_type}", None):
            func(max_count, modbus_feature)

    def parse_features(self) -> None:
        """Parse features from hardware definition."""
        for modbus_feature in self.neuron_hardware.definition.modbus_features:
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
        self.features = FeatureMap()
        self.boards: List[Board] = []

        self.modbus_cache_data: ModbusCacheData = ModbusCacheData(
            modbus_client=self.modbus_client,
            hardware=self.hardware,
        )

    async def init(self) -> None:
        """Initialize internal and external hardware."""
        await self.read_boards()
        await self.read_extensions()

    @staticmethod
    def get_firmware(response: ModbusResponse) -> str:
        versions = getattr(response, "registers", [0, 0])
        return f"{(versions[0] & 0xff00) >> 8}.{(versions[0] & 0x00ff)}"

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
                board = Board(
                    config=self.config,
                    board_config=BoardConfig(
                        modbus_client=self.modbus_client,
                        firmware=self.get_firmware(response),
                        major_group=index,
                    ),
                    neuron_hardware=NeuronHardware(
                        definition=self.hardware["definitions"][0],
                        modbus_cache_data=self.modbus_cache_data,
                        features=self.features,
                    ),
                )
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
                await EastronSDM120M(
                    config=self.config,
                    board_config=BoardConfig(
                        modbus_client=self.modbus_client,
                        major_group=0,
                    ),
                    neuron_hardware=NeuronHardware(
                        definition=definition,
                        modbus_cache_data=self.modbus_cache_data,
                        features=self.features,
                    ),
                ).init()

        await self.modbus_cache_data.scan("serial", hardware_types=[HardwareType.EXTENSION])
