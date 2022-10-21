from typing import Dict
from typing import NamedTuple

from pymodbus.client import AsyncModbusSerialClient
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusIOException
from pymodbus.pdu import ExceptionResponse

from superbox_utils.core.exception import UnexpectedException
from superbox_utils.dict.data_dict import DataDict


class ModbusClient(NamedTuple):
    tcp: AsyncModbusTcpClient
    serial: AsyncModbusSerialClient


class ModbusCacheData(DataDict):
    """Class that scan modbus register blocks and cache the response.

    Attributes
    ----------
    modbus_client : ModbusClient
        A modbus client.
    modbus_register_blocks_map : dict
        The neuron, extensions and third party devices modbus register blocks.
    """

    def __init__(self, modbus_client: ModbusClient, modbus_register_blocks_map: Dict[str, dict]):
        super().__init__()

        self.modbus_client: ModbusClient = modbus_client
        self.modbus_register_blocks_map: Dict[str, dict] = modbus_register_blocks_map

        self.data: dict = {
            "neuron": {},
            "extension": {},
            "third_party": {},
        }

        for key, neuron_modbus_register_blocks in modbus_register_blocks_map.items():
            for modbus_register_block in neuron_modbus_register_blocks.get("modbus_register_blocks", []):
                for index in range(modbus_register_block["count"]):
                    reg_index: int = modbus_register_block["start_reg"] + index
                    self.data[key][reg_index] = None

    async def scan(self):  # TODO: Scan by type
        """Read modbus register blocks and cache the response."""
        for neuron_modbus_register_blocks in self.modbus_register_blocks_map.values():
            for modbus_register_block in neuron_modbus_register_blocks.get("modbus_register_blocks", []):
                data: dict = {
                    "address": modbus_register_block["start_reg"],
                    "count": modbus_register_block["count"],
                    "slave": 0,
                }

                response = await self.modbus_client.tcp.read_holding_registers(**data)

                if not isinstance(response, (ModbusIOException, ExceptionResponse)):
                    for index in range(data["count"]):
                        self.data["neuron"][data["address"] + index] = response.registers[index]

    def get_register(self, address: int, index: int, slave: int = 0) -> list:
        """Get the responses from the cached modbus register blocks.

        Parameters
        ----------
        address : int
            The starting address to read from.
        index : int
            The number of registers to read.
        slave : int, default: 0
            The slave unit this request is targeting.

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

        for _address in range(index, address + index):
            if _address not in self.data["neuron"] or self.data["neuron"][_address] is None:
                raise UnexpectedException(f"Modbus error on address {_address} (slave: {slave})")

            ret += [self.data["neuron"][_address]]

        return ret
