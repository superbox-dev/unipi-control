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
from typing import Dict
from typing import List
from typing import Match
from typing import Optional

import yaml

from helpers import DataStorage

HARDWARE: str = "/etc/unipi/hardware"
COVER_TYPES: list = ["blind", "roller_shutter", "garage_door"]

LOG_COVER_DEVICE_LOCKED: str = "[COVER] [%s] Device is locked! Other position change is currently running."
LOG_MQTT_PUBLISH: str = "[MQTT] [%s] Publishing message: %s"
LOG_MQTT_SUBSCRIBE: str = "[MQTT] [%s] Subscribe message: %s"
LOG_MQTT_SUBSCRIBE_TOPIC: str = "[MQTT] Subscribe topic %s"

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger("asyncio")


@dataclass
class ConfigBase:
    def __post_init__(self):
        for f in dataclasses.fields(self):
            value = getattr(self, f.name)

            if not isinstance(value, f.type):
                logger.error(
                    "[CONFIG] %s - Expected %s to be %s, got %s",
                    self.__class__.__name__,
                    f.name,
                    f.type,
                    repr(value),
                )

                sys.exit(1)

    def update(self, new):
        for key, value in new.items():
            if hasattr(self, key):
                item = getattr(self, key)

                if is_dataclass(item):
                    item.update(value)
                else:
                    setattr(self, key, value)


@dataclass
class MqttConfig(ConfigBase):
    host: str = field(default="localhost")
    port: int = field(default=1883)
    keepalive: int = field(default=15)
    retry_limit: int = field(default=30)
    reconnect_interval: int = field(default=10)


@dataclass
class DeviceInfo(ConfigBase):
    manufacturer: str = field(default="Unipi technology")


@dataclass
class HomeAssistantConfig(ConfigBase):
    enabled: bool = field(default=True)
    discovery_prefix: str = field(default="homeassistant")
    device: DeviceInfo = field(default=DeviceInfo())


@dataclass
class LoggingConfig(ConfigBase):
    level: str = field(default="info")


@dataclass
class FeatureConfig(ConfigBase):
    invert_state: bool = field(default=False)
    friendly_name: str = field(default_factory=str)
    suggested_area: str = field(default_factory=str)


@dataclass
class CoverConfig(ConfigBase):
    friendly_name: str = field(default_factory=str)
    suggested_area: str = field(default_factory=str)
    cover_type: str = field(default_factory=str)
    topic_name: str = field(default_factory=str)
    full_open_time: float = field(default_factory=float)
    full_close_time: float = field(default_factory=float)
    tilt_change_time: float = field(default_factory=float)
    circuit_up: str = field(default_factory=str)
    circuit_down: str = field(default_factory=str)

    def __post_init__(self):
        super().__post_init__()

        for f in [
            "friendly_name",
            "topic_name",
            "cover_type",
            "full_open_time",
            "full_close_time",
            "circuit_up",
            "circuit_down",
        ]:
            if not self.friendly_name:
                logger.error("[CONFIG] [COVER] Required key '%s' is missing! %s", f, repr(self))
                sys.exit(1)

        if self.topic_name:
            result: Optional[Match[str]] = re.search(r"^[a-z\d_-]*$", self.topic_name)

            if result is None:
                logger.error(
                    "[CONFIG] [COVER] Invalid value '%s' in 'topic_name'. "
                    "The following characters are prohibited: a-z 0-9 -_",
                    self.topic_name,
                )
                sys.exit(1)

        if self.cover_type not in COVER_TYPES:
            logger.error(
                "[CONFIG] [COVER] Invalid value '%s' in 'cover_type'. The following values are allowed: %s.",
                self.cover_type,
                " ".join(COVER_TYPES),
            )
            sys.exit(1)


@dataclass
class Config(ConfigBase):
    device_name: str = field(default=socket.gethostname())
    mqtt: MqttConfig = field(default=MqttConfig())
    homeassistant: HomeAssistantConfig = field(default=HomeAssistantConfig())
    features: dict = field(init=False, default_factory=dict)
    covers: list = field(init=False, default_factory=list)
    logging: LoggingConfig = field(default=LoggingConfig())

    def __post_init__(self):
        super().__post_init__()

        config_path: Path = Path("/etc/unipi/control.yaml")
        _config: dict = self.get_config(config_path)

        self.update(_config)

        for circuit, feature_config in self.features.items():
            try:
                self.features[circuit] = FeatureConfig(**feature_config)
            except TypeError:
                logger.error("[CONFIG] Invalid feature property: %s", feature_config)
                sys.exit(1)

        for index, cover_config in enumerate(self.covers):
            self.covers[index] = CoverConfig(**cover_config)

        if self.device_name:
            result: Optional[Match[str]] = re.search(r"^[\w\d_-]*$", self.device_name)

            if result is None:
                logger.error(
                    "[CONFIG] Invalid value '%s' in 'device_name'. "
                    "The following characters are prohibited: A-Z a-z 0-9 -_",
                    self.device_name,
                )
                sys.exit(1)

        self.check_duplicate_covers_circuits()
        self._change_logger_level()

    @staticmethod
    def get_config(config_path: Path) -> dict:
        _config: dict = {}

        if config_path.exists():
            _config = yaml.load(config_path.read_text(), Loader=yaml.FullLoader)

        return _config

    def _change_logger_level(self):
        level: Dict[str, int] = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
        }

        logger.setLevel(level[self.logging.level])

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

    def check_duplicate_covers_circuits(self) -> Optional[str]:
        circuits: List[str] = self.get_cover_circuits()

        for circuit in circuits:
            if circuits.count(circuit) > 1:
                logger.error(
                    "[CONFIG] [COVER] Duplicate circuits found in 'covers'. "
                    "Driving both signals up and down at the same time can damage the motor!"
                )
                sys.exit(1)

        return None


@dataclass
class HardwareInfo:
    name: str = field(default="unknown", init=False)
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
    def __init__(self):
        super().__init__()

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
            for f in Path(f"{HARDWARE}/extension").iterdir():
                if f.suffix == ".yaml":
                    self.data["definitions"].append(yaml.load(f.read_text(), Loader=yaml.FullLoader))
                    logger.debug("[CONFIG] YAML Definition loaded: %s", f)
        except FileNotFoundError as error:
            logger.info("[CONFIG] %s", str(error))

    def _read_neuron_definition(self):
        definition_file: Path = Path(f"{HARDWARE}/neuron/{self._model}.yaml")

        if definition_file.is_file():
            self.data["neuron_definition"] = yaml.load(definition_file.read_text(), Loader=yaml.FullLoader)
            logger.debug("[CONFIG] YAML Definition loaded: %s", definition_file)
        else:
            logger.error("[CONFIG] No valid YAML definition for active Neuron device! Device name is %s", self._model)
            sys.exit(1)


config = Config()
