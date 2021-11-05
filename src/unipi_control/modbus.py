from typing import Coroutine

from pymodbus.client.asynchronous import schedulers
from pymodbus.client.asynchronous.tcp import AsyncModbusTCPClient as ModbusTCPClient


class ModbusException(Exception):
    """Exception when can't connect to Modbus TCP."""
    def __str__(self):
        return "Can't connect to Modbus TCP!"


class UnknownModbusRegister(Exception):
    """Exception when Modbus register not found."""
    def __init__(self, counter):
        message: str = f"Unknown register {counter}"
        super().__init__(message)


class NoCachedModbusRegister(Exception):
    """Exception when cached Modbus register value not found."""
    def __init__(self, counter, unit):
        message: str = f"No cached value of register {counter} " \
                       f"on unit {unit} - read error"
        super().__init__(message)


class Modbus:
    """Class that extend the modbus client with better error handling."""
    def __init__(self, loop):
        """Initialize modbus client.

        Parameters
        ----------
        loop:
            Current asyncio event loop.
        """
        self.loop, self.modbus = ModbusTCPClient(schedulers.ASYNC_IO, loop=loop)
        self.modbus_client = self.modbus.protocol

    async def write_coil(self, address: int, value: int, unit: int) -> Coroutine:
        """Write value to modbus address.

        Parameters
        ----------
        address: int
            Coil offset to write to.
        value: int
            Bit value to write.
        unit: int
            The slave unit this request is targeting.

        Returns
        ----------
        response: Coroutine
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
        address: int
            The starting address to write to.
        value: int
            The value to write to the specified address.
        unit: int
            The slave unit this request is targeting.

        Returns
        ----------
        response: Coroutine
            A deferred response handle.

        Raises
        ------
        ModbusException
            Because can't connect to Modbus TCP.
        """
        if not self.modbus_client or not self.modbus_client.connected:
            raise ModbusException()

        return await self.modbus_client.write_register(address, value, unit=unit)

    async def read_holding_registers(
        self, address: int, count: int, unit: int
    ) -> Coroutine:
        """Read value from modbus registers.

        Parameters
        ----------
        address: int
            The starting address to read from.
        count: int
            The number of registers to read.
        unit: int
            The slave unit this request is targeting.

        Returns
        ----------
        response: Coroutine
            A deferred response handle.

        Raises
        ------
        ModbusException
            Because can't connect to Modbus TCP.
        """
        if not self.modbus_client or not self.modbus_client.connected:
            raise ModbusException()

        return await self.modbus_client.read_holding_registers(
            address, count, unit=unit
        )

    async def read_input_registers(
        self, address: int, count: int, unit: int
    ) -> Coroutine:
        """Read value from modbus input registers.

        Parameters
        ----------
        address: int
            The starting address to read from.
        count: int
            The number of registers to read.
        unit: int
            The slave unit this request is targeting.

        Returns
        ----------
        response: Coroutine
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
    """Class that scan defined modbus register blocks and cache the result.

    Attributes
    ----------
    modbus: class
        The ``modbus.Modbus`` class.
    modbus_register_blocks: list
        Modbus register blocks as ``list`` of ``dicts``.
    """
    def __init__(self, modbus_register_blocks: list, modbus):
        """Initialize modbus cache map.

        Parameters
        ----------
        modbus_register_blocks: list
            The ``modbus.Modbus`` class.
        modbus: class
            Modbus register blocks as ``list`` of ``dicts``.
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

    def get_register(self, count: int, index: int, unit=0, is_input=False) -> list:
        ret: list = []

        for counter in range(index, count + index):
            if is_input:
                if counter not in self._registered_input:
                    raise UnknownModbusRegister(counter)
                elif self._registered_input[counter] is None:
                    raise NoCachedModbusRegister(counter, unit)

                ret += [self._registered_input[counter]]
            else:
                if counter not in self._registered:
                    raise UnknownModbusRegister(counter)
                elif self._registered[counter] is None:
                    raise NoCachedModbusRegister(counter, unit)

                ret += [self._registered[counter]]

        return ret

    async def scan(self):
        for modbus_register_block in self.modbus_register_blocks:
            data: dict = {
                "address": modbus_register_block["start_reg"],
                "count": modbus_register_block["count"],
                "unit": 0,
            }

            if modbus_register_block.get("type") == "input":
                val = await self.modbus.read_input_registers(**data)

                for index in range(data["count"]):
                    reg_index: int = data["address"] + index
                    self._registered_input[reg_index] = val.registers[index]
            else:
                val = await self.modbus.read_holding_registers(**data)

                for index in range(data["count"]):
                    reg_index: int = data["address"] + index
                    self._registered[reg_index] = val.registers[index]
