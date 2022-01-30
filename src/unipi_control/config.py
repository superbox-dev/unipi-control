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
from typing import Union

import yaml
from helpers import DataStorage
from rich.console import Console
from rich.logging import RichHandler

console = Console()

HARDWARE: str = "/etc/unipi/hardware"
COVER_TYPES: list = ["blind", "roller_shutter", "garage_door"]
COVER_DEVICE_LOCKED: str = (
    "[medium_turquoise][COVER][/] [%s] Device is locked! Other position change is currently running."
)
# TODO: Change ImproperlyConfigured to rich output
# COVER_KEY_MISSING: str = """[medium_turquoise][CONFIG][/] [COVER %s] Required key "%s" is missing!"""
COVER_KEY_MISSING: str = """[CONFIG] [COVER %s] Required key "%s" is missing!"""
# COVER_TIME: str = """[medium_turquoise][CONFIG][/] [COVER %s] Key "%s" is not a float or integer!"""
COVER_TIME: str = """[CONFIG] [COVER %s] Key "%s" is not a float or integer!"""
LOG_MQTT_PUBLISH: str = "[medium_turquoise][MQTT][/] [%s] Publishing message: %s"
LOG_MQTT_SUBSCRIBE: str = "[medium_turquoise][MQTT][/] [%s] Subscribe message: %s"
LOG_MQTT_SUBSCRIBE_TOPIC: str = "[medium_turquoise][MQTT][/] Subscribe topic %s"


class ImproperlyConfigured(Exception):
    pass


@dataclass
class ConfigBase:
    def clean(self):
        errors: List[str] = []

        for key in self.__dict__.keys():
            clean_method = getattr(self, f"clean_{key}", None)

            if clean_method and callable(clean_method):
                try:
                    clean_method()
                except ImproperlyConfigured as error:
                    errors.append(str(error))

        if errors:
            [console.print(e, style="red") for e in errors]
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
class Config(ConfigBase):
    device_name: str = field(default=socket.gethostname())
    mqtt: MqttConfig = field(default=MqttConfig())
    homeassistant: HomeAssistantConfig = field(default=HomeAssistantConfig())
    features: dict = field(init=False, default_factory=dict)
    covers: list = field(init=False, default_factory=list)
    logging: LoggingConfig = field(default=LoggingConfig())

    def __post_init__(self):
        config_path: Path = Path("/etc/unipi/control.yaml")
        _config: dict = self.get_config(config_path)
        self.update(_config)
        self.clean()

    @staticmethod
    def get_config(config_path: Path) -> dict:
        _config: dict = {}

        if config_path.exists():
            _config = yaml.load(config_path.read_text(), Loader=yaml.FullLoader)

        return _config

    def logger(self):
        level: Dict[str, int] = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
        }

        logging.basicConfig(
            level=level[self.logging.level],
            format="%(message)s",
            handlers=[RichHandler(show_time=False)],
        )

        return logging.getLogger("asyncio")

    def get_cover_circuits(self) -> List[str]:
        """Get all circuits that are defined in the cover config.

        Returns
        -------
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
        result = re.search(r"^[\w\d_-]*$", self.device_name)

        if result is None:
            raise ImproperlyConfigured(
                '[CONFIG] Invalid value in "device_name". ' "The following characters are prohibited: A-Z a-z 0-9 -_"
            )

    def clean_covers(self):
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
    def _clean_covers_friendly_name(cover: Dict[str, str], index: int):
        if "friendly_name" not in cover:
            raise ImproperlyConfigured(COVER_KEY_MISSING % (index + 1, "friendly_name"))

    @staticmethod
    def _clean_covers_cover_type(cover: Dict[str, str], index: int):
        if "cover_type" not in cover:
            raise ImproperlyConfigured(COVER_KEY_MISSING % (index + 1, "cover_type"))

        if cover.get("cover_type") not in COVER_TYPES:
            raise ImproperlyConfigured(
                f"""[CONFIG] [COVER {index + 1}] Invalid value in \"cover_type\".
                The following values are allowed: {" ".join(COVER_TYPES)}."""
            )

    @staticmethod
    def _clean_covers_topic_name(cover: Dict[str, str], index: int):
        if "topic_name" not in cover:
            raise ImproperlyConfigured(COVER_KEY_MISSING % (index + 1, "topic_name"))

        result: Optional[Match[str]] = re.search(r"^[a-z\d_-]*$", cover.get("topic_name", ""))

        if result is None:
            raise ImproperlyConfigured(
                f'[CONFIG] [COVER {index + 1}] Invalid value in "topic_name".'
                f" The following characters are prohibited: a-z 0-9 -_"
            )

    @staticmethod
    def _clean_covers_full_open_time(cover: Dict[str, Union[float, int]], index: int):
        if "full_open_time" not in cover:
            raise ImproperlyConfigured(COVER_KEY_MISSING % (index + 1, "full_open_time"))

        value = cover.get("full_open_time")

        if value and not isinstance(value, float) and not isinstance(value, int):
            raise ImproperlyConfigured(COVER_TIME % (index + 1, "full_open_time"))

    @staticmethod
    def _clean_covers_full_close_time(cover: Dict[str, Union[float, int]], index: int):
        if "full_close_time" not in cover:
            raise ImproperlyConfigured(COVER_KEY_MISSING % (index + 1, "full_close_time"))

        value = cover.get("full_close_time")

        if value and not isinstance(value, float) and not isinstance(value, int):
            raise ImproperlyConfigured(COVER_TIME % (index + 1, "full_close_time"))

    @staticmethod
    def _clean_covers_tilt_change_time(cover: Dict[str, Union[float, int]], index: int):
        value = cover.get("tilt_change_time")

        if value and not isinstance(value, float) and not isinstance(value, int):
            raise ImproperlyConfigured(COVER_TIME % (index + 1, "tilt_change_time"))

    @staticmethod
    def _clean_covers_circuit_up(cover: Dict[str, str], index: int):
        if "circuit_up" not in cover:
            raise ImproperlyConfigured(COVER_KEY_MISSING % (index + 1, "circuit_up"))

    @staticmethod
    def _clean_covers_circuit_down(cover: Dict[str, str], index: int):
        if "circuit_down" not in cover:
            raise ImproperlyConfigured(COVER_KEY_MISSING % (index + 1, "circuit_down"))

    def _clean_duplicate_covers_circuits(self):
        circuits: List[str] = self.get_cover_circuits()

        for circuit in circuits:
            if circuits.count(circuit) > 1:
                raise ImproperlyConfigured(
                    '[CONFIG] [COVER] Duplicate circuits found in "covers"! '
                    "Driving both signals up and down at the same time can damage the motor."
                )


@dataclass
class HardwareInfo:
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
    def __init__(self):
        super().__init__()

        self.data: dict = {
            "neuron": asdict(HardwareInfo()),
            "definitions": [],
            "neuron_definition": None,
        }

        self._model: str = self.data["neuron"]["model"]

        if self._model is None:
            logger.error("[medium_turquoise][CONFIG][/] Hardware is not supported!", extra={"markup": True})
            sys.exit(1)

        self._read_definitions()
        self._read_neuron_definition()

    def _read_definitions(self):
        try:
            for f in Path(f"{HARDWARE}/extension").iterdir():
                if f.suffix == ".yaml":
                    self.data["definitions"].append(yaml.load(f.read_text(), Loader=yaml.FullLoader))
                    logger.debug("[medium_turquoise][CONFIG][/] YAML Definition loaded: %s", f, extra={"markup": True})
        except FileNotFoundError as error:
            console.print(str(error), style="red")

    def _read_neuron_definition(self):
        definition_file: Path = Path(f"{HARDWARE}/neuron/{self._model}.yaml")

        if definition_file.is_file():
            self.data["neuron_definition"] = yaml.load(definition_file.read_text(), Loader=yaml.FullLoader)
            logger.debug(
                "[medium_turquoise][CONFIG][/] YAML Definition loaded: %s", definition_file, extra={"markup": True}
            )
        else:
            logger.error(
                "[medium_turquoise][CONFIG][/] No valid YAML definition for active Neuron device! Device name is %s",
                self._model,
                extra={"markup": True},
            )
            sys.exit(1)


config = Config()
logger = config.logger()
