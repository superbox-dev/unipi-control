import asyncio
from asyncio import Task
from contextlib import AsyncExitStack
from typing import Iterator
from typing import List
from typing import Set
from unittest.mock import AsyncMock

import pytest
from _pytest.logging import LogCaptureFixture  # pylint: disable=import-private-name
from asyncio_mqtt import Client

from unipi_control.modbus import ModbusClient
from unipi_control.mqtt.discovery.sensors import HassSensorsDiscovery
from unipi_control.mqtt.discovery.sensors import HassSensorsMqttPlugin
from unipi_control.neuron import Neuron
from unittests.conftest import ConfigLoader
from unittests.conftest_data import CONFIG_CONTENT
from unittests.conftest_data import EXTENSION_HARDWARE_DATA_CONTENT
from unittests.conftest_data import HARDWARE_DATA_CONTENT


class TestHappyPathHassSensorsMqttPlugin:
    @pytest.mark.parametrize(
        "_config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    def test_init_tasks(
        self,
        _modbus_client: ModbusClient,
        _config_loader: ConfigLoader,
        _neuron: Neuron,
        caplog: LogCaptureFixture,
    ):
        async def run():
            mock_mqtt_client: AsyncMock = AsyncMock(spec=Client)
            plugin: HassSensorsMqttPlugin = HassSensorsMqttPlugin(neuron=_neuron, mqtt_client=mock_mqtt_client)

            async with AsyncExitStack() as stack:
                tasks: Set[Task] = set()

                await stack.enter_async_context(mock_mqtt_client)
                await plugin.init_tasks(tasks)
                await asyncio.gather(*tasks)

                for task in tasks:
                    assert task.done() is True

            logs: list = [record.getMessage() for record in caplog.records]
            # TODO: add all logs
            assert (
                '[MQTT] [homeassistant/sensor/mocked_unipi/voltage_1/config] Publishing message: {"name": "MOCKED_UNIPI: Voltage 1", "unique_id": "mocked_unipi_voltage_1", "state_topic": "mocked_unipi/meter/voltage_1/get", "qos": 2, "device": {"name": "Eastron SDM120M: Workspace", "identifiers": "Eastron SDM120M: Workspace", "model": "SDM120M", "sw_version": "", "manufacturer": "Eastron", "suggested_area": "Workspace"}, "device_class": "voltage", "state_class": "measurement", "unit_of_measurement": "V"}'
                in logs
            )
            assert (
                '[MQTT] [homeassistant/sensor/mocked_unipi/current_1/config] Publishing message: {"name": "MOCKED_UNIPI: Current 1", "unique_id": "mocked_unipi_current_1", "state_topic": "mocked_unipi/meter/current_1/get", "qos": 2, "device": {"name": "Eastron SDM120M: Workspace", "identifiers": "Eastron SDM120M: Workspace", "model": "SDM120M", "sw_version": "", "manufacturer": "Eastron", "suggested_area": "Workspace"}, "device_class": "current", "state_class": "measurement", "unit_of_measurement": "A"}'
                in logs
            )

        loop = asyncio.new_event_loop()
        loop.run_until_complete(run())

    @pytest.mark.parametrize(
        "_config_loader, expected",
        [
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                [
                    {
                        "message": {
                            "name": "MOCKED_UNIPI: Voltage 1",
                            "unique_id": "mocked_unipi_voltage_1",
                            "state_topic": "mocked_unipi/meter/voltage_1/get",
                            "qos": 2,
                            "device": {
                                "name": "Eastron SDM120M: Workspace",
                                "identifiers": "Eastron SDM120M: Workspace",
                                "model": "SDM120M",
                                "sw_version": "",
                                "manufacturer": "Eastron",
                                "suggested_area": "Workspace",
                            },
                            "device_class": "voltage",
                            "state_class": "measurement",
                            "unit_of_measurement": "V",
                        },
                        "topic": "homeassistant/sensor/mocked_unipi/voltage_1/config",
                    },
                    {
                        "message": {
                            "name": "MOCKED_UNIPI: Current 1",
                            "unique_id": "mocked_unipi_current_1",
                            "state_topic": "mocked_unipi/meter/current_1/get",
                            "qos": 2,
                            "device": {
                                "name": "Eastron SDM120M: Workspace",
                                "identifiers": "Eastron SDM120M: Workspace",
                                "model": "SDM120M",
                                "sw_version": "",
                                "manufacturer": "Eastron",
                                "suggested_area": "Workspace",
                            },
                            "device_class": "current",
                            "state_class": "measurement",
                            "unit_of_measurement": "A",
                        },
                        "topic": "homeassistant/sensor/mocked_unipi/current_1/config",
                    },
                ],
            ),
        ],
        indirect=["_config_loader"],
    )
    def test_discovery_message(
        self,
        _modbus_client: ModbusClient,
        _config_loader: ConfigLoader,
        _neuron: Neuron,
        expected: List[dict],
    ):
        mock_mqtt_client: AsyncMock = AsyncMock(spec=Client)
        plugin: HassSensorsMqttPlugin = HassSensorsMqttPlugin(neuron=_neuron, mqtt_client=mock_mqtt_client)
        features: Iterator = _neuron.features.by_feature_types(HassSensorsDiscovery.publish_feature_types)

        for index, feature in enumerate(features):
            topic, message = plugin._hass._get_discovery(feature)  # pylint: disable=protected-access

            if index + 1 > len(expected):
                break

            assert message == expected[index]["message"]
            assert topic == expected[index]["topic"]
