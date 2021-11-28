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
from typing import List

import yaml
from helpers import DataStorage
from systemd import journal
from termcolor import colored

HARDWARE: str = "/etc/unipi/hardware"
COVER_TYPES: list = ["blind", "roller_shutter", "garage_door"]
COVER_KEY_MISSING: str = "[CONFIG] [COVER %s] Required key `%s` is missing!"
COVER_TIME: str = "[CONFIG] [COVER %s] Key `%s` is not a float or integer!"
LOG_MQTT_PUBLISH: str = "[MQTT] [%s] Publishing message: %s"
LOG_MQTT_SUBSCRIBE: str = "[MQTT] [%s] Subscribe message: %s"
LOG_MQTT_SUBSCRIBE_TOPIC: str = "[MQTT] Subscribe topic %s"


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
        """If a clean function for key exists then validate it.

        Raises
        ------
        ImproperlyConfigured
            If errors exists then exit the script and print the errors.
        """
        errors = []

        for key in self.__dict__.keys():
            clean_method = getattr(self, f"clean_{key}", None)

            if clean_method and callable(clean_method):
                try:
                    clean_method()
                except ImproperlyConfigured as error:
                    errors.append(colored(str(error), "red"))

        if errors:
            sys.exit("\n".join(errors))

    def update(self, new):
        """Update the default config with custom config from the yaml file."""
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

    def get_cover_circuits(self) -> List[str]:
        """Get all circuits that are defined in the cover config.

        Returns
        ----------
        list
            A list of cover circuits.
        """
        circuits: List[str] = []

        for cover in self.covers:
            circuit_up: str = cover.get("circuit_up")
            circuit_down: str = cover.get("circuit_down")

            if circuit_up:
                circuits.append(circuit_up)

            if circuit_down:
                circuits.append(circuit_down)

        return circuits

    def clean_device_name(self):
        """Check if device name is valid."""
        result = re.search(r"^[\w\d_-]*$", self.device_name)

        if result is None:
            raise ImproperlyConfigured(
                "[CONFIG] Invalid value in `device_name`. "
                "The following characters are prohibited: A-Z a-z 0-9 -_"
            )

    def clean_covers(self):
        """Check if covers config is valid."""
        for index, cover in enumerate(self.covers):
            self._clean_covers_friendly_name(cover, index)
            self._clean_covers_cover_type(cover, index)
            self._clean_covers_topic_name(cover, index)
            self._clean_covers_full_open_time(cover, index)
            self._clean_covers_full_close_time(cover, index)
            self._clean_covers_tilt_change_time(cover, index)
            self._clean_covers_circuit_up(cover, index)
            self._clean_covers_circuit_down(cover, index)
            self._clean_duplicate_covers_circuits()

    @staticmethod
    def _clean_covers_friendly_name(cover, index):
        if "friendly_name" not in cover:
            raise ImproperlyConfigured(COVER_KEY_MISSING % (index + 1, "friendly_name"))

    @staticmethod
    def _clean_covers_cover_type(cover, index):
        if "cover_type" not in cover:
            raise ImproperlyConfigured(COVER_KEY_MISSING % (index + 1, "cover_type"))

        if cover.get("cover_type") not in COVER_TYPES:
            raise ImproperlyConfigured(
                f"""[CONFIG] [COVER {index + 1}] Invalid value in `cover_type`.
                The following values are allowed: {" ".join(COVER_TYPES)}."""
            )

    @staticmethod
    def _clean_covers_topic_name(cover, index):
        if "topic_name" not in cover:
            raise ImproperlyConfigured(COVER_KEY_MISSING % (index + 1, "topic_name"))

        result = re.search(r"^[a-z\d_-]*$", cover.get("topic_name", ""))

        if result is None:
            raise ImproperlyConfigured(
                f"[CONFIG] [COVER {index + 1}] Invalid value in `topic_name`."
                f" The following characters are prohibited: a-z 0-9 -_"
            )

    @staticmethod
    def _clean_covers_full_open_time(cover, index):
        if "full_open_time" not in cover:
            raise ImproperlyConfigured(COVER_KEY_MISSING % (index + 1, "full_open_time"))

        value = cover.get("full_open_time")

        if value and not isinstance(value, float) and not isinstance(value, int):
            raise ImproperlyConfigured(COVER_TIME % (index + 1, "full_open_time"))

    @staticmethod
    def _clean_covers_full_close_time(cover, index):
        if "full_close_time" not in cover:
            raise ImproperlyConfigured(COVER_KEY_MISSING % (index + 1, "full_close_time"))

        value = cover.get("full_close_time")

        if value and not isinstance(value, float) and not isinstance(value, int):
            raise ImproperlyConfigured(COVER_TIME % (index + 1, "full_close_time"))

    @staticmethod
    def _clean_covers_tilt_change_time(cover, index):
        value = cover.get("tilt_change_time")

        if value and not isinstance(value, float) and not isinstance(value, int):
            raise ImproperlyConfigured(COVER_TIME % (index + 1, "tilt_change_time"))

    @staticmethod
    def _clean_covers_circuit_up(cover, index):
        if "circuit_up" not in cover:
            raise ImproperlyConfigured(COVER_KEY_MISSING % (index + 1, "circuit_up"))

    @staticmethod
    def _clean_covers_circuit_down(cover, index):
        if "circuit_down" not in cover:
            raise ImproperlyConfigured(COVER_KEY_MISSING % (index + 1, "circuit_down"))

    def _clean_duplicate_covers_circuits(self):
        circuits: list = self.get_cover_circuits()

        for circuit in circuits:
            if circuits.count(circuit) > 1:
                raise ImproperlyConfigured(
                    "[CONFIG] [COVER] Duplicate circuits found in `covers`! "
                    "Driving both signals up and down at the same time can damage the motor."
                )


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
        try:
            for f in Path(f"{HARDWARE}/extension").iterdir():
                if str(f).endswith(".yaml"):
                    with open(f) as yf:
                        self.data["definitions"].append(yaml.load(yf, Loader=yaml.FullLoader))
                        logger.debug("[CONFIG] YAML Definition loaded: %s", f)
        except FileNotFoundError as error:
            print(colored(error, "red"))

    def _read_neuron_definition(self) -> None:
        definition_file: Path = Path(f"{HARDWARE}/neuron/{self._model}.yaml")

        if definition_file.is_file():
            with open(definition_file) as yf:
                self.data["neuron_definition"] = yaml.load(yf, Loader=yaml.FullLoader)
                logger.debug("[CONFIG] YAML Definition loaded: %s", definition_file)
        else:
            raise HardwareException(
                f"[CONFIG] No valid YAML definition for active Neuron device! "
                f"Device name is {self._model}."
            )


config = Config()
logger = config.logger
