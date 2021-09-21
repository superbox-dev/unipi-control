import logging
import os
import struct
from pathlib import Path

import yaml
from deepmerge import always_merger
from mapping import MappingMixin
from systemd import journal

HW_DEFINITIONS = "/etc/umc/hw_definitions"


class ConfigMixin(MappingMixin):
    @staticmethod
    def read_yaml(defaults: dict, path: str) -> dict:
        result: dict = defaults

        if os.path.exists(path):
            with open(path) as f:
                config: dict = yaml.load(f, Loader=yaml.FullLoader)
                result = always_merger.merge(result, config)

        return result


class ClientConfig(ConfigMixin):
    defaults: dict = {
        "device_name": "unipi",
        "mqtt": {
            "host": "localhost",
            "port": 1883,
            "connection": {
                "keepalive": 15,
                "retry_limit": 30,
                "reconnect_interval": 10,
            },
        },
        "logging": {
            "logger": "systemd",
            "level": "info",
        },
    }

    def __init__(self):
        self.mapping: dict = self.read_yaml(self.defaults, "/etc/umc/client.yaml")


class HomeAssistantConfig(ConfigMixin):
    defaults: dict = {
        "discovery_prefix": "homeassistant",
        "device": {
            "manufacturer": "Unipi technology",
        },
    }

    def __init__(self):
        self.mapping: dict = self.read_yaml(self.defaults, "/etc/umc/homeassistant.yaml")


class Hardware(MappingMixin):
    def __init__(self):
        super().__init__()
        self._read_eprom()

    def _read_eprom(self) -> None:
        neuron: Path = Path("/sys/bus/i2c/devices/1-0057/eeprom")

        # TODO: Add other devices
        # https://github.com/UniPiTechnology/evok/blob/master/evok/config.py

        if neuron.is_file():
            with open(neuron, "rb") as f:
                ee_bytes = f.read(128)

                self.mapping.update({
                    "name": "Unipi Neuron",
                    "model": f"{ee_bytes[106:110].decode()}",
                    "version": f"{ee_bytes[99]}.{ee_bytes[98]}",
                    "serial": struct.unpack("i", ee_bytes[100:104])[0],
                })


class HardwareDefinition(MappingMixin):
    def __init__(self):
        super().__init__()

        self.mapping: dict = {
            "neuron": Hardware(),
            "definitions": [],
            "neuron_definition": None,
        }

        self._read_definitions()
        self._read_build_in_definition()

    def _read_definitions(self) -> None:
        for f in Path(HW_DEFINITIONS).iterdir():
            if str(f).endswith(".yaml"):
                with open(f) as yf:
                    self.mapping["definitions"].append(
                        yaml.load(yf, Loader=yaml.FullLoader)
                    )

                    logger.info(f"""YAML Definition loaded: {f}""")

    def _read_build_in_definition(self) -> None:
        definition_file: str = Path(f"""{HW_DEFINITIONS}/BuiltIn/{self.mapping["neuron"]["model"]}.yaml""")

        if definition_file.is_file():
            with open(definition_file) as yf:
                self.mapping["neuron_definition"] = yaml.load(yf, Loader=yaml.FullLoader)
                logger.info(f"""YAML Definition loaded: {definition_file}""")
        else:
            logger.error(f"""No valid YAML definition for active Neuron device! Device name {self.mapping["neuron"]["model"]}""")


config = ClientConfig()
ha_config = HomeAssistantConfig()

logger_type: str = config["logging"]["logger"]
logger = logging.getLogger(__name__)

LEVEL: dict = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}

if logger_type == "systemd":
    logger.addHandler(journal.JournalHandler())
    logger.setLevel(level=LEVEL[config["logging"]["level"]])
elif logger_type == "file":
    logging.basicConfig(
        level=LEVEL[config["logging"]["level"]],
        filename="/var/log/umc.log",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
