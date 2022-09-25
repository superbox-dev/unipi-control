import dataclasses
import logging
import re
import socket
import struct
import sys
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from dataclasses import is_dataclass
from pathlib import Path
from tempfile import gettempdir
from typing import Any
from typing import Dict
from typing import Final
from typing import List
from typing import Match
from typing import NamedTuple
from typing import Optional

import yaml

from unipi_control.helpers import DataStorage

COVER_TYPES: Final[List[str]] = ["blind", "roller_shutter", "garage_door"]

LOG_MQTT_PUBLISH: Final[str] = "[MQTT] [%s] Publishing message: %s"
LOG_MQTT_SUBSCRIBE: Final[str] = "[MQTT] [%s] Subscribe message: %s"
LOG_MQTT_SUBSCRIBE_TOPIC: Final[str] = "[MQTT] Subscribe topic %s"
LOGGER_NAME: Final[str] = "unipi-control"

stdout_handler = logging.StreamHandler(stream=sys.stdout)
stdout_handler.setFormatter(logging.Formatter(fmt="%(levelname)8s | %(message)s"))

logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(logging.INFO)
logger.addHandler(stdout_handler)


class LogPrefix:
    CONFIG: Final[str] = "[CONFIG]"
    COVER: Final[str] = "[COVER]"


class RegexValidation(NamedTuple):
    regex: str
    error: str


class Validation:
    ALLOWED_CHARACTERS: RegexValidation = RegexValidation(
        regex=r"^[a-z\d_-]*$", error="The following characters are prohibited: a-z 0-9 -_"
    )


@dataclass
class ConfigMixin:
    def update(self, new):
        for key, value in new.items():
            if hasattr(self, key):
                item = getattr(self, key)

                if is_dataclass(item):
                    item.update(value)
                else:
                    setattr(self, key, value)

    def validate(self):
        for f in dataclasses.fields(self):
            value: Any = getattr(self, f.name)

            if is_dataclass(value):
                value.validate()
            else:
                if method := getattr(self, f"validate_{f.name}", None):
                    setattr(self, f.name, method(getattr(self, f.name), f=f))

                if not isinstance(value, f.type) and not is_dataclass(value):
                    logger.error(
                        "[CONFIG] Expected %s to be %s, got %s",
                        f.name,
                        f.type,
                        repr(value),
                    )

                    sys.exit(1)


@dataclass
class MqttConfig(ConfigMixin):
    host: str = field(default="localhost")
    port: int = field(default=1883)
    keepalive: int = field(default=15)
    retry_limit: int = field(default=30)
    reconnect_interval: int = field(default=10)


@dataclass
class DeviceInfo(ConfigMixin):
    manufacturer: str = field(default="Unipi technology")


@dataclass
class HomeAssistantConfig(ConfigMixin):
    enabled: bool = field(default=True)
    discovery_prefix: str = field(default="homeassistant")
    device: DeviceInfo = field(default=DeviceInfo())

    def validate_discovery_prefix(self, value: str, f: dataclasses.Field):
        value = value.lower()
        result: Optional[Match[str]] = re.search(Validation.ALLOWED_CHARACTERS.regex, value)

        if result is None:
            logger.error(
                "%s [%s] Invalid value '%s' in '%s'. %s",
                LogPrefix.CONFIG,
                self.__class__.__name__.replace("Config", "").upper(),
                value,
                f.name,
                Validation.ALLOWED_CHARACTERS.error,
            )
            sys.exit(1)

        return value


@dataclass
class LoggingConfig(ConfigMixin):
    level: str = field(default="info")


@dataclass
class FeatureConfig(ConfigMixin):
    id: str = field(default_factory=str)
    invert_state: bool = field(default=False)
    friendly_name: str = field(default_factory=str)
    suggested_area: str = field(default_factory=str)


@dataclass
class CoverConfig(ConfigMixin):
    id: str = field(default_factory=str)
    friendly_name: str = field(default_factory=str)
    suggested_area: str = field(default_factory=str)
    cover_type: str = field(default_factory=str)
    topic_name: str = field(default_factory=str)
    cover_run_time: float = field(default_factory=float)
    tilt_change_time: float = field(default_factory=float)
    circuit_up: str = field(default_factory=str)
    circuit_down: str = field(default_factory=str)

    def validate(self):
        for f in [
            "friendly_name",
            "topic_name",
            "cover_type",
            "circuit_up",
            "circuit_down",
        ]:
            if not getattr(self, f):
                logger.error("[CONFIG] %s Required key '%s' is missing! %s", LogPrefix.COVER, f, repr(self))
                sys.exit(1)

        super().validate()

    def validate_topic_name(self, value: str, f: dataclasses.Field):
        value = value.lower()
        result: Optional[Match[str]] = re.search(Validation.ALLOWED_CHARACTERS.regex, value)

        if result is None:
            logger.error(
                "%s [%s] Invalid value '%s' in '%s'. %s",
                LogPrefix.CONFIG,
                self.__class__.__name__.replace("Config", "").upper(),
                value,
                f.name,
                Validation.ALLOWED_CHARACTERS.error,
            )
            sys.exit(1)

        return value

    def validate_cover_type(self, value: str, f: dataclasses.Field):
        value = value.lower()

        if value not in COVER_TYPES:
            logger.error(
                "[CONFIG] %s Invalid value '%s' in 'cover_type'. The following values are allowed: %s.",
                LogPrefix.COVER,
                self.cover_type,
                " ".join(COVER_TYPES),
            )
            sys.exit(1)

        return value


@dataclass
class Config(ConfigMixin):
    device_name: str = field(default=socket.gethostname())
    mqtt: MqttConfig = field(default_factory=MqttConfig)
    homeassistant: HomeAssistantConfig = field(default_factory=HomeAssistantConfig)
    features: dict = field(init=False, default_factory=dict)
    covers: list = field(init=False, default_factory=list)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    config_base_path: Path = field(default=Path("/etc/unipi"))
    systemd_path: Path = field(default=Path("/etc/systemd/system"))
    temp_path: Path = field(default=Path(gettempdir()) / "unipi")

    def __post_init__(self):
        self.temp_path.mkdir(exist_ok=True)

        _config: dict = self.get_config(self.config_base_path / "control.yaml")
        self.update(_config)
        self.validate()

        self._change_logger_level()

    def validate(self):
        super().validate()

        for circuit, feature_data in self.features.items():
            try:
                feature_config: FeatureConfig = FeatureConfig(**feature_data)
                feature_config.validate()
                self.features[circuit] = feature_config
            except TypeError:
                logger.error("[CONFIG] Invalid feature property: %s", feature_data)
                sys.exit(1)

        for index, cover_data in enumerate(self.covers):
            try:
                cover_config: CoverConfig = CoverConfig(**cover_data)
                cover_config.validate()
                self.covers[index] = cover_config
            except TypeError:
                logger.error("[CONFIG] Invalid cover property: %s", cover_data)
                sys.exit(1)

        self.validate_covers_circuits()

    @property
    def hardware_path(self) -> Path:
        return self.config_base_path / "hardware"

    def _change_logger_level(self):
        level: Dict[str, int] = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
        }

        logger.setLevel(level[self.logging.level])

    @staticmethod
    def get_config(config_path: Path) -> dict:
        _config: dict = {}

        if config_path.exists():
            _config = yaml.load(config_path.read_text(), Loader=yaml.FullLoader)

        return _config

    def get_cover_circuits(self) -> List[str]:
        """Get all circuits that are defined in the cover config."""
        circuits: List[str] = []

        for cover in self.covers:
            circuit_up: str = cover.circuit_up
            circuit_down: str = cover.circuit_down

            if circuit_up:
                circuits.append(circuit_up)

            if circuit_down:
                circuits.append(circuit_down)

        return circuits

    def validate_covers_circuits(self):
        circuits: List[str] = self.get_cover_circuits()

        for circuit in circuits:
            if circuits.count(circuit) > 1:
                logger.error(
                    "[CONFIG] %s Duplicate circuits found in 'covers'. "
                    "Driving both signals up and down at the same time can damage the motor!",
                    LogPrefix.COVER,
                )
                sys.exit(1)

    @staticmethod
    def validate_device_name(value: str, f: dataclasses.Field):
        value = value.lower()
        result: Optional[Match[str]] = re.search(Validation.ALLOWED_CHARACTERS.regex, value)

        if result is None:
            logger.error(
                "%s Invalid value '%s' in '%s'. %s",
                LogPrefix.CONFIG,
                value,
                f.name,
                Validation.ALLOWED_CHARACTERS.error,
            )
            sys.exit(1)

        return value


@dataclass
class HardwareInfo:
    name: str = field(default="unknown")
    model: str = field(default="unknown", init=False)
    version: str = field(default="unknown", init=False)
    serial: str = field(default="unknown", init=False)

    def __post_init__(self):
        unipi_1: Path = Path("/sys/bus/i2c/devices/1-0050/eeprom")
        unipi_patron: Path = Path("/sys/bus/i2c/devices/2-0057/eeprom")
        unipi_neuron_1: Path = Path("/sys/bus/i2c/devices/1-0057/eeprom")
        unipi_neuron_0: Path = Path("/sys/bus/i2c/devices/0-0057/eeprom")

        if unipi_1.is_file():
            with open(unipi_1, "rb") as f:
                ee_bytes = f.read(256)

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
            with open(unipi_patron, "rb") as f:
                ee_bytes = f.read(128)

                self.name = "Unipi Patron"
                self.model = f"{ee_bytes[106:110].decode()}"
                self.version = f"{ee_bytes[99]}.{ee_bytes[98]}"
                self.serial = struct.unpack("i", ee_bytes[100:104])[0]
        elif unipi_neuron_1.is_file():
            with open(unipi_neuron_1, "rb") as f:
                ee_bytes = f.read(128)

                self.name = "Unipi Neuron"
                self.model = f"{ee_bytes[106:110].decode()}"
                self.version = f"{ee_bytes[99]}.{ee_bytes[98]}"
                self.serial = struct.unpack("i", ee_bytes[100:104])[0]
        elif unipi_neuron_0.is_file():
            with open(unipi_neuron_0, "rb") as f:
                ee_bytes = f.read(128)

                self.name = "Unipi Neuron"
                self.model = f"{ee_bytes[106:110].decode()}"
                self.version = f"{ee_bytes[99]}.{ee_bytes[98]}"
                self.serial = struct.unpack("i", ee_bytes[100:104])[0]


class HardwareData(DataStorage):
    def __init__(self, config: Config):
        super().__init__()

        self.config = config

        self.data: dict = {
            "neuron": asdict(HardwareInfo()),
            "definitions": [],
            "neuron_definition": None,
        }

        self._model: str = self.data["neuron"]["model"]

        if self._model is None:
            logger.error("[CONFIG] Hardware is not supported!")
            sys.exit(1)

        self._read_definitions()
        self._read_neuron_definition()

    def _read_definitions(self):
        try:
            for f in Path(f"{self.config.hardware_path}/extension").iterdir():
                if f.suffix == ".yaml":
                    self.data["definitions"].append(yaml.load(f.read_text(), Loader=yaml.FullLoader))
                    logger.debug("[CONFIG] YAML Definition loaded: %s", f)
        except FileNotFoundError as error:
            logger.info("[CONFIG] %s", str(error))

    def _read_neuron_definition(self):
        definition_file: Path = Path(f"{self.config.hardware_path}/neuron/{self._model}.yaml")

        if definition_file.is_file():
            self.data["neuron_definition"] = yaml.load(definition_file.read_text(), Loader=yaml.FullLoader)
            logger.debug("[CONFIG] YAML Definition loaded: %s", definition_file)
        else:
            logger.error("[CONFIG] No valid YAML definition for active Neuron device! Device name is %s", self._model)
            sys.exit(1)
