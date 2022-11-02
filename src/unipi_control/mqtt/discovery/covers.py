import asyncio
import json
from asyncio import Task
from typing import Any
from typing import Set
from typing import Tuple

from unipi_control.config import COVER_TYPES
from unipi_control.config import logger
from unipi_control.integrations.covers import CoverMap
from unipi_control.logging import LOG_MQTT_PUBLISH
from unipi_control.mqtt.discovery.mixin import HassDiscoveryMixin


class HassCoversDiscovery(HassDiscoveryMixin):
    """Provide the covers as Home Assistant MQTT discovery."""

    def __init__(self, covers: CoverMap, *args):
        super().__init__(*args)
        self.covers: CoverMap = covers

    def _get_discovery(self, cover) -> Tuple[str, dict]:
        topic: str = self._get_topic("cover", cover)
        device_name: str = self.config.device_info.name

        if cover.suggested_area:
            device_name = f"{device_name}: {cover.suggested_area}"

        message: dict = {
            "name": cover.friendly_name,
            "unique_id": f"{cover.cover_type}_{cover.object_id}",
            "command_topic": f"{cover.topic}/set",
            "state_topic": f"{cover.topic}/state",
            "qos": 2,
            "optimistic": False,
            "device": {
                "name": device_name,
                "identifiers": device_name,
                "model": self._get_device_model(),
                "manufacturer": self._get_device_manufacturer(),
            },
        }

        if cover.object_id:
            message["object_id"] = cover.object_id

        if cover.suggested_area:
            message["device"]["suggested_area"] = cover.suggested_area

        if cover.settings.set_position:
            message["position_topic"] = f"{cover.topic}/position"
            message["set_position_topic"] = f"{cover.topic}/position/set"

        if cover.settings.set_tilt:
            message["tilt_status_topic"] = f"{cover.topic}/tilt"
            message["tilt_command_topic"] = f"{cover.topic}/tilt/set"

        return topic, message

    async def publish(self):
        for cover in self.covers.by_cover_types(COVER_TYPES):
            topic, message = self._get_discovery(cover)
            json_data: str = json.dumps(message)
            await self.mqtt_client.publish(topic, json_data, qos=2, retain=True)
            logger.debug(LOG_MQTT_PUBLISH, topic, json_data)


class HassCoversMqttPlugin:
    """Provide Home Assistant MQTT commands for covers."""

    def __init__(self, neuron, mqtt_client, covers: CoverMap):
        self._hass = HassCoversDiscovery(covers, neuron, mqtt_client)

    async def init_tasks(self, tasks: Set[Task]):
        task: Task[Any] = asyncio.create_task(self._hass.publish())
        tasks.add(task)
