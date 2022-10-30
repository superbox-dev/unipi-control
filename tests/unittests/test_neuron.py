from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import PropertyMock

import pytest
from _pytest.logging import LogCaptureFixture
from pytest_mock import MockerFixture

from unipi_control.config import Config
from unipi_control.modbus import ModbusClient
from unipi_control.neuron import Neuron
from unittests.conftest import ConfigLoader
from unittests.conftest import MockHardwareInfo
from unittests.conftest_data import CONFIG_CONTENT
from unittests.conftest_data import EXTENSION_HARDWARE_DATA_CONTENT
from unittests.conftest_data import HARDWARE_DATA_CONTENT


class TestUnhappyPathNeuron:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "_config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    async def test_read_boards(
        self,
        mocker: MockerFixture,
        _config_loader: ConfigLoader,
        caplog: LogCaptureFixture,
    ):
        config: Config = _config_loader.get_config()

        mock_response_is_error: MagicMock = MagicMock()
        mock_response_is_error.isError.return_value = True

        mock_modbus_tcp_client: AsyncMock = AsyncMock()
        mock_modbus_tcp_client.read_input_registers.side_effect = mock_response_is_error

        mock_hardware_info: PropertyMock = mocker.patch(
            "unipi_control.config.HardwareInfo", new_callable=PropertyMock()
        )
        mock_hardware_info.return_value = MockHardwareInfo()

        _modbus_client = ModbusClient(tcp=mock_modbus_tcp_client, serial=mock_modbus_tcp_client)
        _neuron: Neuron = Neuron(config=config, modbus_client=_modbus_client)

        await _neuron.read_boards()

        logs: list = [record.getMessage() for record in caplog.records]

        assert "No board on SPI 1" in logs
        assert "No board on SPI 2" in logs
        assert "No board on SPI 3" in logs
