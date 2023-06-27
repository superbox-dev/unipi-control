"""Initialize MQTT subscribe and publish for Home Assistant switches."""

import asyncio
import json
from asyncio import Task
from typing import Any, ClassVar
from typing import Dict
from typing import List
from typing import Set
from typing import Tuple
from typing import Union

from aiomqtt import Client

from unipi_control.config import UNIPI_LOGGER
from unipi_control.features.neuron import DigitalOutput
from unipi_control.features.neuron import Relay
from unipi_control.features.utils import FeatureState
from unipi_control.helpers.log import LOG_MQTT_PUBLISH
from unipi_control.mqtt.discovery.mixin import HassDiscoveryMixin
from unipi_control.neuron import Neuron


class HassSwitchesDiscoveryMixin(HassDiscoveryMixin):
    """Provide the switches (e.g. relay) as Home Assistant MQTT discovery."""

    publish_feature_types: ClassVar[List[str]] = ["DO", "RO"]

    def get_discovery(self, feature: Union[DigitalOutput, Relay]) -> Tuple[str, Dict[str, Any]]:
        """Get Mqtt topic and message for publish with mqtt.

        Parameters
        ----------
        feature:
            All output features.

        Returns
        -------
        tuple:
            Return mqtt topic and message as tuple.
        """
        topic: str = f"{self.config.homeassistant.discovery_prefix}/switch/{feature.unique_id}/config"
        device_name: str = self._get_device_name(feature)

        message: Dict[str, Any] = {
            "name": feature.friendly_name,
            "unique_id": feature.unique_id,
            "command_topic": f"{feature.topic}/set",
            "state_topic": f"{feature.topic}/get",
            "qos": 2,
            "device": {
                "name": device_name,
                "identifiers": device_name,
                "model": self._get_device_model(feature),
                "sw_version": feature.sw_version,
                "manufacturer": self._get_device_manufacturer(feature),
            },
        }

        if feature.object_id:
            message["object_id"] = feature.object_id

        if feature.icon:
            message["icon"] = feature.icon

        if feature.device_class:
            message["device_class"] = feature.device_class

        if self._get_invert_state(feature):
            message["payload_on"] = FeatureState.OFF
            message["payload_off"] = FeatureState.ON

        if feature.suggested_area:
            message["device"]["suggested_area"] = feature.suggested_area

        if via_device := self._get_via_device(feature):
            message["device"]["via_device"] = via_device

        return topic, message

    async def publish(self) -> None:
        """Publish MQTT Home Assistant discovery topics for switches."""
        for feature in self.neuron.features.by_feature_types(self.publish_feature_types):
            if (
                isinstance(feature, (DigitalOutput, Relay))
                and feature.feature_id not in self.config.get_cover_circuits()
            ):
                topic, message = self.get_discovery(feature)

                json_data: str = json.dumps(message)
                await self.mqtt_client.publish(topic, json_data, qos=2, retain=True)
                UNIPI_LOGGER.debug(LOG_MQTT_PUBLISH, topic, json_data)


class HassSwitchesMqttPlugin:
    """Provide Home Assistant MQTT commands for switches."""

    def __init__(self, neuron: Neuron, mqtt_client: Client) -> None:
        self.hass = HassSwitchesDiscoveryMixin(neuron, mqtt_client)

    async def init_tasks(self, tasks: Set[Task]) -> None:
        """Initialize MQTT tasks for publish MQTT topics.

        Parameters
        ----------
        tasks: set
            A set of all MQTT tasks.
        """
        task: Task = asyncio.create_task(self.hass.publish())
        tasks.add(task)
