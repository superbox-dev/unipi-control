"""Modbus helper to connect and scan registers."""

import asyncio
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ModbusResponse

from unipi_control.config import HardwareMap
from unipi_control.config import HardwareType
from unipi_control.config import LogPrefix
from unipi_control.config import UNIPI_LOGGER
from unipi_control.helpers.exception import UnexpectedError
from unipi_control.helpers.typing import ModbusClient
from unipi_control.helpers.typing import ModbusReadData
from unipi_control.helpers.typing import ModbusWriteData
from unipi_control.config import Config


class ModbusHelper:
    def __init__(self, config: Config, client: ModbusClient, hardware: HardwareMap) -> None:
        self.config: Config = config
        self.client: ModbusClient = client
        self.hardware: HardwareMap = hardware

        self.data: Dict[int, Dict[int, int]] = {}

    def connect_tcp(self) -> None:
        """Connect to Modbus TCP."""
        self.client.tcp.connect()  # type: ignore[no-untyped-call]

        if self.client.tcp.connected:
            UNIPI_LOGGER.debug(
                "%s [TCP] Client connected to %s:%s",
                LogPrefix.MODBUS,
                "localhost",
                502,
            )
        else:
            msg: str = (
                f"{LogPrefix.MODBUS} [TCP] Client can't connect to "
                f"{self.config.modbus_tcp.host}:{self.config.modbus_tcp.port}"
            )
            raise UnexpectedError(msg)

    def close_tcp(self) -> None:
        """Close connection to Modbus TCP."""
        self.client.tcp.close()  # type: ignore[no-untyped-call]

        UNIPI_LOGGER.debug(
            "%s [TCP] Client disconnected to %s:%s",
            LogPrefix.MODBUS,
            self.config.modbus_tcp.host,
            self.config.modbus_tcp.port,
        )

    async def scan_tcp(self) -> None:
        """Scan Modbus TCP and add response to the cache."""
        while True:
            if not self.client.tcp.connected:
                self.client.tcp.connect()  # type: ignore[no-untyped-call]

            for definition in self.hardware.get_definition_by_hardware_types([HardwareType.PLC]):
                if not self.data.get(definition.unit):
                    self.data[definition.unit] = {}

                for modbus_register_block in definition.modbus_register_blocks:
                    data: ModbusReadData = {
                        "address": modbus_register_block["start_reg"],
                        "count": modbus_register_block["count"],
                        "slave": modbus_register_block.get("unit", definition.unit),
                    }

                    response: Optional[ModbusResponse] = check_modbus_call(self.client.tcp.read_input_registers, data)

                    if response:
                        register: List[int] = response.registers
                        for index in range(data["count"]):
                            self.data[definition.unit][data["address"] + index] = register[index]

            await asyncio.sleep(1 / 50)

    def connect_serial(self) -> None:
        """Connect to Modbus RTU."""
        self.client.serial.connect()  # type: ignore[no-untyped-call]

        if self.client.serial.connected:
            UNIPI_LOGGER.debug(
                "%s [RTU] Client connected to %s",
                LogPrefix.MODBUS,
                self.config.modbus_serial.port,
            )
        else:
            msg: str = f"{LogPrefix.MODBUS} [RTU] Client can't connect to {self.config.modbus_serial.port}"
            raise UnexpectedError(msg)

    def close_serial(self) -> None:
        """Close connection to Modbus RTU."""
        self.client.serial.close()  # type: ignore[no-untyped-call]

        UNIPI_LOGGER.debug("%s [RTU] Client disconnected to %s", LogPrefix.MODBUS, self.config.modbus_serial.port)

    async def scan_serial(self) -> None:
        """Scan Modbus RTU and add response to the cache."""
        while True:
            if not self.client.serial.connected:
                self.client.serial.connect()  # type: ignore[no-untyped-call]

            for definition in self.hardware.get_definition_by_hardware_types([HardwareType.EXTENSION]):
                if not self.data.get(definition.unit):
                    self.data[definition.unit] = {}

                for modbus_register_block in definition.modbus_register_blocks:
                    data: ModbusReadData = {
                        "address": modbus_register_block["start_reg"],
                        "count": modbus_register_block["count"],
                        "slave": modbus_register_block.get("unit", definition.unit),
                    }

                    response: Optional[ModbusResponse] = check_modbus_call(
                        self.client.serial.read_input_registers, data
                    )

                    if response:
                        register: List[int] = response.registers
                        for index in range(data["count"]):
                            self.data[definition.unit][data["address"] + index] = register[index]

                    await asyncio.sleep(1 / 50)

    def get_register(self, address: int, index: int, unit: int) -> List[Optional[int]]:
        """Get the responses from the cached modbus register blocks.

        Parameters
        ----------
        address: int
            The starting address to read from.
        index: int
            The number of registers to read.
        unit: int
            The unit this request is targeting.

        Returns
        -------
        list
            A list of cached modbus register blocks.
        """
        ret: List[Optional[int]] = []

        for _address in range(address, address + index):
            ret += [self.data.get(unit, {}).get(_address)]

        return ret


def check_modbus_call(
    callback: Callable[..., Any], data: Union[ModbusReadData, ModbusWriteData]
) -> Optional[ModbusResponse]:
    """Check modbus read/write call has errors and log the errors.

    Parameters
    ----------
    callback: Callable
        modbus callback function e.g. read_input_registers()
    data: ModbusReadData
        Arguments pass to the callback function

    Returns
    -------
    ModbusResponse: optional
        Return modbus response if no errors found else None.

    Raises
    ------
    ModbusException
        Write modbus exception to error log.
    """
    response: Optional[ModbusResponse] = None

    try:
        response = callback(**data)

        if response and response.isError():
            response = None
    except ModbusException as error:
        UNIPI_LOGGER.error("%s %s", LogPrefix.MODBUS, error)

    return response
