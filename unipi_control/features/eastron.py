"""Extensions features classes."""

from dataclasses import dataclass
from functools import cached_property
from typing import Callable, List
from typing import Optional
from typing import Union

from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

from unipi_control.config import Config
from unipi_control.config import FeatureConfig
from unipi_control.features.utils import FeatureType
from unipi_control.helpers.text import slugify
from unipi_control.helpers.typing import HardwareDefinition
from unipi_control.modbus.helper import ModbusHelper


@dataclass
class EastronModbus:
    helper: ModbusHelper
    val_reg: int


@dataclass
class EastronHardware:
    feature_type: FeatureType
    definition: HardwareDefinition
    version: Optional[str] = None


@dataclass
class EastronProps:
    friendly_name: str
    device_class: Optional[str] = None
    state_class: Optional[str] = None
    unit_of_measurement: Optional[str] = None


class Eastron:
    def __init__(
        self,
        config: Config,
        modbus: EastronModbus,
        hardware: EastronHardware,
        props: EastronProps,
    ) -> None:
        self.config: Config = config
        self.hardware: EastronHardware = hardware
        self.props: EastronProps = props

        self.features_config: Optional[FeatureConfig] = config.features.get(self.feature_id)

        self._reg_value: Callable[..., List[int]] = lambda: modbus.helper.get_register(
            address=modbus.val_reg, index=2, unit=hardware.definition.unit
        )
        self.saved_value: Optional[Union[float, int]] = None

    def __repr__(self) -> str:
        return self.props.friendly_name

    @property
    def payload(self) -> Optional[float]:
        """Return meter payload."""
        return self.value

    @property
    def value(self) -> Optional[float]:
        """Return Eastron meter value."""
        reg_value: List[int] = self._reg_value()

        return (
            round(
                float(
                    BinaryPayloadDecoder.fromRegisters(  # type: ignore[no-untyped-call]
                        reg_value, byteorder=Endian.BIG, wordorder=Endian.BIG
                    ).decode_32bit_float()
                ),
                2,
            )
            if reg_value
            else None
        )

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
        """Return slugify friendly name for unique feature id."""
        return f"{slugify(self.props.friendly_name)}_{self.hardware.definition.unit}"

    @cached_property
    def object_id(self) -> Optional[str]:
        """Return object id for Home Assistant."""
        if self.features_config:
            if self.features_config.object_id:
                return self.features_config.object_id.lower()

            if self.features_config.friendly_name:
                return slugify(self.features_config.friendly_name)

        return self.feature_id

    @cached_property
    def unique_id(self) -> str:
        """Return unique id for Home Assistant."""
        _unique_id: str = f"{slugify(self.config.device_info.name)}_{self.object_id}"

        return _unique_id

    @cached_property
    def friendly_name(self) -> str:
        """Return friendly name for Home Assistant."""
        _friendly_name: str = self.props.friendly_name

        if self.features_config and self.features_config.friendly_name:
            _friendly_name = self.features_config.friendly_name

        return _friendly_name

    @cached_property
    def topic(self) -> str:
        """Return Unique name for the MQTT topic."""
        return f"{slugify(self.config.device_info.name)}/{self.hardware.feature_type.topic_name}/{self.feature_id}"

    @cached_property
    def icon(self) -> Optional[str]:
        """Return icon from custom feature configuration."""
        return self.features_config.icon if self.features_config else None

    @cached_property
    def device_class(self) -> Optional[str]:
        """Return unit of device class from hardware definition or custom feature configuration."""
        if self.features_config and self.features_config.device_class:
            return self.features_config.device_class

        return self.props.device_class

    @cached_property
    def state_class(self) -> Optional[str]:
        """Return unit of state class from hardware definition or custom feature configuration."""
        if self.features_config and self.features_config.state_class:
            return self.features_config.state_class

        return self.props.state_class

    @cached_property
    def unit_of_measurement(self) -> Optional[str]:
        """Return unit of measurement from hardware definition or custom feature configuration."""
        if self.features_config and self.features_config.unit_of_measurement:
            return self.features_config.unit_of_measurement

        return self.props.unit_of_measurement

    @cached_property
    def sw_version(self) -> Optional[str]:
        """Return software version from the Eastron meter."""
        return self.hardware.version
