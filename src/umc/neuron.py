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
from devices import Register
from devices import Relay
from devices import Watchdog


class ModbusCacheMap:
    def __init__(self, modbus_reg_map, neuron):
        self.modbus_reg_map = modbus_reg_map
        self.neuron = neuron
        self.registered: dict = {}
        self.registered_input: dict = {}

        for modbus_reg_group in modbus_reg_map:
            for index in range(modbus_reg_group["count"]):
                reg: int = modbus_reg_group["start_reg"] + index

                if modbus_reg_group.get("type") == "input":
                    self.registered_input[reg] = None
                else:
                    self.registered[reg] = None

    def get_register(self, count: int, index: int, unit=0, is_input=False) -> list:
        ret: list = []

        for counter in range(index, count + index):
            if is_input:
                if counter not in self.registered_input:
                    raise Exception(f"Unknown register {counter}")
                elif self.registered_input[counter] is None:
                    raise Exception(f"No cached value of register {counter} on unit {unit} - read error")

                ret += [self.registered_input[counter]]
            else:
                if counter not in self.registered:
                    raise Exception(f"Unknown register {counter}")
                elif self.registered[counter] is None:
                    raise Exception(f"No cached value of register {counter} on unit {unit} - read error")

                ret += [self.registered[counter]]

        return ret

    async def scan(self):
        for modbus_reg_group in self.modbus_reg_map:
            data: dict = {
                "address": modbus_reg_group["start_reg"],
                "count": modbus_reg_group["count"],
                "unit": 0,
            }

            if modbus_reg_group.get("type") == "input":
                val = await self.neuron.modbus.read_input_registers(**data)

                for index in range(modbus_reg_group["count"]):
                    self.registered_input[modbus_reg_group["start_reg"] + index] = val.registers[index]
            else:
                val = await self.neuron.modbus.read_holding_registers(**data)

                for index in range(modbus_reg_group["count"]):
                    self.registered[modbus_reg_group["start_reg"] + index] = val.registers[index]


class Board:
    def __init__(self, neuron, major_group: int):
        self.neuron = neuron
        self.major_group: int = major_group

    def _parse_feature_ro(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                ro = Relay(
                    circuit="%s_%s_%02d" % (feature_type.lower(), major_group, index + 1),
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
                di = DigitalInput(
                    circuit="%s_%s_%02d" % (feature_type.lower(), major_group, index + 1),
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
                do = DigitalOutput(
                    circuit="%s_%s_%02d" % (feature_type.lower(), major_group, index + 1),
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
                ao = AnalogOutput(
                    circuit="%s_%s_%02d" % (feature_type.lower(), major_group, index + 1),
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
                ai = AnalogInput(
                    circuit="%s_%s_%02d" % (feature_type.lower(), major_group, index + 1),
                    board=self,
                    reg=modbus_feature["val_reg"],
                    **modbus_feature,
                )

                devices.register(ai)

    def _parse_feature_register(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]
        reg_type: str = modbus_feature.get("reg_type")

        if major_group == self.major_group:
            for index in range(0, max_count):
                if reg_type == "input":
                    name = "%s_%s_%d_inp"
                else:
                    name = "%s_%s_%d"

                reg = Register(
                    circuit=name % (feature_type.lower(), major_group, index + 1),
                    board=self,
                    reg=modbus_feature["start_reg"] + index,
                    **modbus_feature,
                )

                devices.register(reg)

    def _parse_feature_led(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                led = Led(
                    circuit="%s_%s_%02d" % (feature_type.lower(), major_group, index + 1),
                    board=self,
                    coil=modbus_feature["val_coil"] + index,
                    reg=modbus_feature["val_reg"],
                    mask=(0x1 << (index % 16)),
                    **modbus_feature,
                )

                devices.register(led)

    def _parse_feature_wd(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                wd = Watchdog(
                    circuit="%s_%s_%02d" % (feature_type.lower(), major_group, index + 1),
                    board=self,
                    reg=modbus_feature["val_reg"],
                    **modbus_feature,
                )

                devices.register(wd)

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
        self.boards: list = []
        self.modbus_cache_map: Optional[ModbusCacheMap] = None

    async def read_boards(self) -> None:
        logger.info("[MODBUS] Reading SPI boards")

        for index in (1, 2, 3):
            request_fw = await self.modbus.read_input_registers(1000, 1, unit=index)

            if request_fw.isError():
                logger.info(f"[MODBUS] No board on SPI {index}")
            else:
                Board(self, major_group=index).parse_definition()

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
