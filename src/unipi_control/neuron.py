from collections.abc import Mapping
from typing import Optional

from config import HardwareDefinition
from config import logger
from devices import AnalogInput
from devices import AnalogOutput
from devices import devices
from devices import DigitalInput
from devices import DigitalOutput
from devices import Led
from devices import Relay
from modbus import ModbusCacheMap


class Board:
    def __init__(self, neuron, versions, major_group: int):
        self.neuron = neuron
        self.major_group: int = major_group
        self.firmware = f"{(versions[0] & 0xff00) >> 8}.{(versions[0] & 0x00ff)}"
        self.nao = (versions[2] & 0x00f0) >> 4

        if self.nao:
            self.volt_refx = (3.3 * (1 + neuron.modbus_cache_map.get_register(1, 1009)[0]))
            self.volt_ref = self.volt_refx / neuron.modbus_cache_map.get_register(1, 5)[0]

    def _parse_feature_ro(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                circuit: str = "%s_%s_%02d" % (feature_type.lower(), major_group, index + 1)

                ro = Relay(
                    circuit=circuit,
                    board=self,
                    coil=modbus_feature['val_coil'] + index,
                    reg=modbus_feature['val_reg'],
                    mask=(0x1 << (index % 16)),
                    **modbus_feature,
                )

                devices.register(ro)

    def _parse_feature_di(self, max_count: int, modbus_feature: list) -> None:
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

                devices.register(di)

    def _parse_feature_do(self, max_count: int, modbus_feature: list) -> None:
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

                devices.register(do)

    def _parse_feature_ao(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                circuit: str = "%s_%s_%02d" % (feature_type.lower(), major_group, index + 1)

                ao = AnalogOutput(
                    circuit=circuit,
                    board=self,
                    reg=modbus_feature["val_reg"],
                    **modbus_feature,
                )

                devices.register(ao)

    def _parse_feature_ai(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                circuit: str = "%s_%s_%02d" % (feature_type.lower(), major_group, index + 1)

                ai = AnalogInput(
                    circuit=circuit,
                    board=self,
                    reg=modbus_feature["val_reg"],
                    **modbus_feature,
                )

                devices.register(ai)

    def _parse_feature_led(self, max_count: int, modbus_feature: list) -> None:
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

                devices.register(led)

    def _parse_feature(self, modbus_feature: dict) -> None:
        max_count: int = modbus_feature["count"]
        feature_type: str = modbus_feature["type"].lower()
        func = getattr(self, f"_parse_feature_{feature_type}", None)

        if func:
            func(max_count, modbus_feature)

    def parse_definition(self) -> None:
        for modbus_feature in self.neuron.hw["neuron_definition"]["modbus_features"]:
            self._parse_feature(modbus_feature)


class Neuron:
    def __init__(self, modbus):
        self.modbus = modbus
        self.hw: Mapping = HardwareDefinition()
        self._boards: list = []
        self.modbus_cache_map: Optional[ModbusCacheMap] = None

    @property
    def boards(self) -> list:
        return self._boards

    async def read_boards(self) -> None:
        logger.info("[MODBUS] Reading SPI boards")

        for index in (1, 2, 3):
            result = await self.modbus.read_input_registers(1000, 10, unit=index)

            if result.isError():
                logger.info(f"[MODBUS] No board on SPI {index}")
            else:
                board = Board(self, result.registers, major_group=index)
                board.parse_definition()

                self._boards.append(board)

    async def initialise_cache(self):
        if self.modbus_cache_map is None:
            self.modbus_cache_map = ModbusCacheMap(
                self.hw["neuron_definition"]["modbus_register_blocks"],
                self,
            )

            await self.modbus_cache_map.scan()

    async def start_scanning(self):
        if self.modbus_cache_map is not None:
            await self.modbus_cache_map.scan()
