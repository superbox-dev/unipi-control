"""Collection of typed tuples and dicts."""

from typing import List
from typing import NamedTuple
from typing import Optional
from typing import TypedDict

from pymodbus.client import AsyncModbusSerialClient
from pymodbus.client import AsyncModbusTcpClient


class ModbusClient(NamedTuple):
    tcp: AsyncModbusTcpClient
    serial: AsyncModbusSerialClient


class ModbusRegisterBlock(TypedDict):
    start_reg: int
    count: int
    slave: Optional[int]


class ModbusFeature(TypedDict):
    feature_type: str
    major_group: int
    count: int
    val_reg: int
    val_coil: Optional[int]


class EastronModbusFeature(ModbusFeature):
    friendly_name: str
    device_class: Optional[str]
    state_class: Optional[str]
    unit_of_measurement: Optional[str]


class ModbusWriteData(TypedDict):
    address: Optional[int]
    value: bool
    slave: int


class ModbusReadData(TypedDict):
    address: int
    count: int
    slave: Optional[int]


class HardwareDefinition(NamedTuple):
    unit: int
    hardware_type: str
    device_name: Optional[str]
    suggested_area: Optional[str]
    manufacturer: Optional[str]
    model: str
    modbus_register_blocks: List[ModbusRegisterBlock]
    modbus_features: List[ModbusFeature]
