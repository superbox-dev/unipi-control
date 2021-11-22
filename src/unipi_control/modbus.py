from typing import Coroutine

from pymodbus.client.asynchronous import schedulers
from pymodbus.client.asynchronous.tcp import AsyncModbusTCPClient as ModbusTCPClient


class ModbusException(Exception):
    """Unipi Control can't connect to Modbus TCP."""

    def __str__(self):
        return "Can't connect to Modbus TCP!"


class UnknownModbusRegister(Exception):
    """Modbus register not found."""

    def __init__(self, address: int):
        """Initialize exception.

        Parameters
        ----------
        address : int
            The starting address to write to.
        """
        message: str = f"Unknown register {address}"
        super().__init__(message)


class NoCachedModbusRegister(Exception):
    """No cached modbus register value found."""

    def __init__(self, address, unit):
        """Initialize exception.

        Parameters
        ----------
        address : int
            The starting address to write to.
        unit : int
            The slave unit this request is targeting.
        """
        message: str = f"No cached value of register {address} " \
                       f"on unit {unit} - read error"
        super().__init__(message)


class Modbus:
    """Class that extend the modbus client with better error handling.

    Attributes
    ----------
    loop
        Current asyncio event loop.
    modbus_client
        The Modbus TCP client.
    """

    def __init__(self, loop):
        """Initialize modbus client.

        Parameters
        ----------
        loop :
            Current asyncio event loop.
        """
        self.loop, self.modbus = ModbusTCPClient(schedulers.ASYNC_IO, loop=loop)
        self.modbus_client = self.modbus.protocol

    async def write_coil(self, address: int, value: int, unit: int) -> Coroutine:
        """Write value to modbus address.

        Parameters
        ----------
        address : int
            Coil offset to write to.
        value : int
            Bit value to write.
        unit : int
            The slave unit this request is targeting.

        Returns
        ----------
        Coroutine
            A deferred response handle.

        Raises
        ------
        ModbusException
            Because can't connect to Modbus TCP.
        """
        if not self.modbus_client or not self.modbus_client.connected:
            raise ModbusException()

        return await self.modbus_client.write_coil(address, value, unit=unit)

    async def write_register(self, address: int, value: int, unit: int) -> Coroutine:
        """Write value to modbus register.

        Parameters
        ----------
        address : int
            The starting address to write to.
        value : int
            The value to write to the specified address.
        unit : int
            The slave unit this request is targeting.

        Returns
        ----------
        Coroutine
            A deferred response handle.

        Raises
        ------
        ModbusException
            Because can't connect to Modbus TCP.
        """
        if not self.modbus_client or not self.modbus_client.connected:
            raise ModbusException()

        return await self.modbus_client.write_register(address, value, unit=unit)

    async def read_holding_registers(self, address: int, count: int, unit: int) -> Coroutine:
        """Read value from modbus holding registers.

        Parameters
        ----------
        address : int
            The starting address to read from.
        count : int
            The number of registers to read.
        unit : int
            The slave unit this request is targeting.

        Returns
        ----------
        Coroutine
            A deferred response handle.

        Raises
        ------
        ModbusException
            Because can't connect to Modbus TCP.
        """
        if not self.modbus_client or not self.modbus_client.connected:
            raise ModbusException()

        return await self.modbus_client.read_holding_registers(address, count, unit=unit)

    async def read_input_registers(self, address: int, count: int, unit: int) -> Coroutine:
        """Read value from modbus input registers.

        Parameters
        ----------
        address : int
            The starting address to read from.
        count : int
            The number of registers to read.
        unit : int
            The slave unit this request is targeting.

        Returns
        ----------
        Coroutine
            A deferred response handle.

        Raises
        ------
        ModbusException
            Because can't connect to Modbus TCP.
        """
        if not self.modbus_client or not self.modbus_client.connected:
            raise ModbusException()

        return await self.modbus_client.read_input_registers(address, count, unit=unit)


class ModbusCacheMap:
    """Class that scan modbus register blocks and cache the response.

    Attributes
    ----------
    modbus : class
        Extended modbus client class.
    modbus_register_blocks : list of dicts
        The modbus register blocks.
    """

    def __init__(self, modbus, modbus_register_blocks: list):
        """Initialize modbus cache map.

        Parameters
        ----------
        modbus : class
            The ``modbus.Modbus`` class.
        modbus_register_blocks : list of dict
            The modbus register blocks.
        """
        self.modbus = modbus
        self.modbus_register_blocks: list = modbus_register_blocks

        self._registered: dict = {}
        self._registered_input: dict = {}

        for modbus_register_block in modbus_register_blocks:
            for index in range(modbus_register_block["count"]):
                reg_index: int = modbus_register_block["start_reg"] + index

                if modbus_register_block.get("type") == "input":
                    self._registered_input[reg_index] = None
                else:
                    self._registered[reg_index] = None

    async def scan(self) -> None:
        """Read modbus register blocks and cache the response."""
        for modbus_register_block in self.modbus_register_blocks:
            data: dict = {
                "address": modbus_register_block["start_reg"],
                "count": modbus_register_block["count"],
                "unit": 0,
            }

            if modbus_register_block.get("type") == "input":
                response = await self.modbus.read_input_registers(**data)

                for index in range(data["count"]):
                    reg_index: int = data["address"] + index
                    self._registered_input[reg_index] = response.registers[
                        index]
            else:
                response = await self.modbus.read_holding_registers(**data)

                for index in range(data["count"]):
                    reg_index: int = data["address"] + index
                    self._registered[reg_index] = response.registers[index]

    def get_register(self, address: int, index: int, unit: int = 0, is_input: bool = False):
        """Get the responses from the cached modbus register blocks.

        Parameters
        ----------
        address : int
            The starting address to read from.
        index : int
            The number of registers to read.
        unit : int, default: 0
            The slave unit this request is targeting.
        is_input : bool, default: False
            ``True`` if it is modbus input registered else ``False``

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

        for address in range(index, address + index):
            if is_input:
                if address not in self._registered_input:
                    raise UnknownModbusRegister(address)
                elif self._registered_input[address] is None:
                    raise NoCachedModbusRegister(address, unit)

                ret += [self._registered_input[address]]
            else:
                if address not in self._registered:
                    raise UnknownModbusRegister(address)
                elif self._registered[address] is None:
                    raise NoCachedModbusRegister(address, unit)

                ret += [self._registered[address]]

        return ret
