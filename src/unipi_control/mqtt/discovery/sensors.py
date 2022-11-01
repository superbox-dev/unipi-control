import asyncio
import json
from asyncio import Task
from typing import Any
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple

from unipi_control.config import logger
from unipi_control.logging import LOG_MQTT_PUBLISH
from unipi_control.mqtt.discovery.base import HassBaseDiscovery


# TODO: write test
class HassSensorsDiscovery(HassBaseDiscovery):
    """Provide the sensors (e.g. meter) as Home Assistant MQTT discovery."""

    publish_feature_types: List[str] = ["METER"]

    def _get_discovery(self, feature) -> Tuple[str, dict]:
        topic: str = self._get_topic("sensor", feature)
        object_id: Optional[str] = self._get_object_id(feature)
        suggested_area: Optional[str] = self._get_suggested_area(feature)
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
                # TODO: test via_device
            },
        }

        if feature.device_class:
            message["device_class"] = feature.device_class

        if feature.state_class:
            message["state_class"] = feature.state_class

        if object_id:
            message["object_id"] = object_id

        if suggested_area:
            message["device"]["suggested_area"] = suggested_area

        return topic, message

    async def publish(self):
        for feature in self.neuron.features.by_feature_type(self.publish_feature_types):
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
