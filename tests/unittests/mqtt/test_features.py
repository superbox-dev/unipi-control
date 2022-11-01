import asyncio
from asyncio import Task
from contextlib import AsyncExitStack
from typing import Set
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import PropertyMock
from unittest.mock import call

import pytest
from _pytest.logging import LogCaptureFixture  # pylint: disable=import-private-name
from asyncio_mqtt import Client
from pytest_mock import MockerFixture

from unipi_control.modbus import ModbusClient
from unipi_control.mqtt.features import MeterFeaturesMqttPlugin
from unipi_control.mqtt.features import NeuronFeaturesMqttPlugin
from unipi_control.neuron import Neuron
from unittests.conftest import ConfigLoader
from unittests.conftest import MockMQTTMessages
from unittests.conftest_data import CONFIG_CONTENT
from unittests.conftest_data import EXTENSION_HARDWARE_DATA_CONTENT
from unittests.conftest_data import HARDWARE_DATA_CONTENT


class TestHappyPathNeuronFeaturesMqttPlugin:
    @pytest.mark.parametrize(
        "_config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    def test_init_tasks(
        self,
        mocker: MockerFixture,
        _modbus_client: ModbusClient,
        _config_loader: ConfigLoader,
        _neuron: Neuron,
        caplog: LogCaptureFixture,
    ):
        async def run():
            mock_mqtt_messages: AsyncMock = AsyncMock()
            mock_mqtt_messages.__aenter__.return_value = MockMQTTMessages([b"""ON""", b"""OFF"""])

            mock_mqtt_client: AsyncMock = AsyncMock(spec=Client)
            mock_mqtt_client.filtered_messages.return_value = mock_mqtt_messages

            mock_modbus_cache_data_scan: MagicMock = mocker.patch("unipi_control.modbus.ModbusCacheData.scan")

            NeuronFeaturesMqttPlugin.PUBLISH_RUNNING = PropertyMock(side_effect=[True, False])
            NeuronFeaturesMqttPlugin.scan_interval = 25e-3

            async with AsyncExitStack() as stack:
                tasks: Set[Task] = set()

                await stack.enter_async_context(mock_mqtt_client)
                await NeuronFeaturesMqttPlugin(_neuron, mock_mqtt_client).init_tasks(stack, tasks)
                await asyncio.gather(*tasks)

                for task in tasks:
                    assert task.done() is True

            logs: list = [record.getMessage() for record in caplog.records]

            assert mock_modbus_cache_data_scan.mock_calls == [call("tcp", ["Neuron"])]

            for feature_do in range(1, 4):
                assert f"[MQTT] Subscribe topic mocked_unipi/relay/do_1_{feature_do:02d}/set" in logs

            for bord in range(2, 3):
                for feature_ro in range(1, 4):
                    assert f"[MQTT] Subscribe topic mocked_unipi/relay/ro_{bord}_{feature_ro:02d}/set" in logs

            assert "[MQTT] [mocked_unipi/relay/do_1_01/set] Subscribe message: OFF" in logs
            assert "[MQTT] [mocked_unipi/relay/do_1_01/set] Subscribe message: ON" in logs
            assert "[MQTT] [mocked_unipi/relay/ro_2_01/get] Publishing message: OFF" in logs
            assert "[MQTT] [mocked_unipi/relay/ro_2_13/get] Publishing message: OFF" in logs

        loop = asyncio.new_event_loop()
        loop.run_until_complete(run())


class TestHappyPathMeterFeaturesMqttPlugin:
    @pytest.mark.parametrize(
        "_config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    def test_init_tasks(
        self,
        mocker: MockerFixture,
        _modbus_client: ModbusClient,
        _config_loader: ConfigLoader,
        _neuron: Neuron,
        caplog: LogCaptureFixture,
    ):
        async def run():
            mock_mqtt_client: AsyncMock = AsyncMock(spec=Client)
            mock_modbus_cache_data_scan: MagicMock = mocker.patch("unipi_control.modbus.ModbusCacheData.scan")

            MeterFeaturesMqttPlugin.PUBLISH_RUNNING = PropertyMock(side_effect=[True, False])
            MeterFeaturesMqttPlugin.scan_interval = 25e-3

            async with AsyncExitStack() as stack:
                tasks: Set[Task] = set()

                await stack.enter_async_context(mock_mqtt_client)
                await MeterFeaturesMqttPlugin(_neuron, mock_mqtt_client).init_tasks(tasks)
                await asyncio.gather(*tasks)

                for task in tasks:
                    assert task.done() is True

            logs: list = [record.getMessage() for record in caplog.records]

            assert mock_modbus_cache_data_scan.mock_calls == [call("serial", ["Extension"])]

            assert "[MQTT] [mocked_unipi/meter/voltage_1/get] Publishing message: 235.2" in logs
            assert "[MQTT] [mocked_unipi/meter/current_1/get] Publishing message: 0.29" in logs
            assert "[MQTT] [mocked_unipi/meter/active_power_1/get] Publishing message: 37.7" in logs
            assert "[MQTT] [mocked_unipi/meter/apparent_power_1/get] Publishing message: 41.12" in logs
            assert "[MQTT] [mocked_unipi/meter/reactive_power_1/get] Publishing message: -16.3" in logs
            assert "[MQTT] [mocked_unipi/meter/power_factor_1/get] Publishing message: 0.92" in logs
            assert "[MQTT] [mocked_unipi/meter/phase_angle_1/get] Publishing message: 0.0" in logs
            assert "[MQTT] [mocked_unipi/meter/frequency_1/get] Publishing message: 50.04" in logs
            assert "[MQTT] [mocked_unipi/meter/import_active_energy_1/get] Publishing message: 4.42" in logs
            assert "[MQTT] [mocked_unipi/meter/export_active_energy_1/get] Publishing message: 0.0" in logs
            assert "[MQTT] [mocked_unipi/meter/imported_reactive_energy_1/get] Publishing message: 0.3" in logs
            assert "[MQTT] [mocked_unipi/meter/exported_reactive_energy_1/get] Publishing message: 2.74" in logs
            assert "[MQTT] [mocked_unipi/meter/total_system_power_demand_1/get] Publishing message: 37.27" in logs
            assert (
                "[MQTT] [mocked_unipi/meter/maximum_total_system_power_demand_1/get] Publishing message: 81.04" in logs
            )
            assert "[MQTT] [mocked_unipi/meter/import_system_power_demand_1/get] Publishing message: 37.27" in logs
            assert (
                "[MQTT] [mocked_unipi/meter/maximum_import_system_power_demand_1/get] Publishing message: 81.04" in logs
            )
            assert "[MQTT] [mocked_unipi/meter/export_system_power_demand_1/get] Publishing message: 0.0" in logs
            assert (
                "[MQTT] [mocked_unipi/meter/maximum_export_system_power_demand_1/get] Publishing message: 0.03" in logs
            )
            assert "[MQTT] [mocked_unipi/meter/current_demand_1/get] Publishing message: 0.29" in logs
            assert "[MQTT] [mocked_unipi/meter/maximum_current_demand_1/get] Publishing message: 0.71" in logs
            assert "[MQTT] [mocked_unipi/meter/total_active_energy_1/get] Publishing message: 4.42" in logs
            assert "[MQTT] [mocked_unipi/meter/total_reactive_energy_1/get] Publishing message: 3.03" in logs

        loop = asyncio.new_event_loop()
        loop.run_until_complete(run())
