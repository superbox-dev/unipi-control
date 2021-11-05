import asyncio
import json
from dataclasses import asdict

from config import config
from config import COVER_TYPES
from config import LOG_MQTT_PUBLISH
from config import logger


class HassCoversDiscovery:
    def __init__(self, uc, mqtt_client):
        self.uc = uc
        self.mqtt_client = mqtt_client
        self.hardware = uc.neuron.hardware

    def _get_discovery(self, cover) -> tuple:
        topic: str = f"{config.homeassistant.discovery_prefix}/cover/{cover.topic_name}/config"

        message: dict = {
            "name": cover.friendly_name,
            "unique_id": f"{cover.cover_type}_{cover.topic_name}",
            "command_topic": f"{cover.topic}/set",
            "state_topic": f"{cover.topic}/state",
            "position_topic": f"{cover.topic}/position",
            "set_position_topic": f"{cover.topic}/position/set",
            "retain": False,
            "qos": 2,
            "optimistic": False,
            "device": {
                "name": config.device_name,
                "identifiers": config.device_name.lower(),
                "model":
                f"""{self.hardware["neuron"]["name"]} {self.hardware["neuron"]["model"]}""",
                **asdict(config.homeassistant.device),
            }
        }

        if cover.tilt_change_time:
            message.update(
                {
                    "tilt_status_topic": f"{cover.topic}/tilt",
                    "tilt_command_topic": f"{cover.topic}/tilt/set",
                }
            )

        return topic, message

    async def publish(self) -> None:
        for cover in self.uc.covers.by_cover_type(COVER_TYPES):
            topic, message = self._get_discovery(cover)
            json_data: str = json.dumps(message)
            logger.info(LOG_MQTT_PUBLISH, topic, json_data)
            await self.mqtt_client.publish(topic, json_data, qos=2)


class HassCoversMqttPlugin:
    def __init__(self, uc, mqtt_client):
        self.uc = uc
        self.mqtt_client = mqtt_client

        self._hass = HassCoversDiscovery(uc, mqtt_client)

    async def init_task(self) -> set:
        tasks = set()

        task = asyncio.create_task(self._hass.publish())
        tasks.add(task)

        return tasks
