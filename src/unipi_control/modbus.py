import asyncio
from typing import Dict
from typing import List
from typing import NamedTuple

from pymodbus.client import AsyncModbusSerialClient
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusIOException
from pymodbus.pdu import ExceptionResponse

from superbox_utils.core.exception import UnexpectedException
from unipi_control.config import HardwareDefinition
from unipi_control.config import HardwareType
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
    definitions: dict
        hardware definition from the neuron, extensions and third party devices.
    """

    def __init__(self, modbus_client: ModbusClient, definitions: List[HardwareDefinition]):
        self.modbus_client: ModbusClient = modbus_client
        self.definitions: List[HardwareDefinition] = definitions

        self.data: Dict[int, Dict[int, int]] = {}

    async def scan(self, hardware_types: List[str]):
        """Read modbus register blocks and cache the response."""
        for definition in self.definitions:
            if definition.hardware_type not in hardware_types:
                continue

            self.data[definition.unit] = {}

            for modbus_register_block in definition.modbus_register_blocks:
                data: dict = {
                    "address": modbus_register_block["start_reg"],
                    "count": modbus_register_block["count"],
                    "slave": definition.unit,
                }

                try:
                    response = await (
                        self.modbus_client.tcp.read_input_registers(**data)
                        if definition.hardware_type == HardwareType.NEURON
                        else self.modbus_client.serial.read_input_registers(**data)
                    )

                    if not isinstance(response, (ModbusIOException, ExceptionResponse)):
                        for index in range(data["count"]):
                            self.data[definition.unit][data["address"] + index] = response.registers[index]
                except asyncio.exceptions.TimeoutError:
                    logger.error("%s Timeout on: %s", LogPrefix.MODBUS, data)

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

        Raises
        ------
        UnexpectedException
            Because modbus error on register.
        """
        ret: list = []

        for _address in range(address, address + index):
            if _address not in self.data[unit] or self.data[unit][_address] is None:
                raise UnexpectedException(f"Modbus error on address {_address} (unit: {unit})")

            ret += [self.data[unit][_address]]

        return ret
