"""Unit tests MQTT for Home Assistant covers."""
import asyncio
from asyncio import Task
from contextlib import AsyncExitStack
from typing import List
from typing import Set
from unittest.mock import AsyncMock
from unittest.mock import PropertyMock

import pytest
from _pytest.logging import LogCaptureFixture  # pylint: disable=import-private-name
from asyncio_mqtt import Client
from pytest_mock import MockerFixture

from tests.conftest import MockMQTTMessages
from tests.conftest_data import EXTENSION_HARDWARE_DATA_CONTENT
from tests.conftest_data import HARDWARE_DATA_CONTENT
from tests.unit.mqtt.integrations.test_covers_data import CONFIG_CONTENT
from unipi_control.integrations.covers import Cover
from unipi_control.integrations.covers import CoverMap
from unipi_control.integrations.covers import CoverState
from unipi_control.mqtt.integrations.covers import CoversMqttPlugin


async def init_tasks(covers: CoverMap, mqtt_messages: List[MockMQTTMessages], subscribe_running: List[bool]) -> None:
    """Initialize Home Assistant covers.

    Parameters
    ----------
    covers: CoverMap
        A dictionary of grouped cover lists.
    mqtt_messages: list
        A list of mocked MQTT topic messages.
    subscribe_running: List[bool]
        List of running subscribe loops for mocked side effects.
    """
    covers.init()
    mock_mqtt_messages: AsyncMock = AsyncMock()
    mock_mqtt_messages.__aenter__.side_effect = mqtt_messages

    mock_mqtt_client: AsyncMock = AsyncMock(spec=Client)
    mock_mqtt_client.filtered_messages.return_value = mock_mqtt_messages

    CoversMqttPlugin.PUBLISH_RUNNING = PropertyMock(side_effect=[True, False])
    CoversMqttPlugin.SUBSCRIBE_RUNNING = PropertyMock(side_effect=subscribe_running)

    plugin: CoversMqttPlugin = CoversMqttPlugin(mqtt_client=mock_mqtt_client, covers=covers)

    async with AsyncExitStack() as stack:
        tasks: Set[Task] = set()

        await stack.enter_async_context(mock_mqtt_client)
        await plugin.init_tasks(stack, tasks)
        await asyncio.gather(*tasks)

        for task in tasks:
            assert task.done() is True


class TestHappyPathCoversMqttPlugin:
    @pytest.mark.asyncio()
    @pytest.mark.parametrize(
        ("config_loader", "mqtt_messages"),
        [
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                [
                    MockMQTTMessages([b"50"]),  # position
                    MockMQTTMessages([]),  # tilt
                    MockMQTTMessages([b"""OPEN"""]),  # command
                ],
            )
        ],
        indirect=["config_loader"],
    )
    async def test_open_cover_with_cancel_other_task(
        self,
        covers: CoverMap,
        mqtt_messages: List[MockMQTTMessages],
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
    ) -> None:
        """Test mqtt output after set cover command."""
        mock_open_cover = mocker.patch.object(Cover, "open_cover", new_callable=AsyncMock)
        mock_calibrate = mocker.patch.object(Cover, "calibrate", new_callable=AsyncMock)

        mock_set_position = mocker.patch.object(Cover, "set_position", new_callable=AsyncMock)
        mock_set_position.return_value = 10

        mocker.patch.object(Cover, "state_changed", new_callable=PropertyMock(return_value=True))
        mocker.patch.object(Cover, "state", new_callable=PropertyMock(return_value=CoverState.OPENING))

        # Disable endless waiting loop
        mocker.patch.object(Cover, "is_closing", new_callable=PropertyMock(return_value=False))

        await init_tasks(covers=covers, mqtt_messages=mqtt_messages, subscribe_running=[False])
        logs: List[str] = [record.getMessage() for record in caplog.records]

        assert "[CONFIG] 1 covers initialized." in logs
        assert "[MQTT] Subscribe topic mocked_unipi/mocked_blind_topic_name/cover/blind/position/set" in logs
        assert "[MQTT] Subscribe topic mocked_unipi/mocked_blind_topic_name/cover/blind/tilt/set" in logs
        assert "[MQTT] Subscribe topic mocked_unipi/mocked_blind_topic_name/cover/blind/set" in logs
        assert "[COVER] [mocked_unipi/mocked_blind_topic_name/cover/blind] [Worker] 1 task(s) canceled." in logs
        assert "[MQTT] [mocked_unipi/mocked_blind_topic_name/cover/blind/set] Subscribe message: OPEN" in logs
        assert "[MQTT] [mocked_unipi/mocked_blind_topic_name/cover/blind/position] Publishing message: 0" in logs
        assert "[MQTT] [mocked_unipi/mocked_blind_topic_name/cover/blind/tilt] Publishing message: 0" in logs
        assert "[MQTT] [mocked_unipi/mocked_blind_topic_name/cover/blind/state] Publishing message: opening" in logs

        mock_open_cover.assert_called_once()
        mock_calibrate.assert_called_once()

    @pytest.mark.asyncio()
    @pytest.mark.parametrize(
        ("config_loader", "mqtt_messages"),
        [
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                [
                    MockMQTTMessages([]),  # position
                    MockMQTTMessages([]),  # tilt
                    MockMQTTMessages([b"""CLOSE"""]),  # command
                ],
            )
        ],
        indirect=["config_loader"],
    )
    async def test_close_cover(
        self,
        covers: CoverMap,
        mqtt_messages: List[MockMQTTMessages],
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
    ) -> None:
        """Test mqtt output after set cover command."""
        mock_calibrate = mocker.patch.object(Cover, "calibrate", new_callable=AsyncMock)

        mock_close_cover = mocker.patch.object(Cover, "close_cover", new_callable=AsyncMock)
        mock_close_cover.return_value = 10

        mocker.patch.object(Cover, "state_changed", new_callable=PropertyMock(return_value=True))
        mocker.patch.object(Cover, "state", new_callable=PropertyMock(return_value=CoverState.CLOSING))

        await init_tasks(covers=covers, mqtt_messages=mqtt_messages, subscribe_running=[False])
        logs: List[str] = [record.getMessage() for record in caplog.records]

        assert "[CONFIG] 1 covers initialized." in logs
        assert "[MQTT] Subscribe topic mocked_unipi/mocked_blind_topic_name/cover/blind/position/set" in logs
        assert "[MQTT] Subscribe topic mocked_unipi/mocked_blind_topic_name/cover/blind/tilt/set" in logs
        assert "[MQTT] Subscribe topic mocked_unipi/mocked_blind_topic_name/cover/blind/set" in logs
        assert "[MQTT] [mocked_unipi/mocked_blind_topic_name/cover/blind/set] Subscribe message: CLOSE" in logs
        assert "[MQTT] [mocked_unipi/mocked_blind_topic_name/cover/blind/position] Publishing message: 0" in logs
        assert "[MQTT] [mocked_unipi/mocked_blind_topic_name/cover/blind/tilt] Publishing message: 0" in logs
        assert "[MQTT] [mocked_unipi/mocked_blind_topic_name/cover/blind/state] Publishing message: closing" in logs

        mock_close_cover.assert_called_once()
        mock_calibrate.assert_called_once()

    @pytest.mark.asyncio()
    @pytest.mark.parametrize(
        ("config_loader", "mqtt_messages"),
        [
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                [
                    MockMQTTMessages([]),  # position
                    MockMQTTMessages([]),  # tilt
                    MockMQTTMessages([b"""STOP"""]),  # command
                ],
            )
        ],
        indirect=["config_loader"],
    )
    async def test_stop_cover(
        self,
        covers: CoverMap,
        mqtt_messages: List[MockMQTTMessages],
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
    ) -> None:
        """Test mqtt output after set cover command."""
        mock_stop_cover = mocker.patch.object(Cover, "stop_cover", new_callable=AsyncMock)
        mock_calibrate = mocker.patch.object(Cover, "calibrate", new_callable=AsyncMock)

        mocker.patch.object(Cover, "state_changed", new_callable=PropertyMock(return_value=True))
        mocker.patch.object(Cover, "state", new_callable=PropertyMock(return_value=CoverState.STOPPED))

        await init_tasks(covers=covers, mqtt_messages=mqtt_messages, subscribe_running=[False])
        logs: List[str] = [record.getMessage() for record in caplog.records]

        assert "[CONFIG] 1 covers initialized." in logs
        assert "[MQTT] Subscribe topic mocked_unipi/mocked_blind_topic_name/cover/blind/position/set" in logs
        assert "[MQTT] Subscribe topic mocked_unipi/mocked_blind_topic_name/cover/blind/tilt/set" in logs
        assert "[MQTT] Subscribe topic mocked_unipi/mocked_blind_topic_name/cover/blind/set" in logs
        assert "[MQTT] [mocked_unipi/mocked_blind_topic_name/cover/blind/set] Subscribe message: STOP" in logs
        assert "[MQTT] [mocked_unipi/mocked_blind_topic_name/cover/blind/position] Publishing message: 0" in logs
        assert "[MQTT] [mocked_unipi/mocked_blind_topic_name/cover/blind/tilt] Publishing message: 0" in logs
        assert "[MQTT] [mocked_unipi/mocked_blind_topic_name/cover/blind/state] Publishing message: stopped" in logs

        mock_stop_cover.assert_called_once()
        mock_calibrate.assert_called_once()

    @pytest.mark.asyncio()
    @pytest.mark.parametrize(
        ("config_loader", "mqtt_messages"),
        [
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                [
                    MockMQTTMessages([b"""50"""]),  # position
                    MockMQTTMessages([]),  # tilt
                    MockMQTTMessages([]),  # command
                ],
            )
        ],
        indirect=["config_loader"],
    )
    async def test_set_position(
        self,
        covers: CoverMap,
        mqtt_messages: List[MockMQTTMessages],
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
    ) -> None:
        """Test mqtt output after set cover position."""
        mock_set_position = mocker.patch.object(Cover, "set_position", new_callable=AsyncMock)
        mock_set_position.return_value = 10

        mocker.patch.object(Cover, "state_changed", new_callable=PropertyMock(return_value=True))
        mocker.patch.object(Cover, "state", new_callable=PropertyMock(return_value=CoverState.CLOSING))

        # Disable endless waiting loop
        mocker.patch.object(Cover, "is_closing", new_callable=PropertyMock(return_value=False))

        await init_tasks(covers=covers, mqtt_messages=mqtt_messages, subscribe_running=[True, False])
        logs: List[str] = [record.getMessage() for record in caplog.records]

        mock_set_position.assert_called_once_with(50)

        assert "[CONFIG] 1 covers initialized." in logs
        assert "[MQTT] Subscribe topic mocked_unipi/mocked_blind_topic_name/cover/blind/position/set" in logs
        assert "[MQTT] Subscribe topic mocked_unipi/mocked_blind_topic_name/cover/blind/tilt/set" in logs
        assert "[MQTT] Subscribe topic mocked_unipi/mocked_blind_topic_name/cover/blind/set" in logs
        assert "[MQTT] [mocked_unipi/mocked_blind_topic_name/cover/blind/position] Publishing message: 0" in logs
        assert "[MQTT] [mocked_unipi/mocked_blind_topic_name/cover/blind/tilt] Publishing message: 0" in logs
        assert "[MQTT] [mocked_unipi/mocked_blind_topic_name/cover/blind/state] Publishing message: closing" in logs
        assert "[COVER] [mocked_unipi/mocked_blind_topic_name/cover/blind] [Worker] 1 task(s) in queue." in logs
        assert "[MQTT] [mocked_unipi/mocked_blind_topic_name/cover/blind/position/set] Subscribe message: 50" in logs
        assert "[COVER] [mocked_unipi/mocked_blind_topic_name/cover/blind] [Worker] Cover runtime: 10 seconds." in logs

    @pytest.mark.asyncio()
    @pytest.mark.parametrize(
        ("config_loader", "mqtt_messages"),
        [
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                [
                    MockMQTTMessages([]),  # position
                    MockMQTTMessages([b"""50"""]),  # tilt
                    MockMQTTMessages([]),  # command
                ],
            )
        ],
        indirect=["config_loader"],
    )
    async def test_set_tilt(
        self,
        covers: CoverMap,
        mqtt_messages: List[MockMQTTMessages],
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
    ) -> None:
        """Test mqtt output after set cover tilt."""
        mock_set_tilt = mocker.patch.object(Cover, "set_tilt", new_callable=AsyncMock)
        mock_set_tilt.return_value = 0.25

        mocker.patch.object(Cover, "state_changed", new_callable=PropertyMock(return_value=True))
        mocker.patch.object(Cover, "state", new_callable=PropertyMock(return_value=CoverState.OPENING))

        # Disable endless waiting loop
        mocker.patch.object(Cover, "is_opening", new_callable=PropertyMock(return_value=False))

        await init_tasks(covers=covers, mqtt_messages=mqtt_messages, subscribe_running=[True, False])
        logs: List[str] = [record.getMessage() for record in caplog.records]

        mock_set_tilt.assert_called_once_with(50)

        assert "[CONFIG] 1 covers initialized." in logs
        assert "[MQTT] Subscribe topic mocked_unipi/mocked_blind_topic_name/cover/blind/position/set" in logs
        assert "[MQTT] Subscribe topic mocked_unipi/mocked_blind_topic_name/cover/blind/tilt/set" in logs
        assert "[MQTT] Subscribe topic mocked_unipi/mocked_blind_topic_name/cover/blind/set" in logs
        assert "[MQTT] [mocked_unipi/mocked_blind_topic_name/cover/blind/position] Publishing message: 0" in logs
        assert "[MQTT] [mocked_unipi/mocked_blind_topic_name/cover/blind/tilt] Publishing message: 0" in logs
        assert "[MQTT] [mocked_unipi/mocked_blind_topic_name/cover/blind/state] Publishing message: opening" in logs
        assert "[COVER] [mocked_unipi/mocked_blind_topic_name/cover/blind] [Worker] 1 task(s) in queue." in logs
        assert "[MQTT] [mocked_unipi/mocked_blind_topic_name/cover/blind/tilt/set] Subscribe message: 50" in logs
        assert (
            "[COVER] [mocked_unipi/mocked_blind_topic_name/cover/blind] [Worker] Cover runtime: 0.25 seconds." in logs
        )
