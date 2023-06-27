"""Unit tests MQTT for Home Assistant switches."""

import asyncio
from asyncio import Task
from typing import Any, TYPE_CHECKING
from typing import Dict
from typing import Iterator
from typing import List
from typing import Set
from typing import Union
from unittest.mock import AsyncMock

import pytest
from _pytest.logging import LogCaptureFixture  # pylint: disable=import-private-name
from aiomqtt import Client

from tests.conftest_data import CONFIG_CONTENT
from tests.conftest_data import EXTENSION_HARDWARE_DATA_CONTENT
from tests.conftest_data import HARDWARE_DATA_CONTENT
from tests.unit.mqtt.discovery.test_switches_data import discovery_message_expected
from unipi_control.features.neuron import DigitalInput
from unipi_control.features.neuron import DigitalOutput
from unipi_control.features.neuron import Led
from unipi_control.features.neuron import Relay
from unipi_control.mqtt.discovery.switches import HassSwitchesDiscoveryMixin
from unipi_control.mqtt.discovery.switches import HassSwitchesMqttPlugin
from unipi_control.neuron import Neuron

if TYPE_CHECKING:
    from unipi_control.features.extensions import EastronMeter


class TestHappyPathHassSwitchesMqttPlugin:
    @pytest.mark.asyncio()
    @pytest.mark.parametrize(
        "config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    async def test_init_tasks(self, neuron: Neuron, caplog: LogCaptureFixture) -> None:
        """Test mqtt output after initialize Home Assistant switches."""
        mock_mqtt_client: AsyncMock = AsyncMock(spec=Client)
        plugin: HassSwitchesMqttPlugin = HassSwitchesMqttPlugin(neuron=neuron, mqtt_client=mock_mqtt_client)

        tasks: Set[Task] = set()

        await plugin.init_tasks(tasks)
        await asyncio.gather(*tasks)

        for task in tasks:
            assert task.done() is True

        logs: List[str] = [record.getMessage() for record in caplog.records]

        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_mocked_id_ro_2_01/config] "
            "Publishing message: {"
            '"name": "MOCKED_FRIENDLY_NAME - RO_2_01", '
            '"unique_id": "mocked_unipi_mocked_id_ro_2_01", '
            '"command_topic": "mocked_unipi/relay/ro_2_01/set", '
            '"state_topic": "mocked_unipi/relay/ro_2_01/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI - MOCKED AREA 2", '
            '"identifiers": "MOCKED UNIPI - MOCKED AREA 2", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology", '
            '"suggested_area": "MOCKED AREA 2", '
            '"via_device": "MOCKED UNIPI"'
            "}, "
            '"object_id": "mocked_id_ro_2_01", '
            '"payload_on": "OFF", '
            '"payload_off": "ON"'
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_mocked_id_ro_2_02/config] "
            "Publishing message: {"
            '"name": "MOCKED_FRIENDLY_NAME - RO_2_02", '
            '"unique_id": "mocked_unipi_mocked_id_ro_2_02", '
            '"command_topic": "mocked_unipi/relay/ro_2_02/set", '
            '"state_topic": "mocked_unipi/relay/ro_2_02/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI - MOCKED AREA 2", '
            '"identifiers": "MOCKED UNIPI - MOCKED AREA 2", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology", '
            '"suggested_area": "MOCKED AREA 2", '
            '"via_device": "MOCKED UNIPI"'
            "}, "
            '"object_id": "mocked_id_ro_2_02", '
            '"icon": "mdi:power-standby", '
            '"device_class": "switch"'
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_ro_2_03/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Relay 2.03", '
            '"unique_id": "mocked_unipi_ro_2_03", '
            '"command_topic": "mocked_unipi/relay/ro_2_03/set", '
            '"state_topic": "mocked_unipi/relay/ro_2_03/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": '
            '"Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_ro_2_04/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Relay 2.04", '
            '"unique_id": "mocked_unipi_ro_2_04", '
            '"command_topic": "mocked_unipi/relay/ro_2_04/set", '
            '"state_topic": "mocked_unipi/relay/ro_2_04/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_ro_2_05/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Relay 2.05", '
            '"unique_id": "mocked_unipi_ro_2_05", '
            '"command_topic": "mocked_unipi/relay/ro_2_05/set", '
            '"state_topic": "mocked_unipi/relay/ro_2_05/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_ro_2_06/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Relay 2.06", '
            '"unique_id": "mocked_unipi_ro_2_06", '
            '"command_topic": "mocked_unipi/relay/ro_2_06/set", '
            '"state_topic": "mocked_unipi/relay/ro_2_06/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_ro_2_07/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Relay 2.07", '
            '"unique_id": "mocked_unipi_ro_2_07", '
            '"command_topic": "mocked_unipi/relay/ro_2_07/set", '
            '"state_topic": "mocked_unipi/relay/ro_2_07/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_ro_2_08/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Relay 2.08", '
            '"unique_id": "mocked_unipi_ro_2_08", '
            '"command_topic": "mocked_unipi/relay/ro_2_08/set", '
            '"state_topic": "mocked_unipi/relay/ro_2_08/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_ro_2_09/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Relay 2.09", '
            '"unique_id": "mocked_unipi_ro_2_09", '
            '"command_topic": "mocked_unipi/relay/ro_2_09/set", '
            '"state_topic": "mocked_unipi/relay/ro_2_09/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_ro_2_10/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Relay 2.10", '
            '"unique_id": "mocked_unipi_ro_2_10", '
            '"command_topic": "mocked_unipi/relay/ro_2_10/set", '
            '"state_topic": "mocked_unipi/relay/ro_2_10/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_ro_2_11/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Relay 2.11", '
            '"unique_id": "mocked_unipi_ro_2_11", '
            '"command_topic": "mocked_unipi/relay/ro_2_11/set", '
            '"state_topic": "mocked_unipi/relay/ro_2_11/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_ro_2_12/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Relay 2.12", '
            '"unique_id": "mocked_unipi_ro_2_12", '
            '"command_topic": "mocked_unipi/relay/ro_2_12/set", '
            '"state_topic": "mocked_unipi/relay/ro_2_12/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_ro_2_13/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Relay 2.13", '
            '"unique_id": "mocked_unipi_ro_2_13", '
            '"command_topic": "mocked_unipi/relay/ro_2_13/set", '
            '"state_topic": "mocked_unipi/relay/ro_2_13/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_ro_2_14/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Relay 2.14", '
            '"unique_id": "mocked_unipi_ro_2_14", '
            '"command_topic": "mocked_unipi/relay/ro_2_14/set", '
            '"state_topic": "mocked_unipi/relay/ro_2_14/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_ro_3_05/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Relay 3.05", '
            '"unique_id": "mocked_unipi_ro_3_05", '
            '"command_topic": "mocked_unipi/relay/ro_3_05/set", '
            '"state_topic": "mocked_unipi/relay/ro_3_05/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_ro_3_06/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Relay 3.06", '
            '"unique_id": "mocked_unipi_ro_3_06", '
            '"command_topic": "mocked_unipi/relay/ro_3_06/set", '
            '"state_topic": "mocked_unipi/relay/ro_3_06/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_ro_3_07/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Relay 3.07", '
            '"unique_id": "mocked_unipi_ro_3_07", '
            '"command_topic": "mocked_unipi/relay/ro_3_07/set", '
            '"state_topic": "mocked_unipi/relay/ro_3_07/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_ro_3_08/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Relay 3.08", '
            '"unique_id": "mocked_unipi_ro_3_08", '
            '"command_topic": "mocked_unipi/relay/ro_3_08/set", '
            '"state_topic": "mocked_unipi/relay/ro_3_08/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_ro_3_09/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Relay 3.09", '
            '"unique_id": "mocked_unipi_ro_3_09", '
            '"command_topic": "mocked_unipi/relay/ro_3_09/set", '
            '"state_topic": "mocked_unipi/relay/ro_3_09/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_ro_3_10/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Relay 3.10", '
            '"unique_id": "mocked_unipi_ro_3_10",'
            ' "command_topic": "mocked_unipi/relay/ro_3_10/set", '
            '"state_topic": "mocked_unipi/relay/ro_3_10/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_ro_3_11/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Relay 3.11", '
            '"unique_id": "mocked_unipi_ro_3_11", '
            '"command_topic": "mocked_unipi/relay/ro_3_11/set", '
            '"state_topic": "mocked_unipi/relay/ro_3_11/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_ro_3_12/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Relay 3.12", '
            '"unique_id": "mocked_unipi_ro_3_12", '
            '"command_topic": "mocked_unipi/relay/ro_3_12/set", '
            '"state_topic": "mocked_unipi/relay/ro_3_12/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_ro_3_13/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Relay 3.13", '
            '"unique_id": "mocked_unipi_ro_3_13", '
            '"command_topic": "mocked_unipi/relay/ro_3_13/set", '
            '"state_topic": "mocked_unipi/relay/ro_3_13/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_ro_3_14/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Relay 3.14", '
            '"unique_id": "mocked_unipi_ro_3_14", '
            '"command_topic": "mocked_unipi/relay/ro_3_14/set", '
            '"state_topic": "mocked_unipi/relay/ro_3_14/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_do_1_01/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Digital Output 1.01", '
            '"unique_id": "mocked_unipi_do_1_01", '
            '"command_topic": "mocked_unipi/relay/do_1_01/set", '
            '"state_topic": "mocked_unipi/relay/do_1_01/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_do_1_02/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Digital Output 1.02", '
            '"unique_id": "mocked_unipi_do_1_02", '
            '"command_topic": "mocked_unipi/relay/do_1_02/set", '
            '"state_topic": "mocked_unipi/relay/do_1_02/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_do_1_03/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Digital Output 1.03", '
            '"unique_id": "mocked_unipi_do_1_03", '
            '"command_topic": "mocked_unipi/relay/do_1_03/set", '
            '"state_topic": "mocked_unipi/relay/do_1_03/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert (
            "[MQTT] [homeassistant/switch/mocked_unipi_do_1_04/config] "
            "Publishing message: {"
            '"name": "MOCKED UNIPI: Digital Output 1.04", '
            '"unique_id": "mocked_unipi_do_1_04", '
            '"command_topic": "mocked_unipi/relay/do_1_04/set", '
            '"state_topic": "mocked_unipi/relay/do_1_04/get", '
            '"qos": 2, '
            '"device": {'
            '"name": "MOCKED UNIPI", '
            '"identifiers": "MOCKED UNIPI", '
            '"model": "MOCKED_NAME MOCKED_MODEL", '
            '"sw_version": "0.0", '
            '"manufacturer": "Unipi technology"'
            "}"
            "}" in logs
        )
        assert len(logs) == 28

    @pytest.mark.parametrize(
        ("config_loader", "expected"),
        [
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                discovery_message_expected,
            ),
        ],
        indirect=["config_loader"],
    )
    def test_discovery_message(self, neuron: Neuron, expected: List[Dict[str, Any]]) -> None:
        """Test mqtt topic and message when publish a feature."""
        mock_mqtt_client: AsyncMock = AsyncMock(spec=Client)
        plugin: HassSwitchesMqttPlugin = HassSwitchesMqttPlugin(neuron=neuron, mqtt_client=mock_mqtt_client)
        features: Iterator[
            Union[DigitalInput, DigitalOutput, Led, Relay, EastronMeter]
        ] = neuron.features.by_feature_types(HassSwitchesDiscoveryMixin.publish_feature_types)

        for index, feature in enumerate(features):
            if isinstance(feature, (DigitalOutput, Relay)):
                topic, message = plugin.hass.get_discovery(feature)

                assert message == expected[index]["message"]
                assert topic == expected[index]["topic"]
