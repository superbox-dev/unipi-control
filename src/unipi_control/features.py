import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import List
from typing import Match
from typing import Optional
from typing import Type

import itertools
from superbox_utils.dict.data_dict import DataDict

from unipi_control.config import Config
from unipi_control.config import ConfigException
from unipi_control.config import LogPrefix


@dataclass(frozen=True)
class FeatureState:
    ON: str = "ON"
    OFF: str = "OFF"


class Feature:
    """Base class from which all features inherit.

    Attributes
    ----------
    modbus_client : class
        A modbus tcp client.
    circuit : str
        The machine-readable circuit name e.g. ro_2_01.
    """

    name: str = "Feature"
    feature_name: Optional[str] = None

    def __init__(
        self, board, short_name: str, circuit: str, major_group: int, mask: int, reg: int, coil: Optional[int] = None
    ):
        self.config: Config = board.neuron.config
        self.modbus_client = board.neuron.modbus_client

        self.board = board
        self.short_name: str = short_name
        self.circuit: str = circuit
        self.major_group: int = major_group
        self.reg: int = reg
        self.mask: int = mask
        self.coil: Optional[int] = coil

        self._reg_value = lambda: board.neuron.modbus_cache_map.get_register(address=1, index=self.reg)[0]

        self._value: Optional[bool] = None

    def __repr__(self) -> str:
        return self.circuit_name

    @property
    def value(self) -> int:
        """The feature state as integer."""
        return 1 if self._reg_value() & self.mask else 0

    @property
    def state(self) -> str:
        """The feature state as friendly name."""
        return FeatureState.ON if self.value == 1 else FeatureState.OFF

    @property
    def topic(self) -> str:
        """Unique name for the MQTT topic."""
        topic: str = f"{self.config.device_info.name.lower()}/{self.feature_name}"
        topic += f"/{self.circuit}"

        return topic

    @property
    def circuit_name(self) -> str:
        """The friendly name for the circuit."""
        _circuit_name: str = self.name
        _re_match: Optional[Match[str]] = re.match(r"^[a-z]+_(\d)_(\d{2})$", self.circuit)

        if _re_match:
            _circuit_name = f"{_circuit_name} {_re_match.group(1)}.{_re_match.group(2)}"

        return _circuit_name

    @property
    def changed(self) -> bool:
        """Detect whether the status has changed."""
        value: bool = self.value == 1
        changed: bool = value != self._value

        if changed:
            self._value = value

        return changed


class Relay(Feature):
    """Class for the relay feature from the Unipi Neuron."""

    name: str = "Relay"
    feature_name: Optional[str] = "relay"

    async def set_state(self, value: int):
        return await self.modbus_client.write_coil(self.coil, value, unit=0)


class DigitalOutput(Feature):
    """Class for the digital output feature from the Unipi Neuron."""

    name: str = "Digital Output"
    feature_name: Optional[str] = "relay"

    async def set_state(self, value: int):
        return await self.modbus_client.write_coil(self.coil, value, unit=0)


class DigitalInput(Feature):
    """Class for the digital input feature from the Unipi Neuron."""

    name: str = "Digital Input"
    feature_name: Optional[str] = "input"


class Led(Feature):
    """Class for the LED feature from the Unipi Neuron."""

    name: str = "LED"
    feature_name: Optional[str] = "led"

    async def set_state(self, value: int):
        return await self.modbus_client.write_coil(self.coil, value, unit=0)


class FeatureMap(DataDict):
    """A container object that has saved Unipi Neuron feature classes.

    See Also
    --------
    helpers.DataStorage
    """

    def register(self, feature: Feature):
        """Add a feature to the data storage.

        Parameters
        ----------
        feature : Feature
        """
        if not self.data.get(feature.short_name):
            self.data[feature.short_name] = []

        self.data[feature.short_name].append(feature)

    def by_circuit(self, circuit: str, feature_type: Optional[List[str]] = None) -> Type[Feature]:
        """Get feature by circuit name.

        Parameters
        ----------
        circuit : str
            The machine readable circuit name e.g. ro_2_01.
        feature_type : list

        Returns
        -------
        DigitalInput, DigitalOutput, Relay, Led
            The feature class.

        Raises
        ------
        StopIteration
            Get an exception if circuit not found.
        """
        data: Iterator = itertools.chain.from_iterable(self.data.values())

        if feature_type:
            data = self.by_feature_type(feature_type)

        try:
            feature: Type[Feature] = next(filter(lambda d: d.circuit == circuit, data))
        except StopIteration:
            raise ConfigException(f"{LogPrefix.CONFIG} '{circuit}' not found in {self.__class__.__name__}!")

        return feature

    def by_feature_type(self, feature_type: List[str]) -> Iterator:
        """Filter features by feature type.

        Parameters
        ----------
        feature_type : list

        Returns
        -------
        Iterator
            A list of features filtered by feature type.
        """
        return itertools.chain.from_iterable(filter(None, map(self.data.get, feature_type)))
