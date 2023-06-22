"""Unit tests for neuron device."""

from typing import List, TYPE_CHECKING
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import PropertyMock

import pytest
from _pytest.logging import LogCaptureFixture  # pylint: disable=import-private-name
from pymodbus.pdu import ModbusResponse
from pytest_mock import MockerFixture

from tests.conftest import ConfigLoader
from tests.conftest import MockHardwareInfo
from tests.conftest_data import CONFIG_CONTENT
from tests.conftest_data import EXTENSION_HARDWARE_DATA_CONTENT
from tests.conftest_data import HARDWARE_DATA_CONTENT
from unipi_control.helpers.typing import ModbusClient
from unipi_control.neuron import Neuron

if TYPE_CHECKING:
    from unipi_control.config import Config


class TestUnhappyPathNeuron:
    @pytest.mark.asyncio()
    @pytest.mark.parametrize(
        "config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    async def test_no_boards_found(
        self,
        mocker: MockerFixture,
        config_loader: ConfigLoader,
        caplog: LogCaptureFixture,
    ) -> None:
        """Test read neuron boards failed with no boards found."""
        config: Config = config_loader.get_config()

        mock_response: MagicMock = MagicMock(spec=ModbusResponse)
        mock_response.isError.return_value = True

        mock_modbus_tcp_client: AsyncMock = AsyncMock()
        mock_modbus_tcp_client.read_input_registers.return_value = mock_response

        mock_hardware_info: PropertyMock = mocker.patch(
            "unipi_control.config.HardwareInfo", new_callable=PropertyMock()
        )
        mock_hardware_info.return_value = MockHardwareInfo()

        modbus_client = ModbusClient(tcp=mock_modbus_tcp_client, serial=mock_modbus_tcp_client)
        neuron: Neuron = Neuron(config=config, modbus_client=modbus_client)

        await neuron.read_boards()

        logs: List[str] = [record.getMessage() for record in caplog.records]

        assert "[MODBUS] No board on SPI 1" in logs
        assert "[MODBUS] No board on SPI 2" in logs
        assert "[MODBUS] No board on SPI 3" in logs
