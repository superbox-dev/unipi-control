"""Read model informations from /sys path."""

import struct
from pathlib import Path


def main() -> None:
    """Tiny script to detect the Unipi Neuron model."""
    unipi_1: Path = Path("/sys/bus/i2c/devices/1-0050/eeprom")
    unipi_patron: Path = Path("/sys/bus/i2c/devices/2-0057/eeprom")
    unipi_neuron_1: Path = Path("/sys/bus/i2c/devices/1-0057/eeprom")
    unipi_neuron_0: Path = Path("/sys/bus/i2c/devices/0-0057/eeprom")

    name: str = "unknown"
    model: str = "unknown"
    version: str = "unknown"
    serial: str = "unknown"

    if unipi_1.is_file():
        with unipi_1.open("rb") as _file:
            ee_bytes = _file.read(256)

            if ee_bytes[226] == 1 and ee_bytes[227] == 1:
                name = "Unipi"
                version = "1.1"
            elif ee_bytes[226] == 11 and ee_bytes[227] == 1:
                name = "Unipi Lite"
                version = "1.1"
            else:
                name = "Unipi"
                version = "1.0"

            serial = struct.unpack("i", ee_bytes[228:232])[0]
    elif unipi_neuron_1.is_file():
        with unipi_neuron_1.open("rb") as _file:
            ee_bytes = _file.read(128)

            name = "Unipi Neuron"
            model = f"{ee_bytes[106:110].decode()}"
            version = f"{ee_bytes[99]}.{ee_bytes[98]}"
            serial = struct.unpack("i", ee_bytes[100:104])[0]
    elif unipi_patron.is_file():
        with unipi_patron.open("rb") as _file:
            ee_bytes = _file.read(128)

            name = "Unipi Patron"
            model = f"{ee_bytes[106:110].decode()}"
            version = f"{ee_bytes[99]}.{ee_bytes[98]}"
            serial = struct.unpack("i", ee_bytes[100:104])[0]
    elif unipi_neuron_0.is_file():
        with unipi_neuron_0.open("rb") as _file:
            ee_bytes = _file.read(128)

            name = "Unipi Neuron"
            model = f"{ee_bytes[106:110].decode()}"
            version = f"{ee_bytes[99]}.{ee_bytes[98]}"
            serial = struct.unpack("i", ee_bytes[100:104])[0]

    print(f"Name: {name}")
    print(f"Model: {model}")
    print(f"Version: {version}")
    print(f"Serial: {serial}")
