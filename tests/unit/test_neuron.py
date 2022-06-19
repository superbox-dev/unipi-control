from dataclasses import dataclass
from typing import List

import pytest

from src.unipi_control.config import HardwareInfo
from src.unipi_control.neuron import Neuron


class NullModbusClient:
    def __init__(self, error):
        self._error: bool = error
        self._registers: List[int] = []

    @property
    def registers(self) -> List[int]:
        return self._registers

    def isError(self) -> bool:
        return self._error

    async def read_input_registers(self, address, count=1, **kwargs):
        return self

    async def read_holding_registers(self, address, count=1, **kwargs):
        self._registers = []

        for _ in range(count):
            self._registers.append(0)

        return self


@dataclass
class NullHardwareInfo(HardwareInfo):
    name: str = "Neuron"
    model: str = "L203"
    version: str = "unknown"
    serial: str = "unknown"


@pytest.mark.asyncio
async def test_neuron_happy_path(config):
    neuron: Neuron = Neuron(config=config, modbus_client=NullModbusClient(error=False), hardware_info=NullHardwareInfo)
    await neuron.read_boards()

    assert (len(neuron.boards)) == 3


@pytest.mark.asyncio
async def test_neuron_unhappy_path(config):
    neuron: Neuron = Neuron(config=config, modbus_client=NullModbusClient(error=True), hardware_info=NullHardwareInfo)
    await neuron.read_boards()

    assert (len(neuron.boards)) == 0
