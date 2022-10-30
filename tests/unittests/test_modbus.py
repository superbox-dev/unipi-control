import asyncio
from unittest.mock import AsyncMock
from unittest.mock import PropertyMock

import pytest
from _pytest.logging import LogCaptureFixture  # pylint: disable=import-private-name
from pytest_mock import MockerFixture

from superbox_utils.core.exception import UnexpectedException
from unipi_control.config import Config
from unipi_control.config import HardwareType
from unipi_control.modbus import ModbusCacheData
from unipi_control.modbus import ModbusClient
from unipi_control.neuron import Neuron
from unittests.conftest import ConfigLoader
from unittests.conftest import MockHardwareInfo
from unittests.conftest_data import CONFIG_CONTENT
from unittests.conftest_data import EXTENSION_HARDWARE_DATA_CONTENT
from unittests.conftest_data import HARDWARE_DATA_CONTENT


class TestUnhappyPathModbus:
    @pytest.mark.parametrize(
        "_config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    def test_modbus_exceptions(self, _config_loader: ConfigLoader, _neuron: Neuron):
        assert isinstance(_neuron.modbus_cache_data, ModbusCacheData)

        with pytest.raises(UnexpectedException) as error:
            _neuron.modbus_cache_data.get_register(index=3, address=0, unit=1)

        assert str(error.value) == "Modbus error on address 2 (unit: 1)"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "_config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    async def test_timeout_exceptions(
        self,
        mocker: MockerFixture,
        _config_loader: ConfigLoader,
        caplog: LogCaptureFixture,
    ):
        config: Config = _config_loader.get_config()

        mock_modbus_tcp_client: AsyncMock = AsyncMock()
        mock_modbus_tcp_client.read_input_registers.side_effect = asyncio.exceptions.TimeoutError

        mock_hardware_info: PropertyMock = mocker.patch(
            "unipi_control.config.HardwareInfo", new_callable=PropertyMock()
        )
        mock_hardware_info.return_value = MockHardwareInfo()

        _modbus_client = ModbusClient(tcp=mock_modbus_tcp_client, serial=mock_modbus_tcp_client)
        _neuron: Neuron = Neuron(config=config, modbus_client=_modbus_client)

        await _neuron.modbus_cache_data.scan([HardwareType.NEURON])

        logs: list = [record.getMessage() for record in caplog.records]

        assert "[MODBUS] Timeout on: {'address': 0, 'count': 2, 'slave': 0}" in logs
        assert "[MODBUS] Timeout on: {'address': 20, 'count': 1, 'slave': 0}" in logs
        assert "[MODBUS] Timeout on: {'address': 100, 'count': 2, 'slave': 0}" in logs
        assert "[MODBUS] Timeout on: {'address': 200, 'count': 2, 'slave': 0}" in logs
