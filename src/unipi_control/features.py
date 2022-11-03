from abc import ABC
from abc import abstractmethod
from collections.abc import Iterator
from enum import Enum
from typing import Any
from typing import Dict
from typing import Final
from typing import List
from typing import Optional
from typing import Union

import itertools
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

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
    METER: Final[tuple] = ("METER", "meter", "Meter")

    def __init__(self, short_name: str, topic_name: str, long_name: str):
        self.short_name: str = short_name
        self.topic_name: str = topic_name
        self.long_name: str = long_name


class BaseFeature(ABC):
    """Base class from which all features inherit."""

    def __init__(self, neuron, definition: HardwareDefinition, feature_type: str):
        self.neuron = neuron
        self.definition: HardwareDefinition = definition
        self.feature_type: FeatureType = FeatureType[feature_type]

        self.config: Config = neuron.config
        self.modbus_client: ModbusClient = neuron.modbus_client

        self._value: Optional[Union[float, int]] = None

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
    def object_id(self) -> str:
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
    def icon(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def device_class(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def state_class(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def unit_of_measurement(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def value(self) -> Union[float, int]:
        pass

    @property
    def changed(self) -> bool:
        """Detect whether the status has changed."""
        changed: bool = False

        if self.value != self._value:
            changed = True
            self._value = self.value

        return changed

    @property
    @abstractmethod
    def sw_version(self) -> Any:
        pass

    @property
    @abstractmethod
    def payload(self) -> Any:
        pass


class NeuronFeature(BaseFeature):
    def __init__(self, neuron, definition: HardwareDefinition, **kwargs):
        super().__init__(neuron, definition, kwargs["feature_type"])

        self.index: int = kwargs["index"]
        self.major_group: int = kwargs["major_group"]

        _val_coil: Optional[int] = kwargs.get("val_coil")
        self.val_coil: Optional[int] = None if _val_coil is None else _val_coil + self.index

        self._reg_value = lambda: neuron.modbus_cache_data.get_register(address=kwargs["val_reg"], index=1, unit=0)[0]

    @property
    def object_id(self) -> str:
        return f"{self.feature_type.short_name.lower()}_{self.major_group}_{self.index + 1:02d}"

    @property
    def friendly_name(self) -> str:
        """Friendly name for the feature."""
        return f"{self.name} {self.major_group}.{self.index + 1:02d}"

    @property
    def topic(self) -> str:
        """Unique name for the MQTT topic."""
        return f"{super().topic}/{self.object_id}"

    @property
    def icon(self) -> Optional[str]:
        if features_config := self.config.features.get(self.object_id):
            return features_config.icon

        return None

    @property
    def device_class(self) -> Optional[str]:
        if features_config := self.config.features.get(self.object_id):
            return features_config.device_class

        return None

    @property
    def state_class(self) -> None:
        return None

    @property
    def unit_of_measurement(self) -> None:
        return None

    @property
    def value(self) -> int:
        """The feature state as integer."""
        mask: int = 0x1 << (self.index % 16)
        return 1 if self._reg_value() & mask else 0

    @property
    def payload(self) -> str:
        """The feature state as friendly name."""
        return FeatureState.ON if self.value == 1 else FeatureState.OFF

    @property
    def sw_version(self) -> str:
        return self.neuron.boards[self.major_group - 1].firmware


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


class MeterFeature(BaseFeature):
    def __init__(self, neuron, definition: HardwareDefinition, **kwargs):
        super().__init__(neuron, definition, kwargs["feature_type"])

        self._friendly_name: str = kwargs["friendly_name"]
        self._device_class: Optional[str] = kwargs.get("device_class")
        self._state_class: Optional[str] = kwargs.get("state_class")
        self._unit_of_measurement: Optional[str] = kwargs.get("unit_of_measurement")

    @property
    def object_id(self) -> str:
        return f"{slugify(self.friendly_name)}"

    @property
    def friendly_name(self) -> str:
        return f"{self._friendly_name} {self.definition.unit}"

    @property
    def topic(self) -> str:
        """Unique name for the MQTT topic."""
        return f"{super().topic}/{self.object_id}"

    @property
    def icon(self) -> Optional[str]:
        if features_config := self.config.features.get(self.object_id):
            return features_config.icon

        return None

    # TODO: Check features config for meters
    @property
    def device_class(self) -> Optional[str]:
        return self._device_class

    # TODO: Check features config for meters
    @property
    def state_class(self) -> Optional[str]:
        return self._state_class

    # TODO: Check features config for meters
    @property
    def unit_of_measurement(self) -> Optional[str]:
        return self._unit_of_measurement

    @property
    def value(self) -> float:
        return 0.0

    @property
    def payload(self) -> float:
        return self.value

    @property
    def sw_version(self) -> Optional[str]:
        return None


class EastronMeter(MeterFeature):
    def __init__(self, neuron, definition: HardwareDefinition, sw_version: Optional[str], **kwargs):
        super().__init__(neuron, definition, **kwargs)

        self._reg_value = lambda: neuron.modbus_cache_data.get_register(
            address=kwargs["val_reg"], index=2, unit=definition.unit
        )
        self._sw_version: Optional[str] = sw_version

    @property
    def value(self) -> float:
        return round(
            float(
                BinaryPayloadDecoder.fromRegisters(
                    self._reg_value(), byteorder=Endian.Big, wordorder=Endian.Big
                ).decode_32bit_float()
            ),
            2,
        )

    @property
    def sw_version(self) -> Optional[str]:
        return self._sw_version


class FeatureMap:
    def __init__(self):
        self.data: Dict[str, List[Union[DigitalInput, DigitalOutput, Led, Relay, MeterFeature]]] = {}

    def register(self, feature: Union[DigitalInput, DigitalOutput, Led, Relay, MeterFeature]):
        """Add a feature to the data storage.

        Parameters
        ----------
        feature: Feature
        """
        if not self.data.get(feature.feature_type.short_name):
            self.data[feature.feature_type.short_name] = []

        self.data[feature.feature_type.short_name].append(feature)

    def by_object_id(
        self, object_id: str, feature_types: Optional[List[str]] = None
    ) -> Union[DigitalInput, DigitalOutput, Led, Relay, MeterFeature]:
        """Get feature by object id.

        Parameters
        ----------
        object_id: str
            The machine-readable unique name e.g. ro_2_01.
        feature_types: list

        Returns
        -------
        The feature class filtered by circuit.

        Raises
        ------
        ConfigException
            Get an exception if feature type not found.
        """
        data: Iterator = itertools.chain.from_iterable(self.data.values())

        if feature_types:
            data = self.by_feature_types(feature_types)

        try:
            feature: Union[DigitalInput, DigitalOutput, Led, Relay, MeterFeature] = next(
                (d for d in data if d.object_id == object_id)
            )
        except StopIteration as error:
            raise ConfigException(
                f"{LogPrefix.CONFIG} '{object_id}' not found in {self.__class__.__name__}!"
            ) from error

        return feature

    def by_feature_types(self, feature_types: List[str]) -> Iterator:
        """Filter features by feature type.

        Parameters
        ----------
        feature_types: list

        Returns
        -------
        Iterator
            A list of features filtered by feature type.
        """
        return itertools.chain.from_iterable(
            [item for item in (self.data.get(feature_type) for feature_type in feature_types) if item is not None]
        )
