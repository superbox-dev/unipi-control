"""Integration tests for unipi-config-backup cli command."""
from typing import Dict
from typing import List
from unittest.mock import AsyncMock
from unittest.mock import PropertyMock

import pytest
from _pytest.logging import LogCaptureFixture  # pylint: disable=import-private-name
from pytest_mock import MockerFixture

from tests.conftest import ConfigLoader
from tests.conftest import MockHardwareInfo
from tests.conftest_data import CONFIG_CONTENT
from tests.conftest_data import EXTENSION_HARDWARE_DATA_CONTENT
from tests.conftest_data import HARDWARE_DATA_CONTENT
from unipi_control.helpers.typing import ModbusClient
from unipi_control.unipi_control import main


class TestUnhappyPathUnipiControl:
    @pytest.mark.parametrize(
        "config_loader",
        [
            (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
        ],
        indirect=["config_loader"],
    )
    def test_hardware_is_not_supported(self, config_loader: ConfigLoader, caplog: LogCaptureFixture) -> None:
        """Test for hardware is not supported."""
        with pytest.raises(SystemExit) as error:
            main(["-c", config_loader.temp.as_posix()])

        logs: List[str] = [record.getMessage() for record in caplog.records]

        assert "[CONFIG] Hardware is not supported!" in logs
        assert error.value.code == 1

    @pytest.mark.parametrize(
        ("config_loader", "hardware_info"),
        [
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                {
                    "name": "MOCKED_NAME",
                    "model": "MOCKED_MODEL",
                    "version": "MOCKED_VERSION",
                    "serial": "MOCKED_SERIAL",
                },
            )
        ],
        indirect=["config_loader"],
    )
    def test_modbus_tcp_not_connected(
        self,
        config_loader: ConfigLoader,
        hardware_info: Dict[str, str],
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
    ) -> None:
        """Test for Modbus TCP is not connected."""
        mock_hardware_info: PropertyMock = mocker.patch("unipi_control.config.HardwareInfo", new_callable=PropertyMock)
        mock_hardware_info.return_value = MockHardwareInfo(**hardware_info)

        mock_modbus_client_tcp: AsyncMock = mocker.patch.object(ModbusClient, "tcp", new_callable=AsyncMock)
        mock_modbus_client_tcp.params.host = "MOCKED_MODBUS_HOST"
        mock_modbus_client_tcp.params.port = "502"
        mock_modbus_client_tcp.connected = False

        with pytest.raises(SystemExit) as error:
            main(["-c", config_loader.temp.as_posix()])

        logs: List[str] = [record.getMessage() for record in caplog.records]

        assert "[MODBUS] TCP client can't connect to MOCKED_MODBUS_HOST:502" in logs
        assert error.value.code == 1

    @pytest.mark.parametrize(
        ("config_loader", "hardware_info"),
        [
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                {
                    "name": "MOCKED_NAME",
                    "model": "MOCKED_MODEL",
                    "version": "MOCKED_VERSION",
                    "serial": "MOCKED_SERIAL",
                },
            )
        ],
        indirect=["config_loader"],
    )
    def test_modbus_serial_not_connected(
        self,
        config_loader: ConfigLoader,
        hardware_info: Dict[str, str],
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
    ) -> None:
        """Test for Modbus RTU is not connected."""
        mock_hardware_info: PropertyMock = mocker.patch("unipi_control.config.HardwareInfo", new_callable=PropertyMock)
        mock_hardware_info.return_value = MockHardwareInfo(**hardware_info)

        mock_modbus_client_tcp: AsyncMock = mocker.patch.object(ModbusClient, "tcp", new_callable=AsyncMock)
        mock_modbus_client_tcp.params.host = "MOCKED_MODBUS_HOST"
        mock_modbus_client_tcp.params.port = "502"
        mock_modbus_client_tcp.connected = True

        mock_modbus_client_serial: AsyncMock = mocker.patch.object(ModbusClient, "serial", new_callable=AsyncMock)
        mock_modbus_client_serial.params.port = "/dev/MOCKED"
        mock_modbus_client_serial.connected = False

        with pytest.raises(SystemExit) as error:
            main(["-c", config_loader.temp.as_posix()])

        logs: List[str] = [record.getMessage() for record in caplog.records]

        assert "[MODBUS] Serial client can't connect to /dev/MOCKED" in logs
        assert error.value.code == 1
