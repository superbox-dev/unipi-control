"""Read hardware to initialize neuron device."""

from typing import List
from typing import NamedTuple
from typing import Optional

from pymodbus.pdu import ModbusResponse

from unipi_control.config import Config
from unipi_control.config import HardwareMap
from unipi_control.config import HardwareType
from unipi_control.config import LogPrefix
from unipi_control.config import UNIPI_LOGGER
from unipi_control.extensions.eastron import EastronSDM120M
from unipi_control.features.map import FeatureMap
from unipi_control.features.neuron import DigitalInput
from unipi_control.features.neuron import DigitalOutput
from unipi_control.features.neuron import Hardware
from unipi_control.features.neuron import Led
from unipi_control.features.neuron import Modbus
from unipi_control.features.neuron import Relay
from unipi_control.features.utils import FeatureType
from unipi_control.helpers.typing import HardwareDefinition
from unipi_control.helpers.typing import ModbusClient
from unipi_control.helpers.typing import ModbusFeature
from unipi_control.helpers.typing import ModbusReadData
from unipi_control.modbus import ModbusCacheData
from unipi_control.modbus import check_modbus_call


class BoardConfig(NamedTuple):
    major_group: Optional[int]
    firmware: Optional[str] = None


class NeuronHardware(NamedTuple):
    definition: HardwareDefinition
    modbus_cache_data: ModbusCacheData
    features: FeatureMap


class Board:
    """Class to parse board features and register it to the ``FeatureMap``."""

    def __init__(
        self,
        config: Config,
        modbus_client: ModbusClient,
        modbus_cache_data: ModbusCacheData,
        definition: HardwareDefinition,
        features: FeatureMap,
        board_config: BoardConfig,
    ) -> None:
        """Initialize board.

        Parameters
        ----------
        config: Config
            Dataclass with configuration settings from yaml file.
        modbus_client: ModbusClient
            Modbus named tuple with tcp and serial client.
        modbus_cache_data: ModbusCacheData
            Cached modbus registers.
        definition: HardwareDefinition
            Neuron and extension hardware definition data.
        features: FeatureMap
            Input and output features.
        board_config: BoardConfig
            Neuron board configuration e.g. major_group and firmware.
        """
        self.config: Config = config
        self.modbus_client: ModbusClient = modbus_client
        self.modbus_cache_data: ModbusCacheData = modbus_cache_data
        self.definition: HardwareDefinition = definition
        self.features: FeatureMap = features
        self.board_config: BoardConfig = board_config

    def _parse_feature_ro(self, max_count: int, modbus_feature: ModbusFeature) -> None:
        if modbus_feature["major_group"] == self.board_config.major_group:
            for index in range(0, max_count):
                relay: Relay = Relay(
                    config=self.config,
                    modbus=Modbus(
                        client=self.modbus_client,
                        cache=self.modbus_cache_data,
                        val_reg=modbus_feature["val_reg"],
                        val_coil=modbus_feature["val_coil"],
                    ),
                    hardware=Hardware(
                        major_group=self.board_config.major_group,
                        feature_type=FeatureType[modbus_feature["feature_type"]],
                        feature_index=index,
                        definition=self.definition,
                        firmware=self.board_config.firmware,
                    ),
                )

                self.features.register(relay)

    def _parse_feature_di(self, max_count: int, modbus_feature: ModbusFeature) -> None:
        if modbus_feature["major_group"] == self.board_config.major_group:
            for index in range(0, max_count):
                digital_input: DigitalInput = DigitalInput(
                    config=self.config,
                    modbus=Modbus(
                        client=self.modbus_client,
                        cache=self.modbus_cache_data,
                        val_reg=modbus_feature["val_reg"],
                    ),
                    hardware=Hardware(
                        major_group=self.board_config.major_group,
                        feature_type=FeatureType[modbus_feature["feature_type"]],
                        feature_index=index,
                        definition=self.definition,
                        firmware=self.board_config.firmware,
                    ),
                )

                self.features.register(digital_input)

    def _parse_feature_do(self, max_count: int, modbus_feature: ModbusFeature) -> None:
        if modbus_feature["major_group"] == self.board_config.major_group:
            for index in range(0, max_count):
                digital_output: DigitalOutput = DigitalOutput(
                    config=self.config,
                    modbus=Modbus(
                        client=self.modbus_client,
                        cache=self.modbus_cache_data,
                        val_reg=modbus_feature["val_reg"],
                        val_coil=modbus_feature["val_coil"],
                    ),
                    hardware=Hardware(
                        major_group=self.board_config.major_group,
                        feature_type=FeatureType[modbus_feature["feature_type"]],
                        feature_index=index,
                        definition=self.definition,
                        firmware=self.board_config.firmware,
                    ),
                )

                self.features.register(digital_output)

    def _parse_feature_led(self, max_count: int, modbus_feature: ModbusFeature) -> None:
        if modbus_feature["major_group"] == self.board_config.major_group:
            for index in range(0, max_count):
                led: Led = Led(
                    config=self.config,
                    modbus=Modbus(
                        client=self.modbus_client,
                        cache=self.modbus_cache_data,
                        val_reg=modbus_feature["val_reg"],
                        val_coil=modbus_feature["val_coil"],
                    ),
                    hardware=Hardware(
                        major_group=self.board_config.major_group,
                        feature_type=FeatureType[modbus_feature["feature_type"]],
                        feature_index=index,
                        definition=self.definition,
                        firmware=self.board_config.firmware,
                    ),
                )

                self.features.register(led)

    def _parse_feature(self, modbus_feature: ModbusFeature) -> None:
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
    hardware: HardwareMap
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
        self.hardware: HardwareMap = HardwareMap(config=config)
        self.features = FeatureMap()
        self.boards: List[Board] = []

        self.modbus_cache_data: ModbusCacheData = ModbusCacheData(
            modbus_client=self.modbus_client,
            hardware=self.hardware,
        )

    async def init(self) -> None:
        """Initialize internal and external hardware."""
        UNIPI_LOGGER.debug("%s %s hardware definition(s) found.", LogPrefix.CONFIG, len(self.hardware))

        await self.read_boards()
        await self.read_extensions()

        UNIPI_LOGGER.info("%s %s features initialized.", LogPrefix.CONFIG, len(self.features))

    @staticmethod
    def get_firmware(response: ModbusResponse) -> str:
        """Get the Unipi Neuron firmware version.

        Parameters
        ----------
        response: ModbusResponse
            Modbus response PDU

        Returns
        -------
        str:
            Unipi Neuron firmware version
        """
        versions = getattr(response, "registers", [0, 0])
        return f"{(versions[0] & 0xff00) >> 8}.{(versions[0] & 0x00ff)}"

    async def read_boards(self) -> None:
        """Scan Modbus TCP and initialize Unipi Neuron board."""
        UNIPI_LOGGER.info("%s Reading SPI boards", LogPrefix.MODBUS)

        for index in (1, 2, 3):
            data: ModbusReadData = {
                "address": 1000,
                "count": 1,
                "slave": index,
            }

            response: Optional[ModbusResponse] = await check_modbus_call(
                self.modbus_client.tcp.read_input_registers, data
            )

            if response:
                board = Board(
                    config=self.config,
                    modbus_client=self.modbus_client,
                    definition=self.hardware["neuron"],
                    modbus_cache_data=self.modbus_cache_data,
                    features=self.features,
                    board_config=BoardConfig(
                        firmware=self.get_firmware(response),
                        major_group=index,
                    ),
                )
                board.parse_features()

                self.boards.append(board)
            else:
                UNIPI_LOGGER.info("%s No board on SPI %s", LogPrefix.MODBUS, index)

        await self.modbus_cache_data.scan("tcp", hardware_types=[HardwareType.NEURON])

    async def read_extensions(self) -> None:
        """Scan Modbus RTU and initialize extension classes."""
        UNIPI_LOGGER.info("%s Reading extensions", LogPrefix.MODBUS)

        for key, definition in self.hardware.items():
            if (
                key != "neuron"
                and (definition.manufacturer and definition.manufacturer.lower() == "eastron")
                and (definition.model and definition.model == "SDM120M")
            ):
                await EastronSDM120M(
                    config=self.config,
                    modbus_client=self.modbus_client,
                    modbus_cache_data=self.modbus_cache_data,
                    definition=definition,
                    features=self.features,
                ).init()

        await self.modbus_cache_data.scan("serial", hardware_types=[HardwareType.EXTENSION])
