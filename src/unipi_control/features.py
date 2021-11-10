import itertools
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Optional
from typing import Union

from config import config
from helpers import DataStorage
from termcolor import colored


@dataclass(frozen=True)
class FeatureState:
    """Feature state constants."""

    ON: str = "ON"
    OFF: str = "OFF"


class Feature:
    """Base class from which all features inherit.

    Attributes
    ----------
    type : str:
        The feature type e.g. DI for digital input.
    modbus : class
        Extended modbus client class.
    circuit : str
        The machine readable circuit name e.g. ro_2_01.
    value : int
        The feature state as integer.
    state : str
        The feature state as friendly name.
    topic : str
        Unique name for the MQTT topic.
    circuit_name : str
        The friendly name for the circuit.
    changed : bool
        Detect whether the status has changed.
    """

    name: Optional[str] = None
    feature_name: Optional[str] = None
    feature_type: Optional[str] = None

    def __init__(self, board, circuit: str, mask: Optional[int] = None, *args, **kwargs):
        """Initialize feature.

        Parameters
        ----------
        circuit : str
            The machine readable circuit name e.g. ro_2_01.
        """
        self.type = kwargs.get("type")
        self.major_group = kwargs.get("major_group")
        self._coil = kwargs.get("coil")
        self._cal_reg = kwargs.get("cal_reg")
        self._reg = kwargs.get("reg")

        self.board = board
        self.modbus = board.neuron.modbus
        self.circuit: str = circuit
        self._mask: int = mask

        self._reg_value = lambda: board.neuron.modbus_cache_map.get_register(
            address=1,
            index=self._reg
        )[0]

        self._value: bool = False

    def __repr__(self) -> str:
        return self.circuit_name

    @property
    def value(self) -> int:
        """Get the feature state as integer."""
        return 1 if self._reg_value() & self._mask else 0

    @property
    def state(self) -> str:
        """Get the feature state as friendly name."""
        return FeatureState.ON if self.value == 1 else FeatureState.OFF

    @property
    def topic(self) -> str:
        """Get unique name for the MQTT topic."""
        topic: str = f"{config.device_name.lower()}/{self.feature_name}"

        if self.feature_type:
            topic += f"/{self.feature_type}"

        topic += f"/{self.circuit}"

        return topic

    @property
    def circuit_name(self) -> str:
        """Get the friendly name for the circuit."""
        m = re.match(r"^[a-z]+_(\d)_(\d{2})$", self.circuit)
        return f"{self.name} {m.group(1)}.{m.group(2)}"

    @property
    def changed(self) -> bool:
        """Detect whether the status has changed."""
        value: bool = self.value == True  # noqa
        changed: bool = value != self._value

        if changed:
            self._value = value

        return changed


class Relay(Feature):
    """Class for the relay feature from the Unipi Neuron."""

    name: Optional[str] = "Relay"
    feature_name: Optional[str] = "relay"
    feature_type: Optional[str] = "physical"

    async def set_state(self, value: int):
        """Set the state for the relay feature.

        Parameters
        ----------
        value : int
            Allowed values for the state are 0 (ON) or 1 (OFF).
        """
        return await self.modbus.write_coil(self._coil, value, unit=0)


class DigitalOutput(Feature):
    """Class for the digital output feature from the Unipi Neuron."""

    name: Optional[str] = "Digital Output"
    feature_name: Optional[str] = "relay"
    feature_type: Optional[str] = "digital"

    async def set_state(self, value: int):
        """Set the state for the digital output feature.

        Parameters
        ----------
        value : int
            Allowed values for the state are 0 (ON) or 1 (OFF).
        """
        return await self.modbus.write_coil(self._coil, value, unit=0)


class DigitalInput(Feature):
    """Class for the digital input feature from the Unipi Neuron."""

    name: Optional[str] = "Digital Input"
    feature_name: Optional[str] = "input"
    feature_type: Optional[str] = "digital"


class AnalogueOutput(Feature):
    """Class for the analogue output feature from the Unipi Neuron."""

    name: Optional[str] = "Analog Output"
    feature_name: Optional[str] = "output"
    feature_type: Optional[str] = "analog"

    def __init__(self, board, circuit: str, mask: Optional[int] = None, *args, **kwargs):
        super().__init__(board, circuit, mask, *args, **kwargs)

        self.ai_config = board.neuron.modbus_cache_map.get_register(
            address=1,
            index=self._cal_reg
        )

        self.ai_voltage_deviation = board.neuron.modbus_cache_map.get_register(
            address=1,
            index=self._cal_reg + 1
        )

        self.ai_voltage_offset = board.neuron.modbus_cache_map.get_register(
            address=1,
            index=self._cal_reg + 2
        )

    @staticmethod
    def _uint16_to_int(inp):
        if inp > 0x8000:
            return inp - 0x10000

        return inp

    @property
    def offset(self) -> float:
        _offset: float = 0

        if self._cal_reg > 0:
            _offset = self._uint16_to_int(
                self.ai_voltage_deviation[0]
            ) / 10000.0

        return _offset

    @property
    def is_voltage(self) -> bool:
        _is_voltage: bool = True

        if self.circuit == "ao_1_01" and self._cal_reg >= 0:
            _is_voltage = self.ai_config == 0

        return _is_voltage

    @property
    def mode(self) -> str:
        _mode: str = "Resistance"

        if self.is_voltage:
            _mode: str = "Voltage"
        elif self.ai_config[0] == 1:
            _mode = "Current"

        return _mode

    @property
    def factor(self) -> float:
        _factor: float = self.board.volt_ref / 4095 * (1 / 10000.0)

        if self.circuit == "ao_1_01":
            _factor = self.board.volt_ref / 4095 * (
                1 + self._uint16_to_int(self.ai_voltage_deviation[0]) / 10000.0
            )

        if self.is_voltage:
            _factor *= 3
        else:
            _factor *= 10

        return _factor

    @property
    def factor_x(self) -> float:
        _factor_x: float = self.board.volt_ref_x / 4095 * (1 / 10000.0)

        if self.circuit == "ao_1_01":
            _factor_x = self.board.volt_ref_x / 4095 * (
                1 + self._uint16_to_int(self.ai_config[0]) / 10000.0
            )

        if self.is_voltage:
            _factor_x *= 3
        else:
            _factor_x *= 10

        return _factor_x

    @property
    def changed(self) -> bool:
        value: bool = self.value == True  # noqa
        changed: bool = value != self._value

        if changed:
            self._value = value

        return changed

    @property
    def value(self) -> int:
        _value = self._reg_value() * 0.0025

        if self.circuit == "ao_1_01":
            _value = self._reg_value() * self.factor + self.offset

        return _value

    async def set_state(self, value: int) -> None:
        """Set the state for the analog output feature.

        Parameters
        ----------
        value : int
            Allowed values for the state are 0 (ON) or 1 (OFF).
        """
        value_i: int = int(float(value) / 0.0025)

        if self.circuit == "ao_1_01":
            value_i = int((float(value) - self.offset) / self.factor)

        if value_i < 0:
            value_i = 0
        elif value_i > 4095:
            value_i = 4095

        await self.modbus.write_register(self._cal_reg, value_i, unit=0)


class AnalogueInput(Feature):
    """Class for the analog input feature from the Unipi Neuron."""

    name: Optional[str] = "Analog Input"
    feature_name: Optional[str] = "input"
    feature_type: Optional[str] = "analog"


class Led(Feature):
    """Class for the LED feature from the Unipi Neuron."""

    name: Optional[str] = "LED"
    feature_name: Optional[str] = "led"
    feature_type: Optional[str] = None

    async def set_state(self, value: int) -> None:
        """Set the state for the LED feature.

        Parameters
        ----------
        value : int
            Allowed values for the state are 0 (ON) or 1 (OFF).
        """
        await self.modbus.write_coil(self._coil, value, unit=0)


class FeatureMap(DataStorage):
    """A read-only container object that has saved Unipi Neuron feature classes.

    See Also
    --------
    helpers.DataStorage
    """

    def register(self, feature: Feature) -> None:
        """Add a feature to the data storage.

        Parameters
        ----------
        feature : Feature
        """
        if not self.data.get(feature.type):
            self.data[feature.type] = []

        self.data[feature.type].append(feature)

    def by_circuit(self, circuit: str, feature_type: Optional[list] = None) -> Union[DigitalInput, DigitalOutput, Relay, Led]:
        """Get feature by circuit name.

        Parameters
        ----------
        circuit : str
            The machine readable circuit name e.g. ro_2_01.
        feature_type : list

        Returns
        ----------
        DigitalInput, DigitalOutput, Relay, Led
            The feature class.

        Raises
        ------
        StopIteration
            Get an exception if circuit not found.
        """
        if feature_type:
            data: Iterator = self.by_feature_type(feature_type)
        else:
            data: Iterator = itertools.chain.from_iterable(self.data.values())

        try:
            feature = next(filter(lambda d: d.circuit == circuit, data))
        except StopIteration:
            sys.exit(colored(f"[CONFIG] `{circuit}` not found in {self.__class__.__name__}!", "red"))

        return feature

    def by_feature_type(self, feature_type: list) -> Iterator:
        """Filter features by feature type.

        Parameters
        ----------
        feature_type : list

        Returns
        ----------
        Iterator
            A list of features filtered by feature type.
        """
        return itertools.chain.from_iterable(
            filter(None, map(self.data.get, feature_type))
        )
