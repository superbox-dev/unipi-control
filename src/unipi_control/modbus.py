class UnknownModbusRegister(Exception):
    """Modbus register not found."""

    def __init__(self, address: int):
        message: str = f"Unknown register {address}"
        super().__init__(message)


class NoCachedModbusRegister(Exception):
    """No cached modbus register value found."""

    def __init__(self, address, unit):
        message: str = f"No cached value of register {address} " f"on unit {unit} - read error"
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
        self._registered_input: dict = {}

        for modbus_register_block in modbus_register_blocks:
            for index in range(modbus_register_block["count"]):
                reg_index: int = modbus_register_block["start_reg"] + index

                if modbus_register_block.get("type") == "input":
                    self._registered_input[reg_index] = None
                else:
                    self._registered[reg_index] = None

    async def scan(self):
        """Read modbus register blocks and cache the response."""
        for modbus_register_block in self.modbus_register_blocks:
            data: dict = {
                "address": modbus_register_block["start_reg"],
                "count": modbus_register_block["count"],
                "unit": 0,
            }

            if modbus_register_block.get("type") == "input":
                response = await self.modbus_client.read_input_registers(**data)

                for index in range(data["count"]):
                    self._registered_input[data["address"] + index] = response.registers[index]
            else:
                response = await self.modbus_client.read_holding_registers(**data)

                for index in range(data["count"]):
                    self._registered[data["address"] + index] = response.registers[index]

    def get_register(self, address: int, index: int, unit: int = 0, is_input: bool = False) -> list:
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
