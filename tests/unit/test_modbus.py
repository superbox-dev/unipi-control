"""Unit tests for modbus."""

import asyncio
from typing import Any
from typing import Callable
from typing import List
from unittest.mock import AsyncMock
from unittest.mock import PropertyMock

import pytest
from _pytest.logging import LogCaptureFixture  # pylint: disable=import-private-name
from pymodbus.exceptions import ModbusException
from pytest_mock import MockerFixture

from tests.conftest import ConfigLoader
from tests.conftest import MockHardwareInfo
from tests.conftest_data import CONFIG_CONTENT
from tests.conftest_data import EXTENSION_HARDWARE_DATA_CONTENT
from tests.conftest_data import HARDWARE_DATA_CONTENT
from unipi_control.config import Config
from unipi_control.config import HardwareType
from unipi_control.helpers.typing import ModbusClient
from unipi_control.neuron import Neuron


class TestUnhappyPathModbus:
    @pytest.mark.parametrize(
        "config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    def test_modbus_error(self, neuron: Neuron, caplog: LogCaptureFixture) -> None:
        """Test modbus error logging if read register failed."""
        neuron.modbus_cache_data.get_register(index=3, address=0, unit=1)
        logs: List[str] = [record.getMessage() for record in caplog.records]

        assert "[MODBUS] Error on address 0 (unit: 1)" in logs

    @pytest.mark.asyncio()
    @pytest.mark.parametrize(
        ("config_loader", "exception", "expected"),
        [
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                asyncio.exceptions.TimeoutError,
                [
                    "[MODBUS] Timeout on: {'address': 0, 'count': 2, 'slave': 0}",
                    "[MODBUS] Timeout on: {'address': 20, 'count': 1, 'slave': 0}",
                    "[MODBUS] Timeout on: {'address': 100, 'count': 2, 'slave': 0}",
                    "[MODBUS] Timeout on: {'address': 200, 'count': 2, 'slave': 0}",
                ],
            ),
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                ModbusException,
                [
                    "[MODBUS] Modbus Error: MOCKED ERROR",
                ],
            ),
        ],
        indirect=["config_loader"],
    )
    async def test_modbus_exceptions(
        self,
        mocker: MockerFixture,
        config_loader: ConfigLoader,
        exception: Callable[..., Any],
        expected: List[str],
        caplog: LogCaptureFixture,
    ) -> None:
        """Test modbus error logging if read register failed with exception."""
        config: Config = config_loader.get_config()

        mock_modbus_tcp_client: AsyncMock = AsyncMock()
        mock_modbus_tcp_client.read_input_registers.side_effect = exception("MOCKED ERROR")

        mock_hardware_info: PropertyMock = mocker.patch(
            "unipi_control.config.HardwareInfo", new_callable=PropertyMock()
        )
        mock_hardware_info.return_value = MockHardwareInfo()

        modbus_client = ModbusClient(tcp=mock_modbus_tcp_client, serial=mock_modbus_tcp_client)
        neuron: Neuron = Neuron(config=config, modbus_client=modbus_client)

        await neuron.modbus_cache_data.scan("tcp", hardware_types=[HardwareType.NEURON])

        logs: List[str] = [record.getMessage() for record in caplog.records]

        assert set(expected).issubset(logs)
