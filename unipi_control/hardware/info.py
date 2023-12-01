"""Collection of hardware classes."""

import struct
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path


@dataclass
class HardwareInfo:
    sys_bus_dir: Path
    name: str = field(default="unknown")
    model: str = field(default="unknown", init=False)
    version: str = field(default="unknown", init=False)
    serial: str = field(default="unknown", init=False)

    def __post_init__(self) -> None:  # pragma: no cover
        # Can't unit testing the hardware info.
        # This code only works on the real hardware!
        unipi_1_file: Path = self.sys_bus_dir / "1-0050/eeprom"
        unipi_patron_file: Path = self.sys_bus_dir / "2-0057/eeprom"
        unipi_neuron_1_file: Path = self.sys_bus_dir / "1-0057/eeprom"
        unipi_neuron_0_file: Path = self.sys_bus_dir / "0-0057/eeprom"

        if unipi_1_file.is_file():
            with unipi_1_file.open("rb") as _file:
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
        elif unipi_patron_file.is_file():
            with unipi_patron_file.open("rb") as _file:
                ee_bytes = _file.read(128)

                self.name = "Unipi Patron"
                self.model = f"{ee_bytes[106:110].decode()}"
                self.version = f"{ee_bytes[99]}.{ee_bytes[98]}"
                self.serial = struct.unpack("i", ee_bytes[100:104])[0]
        elif unipi_neuron_1_file.is_file():
            with unipi_neuron_1_file.open("rb") as _file:
                ee_bytes = _file.read(128)

                self.name = "Unipi Neuron"
                self.model = f"{ee_bytes[106:110].decode()}"
                self.version = f"{ee_bytes[99]}.{ee_bytes[98]}"
                self.serial = struct.unpack("i", ee_bytes[100:104])[0]
        elif unipi_neuron_0_file.is_file():
            with unipi_neuron_0_file.open("rb") as _file:
                ee_bytes = _file.read(128)

                self.name = "Unipi Neuron"
                self.model = f"{ee_bytes[106:110].decode()}"
                self.version = f"{ee_bytes[99]}.{ee_bytes[98]}"
                self.serial = struct.unpack("i", ee_bytes[100:104])[0]
