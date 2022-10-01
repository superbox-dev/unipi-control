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
from unipi_control.config import COVER_TYPES
from unipi_control.covers import CoverMap
from unipi_control.neuron import Neuron
from unipi_control.plugins.hass.covers import HassCoversMqttPlugin


class TestHappyPathHassSwitchesCoversMqttPlugin:
    @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
    def test_init_tasks(
        self,
        modbus_client,
        config_loader: ConfigLoader,
        neuron: Neuron,
        covers: CoverMap,
        caplog: LogCaptureFixture,
    ):
        async def run():
            mock_mqtt_client: AsyncMock = AsyncMock(spec=Client)

            plugin = HassCoversMqttPlugin(neuron=neuron, mqtt_client=mock_mqtt_client, covers=covers)

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
                '[MQTT] [homeassistant/cover/mocked_blind_topic_name/config] Publishing message: {"name": "MOCKED_FRIENDLY_NAME - BLIND", "unique_id": "blind_mocked_blind_topic_name", "command_topic": "mocked_unipi/mocked_blind_topic_name/cover/blind/set", "state_topic": "mocked_unipi/mocked_blind_topic_name/cover/blind/state", "qos": 2, "optimistic": false, "device": {"name": "mocked_unipi", "identifiers": "mocked_unipi", "model": "MOCKED_NAME MOCKED_MODEL", "manufacturer": "Unipi technology"}, "object_id": "MOCKED_ID_COVER_BLIND", "position_topic": "mocked_unipi/mocked_blind_topic_name/cover/blind/position", "set_position_topic": "mocked_unipi/mocked_blind_topic_name/cover/blind/position/set", "tilt_status_topic": "mocked_unipi/mocked_blind_topic_name/cover/blind/tilt", "tilt_command_topic": "mocked_unipi/mocked_blind_topic_name/cover/blind/tilt/set"}'
                in logs
            )
            assert (
                '[MQTT] [homeassistant/cover/mocked_roller_shutter_topic_name/config] Publishing message: {"name": "MOCKED_FRIENDLY_NAME - ROLLER SHUTTER", "unique_id": "roller_shutter_mocked_roller_shutter_topic_name", "command_topic": "mocked_unipi/mocked_roller_shutter_topic_name/cover/roller_shutter/set", "state_topic": "mocked_unipi/mocked_roller_shutter_topic_name/cover/roller_shutter/state", "qos": 2, "optimistic": false, "device": {"name": "mocked_unipi: MOCKED AREA", "identifiers": "mocked_unipi: MOCKED AREA", "model": "MOCKED_NAME MOCKED_MODEL", "manufacturer": "Unipi technology", "suggested_area": "MOCKED AREA"}}'
                in logs
            )
            assert 2 == len(logs)

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
                            "name": "MOCKED_FRIENDLY_NAME - BLIND",
                            "unique_id": "blind_mocked_blind_topic_name",
                            "command_topic": "mocked_unipi/mocked_blind_topic_name/cover/blind/set",
                            "state_topic": "mocked_unipi/mocked_blind_topic_name/cover/blind/state",
                            "qos": 2,
                            "optimistic": False,
                            "device": {
                                "name": "mocked_unipi",
                                "identifiers": "mocked_unipi",
                                "model": "MOCKED_NAME MOCKED_MODEL",
                                "manufacturer": "Unipi technology",
                            },
                            "object_id": "MOCKED_ID_COVER_BLIND",
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
                                "name": "mocked_unipi: MOCKED AREA",
                                "identifiers": "mocked_unipi: MOCKED AREA",
                                "model": "MOCKED_NAME MOCKED_MODEL",
                                "manufacturer": "Unipi technology",
                                "suggested_area": "MOCKED AREA",
                            },
                        },
                        "topic": "homeassistant/cover/mocked_roller_shutter_topic_name/config",
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
        covers: CoverMap,
        caplog: LogCaptureFixture,
        expected: List[dict],
    ):
        mock_mqtt_client: AsyncMock = AsyncMock(spec=Client)

        plugin = HassCoversMqttPlugin(neuron=neuron, mqtt_client=mock_mqtt_client, covers=covers)

        for index, cover in enumerate(covers.by_cover_type(COVER_TYPES)):
            topic, message = plugin._hass._get_discovery(cover)

            assert expected[index]["message"] == message
            assert expected[index]["topic"] == topic
