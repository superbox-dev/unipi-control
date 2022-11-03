import asyncio
import json
from asyncio import Task
from typing import Any
from typing import List
from typing import Set
from typing import Tuple

from unipi_control.config import logger
from unipi_control.features import FeatureState
from unipi_control.logging import LOG_MQTT_PUBLISH
from unipi_control.mqtt.discovery.mixin import HassDiscoveryMixin


class HassBinarySensorsDiscovery(HassDiscoveryMixin):
    """Provide the binary sensors (e.g. digital input) as Home Assistant MQTT discovery."""

    publish_feature_types: List[str] = ["DI"]

    def _get_discovery(self, feature) -> Tuple[str, dict]:
        topic: str = self._get_topic("binary_sensor", feature)
        device_name: str = self._get_device_name(feature)

        message: dict = {
            "name": self._get_friendly_name(feature),
            "unique_id": self._get_unique_id(feature),
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

        if object_id := self._get_object_id(feature):
            message["object_id"] = object_id

        if suggested_area := self._get_suggested_area(feature):
            message["device"]["suggested_area"] = suggested_area

        if self._get_invert_state(feature):
            message["payload_on"] = FeatureState.OFF
            message["payload_off"] = FeatureState.ON

        return topic, message

    async def publish(self):
        for feature in self.neuron.features.by_feature_types(self.publish_feature_types):
            topic, message = self._get_discovery(feature)
            json_data: str = json.dumps(message)
            await self.mqtt_client.publish(topic, json_data, qos=2, retain=True)
            logger.debug(LOG_MQTT_PUBLISH, topic, json_data)


class HassBinarySensorsMqttPlugin:
    """Provide Home Assistant MQTT commands for binary sensors."""

    def __init__(self, neuron, mqtt_client):
        self._hass = HassBinarySensorsDiscovery(neuron, mqtt_client)

    async def init_tasks(self, tasks: Set[Task]):
        task: Task[Any] = asyncio.create_task(self._hass.publish())
        tasks.add(task)
