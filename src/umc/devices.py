import itertools
import re
from dataclasses import dataclass
from typing import Optional
from typing import Union

from config import config
from helpers import MutableMappingMixin


class DeviceMap(MutableMappingMixin):
    def register(self, device):
        if not self.mapping.get(device.type):
            self.mapping[device.type] = []

        self.mapping[device.type].append(device)

    def by_name(self, device_type: Union[str, list]) -> list:
        if isinstance(device_type, str):
            return self.mapping[device_type]
        elif isinstance(device_type, list):
            return list(
                itertools.chain.from_iterable(
                    map(self.mapping.get, device_type)
                )
            )


@dataclass
class Message:
    dev_name: str
    dev_type: str
    circuit: str
    value: bool
    topic: str


class FeatureMixin:
    def __init__(self, board, circuit: str, mask: Optional[int] = None, *args, **kwargs):
        self.__dict__.update(kwargs)
        self.modbus = board.neuron.modbus
        self.circuit: str = circuit
        self.mask: int = mask
        self.reg_value = lambda: board.neuron.modbus_cache_map.get_register(1, self.reg, unit=0)[0]
        self._value: bool = False

    @property
    def value(self) -> int:
        return 1 if self.reg_value() & self.mask else 0

    @property
    def topic(self) -> str:
        topic: str = f"""{config.device_name}/{self.dev_name}"""

        if self.dev_type:
            topic += f"/{self.dev_type}"

        topic += f"/{self.circuit}"

        return topic

    @property
    def circuit_name(self) -> str:
        m = re.match(r"^[a-z]+_(\d{1})_(\d{2})$", self.circuit)
        return f"""{self.name} {m.group(1)}.{m.group(2).lstrip("0")}"""

    @property
    def changed(self) -> bool:
        value: bool = self.value == True  # noqa
        changed: bool = value != self._value

        if changed:
            self._value = value

        return changed

    @property
    def message(self) -> Message:
        return Message(
            self.dev_name,
            self.dev_type,
            self.circuit,
            self.value,
            f"{self.topic}/get",
        )


class FeatureWriteMixin:
    async def set_state(self, value: int) -> None:
        await self.modbus.write_coil(self.coil, value, unit=0)


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


class AnalogOutput(FeatureMixin, FeatureWriteMixin):
    name = "Analog Output"
    dev_name = "output"
    dev_type = "analog"


class AnalogInput(FeatureMixin):
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


devices = DeviceMap()
