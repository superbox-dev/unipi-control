import asyncio
from asyncio import Task
from contextlib import AsyncExitStack
from typing import Set
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import PropertyMock

import pytest
from _pytest.logging import LogCaptureFixture
from asyncio_mqtt import Client
from pytest_mock import MockerFixture

from conftest import ConfigLoader
from conftest import MockMQTTMessages
from conftest_data import CONFIG_CONTENT
from conftest_data import HARDWARE_DATA_CONTENT
from unipi_control.neuron import Neuron
from unipi_control.plugins.features import FeaturesMqttPlugin


class TestHappyPathFeaturesMqttPlugin:
    @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
    def test_init_tasks(
        self,
        mocker: MockerFixture,
        modbus_client: AsyncMock,
        config_loader: ConfigLoader,
        neuron: Neuron,
        caplog: LogCaptureFixture,
    ):
        async def run():
            mock_mqtt_messages: AsyncMock = AsyncMock()
            mock_mqtt_messages.__aenter__.return_value = MockMQTTMessages([b"""ON""", b"""OFF"""])

            mock_mqtt_client: AsyncMock = AsyncMock(spec=Client)
            mock_mqtt_client.filtered_messages.return_value = mock_mqtt_messages

            mock_neuron_scan: MagicMock = mocker.patch("unipi_control.neuron.Neuron.scan")

            FeaturesMqttPlugin.PUBLISH_RUNNING = PropertyMock(side_effect=[True, False])
            plugin: FeaturesMqttPlugin = FeaturesMqttPlugin(neuron=neuron, mqtt_client=mock_mqtt_client)

            async with AsyncExitStack() as stack:
                tasks: Set[Task] = set()

                await stack.enter_async_context(mock_mqtt_client)

                features_tasks = await plugin.init_tasks(stack)
                tasks.update(features_tasks)

                await asyncio.gather(*tasks)

                for task in tasks:
                    assert True is task.done()

            logs: list = [record.getMessage() for record in caplog.records]

            mock_neuron_scan.assert_called_once()

            for do in range(1, 4):
                assert f"[MQTT] Subscribe topic mocked_unipi/relay/do_1_{do:02d}/set" in logs

            for bord in range(2, 3):
                for ro in range(1, 4):
                    assert f"[MQTT] Subscribe topic mocked_unipi/relay/ro_{bord}_{ro:02d}/set" in logs

            assert "[MQTT] [mocked_unipi/relay/do_1_01/set] Subscribe message: OFF" in logs
            assert "[MQTT] [mocked_unipi/relay/do_1_01/set] Subscribe message: ON" in logs
            assert "[MQTT] [mocked_unipi/relay/ro_2_01/get] Publishing message: OFF" in logs
            assert "[MQTT] [mocked_unipi/relay/ro_2_13/get] Publishing message: ON" in logs

            assert 102 == len(logs)

        loop = asyncio.new_event_loop()
        loop.run_until_complete(run())
