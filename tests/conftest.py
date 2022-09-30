import logging
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import PropertyMock

import pytest
from pytest_asyncio.plugin import SubRequest
from pytest_mock import MockerFixture

from conftest_data import MODBUS_HOLDING_REGISTER
from unipi_control.config import Config
from unipi_control.config import LOGGER_NAME


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

        self.systemd_path = self.temp / "systemd/system"
        self.systemd_path.mkdir(parents=True)

        self.temp_path = self.temp / "unipi"
        self.temp_path.mkdir(parents=True)

    def write_config(self, content: str):
        with open(self.config_file_path, "w") as f:
            f.write(content)

    def write_hardware_data(self, content: str):
        with open(self.hardware_data_file_path, "w") as f:
            f.write(content)

    def get_config(self) -> Config:
        return Config(
            config_base_path=self.temp,
            systemd_path=self.systemd_path,
            temp_path=self.temp_path,
        )


@pytest.fixture()
def config_loader(request: SubRequest, tmp_path: Path) -> ConfigLoader:
    c = ConfigLoader(temp=tmp_path)
    c.write_config(request.param[0])
    c.write_hardware_data(request.param[1])

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

    mock_response_is_error: MagicMock = MagicMock()
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
