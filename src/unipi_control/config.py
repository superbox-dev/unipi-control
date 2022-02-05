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
    "[medium_turquoise][COVER][/] [dark_orange][%s][/] Device is locked! Other position change is currently running."
)
COVER_KEY_MISSING: str = "[medium_turquoise][CONFIG][/] [light_coral][COVER %s][/] Required key '%s' is missing!"
COVER_TIME: str = "[medium_turquoise][CONFIG][/] [light_coral][COVER %s][/] Key '%s' is not a float or integer!"
LOG_MQTT_PUBLISH: str = r"[medium_turquoise][MQTT][/] [light_coral]\[%s][/] Publishing message: [bright_cyan]%s[/]"
LOG_MQTT_SUBSCRIBE: str = r"[medium_turquoise][MQTT][/] [light_coral]\[%s][/] Subscribe message: [bright_cyan]%s[/]"
LOG_MQTT_SUBSCRIBE_TOPIC: str = "[medium_turquoise][MQTT][/] Subscribe topic [bright_cyan]%s[/]"

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        RichHandler(
            console=Console(soft_wrap=True, tab_size=4),
            show_time=False,
            omit_repeated_times=False,
        ),
    ],
)

logger = logging.getLogger("asyncio")


@dataclass
class ConfigBase:
    def clean(self):
        errors: List[str] = []

        for key in self.__dict__.keys():
            clean_method = getattr(self, f"clean_{key}", None)

            if clean_method and callable(clean_method):
                error: Optional[Union[str, List[str]]] = clean_method()

                if error is not None:
                    if isinstance(error, list):
                        errors += error
                    else:
                        errors.append(error)

        if errors:
            [logger.error(e, extra={"markup": True}) for e in errors]
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

    def clean_device_name(self) -> Optional[str]:
        result = re.search(r"^[\w\d_-]*$", self.device_name)

        if result is None:
            return (
                "[medium_turquoise][CONFIG][/] Invalid value in 'device_name'. "
                "The following characters are prohibited: [bright_cyan]A-Z a-z 0-9 -_[/]"
            )

        return None

    def clean_covers(self) -> Optional[List[str]]:
        errors: List[Optional[str]] = []

        for index, cover in enumerate(self.covers):
            errors.append(self._clean_covers_friendly_name(cover, index))
            errors.append(self._clean_covers_cover_type(cover, index))
            errors.append(self._clean_covers_topic_name(cover, index))
            errors.append(self._clean_covers_full_open_time(cover, index))
            errors.append(self._clean_covers_full_close_time(cover, index))
            errors.append(self._clean_covers_tilt_change_time(cover, index))
            errors.append(self._clean_covers_circuit_up(cover, index))
            errors.append(self._clean_covers_circuit_down(cover, index))
            errors.append(self._clean_duplicate_covers_circuits())

        return [error for error in errors if error is not None]

    @staticmethod
    def _clean_covers_friendly_name(cover: Dict[str, str], index: int) -> Optional[str]:
        if "friendly_name" not in cover:
            return COVER_KEY_MISSING % (index + 1, "friendly_name")

        return None

    @staticmethod
    def _clean_covers_cover_type(cover: Dict[str, str], index: int) -> Optional[str]:
        if "cover_type" not in cover:
            return COVER_KEY_MISSING % (index + 1, "cover_type")

        if cover.get("cover_type") not in COVER_TYPES:
            return (
                f"[medium_turquoise][CONFIG][/] [light_coral][COVER {index + 1}][/] Invalid value in 'cover_type'. "
                f"The following values are allowed: [bright_cyan]{' '.join(COVER_TYPES)}[/]."
            )

        return None

    @staticmethod
    def _clean_covers_topic_name(cover: Dict[str, str], index: int) -> Optional[str]:
        if "topic_name" not in cover:
            return COVER_KEY_MISSING % (index + 1, "topic_name")

        result: Optional[Match[str]] = re.search(r"^[a-z\d_-]*$", cover.get("topic_name", ""))

        if result is None:
            return (
                f"[medium_turquoise][CONFIG][/] [light_coral][COVER {index + 1}][/] Invalid value in 'topic_name'. "
                f"The following characters are prohibited: [bright_cyan]a-z 0-9 -_[/]"
            )

        return None

    @staticmethod
    def _clean_covers_full_open_time(cover: Dict[str, Union[float, int]], index: int) -> Optional[str]:
        if "full_open_time" not in cover:
            return COVER_KEY_MISSING % (index + 1, "full_open_time")

        value = cover.get("full_open_time")

        if value and not isinstance(value, float) and not isinstance(value, int):
            return COVER_TIME % (index + 1, "full_open_time")

        return None

    @staticmethod
    def _clean_covers_full_close_time(cover: Dict[str, Union[float, int]], index: int) -> Optional[str]:
        if "full_close_time" not in cover:
            return COVER_KEY_MISSING % (index + 1, "full_close_time")

        value = cover.get("full_close_time")

        if value and not isinstance(value, float) and not isinstance(value, int):
            return COVER_TIME % (index + 1, "full_close_time")

        return None

    @staticmethod
    def _clean_covers_tilt_change_time(cover: Dict[str, Union[float, int]], index: int) -> Optional[str]:
        value = cover.get("tilt_change_time")

        if value and not isinstance(value, float) and not isinstance(value, int):
            return COVER_TIME % (index + 1, "tilt_change_time")

        return None

    @staticmethod
    def _clean_covers_circuit_up(cover: Dict[str, str], index: int) -> Optional[str]:
        if "circuit_up" not in cover:
            return COVER_KEY_MISSING % (index + 1, "circuit_up")

        return None

    @staticmethod
    def _clean_covers_circuit_down(cover: Dict[str, str], index: int) -> Optional[str]:
        if "circuit_down" not in cover:
            return COVER_KEY_MISSING % (index + 1, "circuit_down")

        return None

    def _clean_duplicate_covers_circuits(self) -> Optional[str]:
        circuits: List[str] = self.get_cover_circuits()

        for circuit in circuits:
            if circuits.count(circuit) > 1:
                return (
                    "[medium_turquoise][CONFIG][/] [light_coral][COVER][/] Duplicate circuits found in 'covers'. "
                    "Driving both signals up and down at the same time can damage the motor!"
                )

        return None


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
            logger.info("[medium_turquoise][CONFIG][/] %s", str(error), extra={"markup": True})

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
