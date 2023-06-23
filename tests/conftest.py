"""Test configuration for pytest."""
import asyncio
import logging
from asyncio import AbstractEventLoop
from asyncio import AbstractEventLoopPolicy
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import AsyncGenerator
from typing import Dict
from typing import Generator
from typing import List
from typing import NamedTuple
from typing import Optional
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import PropertyMock

import pytest
import pytest_asyncio
from _pytest.fixtures import SubRequest  # pylint: disable=import-private-name
from pymodbus.pdu import ModbusResponse
from pytest_mock import MockerFixture

from tests.conftest_data import EXTENSION_EASTRON_SDM120M_MODBUS_REGISTER
from tests.conftest_data import NEURON_L203_MODBUS_REGISTER
from unipi_control.config import Config
from unipi_control.extensions.eastron import EastronSDM120M
from unipi_control.helpers.typing import ModbusClient
from unipi_control.integrations.covers import CoverMap
from unipi_control.neuron import Neuron


@pytest.fixture(autouse=True)
def _logger() -> None:
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.info("Initialized logging")


@pytest.fixture()
def event_loop() -> Generator[AbstractEventLoop, None, None]:
    """Modify the original pytest asyncio event loop.

    INFO: https://pytest-asyncio.readthedocs.io/en/latest/reference/fixtures.html
    """
    policy: AbstractEventLoopPolicy = asyncio.get_event_loop_policy()
    loop: AbstractEventLoop = policy.new_event_loop()

    yield loop

    pending = asyncio.all_tasks(loop=loop)
    group = asyncio.gather(*pending)
    loop.run_until_complete(group)

    loop.close()


class ConfigLoader:
    def __init__(self, temp: Path) -> None:
        self.temp: Path = temp
        self.config_file_path: Path = self.temp / "control.yaml"

        hardware_data_path: Path = self.temp / "hardware/neuron"
        hardware_data_path.mkdir(parents=True)
        self.hardware_data_file_path = hardware_data_path / "MOCKED_MODEL.yaml"

        extension_hardware_data_path: Path = self.temp / "hardware/extensions"
        extension_hardware_data_path.mkdir(parents=True)
        self.extension_hardware_data_file_path = extension_hardware_data_path / "MOCKED_EASTRON.yaml"

        self.temp_path: Path = self.temp / "unipi"
        self.temp_path.mkdir(parents=True)

    def write_config(self, content: str) -> None:
        """Write config yaml file to temporary directory.

        Parameters
        ----------
        content: str
            Content for the config yaml file
        """
        with self.config_file_path.open("w", encoding="utf-8") as _file:
            _file.write(content)

    def write_hardware_data(self, content: str) -> None:
        """Write hardware yaml file to temporary directory.

        Parameters
        ----------
        content: str
            Content for the hardware yaml file
        """
        with self.hardware_data_file_path.open("w", encoding="utf-8") as _file:
            _file.write(content)

    def write_extension_hardware_data(self, content: str) -> None:
        """Write extension hardware yaml file to temporary directory.

        Parameters
        ----------
        content: str
            Content for extension the hardware yaml file
        """
        with self.extension_hardware_data_file_path.open("w", encoding="utf-8") as _file:
            _file.write(content)

    def get_config(self, config_base_path: Optional[Path] = None) -> Config:
        """Get the config dataclass."""
        if not config_base_path:
            config_base_path = self.temp

        return Config(config_base_path=config_base_path, temp_path=self.temp_path)


@pytest.fixture(name="config_loader")
def create_config(request: SubRequest, tmp_path: Path) -> ConfigLoader:
    """Create config yaml file in temporary directory.

    Parameters
    ----------
    request: SubRequest
        config, hardware data and extension hardware data content.
    tmp_path: Path
        Temporary directory for pytest.

    Returns
    -------
    ConfigLoader:
        Helper methods from the config loader class.
    """
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


class MockModbusClient(NamedTuple):
    tcp: AsyncMock
    serial: AsyncMock


@pytest.fixture(name="modbus_client")
def mock_modbus_client(request: SubRequest, mocker: MockerFixture) -> MockModbusClient:
    """Mock modbus client responses from read registers.

    Parameters
    ----------
    request: SubRequest
        Config for mocked modbus fixture.
    mocker: MockerFixture
        pytest fixture for mocking.

    Returns
    -------
    MockModbusClient: NamedTuple
        Named tuple with mocked tcp and serial client
    """
    modbus_client_config: Dict[str, Any] = getattr(request, "param", {})

    mock_bord_response: MagicMock = MagicMock(spec=ModbusResponse, registers=[0])
    mock_bord_response.isError.return_value = False

    for mock_response in NEURON_L203_MODBUS_REGISTER:
        mock_response.isError.return_value = False

    mock_modbus_tcp_client: AsyncMock = AsyncMock()
    mock_modbus_tcp_client.read_input_registers.side_effect = [
        # Board 1
        mock_bord_response,
        # Board 2
        mock_bord_response,
        # Board 3
        mock_bord_response,
        # Add the modbus register twice to test if feature changed.
        # In the first scan() features changed and in the second scan() features not changed.
        *NEURON_L203_MODBUS_REGISTER + NEURON_L203_MODBUS_REGISTER,
    ]

    for mock_response in EXTENSION_EASTRON_SDM120M_MODBUS_REGISTER:
        mock_response.isError.return_value = False

    mock_modbus_serial_client: AsyncMock = AsyncMock()
    mock_modbus_serial_client.read_input_registers.side_effect = EXTENSION_EASTRON_SDM120M_MODBUS_REGISTER

    mock_response_sw_version: MagicMock = MagicMock(spec=ModbusResponse, registers=[32, 516])
    mock_response_sw_version.isError.return_value = modbus_client_config.get("eastron_sw_version_failed", False)

    mock_modbus_serial_client.read_holding_registers.side_effect = [
        # Eastron SDM120M Software Version
        mock_response_sw_version,
    ] * (EastronSDM120M.RETRY_LIMIT if modbus_client_config.get("eastron_sw_version_failed") else 1)

    mock_hardware_info: PropertyMock = mocker.patch("unipi_control.config.HardwareInfo", new_callable=PropertyMock())
    mock_hardware_info.return_value = MockHardwareInfo()

    return MockModbusClient(tcp=mock_modbus_tcp_client, serial=mock_modbus_serial_client)


@pytest_asyncio.fixture(name="neuron")
async def init_neuron(config_loader: ConfigLoader, modbus_client: ModbusClient) -> AsyncGenerator[Neuron, None]:
    """Initialize neuron device for tests.

    Parameters
    ----------
    config_loader: ConfigLoader
        Config loader class with helper methods.
    modbus_client: ModbusClient
        Mocked modbus client.
    """
    config: Config = config_loader.get_config()
    config.logging.init()

    neuron: Neuron = Neuron(config=config, modbus_client=modbus_client)
    await neuron.init()

    yield neuron


@pytest_asyncio.fixture(name="covers")
async def create_cover_map(config_loader: ConfigLoader, neuron: Neuron) -> AsyncGenerator[CoverMap, None]:
    """Initialize cover map for tests.

    Parameters
    ----------
    config_loader: ConfigLoader
        Config loader class with helper methods.
    neuron: Neuron
        Initialized neuron device.
    """
    config: Config = config_loader.get_config()
    config.logging.init()
    covers: CoverMap = CoverMap(config=config, features=neuron.features)

    yield covers


class MockMQTTMessage(NamedTuple):
    payload: bytes


class MockMQTTMessages:
    def __init__(self, message: List[bytes]) -> None:
        self.message: List[bytes] = message

    def __aiter__(self) -> "MockMQTTMessages":
        return self

    async def __anext__(self) -> MockMQTTMessage:
        if self.message:
            return MockMQTTMessage(self.message.pop())

        raise StopAsyncIteration
