"""Modbus helper to connect and scan registers."""
import asyncio
from time import time
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import NamedTuple
from typing import Optional
from typing import TypedDict
from typing import Union

from pymodbus.client import AsyncModbusSerialClient
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ModbusResponse

from unipi_control.config import LogPrefix
from unipi_control.config import UNIPI_LOGGER
from unipi_control.hardware.map import HardwareMap
from unipi_control.hardware.constants import HardwareType
from unipi_control.helpers.exceptions import UnexpectedError
from unipi_control.config import Config


class ModbusClient(NamedTuple):
    tcp: AsyncModbusTcpClient
    serial: AsyncModbusSerialClient


class ModbusReadData(TypedDict):
    address: int
    count: int
    slave: Optional[int]


class ModbusWriteData(TypedDict):
    address: Optional[int]
    value: bool
    slave: int


class ModbusHelper:
    def __init__(self, config: Config, client: ModbusClient, hardware: HardwareMap) -> None:
        self.config: Config = config
        self.client: ModbusClient = client
        self.hardware: HardwareMap = hardware

        self.data: Dict[int, Dict[int, int]] = {}

        self.modubus_rtu_sleep: float = round(3.5 * 11 / self.config.modbus_serial.baud_rate, 4)
        UNIPI_LOGGER.debug("%s [RTU] 3.5 character time: %s", LogPrefix.MODBUS, self.modubus_rtu_sleep)

    async def connect_tcp(self, *, reconnect: bool = False) -> None:
        """Connect to Modbus TCP."""
        await self.client.tcp.connect()

        if self.client.tcp.connected:
            UNIPI_LOGGER.debug(
                "%s [TCP] Client reconnected to %s:%s" if reconnect else "%s [TCP] Client connected to %s:%s",
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

    async def scan_tcp(self) -> None:
        """Scan Modbus TCP and add response to the cache."""
        if not self.client.tcp.connected:
            await self.connect_tcp(reconnect=True)

        for definition in self.hardware.get_definition_by_hardware_types([HardwareType.PLC]):
            if not self.data.get(definition.unit):
                self.data[definition.unit] = {}

            for modbus_register_block in definition.modbus_register_blocks:
                data: ModbusReadData = {
                    "address": modbus_register_block["start_reg"],
                    "count": modbus_register_block["count"],
                    "slave": modbus_register_block.get("unit", definition.unit),
                }

                response: Optional[ModbusResponse] = await check_modbus_call(self.client.tcp.read_input_registers, data)

                if response:
                    register: List[int] = response.registers
                    for index in range(data["count"]):
                        self.data[definition.unit][data["address"] + index] = register[index]

    async def connect_serial(self, *, reconnect: bool = False) -> None:
        """Connect to Modbus RTU."""
        await self.client.serial.connect()

        if self.client.serial.connected:
            UNIPI_LOGGER.debug(
                "%s [RTU] Client reconnected to %s" if reconnect else "%s [RTU] Client connected to %s",
                LogPrefix.MODBUS,
                self.config.modbus_serial.port,
            )
        else:
            msg: str = f"{LogPrefix.MODBUS} [RTU] Client can't connect to {self.config.modbus_serial.port}"
            raise UnexpectedError(msg)

    async def scan_serial(self) -> None:
        """Scan Modbus RTU and add response to the cache."""
        start_time_1: float = time()

        for definition in self.hardware.get_definition_by_hardware_types([HardwareType.EXTENSION]):
            start_time_2: float = time()

            if not self.client.serial.connected:
                await self.connect_serial(reconnect=True)

            if not self.data.get(definition.unit):
                self.data[definition.unit] = {}

            for modbus_register_block in definition.modbus_register_blocks:
                data: ModbusReadData = {
                    "address": modbus_register_block["start_reg"],
                    "count": modbus_register_block["count"],
                    "slave": modbus_register_block.get("unit", definition.unit),
                }

                response: Optional[ModbusResponse] = await check_modbus_call(
                    self.client.serial.read_input_registers, data
                )

                if response:
                    register: List[int] = response.registers
                    for index in range(data["count"]):
                        self.data[definition.unit][data["address"] + index] = register[index]

            await asyncio.sleep(self.modubus_rtu_sleep * 2)

            UNIPI_LOGGER.debug(
                "%s [RTU] Unit %s scan duration: %s",
                LogPrefix.MODBUS,
                definition.unit,
                round(time() - start_time_2, 4),
            )

        UNIPI_LOGGER.debug(
            "%s [RTU] Full scan duration: %s",
            LogPrefix.MODBUS,
            round(time() - start_time_1, 4),
        )

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

        try:
            data = self.data[unit]
        except KeyError:
            UNIPI_LOGGER.error("%s Cached data for unit %s not found!", LogPrefix.MODBUS, unit)
        else:
            for _address in range(address, address + index):
                if _address not in data or data[_address] is None:
                    UNIPI_LOGGER.error("%s Error on address %s (unit: %s)", LogPrefix.MODBUS, address, unit)
                else:
                    ret += [data[_address]]

        return ret


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

    Raises
    ------
    ModbusException
        Write modbus exception to error log.
    """
    response: Optional[ModbusResponse] = None

    try:
        response = await callback(**data)

        if response and response.isError():
            response = None
    except ModbusException as error:
        UNIPI_LOGGER.error("%s %s", LogPrefix.MODBUS, error)

    return response
