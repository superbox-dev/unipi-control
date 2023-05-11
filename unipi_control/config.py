import dataclasses
import logging
import re
import socket
import struct
from dataclasses import dataclass
from dataclasses import field
from dataclasses import is_dataclass
from functools import cached_property
from pathlib import Path
from tempfile import gettempdir
from typing import Any
from typing import Final
from typing import Generator
from typing import Iterator
from typing import List
from typing import Literal
from typing import Mapping
from typing import NamedTuple
from typing import Optional
from typing import TypedDict
from typing import Union

from unipi_control.exception import ConfigError
from unipi_control.helpers.log import LOG_LEVEL
from unipi_control.helpers.log import STDOUT_LOG_FORMAT
from unipi_control.helpers.log import SYSTEMD_LOG_FORMAT
from unipi_control.helpers.log import SystemdHandler
from unipi_control.helpers.yaml import yaml_loader_safe

logger: logging.Logger = logging.getLogger()

DEFAULT_CONFIG_PATH: Final[Path] = Path("/etc/unipi")
DEVICE_CLASSES: Final[List[str]] = ["blind", "roller_shutter", "garage_door"]

MODBUS_BAUD_RATES: Final[List[int]] = [2400, 4800, 9600, 19200, 38400, 57600, 115200]
MODBUS_PARITY: Final[List[str]] = ["E", "O", "N"]


class LogPrefix:
    CONFIG: Final[str] = "[CONFIG]"
    COVER: Final[str] = "[COVER]"
    DEVICEINFO: Final[str] = "[DEVICEINFO]"
    MQTT: Final[str] = "[MQTT]"
    FEATURE: Final[str] = "[FEATURE]"
    MODBUS: Final[str] = "[MODBUS]"


class RegexValidation(NamedTuple):
    regex: str
    error: str


class Validation:
    NAME: RegexValidation = RegexValidation(
        regex=r"^[A-Za-z\d\s_-]*$", error="The following characters are prohibited: a-z 0-9 -_ space"
    )

    ID: RegexValidation = RegexValidation(
        regex=r"^[A-Za-z\d_-]*$", error="The following characters are prohibited: a-z 0-9 -_"
    )


@dataclass
class ConfigLoaderMixin:
    def update(self, new: dict) -> None:
        """Update and validate config data class with settings from a dictionary.

        Parameters
        ----------
        new: dict
            Overwrite settings as dictionary.
        """
        for key, value in new.items():
            if hasattr(self, key):
                item = getattr(self, key)

                if is_dataclass(item):
                    item.update(value)
                else:
                    setattr(self, key, value)

        self.validate()

    def update_from_yaml_file(self, config_path: Path) -> None:
        """Update and validate config data class with settings from a YAML file.

        Parameters
        ----------
        config_path: Path
            Path to the YAML file.
        """
        if config_path.exists():
            yaml_data: Union[dict, list] = yaml_loader_safe(config_path)

            if isinstance(yaml_data, dict):
                self.update(yaml_data)

    def validate(self) -> None:
        """Validate config data class arguments."""
        for _field in dataclasses.fields(self):
            value: Any = getattr(self, _field.name)

            if is_dataclass(value):
                value.validate()
            else:
                if method := getattr(self, f"_validate_{_field.name}", None):
                    setattr(self, _field.name, method(getattr(self, _field.name), _field=_field))

                if not isinstance(value, _field.type) and not is_dataclass(value):
                    msg = f"Expected {_field.name} to be {_field.type}, got {repr(value)}"
                    raise ConfigError(msg)


@dataclass
class DeviceInfo(ConfigLoaderMixin):
    name: str = field(default=socket.gethostname())
    manufacturer: str = field(default="Unipi technology")

    @staticmethod
    def _validate_name(value: str, _field: dataclasses.Field) -> str:
        if re.search(Validation.NAME.regex, value) is None:
            msg = f"{LogPrefix.DEVICEINFO} Invalid value '{value}' in '{_field.name}'. {Validation.NAME.error}"
            raise ConfigError(msg)

        return value


@dataclass
class MqttConfig(ConfigLoaderMixin):
    host: str = field(default="localhost")
    port: int = field(default=1883)
    keepalive: int = field(default=15)
    retry_limit: int = field(default=30)
    reconnect_interval: int = field(default=10)


@dataclass
class FeatureConfig(ConfigLoaderMixin):
    object_id: str = field(default_factory=str)
    friendly_name: str = field(default_factory=str)
    icon: str = field(default_factory=str)
    device_class: str = field(default_factory=str)
    state_class: str = field(default_factory=str)
    unit_of_measurement: str = field(default_factory=str)
    suggested_area: str = field(default_factory=str)
    invert_state: bool = field(default=False)

    @staticmethod
    def _validate_object_id(value: str, _field: dataclasses.Field) -> str:
        value = value.lower()

        if re.search(Validation.ID.regex, value) is None:
            msg = f"{LogPrefix.FEATURE} Invalid value '{value}' in '{_field.name}'. {Validation.ID.error}"
            raise ConfigError(msg)

        return value


@dataclass
class CoverConfig(ConfigLoaderMixin):
    object_id: str = field(default_factory=str)  # pylint: disable=invalid-name
    friendly_name: str = field(default_factory=str)
    suggested_area: str = field(default_factory=str)
    device_class: str = field(default_factory=str)
    cover_run_time: float = field(default_factory=float)
    tilt_change_time: float = field(default_factory=float)
    cover_up: str = field(default_factory=str)
    cover_down: str = field(default_factory=str)

    def validate(self) -> None:
        """Validate cover configuration."""
        for _field in ("object_id", "friendly_name", "device_class", "cover_up", "cover_down"):
            if not getattr(self, _field):
                msg = f"{LogPrefix.COVER} Required key '{_field}' is missing! {repr(self)}"
                raise ConfigError(msg)

        super().validate()

    @staticmethod
    def _validate_object_id(value: str, _field: dataclasses.Field) -> str:
        value = value.lower()

        if re.search(Validation.ID.regex, value) is None:
            msg = f"{LogPrefix.COVER} Invalid value '{value}' in '{_field.name}'. {Validation.ID.error}"
            raise ConfigError(msg)

        return value

    def _validate_device_class(self, value: str, _field: dataclasses.Field) -> str:
        if (value := value.lower()) not in DEVICE_CLASSES:
            exception_message: str = (
                f"{LogPrefix.COVER} Invalid value '{self.device_class}' in '{_field.name}'. "
                f"The following values are allowed: {' '.join(DEVICE_CLASSES)}."
            )
            raise ConfigError(exception_message)

        return value


@dataclass
class ModbusUnitConfig(ConfigLoaderMixin):
    unit: int = field(default_factory=int)
    device_name: str = field(default_factory=str)
    identifier: str = field(default_factory=str)
    suggested_area: str = field(default_factory=str)

    def _validate_device_name(self, value: str, _field: dataclasses.Field) -> str:
        if not value:
            msg = f"{LogPrefix.MODBUS} Device name for unit '{self.unit}' is missing!"
            raise ConfigError(msg)

        return value


@dataclass
class ModbusConfig(ConfigLoaderMixin):
    baud_rate: int = field(default=2400)
    parity: str = field(default="N")
    units: list = field(init=False, default_factory=list)

    def init(self) -> None:
        """Initialize Modbus configuration and start custom validation."""
        for index, unit in enumerate(self.units):
            unit_config: ModbusUnitConfig = ModbusUnitConfig()
            unit_config.update(unit)
            self.units[index] = unit_config

        self._validate_unique_units()

    def get_units_by_identifier(self, identifier: str) -> Generator:
        """Filter units by identifier.

        Parameters
        ----------
        identifier: str
            A unique units identifier.

        Returns
        -------
        Generator:
            Filtered units.
        """
        return (modbus_unit for modbus_unit in self.units if modbus_unit.identifier == identifier)

    def _validate_unique_units(self) -> None:
        unique_units: List[int] = []

        for unit in self.units:
            if unit.unit in unique_units:
                msg = f"{LogPrefix.MODBUS} Duplicate modbus unit '{unit.unit}' found in 'units'!"
                raise ConfigError(msg)

            unique_units.append(unit.unit)

    @staticmethod
    def _validate_baud_rate(value: str, _field: dataclasses.Field) -> str:
        if value not in MODBUS_BAUD_RATES:
            exception_message: str = (
                f"{LogPrefix.MODBUS} Invalid baud rate '{value}. "
                f"The following baud rates are allowed: {' '.join(str(baud_rate) for baud_rate in MODBUS_BAUD_RATES)}."
            )
            raise ConfigError(exception_message)

        return value

    @staticmethod
    def _validate_parity(value: str, _field: dataclasses.Field) -> str:
        if (value := value.upper()) not in MODBUS_PARITY:
            exception_message: str = (
                f"{LogPrefix.MODBUS} Invalid value '{value}' in '{_field.name}'. "
                f"The following parity options are allowed: {' '.join(MODBUS_PARITY)}."
            )
            raise ConfigError(exception_message)

        return value


@dataclass
class HomeAssistantConfig(ConfigLoaderMixin):
    enabled: bool = field(default=True)
    discovery_prefix: str = field(default="homeassistant")

    def _validate_discovery_prefix(self, value: str, _field: dataclasses.Field) -> str:
        value = value.lower()

        if re.search(Validation.ID.regex, value) is None:
            exception_message: str = (
                f"[{self.__class__.__name__.replace('Config', '').upper()}] "
                f"Invalid value '{value}' in '{_field.name}'. {Validation.ID.error}"
            )
            raise ConfigError(exception_message)

        return value


@dataclass
class LoggingConfig(ConfigLoaderMixin):
    level: str = field(default="error")

    @property
    def verbose(self) -> int:
        """Get logging verbose level as integer."""
        return list(LOG_LEVEL).index(self.level)

    def init(self, log: Optional[str], verbose: int = 0) -> None:
        """Initialize logger handler and formatter.

        Parameters
        ----------
        log: str
            set log handler to systemd, stdout or file.
        verbose: int
            Logging verbose level as integer.
        """
        logger.setLevel(LOG_LEVEL["info"])

        if log == "systemd":
            systemd_handler = SystemdHandler()
            systemd_handler.setFormatter(logging.Formatter(SYSTEMD_LOG_FORMAT))
            logger.addHandler(systemd_handler)
        else:
            stdout_handler: logging.Handler = logging.StreamHandler()
            stdout_handler.setFormatter(logging.Formatter(STDOUT_LOG_FORMAT))
            logger.addHandler(stdout_handler)

        self.update_level(verbose)

    def update_level(self, verbose: int) -> None:
        """Update the logging level in config data class.

        Parameters
        ----------
        verbose: int
            Logging verbose level as integer.
        """
        levels: List[int] = list(LOG_LEVEL.values())
        level: int = levels[min(max(verbose, self.verbose), len(levels) - 1)]

        logger.setLevel(level)

    def _validate_level(self, value: str, _field: dataclasses.Field) -> str:
        if (value := value.lower()) not in LOG_LEVEL.keys():
            exception_message: str = (
                f"[{self.__class__.__name__.replace('Config', '').upper()}] "
                f"Invalid log level '{self.level}'. The following log levels are allowed: {' '.join(LOG_LEVEL.keys())}."
            )
            raise ConfigError(exception_message)

        return value


@dataclass
class Config(ConfigLoaderMixin):
    device_info: DeviceInfo = field(default_factory=DeviceInfo)
    mqtt: MqttConfig = field(default_factory=MqttConfig)
    modbus: ModbusConfig = field(default_factory=ModbusConfig)
    homeassistant: HomeAssistantConfig = field(default_factory=HomeAssistantConfig)
    features: dict = field(init=False, default_factory=dict)
    covers: list = field(init=False, default_factory=list)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    config_base_path: Path = field(default=DEFAULT_CONFIG_PATH)
    temp_path: Path = field(default=Path(gettempdir()) / "unipi")
    sys_bus: Path = field(default=Path("/sys/bus/i2c/devices"))

    @cached_property
    def hardware_path(self) -> Path:
        """Return hardware path to neuron devices and extensions."""
        return self.config_base_path / "hardware"

    def __post_init__(self) -> None:
        self.temp_path.mkdir(exist_ok=True)
        self.update_from_yaml_file(config_path=self.config_base_path / "control.yaml")

        self.init()
        self.modbus.init()

    def init(self) -> None:
        """Initialize configuration and start custom validation."""
        for feature_id, feature_data in self.features.items():
            feature_config: FeatureConfig = FeatureConfig()
            feature_config.update(feature_data)
            self.features[feature_id] = feature_config

        for index, cover_data in enumerate(self.covers):
            cover_config: CoverConfig = CoverConfig()
            cover_config.update(cover_data)
            self.covers[index] = cover_config

        self._validate_feature_object_ids()
        self._validate_covers_circuits()
        self._validate_cover_ids()

    def _validate_feature_object_ids(self) -> None:
        object_ids: List[str] = []

        for feature in self.features.values():
            if feature.object_id in object_ids:
                msg = f"{LogPrefix.FEATURE} Duplicate ID '{feature.object_id}' found in 'features'!"
                raise ConfigError(msg)

            if feature.object_id:
                object_ids.append(feature.object_id)

    def get_cover_circuits(self) -> List[str]:
        """Get all circuits that are defined in the cover config."""
        circuits: List[str] = []

        for cover in self.covers:
            cover_up: str = cover.cover_up
            cover_down: str = cover.cover_down

            if cover_up:
                circuits.append(cover_up)

            if cover_down:
                circuits.append(cover_down)

        return circuits

    def _validate_covers_circuits(self) -> None:
        circuits: List[str] = self.get_cover_circuits()

        for circuit in circuits:
            if circuits.count(circuit) > 1:
                exception_message: str = (
                    f"{LogPrefix.COVER} Duplicate circuits found in 'covers'. "
                    f"Driving both signals up and down at the same time can damage the motor!"
                )
                raise ConfigError(exception_message)

    def _validate_cover_ids(self) -> None:
        object_ids: List[str] = []

        for cover in self.covers:
            if cover.object_id in object_ids:
                msg = f"{LogPrefix.COVER} Duplicate ID '{cover.object_id}' found in 'covers'!"
                raise ConfigError(msg)

            object_ids.append(cover.object_id)

    @staticmethod
    def _validate_config_base_path(value: Path, _field: dataclasses.Field) -> Path:
        if not value.is_dir() or not value.exists():
            msg = f"{LogPrefix.DEVICEINFO} Config path '{value}' is invalid!"
            raise ConfigError(msg)

        return value


@dataclass
class HardwareInfo:
    sys_bus: Path
    name: str = field(default="unknown")
    model: str = field(default="unknown", init=False)
    version: str = field(default="unknown", init=False)
    serial: str = field(default="unknown", init=False)

    def __post_init__(self) -> None:
        unipi_1: Path = self.sys_bus / "1-0050/eeprom"
        unipi_patron: Path = self.sys_bus / "2-0057/eeprom"
        unipi_neuron_1: Path = self.sys_bus / "1-0057/eeprom"
        unipi_neuron_0: Path = self.sys_bus / "0-0057/eeprom"

        if unipi_1.is_file():
            with unipi_1.open("rb") as _file:
                ee_bytes = _file.read(256)

                if ee_bytes[226] == 1 and ee_bytes[227] == 1:
                    self.name = "Unipi"
                    self.version = "1.1"
                elif ee_bytes[226] == 11 and ee_bytes[227] == 1:
                    self.name = "Unipi Lite"
                    self.version = "1.1"
                else:
                    self.name = "Unipi"
                    self.version = "1.0"

                self.serial = struct.unpack("i", ee_bytes[228:232])[0]
        elif unipi_patron.is_file():
            with unipi_patron.open("rb") as _file:
                ee_bytes = _file.read(128)

                self.name = "Unipi Patron"
                self.model = f"{ee_bytes[106:110].decode()}"
                self.version = f"{ee_bytes[99]}.{ee_bytes[98]}"
                self.serial = struct.unpack("i", ee_bytes[100:104])[0]
        elif unipi_neuron_1.is_file():
            with unipi_neuron_1.open("rb") as _file:
                ee_bytes = _file.read(128)

                self.name = "Unipi Neuron"
                self.model = f"{ee_bytes[106:110].decode()}"
                self.version = f"{ee_bytes[99]}.{ee_bytes[98]}"
                self.serial = struct.unpack("i", ee_bytes[100:104])[0]
        elif unipi_neuron_0.is_file():
            with unipi_neuron_0.open("rb") as _file:
                ee_bytes = _file.read(128)

                self.name = "Unipi Neuron"
                self.model = f"{ee_bytes[106:110].decode()}"
                self.version = f"{ee_bytes[99]}.{ee_bytes[98]}"
                self.serial = struct.unpack("i", ee_bytes[100:104])[0]


class HardwareType:
    NEURON: Final[str] = "Neuron"
    EXTENSION: Final[str] = "Extension"


class HardwareDefinition(NamedTuple):
    unit: int
    hardware_type: str
    device_name: Optional[str]
    suggested_area: Optional[str]
    manufacturer: Optional[str]
    model: Optional[str]
    modbus_register_blocks: List[dict]
    modbus_features: List[dict]


class HardwareDataDict(TypedDict):
    neuron: HardwareInfo
    definitions: List[HardwareDefinition]


class HardwareData(Mapping):
    def __init__(self, config: Config) -> None:
        self.config = config

        self.data: HardwareDataDict = HardwareDataDict(
            neuron=HardwareInfo(sys_bus=config.sys_bus),
            definitions=[],
        )

        if self.data["neuron"].model is None:
            msg = "Hardware is not supported!"
            raise ConfigError(msg)

        self._read_neuron_definition()
        self._read_extension_definitions()

    def __getitem__(self, key: Literal["neuron", "definitions"]) -> Any:
        return self.data[key]

    def __iter__(self) -> Iterator:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def _read_neuron_definition(self) -> None:
        definition_file: Path = Path(f'{self.config.hardware_path}/neuron/{self.data["neuron"].model}.yaml')

        if definition_file.is_file():
            try:
                yaml_content: Union[dict, list] = yaml_loader_safe(definition_file)

                if isinstance(yaml_content, dict):
                    self.data["definitions"].append(
                        HardwareDefinition(
                            unit=0,
                            hardware_type=HardwareType.NEURON,
                            device_name=None,
                            suggested_area=None,
                            manufacturer=None,
                            model=f'{self.data["neuron"].name} {self.data["neuron"].model}',
                            modbus_register_blocks=yaml_content["modbus_register_blocks"],
                            modbus_features=yaml_content["modbus_features"],
                        )
                    )
            except TypeError as error:
                msg = f"{LogPrefix.CONFIG} Definition is invalid: {definition_file}"
                raise ConfigError(msg) from error

            logger.debug("%s Definition loaded: %s", LogPrefix.CONFIG, definition_file)
        else:
            msg = "No valid YAML definition found for this device!"
            raise ConfigError(msg)

    def _read_extension_definitions(self) -> None:
        try:
            for definition_file in Path(f"{self.config.hardware_path}/extensions").glob("*.yaml"):
                yaml_content: Union[dict, list] = yaml_loader_safe(definition_file)

                if isinstance(yaml_content, dict):
                    try:
                        units: Generator = self.config.modbus.get_units_by_identifier(identifier=definition_file.stem)

                        for unit in units:
                            self.data["definitions"].append(
                                HardwareDefinition(
                                    unit=unit.unit,
                                    hardware_type=HardwareType.EXTENSION,
                                    device_name=unit.device_name,
                                    suggested_area=unit.suggested_area,
                                    **yaml_content,
                                )
                            )
                    except TypeError as error:
                        msg = f"{LogPrefix.CONFIG} Definition is invalid: {definition_file}"
                        raise ConfigError(msg) from error

                    logger.debug("%s Definition loaded: %s", LogPrefix.CONFIG, definition_file)
        except FileNotFoundError as error:
            logger.info("%s %s", LogPrefix.CONFIG, str(error))

    def get_definition_by_hardware_types(self, hardware_types: List[str]) -> Generator:
        """Filter hardware definitions by hardware types.

        Parameters
        ----------
        hardware_types: list
            A list of hardware types to filter hardware definitions.

        Returns
        -------
        Generator:
            Filtered hardware definitions.
        """
        return (definition for definition in self.data["definitions"] if definition.hardware_type in hardware_types)
