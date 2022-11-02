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
from unipi_control.mqtt.discovery.switches import HassSwitchesDiscoveryMixin
from unipi_control.mqtt.discovery.switches import HassSwitchesMqttPlugin
from unipi_control.neuron import Neuron
from unittests.conftest import ConfigLoader
from unittests.conftest_data import CONFIG_CONTENT
from unittests.conftest_data import EXTENSION_HARDWARE_DATA_CONTENT
from unittests.conftest_data import HARDWARE_DATA_CONTENT


class TestHappyPathHassSwitchesMqttPlugin:
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
            plugin: HassSwitchesMqttPlugin = HassSwitchesMqttPlugin(neuron=_neuron, mqtt_client=mock_mqtt_client)

            async with AsyncExitStack() as stack:
                tasks: Set[Task] = set()

                await stack.enter_async_context(mock_mqtt_client)
                await plugin.init_tasks(tasks)
                await asyncio.gather(*tasks)

                for task in tasks:
                    assert task.done() is True

            logs: list = [record.getMessage() for record in caplog.records]
            assert (
                '[MQTT] [homeassistant/switch/mocked_unipi/do_1_01/config] Publishing message: {"name": "MOCKED_UNIPI: Digital Output 1.01", "unique_id": "mocked_unipi_do_1_01", "command_topic": "mocked_unipi/relay/do_1_01/set", "state_topic": "mocked_unipi/relay/do_1_01/get", "qos": 2, "device": {"name": "MOCKED_UNIPI", "identifiers": "MOCKED_UNIPI", "model": "MOCKED_NAME MOCKED_MODEL", "sw_version": "0.0", "manufacturer": "Unipi technology"}}'
                in logs
            )
            assert (
                '[MQTT] [homeassistant/switch/mocked_unipi/do_1_02/config] Publishing message: {"name": "MOCKED_UNIPI: Digital Output 1.02", "unique_id": "mocked_unipi_do_1_02", "command_topic": "mocked_unipi/relay/do_1_02/set", "state_topic": "mocked_unipi/relay/do_1_02/get", "qos": 2, "device": {"name": "MOCKED_UNIPI", "identifiers": "MOCKED_UNIPI", "model": "MOCKED_NAME MOCKED_MODEL", "sw_version": "0.0", "manufacturer": "Unipi technology"}}'
                in logs
            )
            assert len(logs) == 28

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
                            "name": "MOCKED_FRIENDLY_NAME - RO_2_01",
                            "unique_id": "mocked_unipi_ro_2_01",
                            "command_topic": "mocked_unipi/relay/ro_2_01/set",
                            "state_topic": "mocked_unipi/relay/ro_2_01/get",
                            "qos": 2,
                            "device": {
                                "name": "MOCKED_UNIPI: MOCKED AREA 2",
                                "identifiers": "MOCKED_UNIPI: MOCKED AREA 2",
                                "model": "MOCKED_NAME MOCKED_MODEL",
                                "sw_version": "0.0",
                                "manufacturer": "Unipi technology",
                                "suggested_area": "MOCKED AREA 2",
                            },
                            "object_id": "mocked_id_ro_2_01",
                            "payload_on": "OFF",
                            "payload_off": "ON",
                        },
                        "topic": "homeassistant/switch/mocked_unipi/ro_2_01/config",
                    },
                    {
                        "message": {
                            "name": "MOCKED_FRIENDLY_NAME - RO_2_02",
                            "unique_id": "mocked_unipi_ro_2_02",
                            "command_topic": "mocked_unipi/relay/ro_2_02/set",
                            "state_topic": "mocked_unipi/relay/ro_2_02/get",
                            "qos": 2,
                            "device": {
                                "name": "MOCKED_UNIPI: MOCKED AREA 2",
                                "identifiers": "MOCKED_UNIPI: MOCKED AREA 2",
                                "model": "MOCKED_NAME MOCKED_MODEL",
                                "sw_version": "0.0",
                                "manufacturer": "Unipi technology",
                                "suggested_area": "MOCKED AREA 2",
                            },
                            "object_id": "mocked_id_ro_2_02",
                        },
                        "topic": "homeassistant/switch/mocked_unipi/ro_2_02/config",
                    },
                ],
            ),
        ],
        indirect=["_config_loader"],
    )
    def test_discovery_message(
        self, _modbus_client: ModbusClient, _config_loader: ConfigLoader, _neuron: Neuron, expected: List[dict]
    ):
        mock_mqtt_client: AsyncMock = AsyncMock(spec=Client)
        plugin: HassSwitchesMqttPlugin = HassSwitchesMqttPlugin(neuron=_neuron, mqtt_client=mock_mqtt_client)
        features: Iterator = _neuron.features.by_feature_types(HassSwitchesDiscoveryMixin.publish_feature_types)

        for index, feature in enumerate(features):
            topic, message = plugin._hass._get_discovery(feature)  # pylint: disable=protected-access

            if index + 1 > len(expected):
                break

            assert message == expected[index]["message"]
            assert topic == expected[index]["topic"]
