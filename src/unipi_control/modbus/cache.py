import asyncio
from typing import Any
from typing import Dict
from typing import List
from typing import NamedTuple

from pymodbus.client import AsyncModbusSerialClient
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusIOException
from pymodbus.pdu import ExceptionResponse

from superbox_utils.core.exception import UnexpectedException
from superbox_utils.dict.data_dict import DataDict
from unipi_control.config import HardwareType
from unipi_control.config import LogPrefix
from unipi_control.config import logger


class ModbusClient(NamedTuple):
    tcp: AsyncModbusTcpClient
    serial: AsyncModbusSerialClient


class ModbusCacheData(DataDict):
    """Class that scan modbus register blocks and cache the response.

    Attributes
    ----------
    modbus_client : ModbusClient
        A modbus client.
    hardware_definitions : dict
        hardware definition from the neuron, extensions and third party devices.
    """

    def __init__(self, modbus_client: ModbusClient, hardware_definitions: Dict[str, dict]):
        super().__init__()

        self.modbus_client: ModbusClient = modbus_client
        self.hardware_definitions: Dict[str, dict] = hardware_definitions
        self.data: Dict[str, Dict[int, Any]] = {}

    async def scan(self, hardware_types: List[str]):
        """Read modbus register blocks and cache the response."""

        for hardware_type, hardware_definition in self.hardware_definitions.items():
            if not [item for item in hardware_types if item in hardware_type]:
                continue

            if not self.data.get(hardware_type):
                self.data[hardware_type] = {}

            for modbus_register_block in hardware_definition.get("modbus_register_blocks", []):
                data: dict = {
                    "address": modbus_register_block["start_reg"],
                    "count": modbus_register_block["count"],
                    "slave": modbus_register_block.get("unit", 0),
                }

                try:
                    response = await (
                        self.modbus_client.tcp.read_input_registers(**data)
                        if hardware_type == HardwareType.NEURON
                        else self.modbus_client.serial.read_input_registers(**data)
                    )

                    if not isinstance(response, (ModbusIOException, ExceptionResponse)):
                        for index in range(data["count"]):
                            self.data[hardware_type][data["address"] + index] = response.registers[index]
                except asyncio.exceptions.TimeoutError:
                    logger.error("%s [%s] Timeout on: %s", LogPrefix.MODBUS, hardware_definition.get("type"), data)

    def get_register(self, address: int, index: int, unit: int) -> list:
        """Get the responses from the cached modbus register blocks.

        Parameters
        ----------
        address : int
            The starting address to read from.
        index : int
            The number of registers to read.
        unit : int
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
            if _address not in self.data["neuron"] or self.data["neuron"][_address] is None:
                raise UnexpectedException(f"Modbus error on address {_address} (unit: {unit})")
            ret += [self.data["neuron"][_address]]

        return ret
