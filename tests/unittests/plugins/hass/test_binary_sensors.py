import asyncio
from asyncio import Task
from contextlib import AsyncExitStack
from typing import List
from typing import Set
from unittest.mock import AsyncMock

import pytest
from _pytest.logging import LogCaptureFixture
from asyncio_mqtt import Client

from conftest import ConfigLoader
from conftest_data import CONFIG_CONTENT
from conftest_data import HARDWARE_DATA_CONTENT
from unipi_control.neuron import Neuron
from unipi_control.plugins.hass.binary_sensors import HassBinarySensorsDiscovery
from unipi_control.plugins.hass.binary_sensors import HassBinarySensorsMqttPlugin


class TestHappyPathHassBinarySensorsMqttPlugin:
    @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
    def test_init_tasks(
        self,
        modbus_client,
        config_loader: ConfigLoader,
        neuron: Neuron,
        caplog: LogCaptureFixture,
    ):
        async def run():
            mock_mqtt_client: AsyncMock = AsyncMock(spec=Client)

            plugin = HassBinarySensorsMqttPlugin(neuron=neuron, mqtt_client=mock_mqtt_client)

            async with AsyncExitStack() as stack:
                tasks: Set[Task] = set()

                await stack.enter_async_context(mock_mqtt_client)

                plugin_tasks = await plugin.init_tasks()
                tasks.update(plugin_tasks)

                await asyncio.gather(*tasks)

                for task in tasks:
                    assert True is task.done()

            logs: list = [record.getMessage() for record in caplog.records]

            assert (
                '[MQTT] [homeassistant/binary_sensor/mocked_unipi/di_3_01/config] Publishing message: {"name": "MOCKED_FRIENDLY_NAME - 3_01", "unique_id": "mocked_unipi_di_3_01", "state_topic": "mocked_unipi/input/di_3_01/get", "qos": 2, "device": {"name": "mocked_unipi: MOCKED AREA 1", "identifiers": "mocked_unipi: MOCKED AREA 1", "model": "MOCKED_NAME MOCKED_MODEL", "sw_version": "0.0", "manufacturer": "Unipi technology", "suggested_area": "MOCKED AREA 1"}}'
                in logs
            )
            assert (
                '[MQTT] [homeassistant/binary_sensor/mocked_unipi/di_3_02/config] Publishing message: {"name": "MOCKED_FRIENDLY_NAME - 3_02", "unique_id": "mocked_unipi_di_3_02", "state_topic": "mocked_unipi/input/di_3_02/get", "qos": 2, "device": {"name": "mocked_unipi: MOCKED AREA 1", "identifiers": "mocked_unipi: MOCKED AREA 1", "model": "MOCKED_NAME MOCKED_MODEL", "sw_version": "0.0", "manufacturer": "Unipi technology", "suggested_area": "MOCKED AREA 1"}}'
                in logs
            )

        loop = asyncio.new_event_loop()
        loop.run_until_complete(run())

    @pytest.mark.parametrize(
        "config_loader, expected",
        [
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT),
                [
                    {
                        "message": {
                            "name": "MOCKED_FRIENDLY_NAME - 1_01",
                            "unique_id": "mocked_unipi_di_1_01",
                            "state_topic": "mocked_unipi/input/di_1_01/get",
                            "qos": 2,
                            "device": {
                                "name": "mocked_unipi: MOCKED AREA 1",
                                "identifiers": "mocked_unipi: MOCKED AREA 1",
                                "model": "MOCKED_NAME MOCKED_MODEL",
                                "sw_version": "0.0",
                                "manufacturer": "Unipi technology",
                                "suggested_area": "MOCKED AREA 1",
                            },
                            "object_id": "MOCKED_ID_1_01",
                            "payload_on": "OFF",
                            "payload_off": "ON",
                        },
                        "topic": "homeassistant/binary_sensor/mocked_unipi/di_1_01/config",
                    },
                    {
                        "message": {
                            "name": "MOCKED_FRIENDLY_NAME - 1_02",
                            "unique_id": "mocked_unipi_di_1_02",
                            "state_topic": "mocked_unipi/input/di_1_02/get",
                            "qos": 2,
                            "device": {
                                "name": "mocked_unipi: MOCKED AREA 2",
                                "identifiers": "mocked_unipi: MOCKED AREA 2",
                                "model": "MOCKED_NAME MOCKED_MODEL",
                                "sw_version": "0.0",
                                "manufacturer": "Unipi technology",
                                "suggested_area": "MOCKED AREA 2",
                            },
                            "object_id": "MOCKED_ID_1_02",
                        },
                        "topic": "homeassistant/binary_sensor/mocked_unipi/di_1_02/config",
                    },
                ],
            ),
        ],
        indirect=["config_loader"],
    )
    def test_discovery_message(
        self,
        modbus_client,
        config_loader: ConfigLoader,
        neuron: Neuron,
        caplog: LogCaptureFixture,
        expected: List[dict],
    ):
        mock_mqtt_client: AsyncMock = AsyncMock(spec=Client)

        plugin = HassBinarySensorsMqttPlugin(neuron=neuron, mqtt_client=mock_mqtt_client)

        features = neuron.features.by_feature_type(HassBinarySensorsDiscovery.publish_feature_types)

        for index, feature in enumerate(features):
            topic, message = plugin._hass._get_discovery(feature)

            if index + 1 > len(expected):
                break

            assert expected[index]["message"] == message
            assert expected[index]["topic"] == topic
