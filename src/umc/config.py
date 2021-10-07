import logging
import os
import re
import struct
import sys
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from dataclasses import is_dataclass
from pathlib import Path

import yaml
from helpers import MappingMixin
from systemd import journal
from termcolor import colored

HW_CONFIGS = "/etc/umc/hardware"


@dataclass
class ConfigBase:
    def clean(self):
        for key in self.__dict__.keys():
            clean_method = getattr(self, f"clean_{key}", None)
            if clean_method and callable(clean_method):
                clean_method()

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
    discovery_prefix: str = field(default="homeassistant")
    device: dataclass = field(default=DeviceInfo())


@dataclass
class LoggingConfig(ConfigBase):
    logger: str = field(default="systemd")
    level: str = field(default="level")


class DevicesPluginsConfig(ConfigBase):
    enabled: list = field(init=False, default_factory=list)
    mapping: dict = field(init=False, default_factory=dict)


class CoversPluginsConfig(ConfigBase):
    blinds: list = field(init=False, default_factory=list)


class PluginsConfig(ConfigBase):
    devices: dataclass = field(default=DevicesPluginsConfig())
    covers: dataclass = field(default=CoversPluginsConfig())


@dataclass
class Config(ConfigBase):
    device_name: str = field(default="Unipi")
    mqtt: dataclass = field(default=MqttConfig())
    homeassistant: dataclass = field(default=HomeAssistantConfig())
    plugins: dataclass = field(default=PluginsConfig())
    logging: dataclass = field(default=LoggingConfig())

    def __post_init__(self):
        config: dict = self.get_config("/etc/umc/client.yaml")
        self.update(config)
        self.clean()

    @staticmethod
    def get_config(path: str) -> dict:
        if os.path.exists(path):
            with open(path) as f:
                config: dict = yaml.load(f, Loader=yaml.FullLoader)

        return config

    @property
    def logger(self):
        logger_type: str = self.logging.logger
        logger = logging.getLogger(__name__)

        level: dict = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
        }

        logger_level = level[self.logging.level]

        if logger_type == "systemd":
            logger.addHandler(journal.JournalHandler())
            logger.setLevel(level=logger_level)
        elif logger_type == "file":
            logging.basicConfig(
                level=logger_level,
                filename="/var/log/umc.log",
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )

        return logger

    def clean_device_name(self):
        result = re.search(r"^[\w\d_-]*$", self.device_name)

        if result is None:
            sys.exit(colored("[CONFIG] Invalid value in \"device_name\". The following characters are prohibited: A-Z a-z 0-9 -_", "red"))


class HardwareException(Exception):
    pass


@dataclass
class Hardware:
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


class HardwareDefinition(MappingMixin):
    def __init__(self):
        super().__init__()

        self.hardware = Hardware()

        self.mapping: dict = {
            "neuron": asdict(Hardware()),
            "definitions": [],
            "neuron_definition": None,
        }

        self.model: str = self.mapping["neuron"]["model"]

        if self.model is None:
            raise HardwareException("[CONFIG] Hardware is not supported!")

        self._read_definitions()
        self._read_neuron_definition()

    def _read_definitions(self) -> None:
        for f in Path(f"{HW_CONFIGS}/extension").iterdir():
            if str(f).endswith(".yaml"):
                with open(f) as yf:
                    self.mapping["definitions"].append(
                        yaml.load(yf, Loader=yaml.FullLoader)
                    )

                    logger.info(f"""[CONFIG] YAML Definition loaded: {f}""")

    def _read_neuron_definition(self) -> None:
        definition_file: str = Path(f"""{HW_CONFIGS}/neuron/{self.model}.yaml""")

        if definition_file.is_file():
            with open(definition_file) as yf:
                self.mapping["neuron_definition"] = yaml.load(yf, Loader=yaml.FullLoader)
                logger.info(f"""[CONFIG] YAML Definition loaded: {definition_file}""")
        else:
            raise HardwareException(f"[CONFIG] No valid YAML definition for active Neuron device! Device name is {self.model}.")


config = Config()
logger = config.logger
