import asyncio
from asyncio import Task
from contextlib import AsyncExitStack
from typing import List
from typing import Set
from unittest.mock import AsyncMock

import pytest
from _pytest.logging import LogCaptureFixture  # pylint: disable=import-private-name
from asyncio_mqtt import Client

from unipi_control.config import COVER_TYPES
from unipi_control.integrations.covers import CoverMap
from unipi_control.modbus import ModbusClient
from unipi_control.mqtt.discovery.covers import HassCoversMqttPlugin
from unipi_control.neuron import Neuron
from unittests.conftest import ConfigLoader
from unittests.conftest_data import CONFIG_CONTENT
from unittests.conftest_data import EXTENSION_HARDWARE_DATA_CONTENT
from unittests.conftest_data import HARDWARE_DATA_CONTENT


class TestHappyPathHassCoversMqttPlugin:
    @pytest.mark.parametrize(
        "_config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    def test_init_tasks(
        self,
        _modbus_client: ModbusClient,
        _config_loader: ConfigLoader,
        _neuron: Neuron,
        _covers: CoverMap,
        caplog: LogCaptureFixture,
    ):
        async def run():
            mock_mqtt_client: AsyncMock = AsyncMock(spec=Client)
            plugin: HassCoversMqttPlugin = HassCoversMqttPlugin(
                neuron=_neuron, mqtt_client=mock_mqtt_client, covers=_covers
            )

            async with AsyncExitStack() as stack:
                tasks: Set[Task] = set()

                await stack.enter_async_context(mock_mqtt_client)

                plugin_tasks = await plugin.init_tasks()
                tasks.update(plugin_tasks)

                await asyncio.gather(*tasks)

                for task in tasks:
                    assert task.done() is True

            logs: list = [record.getMessage() for record in caplog.records]
            assert (
                '[MQTT] [homeassistant/cover/mocked_blind_topic_name/config] Publishing message: {"name": "MOCKED_FRIENDLY_NAME - BLIND", "unique_id": "blind_mocked_blind_topic_name", "command_topic": "mocked_unipi/mocked_blind_topic_name/cover/blind/set", "state_topic": "mocked_unipi/mocked_blind_topic_name/cover/blind/state", "qos": 2, "optimistic": false, "device": {"name": "MOCKED_UNIPI", "identifiers": "MOCKED_UNIPI", "model": "MOCKED_NAME MOCKED_MODEL", "manufacturer": "Unipi technology"}, "object_id": "mocked_blind_topic_name", "position_topic": "mocked_unipi/mocked_blind_topic_name/cover/blind/position", "set_position_topic": "mocked_unipi/mocked_blind_topic_name/cover/blind/position/set", "tilt_status_topic": "mocked_unipi/mocked_blind_topic_name/cover/blind/tilt", "tilt_command_topic": "mocked_unipi/mocked_blind_topic_name/cover/blind/tilt/set"}'
                in logs
            )
            assert (
                '[MQTT] [homeassistant/cover/mocked_roller_shutter_topic_name/config] Publishing message: {"name": "MOCKED_FRIENDLY_NAME - ROLLER SHUTTER", "unique_id": "roller_shutter_mocked_roller_shutter_topic_name", "command_topic": "mocked_unipi/mocked_roller_shutter_topic_name/cover/roller_shutter/set", "state_topic": "mocked_unipi/mocked_roller_shutter_topic_name/cover/roller_shutter/state", "qos": 2, "optimistic": false, "device": {"name": "MOCKED_UNIPI: MOCKED AREA", "identifiers": "MOCKED_UNIPI: MOCKED AREA", "model": "MOCKED_NAME MOCKED_MODEL", "manufacturer": "Unipi technology", "suggested_area": "MOCKED AREA"}, "object_id": "mocked_roller_shutter_topic_name"}'
                in logs
            )
            assert len(logs) == 2

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
                            "name": "MOCKED_FRIENDLY_NAME - BLIND",
                            "unique_id": "blind_mocked_blind_topic_name",
                            "command_topic": "mocked_unipi/mocked_blind_topic_name/cover/blind/set",
                            "state_topic": "mocked_unipi/mocked_blind_topic_name/cover/blind/state",
                            "qos": 2,
                            "optimistic": False,
                            "device": {
                                "name": "MOCKED_UNIPI",
                                "identifiers": "MOCKED_UNIPI",
                                "model": "MOCKED_NAME MOCKED_MODEL",
                                "manufacturer": "Unipi technology",
                            },
                            "object_id": "mocked_blind_topic_name",
                            "position_topic": "mocked_unipi/mocked_blind_topic_name/cover/blind/position",
                            "set_position_topic": "mocked_unipi/mocked_blind_topic_name/cover/blind/position/set",
                            "tilt_status_topic": "mocked_unipi/mocked_blind_topic_name/cover/blind/tilt",
                            "tilt_command_topic": "mocked_unipi/mocked_blind_topic_name/cover/blind/tilt/set",
                        },
                        "topic": "homeassistant/cover/mocked_blind_topic_name/config",
                    },
                    {
                        "message": {
                            "name": "MOCKED_FRIENDLY_NAME - ROLLER SHUTTER",
                            "unique_id": "roller_shutter_mocked_roller_shutter_topic_name",
                            "command_topic": "mocked_unipi/mocked_roller_shutter_topic_name/cover/roller_shutter/set",
                            "state_topic": "mocked_unipi/mocked_roller_shutter_topic_name/cover/roller_shutter/state",
                            "qos": 2,
                            "optimistic": False,
                            "device": {
                                "name": "MOCKED_UNIPI: MOCKED AREA",
                                "identifiers": "MOCKED_UNIPI: MOCKED AREA",
                                "model": "MOCKED_NAME MOCKED_MODEL",
                                "manufacturer": "Unipi technology",
                                "suggested_area": "MOCKED AREA",
                            },
                            "object_id": "mocked_roller_shutter_topic_name",
                        },
                        "topic": "homeassistant/cover/mocked_roller_shutter_topic_name/config",
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
        _covers: CoverMap,
        expected: List[dict],
    ):
        mock_mqtt_client: AsyncMock = AsyncMock(spec=Client)
        plugin: HassCoversMqttPlugin = HassCoversMqttPlugin(
            neuron=_neuron, mqtt_client=mock_mqtt_client, covers=_covers
        )

        for index, cover in enumerate(_covers.by_cover_type(COVER_TYPES)):
            topic, message = plugin._hass._get_discovery(cover)  # pylint: disable=protected-access

            assert message == expected[index]["message"]
            assert topic == expected[index]["topic"]
