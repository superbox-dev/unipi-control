import asyncio
import json
from asyncio import Task
from typing import Any
from typing import Set
from typing import Tuple

from unipi_control.config import COVER_TYPES
from unipi_control.config import Config
from unipi_control.config import HardwareData
from unipi_control.config import logger
from unipi_control.covers import CoverMap
from unipi_control.logging import LOG_MQTT_PUBLISH


class HassCoversDiscovery:
    """Provide the covers as Home Assistant MQTT discovery.

    Attributes
    ----------
    hardware : HardwareData
        The Unipi Neuron hardware definitions.
    """

    def __init__(self, neuron, mqtt_client, covers: CoverMap):
        self.config: Config = neuron.config

        self._mqtt_client = mqtt_client
        self._covers: CoverMap = covers
        self.hardware: HardwareData = neuron.hardware

    def _get_discovery(self, cover) -> Tuple[str, dict]:
        topic: str = f"{self.config.homeassistant.discovery_prefix}/cover/{cover.topic_name}/config"
        device_name: str = self.config.device_info.name

        if cover.suggested_area:
            device_name = f"{device_name}: {cover.suggested_area}"

        message: dict = {
            "name": cover.friendly_name,
            "unique_id": f"{cover.cover_type}_{cover.topic_name}",
            "command_topic": f"{cover.topic}/set",
            "state_topic": f"{cover.topic}/state",
            "qos": 2,
            "optimistic": False,
            "device": {
                "name": device_name,
                "identifiers": device_name,
                "model": f"""{self.hardware["neuron"]["name"]} {self.hardware["neuron"]["model"]}""",
                "manufacturer": self.config.device_info.manufacturer,
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
        for cover in self._covers.by_cover_type(COVER_TYPES):
            topic, message = self._get_discovery(cover)
            json_data: str = json.dumps(message)
            await self._mqtt_client.publish(topic, json_data, qos=2, retain=True)
            logger.debug(LOG_MQTT_PUBLISH, topic, json_data)


class HassCoversMqttPlugin:
    """Provide Home Assistant MQTT commands for covers."""

    def __init__(self, neuron, mqtt_client, covers: CoverMap):
        self._hass = HassCoversDiscovery(neuron, mqtt_client, covers)

    async def init_tasks(self) -> Set[Task]:
        tasks: Set[Task] = set()

        task: Task[Any] = asyncio.create_task(self._hass.publish())
        tasks.add(task)

        return tasks
