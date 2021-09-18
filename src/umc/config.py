import struct
from pathlib import Path

import yaml
from api.settings import logger
from helpers import MappingMixin

HW_DEFINITIONS = "/etc/umc/hw_definitions"


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
                    "version": f"{ee_bytes[99]}.{ee_bytes[98]}",
                    "model": f"{ee_bytes[106:110].decode()}",
                    "serial": struct.unpack("i", ee_bytes[100:104])[0],
                })


class HardwareDefinition(MappingMixin):
    def __init__(self):
        super().__init__()

        self.mapping: dict = {
            "definitions": [],
            "neuron_definition": None,
        }

        self._hw = Hardware()

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
        definition_file: str = Path(f"""{HW_DEFINITIONS}/BuiltIn/{self._hw["model"]}.yaml""")

        if definition_file.is_file():
            with open(definition_file) as yf:
                self.mapping["neuron_definition"] = yaml.load(yf, Loader=yaml.FullLoader)
                logger.info(f"""YAML Definition loaded: {definition_file}""")
        else:
            logger.error(f"""No valid YAML definition for active Neuron device! Device name {self._hw["model"]}""")
