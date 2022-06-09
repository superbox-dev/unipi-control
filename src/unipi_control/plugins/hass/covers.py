import asyncio
import json
from asyncio import Task
from dataclasses import asdict
from typing import Any
from typing import Set
from typing import Tuple

from config import COVER_TYPES
from config import HardwareData
from config import LOG_MQTT_PUBLISH
from config import config
from config import logger
from covers import CoverMap


class HassCoversDiscovery:
    """Provide the covers as Home Assistant MQTT discovery.

    Attributes
    ----------
    hardware : HardwareData
        The Unipi Neuron hardware definitions.
    """

    def __init__(self, uc, mqtt_client, covers):
        self._mqtt_client = mqtt_client
        self._covers: CoverMap = covers
        self.hardware: HardwareData = uc.neuron.hardware

    def _get_discovery(self, cover) -> Tuple[str, dict]:
        topic: str = f"{config.homeassistant.discovery_prefix}/cover/{cover.topic_name}/config"
        device_name: str = config.device_name

        if cover.suggested_area:
            device_name = f"{config.device_name}: {cover.suggested_area}"

        message: dict = {
            "name": cover.friendly_name,
            "unique_id": f"{cover.cover_type}_{cover.topic_name}",
            "command_topic": f"{cover.topic}/set",
            "state_topic": f"{cover.topic}/state",
            "position_topic": f"{cover.topic}/position",
            "qos": 2,
            "optimistic": False,
            "device": {
                "name": device_name,
                "identifiers": device_name,
                "model": f"""{self.hardware["neuron"]["name"]} {self.hardware["neuron"]["model"]}""",
                "suggested_area": cover.suggested_area or "",
                **asdict(config.homeassistant.device),
            },
        }

        if cover.settings.set_position:
            message.update(
                {
                    "set_position_topic": f"{cover.topic}/position/set",
                }
            )

        if cover.settings.set_tilt:
            message.update(
                {
                    "tilt_status_topic": f"{cover.topic}/tilt",
                    "tilt_command_topic": f"{cover.topic}/tilt/set",
                }
            )

        return topic, message

    async def publish(self):
        for cover in self._covers.by_cover_type(COVER_TYPES):
            topic, message = self._get_discovery(cover)
            json_data: str = json.dumps(message)
            await self._mqtt_client.publish(topic, json_data, qos=2, retain=True)
            logger.debug(LOG_MQTT_PUBLISH, topic, json_data)


class HassCoversMqttPlugin:
    """Provide Home Assistant MQTT commands for covers."""

    def __init__(self, uc, mqtt_client, covers):
        self._hass = HassCoversDiscovery(uc, mqtt_client, covers)

    async def init_tasks(self) -> Set[Task]:
        tasks: Set[Task] = set()

        task: Task[Any] = asyncio.create_task(self._hass.publish())
        tasks.add(task)

        return tasks
