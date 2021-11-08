import os
import re
import socket
import struct
import sys
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from dataclasses import is_dataclass
from logging import basicConfig
from logging import DEBUG
from logging import ERROR
from logging import getLogger
from logging import INFO
from logging import Logger
from logging import WARNING
from pathlib import Path
from typing import Optional

import yaml
from helpers import DataStorage
from systemd import journal
from termcolor import colored

HARDWARE = "/etc/unipi/hardware"
COVER_TYPES = ["blind", "roller_shutter", "garage_door"]
LOG_MQTT_PUBLISH = "[MQTT][%s] Publishing message: %s"
LOG_MQTT_SUBSCRIBE = "[MQTT][%s] Subscribe message: %s"
LOG_MQTT_SUBSCRIBE_TOPIC = "[MQTT] Subscribe topic %s"


class HardwareException(Exception):
    """Unipi Control detect unsupported hardware."""
    pass


class ImproperlyConfigured(Exception):
    """Unipi Control is somehow improperly configured."""
    pass


@dataclass
class ConfigBase:
    """Base data class for the unipi control configs."""
    def clean(self):
        errors = []

        for key in self.__dict__.keys():
            clean_method = getattr(self, f"clean_{key}", None)

            if clean_method and callable(clean_method):
                error_msg: Optional[str] = clean_method()

                if error_msg:
                    errors.append(error_msg)

        if errors:
            sys.exit("\n".join(errors))

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
    """Data class for the default MQTT client config."""
    host: str = field(default="localhost")
    port: int = field(default=1883)
    keepalive: int = field(default=15)
    retry_limit: int = field(default=30)
    reconnect_interval: int = field(default=10)


@dataclass
class DeviceInfo(ConfigBase):
    """Data class for the default device info."""
    manufacturer: str = field(default="Unipi technology")


@dataclass
class HomeAssistantConfig(ConfigBase):
    """Data class for the default Home Assistant config."""
    enabled: bool = field(default=True)
    discovery_prefix: str = field(default="homeassistant")
    device: dataclass = field(default=DeviceInfo())


@dataclass
class LoggingConfig(ConfigBase):
    """Data class for the default logging config."""
    logger: str = field(default="systemd")
    level: str = field(default="info")


@dataclass
class Config(ConfigBase):
    """Data class for the default unipi control base config."""
    device_name: str = field(default=socket.gethostname())
    mqtt: dataclass = field(default=MqttConfig())
    homeassistant: dataclass = field(default=HomeAssistantConfig())
    features: dict = field(init=False, default_factory=dict)
    covers: list = field(init=False, default_factory=list)
    logging: dataclass = field(default=LoggingConfig())

    def __post_init__(self):
        _config: dict = self.get_config("/etc/unipi/control.yaml")
        self.update(_config)
        self.clean()

    @staticmethod
    def get_config(path: str) -> dict:
        """Read the unipi control yaml config file.

        Returns
        ----------
        dict
            The unipi control config as dict.
        """
        _config: dict = {}

        if os.path.exists(path):
            with open(path) as f:
                _config = yaml.load(f, Loader=yaml.FullLoader)

        return _config

    @property
    def logger(self):
        """Initialize logger with config settings.

        Returns
        -------
        Logger
            Return ``Logger`` class.
        """
        logger_type: str = self.logging.logger
        _logger: Logger = getLogger(__name__)

        level: dict = {
            "debug": DEBUG,
            "info": INFO,
            "warning": WARNING,
            "error": ERROR,
        }

        logger_level = level[self.logging.level]

        if logger_type == "systemd":
            _logger.addHandler(journal.JournalHandler())
            _logger.setLevel(level=logger_level)
        elif logger_type == "file":
            basicConfig(
                level=logger_level,
                filename="/var/log/unipi-control.log",
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )

        return _logger

    def get_cover_circuits(self) -> list:
        circuits: list = []

        for cover in self.covers:
            circuit_up: str = cover.get("circuit_up")
            circuit_down: str = cover.get("circuit_down")

            if circuit_up:
                circuits.append(circuit_up)

            if circuit_down:
                circuits.append(circuit_down)

        return circuits

    def clean_device_name(self) -> Optional[str]:
        result = re.search(r"^[\w\d_-]*$", self.device_name)

        if result is None:
            return colored("[CONFIG] Invalid value in \"device_name\". The following characters are prohibited: A-Z a-z 0-9 -_", "red")

    def clean_covers(self) -> Optional[str]:
        errors: list = []
        required_fields: list = [
            "cover_type", "topic_name", "full_open_time", "full_close_time",
            "circuit_up", "circuit_down"
        ]

        for index, cover in enumerate(self.covers):
            for key in list(set(required_fields) - set(cover.keys())):
                if key in required_fields:
                    errors.append(colored(f"""[CONFIG][COVER {index + 1}] Required key "{key}" is missing!""", "red"))
                    raise ImproperlyConfigured(f"""[CONFIG][COVER {index + 1}] Required key "{key}" is missing!""")

            for cover_time in ["full_open_time", "full_close_time", "tilt_change_time"]:
                value = cover.get(cover_time)

                if value and not isinstance(value, float) and not isinstance(value, int):
                    errors.append(
                        colored(f"""[CONFIG][COVER {index + 1}] Key "{cover_time}" is not a float or integer!""", "red"))

            result = re.search(r"^[a-z\d_-]*$", cover.get("topic_name", ""))

            if result is None:
                errors.append(
                    colored(f"""[CONFIG][COVER {index + 1}] Invalid value in "topic_name". The following characters are prohibited: a-z 0-9 -_""", "red"))

            if cover.get("cover_type") not in COVER_TYPES:
                errors.append(
                    colored(f"""[CONFIG][COVER {index + 1}] Invalid value in "cover_type". The following values are allowed: {" ".join(COVER_TYPES)}.""", "red"))

        return "\n".join(errors)

    def clean_dupicate_covers_circuits(self) -> Optional[str]:
        circuits: list = self.get_cover_circuits()

        for circuit in circuits:
            if circuits.count(circuit) > 1:
                return colored("[CONFIG][COVER] Duplicate circuits found in \"covers\"! Driving both signals up and down at the same time can damage the motor.", "red")


@dataclass
class HardwareInfo:
    """Data class for the Unipi neuron hardware information."""
    name: str = field(default="unknown", init=False)
    model: str = field(default="unknown", init=False)
    version: str = field(default="unknown", init=False)
    serial: str = field(default="unknown", init=False)

    def __post_init__(self):
        neuron: Path = Path("/sys/bus/i2c/devices/1-0057/eeprom")

        if neuron.is_file():
            with open(neuron, "rb") as f:
                ee_bytes = f.read(128)

                self.name = "Unipi Neuron"
                self.model = f"{ee_bytes[106:110].decode()}"
                self.version = f"{ee_bytes[99]}.{ee_bytes[98]}"
                self.serial = struct.unpack("i", ee_bytes[100:104])[0]


class HardwareData(DataStorage):
    """A read-only container object that has saved Unipi Neuron hardware data.

    The hardware data is imported from yaml files from ``/etc/unipi/hardware``.

    See Also
    --------
    helpers.DataStorage
    """
    def __init__(self):
        """Initialize hardware data."""
        super().__init__()

        self.data: dict = {
            "neuron": asdict(HardwareInfo()),
            "definitions": [],
            "neuron_definition": None,
        }

        self._model: str = self.data["neuron"]["model"]

        if self._model is None:
            raise HardwareException("[CONFIG] Hardware is not supported!")

        self._read_definitions()
        self._read_neuron_definition()

    def _read_definitions(self) -> None:
        for f in Path(f"{HARDWARE}/extension").iterdir():
            if str(f).endswith(".yaml"):
                with open(f) as yf:
                    self.data["definitions"].append(yaml.load(yf, Loader=yaml.FullLoader))
                    logger.info("[CONFIG] YAML Definition loaded: %s", f)

    def _read_neuron_definition(self) -> None:
        definition_file: Path = Path(f"{HARDWARE}/neuron/{self._model}.yaml")

        if definition_file.is_file():
            with open(definition_file) as yf:
                self.data["neuron_definition"] = yaml.load(yf, Loader=yaml.FullLoader)
                logger.info("[CONFIG] YAML Definition loaded: %s", definition_file)
        else:
            raise HardwareException(f"[CONFIG] No valid YAML definition for active Neuron device! Device name is {self._model}.")


config = Config()
logger = config.logger
