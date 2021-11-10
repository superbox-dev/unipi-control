from typing import Optional

from config import HardwareData
from config import logger
from features import AnalogueInput
from features import AnalogueOutput
from features import DigitalInput
from features import DigitalOutput
from features import FeatureMap
from features import Led
from features import Relay
from modbus import ModbusCacheMap


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
        self.neuron = neuron
        self.major_group: int = major_group
        self.firmware = f"{(versions[0] & 0xff00) >> 8}.{(versions[0] & 0x00ff)}"

        self._nao = (versions[2] & 0x00f0) >> 4

        if self._nao:
            modbus_cache_map: ModbusCacheMap = neuron.modbus_cache_map

            self.volt_ref_x = (3.3 * (1 + modbus_cache_map.get_register(address=1, index=1009)[0]))
            self.volt_ref = self.volt_ref_x / modbus_cache_map.get_register(address=1, index=5)[0]

    def _parse_feature_ro(self, max_count: int, modbus_feature: dict) -> None:
        major_group: str = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                circuit: str = "%s_%s_%02d" % (feature_type.lower(), major_group, index + 1)

                ro = Relay(
                    circuit=circuit,
                    board=self,
                    coil=modbus_feature["val_coil"] + index,
                    reg=modbus_feature["val_reg"],
                    mask=(0x1 << (index % 16)),
                    **modbus_feature,
                )

                self.neuron.features.register(ro)

    def _parse_feature_di(self, max_count: int, modbus_feature: dict) -> None:
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                circuit: str = "%s_%s_%02d" % (feature_type.lower(), major_group, index + 1)

                di = DigitalInput(
                    circuit=circuit,
                    board=self,
                    reg=modbus_feature["val_reg"],
                    mask=(0x1 << (index % 16)),
                    **modbus_feature,
                )

                self.neuron.features.register(di)

    def _parse_feature_do(self, max_count: int, modbus_feature: dict) -> None:
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                circuit: str = "%s_%s_%02d" % (feature_type.lower(), major_group, index + 1)

                do = DigitalOutput(
                    circuit=circuit,
                    board=self,
                    coil=modbus_feature["val_coil"] + index,
                    reg=modbus_feature["val_reg"],
                    mask=(0x1 << (index % 16)),
                    **modbus_feature,
                )

                self.neuron.features.register(do)

    def _parse_feature_ao(self, max_count: int, modbus_feature: dict) -> None:
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                circuit: str = "%s_%s_%02d" % (feature_type.lower(), major_group, index + 1)

                ao = AnalogueOutput(
                    circuit=circuit,
                    board=self,
                    reg=modbus_feature["val_reg"],
                    **modbus_feature,
                )

                self.neuron.features.register(ao)

    def _parse_feature_ai(self, max_count: int, modbus_feature: dict) -> None:
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                circuit: str = "%s_%s_%02d" % (feature_type.lower(), major_group, index + 1)

                ai = AnalogueInput(
                    circuit=circuit,
                    board=self,
                    reg=modbus_feature["val_reg"],
                    **modbus_feature,
                )

                self.neuron.features.register(ai)

    def _parse_feature_led(self, max_count: int, modbus_feature: dict) -> None:
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                circuit: str = "%s_%s_%02d" % (feature_type.lower(), major_group, index + 1)

                led = Led(
                    circuit=circuit,
                    board=self,
                    coil=modbus_feature["val_coil"] + index,
                    reg=modbus_feature["val_reg"],
                    mask=(0x1 << (index % 16)),
                    **modbus_feature,
                )

                self.neuron.features.register(led)

    def _parse_feature(self, modbus_feature: dict) -> None:
        max_count: int = modbus_feature["count"]
        feature_type: str = modbus_feature["type"].lower()
        func = getattr(self, f"_parse_feature_{feature_type}", None)

        if func:
            func(max_count, modbus_feature)

    def parse_features(self) -> None:
        """Parse all features from the hardware mapping."""
        neuron_definition: dict = self.neuron.hardware["neuron_definition"]
        modbus_features: list = neuron_definition["modbus_features"]

        for modbus_feature in modbus_features:
            self._parse_feature(modbus_feature)


class Neuron:
    """Class that reads all boards and scan modbus registers from an Unipi Neuron.

    The Unipi Neuron has one or more boards and each board has it's features
    (e. g. Relay, Digital Input). This class reads out all boards and append
    it to the boards ``list``.

    Attributes
    ----------
    modbus : class
        Extended modbus client class.
    modbus_cache_map : class, optional
        All cached modbus input register blocks.
    hardware : HardwareData
        The Unipi Neuron hardware definitions.
    boards : list
        All available boards from the Unipi Neuron.
    features : FeatureMap
        All registered features (e.g. Relay, Digital Input, ...) from the
        Unipi Neuron.
    """

    def __init__(self, modbus):
        """Initialize Unipi Neuron.

        Parameters
        ----------
        modbus : class
            Extended modbus client class.
        """
        self.modbus = modbus
        self.modbus_cache_map: Optional[ModbusCacheMap] = None
        self.hardware = HardwareData()
        self.boards: list = []
        self.features = FeatureMap()

    async def _initialise_cache(self) -> None:
        if self.modbus_cache_map is None:
            self.modbus_cache_map = ModbusCacheMap(
                self.modbus,
                self.hardware["neuron_definition"]["modbus_register_blocks"],
            )

            await self.modbus_cache_map.scan()

    async def read_boards(self) -> None:
        """Append all available boards to a list."""
        await self._initialise_cache()

        logger.info("[MODBUS] Reading SPI boards")

        for index in (1, 2, 3):
            response = await self.modbus.read_input_registers(address=1000, count=10, unit=index)

            if response.isError():
                logger.info("[MODBUS] No board on SPI %s", index)
            else:
                board = Board(self, versions=response.registers, major_group=index)
                board.parse_features()

                self.boards.append(board)

    async def scan(self) -> None:
        """Scan and cache modbus register blocks if no cache exists."""
        if self.modbus_cache_map is not None:
            await self.modbus_cache_map.scan()
