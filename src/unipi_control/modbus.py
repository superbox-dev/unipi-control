from pymodbus.exceptions import ModbusIOException
from pymodbus.pdu import ExceptionResponse


class ModbusRegisterException(Exception):
    """Modbus register exception."""

    def __init__(self, address: int, unit: int):
        message: str = f"Modbus error on address {address} (unit: {unit})"
        super().__init__(message)


class ModbusCacheMap:
    """Class that scan modbus register blocks and cache the response.

    Attributes
    ----------
    modbus_client : class
        A modbus tcp client.
    modbus_register_blocks : list of dicts
        The modbus register blocks.
    """

    def __init__(self, modbus_client, modbus_register_blocks: list):
        self.modbus_client = modbus_client
        self.modbus_register_blocks: list = modbus_register_blocks

        self._registered: dict = {}

        for modbus_register_block in modbus_register_blocks:
            for index in range(modbus_register_block["count"]):
                reg_index: int = modbus_register_block["start_reg"] + index
                self._registered[reg_index] = None

    async def scan(self):
        """Read modbus register blocks and cache the response."""
        for modbus_register_block in self.modbus_register_blocks:
            data: dict = {
                "address": modbus_register_block["start_reg"],
                "count": modbus_register_block["count"],
                "unit": 0,
            }

            response = await self.modbus_client.read_holding_registers(**data)

            if not isinstance(response, ModbusIOException) and not isinstance(response, ExceptionResponse):
                for index in range(data["count"]):
                    self._registered[data["address"] + index] = response.registers[index]

    def get_register(self, address: int, index: int, unit: int = 0) -> list:
        """Get the responses from the cached modbus register blocks.

        Parameters
        ----------
        address : int
            The starting address to read from.
        index : int
            The number of registers to read.
        unit : int, default: 0
            The slave unit this request is targeting.

        Returns
        -------
        list
            A list of cached modbus register blocks.

        Raises
        ------
        UnknownModbusRegister
            Because modbus register not found.
        NoCachedModbusRegister
            Because cached Modbus register value not found.
        """
        ret: list = []

        for _address in range(index, address + index):
            if _address not in self._registered or self._registered[_address] is None:
                raise ModbusRegisterException(_address, unit)

            ret += [self._registered[_address]]

        return ret
