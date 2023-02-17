import logging
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncGenerator
from typing import NamedTuple
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import PropertyMock

import pytest
import pytest_asyncio
from _pytest.fixtures import SubRequest  # pylint: disable=import-private-name
from pytest_mock import MockerFixture

from unipi_control.config import Config
from unipi_control.integrations.covers import CoverMap
from unipi_control.modbus import ModbusClient
from unipi_control.neuron import Neuron
from unipi_control.unipi_control import UnipiControl
from unittests.conftest_data import EXTENSION_EASTRON_SDM120M_MODBUS_REGISTER
from unittests.conftest_data import NEURON_L203_MODBUS_REGISTER


@pytest.fixture(autouse=True, scope="session")
def logger():
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger(UnipiControl.NAME).handlers.clear()
    logging.info("Initialize logging")


class ConfigLoader:
    def __init__(self, temp: Path):
        self.temp: Path = temp
        self.config_file_path: Path = self.temp / "control.yaml"

        hardware_data_path: Path = self.temp / "hardware/neuron"
        hardware_data_path.mkdir(parents=True)
        self.hardware_data_file_path = hardware_data_path / "MOCKED_MODEL.yaml"

        extension_hardware_data_path: Path = self.temp / "hardware/extensions"
        extension_hardware_data_path.mkdir(parents=True)
        self.extension_hardware_data_file_path = extension_hardware_data_path / "MOCKED_EASTRON.yaml"

        self.systemd_path: Path = self.temp / "systemd/system"
        self.systemd_path.mkdir(parents=True)

        self.temp_path: Path = self.temp / "unipi"
        self.temp_path.mkdir(parents=True)

    def write_config(self, content: str):
        with open(self.config_file_path, "w", encoding="utf-8") as _file:
            _file.write(content)

    def write_hardware_data(self, content: str):
        with open(self.hardware_data_file_path, "w", encoding="utf-8") as _file:
            _file.write(content)

    def write_extension_hardware_data(self, content: str):
        with open(self.extension_hardware_data_file_path, "w", encoding="utf-8") as _file:
            _file.write(content)

    def get_config(self) -> Config:
        return Config(config_base_path=self.temp, systemd_path=self.systemd_path, temp_path=self.temp_path)


@pytest.fixture()
def _config_loader(request: SubRequest, tmp_path: Path) -> ConfigLoader:
    config_loader: ConfigLoader = ConfigLoader(temp=tmp_path)
    config_loader.write_config(request.param[0])
    config_loader.write_hardware_data(request.param[1])
    config_loader.write_extension_hardware_data(request.param[2])

    logging.info("Create configuration: %s", tmp_path)

    return config_loader


@dataclass
class MockHardwareInfo:
    name: str = "MOCKED_NAME"
    model: str = "MOCKED_MODEL"
    version: str = "MOCKED_VERSION"
    serial: str = "MOCKED_SERIAL"


@pytest.fixture()
def _modbus_client(mocker: MockerFixture) -> ModbusClient:
    mock_response_is_error: MagicMock = MagicMock(registers=[0])
    mock_response_is_error.isError.return_value = False

    mock_modbus_tcp_client: AsyncMock = AsyncMock()
    mock_modbus_tcp_client.read_input_registers.side_effect = [
        # Board 1
        mock_response_is_error,
        # Board 2
        mock_response_is_error,
        # Board 3
        mock_response_is_error,
    ] + NEURON_L203_MODBUS_REGISTER

    mock_modbus_serial_client: AsyncMock = AsyncMock()
    mock_modbus_serial_client.read_input_registers.side_effect = EXTENSION_EASTRON_SDM120M_MODBUS_REGISTER

    mock_response_sw_version: MagicMock = MagicMock(registers=[32, 516])
    mock_response_sw_version.isError.return_value = False

    mock_modbus_serial_client.read_holding_registers.side_effect = [
        # Eastron SDM120M Software Version
        mock_response_sw_version
    ]

    mock_hardware_info: PropertyMock = mocker.patch("unipi_control.config.HardwareInfo", new_callable=PropertyMock())
    mock_hardware_info.return_value = MockHardwareInfo()

    return ModbusClient(tcp=mock_modbus_tcp_client, serial=mock_modbus_serial_client)


@pytest_asyncio.fixture()
async def _neuron(_config_loader: ConfigLoader, _modbus_client: ModbusClient) -> AsyncGenerator:
    config: Config = _config_loader.get_config()

    _neuron: Neuron = Neuron(config=config, modbus_client=_modbus_client)
    await _neuron.init()

    yield _neuron


@pytest_asyncio.fixture()
async def _covers(_config_loader: ConfigLoader, _neuron: Neuron) -> AsyncGenerator:
    config: Config = _config_loader.get_config()
    yield CoverMap(config=config, features=_neuron.features)


class MockMQTTMessage(NamedTuple):
    payload: bytes


class MockMQTTMessages:
    def __init__(self, message):
        self.message = message

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.message:
            return MockMQTTMessage(self.message.pop())

        raise StopAsyncIteration
