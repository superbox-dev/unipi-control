import asyncio
import json
from asyncio import Task
from typing import Any
from typing import List
from typing import Set
from typing import Tuple

from asyncio_mqtt import Client

from unipi_control.config import logger
from unipi_control.helpers.log import LOG_MQTT_PUBLISH
from unipi_control.mqtt.discovery.mixin import HassDiscoveryMixin
from unipi_control.neuron import Neuron


class HassSensorsDiscovery(HassDiscoveryMixin):
    """Provide the sensors (e.g. meter) as Home Assistant MQTT discovery."""

    publish_feature_types: List[str] = ["METER"]

    def _get_discovery(self, feature) -> Tuple[str, dict]:
        topic: str = f"{self.config.homeassistant.discovery_prefix}/sensor/{feature.unique_id}/config"
        device_name: str = self._get_device_name(feature)

        message: dict = {
            "name": feature.friendly_name,
            "unique_id": feature.unique_id,
            "state_topic": f"{feature.topic}/get",
            "qos": 2,
            "force_update": True,
            "device": {
                "name": device_name,
                "identifiers": device_name,
                "model": self._get_device_model(feature),
                "sw_version": "" if feature.sw_version is None else str(feature.sw_version),
                "manufacturer": self._get_device_manufacturer(feature),
            },
        }

        if feature.object_id:
            message["object_id"] = feature.object_id

        if feature.icon:
            message["icon"] = feature.icon

        if feature.device_class:
            message["device_class"] = feature.device_class

        if feature.state_class:
            message["state_class"] = feature.state_class

        if feature.unit_of_measurement:
            message["unit_of_measurement"] = feature.unit_of_measurement

        if feature.suggested_area:
            message["device"]["suggested_area"] = feature.suggested_area

        if via_device := self._get_via_device(feature):
            message["device"]["via_device"] = via_device

        return topic, message

    async def publish(self) -> None:
        """Publish MQTT Home Assistant discovery topics for sensors."""
        for feature in self.neuron.features.by_feature_types(self.publish_feature_types):
            topic, message = self._get_discovery(feature)
            json_data: str = json.dumps(message)
            await self.mqtt_client.publish(topic, json_data, qos=2, retain=True)
            logger.debug(LOG_MQTT_PUBLISH, topic, json_data)


class HassSensorsMqttPlugin:
    """Provide Home Assistant MQTT commands for sensors."""

    def __init__(self, neuron: Neuron, mqtt_client: Client) -> None:
        self._hass = HassSensorsDiscovery(neuron, mqtt_client)

    async def init_tasks(self, tasks: Set[Task]) -> None:
        """Initialize MQTT tasks for publish MQTT topics.

        Parameters
        ----------
        tasks: set
            A set of all MQTT tasks.
        """
        task: Task[Any] = asyncio.create_task(self._hass.publish())
        tasks.add(task)
