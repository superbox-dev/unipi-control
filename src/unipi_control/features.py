from abc import ABC
from abc import abstractmethod
from collections.abc import Iterator
from enum import Enum
from typing import Dict
from typing import Final
from typing import List
from typing import Optional
from typing import Union

import itertools

from superbox_utils.text.text import slugify
from unipi_control.config import Config
from unipi_control.config import ConfigException
from unipi_control.config import HardwareDefinition
from unipi_control.config import LogPrefix
from unipi_control.modbus import ModbusClient


class FeatureState:
    ON: str = "ON"
    OFF: str = "OFF"


class FeatureType(Enum):
    DI: Final[tuple] = ("DI", "input", "Digital Input")
    DO: Final[tuple] = ("DO", "relay", "Digital Output")
    LED: Final[tuple] = ("LED", "led", "LED")
    RO: Final[tuple] = ("RO", "relay", "Relay")
    METER: Final[tuple] = ("Meter", "meter", "Meter")

    def __init__(self, short_name: str, topic_name: str, long_name: str):
        self.short_name: str = short_name
        self.topic_name: str = topic_name
        self.long_name: str = long_name


class BaseFeature(ABC):
    """Base class from which all features inherit."""

    def __init__(self, neuron, definition: HardwareDefinition, feature_type: str):
        self.config: Config = neuron.config
        self.modbus_client: ModbusClient = neuron.modbus_client

        self.feature_type: FeatureType = FeatureType[feature_type]
        self.definition: HardwareDefinition = definition

    def __repr__(self) -> str:
        return self.friendly_name

    @property
    def name(self) -> str:
        return self.feature_type.long_name

    @property
    def feature_name(self) -> str:
        return self.feature_type.topic_name

    @property
    @abstractmethod
    def unique_name(self) -> str:
        pass

    @property
    @abstractmethod
    def friendly_name(self) -> str:
        pass

    @property
    @abstractmethod
    def topic(self) -> str:
        """Unique name for the MQTT topic."""
        return f"{self.config.device_info.name.lower()}/{self.feature_name}"

    @property
    @abstractmethod
    def value(self) -> int:
        pass


class NeuronFeature(BaseFeature):
    def __init__(
        self,
        neuron,
        definition: HardwareDefinition,
        **kwargs,
    ):
        super().__init__(neuron, definition, kwargs["feature_type"])

        self.index: int = kwargs["index"]
        self.major_group: int = kwargs["major_group"]

        _val_coil: Optional[int] = kwargs.get("val_coil")
        self.val_coil: Optional[int] = None if _val_coil is None else _val_coil + self.index

        self._reg_value = lambda: neuron.modbus_cache_data.get_register(address=kwargs["val_reg"], index=1, unit=0)[0]
        self._value: Optional[bool] = None

    @property
    def unique_name(self) -> str:
        return f"{self.feature_type.short_name.lower()}_{self.major_group}_{self.index + 1:02d}"

    @property
    def friendly_name(self) -> str:
        """Friendly name for the feature."""
        return f"{self.name} {self.major_group}.{self.index + 1:02d}"

    @property
    def topic(self) -> str:
        """Unique name for the MQTT topic."""
        return f"{super().topic}/{self.unique_name}"

    @property
    def value(self) -> int:
        """The feature state as integer."""
        mask: int = 0x1 << (self.index % 16)
        return 1 if self._reg_value() & mask else 0

    @property
    def changed(self) -> bool:
        """Detect whether the status has changed."""
        value: bool = self.value == 1

        if changed := value != self._value:
            self._value = value

        return changed

    @property
    def state(self) -> str:
        """The feature state as friendly name."""
        return FeatureState.ON if self.value == 1 else FeatureState.OFF


class Relay(NeuronFeature):
    """Class for the relay feature from the Unipi Neuron."""

    async def set_state(self, value: bool):
        return await self.modbus_client.tcp.write_coil(address=self.val_coil, value=value, slave=0)


class DigitalOutput(NeuronFeature):
    """Class for the digital output feature from the Unipi Neuron."""

    @property
    def feature_name(self) -> str:
        return "relay"

    async def set_state(self, value: bool):
        return await self.modbus_client.tcp.write_coil(address=self.val_coil, value=value, slave=0)


class DigitalInput(NeuronFeature):
    """Class for the digital input feature from the Unipi Neuron."""

    @property
    def feature_name(self) -> str:
        return "input"


class Led(NeuronFeature):
    """Class for the LED feature from the Unipi Neuron."""

    @property
    def name(self) -> str:
        return self.__class__.__name__.upper()

    async def set_state(self, value: bool):
        return await self.modbus_client.tcp.write_coil(address=self.val_coil, value=value, slave=0)


class Meter(BaseFeature):
    def __init__(
        self,
        neuron,
        definition: HardwareDefinition,
        **kwargs,
    ):
        super().__init__(neuron, definition, kwargs["feature_type"])

        self._friendly_name: str = kwargs["friendly_name"]

    @property
    def unique_name(self) -> str:
        return f"{slugify(self.friendly_name)}_{self.definition.unit}"

    @property
    def friendly_name(self) -> str:
        return f"{self._friendly_name} {self.definition.unit}"

    @property
    def topic(self) -> str:
        """Unique name for the MQTT topic."""
        return f"{super().topic}/{self.unique_name}"

    @property
    def value(self) -> int:
        return 0


class FeatureMap:
    def __init__(self):
        self.data: Dict[str, List[Union[DigitalInput, DigitalOutput, Led, Relay, Meter]]] = {}

    def register(self, feature: Union[DigitalInput, DigitalOutput, Led, Relay, Meter]):
        """Add a feature to the data storage.

        Parameters
        ----------
        feature: Feature
        """
        if not self.data.get(feature.feature_type.short_name):
            self.data[feature.feature_type.short_name] = []

        self.data[feature.feature_type.short_name].append(feature)

    def by_unique_name(
        self, unique_name: str, feature_type: Optional[List[str]] = None
    ) -> Union[DigitalInput, DigitalOutput, Led, Relay, Meter]:
        """Get feature by unique name.

        Parameters
        ----------
        unique_name: str
            The machine-readable unique name e.g. ro_2_01.
        feature_type: list

        Returns
        -------
        The feature class filtered by circuit.

        Raises
        ------
        ConfigException
            Get an exception if circuit not found.
        """
        data: Iterator = itertools.chain.from_iterable(self.data.values())

        if feature_type:
            data = self.by_feature_type(feature_type)

        try:
            feature: Union[DigitalInput, DigitalOutput, Led, Relay, Meter] = next(
                filter(lambda d: d.unique_name == unique_name, data)
            )
        except StopIteration as error:
            raise ConfigException(
                f"{LogPrefix.CONFIG} '{unique_name}' not found in {self.__class__.__name__}!"
            ) from error

        return feature

    def by_feature_type(self, feature_type: List[str]) -> Iterator:
        """Filter features by feature type.

        Parameters
        ----------
        feature_type: list

        Returns
        -------
        Iterator
            A list of features filtered by feature type.
        """
        return itertools.chain.from_iterable(filter(None, map(self.data.get, feature_type)))
