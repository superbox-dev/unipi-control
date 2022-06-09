import asyncio
import json
from asyncio import Task
from dataclasses import asdict
from typing import Any
from typing import Optional
from typing import Set
from typing import Tuple

from config import HardwareData
from config import LOG_MQTT_PUBLISH
from config import config
from config import logger
from plugins.hass.discover import HassBaseDiscovery


class HassBinarySensorsDiscovery(HassBaseDiscovery):
    """Provide the binary sensors (e.g. digital input) as Home Assistant MQTT discovery.

    Attributes
    ----------
    hardware : HardwareData
        The Unipi Neuron hardware definitions.
    """

    def __init__(self, uc, mqtt_client):
        self._uc = uc
        self._mqtt_client = mqtt_client
        self.hardware: HardwareData = uc.neuron.hardware

    def _get_discovery(self, feature) -> Tuple[str, dict]:
        topic: str = f"{config.homeassistant.discovery_prefix}/binary_sensor/{config.device_name.lower()}/{feature.circuit}/config"
        suggested_area: Optional[str] = self._get_suggested_area(feature)
        invert_state: bool = self._get_invert_state(feature)
        device_name: str = config.device_name

        if suggested_area:
            device_name = f"{device_name}: {suggested_area}"

        message: dict = {
            "name": self._get_friendly_name(feature),
            "unique_id": f"{config.device_name.lower()}_{feature.circuit}",
            "state_topic": f"{feature.topic}/get",
            "qos": 2,
            "device": {
                "name": device_name,
                "identifiers": device_name,
                "model": f"""{self.hardware["neuron"]["name"]} {self.hardware["neuron"]["model"]}""",
                "sw_version": self._uc.neuron.boards[feature.major_group - 1].firmware,
                "suggested_area": suggested_area,
                **asdict(config.homeassistant.device),
            },
        }

        if invert_state:
            message.update(
                {
                    "payload_on": "OFF",
                    "payload_off": "ON",
                }
            )

        return topic, message

    async def publish(self):
        for feature in self._uc.neuron.features.by_feature_type(["DI"]):
            topic, message = self._get_discovery(feature)
            json_data: str = json.dumps(message)
            await self._mqtt_client.publish(topic, json_data, qos=2, retain=True)
            logger.debug(LOG_MQTT_PUBLISH, topic, json_data)


class HassBinarySensorsMqttPlugin:
    """Provide Home Assistant MQTT commands for binary sensors."""

    def __init__(self, uc, mqtt_client):
        self._hass = HassBinarySensorsDiscovery(uc, mqtt_client)

    async def init_tasks(self) -> Set[Task]:
        tasks: Set[Task] = set()

        task: Task[Any] = asyncio.create_task(self._hass.publish())
        tasks.add(task)

        return tasks
