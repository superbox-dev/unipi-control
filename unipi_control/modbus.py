"""Modbus helpers and register caches."""

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
from unipi_control.config import LogPrefix
from unipi_control.config import UNIPI_LOGGER
from unipi_control.helpers.typing import HardwareDefinition
from unipi_control.helpers.typing import ModbusClient
from unipi_control.helpers.typing import ModbusReadData
from unipi_control.helpers.typing import ModbusRegisterBlock
from unipi_control.helpers.typing import ModbusWriteData


async def check_modbus_call(
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
    """
    response: Optional[ModbusResponse] = None

    try:
        response = await callback(**data)

        if response and response.isError():  # type: ignore[no-untyped-call]
            response = None
    except ModbusException as error:
        UNIPI_LOGGER.error("%s %s", LogPrefix.MODBUS, error)
    except asyncio.exceptions.TimeoutError:
        UNIPI_LOGGER.error("%s Timeout on: %s", LogPrefix.MODBUS, data)

    return response


class ModbusCacheData:
    """Class that scan modbus register blocks and cache the response.

    Attributes
    ----------
    modbus_client: ModbusClient
        A modbus client.
    hardware: HardwareMap
        The Unipi Neuron hardware definitions.
    """

    def __init__(self, modbus_client: ModbusClient, hardware: HardwareMap) -> None:
        self.modbus_client: ModbusClient = modbus_client
        self.hardware: HardwareMap = hardware

        self.data: Dict[int, Dict[int, int]] = {}

    async def _save_response(
        self, scan_type: str, modbus_register_block: ModbusRegisterBlock, definition: HardwareDefinition
    ) -> None:
        data: ModbusReadData = {
            "address": modbus_register_block["start_reg"],
            "count": modbus_register_block["count"],
            "slave": modbus_register_block.get("slave", definition.unit),
        }

        response: Optional[ModbusResponse] = None

        if scan_type == "tcp":
            response = await check_modbus_call(self.modbus_client.tcp.read_input_registers, data)
        elif scan_type == "serial":
            response = await check_modbus_call(self.modbus_client.serial.read_input_registers, data)

        if response:
            register = response.registers  # type: ignore[attr-defined]
            for index in range(data["count"]):
                self.data[definition.unit][data["address"] + index] = register[index]

    async def scan(self, scan_type: str, hardware_types: List[str]) -> None:
        """Read modbus register blocks and cache the response."""
        for definition in self.hardware.get_definition_by_hardware_types(hardware_types):
            if not self.data.get(definition.unit):
                self.data[definition.unit] = {}

            if scan_type == "serial":
                await asyncio.sleep(1)

            for modbus_register_block in definition.modbus_register_blocks:
                await self._save_response(scan_type, modbus_register_block, definition)

    def get_register(self, address: int, index: int, unit: int) -> List[int]:
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
        ret: List[int] = []

        for _address in range(address, address + index):
            if _address not in self.data[unit] or self.data[unit][_address] is None:
                UNIPI_LOGGER.error("%s Error on address %s (unit: %s)", LogPrefix.MODBUS, address, unit)
            else:
                ret += [self.data[unit][_address]]

        return ret
