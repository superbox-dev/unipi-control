import asyncio
from typing import Dict
from typing import List
from typing import NamedTuple
from typing import Optional

from pymodbus.client import AsyncModbusSerialClient
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusIOException
from pymodbus.pdu import ExceptionResponse
from pymodbus.register_read_message import ReadInputRegistersResponse

from unipi_control.config import HardwareData
from unipi_control.config import HardwareDefinition
from unipi_control.config import LogPrefix
from unipi_control.config import logger


class ModbusClient(NamedTuple):
    tcp: AsyncModbusTcpClient
    serial: AsyncModbusSerialClient


class ModbusCacheData:
    """Class that scan modbus register blocks and cache the response.

    Attributes
    ----------
    modbus_client: ModbusClient
        A modbus client.
    hardware: HardwareData
        The Unipi Neuron hardware definitions.
    """

    def __init__(self, modbus_client: ModbusClient, hardware: HardwareData) -> None:
        self.modbus_client: ModbusClient = modbus_client
        self.hardware: HardwareData = hardware

        self.data: Dict[int, Dict[int, int]] = {}

    async def _save_response(self, scan_type: str, modbus_register_block: dict, definition: HardwareDefinition) -> None:
        data: dict = {
            "address": modbus_register_block["start_reg"],
            "count": modbus_register_block["count"],
            "slave": modbus_register_block.get("slave", definition.unit),
        }

        response: Optional[ReadInputRegistersResponse] = None

        try:
            # TODO: Class 'ModbusResponse' does not define '__await__', so the 'await' operator cannot be used on its instances
            if scan_type == "tcp":
                response = await self.modbus_client.tcp.read_input_registers(**data)
            elif scan_type == "serial":
                response = await self.modbus_client.serial.read_input_registers(**data)

            if response:
                if not isinstance(response, (ModbusIOException, ExceptionResponse)):
                    for index in range(data["count"]):
                        self.data[definition.unit][data["address"] + index] = response.registers[index]
        except asyncio.exceptions.TimeoutError:
            logger.error("%s [%s] Timeout on: %s", LogPrefix.MODBUS, scan_type.upper(), data)

    async def scan(self, scan_type: str, hardware_types: List[str]) -> None:
        """Read modbus register blocks and cache the response."""
        for definition in self.hardware.get_definition_by_hardware_types(hardware_types):
            if not self.data.get(definition.unit):
                self.data[definition.unit] = {}

            await asyncio.sleep(8e-3)

            for modbus_register_block in definition.modbus_register_blocks:
                await self._save_response(scan_type, modbus_register_block, definition)

    def get_register(self, address: int, index: int, unit: int) -> list:
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
        ret: list = []

        for _address in range(address, address + index):
            if _address not in self.data[unit] or self.data[unit][_address] is None:
                logger.error("%s Error on address %s (unit: %s)", LogPrefix.MODBUS, address, unit)
            else:
                ret += [self.data[unit][_address]]

        return ret
