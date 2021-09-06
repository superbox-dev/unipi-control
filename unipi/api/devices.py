#!/usr/bin/env python3

import asyncio
import os
import re
from collections import namedtuple
from functools import partial
from typing import Optional

from api.settings import logger


class DeviceMixin:
    """Device class mixin for observe the SysFS devices."""

    def __init__(self, device_path: str):
        """Initialize the device class.

        Args:
            device_path (str): SysFS path to the circuit file.
        """
        self.device = namedtuple("Device", "dev dev_type circuit value changed")
        self.device_path: str = device_path
        self._value: bool = False
        self._file_r = None

    @property
    def dev(self) -> str:
        """Return device name."""
        return self.DEVICE

    @property
    def dev_name(self) -> str:
        """Return human readable device name."""
        circuit = self.circuit[3:].replace("_", ".")
        return f"{self.DEVICE_NAME} {circuit}"

    @property
    def dev_type(self) -> str:
        """Return device name."""
        return self.DEVICE_TYPE

    @property
    def circuit(self) -> Optional[str]:
        """Get the circuit name."""
        match = self.FOLDER_REGEX.search(self.device_path)

        if match:
            return match.group(0)

    @property
    def value_path(self) -> str:
        """Get the circuit value file path."""
        return os.path.join(self.device_path, self.VALUE_FILENAME)

    def _read_value_file(self) -> str:
        """Read circuit state from value file and return."""
        if self._file_r is None:
            self._file_r = open(self.value_path, "r")

            logger.info(f"Observe circuit `{self.circuit}`")

        self._file_r.seek(0)
        return self._file_r.read().rstrip()

    async def get(self) -> None:
        """Get circuit state."""
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, self._read_value_file)
        value: bool = result == "1"
        changed: bool = value != self._value

        if changed:
            self._value = value

        return self.device(
            self.dev,
            self.dev_type,
            self.circuit,
            result,
            changed,
        )


class DeviceSetMixin(DeviceMixin):
    def _write_value_file(self, value: str) -> None:
        """Write circuit state to value file.

        Args:
            value (str): Value can be 0 (False) or 1 (True).
        """
        with open(self.value_path, "w") as f:
            f.write(value)

    async def set(self, payload: str) -> None:
        """Set cricuit state.

        Args:
            payload (str): "0" or "1"
        """
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, partial(self._write_value_file, payload))


class DeviceRelay(DeviceSetMixin):
    """Observe relay output and publish with Mqtt."""

    DEVICE = "relay"
    DEVICE_NAME = "Relay"
    DEVICE_TYPE = "physical"
    FOLDER_REGEX = re.compile(r"ro_\d_\d{2}")
    VALUE_FILENAME = "ro_value"


class DeviceDigitalInput(DeviceMixin):
    """Observe digital input and publish with Mqtt."""

    DEVICE = "input"
    DEVICE_NAME ="Digital Input"
    DEVICE_TYPE = "digital"
    FOLDER_REGEX = re.compile(r"di_\d_\d{2}")
    VALUE_FILENAME = "di_value"


class DeviceDigitalOutput(DeviceSetMixin):
    """Observe digital output and publish with Mqtt."""

    DEVICE = "relay"
    DEVICE_NAME ="Digital Output"
    DEVICE_TYPE = "digital"
    FOLDER_REGEX = re.compile(r"do_\d_\d{2}")
    VALUE_FILENAME = "do_value"
