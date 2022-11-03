import asyncio
import json
from asyncio import Task
from typing import Any
from typing import List
from typing import Set
from typing import Tuple

from unipi_control.config import logger
from unipi_control.logging import LOG_MQTT_PUBLISH
from unipi_control.mqtt.discovery.mixin import HassDiscoveryMixin


class HassSensorsDiscovery(HassDiscoveryMixin):
    """Provide the sensors (e.g. meter) as Home Assistant MQTT discovery."""

    publish_feature_types: List[str] = ["METER"]

    def _get_discovery(self, feature) -> Tuple[str, dict]:
        topic: str = self._get_topic("sensor", feature)
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
                "sw_version": "" if feature.sw_version is None else str(feature.sw_version),
                "manufacturer": self._get_device_manufacturer(feature),
                "via_device": self._get_device_name(feature),
            },
        }

        if object_id := self._get_object_id(feature):
            message["object_id"] = object_id

        if feature.icon:
            message["icon"] = feature.icon

        if feature.device_class:
            message["device_class"] = feature.device_class

        if feature.state_class:
            message["state_class"] = feature.state_class

        if feature.unit_of_measurement:
            message["unit_of_measurement"] = feature.unit_of_measurement

        if suggested_area := self._get_suggested_area(feature):
            message["device"]["suggested_area"] = suggested_area

        if via_device := self._get_via_device(feature):
            message["device"]["via_device"] = via_device

        return topic, message

    async def publish(self):
        for feature in self.neuron.features.by_feature_types(self.publish_feature_types):
            topic, message = self._get_discovery(feature)
            json_data: str = json.dumps(message)
            await self.mqtt_client.publish(topic, json_data, qos=2, retain=True)
            logger.debug(LOG_MQTT_PUBLISH, topic, json_data)


class HassSensorsMqttPlugin:
    """Provide Home Assistant MQTT commands for sensors."""

    def __init__(self, neuron, mqtt_client):
        self._hass = HassSensorsDiscovery(neuron, mqtt_client)

    async def init_tasks(self, tasks: Set[Task]):
        task: Task[Any] = asyncio.create_task(self._hass.publish())
        tasks.add(task)
