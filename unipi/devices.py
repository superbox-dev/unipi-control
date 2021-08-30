#!/usr/bin/env python3

import os
import re
from collections import namedtuple

import aiofiles

from settings import logger


class DeviceMixin:
    """Device class mixin for observe the SysFS devices."""

    def __init__(self, device_path: str):
        """Initialize the device class.

        Args:
            device_path (str): SysFS path to the circuit file
        """
        self.device = namedtuple("Device", "name circuit value changed")
        self.device_path: str = device_path
        self._value: bool = False
        self._file_handle = None

    @property
    def name(self) -> str:
        return self.DEVICE

    @property
    def circuit(self) -> str:
        """Get the circuit name."""
        match = self.FOLDER_REGEX.search(self.device_path)
        start, end = match.span()
        return self.device_path[start:end]

    @property
    def value_path(self) -> str:
        """Get the circuit value file path."""
        return os.path.join(self.device_path, self.VALUE_FILENAME)

    async def _read_value_file(self) -> str:
        """Read circuit value file and return file content."""
        if self._file_handle is None:
            self._file_handle = await aiofiles.open(self.value_path, "r")
            logger.info(f"Observe circuit `{self.circuit}`")

        await self._file_handle.seek(0)
        return await self._file_handle.read()

    async def get(self) -> None:
        """Get circuit state."""
        value: bool = await self._read_value_file() == "1\n"
        changed: bool = value != self._value

        if changed:
            self._value = value

        return self.device(self.name, self.circuit, value, changed)


class DeviceRelay(DeviceMixin):
    """Observe relay output and publish with Mqtt."""

    DEVICE = "relay"
    FOLDER_REGEX = re.compile(r"ro_\d_\d{2}")
    VALUE_FILENAME = "ro_value"

    def set(self, value: str) -> None:
        value: str = "1" if value.lower() in ["true", "t", "1", "on"] else "0"

        with open(self.value_path, "w") as f:
            f.write(value)


class DeviceDigitalInput(DeviceMixin):
    """Observe digital input and publish with Mqtt."""

    DEVICE = "input"
    FOLDER_REGEX = re.compile(r"di_\d_\d{2}")
    VALUE_FILENAME = "di_value"
