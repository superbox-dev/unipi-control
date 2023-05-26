"""Neuron features classes."""

from dataclasses import dataclass
from functools import cached_property
from typing import Callable
from typing import Optional
from typing import Union

from pymodbus.pdu import ModbusResponse

from unipi_control.config import Config
from unipi_control.config import FeatureConfig
from unipi_control.features.utils import FeatureState
from unipi_control.features.utils import FeatureType
from unipi_control.helpers.text import slugify
from unipi_control.helpers.typing import HardwareDefinition
from unipi_control.helpers.typing import ModbusClient
from unipi_control.helpers.typing import ModbusWriteData
from unipi_control.modbus import ModbusCacheData
from unipi_control.modbus import check_modbus_call


@dataclass
class Modbus:
    client: ModbusClient
    cache: ModbusCacheData
    val_reg: int
    val_coil: Optional[int] = None


@dataclass
class Hardware:
    major_group: int
    feature_type: FeatureType
    feature_index: int
    definition: HardwareDefinition
    firmware: Optional[str] = None


class NeuronFeature:
    def __init__(
        self,
        config: Config,
        modbus: Modbus,
        hardware: Hardware,
    ) -> None:
        self.config: Config = config
        self.modbus: Modbus = modbus
        self.hardware: Hardware = hardware

        self.features_config: Optional[FeatureConfig] = config.features.get(self.feature_id)

        self.val_coil: Optional[int] = (
            None if modbus.val_coil is None else modbus.val_coil + self.hardware.feature_index
        )
        self._reg_value: Callable[..., int] = lambda: modbus.cache.get_register(
            address=modbus.val_reg, index=1, unit=0
        )[0]
        self.saved_value: Optional[Union[float, int]] = None

    def __repr__(self) -> str:
        return self.base_friendly_name

    @property
    def changed(self) -> bool:
        """Detect whether the status has changed."""
        changed: bool = False

        if self.value != self.saved_value:
            changed = True
            self.saved_value = self.value

        return changed

    @cached_property
    def feature_id(self) -> str:
        """Return unique feature id."""
        return (
            f"{self.hardware.feature_type.short_name.lower()}_"
            f"{self.hardware.major_group}_"
            f"{self.hardware.feature_index + 1:02d}"
        )

    @cached_property
    def object_id(self) -> Optional[str]:
        """Return object id for Home Assistant."""
        if self.features_config and self.features_config.object_id:
            return self.features_config.object_id.lower()

        return None

    @cached_property
    def unique_id(self) -> str:
        """Return unique id for Home Assistant."""
        _unique_id: str = f"{slugify(self.config.device_info.name)}_"
        _unique_id += self.object_id if self.object_id else self.feature_id

        return _unique_id

    @cached_property
    def base_friendly_name(self) -> str:
        """Friendly name for the feature."""
        return (
            f"{self.hardware.feature_type.long_name} {self.hardware.major_group}.{self.hardware.feature_index + 1:02d}"
        )

    @cached_property
    def friendly_name(self) -> str:
        """Return friendly name for Home Assistant."""
        _friendly_name: str = f"{self.config.device_info.name}: {self.base_friendly_name}"

        if self.suggested_area:
            _friendly_name = f"{self.config.device_info.name} - {self.suggested_area}: {self.base_friendly_name}"

        if self.features_config and self.features_config.friendly_name:
            _friendly_name = self.features_config.friendly_name

        return _friendly_name

    @cached_property
    def suggested_area(self) -> Optional[str]:
        """Return suggested area for Home Assistant from hardware definition or custom feature configuration."""
        if self.features_config and self.features_config.suggested_area:
            return self.features_config.suggested_area

        return None

    @cached_property
    def topic(self) -> str:
        """Return Unique name for the MQTT topic."""
        return f"{slugify(self.config.device_info.name)}/{self.hardware.feature_type.topic_name}/{self.feature_id}"

    @property
    def payload(self) -> str:
        """Return the feature state as friendly name."""
        return FeatureState.ON if self.value == 1 else FeatureState.OFF

    @property
    def value(self) -> int:
        """Return the feature state as integer."""
        mask: int = 0x1 << (self.hardware.feature_index % 16)
        return 1 if self._reg_value() & mask else 0

    @cached_property
    def icon(self) -> Optional[str]:
        """Return icon from custom feature configuration."""
        return self.features_config.icon if self.features_config else None

    @cached_property
    def device_class(self) -> Optional[str]:
        """Return unit of device class from custom feature configuration."""
        return self.features_config.device_class if self.features_config else None

    @cached_property
    def sw_version(self) -> Optional[str]:
        """Return software version from the Unipi Neuron."""
        return self.hardware.firmware


class Relay(NeuronFeature):
    """Class for the relay feature from the Unipi Neuron."""

    async def set_state(self, value: bool) -> Optional[ModbusResponse]:
        """Set state for relay feature.

        Parameters
        ----------
        value: bool
            Feature value as boolean.

        Returns
        -------
        ModbusResponse
        """
        data: ModbusWriteData = {
            "address": self.val_coil,
            "value": value,
            "slave": 0,
        }

        return await check_modbus_call(self.modbus.client.tcp.write_coil, data)


class DigitalOutput(NeuronFeature):
    """Class for the digital output feature from the Unipi Neuron."""

    async def set_state(self, value: bool) -> Optional[ModbusResponse]:
        """Set state for digital output feature.

        Parameters
        ----------
        value: bool
            Feature value as boolean.

        Returns
        -------
        ModbusResponse
        """
        data: ModbusWriteData = {
            "address": self.val_coil,
            "value": value,
            "slave": 0,
        }

        return await check_modbus_call(self.modbus.client.tcp.write_coil, data)


class DigitalInput(NeuronFeature):
    """Class for the digital input feature from the Unipi Neuron."""


class Led(NeuronFeature):
    """Class for the LED feature from the Unipi Neuron."""

    async def set_state(self, value: bool) -> Optional[ModbusResponse]:
        """Set state for LED feature.

        Parameters
        ----------
        value: bool
            Feature value as boolean.

        Returns
        -------
        ModbusResponse
        """
        data: ModbusWriteData = {
            "address": self.val_coil,
            "value": value,
            "slave": 0,
        }

        return await check_modbus_call(self.modbus.client.tcp.write_coil, data)
