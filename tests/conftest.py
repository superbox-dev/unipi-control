import logging
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import PropertyMock

import pytest
import pytest_asyncio
from _pytest.fixtures import SubRequest
from pytest_mock import MockerFixture

from conftest_data import MODBUS_HOLDING_REGISTER
from unipi_control.config import Config
from unipi_control.config import LOGGER_NAME
from unipi_control.neuron import Neuron


@pytest.fixture(autouse=True, scope="session")
def logger():
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger(LOGGER_NAME).handlers.clear()
    logging.info("Initialize logging")


class ConfigLoader:
    def __init__(self, temp: Path):
        self.temp: Path = temp
        self.config_file_path: Path = self.temp / "control.yaml"

        self.hardware_data_path: Path = self.temp / "hardware/neuron"
        self.hardware_data_path.mkdir(parents=True)
        self.hardware_data_file_path = self.hardware_data_path / "MOCKED_MODEL.yaml"

        self.systemd_path: Path = self.temp / "systemd/system"
        self.systemd_path.mkdir(parents=True)

        self.temp_path: Path = self.temp / "unipi"
        self.temp_path.mkdir(parents=True)

        self.sys_bus: Path = self.temp / "sys/bus/i2c/devices"
        self.sys_bus.mkdir(parents=True)

        self.unipi_1: Path = self.sys_bus / "1-0050"
        self.unipi_1.mkdir(parents=True)
        self.unipi_patron: Path = self.sys_bus / "2-0057"
        self.unipi_patron.mkdir(parents=True)
        self.unipi_neuron_1: Path = self.sys_bus / "1-0057"
        self.unipi_neuron_1.mkdir(parents=True)
        self.unipi_neuron_0: Path = self.sys_bus / "0-0057"
        self.unipi_neuron_0.mkdir(parents=True)

    def write_config(self, content: str):
        with open(self.config_file_path, "w") as f:
            f.write(content)

    def write_hardware_data(self, content: str):
        with open(self.hardware_data_file_path, "w") as f:
            f.write(content)

    def write_hardware_info(self):
        with open(self.unipi_1 / "eeprom", "w") as f:
            f.write("MOCKED")

    def get_config(self) -> Config:
        return Config(
            config_base_path=self.temp,
            systemd_path=self.systemd_path,
            temp_path=self.temp_path,
            sys_bus=self.sys_bus,
        )


@pytest.fixture()
def config_loader(request: SubRequest, tmp_path: Path) -> ConfigLoader:
    c: ConfigLoader = ConfigLoader(temp=tmp_path)
    c.write_config(request.param[0])
    c.write_hardware_data(request.param[1])
    c.write_hardware_info()

    logging.info("Create configuration: %s", tmp_path)

    return c


@dataclass
class MockHardwareInfo:
    name: str = "MOCKED_NAME"
    model: str = "MOCKED_MODEL"
    version: str = "MOCKED_VERSION"
    serial: str = "MOCKED_SERIAL"


@pytest.fixture()
def modbus_client(mocker: MockerFixture) -> AsyncMock:
    mock_modbus_client: AsyncMock = AsyncMock()
    mock_modbus_client.read_holding_registers.side_effect = MODBUS_HOLDING_REGISTER

    mock_response_is_error: MagicMock = MagicMock(registers=[0])
    mock_response_is_error.isError.return_value = False

    mock_modbus_client.read_input_registers.return_value = mock_response_is_error

    mock_hardware_info: PropertyMock = mocker.patch("unipi_control.config.HardwareInfo", new_callable=PropertyMock())
    mock_hardware_info.return_value = MockHardwareInfo()

    return mock_modbus_client


@pytest_asyncio.fixture
async def neuron(config_loader: ConfigLoader, modbus_client):
    config: Config = config_loader.get_config()

    _neuron: Neuron = Neuron(config=config, modbus_client=modbus_client)
    await _neuron.read_boards()

    yield _neuron
