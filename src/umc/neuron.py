from collections import namedtuple
from typing import Optional

from config import HardwareDefinition
from config import logger
from devices import devices


class ModbusCacheMap:
    def __init__(self, modbus_reg_map, neuron):
        self.modbus_reg_map = modbus_reg_map
        self.neuron = neuron
        self.registered: dict = {}
        self.registered_input: dict = {}

        for modbus_reg_group in modbus_reg_map:
            for index in range(modbus_reg_group["count"]):
                reg: int = modbus_reg_group["start_reg"] + index

                if modbus_reg_group.get('type') == "input":
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
                val = await self.neuron.modbus_client.read_input_registers(**data)

                for index in range(modbus_reg_group["count"]):
                    self.registered_input[modbus_reg_group["start_reg"] + index] = val.registers[index]
            else:
                val = await self.neuron.modbus_client.read_holding_registers(**data)

                for index in range(modbus_reg_group["count"]):
                    self.registered[modbus_reg_group["start_reg"] + index] = val.registers[index]


class FeatureMixin:
    def __init__(self, board, circuit: str, mask: Optional[int] = None, *args, **kwargs):
        self.__dict__.update(kwargs)
        self.modbus_client = board.neuron.modbus_client
        self.circuit: str = circuit
        self.mask: int = mask
        self.device = namedtuple("Device", "dev_name dev_type circuit value changed")
        self.reg_value = lambda: board.neuron.modbus_cache_map.get_register(1, self.reg, unit=0)[0]
        self._value: bool = False

        devices.register(self.type, self)

    @property
    def value(self):
        return 1 if self.reg_value() & self.mask else 0

    @property
    def circuit_name(self):
        return f"""{self.name} {self.circuit.replace("_", ".")}"""

    async def get_state(self) -> namedtuple:
        value: bool = self.value == True  # noqa
        changed: bool = value != self._value

        if changed:
            self._value = value

        return self.device(
            self.dev_name,
            self.dev_type,
            self.circuit,
            self.value,
            changed,
        )


class FeatureWriteMixin:
    async def set_state(self, value: int) -> None:
        await self.modbus_client.write_coil(self.coil, value)


class Relay(FeatureMixin, FeatureWriteMixin):
    name = "Relay"
    dev_name = "relay"
    dev_type = "physical"


class DigitalOutput(FeatureMixin, FeatureWriteMixin):
    name = "Digital Output"
    dev_name = "relay"
    dev_type = "digital"


class DigitalInput(FeatureMixin):
    name = "Digital Input"
    dev_name = "input"
    dev_type = "digital"


class AnlogOutput(FeatureMixin, FeatureWriteMixin):
    name = "Analog Output"
    dev_name = "output"
    dev_type = "analog"


class AnlogInput(FeatureMixin):
    name = "Analog Input"
    dev_name = "input"
    dev_type = "analog"


class Led(FeatureMixin, FeatureWriteMixin):
    name = "LED"
    dev_name = "led"
    dev_type = None


class Watchdog(FeatureMixin, FeatureWriteMixin):
    name = "Watchdog"
    dev_name = "wd"


class Register(FeatureMixin, FeatureWriteMixin):
    name = "Register"
    dev_name = "register"


class Board:
    def __init__(self, neuron, major_group: int):
        self.neuron = neuron
        self.major_group: int = major_group

    def _parse_feature_ro(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                Relay(
                    circuit="%s_%s_%02d" % (feature_type.lower(), major_group, index + 1),
                    board=self,
                    coil=modbus_feature['val_coil'] + index,
                    reg=modbus_feature['val_reg'],
                    mask=(0x1 << (index % 16)),
                    **modbus_feature,
                )

    def _parse_feature_di(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                DigitalInput(
                    circuit="%s_%02d" % (major_group, index + 1),
                    board=self,
                    reg=modbus_feature['val_reg'],
                    mask=(0x1 << (index % 16)),
                    **modbus_feature,
                )

    def _parse_feature_do(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                DigitalOutput(
                    circuit="%s_%02d" % (major_group, index + 1),
                    board=self,
                    coil=modbus_feature['val_coil'] + index,
                    reg=modbus_feature['val_reg'],
                    mask=(0x1 << (index % 16)),
                    **modbus_feature,
                )

    def _parse_feature_ao(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                AnlogOutput(
                    circuit="%s_%02d" % (major_group, index + 1),
                    board=self,
                    reg=modbus_feature['val_reg'],
                    **modbus_feature,
                )

    def _parse_feature_ai(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                AnlogInput(
                    circuit="%s_%02d" % (major_group, index + 1),
                    board=self,
                    reg=modbus_feature['val_reg'],
                    **modbus_feature,
                )

    def _parse_feature_register(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]
        reg_type: str = modbus_feature.get("reg_type")

        if major_group == self.major_group:
            for index in range(0, max_count):
                if reg_type == "input":
                    name = "%s_%d_inp"
                else:
                    name = "%s_%d"

                Register(
                    circuit=name % (major_group, index + 1),
                    board=self,
                    reg=modbus_feature['start_reg'] + index,
                    **modbus_feature,
                )

    def _parse_feature_led(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                Led(
                    circuit="%s_%02d" % (major_group, index + 1),
                    board=self,
                    coil=modbus_feature['val_coil'] + index,
                    reg=modbus_feature['val_reg'],
                    mask=(0x1 << (index % 16)),
                    **modbus_feature,
                )

    def _parse_feature_wd(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                Watchdog(
                    circuit="%s_%02d" % (major_group, index + 1),
                    board=self,
                    reg=modbus_feature['val_reg'],
                    **modbus_feature,
                )

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
    def __init__(self, modbus_client):
        self.modbus_client = modbus_client
        self.hw = HardwareDefinition()
        self.boards: list = []
        self.modbus_cache_map = None

    async def read_boards(self) -> None:
        logger.info("[MODBUS] Reading SPI boards")

        for index in (1, 2, 3):
            request_fw = await self.modbus_client.read_input_registers(1000, 1, unit=index)

            if request_fw.isError():
                logger.info(f"[MODBUS] No board on SPI {index}")
            else:
                Board(self, major_group=index).parse_definition()

    async def initialise_cache(self):
        if self.modbus_cache_map is None:
            self.modbus_cache_map = ModbusCacheMap(
                self.hw["neuron_definition"]['modbus_register_blocks'],
                self,
            )

            await self.modbus_cache_map.scan()

    async def start_scanning(self):
        if self.modbus_cache_map is not None:
            await self.modbus_cache_map.scan()
